"""
Local Scanner Module

Scans local directories for existing models and builds an index.
"""

import os
import json
import time
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from .keyword_extractor import KeywordExtractor


class LocalScanner:
    """Scans local model directories and manages model inventory."""
    
    def __init__(self, base_path: str = "/workspace/comfyui/models", 
                 cache_dir: Optional[str] = None,
                 cache_ttl_hours: int = 24):
        """
        Initialize the local scanner.
        
        Args:
            base_path: Base directory for ComfyUI models
            cache_dir: Directory for caching scan results
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.base_path = Path(base_path)
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "comfyui-model-resolver"
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_file = self.cache_dir / "local_models_cache.json"
        self.keyword_extractor = KeywordExtractor()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Model extensions to look for
        self.model_extensions = {
            '.safetensors', '.ckpt', '.pt', '.pth', '.bin', 
            '.onnx', '.pb', '.h5', '.pkl', '.model'
        }
        
    def scan_directory(self, directory: str, use_cache: bool = True) -> Dict[str, List[Dict]]:
        """
        Scan a specific directory for models.
        
        Args:
            directory: Directory name relative to base_path (e.g., 'checkpoints')
            use_cache: Whether to use cached results if available
            
        Returns:
            Dictionary with directory name and list of found models
        """
        full_path = self.base_path / directory
        
        # Check cache first
        if use_cache:
            cached_data = self._load_cache()
            if cached_data and directory in cached_data.get('directories', {}):
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - cache_time < self.cache_ttl:
                    return {directory: cached_data['directories'][directory]}
        
        # Perform actual scan
        models = []
        
        if not full_path.exists():
            print(f"Warning: Directory {full_path} does not exist")
            return {directory: models}
        
        for root, _, files in os.walk(full_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.model_extensions):
                    rel_path = Path(root).relative_to(full_path)
                    
                    # Get file info
                    file_path = Path(root) / file
                    try:
                        stat = file_path.stat()
                        size_gb = stat.st_size / (1024 ** 3)
                        modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    except:
                        size_gb = 0
                        modified = None
                    
                    # Extract keywords for searching
                    keywords = self.keyword_extractor.extract_keywords(file)
                    
                    model_info = {
                        'filename': file,
                        'path': str(rel_path / file) if str(rel_path) != '.' else file,
                        'full_path': str(file_path),
                        'size_gb': round(size_gb, 2),
                        'modified': modified,
                        'keywords': keywords
                    }
                    
                    models.append(model_info)
        
        # Update cache
        self._update_cache(directory, models)
        
        return {directory: models}
    
    def scan_all_directories(self, directories: Optional[List[str]] = None, 
                           use_cache: bool = True) -> Dict[str, List[Dict]]:
        """
        Scan all model directories.
        
        Args:
            directories: List of directories to scan. If None, scan all subdirectories
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary mapping directory names to lists of models
        """
        if directories is None:
            # Get all subdirectories
            if self.base_path.exists():
                directories = [d.name for d in self.base_path.iterdir() if d.is_dir()]
            else:
                directories = []
        
        all_models = {}
        
        for directory in directories:
            result = self.scan_directory(directory, use_cache)
            all_models.update(result)
        
        return all_models
    
    def find_model_by_name(self, filename: str, model_type: Optional[str] = None) -> List[Dict]:
        """
        Find models by exact filename.
        
        Args:
            filename: Model filename to search for
            model_type: Optional model type to narrow search
            
        Returns:
            List of matching models with full information
        """
        # Determine which directories to search
        if model_type:
            directories = [self._get_directory_for_type(model_type)]
        else:
            directories = None
        
        # Scan directories
        all_models = self.scan_all_directories(directories)
        
        # Find exact matches
        matches = []
        for directory, models in all_models.items():
            for model in models:
                if model['filename'].lower() == filename.lower():
                    model['directory'] = directory
                    matches.append(model)
        
        return matches
    
    def find_models_by_keywords(self, keywords: List[str], 
                              model_type: Optional[str] = None,
                              threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        """
        Find models by keyword matching.
        
        Args:
            keywords: Keywords to search for
            model_type: Optional model type to narrow search
            threshold: Minimum similarity threshold
            
        Returns:
            List of tuples (model_info, similarity_score) sorted by score
        """
        # Determine which directories to search
        if model_type:
            directories = [self._get_directory_for_type(model_type)]
        else:
            directories = None
        
        # Scan directories
        all_models = self.scan_all_directories(directories)
        
        # Find matches
        matches = []
        
        for directory, models in all_models.items():
            for model in models:
                match_type, score = self.keyword_extractor.match_keywords(
                    keywords, 
                    model['keywords'],
                    threshold
                )
                
                if match_type in ['full', 'partial']:
                    model['directory'] = directory
                    model['match_type'] = match_type
                    matches.append((model, score))
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def get_model_stats(self) -> Dict:
        """
        Get statistics about local models.
        
        Returns:
            Dictionary with model statistics
        """
        all_models = self.scan_all_directories()
        
        stats = {
            'total_models': 0,
            'total_size_gb': 0,
            'by_directory': {},
            'by_extension': {},
            'scan_time': datetime.now().isoformat()
        }
        
        for directory, models in all_models.items():
            stats['by_directory'][directory] = {
                'count': len(models),
                'size_gb': sum(m['size_gb'] for m in models)
            }
            stats['total_models'] += len(models)
            stats['total_size_gb'] += stats['by_directory'][directory]['size_gb']
            
            # Count by extension
            for model in models:
                ext = Path(model['filename']).suffix.lower()
                stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
        
        stats['total_size_gb'] = round(stats['total_size_gb'], 2)
        
        return stats
    
    def _get_directory_for_type(self, model_type: str) -> str:
        """Map model type to directory name."""
        type_to_dir = {
            'checkpoint': 'checkpoints',
            'controlnet': 'controlnet',
            'lora': 'loras',
            'vae': 'vae',
            'upscale': 'upscale_models',
            'embeddings': 'embeddings',
            'clip': 'clip',
            'unet': 'unet'
        }
        return type_to_dir.get(model_type, model_type)
    
    def _load_cache(self) -> Optional[Dict]:
        """Load cached scan results."""
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def _update_cache(self, directory: str, models: List[Dict]):
        """Update cache with new scan results."""
        # Load existing cache or create new
        cached_data = self._load_cache() or {
            'timestamp': datetime.now().isoformat(),
            'directories': {}
        }
        
        # Update specific directory
        cached_data['directories'][directory] = models
        cached_data['timestamp'] = datetime.now().isoformat()
        
        # Save cache
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cached_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to update cache: {e}")
    
    def clear_cache(self):
        """Clear the local scan cache."""
        if self.cache_file.exists():
            self.cache_file.unlink()
            print("Local scan cache cleared")