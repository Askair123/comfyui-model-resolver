#!/usr/bin/env python3
"""
Fix for workflow analyzer duplicate detection issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3


class FixedWorkflowAnalyzerV3(WorkflowAnalyzerV3):
    """Fixed version with better deduplication and type inference."""
    
    def _merge_duplicates(self, models: list) -> list:
        """Merge duplicate models with improved type inference."""
        merged = {}
        
        for model in models:
            filename = model['filename']
            
            if filename not in merged:
                merged[filename] = model
            else:
                # Keep the most specific type
                existing = merged[filename]
                
                # Priority order for model types
                type_priority = {
                    'checkpoint': 0,
                    'lora': 1,
                    'vae': 2,
                    'clip': 3,
                    'unet': 4,
                    'controlnet': 5,
                    'reactor': 6,
                    'upscale': 7,
                    'unknown': 99
                }
                
                # Special rules for filename patterns
                if 'vae' in filename.lower():
                    model['model_type'] = 'vae'
                elif 'lora' in filename.lower() or 'rank' in filename.lower():
                    model['model_type'] = 'lora'
                elif filename.endswith('.gguf'):
                    # GGUF files are usually unet models
                    if 'encoder' in filename.lower() or 'clip' in filename.lower() or 'umt5' in filename.lower():
                        model['model_type'] = 'clip'
                    else:
                        model['model_type'] = 'unet'
                elif filename.endswith('.onnx'):
                    model['model_type'] = 'reactor'
                elif filename.endswith('.pth') and 'GFPGAN' in filename:
                    model['model_type'] = 'reactor'
                
                # Compare priorities
                current_priority = type_priority.get(model['model_type'], 99)
                existing_priority = type_priority.get(existing['model_type'], 99)
                
                if current_priority < existing_priority:
                    # Update with more specific type
                    existing['model_type'] = model['model_type']
                
                # Merge detection sources
                existing_sources = set(existing.get('detection_sources', []))
                new_sources = set(model.get('detection_sources', []))
                existing['detection_sources'] = list(existing_sources | new_sources)
                
                # Merge node types
                existing_nodes = set(existing.get('node_types', []))
                new_nodes = set(model.get('node_types', []))
                existing['node_types'] = list(existing_nodes | new_nodes)
        
        return list(merged.values())

    def analyze_workflow(self, workflow_path: str) -> dict:
        """Analyze workflow with fixed deduplication."""
        result = super().analyze_workflow(workflow_path)
        
        # Apply fixed deduplication
        if 'models' in result:
            result['models'] = self._merge_duplicates(result['models'])
            result['total_models'] = len(result['models'])
        
        return result


def test_fix():
    """Test the fix with a workflow."""
    analyzer = FixedWorkflowAnalyzerV3()
    
    # Test with the problematic workflow
    workflow_path = "/workspace/comfyui/user/default/workflows/vace-xclbr-v2.json"
    
    if os.path.exists(workflow_path):
        print(f"Analyzing {workflow_path}...")
        result = analyzer.analyze_workflow(workflow_path)
        
        print(f"\nTotal models: {result['total_models']}")
        print("\nModels found:")
        for model in result['models']:
            print(f"  - {model['filename']} → {model['model_type']}")
    else:
        print(f"Workflow not found: {workflow_path}")


if __name__ == "__main__":
    test_fix()