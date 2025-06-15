"""
Workflow Analyzer Module

Parses ComfyUI workflow JSON files and extracts model dependencies.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml


class WorkflowAnalyzer:
    """Analyzes ComfyUI workflow files to extract model dependencies."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the workflow analyzer.
        
        Args:
            config_path: Path to model mappings configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.node_mappings = self._load_node_mappings()
        
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Navigate from src/core to config directory
        current_dir = Path(__file__).parent
        config_path = current_dir.parent.parent / "config" / "model_mappings.yaml"
        return str(config_path)
        
    def _load_node_mappings(self) -> Dict[str, Dict]:
        """Load node type to model type mappings from configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Merge standard and custom node mappings
                mappings = config.get('node_mappings', {})
                custom_mappings = config.get('custom_node_mappings', {})
                mappings.update(custom_mappings)
                return mappings
        except FileNotFoundError:
            # Fallback to hardcoded mappings if config not found
            return self._get_default_mappings()
            
    def _get_default_mappings(self) -> Dict[str, Dict]:
        """Get default node mappings if config file is not available."""
        return {
            'CheckpointLoaderSimple': {
                'model_type': 'checkpoint',
                'directory': 'checkpoints',
                'extensions': ['.safetensors', '.ckpt', '.pt']
            },
            'ControlNetLoader': {
                'model_type': 'controlnet',
                'directory': 'controlnet',
                'extensions': ['.safetensors', '.pth', '.pt']
            },
            'LoraLoader': {
                'model_type': 'lora',
                'directory': 'loras',
                'extensions': ['.safetensors', '.pt']
            },
            'VAELoader': {
                'model_type': 'vae',
                'directory': 'vae',
                'extensions': ['.safetensors', '.pt', '.ckpt']
            },
            'UpscaleModelLoader': {
                'model_type': 'upscale',
                'directory': 'upscale_models',
                'extensions': ['.pth', '.pt', '.safetensors']
            },
            'CLIPLoader': {
                'model_type': 'clip',
                'directory': 'clip',
                'extensions': ['.safetensors', '.bin', '.pt']
            },
            'UNETLoader': {
                'model_type': 'unet',
                'directory': 'unet',
                'extensions': ['.safetensors', '.pt']
            },
            # GGUF support
            'LoaderGGUF': {
                'model_type': 'unet',
                'directory': 'unet',
                'extensions': ['.gguf']
            },
            'ClipLoaderGGUF': {
                'model_type': 'text_encoders',
                'directory': 'text_encoders',
                'extensions': ['.safetensors', '.gguf']
            },
            # Custom loaders
            'Power Lora Loader (rgthree)': {
                'model_type': 'lora',
                'directory': 'loras',
                'extensions': ['.safetensors', '.pt']
            }
        }
    
    def analyze_workflow(self, workflow_path: str) -> Dict[str, List[Dict]]:
        """
        Analyze a workflow file and extract model dependencies.
        
        Args:
            workflow_path: Path to the workflow JSON file
            
        Returns:
            Dictionary containing extracted model information
        """
        if not os.path.exists(workflow_path):
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
            
        with open(workflow_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in workflow file: {e}")
        
        models = []
        nodes = data.get('nodes', [])
        
        for node in nodes:
            model_info = self._extract_model_from_node(node)
            if model_info:
                models.append(model_info)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in models:
            key = (model['filename'], model['model_type'])
            if key not in seen:
                seen.add(key)
                unique_models.append(model)
        
        return {
            'workflow_file': workflow_path,
            'total_nodes': len(nodes),
            'model_count': len(unique_models),
            'models': unique_models
        }
    
    def _extract_model_from_node(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract model information from a single node.
        
        Args:
            node: Node dictionary from workflow
            
        Returns:
            Model information dict or None if no model found
        """
        node_type = node.get('type', '')
        
        # Skip if not a model loader node
        if node_type not in self.node_mappings:
            return None
            
        # Get model configuration for this node type
        model_config = self.node_mappings[node_type]
        
        # Extract filename from widgets_values
        widgets = node.get('widgets_values', [])
        if not widgets:
            return None
            
        # Special handling for different node types
        filename = None
        
        if node_type == 'Power Lora Loader (rgthree)':
            # For Power Lora Loader, the model name is in a dict
            for widget in widgets:
                if isinstance(widget, dict) and 'lora' in widget:
                    filename = widget.get('lora')
                    break
        else:
            # For standard nodes, filename is usually the first string
            for widget in widgets:
                if isinstance(widget, str) and any(ext in widget for ext in model_config['extensions']):
                    filename = widget
                    break
        
        if not filename:
            return None
        
        # Check if it has a valid extension
        valid_extensions = model_config.get('extensions', [])
        if not any(filename.lower().endswith(ext) for ext in valid_extensions):
            return None
        
        return {
            'filename': filename,
            'model_type': model_config['model_type'],
            'directory': model_config['directory'],
            'node_id': node.get('id', 'unknown'),
            'node_type': node_type,
            'full_path': None  # Will be populated during local scan
        }
    
    def analyze_directory(self, directory: str) -> List[Dict[str, List[Dict]]]:
        """
        Analyze all workflow files in a directory.
        
        Args:
            directory: Directory containing workflow files
            
        Returns:
            List of analysis results for each workflow
        """
        results = []
        
        # Find all JSON files in directory
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    filepath = os.path.join(root, file)
                    try:
                        result = self.analyze_workflow(filepath)
                        results.append(result)
                    except Exception as e:
                        print(f"Error analyzing {filepath}: {e}")
                        
        return results