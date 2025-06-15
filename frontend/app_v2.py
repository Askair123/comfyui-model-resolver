"""
ComfyUI Model Resolver v2.0 - Optimized Gradio Frontend
"""

import gradio as gr
import asyncio
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import logging
import time

from api_client import SyncAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global API client
api_client = SyncAPIClient()

# Global state
current_workflows = {}
current_models = {}
search_results = {}
selected_downloads = {}

# Model type icons and colors
MODEL_TYPE_INFO = {
    "checkpoint": {"icon": "🗂️", "color": "#4CAF50"},
    "lora": {"icon": "🎨", "color": "#2196F3"},
    "vae": {"icon": "🔧", "color": "#FF9800"},
    "clip": {"icon": "📎", "color": "#9C27B0"},
    "unet": {"icon": "🧠", "color": "#F44336"},
    "controlnet": {"icon": "🎮", "color": "#00BCD4"},
    "upscale": {"icon": "⬆️", "color": "#795548"},
    "unknown": {"icon": "❓", "color": "#607D8B"}
}


def format_file_size(size_bytes: Optional[int]) -> str:
    """Format file size to human readable."""
    if not size_bytes:
        return "未知大小"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def refresh_workflows(directory: str) -> Tuple[gr.CheckboxGroup, str]:
    """Refresh workflow list from directory."""
    try:
        workflows = api_client.list_workflows(directory)
        
        # Format for checkbox group
        choices = []
        values = []
        
        for wf in workflows:
            # Format label with status
            status_icon = {
                "ready": "✅",
                "partial": "⚠️",
                "missing": "❌",
                "unanalyzed": "❓"
            }.get(wf['status'], "❓")
            
            # Format workflow info
            missing_info = f"{wf.get('missing_count', 0)}个缺失" if wf.get('missing_count', 0) > 0 else "全部就绪"
            label = f"{status_icon} {wf['name']} ({missing_info})"
            choices.append((label, wf['path']))
            
            # Store workflow data
            current_workflows[wf['path']] = wf
            
            # Auto-select workflows with missing models
            if wf['status'] in ['partial', 'missing']:
                values.append(wf['path'])
        
        info = f"📁 找到 {len(workflows)} 个工作流"
        
        return gr.CheckboxGroup(choices=choices, value=values), info
        
    except Exception as e:
        logger.error(f"Error refreshing workflows: {e}")
        return gr.CheckboxGroup(choices=[], value=[]), f"❌ 错误: {str(e)}"


def analyze_selected_workflows(selected_paths: List[str]) -> Tuple[gr.CheckboxGroup, str, str, gr.DataFrame]:
    """Analyze selected workflows and display models."""
    if not selected_paths:
        return gr.CheckboxGroup(choices=[], value=[]), "请选择要分析的工作流", "", gr.DataFrame()
    
    try:
        # Analyze workflows
        result = api_client.analyze_workflows(selected_paths)
        
        # Clear previous state
        current_models.clear()
        
        # Format workflow info
        workflow_info = f"### 📊 分析结果\n\n"
        workflow_info += f"- 🗂️ 分析工作流数: {len(result['workflows'])}\n"
        workflow_info += f"- 📦 总模型数: {result['total_models']}\n"
        workflow_info += f"- ❌ 缺失模型数: {result['missing_models']}\n"
        workflow_info += f"- ⏱️ 分析耗时: {result['analysis_time']:.2f}秒\n"
        
        # Format model choices with enhanced info
        model_choices = []
        model_values = []
        table_data = []
        
        for model in result['models']:
            # Get model type info
            type_info = MODEL_TYPE_INFO.get(model['model_type'], MODEL_TYPE_INFO['unknown'])
            
            # Format status
            status = "✅ 已存在" if model['exists_locally'] else "❌ 缺失"
            
            # Format label with icon and status
            label = f"{type_info['icon']} [{model['model_type'].upper()}] {model['filename']} — {status}"
            
            model_choices.append((label, model['filename']))
            
            # Default selection: missing models
            if not model['exists_locally']:
                model_values.append(model['filename'])
            
            # Store model data
            current_models[model['filename']] = model
            
            # Add to table data
            table_data.append({
                "类型": f"{type_info['icon']} {model['model_type']}",
                "文件名": model['filename'],
                "大小": format_file_size(model.get('size')),
                "状态": status,
                "检测来源": ", ".join(model.get('detection_sources', [])),
            })
        
        # Create DataFrame for better display
        import pandas as pd
        df = pd.DataFrame(table_data)
        
        log_msg = f"✅ [{datetime.now().strftime('%H:%M:%S')}] 分析完成: {result['total_models']} 个模型，{result['missing_models']} 个缺失"
        
        return gr.CheckboxGroup(choices=model_choices, value=model_values), workflow_info, log_msg, gr.DataFrame(df)
        
    except Exception as e:
        logger.error(f"Error analyzing workflows: {e}")
        return gr.CheckboxGroup(choices=[], value=[]), f"❌ 错误: {str(e)}", f"分析失败: {str(e)}", gr.DataFrame()


def create_interface():
    """Create the Gradio interface with optimized UI."""
    
    # Custom CSS for better styling
    custom_css = """
    .container {
        max-width: 1400px;
        margin: auto;
    }
    .model-checkbox {
        margin: 5px 0;
        padding: 8px;
        border-radius: 5px;
        transition: background-color 0.3s;
    }
    .model-checkbox:hover {
        background-color: #f0f0f0;
    }
    .status-ready { color: #4CAF50; }
    .status-missing { color: #F44336; }
    .status-partial { color: #FF9800; }
    """
    
    with gr.Blocks(title="ComfyUI Model Resolver v2.0", css=custom_css) as app:
        # Header
        gr.Markdown("# 🎨 ComfyUI Model Resolver v2.0")
        gr.Markdown("智能分析和下载 ComfyUI 工作流所需的模型")
        
        # Main tabs
        with gr.Tabs() as tabs:
            # Tab 1: Workflow Analysis
            with gr.Tab("🔍 工作流分析", elem_id="tab-workflow"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📁 选择工作流目录")
                        workflow_dir = gr.Textbox(
                            label="工作流目录",
                            value="/workspace/comfyui/user/default/workflows",
                            placeholder="输入包含工作流的目录路径"
                        )
                        refresh_btn = gr.Button("🔄 刷新列表", variant="primary")
                        
                        workflow_list = gr.CheckboxGroup(
                            label="选择工作流",
                            choices=[],
                            interactive=True
                        )
                        
                        analyze_btn = gr.Button("🔎 分析选中的工作流", variant="primary", size="lg")
                    
                    with gr.Column(scale=2):
                        workflow_info = gr.Markdown("请选择并分析工作流")
                        
                        with gr.Row():
                            select_all_btn = gr.Button("✅ 全选", size="sm")
                            select_none_btn = gr.Button("⬜ 全不选", size="sm")
                            select_missing_btn = gr.Button("❌ 仅选缺失", size="sm", variant="primary")
                        
                        model_list = gr.CheckboxGroup(
                            label="模型列表",
                            choices=[],
                            interactive=True
                        )
                        
                        # Add model table for better visualization
                        model_table = gr.DataFrame(
                            label="模型详情",
                            headers=["类型", "文件名", "大小", "状态", "检测来源"],
                            interactive=False
                        )
                        
                        with gr.Row():
                            search_btn = gr.Button("🔍 搜索选中的模型", variant="primary", size="lg")
                            export_btn = gr.Button("📥 导出下载脚本", size="lg")
            
            # Tab 2: Model Search
            with gr.Tab("🔎 模型搜索", elem_id="tab-search"):
                search_output = gr.Markdown("搜索结果将显示在这里")
                
                with gr.Row():
                    download_selected_btn = gr.Button("⬇️ 下载选中的模型", variant="primary")
                    download_all_btn = gr.Button("⬇️ 下载所有找到的模型")
            
            # Tab 3: Download Manager
            with gr.Tab("📥 下载管理", elem_id="tab-download"):
                with gr.Row():
                    refresh_status_btn = gr.Button("🔄 刷新状态", variant="primary")
                    clear_completed_btn = gr.Button("🗑️ 清理已完成")
                
                download_status = gr.Markdown("下载状态将显示在这里")
                
                # Download controls
                with gr.Row():
                    pause_all_btn = gr.Button("⏸️ 暂停所有")
                    resume_all_btn = gr.Button("▶️ 恢复所有")
                    cancel_all_btn = gr.Button("❌ 取消所有")
            
            # Tab 4: Batch Export
            with gr.Tab("📤 批量导出", elem_id="tab-export"):
                with gr.Row():
                    export_format = gr.Radio(
                        label="脚本格式",
                        choices=[
                            ("🐚 Bash (Linux/Mac)", "bash"),
                            ("💻 PowerShell (Windows)", "powershell"),
                            ("🐍 Python", "python")
                        ],
                        value="bash"
                    )
                    include_existing = gr.Checkbox(
                        label="包含已存在的模型",
                        value=False
                    )
                
                export_script_btn = gr.Button("🚀 生成下载脚本", variant="primary", size="lg")
                script_output = gr.Code(
                    label="导出的脚本",
                    language="bash",
                    interactive=True
                )
        
        # Status bar
        with gr.Row():
            status_log = gr.Textbox(
                label="状态日志",
                interactive=False,
                max_lines=3
            )
        
        # Event handlers
        refresh_btn.click(
            refresh_workflows,
            inputs=[workflow_dir],
            outputs=[workflow_list, status_log]
        )
        
        analyze_btn.click(
            analyze_selected_workflows,
            inputs=[workflow_list],
            outputs=[model_list, workflow_info, status_log, model_table]
        )
        
        # Model selection handlers
        select_all_btn.click(
            lambda choices: [filename for _, filename in choices],
            inputs=[model_list],
            outputs=[model_list]
        )
        
        select_none_btn.click(
            lambda: [],
            outputs=[model_list]
        )
        
        select_missing_btn.click(
            select_missing_models,
            inputs=[model_list],
            outputs=[model_list]
        )
        
        # Search handler
        search_btn.click(
            search_selected_models,
            inputs=[model_list],
            outputs=[search_output, status_log]
        ).then(
            lambda: gr.update(selected="tab-search"),
            outputs=[tabs]
        )
        
        # Download handlers
        refresh_status_btn.click(
            get_download_status,
            outputs=[download_status]
        )
        
        # Export handlers
        export_script_btn.click(
            export_workflow_script,
            inputs=[workflow_list, export_format],
            outputs=[script_output]
        )
    
    return app


def select_missing_models(current_choices):
    """Select only missing models."""
    missing = []
    for label, filename in current_choices:
        if filename in current_models and not current_models[filename]['exists_locally']:
            missing.append(filename)
    return missing


def search_selected_models(selected_models: List[str]) -> Tuple[str, str]:
    """Search for selected models with enhanced formatting."""
    if not selected_models:
        return "❌ 请选择要搜索的模型", ""
    
    try:
        # Search models
        result = api_client.search_models(selected_models)
        
        # Store results
        global search_results
        search_results = {r['filename']: r for r in result['results']}
        
        # Format results with better visualization
        output = f"# 🔍 搜索结果\n\n"
        output += f"| 指标 | 数值 |\n"
        output += f"|------|------|\n"
        output += f"| 🔢 搜索模型数 | {result['total_searched']} |\n"
        output += f"| ✅ 找到源数 | {result['total_found']} |\n"
        output += f"| ⏱️ 搜索耗时 | {result['search_time']:.2f}秒 |\n"
        output += f"| 🌐 使用平台 | {', '.join(result['platforms_used'])} |\n\n"
        
        # Format individual results
        for model_result in result['results']:
            type_info = MODEL_TYPE_INFO.get(
                current_models.get(model_result['filename'], {}).get('model_type', 'unknown'),
                MODEL_TYPE_INFO['unknown']
            )
            
            output += f"## {type_info['icon']} {model_result['filename']}\n\n"
            
            if model_result['sources']:
                output += "| 评分 | 平台 | 名称 | 大小 | 操作 |\n"
                output += "|------|------|------|------|------|\n"
                
                for source in model_result['sources']:
                    stars = "⭐" * source['rating']
                    size_str = format_file_size(source['size_bytes']) if source['size_bytes'] else "未知"
                    platform_icon = "🤗" if source['platform'] == "huggingface" else "🎨"
                    
                    output += f"| {stars} | {platform_icon} {source['platform']} | {source['name']} | {size_str} | "
                    output += f"[下载]({source['url']}) |\n"
            else:
                output += "❌ 未找到下载源\n"
            output += "\n---\n\n"
        
        log_msg = f"✅ [{datetime.now().strftime('%H:%M:%S')}] 搜索完成: {result['total_found']}/{result['total_searched']} 找到下载源"
        
        return output, log_msg
        
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        return f"❌ 搜索失败: {str(e)}", f"错误: {str(e)}"


def export_workflow_script(selected_workflows: List[str], script_format: str) -> str:
    """Export download script with enhanced formatting."""
    if not selected_workflows:
        return "❌ 请选择要导出的工作流"
    
    try:
        result = api_client.export_download_script(selected_workflows, script_format)
        
        # Format header with icons
        format_icons = {"bash": "🐚", "powershell": "💻", "python": "🐍"}
        icon = format_icons.get(script_format, "📄")
        
        header = f"{icon} 导出的下载脚本\n"
        header += f"# ========================================\n"
        header += f"# 📦 模型总数: {result['total_models']}\n"
        header += f"# 💾 预计大小: {result['total_size_gb']:.2f}GB\n"
        header += f"# 🔧 格式: {result['output_format']}\n"
        header += f"# 📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"# ========================================\n\n"
        
        return header + result['script_content']
        
    except Exception as e:
        logger.error(f"Error exporting script: {e}")
        return f"❌ 导出失败: {str(e)}"


def get_download_status() -> str:
    """Get current download status with enhanced formatting."""
    try:
        status = api_client.get_download_status()
        
        output = "# 📥 下载状态\n\n"
        
        # Queue info
        output += f"## 📊 队列信息\n"
        output += f"- 🔢 队列大小: {status['queue_size']}\n"
        output += f"- ⏳ 活动下载: {len(status.get('active', []))}\n"
        output += f"- ✅ 最近完成: {len(status.get('completed', []))}\n\n"
        
        # Active downloads
        if status.get('active'):
            output += "## ⏳ 正在下载\n\n"
            output += "| 文件名 | 进度 | 速度 | 剩余时间 | 操作 |\n"
            output += "|--------|------|------|----------|------|\n"
            
            for task in status['active']:
                progress = task.get('progress', 0)
                speed = format_file_size(task.get('speed_bytes_per_sec', 0)) + "/s"
                eta = task.get('eta_seconds', 0)
                eta_str = f"{eta//60}:{eta%60:02d}" if eta > 0 else "计算中..."
                
                output += f"| {task['filename'][:30]}... | {progress:.1f}% | {speed} | {eta_str} | "
                output += f"[暂停] [取消] |\n"
        
        # Completed downloads
        if status.get('completed'):
            output += "\n## ✅ 最近完成\n\n"
            for task in status['completed'][-5:]:  # Show last 5
                output += f"- ✅ {task['filename']} ({format_file_size(task.get('size_bytes', 0))})\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        return f"❌ 获取状态失败: {str(e)}"


# Main execution
if __name__ == "__main__":
    # Check API connection
    logger.info("Checking API connection...")
    try:
        response = api_client._run_sync(api_client._get_client().test_connection())
        logger.info("API connection successful")
    except Exception as e:
        logger.error(f"API connection failed: {e}")
        logger.warning("Some features may not work properly")
    
    # Create and launch interface
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 7861)),
        share=False,
        inbrowser=False
    )