"""
Enhanced Workflow Analyzer with hybrid detection strategy
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import logging

class WorkflowAnalyzerV2:
    """Enhanced workflow analyzer using multiple detection strategies."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model file extensions
        self.model_extensions = {
            '.safetensors', '.ckpt', '.pt', '.pth', '.bin', 
            '.gguf', '.onnx', '.pb', '.h5', '.pkl', '.model'
        }
        
        # Known model directories for type inference
        self.directory_types = {
            'checkpoints': ['checkpoint', 'model'],
            'loras': ['lora', 'lycoris'],
            'vae': ['vae'],
            'controlnet': ['controlnet', 'control'],
            'embeddings': ['embedding', 'textual_inversion'],
            'upscale_models': ['upscale', 'esrgan', 'realesrgan'],
            'clip': ['clip', 'text_encoder'],
            'unet': ['unet', 'diffusion'],
            'ipadapter': ['ipadapter', 'ip_adapter'],
            'animatediff': ['animatediff', 'motion'],
            'instantid': ['instantid', 'instant_id']
        }
        
    def analyze_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Analyze workflow using multiple strategies.
        
        Args:
            workflow_path: Path to workflow JSON file
            
        Returns:
            Analysis results with all detected models
        """
        with open(workflow_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Strategy 1: Node-based detection (traditional)
        node_models = self._extract_from_nodes(data)
        
        # Strategy 2: Pattern-based detection (comprehensive)
        pattern_models = self._extract_by_pattern(data)
        
        # Strategy 3: Path-based detection (for embedded paths)
        path_models = self._extract_from_paths(data)
        
        # Merge results
        all_models = self._merge_results(node_models, pattern_models, path_models)
        
        # Deduplicate and enrich
        unique_models = self._deduplicate_models(all_models)
        
        return {
            'workflow_file': workflow_path,
            'total_nodes': len(data.get('nodes', [])),
            'model_count': len(unique_models),
            'models': unique_models,
            'detection_stats': {
                'node_based': len(node_models),
                'pattern_based': len(pattern_models),
                'path_based': len(path_models)
            }
        }
    
    def _extract_from_nodes(self, data: Dict) -> List[Dict]:
        """Traditional node-based extraction (backward compatible)."""
        models = []
        nodes = data.get('nodes', [])
        
        for node in nodes:
            node_type = node.get('type', '')
            widgets_values = node.get('widgets_values', [])
            
            # Check all widget values for model files
            for i, value in enumerate(widgets_values):
                if isinstance(value, str) and self._is_model_file(value):
                    model_type = self._infer_type_from_node(node_type, value)
                    models.append({
                        'filename': value,
                        'model_type': model_type,
                        'source': 'node',
                        'node_type': node_type,
                        'node_id': node.get('id', 'unknown'),
                        'widget_index': i
                    })
                elif isinstance(value, dict):
                    # Handle nested structures (like Power Lora Loader)
                    for key, val in value.items():
                        if isinstance(val, str) and self._is_model_file(val):
                            model_type = self._infer_type_from_key(key, val)
                            models.append({
                                'filename': val,
                                'model_type': model_type,
                                'source': 'node_nested',
                                'node_type': node_type,
                                'node_id': node.get('id', 'unknown'),
                                'nested_key': key
                            })
        
        return models
    
    def _extract_by_pattern(self, data: Dict) -> List[Dict]:
        """Pattern-based extraction using regex."""
        models = []
        data_str = json.dumps(data)
        
        # Create regex for each extension
        for ext in self.model_extensions:
            # Pattern to match filenames with extension
            pattern = r'([^"\'\\\/\s]+' + re.escape(ext) + r')'
            matches = re.finditer(pattern, data_str, re.IGNORECASE)
            
            for match in matches:
                filename = match.group(1)
                # Clean up the filename
                filename = filename.split('/')[-1].split('\\')[-1]
                
                if filename and not filename.startswith('.'):
                    model_type = self._infer_type_from_filename(filename)
                    models.append({
                        'filename': filename,
                        'model_type': model_type,
                        'source': 'pattern',
                        'context': self._get_context(data_str, match.start(), match.end())
                    })
        
        return models
    
    def _extract_from_paths(self, data: Dict) -> List[Dict]:
        """Extract from path-like structures."""
        models = []
        
        def scan_for_paths(obj, path=""):
            if isinstance(obj, str):
                # Check if it looks like a path with model file
                if '/' in obj or '\\' in obj:
                    for ext in self.model_extensions:
                        if ext in obj.lower():
                            filename = obj.split('/')[-1].split('\\')[-1]
                            if filename and not filename.startswith('.'):
                                model_type = self._infer_type_from_path(obj)
                                models.append({
                                    'filename': filename,
                                    'model_type': model_type,
                                    'source': 'path',
                                    'full_path': obj,
                                    'json_path': path
                                })
                            break
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_for_paths(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_paths(item, f"{path}[{i}]")
        
        scan_for_paths(data)
        return models
    
    def _is_model_file(self, value: str) -> bool:
        """Check if a string is likely a model filename."""
        if not isinstance(value, str):
            return False
        return any(value.lower().endswith(ext) for ext in self.model_extensions)
    
    def _infer_type_from_node(self, node_type: str, filename: str) -> str:
        """Infer model type from node type."""
        node_lower = node_type.lower()
        
        # Direct mappings
        if 'checkpoint' in node_lower:
            return 'checkpoint'
        elif 'lora' in node_lower or 'lycoris' in node_lower:
            return 'lora'
        elif 'vae' in node_lower:
            return 'vae'
        elif 'controlnet' in node_lower:
            return 'controlnet'
        elif 'upscale' in node_lower or 'esrgan' in node_lower:
            return 'upscale'
        elif 'clip' in node_lower:
            return 'clip'
        elif 'unet' in node_lower:
            return 'unet'
        elif 'embed' in node_lower:
            return 'embeddings'
        
        # Fallback to filename inference
        return self._infer_type_from_filename(filename)
    
    def _infer_type_from_key(self, key: str, filename: str) -> str:
        """Infer model type from dictionary key."""
        key_lower = key.lower()
        
        if 'lora' in key_lower:
            return 'lora'
        elif 'model' in key_lower or 'ckpt' in key_lower:
            return 'checkpoint'
        elif 'vae' in key_lower:
            return 'vae'
        
        return self._infer_type_from_filename(filename)
    
    def _infer_type_from_filename(self, filename: str) -> str:
        """Infer model type from filename patterns."""
        filename_lower = filename.lower()
        
        # Check for type indicators in filename
        for model_type, keywords in self.directory_types.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return model_type
        
        # Extension-based inference
        if filename_lower.endswith('.gguf'):
            return 'unet'  # GGUF files are typically unet models
        elif filename_lower.endswith(('.pt', '.pth')):
            if 'yolo' in filename_lower or 'sam_vit' in filename_lower:
                return 'detector'  # YOLO/SAM models
            elif 'upscale' in filename_lower or '4x' in filename_lower:
                return 'upscale'
        
        # Check for common patterns
        if 'xl' in filename_lower or 'sdxl' in filename_lower:
            return 'checkpoint'
        elif 'lora' in filename_lower:
            return 'lora'
        elif 'embed' in filename_lower:
            return 'embeddings'
        
        return 'unknown'
    
    def _infer_type_from_path(self, path: str) -> str:
        """Infer model type from full path."""
        path_lower = path.lower()
        
        # Check directory names in path
        for model_type, keywords in self.directory_types.items():
            for keyword in keywords:
                if f'/{keyword}/' in path_lower or f'\\{keyword}\\' in path_lower:
                    return model_type
        
        # Fallback to filename
        filename = path.split('/')[-1].split('\\')[-1]
        return self._infer_type_from_filename(filename)
    
    def _get_context(self, text: str, start: int, end: int, context_size: int = 50) -> str:
        """Get surrounding context for a match."""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end].replace('\n', ' ')
    
    def _merge_results(self, *model_lists) -> List[Dict]:
        """Merge model lists from different strategies."""
        all_models = []
        for models in model_lists:
            all_models.extend(models)
        return all_models
    
    def _deduplicate_models(self, models: List[Dict]) -> List[Dict]:
        """Deduplicate models while preserving information."""
        unique = {}
        
        for model in models:
            filename = model['filename']
            if filename not in unique:
                unique[filename] = model
                unique[filename]['sources'] = [model['source']]
            else:
                # Merge information
                unique[filename]['sources'].append(model['source'])
                # Prefer more specific type
                if unique[filename]['model_type'] == 'unknown' and model['model_type'] != 'unknown':
                    unique[filename]['model_type'] = model['model_type']
        
        # Convert back to list
        result = list(unique.values())
        
        # Ensure unique sources
        for model in result:
            model['sources'] = list(set(model['sources']))
        
        return result