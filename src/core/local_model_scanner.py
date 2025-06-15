"""
Local Model Scanner - Wrapper for LocalScanner with simplified interface
"""

from typing import List, Dict, Optional
from .local_scanner import LocalScanner


class LocalModelScanner:
    """Simplified scanner interface for workflow service."""
    
    def __init__(self, comfyui_root: str = "/workspace/ComfyUI"):
        # Initialize the base scanner
        models_path = f"{comfyui_root}/models"
        self.scanner = LocalScanner(base_path=models_path)
    
    def scan_for_model(self, filename: str, model_type: Optional[str] = None) -> List[Dict]:
        """
        Scan for a specific model file.
        
        Args:
            filename: Model filename to search for
            model_type: Optional model type hint to narrow search
            
        Returns:
            List of found models with metadata
        """
        # Use the base scanner's find method
        matches = self.scanner.find_model_by_name(filename, model_type)
        
        # Format results
        results = []
        for match in matches:
            results.append({
                'path': match['full_path'],
                'size': int(match.get('size_gb', 0) * 1024 * 1024 * 1024),  # Convert to bytes
                'directory': match.get('directory', ''),
                'match_type': 'exact'
            })
        
        return results