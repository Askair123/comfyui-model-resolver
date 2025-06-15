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
SSH_KEY = "~/.ssh/id_rsa"

def run_ssh_command(command, description=""):
    """Execute command on remote server."""
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{POD_IP} -p {POD_SSH_PORT} -i {SSH_KEY}"
    full_cmd = f"{ssh_cmd} '{command}'"
    
    if description:
        print(f"\n{description}...")
    
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Success: {result.stdout}")
    return result

def apply_analyzer_fix():
    """Apply the model deduplication fix."""
    print("\n1. Applying analyzer fix...")
    
    # Create the improved analyzer file
    analyzer_content = """
from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3

class ImprovedAnalyzer(WorkflowAnalyzerV3):
    def analyze_workflow(self, workflow_path: str) -> dict:
        result = super().analyze_workflow(workflow_path)
        if 'models' in result:
            result['models'] = self._merge_duplicates_fixed(result['models'])
            result['total_models'] = len(result['models'])
            result['missing_models'] = sum(1 for m in result['models'] if not m.get('exists_locally', False))
        return result
    
    def _merge_duplicates_fixed(self, models: list) -> list:
        merged = {}
        for model in models:
            filename = model['filename']
            # Apply type rules
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
            
            if filename not in merged:
                merged[filename] = model
        return list(merged.values())
"""
    
    # Write the file
    run_ssh_command(
        f'cat > /workspace/api/services/improved_analyzer.py << "EOF"{analyzer_content}\nEOF',
        "Creating improved analyzer"
    )
    
    # Update workflow service to use it
    update_cmd = """
cd /workspace && python3 -c "
import re
content = open('api/services/workflow_service.py', 'r').read()
# Replace the import
content = re.sub(
    r'from src\.core\.workflow_analyzer_v3 import WorkflowAnalyzerV3',
    'from .improved_analyzer import ImprovedAnalyzer as WorkflowAnalyzerV3',
    content
)
open('api/services/workflow_service.py', 'w').write(content)
print('Updated workflow service')
"
"""
    run_ssh_command(update_cmd.strip(), "Updating workflow service")

def apply_search_fix():
    """Apply the search service fix for special model names."""
    print("\n2. Applying search fix...")
    
    search_fix = '''
def clean_model_name_for_search(filename: str) -> str:
    """Clean model name for better search results."""
    name = filename.lower()
    for suffix in ['.safetensors', '.ckpt', '.pth', '.onnx', '.gguf', '.bin']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    replacements = {
        'wan_2.1_vae': 'wan21 vae',
        'wan2.1-vace-14b': 'wan21 vace 14b',
        'umt5_xxl': 'umt5 xxl',
        'inswapper_128': 'inswapper 128',
        'gfpganv1.4': 'gfpgan v1.4',
        'wan21_causvid_14b_t2v_lora_rank32': 'wan21 causvid lora',
        '_': ' ',
        '-': ' ',
    }
    
    for old, new in replacements.items():
        if old in name:
            name = name.replace(old, new)
    
    name = ' '.join(name.split())
    return name.strip()
'''
    
    # Update search service
    update_cmd = f"""
cd /workspace && python3 -c "
import re
content = open('api/services/search_service.py', 'r').read()

# Add the function before the class
fix = '''{search_fix}
'''

# Find where to insert
class_pos = content.find('class SearchService:')
if class_pos > 0:
    # Insert the function before the class
    content = content[:class_pos] + fix + '\\n\\n' + content[class_pos:]
    
    # Update the search method to use it
    # Find search_models method
    method_start = content.find('async def search_models')
    if method_start > 0:
        # Find where model_name is used
        query_pos = content.find('query = model_name', method_start)
        if query_pos > 0:
            content = content[:query_pos] + 'query = clean_model_name_for_search(model_name)' + content[query_pos + len('query = model_name'):]
    
    open('api/services/search_service.py', 'w').write(content)
    print('Search service updated')
else:
    print('Could not update search service')
"
"""
    run_ssh_command(update_cmd.strip(), "Updating search service")

def apply_frontend_fix():
    """Apply the frontend fix to remove problematic button."""
    print("\n3. Applying frontend fix...")
    
    # Copy the fixed frontend file
    run_ssh_command(
        "cd /workspace && cp frontend/app_fixed.py frontend/app.py",
        "Copying fixed frontend"
    )

def restart_services():
    """Restart all services."""
    print("\n4. Restarting services...")
    
    # Kill existing processes
    run_ssh_command("pkill -f 'uvicorn|python app' || true", "Stopping services")
    
    # Wait a moment
    run_ssh_command("sleep 2", "Waiting")
    
    # Restart services
    run_ssh_command("cd /workspace && ./scripts/deploy-runpod.sh", "Starting services")

def main():
    print("Applying fixes to RunPod deployment...")
    print(f"Target: {POD_IP}:{POD_SSH_PORT}")
    
    # Apply all fixes
    apply_analyzer_fix()
    apply_search_fix()
    apply_frontend_fix()
    restart_services()
    
    print("\n✅ All fixes applied!")
    print("\nYou can now access:")
    print(f"- FastAPI: http://localhost:7860")
    print(f"- Gradio UI: http://localhost:7861")
    print("\nOr through SSH tunnel:")
    print(f"  ssh -L 7860:localhost:7860 -L 7861:localhost:7861 root@{POD_IP} -p {POD_SSH_PORT} -i {SSH_KEY}")

if __name__ == "__main__":
    main()