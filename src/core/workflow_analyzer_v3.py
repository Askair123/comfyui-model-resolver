"""
Ultimate Workflow Analyzer with comprehensive detection
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import logging

class WorkflowAnalyzerV3:
    """Ultimate workflow analyzer with maximum detection coverage."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model file extensions
        self.model_extensions = {
            '.safetensors', '.ckpt', '.pt', '.pth', '.bin', 
            '.gguf', '.onnx', '.pb', '.h5', '.pkl', '.model',
            '.zip', '.tar', '.tgz'  # Some models come compressed
        }
        
        # Extension to type mapping
        self.extension_hints = {
            '.gguf': 'unet',
            '.onnx': 'detector',
            '.h5': 'keras_model'
        }
        
        # Common model type indicators
        self.type_indicators = {
            'checkpoint': ['ckpt', 'checkpoint', 'model', 'dreambooth', 'merged'],
            'lora': ['lora', 'locon', 'lycoris', 'loha'],
            'vae': ['vae', 'variational'],
            'controlnet': ['controlnet', 'control', 'cnet'],
            'upscale': ['upscale', 'esrgan', 'realesrgan', 'swinir', '2x', '4x', '8x'],
            'embeddings': ['embedding', 'embed', 'textual_inversion', 'ti'],
            'clip': ['clip', 'text_encoder', 't5', 'bert'],
            'unet': ['unet', 'diffusion', 'denoiser'],
            'ipadapter': ['ipadapter', 'ip_adapter', 'ip-adapter'],
            'animatediff': ['animatediff', 'motion', 'temporal'],
            'instantid': ['instantid', 'instant_id'],
            'detector': ['yolo', 'sam', 'detectron', 'rcnn', 'detector'],
            'pose': ['pose', 'openpose', 'dwpose'],
            'depth': ['depth', 'midas', 'dpt'],
            'normal': ['normal', 'bae'],
            'segmentation': ['seg', 'segment', 'sam'],
            'inpaint': ['inpaint', 'outpaint'],
            'hypernetwork': ['hypernet', 'hypernetwork'],
            'style': ['style', 'aesthetic'],
            'wildcard': ['wildcard', 'dynamic'],
            'reactor': ['reactor', 'face', 'swap'],
            'ipadapter': ['ipadapter', 'ip-adapter', 'image_encoder'],
            'text_encoders': ['t5', 'clip', 'bert', 'text_encoder', 'tokenizer'],
            'flux': ['flux', 'flow'],
            'custom': ['custom', 'community']
        }
        
    def analyze_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        Comprehensively analyze workflow for all model references.
        
        Args:
            workflow_path: Path to workflow JSON file
            
        Returns:
            Complete analysis results
        """
        with open(workflow_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Multiple detection strategies
        all_detections = []
        
        # Strategy 1: Widget values extraction
        widget_models = self._extract_from_widgets(data)
        all_detections.extend(widget_models)
        
        # Strategy 2: String scanning with context
        string_models = self._scan_all_strings(data)
        all_detections.extend(string_models)
        
        # Strategy 3: Path extraction
        path_models = self._extract_paths(data)
        all_detections.extend(path_models)
        
        # Strategy 4: Input/Output connections
        connection_models = self._extract_from_connections(data)
        all_detections.extend(connection_models)
        
        # Strategy 5: Node metadata
        metadata_models = self._extract_from_metadata(data)
        all_detections.extend(metadata_models)
        
        # Strategy 6: Comments and notes
        comment_models = self._extract_from_comments(data)
        all_detections.extend(comment_models)
        
        # Clean and deduplicate
        unique_models = self._process_detections(all_detections)
        
        return {
            'workflow_file': workflow_path,
            'total_nodes': len(data.get('nodes', [])),
            'model_count': len(unique_models),
            'models': unique_models,
            'raw_detections': len(all_detections),
            'detection_methods': self._count_methods(all_detections)
        }
    
    def _extract_from_widgets(self, data: Dict) -> List[Dict]:
        """Extract from widget values (most reliable source)."""
        models = []
        nodes = data.get('nodes', [])
        
        for node in nodes:
            node_id = node.get('id', 'unknown')
            node_type = node.get('type', '')
            widgets = node.get('widgets_values', [])
            
            # Process each widget value
            for idx, widget in enumerate(widgets):
                extracted = self._extract_from_value(
                    widget, 
                    source='widget',
                    node_id=node_id,
                    node_type=node_type,
                    widget_index=idx
                )
                models.extend(extracted)
        
        return models
    
    def _extract_from_value(self, value: Any, **context) -> List[Dict]:
        """Recursively extract model references from any value."""
        models = []
        
        if isinstance(value, str):
            # Check if it's a model file
            for ext in self.model_extensions:
                if ext in value.lower():
                    # Extract filename
                    filename = self._extract_filename(value)
                    if filename:
                        model_type = self._infer_type(filename, value, context.get('node_type', ''))
                        models.append({
                            'filename': filename,
                            'model_type': model_type,
                            'full_string': value,
                            **context
                        })
                    break
                    
        elif isinstance(value, dict):
            # Recursively process dict
            for k, v in value.items():
                sub_models = self._extract_from_value(
                    v, 
                    dict_key=k,
                    **context
                )
                models.extend(sub_models)
                
        elif isinstance(value, list):
            # Process list items
            for i, item in enumerate(value):
                sub_models = self._extract_from_value(
                    item,
                    list_index=i,
                    **context
                )
                models.extend(sub_models)
        
        return models
    
    def _scan_all_strings(self, data: Dict) -> List[Dict]:
        """Scan all string values in the JSON."""
        models = []
        
        def scan_object(obj, path=""):
            if isinstance(obj, str):
                # Skip if this looks like markdown documentation
                if self._is_markdown_content(obj):
                    # Extract only model filenames from markdown links
                    markdown_models = self._extract_from_markdown_links(obj)
                    for filename in markdown_models:
                        model_type = self._infer_type(filename, obj, "")
                        models.append({
                            'filename': filename,
                            'model_type': model_type,
                            'full_string': filename,
                            'source': 'markdown_link',
                            'json_path': path
                        })
                else:
                    # Check for model files
                    for ext in self.model_extensions:
                        if ext in obj.lower():
                            filename = self._extract_filename(obj)
                            if filename:
                                model_type = self._infer_type(filename, obj, "")
                                models.append({
                                    'filename': filename,
                                    'model_type': model_type,
                                    'full_string': obj,
                                    'source': 'string_scan',
                                    'json_path': path
                                })
                            break
                        
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_object(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_object(item, f"{path}[{i}]")
        
        scan_object(data)
        return models
    
    def _extract_paths(self, data: Dict) -> List[Dict]:
        """Extract from path-like structures."""
        models = []
        data_str = json.dumps(data)
        
        # Pattern for paths with model files
        path_patterns = [
            # Windows paths
            r'[A-Za-z]:\\[^"\']*?\.(?:' + '|'.join(ext[1:] for ext in self.model_extensions) + r')',
            # Unix paths
            r'/[^"\']*?\.(?:' + '|'.join(ext[1:] for ext in self.model_extensions) + r')',
            # Relative paths
            r'\.{1,2}/[^"\']*?\.(?:' + '|'.join(ext[1:] for ext in self.model_extensions) + r')',
        ]
        
        for pattern in path_patterns:
            matches = re.finditer(pattern, data_str, re.IGNORECASE)
            for match in matches:
                full_path = match.group(0)
                filename = self._extract_filename(full_path)
                if filename:
                    model_type = self._infer_type(filename, full_path, "")
                    models.append({
                        'filename': filename,
                        'model_type': model_type,
                        'full_string': full_path,
                        'source': 'path_scan'
                    })
        
        return models
    
    def _extract_from_connections(self, data: Dict) -> List[Dict]:
        """Extract from node connections and links."""
        models = []
        
        # Check links array
        links = data.get('links', [])
        for link in links:
            if isinstance(link, list) and len(link) >= 6:
                # Sometimes model names are stored in link data
                for item in link:
                    if isinstance(item, str):
                        for ext in self.model_extensions:
                            if ext in item.lower():
                                filename = self._extract_filename(item)
                                if filename:
                                    models.append({
                                        'filename': filename,
                                        'model_type': 'unknown',
                                        'source': 'connection'
                                    })
        
        return models
    
    def _extract_from_metadata(self, data: Dict) -> List[Dict]:
        """Extract from node metadata and properties."""
        models = []
        nodes = data.get('nodes', [])
        
        for node in nodes:
            # Check properties
            props = node.get('properties', {})
            for key, value in props.items():
                if isinstance(value, str):
                    for ext in self.model_extensions:
                        if ext in value.lower():
                            filename = self._extract_filename(value)
                            if filename:
                                models.append({
                                    'filename': filename,
                                    'model_type': self._infer_type(filename, value, node.get('type', '')),
                                    'source': 'metadata',
                                    'metadata_key': key
                                })
            
            # Check for model lists in node data
            if 'models' in node:
                model_list = node.get('models', [])
                if isinstance(model_list, list):
                    for model_data in model_list:
                        if isinstance(model_data, dict) and 'name' in model_data:
                            filename = model_data['name']
                            if any(ext in filename.lower() for ext in self.model_extensions):
                                models.append({
                                    'filename': filename,
                                    'model_type': self._infer_type(filename, "", node.get('type', '')),
                                    'source': 'model_list',
                                    'node_id': node.get('id', 'unknown')
                                })
        
        return models
    
    def _extract_from_comments(self, data: Dict) -> List[Dict]:
        """Extract from comments, notes, and text fields."""
        models = []
        nodes = data.get('nodes', [])
        
        for node in nodes:
            node_type = node.get('type', '').lower()
            
            # Note nodes often contain model information
            if 'note' in node_type or 'comment' in node_type or 'text' in node_type:
                widgets = node.get('widgets_values', [])
                for widget in widgets:
                    if isinstance(widget, str):
                        # Extract model references from text
                        for ext in self.model_extensions:
                            pattern = r'([^\s\/\\:"\']+' + re.escape(ext) + r')'
                            matches = re.finditer(pattern, widget, re.IGNORECASE)
                            for match in matches:
                                filename = match.group(1)
                                models.append({
                                    'filename': filename,
                                    'model_type': self._infer_type(filename, widget, ""),
                                    'source': 'comment',
                                    'node_type': node_type
                                })
        
        return models
    
    def _is_markdown_content(self, text: str) -> bool:
        """Check if text appears to be markdown documentation."""
        if len(text) < 100:
            return False
        
        # Check for multiple markdown indicators
        markdown_indicators = [
            '\n## ', '\n### ', '**', '- [', '](', '\n- ', '\n* '
        ]
        
        indicator_count = sum(1 for indicator in markdown_indicators if indicator in text)
        newline_count = text.count('\n')
        
        # If it has many newlines and markdown features, it's probably documentation
        return newline_count > 5 and indicator_count >= 2
    
    def _extract_from_markdown_links(self, markdown: str) -> List[str]:
        """Extract model filenames only from markdown links."""
        models = []
        
        # Pattern to find markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for match in re.finditer(link_pattern, markdown):
            link_text = match.group(1)
            
            # Check if link text is a model filename
            if any(ext in link_text.lower() for ext in self.model_extensions):
                # Clean up the filename
                filename = link_text.strip()
                if filename not in models:
                    models.append(filename)
        
        return models
    
    def _extract_filename(self, value: str) -> Optional[str]:
        """Extract clean filename from various formats."""
        if not value:
            return None
            
        # Remove quotes
        value = value.strip('"\'')
        
        # Handle paths (Windows and Unix)
        if '\\' in value or '/' in value:
            # Get last component
            parts = re.split(r'[\\\/]', value)
            filename = parts[-1]
        else:
            filename = value
        
        # Clean up
        filename = filename.strip()
        
        # Validate it's a model file
        if any(filename.lower().endswith(ext) for ext in self.model_extensions):
            return filename
        
        return None
    
    def _infer_type(self, filename: str, full_string: str = "", node_type: str = "") -> str:
        """Intelligently infer model type from all available context."""
        filename_lower = filename.lower()
        full_lower = full_string.lower()
        node_lower = node_type.lower()
        
        # Check all contexts for type indicators
        contexts = [filename_lower, full_lower, node_lower]
        
        for model_type, indicators in self.type_indicators.items():
            for indicator in indicators:
                if any(indicator in ctx for ctx in contexts):
                    return model_type
        
        # Extension-based hints
        for ext, type_hint in self.extension_hints.items():
            if filename_lower.endswith(ext):
                return type_hint
        
        # Special patterns
        if re.search(r'\d+x[-_]', filename_lower):  # Like "4x-UltraSharp"
            return 'upscale'
        
        if 'xl' in filename_lower or 'sdxl' in filename_lower:
            return 'checkpoint'
            
        if re.search(r'v\d+', filename_lower):  # Version numbers often in checkpoints
            return 'checkpoint'
        
        return 'unknown'
    
    def _process_detections(self, detections: List[Dict]) -> List[Dict]:
        """Process and deduplicate detections."""
        # Group by filename
        by_filename = {}
        
        for detection in detections:
            filename = detection['filename']
            if filename not in by_filename:
                by_filename[filename] = []
            by_filename[filename].append(detection)
        
        # Create unique model entries
        unique_models = []
        
        for filename, detections_list in by_filename.items():
            # Determine best type (prefer non-unknown)
            types = [d['model_type'] for d in detections_list]
            best_type = next((t for t in types if t != 'unknown'), 'unknown')
            
            # Collect all sources
            sources = list(set(d.get('source', 'unknown') for d in detections_list))
            
            # Get additional context
            node_types = list(set(d.get('node_type', '') for d in detections_list if d.get('node_type')))
            
            unique_models.append({
                'filename': filename,
                'model_type': best_type,
                'sources': sources,
                'detection_count': len(detections_list),
                'node_types': node_types
            })
        
        return unique_models
    
    def _count_methods(self, detections: List[Dict]) -> Dict[str, int]:
        """Count detections by method."""
        method_counts = {}
        for detection in detections:
            source = detection.get('source', 'unknown')
            method_counts[source] = method_counts.get(source, 0) + 1
        return method_counts