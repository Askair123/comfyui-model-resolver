"""
HuggingFace Searcher Module

Searches for models on HuggingFace Hub.
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import quote

from ..utils.cache_manager import CacheManager
from ..utils.logger import get_logger
from ..core.keyword_extractor import KeywordExtractor
try:
    from .optimized_search import OptimizedModelSearcher
except ImportError:
    OptimizedModelSearcher = None


class HuggingFaceSearcher:
    """Searches for models on HuggingFace Hub."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None,
                 api_token: Optional[str] = None):
        """
        Initialize the HuggingFace searcher.
        
        Args:
            cache_manager: Cache manager instance
            api_token: Optional HuggingFace API token
        """
        self.cache_manager = cache_manager or CacheManager()
        self.api_token = api_token
        self.keyword_extractor = KeywordExtractor()
        self.optimized_searcher = OptimizedModelSearcher() if OptimizedModelSearcher else None
        self.logger = get_logger(__name__)
        
        # API endpoints
        self.base_url = "https://huggingface.co/api"
        self.models_endpoint = f"{self.base_url}/models"
        
        # Request headers
        self.headers = {}
        if self.api_token:
            self.headers['Authorization'] = f'Bearer {self.api_token}'
    
    async def search_model(self, filename: str, 
                          use_cache: bool = True) -> Optional[Dict]:
        """
        Search for a specific model file on HuggingFace.
        
        Args:
            filename: Model filename to search for
            use_cache: Whether to use cached results
            
        Returns:
            Model information if found, None otherwise
        """
        # Check cache first
        if use_cache:
            cached = self.cache_manager.get(filename, cache_type='search')
            if cached is not None:
                self.logger.debug(f"Cache hit for: {filename}")
                return cached
        
        # Extract search terms from filename
        search_terms = self._generate_search_terms(filename)
        
        # Try different search strategies
        result = None
        for term in search_terms:
            result = await self._search_by_term(term, filename)
            if result:
                break
        
        # Cache the result (even if None)
        self.cache_manager.set(filename, result, cache_type='search')
        
        return result
    
    async def batch_search(self, filenames: List[str],
                          max_concurrent: int = 5) -> Dict[str, Optional[Dict]]:
        """
        Search for multiple models concurrently.
        
        Args:
            filenames: List of model filenames
            max_concurrent: Maximum concurrent searches
            
        Returns:
            Dictionary mapping filenames to search results
        """
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_with_semaphore(filename):
            async with semaphore:
                return filename, await self.search_model(filename)
        
        # Run searches concurrently
        tasks = [search_with_semaphore(fn) for fn in filenames]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    def _generate_search_terms(self, filename: str) -> List[str]:
        """
        Generate search terms from filename.
        
        Args:
            filename: Model filename
            
        Returns:
            List of search terms to try
        """
        # Use optimized searcher if available
        if self.optimized_searcher:
            optimized_terms = self.optimized_searcher.generate_search_terms(filename)
            if optimized_terms:
                self.logger.debug(f"Using optimized search terms for {filename}: {optimized_terms}")
                return optimized_terms
        
        # Fallback to original logic
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Extract keywords
        keywords = self.keyword_extractor.extract_keywords(filename)
        
        search_terms = []
        
        # Try full name without extension
        search_terms.append(name_without_ext)
        
        # Try core keywords joined
        if keywords:
            # First 2-3 keywords
            if len(keywords) >= 2:
                search_terms.append('_'.join(keywords[:2]))
                search_terms.append(' '.join(keywords[:2]))
            if len(keywords) >= 3:
                search_terms.append('_'.join(keywords[:3]))
            
            # Just the first keyword
            search_terms.append(keywords[0])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    async def _search_by_term(self, search_term: str, 
                             target_filename: str) -> Optional[Dict]:
        """
        Search HuggingFace for a specific term and filename.
        
        Args:
            search_term: Search query
            target_filename: Target filename to find
            
        Returns:
            Model information if found
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Search for models
                search_url = f"{self.models_endpoint}?search={quote(search_term)}&full=true"
                
                async with session.get(search_url, headers=self.headers) as response:
                    if response.status != 200:
                        self.logger.warning(f"Search failed with status {response.status}")
                        return None
                    
                    models = await response.json()
                    
                    # Look for exact filename match in results
                    best_match = None
                    best_score = 0.0
                    
                    for model in models:
                        model_id = model.get('modelId', '')
                        
                        # Check siblings (files in the model)
                        for sibling in model.get('siblings', []):
                            sibling_name = sibling.get('rfilename', '')
                            
                            # Check exact match first
                            if sibling_name.lower() == target_filename.lower():
                                # Found exact match
                                return {
                                    'repo_id': model_id,
                                    'filename': sibling['rfilename'],
                                    'url': f"https://huggingface.co/{model_id}/resolve/main/{sibling['rfilename']}",
                                    'size': sibling.get('size', 0),
                                    'model_info': {
                                        'downloads': model.get('downloads', 0),
                                        'likes': model.get('likes', 0),
                                        'tags': model.get('tags', []),
                                        'lastModified': model.get('lastModified', '')
                                    }
                                }
                            
                            # Use optimized matching if available
                            if self.optimized_searcher and sibling_name:
                                score = self.optimized_searcher.match_score(target_filename, sibling_name)
                                if score > best_score:
                                    best_score = score
                                    best_match = {
                                        'repo_id': model_id,
                                        'filename': sibling['rfilename'],
                                        'url': f"https://huggingface.co/{model_id}/resolve/main/{sibling['rfilename']}",
                                        'size': sibling.get('size', 0),
                                        'match_score': score,
                                        'model_info': {
                                            'downloads': model.get('downloads', 0),
                                            'likes': model.get('likes', 0),
                                            'tags': model.get('tags', []),
                                            'lastModified': model.get('lastModified', '')
                                        }
                                    }
                    
                    # Return best match if score is high enough
                    if best_match and best_score >= 0.7:
                        self.logger.info(f"Found fuzzy match for {target_filename}: {best_match['filename']} (score: {best_score:.2f})")
                        return best_match
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Search error for '{search_term}': {e}")
            return None
    
    async def get_model_info(self, repo_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific model.
        
        Args:
            repo_id: HuggingFace repository ID
            
        Returns:
            Model information dictionary
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.models_endpoint}/{repo_id}"
                
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
                    
        except Exception as e:
            self.logger.error(f"Failed to get model info for {repo_id}: {e}")
            return None
    
    async def check_file_exists(self, repo_id: str, filename: str) -> bool:
        """
        Check if a specific file exists in a repository.
        
        Args:
            repo_id: HuggingFace repository ID
            filename: Filename to check
            
        Returns:
            True if file exists
        """
        model_info = await self.get_model_info(repo_id)
        if not model_info:
            return False
        
        for sibling in model_info.get('siblings', []):
            if sibling.get('rfilename', '').lower() == filename.lower():
                return True
        
        return False
    
    def search_sync(self, filename: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Synchronous wrapper for search_model.
        
        Args:
            filename: Model filename to search for
            use_cache: Whether to use cached results
            
        Returns:
            Model information if found
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.search_model(filename, use_cache))
        finally:
            loop.close()
    
    def batch_search_sync(self, filenames: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Synchronous wrapper for batch_search.
        
        Args:
            filenames: List of model filenames
            
        Returns:
            Dictionary mapping filenames to search results
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.batch_search(filenames))
        finally:
            loop.close()