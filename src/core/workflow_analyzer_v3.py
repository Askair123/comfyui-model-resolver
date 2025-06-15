"""
Fixed Workflow Analyzer that properly handles markdown notes
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import logging

class WorkflowAnalyzerV3:
    """Fixed workflow analyzer that correctly ignores markdown documentation nodes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model file extensions
        self.model_extensions = {
            '.safetensors', '.ckpt', '.pt', '.pth', '.bin', 
            '.gguf', '.onnx', '.pb', '.h5', '.pkl', '.model'
        }
        
        # Node type to model type mappings
        self.node_mappings = {
            'CheckpointLoaderSimple': 'checkpoint',
            'LoraLoader': 'lora',
            'VAELoader': 'vae',
            'ControlNetLoader': 'controlnet',
            'CLIPLoader': 'clip',
            'UNETLoader': 'unet',
            'LoaderGGUF': 'unet',
            'ClipLoaderGGUF': 'clip',
            'Power Lora Loader (rgthree)': 'lora',
            'UpscaleModelLoader': 'upscale',
            'AnimateDiffModuleLoader': 'animatediff',
            'IPAdapterModelLoader': 'ipadapter',
            'InstantIDModelLoader': 'instantid',
        }
        
        # Model type indicators for inference
        self.type_indicators = {
            'checkpoint': ['ckpt', 'checkpoint', 'model', 'dreambooth'],
            'lora': ['lora', 'locon', 'lycoris'],
            'vae': ['vae', 'variational'],
            'controlnet': ['controlnet', 'control', 'cnet'],
            'upscale': ['upscale', 'esrgan', 'realesrgan', '2x', '4x'],
            'embeddings': ['embedding', 'embed', 'textual_inversion'],
            'clip': ['clip', 'text_encoder', 't5', 'umt5'],
            'unet': ['unet', 'diffusion', 'denoiser', 'vace'],
        }
        
    def analyze_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """Analyze workflow and extract unique models."""
        with open(workflow_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract models from actual loader nodes only
        models = []
        seen_models: Set[Tuple[str, str]] = set()
        
        nodes = data.get('nodes', [])
        for node in nodes:
            # Skip documentation nodes
            if node.get('type') in ['Note', 'MarkdownNote', 'PrimitiveNode']:
                continue
                
            # Only process known model loader nodes
            if node.get('type') not in self.node_mappings:
                continue
                
            # Extract models from this loader node
            node_models = self._extract_models_from_loader(node)
            for model in node_models:
                key = (model['filename'], model['model_type'])
                if key not in seen_models:
                    seen_models.add(key)
                    models.append(model)
        
        return {
            'workflow_file': workflow_path,
            'total_nodes': len(nodes),
            'model_count': len(models),
            'models': models
        }
    
    def _extract_models_from_loader(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract models from a model loader node."""
        models = []
        node_type = node.get('type', '')
        model_type = self.node_mappings.get(node_type, 'unknown')
        
        # Get widgets values
        widgets = node.get('widgets_values', [])
        
        # Special handling for Power Lora Loader
        if node_type == 'Power Lora Loader (rgthree)':
            for widget in widgets:
                if isinstance(widget, dict) and 'lora' in widget:
                    filename = widget.get('lora')
                    if filename and self._is_model_file(filename):
                        models.append({
                            'filename': filename,
                            'model_type': model_type,
                            'node_type': node_type,
                            'node_id': node.get('id', 'unknown')
                        })
        else:
            # For standard loaders, look for model filenames in widgets
            for widget in widgets:
                if isinstance(widget, str) and self._is_model_file(widget):
                    models.append({
                        'filename': widget,
                        'model_type': model_type,
                        'node_type': node_type,
                        'node_id': node.get('id', 'unknown')
                    })
        
        return models
    
    def _is_model_file(self, text: str) -> bool:
        """Check if text is a model filename."""
        if not text or not isinstance(text, str):
            return False
        
        # Must end with a model extension
        text_lower = text.lower()
        return any(text_lower.endswith(ext) for ext in self.model_extensions)


# Test function
if __name__ == "__main__":
    analyzer = WorkflowAnalyzerV3()
    result = analyzer.analyze_workflow('/workspace/comfyui/user/default/workflows/vace-xclbr-v2.json')
    
    print(f'Total models detected: {result["model_count"]}')
    print('\nModels found:')
    for i, model in enumerate(result['models'], 1):
        print(f'{i}. {model["filename"]} ({model["model_type"]}) - node: {model["node_type"]}')
