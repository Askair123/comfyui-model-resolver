#!/usr/bin/env python3
"""
Apply all fixes to the ComfyUI Model Resolver deployment on RunPod
"""

import subprocess
import sys
import os

# RunPod Pod details
POD_IP = "69.30.85.192"
POD_SSH_PORT = 15718

# Fix 1: Update workflow service with improved analyzer
analyzer_fix_content = '''
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3

class ImprovedAnalyzer(WorkflowAnalyzerV3):
    """Fixed version with better deduplication and type inference."""
    
    def analyze_workflow(self, workflow_path: str) -> dict:
        """Analyze workflow with fixed deduplication."""
        result = super().analyze_workflow(workflow_path)
        
        # Apply fixed deduplication
        if 'models' in result:
            result['models'] = self._merge_duplicates_fixed(result['models'])
            result['total_models'] = len(result['models'])
            result['missing_models'] = sum(1 for m in result['models'] if not m.get('exists_locally', False))
        
        return result
    
    def _merge_duplicates_fixed(self, models: list) -> list:
        """Merge duplicate models with improved type inference."""
        merged = {}
        
        for model in models:
            filename = model['filename']
            
            # Apply type rules based on filename patterns
            if 'vae' in filename.lower():
                model['model_type'] = 'vae'
            elif 'lora' in filename.lower() or 'rank' in filename.lower():
                model['model_type'] = 'lora'
            elif filename.endswith('.gguf'):
                if 'encoder' in filename.lower() or 'umt5' in filename.lower():
                    model['model_type'] = 'clip'
                else:
                    model['model_type'] = 'unet'
            elif filename.endswith('.onnx'):
                model['model_type'] = 'reactor'
            elif filename.endswith('.pth') and 'gfpgan' in filename.lower():
                model['model_type'] = 'reactor'
            
            # Only keep first occurrence
            if filename not in merged:
                merged[filename] = model
            else:
                # Keep the most specific type
                existing = merged[filename]
                type_priority = {
                    'vae': 0, 'lora': 1, 'clip': 2, 'unet': 3,
                    'reactor': 4, 'checkpoint': 5, 'unknown': 99
                }
                
                if type_priority.get(model['model_type'], 99) < type_priority.get(existing['model_type'], 99):
                    existing['model_type'] = model['model_type']
        
        return list(merged.values())

# Replace the analyzer in workflow_service
analyzer = ImprovedAnalyzer()
'''

# Fix 2: Update search service to handle special model names
search_fix_content = '''
def clean_model_name_for_search(filename: str) -> str:
    """Clean model name for better search results."""
    # Remove common suffixes
    name = filename.lower()
    for suffix in ['.safetensors', '.ckpt', '.pth', '.onnx', '.gguf', '.bin']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Handle special cases that cause search issues
    replacements = {
        'wan_2.1_vae': 'wan21 vae',
        'wan2.1-vace-14b': 'wan21 vace 14b',
        'umt5_xxl': 'umt5 xxl',
        'inswapper_128': 'inswapper 128',
        'gfpganv1.4': 'gfpgan v1.4',
        'wan21_causvid_14b_t2v_lora_rank32': 'wan21 causvid lora',
        '_': ' ',  # Replace underscores with spaces
        '-': ' ',  # Replace hyphens with spaces
    }
    
    for old, new in replacements.items():
        if old in name:
            name = name.replace(old, new)
    
    # Clean up multiple spaces
    name = ' '.join(name.split())
    
    return name.strip()
'''

# Fix 3: Frontend fix - Remove problematic button and fix default directory
frontend_fix_content = '''#!/usr/bin/env python3
"""
Fixed frontend without problematic button
"""

import gradio as gr
import asyncio
import json
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import logging

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
        # Return empty choices but keep default directory visible
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
        result = api_client.search_models(selected_models)
        
        # Store results
        global search_results
        search_results = {r['filename']: r for r in result['results']}
        
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
            
            # Tab 3: Settings
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
        
        back_to_workflow_btn.click(
            lambda: gr.Tabs(selected=0),
            outputs=[main_tabs]
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
'''

def main():
    print("Applying fixes to RunPod deployment...")
    
    # SSH connection command
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{POD_IP} -p {POD_SSH_PORT} -i ~/.ssh/id_rsa"
    
    # Fix 1: Create improved analyzer
    print("\n1. Creating improved analyzer...")
    analyzer_file = "/workspace/api/services/improved_analyzer.py"
    cmd = f"{ssh_cmd} 'cat > {analyzer_file} << \"EOF\"\n{analyzer_fix_content}\nEOF'"
    subprocess.run(cmd, shell=True)
    
    # Fix 2: Update workflow service to use improved analyzer
    print("\n2. Updating workflow service...")
    cmd = f"{ssh_cmd} 'cd /workspace && python -c \"" \
          "import sys; " \
          "content = open(\\'api/services/workflow_service.py\\', \\'r\\').read(); " \
          "if \\'from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3\\' in content: " \
          "  content = content.replace(" \
          "    \\'from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3\\', " \
          "    \\'from .improved_analyzer import ImprovedAnalyzer as WorkflowAnalyzerV3\\'" \
          "  ); " \
          "  open(\\'api/services/workflow_service.py\\', \\'w\\').write(content); " \
          "  print(\\'Workflow service updated\\');" \
          "else: print(\\'Pattern not found\\');" \
          "\"'"
    subprocess.run(cmd, shell=True)
    
    # Fix 3: Update search service
    print("\n3. Updating search service...")
    search_update = f'''cd /workspace && python -c "
content = open('api/services/search_service.py', 'r').read()

# Add the clean_model_name_for_search function
fix = '''
{search_fix_content}
'''

# Insert after imports
import_end = content.find('class SearchService:')
if import_end > 0:
    content = content[:import_end] + fix + '\\n\\n' + content[import_end:]
    
    # Update search_models method to use the new function
    content = content.replace(
        'query = model_name',
        'query = clean_model_name_for_search(model_name)'
    )
    
    open('api/services/search_service.py', 'w').write(content)
    print('Search service updated')
else:
    print('Could not find insertion point')
"'''
    
    cmd = f"{ssh_cmd} '{search_update}'"
    subprocess.run(cmd, shell=True)
    
    # Fix 4: Replace frontend with fixed version
    print("\n4. Replacing frontend...")
    frontend_file = "/workspace/frontend/app.py"
    cmd = f"{ssh_cmd} 'cat > {frontend_file} << \"EOF\"\n{frontend_fix_content}\nEOF'"
    subprocess.run(cmd, shell=True)
    
    # Fix 5: Restart services
    print("\n5. Restarting services...")
    restart_cmd = f"{ssh_cmd} 'cd /workspace && " \
                  "pkill -f \"uvicorn|python app\" || true; " \
                  "sleep 2; " \
                  "./scripts/deploy-runpod.sh'"
    subprocess.run(restart_cmd, shell=True)
    
    print("\n✅ All fixes applied!")
    print("\nYou can now access:")
    print(f"- FastAPI: http://localhost:7860")
    print(f"- Gradio UI: http://localhost:7861")
    print("\nOr through SSH tunnel:")
    print(f"  ssh -L 7860:localhost:7860 -L 7861:localhost:7861 root@{POD_IP} -p {POD_SSH_PORT} -i ~/.ssh/id_rsa")

if __name__ == "__main__":
    main()