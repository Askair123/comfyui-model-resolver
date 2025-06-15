#!/usr/bin/env python3
"""
Fix frontend issues for RunPod deployment
"""

# Fix 1: Update api_client.py to fix the _run_sync issue
api_client_fix = '''"""
API Client for ComfyUI Model Resolver
"""

import httpx
import asyncio
from typing import Dict, List, Any, Optional
import os

class SyncAPIClient:
    """Synchronous API client for the backend."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("API_URL", "http://localhost:7860")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
    
    def _get_client(self):
        """Get the HTTP client."""
        return self.client
    
    def test_connection(self) -> dict:
        """Test API connection."""
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API connection failed: {e}")
    
    def list_workflows(self, directory: str) -> List[Dict]:
        """List workflows in a directory."""
        response = self.client.post("/api/workflows/list", json={"directory": directory})
        response.raise_for_status()
        return response.json()["workflows"]
    
    def analyze_workflows(self, workflow_paths: List[str]) -> Dict:
        """Analyze multiple workflows."""
        response = self.client.post("/api/workflows/analyze", json={"workflow_paths": workflow_paths})
        response.raise_for_status()
        return response.json()
    
    def search_models(self, model_names: List[str]) -> Dict:
        """Search for models."""
        response = self.client.post("/api/models/search", json={"model_names": model_names})
        response.raise_for_status()
        return response.json()
    
    def export_download_script(self, workflow_paths: List[str], output_format: str) -> Dict:
        """Export download script."""
        response = self.client.post(
            "/api/export/script",
            json={"workflow_paths": workflow_paths, "output_format": output_format}
        )
        response.raise_for_status()
        return response.json()
    
    def get_download_status(self) -> Dict:
        """Get download status."""
        response = self.client.get("/api/downloads/status")
        response.raise_for_status()
        return response.json()
'''

# Fix 2: Create a simpler working frontend
simple_frontend = '''"""
ComfyUI Model Resolver v2.0 - Simple Working Frontend
"""

import gradio as gr
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:7860")

# Global state
current_workflows = {}
current_models = {}

def call_api(endpoint: str, method: str = "GET", json_data: dict = None):
    """Make API call."""
    url = f"{API_URL}{endpoint}"
    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=json_data)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise

def refresh_workflows(directory: str) -> Tuple[gr.CheckboxGroup, str]:
    """Refresh workflow list from directory."""
    try:
        # Use default directory if empty
        if not directory:
            directory = "/workspace/comfyui/user/default/workflows"
            
        result = call_api("/api/workflows/list", "POST", {"directory": directory})
        workflows = result.get("workflows", [])
        
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
        result = call_api("/api/workflows/analyze", "POST", {"workflow_paths": selected_paths})
        
        # Clear previous state
        current_models.clear()
        
        # Format workflow info
        workflow_info = f"### 分析结果\\n\\n"
        workflow_info += f"- 分析工作流数: {len(result['workflows'])}\\n"
        workflow_info += f"- 总模型数: {result['total_models']}\\n"
        workflow_info += f"- 缺失模型数: {result['missing_models']}\\n"
        workflow_info += f"- 分析耗时: {result['analysis_time']:.2f}秒\\n"
        
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
        result = call_api("/api/models/search", "POST", {"model_names": selected_models})
        
        # Format results
        output = f"### 搜索结果\\n\\n"
        output += f"- 搜索模型数: {result['total_searched']}\\n"
        output += f"- 找到源数: {result['total_found']}\\n"
        output += f"- 搜索耗时: {result['search_time']:.2f}秒\\n"
        output += f"- 使用平台: {', '.join(result['platforms_used'])}\\n\\n"
        
        # Format individual results
        for model_result in result['results']:
            output += f"#### {model_result['filename']}\\n"
            if model_result['sources']:
                for source in model_result['sources']:
                    stars = "⭐" * source['rating']
                    output += f"- {stars} {source['platform']} - {source['name']}\\n"
                    if source['size_bytes']:
                        size_mb = source['size_bytes'] / (1024 * 1024)
                        output += f"  大小: {size_mb:.1f}MB\\n"
            else:
                output += "- 未找到下载源\\n"
            output += "\\n"
        
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] 搜索完成: {result['total_found']}/{result['total_searched']} 找到下载源"
        
        return output, log_msg
        
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        return f"搜索失败: {str(e)}", f"错误: {str(e)}"

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="ComfyUI Model Resolver v2.0") as app:
        gr.Markdown("# ComfyUI Model Resolver v2.0")
        gr.Markdown("智能分析和下载 ComfyUI 工作流所需的模型")
        
        with gr.Tabs():
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
                
                gr.Markdown("---")
                
                workflow_info = gr.Markdown("请选择工作流查看详情")
                
                model_checklist = gr.CheckboxGroup(
                    label="模型列表",
                    choices=[],
                    value=[]
                )
                
                with gr.Row():
                    search_btn = gr.Button("搜索选中的模型", variant="primary")
                
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
                    back_to_workflow_btn = gr.Button("返回工作流分析")
        
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
        result = call_api("/health")
        logger.info(f"API connection successful: {result}")
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
'''

print("Fixes to apply:")
print("1. Fix api_client.py to remove _run_sync issue")
print("2. Create simple working frontend")
print("\nSave these as:")
print("- /workspace/api_client_fixed.py")
print("- /workspace/frontend/app_simple.py")

# Output the fixes
with open("/tmp/api_client_fixed.py", "w") as f:
    f.write(api_client_fix)

with open("/tmp/app_simple.py", "w") as f:
    f.write(simple_frontend)

print("\nFiles created in /tmp/")
print("Copy them to the server and run:")
print("cp /tmp/api_client_fixed.py /workspace/frontend/api_client.py")
print("cp /tmp/app_simple.py /workspace/frontend/app_simple.py")
print("cd /workspace && GRADIO_SERVER_PORT=7861 python frontend/app_simple.py")