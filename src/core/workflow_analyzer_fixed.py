"""
Fixed version of workflow analyzer that properly handles markdown content
and deduplicates models.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WorkflowAnalyzerFixed:
    """
    Fixed analyzer for ComfyUI workflow files.
    Properly handles markdown content and deduplicates models.
    """
    
    # Supported model extensions
    MODEL_EXTENSIONS = ['.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.gguf']
    
    # Node type to model type mappings
    NODE_MAPPINGS = {
        'CheckpointLoaderSimple': {'model_type': 'checkpoints', 'directory': 'checkpoints'},
        'LoraLoader': {'model_type': 'loras', 'directory': 'loras'},
        'VAELoader': {'model_type': 'vae', 'directory': 'vae'},
        'ControlNetLoader': {'model_type': 'controlnet', 'directory': 'controlnet'},
        'CLIPLoader': {'model_type': 'clip', 'directory': 'clip'},
        'UNETLoader': {'model_type': 'unet', 'directory': 'unet'},
        'LoaderGGUF': {'model_type': 'unet', 'directory': 'unet'},
        'ClipLoaderGGUF': {'model_type': 'clip', 'directory': 'text_encoders'},
        'Power Lora Loader (rgthree)': {'model_type': 'loras', 'directory': 'loras'},
    }
    
    def __init__(self, comfyui_dir: str = "/workspace/ComfyUI"):
        self.comfyui_dir = comfyui_dir
        self.models_dir = os.path.join(comfyui_dir, "models")
        
    def analyze_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """Analyze workflow and extract unique models."""
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
            
        with open(workflow_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in workflow file: {e}")
        
        # Extract models from nodes
        models = []
        seen_models: Set[Tuple[str, str]] = set()
        
        # Process nodes
        nodes = data.get('nodes', [])
        for node in nodes:
            node_models = self._extract_models_from_node(node)
            for model in node_models:
                # Create unique key for deduplication
                key = (model['filename'], model['model_type'])
                if key not in seen_models:
                    seen_models.add(key)
                    models.append(model)
        
        # Also check old format workflows
        if not nodes and isinstance(data, dict):
            for node_id, node in data.items():
                if isinstance(node, dict) and 'inputs' in node:
                    node_models = self._extract_models_from_old_format(node)
                    for model in node_models:
                        key = (model['filename'], model['model_type'])
                        if key not in seen_models:
                            seen_models.add(key)
                            models.append(model)
        
        return {
            'workflow_file': workflow_path,
            'total_nodes': len(nodes) if nodes else len(data),
            'model_count': len(models),
            'models': models
        }
    
    def _extract_models_from_node(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract models from a single node."""
        models = []
        node_type = node.get('type', '')
        
        # Check if it's a known model loader node
        if node_type not in self.NODE_MAPPINGS:
            return models
            
        model_config = self.NODE_MAPPINGS[node_type]
        
        # Extract from widgets_values
        widgets = node.get('widgets_values', [])
        for widget in widgets:
            if isinstance(widget, str):
                # Check if it's a model filename
                if self._is_model_filename(widget):
                    models.append({
                        'filename': widget,
                        'model_type': model_config['model_type'],
                        'directory': model_config['directory'],
                        'node_type': node_type
                    })
                # Check if it contains markdown with model references
                elif self._looks_like_markdown(widget):
                    markdown_models = self._extract_models_from_markdown(widget)
                    for model_name in markdown_models:
                        models.append({
                            'filename': model_name,
                            'model_type': model_config['model_type'],
                            'directory': model_config['directory'],
                            'node_type': node_type
                        })
            elif isinstance(widget, dict):
                # Handle Power Lora Loader format
                for key, value in widget.items():
                    if isinstance(value, str) and self._is_model_filename(value):
                        models.append({
                            'filename': value,
                            'model_type': model_config['model_type'],
                            'directory': model_config['directory'],
                            'node_type': node_type
                        })
        
        return models
    
    def _extract_models_from_old_format(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract models from old workflow format."""
        models = []
        inputs = node.get('inputs', {})
        
        # Map of input keys to model types
        input_mappings = {
            'ckpt_name': 'checkpoints',
            'lora_name': 'loras',
            'vae_name': 'vae',
            'control_net_name': 'controlnet',
            'clip_name': 'clip',
            'unet_name': 'unet',
            'model_name': 'checkpoints',  # Generic
        }
        
        for key, value in inputs.items():
            if key in input_mappings and isinstance(value, str):
                if self._is_model_filename(value):
                    models.append({
                        'filename': value,
                        'model_type': input_mappings[key],
                        'directory': input_mappings[key],
                        'node_type': 'legacy'
                    })
        
        return models
    
    def _is_model_filename(self, text: str) -> bool:
        """Check if text is a model filename."""
        if not text or not isinstance(text, str):
            return False
        return any(text.endswith(ext) for ext in self.MODEL_EXTENSIONS)
    
    def _looks_like_markdown(self, text: str) -> bool:
        """Check if text looks like markdown documentation."""
        if not text or len(text) < 100:
            return False
        
        # Check for markdown indicators
        markdown_indicators = [
            '\n## ',  # Headers
            '\n- ',   # Lists
            '**',     # Bold
            '[',      # Links
            '](', 
        ]
        
        # Count newlines and markdown features
        newline_count = text.count('\n')
        markdown_count = sum(1 for indicator in markdown_indicators if indicator in text)
        
        # If it has many newlines and markdown features, it's probably documentation
        return newline_count > 5 and markdown_count > 2
    
    def _extract_models_from_markdown(self, markdown: str) -> List[str]:
        """Extract model filenames from markdown content."""
        models = []
        
        # Pattern to find links in markdown
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for match in re.finditer(link_pattern, markdown):
            link_text = match.group(1)
            link_url = match.group(2)
            
            # Check if link text or URL contains a model filename
            for text in [link_text, link_url]:
                if self._is_model_filename(text):
                    # Extract just the filename
                    filename = os.path.basename(text)
                    if filename not in models:
                        models.append(filename)
        
        # Also look for bare filenames in the text
        for ext in self.MODEL_EXTENSIONS:
            pattern = rf'(\S+{re.escape(ext)})'
            for match in re.finditer(pattern, markdown):
                filename = match.group(1)
                # Clean up the filename
                filename = filename.strip('[]()"\',')
                if filename not in models:
                    models.append(filename)
        
        return models
    
    def check_model_exists(self, model_info: Dict[str, Any]) -> bool:
        """Check if a model exists locally."""
        model_dir = os.path.join(self.models_dir, model_info['directory'])
        model_path = os.path.join(model_dir, model_info['filename'])
        
        return os.path.exists(model_path)