"""
Civitai Searcher Module

Searches for models on Civitai platform using their API.
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
import logging
from urllib.parse import quote

from ..utils.cache_manager import CacheManager
from ..utils.logger import get_logger


class CivitaiSearcher:
    """Searches for models on Civitai platform."""
    
    def __init__(self, api_key: str, cache_manager: Optional[CacheManager] = None):
        """
        Initialize the Civitai searcher.
        
        Args:
            api_key: Civitai API key
            cache_manager: Cache manager instance
        """
        self.api_key = api_key
        self.cache_manager = cache_manager or CacheManager()
        self.logger = get_logger(__name__)
        
        # API endpoints
        self.base_url = "https://civitai.com/api/v1"
        self.models_endpoint = f"{self.base_url}/models"
        
        # Request headers
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def search_model(self, filename: str, 
                          model_type: Optional[str] = None,
                          use_cache: bool = True) -> Optional[Dict]:
        """
        Search for a specific model file on Civitai.
        
        Args:
            filename: Model filename to search for
            model_type: Type of model (lora, checkpoint, etc.)
            use_cache: Whether to use cached results
            
        Returns:
            Model information if found, None otherwise
        """
        # Check cache first
        cache_key = f"civitai_{filename}"
        if use_cache:
            cached = self.cache_manager.get(cache_key, cache_type='search')
            if cached is not None:
                self.logger.debug(f"Cache hit for Civitai: {filename}")
                return cached
        
        # Extract search query from filename
        search_query = self._extract_search_query(filename)
        
        try:
            result = await self._search_by_query(search_query, filename, model_type)
            
            # Cache the result
            self.cache_manager.set(cache_key, result, cache_type='search')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Civitai search error for '{filename}': {e}")
            return None
    
    def _extract_search_query(self, filename: str) -> str:
        """
        Extract search query from filename.
        
        Args:
            filename: Model filename
            
        Returns:
            Search query string
        """
        # Remove extension
        name = filename.rsplit('.', 1)[0]
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Extract meaningful parts
        parts = []
        for word in name.split():
            # Skip common technical terms
            if word.lower() not in ['safetensors', 'ckpt', 'pt', 'bin', 'fp16', 'fp8']:
                parts.append(word)
        
        return ' '.join(parts)
    
    async def _search_by_query(self, query: str, 
                              target_filename: str,
                              model_type: Optional[str] = None) -> Optional[Dict]:
        """
        Search Civitai for a specific query.
        
        Args:
            query: Search query
            target_filename: Target filename to find
            model_type: Optional model type filter
            
        Returns:
            Model information if found
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Build search parameters
                params = {
                    'query': query,
                    'limit': 20,
                    'sort': 'Most Downloaded'
                }
                
                # Add type filter if specified
                if model_type:
                    type_mapping = {
                        'lora': 'LORA',
                        'checkpoint': 'Checkpoint',
                        'controlnet': 'Controlnet',
                        'vae': 'VAE',
                        'upscale': 'Upscaler'
                    }
                    if model_type.lower() in type_mapping:
                        params['types'] = type_mapping[model_type.lower()]
                
                self.logger.debug(f"Civitai search params: {params}")
                
                async with session.get(self.models_endpoint, 
                                     headers=self.headers,
                                     params=params) as response:
                    if response.status != 200:
                        self.logger.warning(f"Civitai search failed with status {response.status}")
                        return None
                    
                    data = await response.json()
                    models = data.get('items', [])
                    
                    # Look for matching model
                    for model in models:
                        # Check model versions
                        model_versions = model.get('modelVersions', [])
                        
                        for version in model_versions:
                            # Check files in this version
                            files = version.get('files', [])
                            
                            for file in files:
                                file_name = file.get('name', '').lower()
                                target_lower = target_filename.lower()
                                
                                # Check for exact match or close match
                                if (file_name == target_lower or
                                    self._is_similar_filename(file_name, target_lower)):
                                    
                                    # Found a match!
                                    download_url = file.get('downloadUrl', '')
                                    
                                    # Add API key to download URL if needed
                                    if download_url and '?' in download_url:
                                        download_url += f"&token={self.api_key}"
                                    elif download_url:
                                        download_url += f"?token={self.api_key}"
                                    
                                    return {
                                        'model_id': model.get('id'),
                                        'model_name': model.get('name'),
                                        'version_id': version.get('id'),
                                        'version_name': version.get('name'),
                                        'filename': file.get('name'),
                                        'url': download_url,
                                        'size': file.get('sizeKB', 0) * 1024,  # Convert to bytes
                                        'model_info': {
                                            'type': model.get('type'),
                                            'tags': model.get('tags', []),
                                            'downloadCount': version.get('downloadCount', 0),
                                            'description': model.get('description', ''),
                                            'baseModel': version.get('baseModel'),
                                            'images': version.get('images', [])
                                        },
                                        'platform': 'civitai'
                                    }
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Civitai API error: {e}")
            return None
    
    def _is_similar_filename(self, file1: str, file2: str) -> bool:
        """
        Check if two filenames are similar enough to be considered a match.
        
        Args:
            file1: First filename (lowercase)
            file2: Second filename (lowercase)
            
        Returns:
            True if similar
        """
        # Remove extensions
        base1 = file1.rsplit('.', 1)[0]
        base2 = file2.rsplit('.', 1)[0]
        
        # Normalize separators
        norm1 = base1.replace('-', '_').replace(' ', '_')
        norm2 = base2.replace('-', '_').replace(' ', '_')
        
        return norm1 == norm2
    
    def search_sync(self, filename: str, 
                   model_type: Optional[str] = None,
                   use_cache: bool = True) -> Optional[Dict]:
        """
        Synchronous wrapper for search_model.
        
        Args:
            filename: Model filename to search for
            model_type: Type of model
            use_cache: Whether to use cached results
            
        Returns:
            Model information if found
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.search_model(filename, model_type, use_cache)
            )
        finally:
            loop.close()
    
    async def get_model_details(self, model_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: Civitai model ID
            
        Returns:
            Detailed model information
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.models_endpoint}/{model_id}"
                
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
                    
        except Exception as e:
            self.logger.error(f"Failed to get model details for {model_id}: {e}")
            return None