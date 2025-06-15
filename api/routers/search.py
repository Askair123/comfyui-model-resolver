"""
Search-related API endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Optional
import logging
import httpx
from urllib.parse import urlparse

from ..models.search import (
    SearchRequest, SearchResponse, SearchResult,
    ValidateUrlRequest, ValidateUrlResponse
)
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])

# Dependency to get search service
def get_search_service():
    return SearchService()

@router.post("/models", response_model=SearchResponse)
async def search_models(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    Search for models across multiple platforms.
    
    Returns download sources with recommendation ratings.
    """
    try:
        # Perform search
        result = await service.search_models(
            request.models,
            platforms=request.platforms,
            use_cache=request.use_cache
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error searching models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-url", response_model=ValidateUrlResponse)
async def validate_custom_url(
    request: ValidateUrlRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    Validate a custom download URL.
    
    Checks if the URL is accessible and returns file metadata.
    """
    try:
        # Parse URL
        parsed = urlparse(request.url)
        if not parsed.scheme or not parsed.netloc:
            return ValidateUrlResponse(
                valid=False,
                error="Invalid URL format"
            )
        
        # Validate URL
        result = await service.validate_url(request.url)
        return result
        
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return ValidateUrlResponse(
            valid=False,
            error=str(e)
        )


@router.get("/cached-results/{model_hash}", response_model=Optional[SearchResult])
async def get_cached_results(
    model_hash: str,
    service: SearchService = Depends(get_search_service)
):
    """
    Get cached search results for a model.
    
    Returns cached results if available, otherwise None.
    """
    try:
        # Get from cache
        result = await service.get_cached_result(model_hash)
        
        if result is None:
            raise HTTPException(status_code=404, detail="No cached results found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cached results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms", response_model=List[str])
async def list_available_platforms(
    service: SearchService = Depends(get_search_service)
):
    """
    List available search platforms.
    
    Returns platforms that are currently configured and available.
    """
    try:
        platforms = await service.get_available_platforms()
        return platforms
        
    except Exception as e:
        logger.error(f"Error listing platforms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-search/{filename}", response_model=SearchResult)
async def quick_search_single_model(
    filename: str,
    platform: Optional[str] = None,
    service: SearchService = Depends(get_search_service)
):
    """
    Quick search for a single model.
    
    Simplified endpoint for searching one model at a time.
    """
    try:
        # Perform search
        result = await service.quick_search(
            filename,
            platform=platform
        )
        
        if not result.sources:
            raise HTTPException(status_code=404, detail=f"No sources found for {filename}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick search: {e}")
        raise HTTPException(status_code=500, detail=str(e))