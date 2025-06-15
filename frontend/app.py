"""
ComfyUI Model Resolver v2.0 - Gradio Frontend
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
            
            label = f"{wf['name']} ━━━ {wf.get('missing_count', 0)}个缺失 {status_icon}"
            choices.append((label, wf['path']))
            
            # Store workflow data
            current_workflows[wf['path']] = wf
        
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 扫描完成: 找到 {len(workflows)} 个工作流"
        
        return gr.CheckboxGroup(choices=choices, value=[]), log_msg
        
    except Exception as e:
        logger.error(f"Error refreshing workflows: {e}")
        return gr.CheckboxGroup(choices=[], value=[]), f"错误: {str(e)}"


def select_all_workflows(current_choices):
    """Select all workflows."""
    return [choice[1] for choice in current_choices.choices]


def select_none_workflows():
    """Deselect all workflows."""
    return []


def analyze_selected_workflows(selected_paths: List[str]) -> Tuple[gr.CheckboxGroup, str, str]:
    """Analyze selected workflows."""
    if not selected_paths:
        return gr.CheckboxGroup(choices=[], value=[]), "请选择要分析的工作流", ""
    
    try:
        # Analyze workflows
        result = api_client.analyze_workflows(selected_paths)
        
        # Format workflow info
        workflow_info = f"### 分析结果\n\n"
        workflow_info += f"- 分析工作流数: {len(result['workflows'])}\n"
        workflow_info += f"- 总模型数: {result['total_models']}\n"
        workflow_info += f"- 缺失模型数: {result['missing_models']}\n"
        workflow_info += f"- 分析耗时: {result['analysis_time']:.2f}秒\n"
        
        # Format model list
        model_choices = []
        model_values = []
        
        for model in result['models']:
            # Format label
            status = "✓ 已存在" if model['exists_locally'] else "✗ 缺失"
            label = f"{model['filename']} ━━━ {model['model_type']} ━━━ {status}"
            
            model_choices.append((label, model['filename']))
            
            # Default selection: missing models
            if not model['exists_locally']:
                model_values.append(model['filename'])
            
            # Store model data
            current_models[model['filename']] = model
        
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 分析完成: {result['total_models']} 个模型，{result['missing_models']} 个缺失"
        
        return gr.CheckboxGroup(choices=model_choices, value=model_values), workflow_info, log_msg
        
    except Exception as e:
        logger.error(f"Error analyzing workflows: {e}")
        return gr.CheckboxGroup(choices=[], value=[]), f"错误: {str(e)}", f"分析失败: {str(e)}"


def search_selected_models(selected_models: List[str]) -> Tuple[str, str]:
    """Search for selected models."""
    if not selected_models:
        return "请选择要搜索的模型", ""
    
    try:
        # Search models
        result = api_client.search_models(selected_models)
        
        # Store results
        global search_results
        search_results = {r['filename']: r for r in result['results']}
        
        # Format results
        output = f"### 搜索结果\n\n"
        output += f"- 搜索模型数: {result['total_searched']}\n"
        output += f"- 找到源数: {result['total_found']}\n"
        output += f"- 搜索耗时: {result['search_time']:.2f}秒\n"
        output += f"- 使用平台: {', '.join(result['platforms_used'])}\n\n"
        
        # Format individual results
        for model_result in result['results']:
            output += f"#### {model_result['filename']}\n"
            if model_result['sources']:
                for source in model_result['sources']:
                    stars = "⭐" * source['rating']
                    output += f"- {stars} {source['platform']} - {source['name']}\n"
                    if source['size_bytes']:
                        size_mb = source['size_bytes'] / (1024 * 1024)
                        output += f"  大小: {size_mb:.1f}MB\n"
            else:
                output += "- 未找到下载源\n"
            output += "\n"
        
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 搜索完成: {result['total_found']}/{result['total_searched']} 找到下载源"
        
        # Switch to search results tab
        return output, log_msg
        
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        return f"搜索失败: {str(e)}", f"错误: {str(e)}"


def export_workflow_script(selected_workflows: List[str], script_format: str) -> str:
    """Export download script for workflows."""
    if not selected_workflows:
        return "请选择要导出的工作流"
    
    try:
        result = api_client.export_download_script(selected_workflows, script_format)
        
        # Format header
        header = f"# 导出的下载脚本\n"
        header += f"# 模型总数: {result['total_models']}\n"
        header += f"# 预计大小: {result['total_size_gb']:.2f}GB\n"
        header += f"# 格式: {result['output_format']}\n\n"
        
        return header + result['script_content']
        
    except Exception as e:
        logger.error(f"Error exporting script: {e}")
        return f"导出失败: {str(e)}"


def get_download_status() -> str:
    """Get current download status."""
    try:
        status = api_client.get_download_status()
        
        output = "### 下载状态\n\n"
        output += f"队列大小: {status['queue_size']}\n\n"
        
        if status['active_downloads']:
            output += "#### 当前下载:\n"
            for task in status['active_downloads']:
                output += f"- {task['filename']}\n"
                output += f"  进度: {task['progress']:.1f}% | "
                output += f"速度: {task['speed_mbps']:.1f} MB/s | "
                if task['eta_seconds']:
                    output += f"剩余: {task['eta_seconds']}秒\n"
                else:
                    output += "计算中...\n"
        
        if status['completed_recent']:
            output += "\n#### 最近完成:\n"
            for task in status['completed_recent'][-5:]:
                icon = "✓" if task['status'] == "completed" else "✗"
                output += f"{icon} {task['filename']}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        return f"获取状态失败: {str(e)}"


def create_interface():
    """Create Gradio interface."""
    with gr.Blocks(title="ComfyUI Model Resolver v2.0", theme=gr.themes.Soft()) as app:
        # Header
        gr.Markdown("# ComfyUI Model Resolver v2.0")
        gr.Markdown("智能分析和下载 ComfyUI 工作流所需的模型")
        
        # Main tabs
        with gr.Tabs() as main_tabs:
            # Tab 1: Workflow Analysis
            with gr.Tab("工作流分析"):
                with gr.Row():
                    directory_input = gr.Textbox(
                        value="/workspace/ComfyUI/workflows",
                        label="工作流目录",
                        scale=4
                    )
                    refresh_btn = gr.Button("🔄 刷新", scale=1)
                
                workflow_checklist = gr.CheckboxGroup(
                    label="选择工作流",
                    choices=[],
                    value=[]
                )
                
                with gr.Row():
                    select_all_btn = gr.Button("全选", size="sm")
                    select_none_btn = gr.Button("全不选", size="sm")
                    analyze_btn = gr.Button("分析选中的工作流", variant="primary")
                    export_script_btn = gr.Button("导出批量下载脚本")
                
                gr.Markdown("---")
                
                workflow_info = gr.Markdown("请选择工作流查看详情")
                
                model_checklist = gr.CheckboxGroup(
                    label="模型列表",
                    choices=[],
                    value=[]
                )
                
                with gr.Row():
                    search_btn = gr.Button("搜索选中的模型", variant="primary")
                    export_model_script_btn = gr.Button("导出下载脚本")
                
                with gr.Row():
                    script_format = gr.Radio(
                        choices=["bash", "powershell", "python"],
                        value="bash",
                        label="脚本格式"
                    )
                
                log_output = gr.Textbox(
                    label="操作日志",
                    lines=5,
                    max_lines=10,
                    autoscroll=True
                )
            
            # Tab 2: Search Results
            with gr.Tab("搜索结果"):
                search_output = gr.Markdown("搜索结果将显示在这里")
                
                with gr.Row():
                    download_selected_btn = gr.Button("下载选中的模型", variant="primary")
                    back_to_workflow_btn = gr.Button("返回工作流分析")
            
            # Tab 3: Download Management
            with gr.Tab("下载管理"):
                download_status = gr.Markdown("下载状态")
                
                with gr.Row():
                    refresh_status_btn = gr.Button("🔄 刷新状态")
                    pause_all_btn = gr.Button("暂停全部")
                    clear_queue_btn = gr.Button("清空队列", variant="stop")
                
                # Auto-refresh
                status_timer = gr.Timer(1.0)
            
            # Tab 4: Settings
            with gr.Tab("设置"):
                gr.Markdown("### API 配置")
                civitai_key_input = gr.Textbox(
                    label="Civitai API Key",
                    type="password",
                    placeholder="输入你的 Civitai API Key"
                )
                hf_token_input = gr.Textbox(
                    label="HuggingFace Token",
                    type="password",
                    placeholder="输入你的 HuggingFace Token (可选)"
                )
                
                gr.Markdown("### 路径配置")
                comfyui_root_input = gr.Textbox(
                    label="ComfyUI 根目录",
                    value="/workspace/ComfyUI"
                )
                
                gr.Markdown("### 下载选项")
                auto_skip_checkbox = gr.Checkbox(
                    label="自动跳过已存在的文件",
                    value=True
                )
                verify_checkbox = gr.Checkbox(
                    label="下载完成后验证文件完整性",
                    value=False
                )
                
                save_config_btn = gr.Button("保存设置", variant="primary")
                config_status = gr.Markdown("")
        
        # Event handlers
        refresh_btn.click(
            fn=refresh_workflows,
            inputs=[directory_input],
            outputs=[workflow_checklist, log_output]
        )
        
        select_all_btn.click(
            fn=select_all_workflows,
            inputs=[workflow_checklist],
            outputs=[workflow_checklist]
        )
        
        select_none_btn.click(
            fn=select_none_workflows,
            outputs=[workflow_checklist]
        )
        
        analyze_btn.click(
            fn=analyze_selected_workflows,
            inputs=[workflow_checklist],
            outputs=[model_checklist, workflow_info, log_output]
        )
        
        search_btn.click(
            fn=search_selected_models,
            inputs=[model_checklist],
            outputs=[search_output, log_output]
        ).then(
            lambda: gr.Tabs(selected=1),
            outputs=[main_tabs]
        )
        
        export_script_btn.click(
            fn=export_workflow_script,
            inputs=[workflow_checklist, script_format],
            outputs=[log_output]
        )
        
        export_model_script_btn.click(
            fn=lambda models, fmt: export_workflow_script(
                list(current_workflows.keys()), fmt
            ),
            inputs=[model_checklist, script_format],
            outputs=[log_output]
        )
        
        back_to_workflow_btn.click(
            lambda: gr.Tabs(selected=0),
            outputs=[main_tabs]
        )
        
        refresh_status_btn.click(
            fn=get_download_status,
            outputs=[download_status]
        )
        
        # Auto-refresh download status
        status_timer.tick(
            fn=get_download_status,
            outputs=[download_status]
        )
        
        # Settings handlers
        def save_config(civitai_key, hf_token, comfyui_root, auto_skip, verify):
            try:
                config = {}
                if civitai_key:
                    config['civitai_api_key'] = civitai_key
                if hf_token:
                    config['huggingface_token'] = hf_token
                if comfyui_root:
                    config['comfyui_root'] = comfyui_root
                config['auto_skip_existing'] = auto_skip
                config['verify_downloads'] = verify
                
                result = api_client.update_config(config)
                return "✓ 设置已保存"
            except Exception as e:
                return f"✗ 保存失败: {str(e)}"
        
        save_config_btn.click(
            fn=save_config,
            inputs=[
                civitai_key_input,
                hf_token_input,
                comfyui_root_input,
                auto_skip_checkbox,
                verify_checkbox
            ],
            outputs=[config_status]
        )
        
        # Load initial config
        def load_config():
            try:
                config = api_client.get_config()
                return (
                    config.get('civitai_api_key', ''),
                    config.get('huggingface_token', ''),
                    config.get('comfyui_root', '/workspace/ComfyUI'),
                    config.get('auto_skip_existing', True),
                    config.get('verify_downloads', False)
                )
            except:
                return '', '', '/workspace/ComfyUI', True, False
        
        app.load(
            fn=load_config,
            outputs=[
                civitai_key_input,
                hf_token_input,
                comfyui_root_input,
                auto_skip_checkbox,
                verify_checkbox
            ]
        )
    
    return app


if __name__ == "__main__":
    # Check API connection
    logger.info("Checking API connection...")
    if not api_client.health_check():
        logger.error("Cannot connect to API. Please ensure the backend is running.")
        logger.error("Run './start.sh' or 'uvicorn api.main:app' first.")
        exit(1)
    
    logger.info("API connection successful")
    
    # Create and launch interface
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 5001)),
        share=False,
        inbrowser=True
    )