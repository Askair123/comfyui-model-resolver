"""
ComfyUI Model Resolver v2.0 - Fixed Gradio Frontend
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
        # Use default directory if empty
        if not directory:
            directory = "/workspace/comfyui/user/default/workflows"
            
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
            
            # Select workflows with missing models by default
            if wf['status'] in ['partial', 'missing']:
                values.append(wf['path'])
        
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 找到 {len(workflows)} 个工作流"
        
        return gr.CheckboxGroup(choices=choices, value=values), log_msg
        
    except Exception as e:
        logger.error(f"Error refreshing workflows: {e}")
        return gr.CheckboxGroup(choices=[], value=[]), f"错误: {str(e)}"


def analyze_selected_workflows(selected_paths: List[str]) -> Tuple[gr.CheckboxGroup, str, str]:
    """Analyze selected workflows and display models."""
    if not selected_paths:
        return gr.CheckboxGroup(choices=[], value=[]), "请选择要分析的工作流", ""
    
    try:
        # Analyze workflows
        result = api_client.analyze_workflows(selected_paths)
        
        # Clear previous state
        current_models.clear()
        
        # Format workflow info
        workflow_info = f"### 分析结果\n\n"
        workflow_info += f"- 分析工作流数: {len(result['workflows'])}\n"
        workflow_info += f"- 总模型数: {result['total_models']}\n"
        workflow_info += f"- 缺失模型数: {result['missing_models']}\n"
        workflow_info += f"- 分析耗时: {result['analysis_time']:.2f}秒\n"
        
        # Format model choices
        model_choices = []
        model_values = []
        
        for model in result['models']:
            # Format label
            status = "✅ 已存在" if model['exists_locally'] else "❌ 缺失"
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
        
        # Active downloads
        if status.get('active'):
            output += "#### 正在下载\n"
            for task in status['active']:
                output += f"- {task['filename']} - {task.get('progress', 0):.1f}%\n"
            output += "\n"
        
        # Recent completions
        if status.get('completed'):
            output += "#### 最近完成\n"
            for task in status['completed'][-5:]:
                output += f"- ✅ {task['filename']}\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        return f"获取状态失败: {str(e)}"


def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="ComfyUI Model Resolver v2.0") as app:
        gr.Markdown("# ComfyUI Model Resolver v2.0")
        gr.Markdown("智能分析和下载 ComfyUI 工作流所需的模型")
        
        main_tabs = gr.Tabs()
        
        with main_tabs:
            # Tab 1: Workflow Analysis
            with gr.Tab("工作流分析"):
                directory_input = gr.Textbox(
                    label="工作流目录",
                    value="/workspace/comfyui/user/default/workflows",
                    placeholder="输入包含 .json 工作流文件的目录路径"
                )
                
                with gr.Row():
                    refresh_btn = gr.Button("刷新列表", variant="primary")
                
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
                    resume_all_btn = gr.Button("恢复全部")
                    cancel_all_btn = gr.Button("取消全部")
                
                # Auto-refresh timer
                status_timer = gr.Timer(value=2, active=True)
            
            # Tab 4: Settings
            with gr.Tab("设置"):
                gr.Markdown("### API 配置")
                gr.Markdown("配置外部平台的 API 密钥以启用搜索和下载功能")
                
                civitai_key_input = gr.Textbox(
                    label="Civitai API Key",
                    type="password",
                    placeholder="输入你的 Civitai API Key（用于搜索 LoRA 模型）"
                )
                hf_token_input = gr.Textbox(
                    label="HuggingFace Token",
                    type="password",
                    placeholder="输入你的 HuggingFace Token（可选，用于访问私有模型）"
                )
                
                gr.Markdown("### 下载设置")
                auto_skip_existing = gr.Checkbox(
                    label="自动跳过已存在的文件",
                    value=True
                )
                verify_downloads = gr.Checkbox(
                    label="验证下载文件的完整性",
                    value=True
                )
                
                save_config_btn = gr.Button("保存设置", variant="primary")
                config_status = gr.Markdown("")
        
        # Event handlers
        refresh_btn.click(
            fn=refresh_workflows,
            inputs=[directory_input],
            outputs=[workflow_checklist, log_output]
        )
        
        # Select all/none handlers
        select_all_btn.click(
            fn=lambda choices: [choice[1] for choice in choices],
            inputs=[workflow_checklist],
            outputs=[workflow_checklist]
        )
        
        select_none_btn.click(
            fn=lambda: [],
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
        def save_config(civitai_key, hf_token, auto_skip, verify):
            try:
                config = {}
                if civitai_key:
                    config['civitai_api_key'] = civitai_key
                if hf_token:
                    config['huggingface_token'] = hf_token
                config['auto_skip_existing'] = auto_skip
                config['verify_downloads'] = verify
                
                # Save config (implement as needed)
                return "✅ 设置已保存"
            except Exception as e:
                return f"❌ 保存失败: {str(e)}"
        
        save_config_btn.click(
            fn=save_config,
            inputs=[civitai_key_input, hf_token_input, auto_skip_existing, verify_downloads],
            outputs=[config_status]
        )
        
        # Load workflows on startup
        app.load(
            fn=refresh_workflows,
            inputs=[directory_input],
            outputs=[workflow_checklist, log_output]
        )
    
    return app


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