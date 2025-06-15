"""
Search Service - Business logic for model searching
"""

import os
import sys
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import logging
import hashlib

# Import from existing core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.integrations.multi_platform_searcher import MultiPlatformSearcher
from src.integrations.optimized_search import OptimizedModelSearcher
from src.utils.cache_manager import CacheManager

from ..models.search import (
    SearchResponse, SearchResult, ModelSource,
    ValidateUrlResponse, SearchPlatform
)

logger = logging.getLogger(__name__)


class SearchService:
    """Service for searching models across platforms."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        
        # Initialize searchers with API keys from environment
        civitai_token = os.getenv('CIVITAI_API_KEY')
        hf_token = os.getenv('HF_TOKEN')
        
        self.searcher = MultiPlatformSearcher(
            hf_token=hf_token,
            civitai_token=civitai_token,
            cache_manager=self.cache_manager
        )
        
        self.optimizer = OptimizedModelSearcher()
    
    async def search_models(self, models: List[str], 
                           platforms: List[SearchPlatform] = None,
                           use_cache: bool = True) -> SearchResponse:
        """Search for multiple models across platforms."""
        import time
        start_time = time.time()
        
        # Default to all platforms
        if not platforms:
            platforms = [SearchPlatform.HUGGINGFACE, SearchPlatform.CIVITAI]
        
        # Prepare model list
        model_list = [{'filename': m} for m in models]
        
        # Perform batch search
        search_results = await self.searcher.batch_search(model_list, max_concurrent=5)
        
        # Process results
        results = []
        total_found = 0
        
        for search_result in search_results:
            filename = search_result['filename']
            raw_result = search_result.get('search_result', {})
            
            sources = []
            
            # Process successful results
            if raw_result.get('found'):
                # Handle different result formats
                if 'sources' in raw_result:
                    # Multi-platform search result
                    for source in raw_result['sources']:
                        model_source = self._convert_to_model_source(source)
                        sources.append(model_source)
                else:
                    # Single platform result
                    model_source = self._convert_to_model_source(raw_result)
                    sources.append(model_source)
                
                total_found += 1
            
            # Sort sources by rating
            sources.sort(key=lambda x: x.rating, reverse=True)
            
            # Select best source by default
            selected_source = sources[0].url if sources else None
            
            # Add search strategy info
            strategy = raw_result.get('search_strategy', {})
            
            results.append(SearchResult(
                filename=filename,
                sources=sources,
                selected_source=selected_source,
                search_strategy=strategy
            ))
        
        # Get platforms actually used
        platforms_used = list(set(
            source.platform 
            for result in results 
            for source in result.sources
        ))
        
        return SearchResponse(
            results=results,
            total_searched=len(models),
            total_found=total_found,
            search_time=time.time() - start_time,
            platforms_used=platforms_used
        )
    
    def _convert_to_model_source(self, raw_source: Dict) -> ModelSource:
        """Convert raw search result to ModelSource."""
        # Calculate rating based on various factors
        rating = self._calculate_rating(raw_source)
        
        # Extract platform
        platform = raw_source.get('platform', 'unknown')
        if 'huggingface.co' in raw_source.get('url', ''):
            platform = 'huggingface'
        elif 'civitai.com' in raw_source.get('url', ''):
            platform = 'civitai'
        
        return ModelSource(
            url=raw_source.get('url', ''),
            platform=platform,
            name=raw_source.get('name', raw_source.get('filename', 'Unknown')),
            description=raw_source.get('description'),
            rating=rating,
            size_bytes=raw_source.get('size', raw_source.get('size_bytes')),
            download_count=raw_source.get('downloads', raw_source.get('download_count')),
            author=raw_source.get('author', raw_source.get('creator')),
            requires_auth=raw_source.get('requires_auth', False),
            metadata=raw_source.get('metadata', {})
        )
    
    def _calculate_rating(self, source: Dict) -> int:
        """Calculate recommendation rating (1-5 stars)."""
        rating = 3  # Default
        
        # Platform bonuses
        platform = source.get('platform', '')
        if platform == 'huggingface':
            # Official sources get bonus
            if any(org in source.get('url', '') for org in 
                   ['stabilityai/', 'black-forest-labs/', 'openai/']):
                rating = 5
            else:
                rating = 4
        elif platform == 'civitai':
            # High download count
            downloads = source.get('downloads', 0)
            if downloads > 10000:
                rating = 5
            elif downloads > 1000:
                rating = 4
        
        # Search strategy confidence
        strategy = source.get('search_strategy', {})
        if strategy.get('confidence') == 'high':
            rating = min(5, rating + 1)
        elif strategy.get('confidence') == 'low':
            rating = max(1, rating - 1)
        
        # Requires authentication penalty
        if source.get('requires_auth'):
            rating = max(1, rating - 1)
        
        return rating
    
    async def validate_url(self, url: str) -> ValidateUrlResponse:
        """Validate a custom URL."""
        async with httpx.AsyncClient() as client:
            try:
                # Send HEAD request
                response = await client.head(
                    url, 
                    follow_redirects=True,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    # Extract metadata
                    content_length = response.headers.get('content-length')
                    content_type = response.headers.get('content-type', '')
                    
                    # Extract filename from URL or headers
                    filename = None
                    if 'content-disposition' in response.headers:
                        # Parse filename from header
                        disposition = response.headers['content-disposition']
                        if 'filename=' in disposition:
                            filename = disposition.split('filename=')[-1].strip('"')
                    
                    if not filename:
                        # Get from URL
                        parsed = urlparse(url)
                        filename = os.path.basename(parsed.path)
                    
                    return ValidateUrlResponse(
                        valid=True,
                        size=int(content_length) if content_length else None,
                        filename=filename,
                        content_type=content_type
                    )
                else:
                    return ValidateUrlResponse(
                        valid=False,
                        error=f"HTTP {response.status_code}"
                    )
                    
            except Exception as e:
                return ValidateUrlResponse(
                    valid=False,
                    error=str(e)
                )
    
    async def get_cached_result(self, model_hash: str) -> Optional[SearchResult]:
        """Get cached search result."""
        cached = self.cache_manager.get(f"search_{model_hash}", cache_type='search')
        if cached:
            return SearchResult(**cached)
        return None
    
    async def get_available_platforms(self) -> List[str]:
        """Get list of available platforms."""
        platforms = ['huggingface']  # Always available
        
        if os.getenv('CIVITAI_API_KEY'):
            platforms.append('civitai')
        
        return platforms
    
    async def quick_search(self, filename: str, 
                          platform: Optional[str] = None) -> SearchResult:
        """Quick search for a single model."""
        # Use main search with single model
        if platform:
            platforms = [SearchPlatform(platform)]
        else:
            platforms = None
        
        response = await self.search_models([filename], platforms=platforms)
        
        if response.results:
            return response.results[0]
        
        # Return empty result
        return SearchResult(
            filename=filename,
            sources=[],
            selected_source=None
        )