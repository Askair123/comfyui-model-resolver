#!/usr/bin/env python3
"""
Apply fixes to the ComfyUI Model Resolver deployment
"""

import os
import sys

# Fix 1: Update workflow analyzer to prevent duplicates
analyzer_fix = '''
# Add this to api/services/workflow_service.py after the WorkflowAnalyzerV3 import

class ImprovedAnalyzer:
    """Wrapper to fix analyzer issues."""
    
    def __init__(self):
        self.analyzer = WorkflowAnalyzerV3()
    
    def analyze_workflow(self, workflow_path: str) -> dict:
        result = self.analyzer.analyze_workflow(workflow_path)
        
        # Fix duplicate models
        if 'models' in result:
            seen = {}
            fixed_models = []
            
            for model in result['models']:
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
                if filename not in seen:
                    seen[filename] = True
                    fixed_models.append(model)
            
            result['models'] = fixed_models
            result['total_models'] = len(fixed_models)
        
        return result
'''

# Fix 2: Update search service to handle special model names
search_fix = '''
def clean_model_name(filename: str) -> str:
    """Clean model name for better search results."""
    # Remove common suffixes
    name = filename.lower()
    for suffix in ['.safetensors', '.ckpt', '.pth', '.onnx', '.gguf', '.bin']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Handle special cases
    replacements = {
        'wan_2.1_vae': 'wan21 vae',
        'wan2.1-vace-14b': 'wan21 vace 14b',
        'umt5_xxl': 'umt5 xxl',
        'inswapper_128': 'inswapper 128',
        'gfpganv1.4': 'gfpgan v1.4',
        'wan21_causvid_14b_t2v_lora_rank32': 'wan21 causvid lora'
    }
    
    for old, new in replacements.items():
        if old in name:
            name = name.replace(old, new)
    
    return name.strip()
'''

# Fix 3: Remove problematic button from frontend
frontend_fix = '''
# In frontend/app.py, remove the select_missing_btn and its handler
# Just keep select_all_btn and select_none_btn
'''

print("Fixes to apply:")
print("1. Analyzer deduplication fix")
print("2. Search service model name cleaning")
print("3. Remove 'select missing' button from frontend")
print("\nThese fixes need to be applied manually to the running services.")