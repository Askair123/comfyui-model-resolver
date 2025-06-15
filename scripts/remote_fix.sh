#!/bin/bash
# Remote fix script to be run on the RunPod server

echo "Applying fixes to ComfyUI Model Resolver..."

# 1. Create improved analyzer
echo "1. Creating improved analyzer..."
cat > /workspace/api/services/improved_analyzer.py << 'EOF'
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
            # Apply type rules based on filename
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
EOF

# 2. Update workflow service
echo "2. Updating workflow service..."
cd /workspace
python3 -c "
import re
content = open('api/services/workflow_service.py', 'r').read()
content = re.sub(
    r'from src\.core\.workflow_analyzer_v3 import WorkflowAnalyzerV3',
    'from .improved_analyzer import ImprovedAnalyzer as WorkflowAnalyzerV3',
    content
)
open('api/services/workflow_service.py', 'w').write(content)
print('Workflow service updated')
"

# 3. Add search fix
echo "3. Adding search fix..."
python3 -c "
content = open('api/services/search_service.py', 'r').read()

# Add the clean function if not exists
if 'clean_model_name_for_search' not in content:
    fix = '''
def clean_model_name_for_search(filename: str) -> str:
    \"\"\"Clean model name for better search results.\"\"\"
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
    
    # Insert before class
    class_pos = content.find('class SearchService:')
    if class_pos > 0:
        content = content[:class_pos] + fix + content[class_pos:]
        
        # Update search method
        content = content.replace(
            'query = model_name',
            'query = clean_model_name_for_search(model_name)'
        )
        
        open('api/services/search_service.py', 'w').write(content)
        print('Search service updated')
"

# 4. Copy fixed frontend
echo "4. Fixing frontend..."
if [ -f /workspace/frontend/app_fixed.py ]; then
    cp /workspace/frontend/app_fixed.py /workspace/frontend/app.py
    echo "Frontend updated"
else
    echo "app_fixed.py not found, skipping frontend update"
fi

# 5. Restart services
echo "5. Restarting services..."
pkill -f 'uvicorn|python app' || true
sleep 2
cd /workspace && ./scripts/deploy-runpod.sh

echo "✅ All fixes applied!"