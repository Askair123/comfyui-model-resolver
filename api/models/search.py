"""
Search-related data models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class SearchPlatform(str, Enum):
    """Supported search platforms."""
    HUGGINGFACE = "huggingface"
    CIVITAI = "civitai"
    GITHUB = "github"
    ALL = "all"


class SearchRequest(BaseModel):
    """Model search request."""
    models: List[str]
    platforms: List[SearchPlatform] = [SearchPlatform.HUGGINGFACE, SearchPlatform.CIVITAI]
    use_cache: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "models": [
                    "cute_3d_cartoon.safetensors",
                    "detail_tweaker_xl.safetensors"
                ],
                "platforms": ["huggingface", "civitai"],
                "use_cache": True
            }
        }


class ModelSource(BaseModel):
    """Model download source."""
    url: str
    platform: str
    name: str
    description: Optional[str] = None
    rating: int = Field(ge=1, le=5, description="Recommendation rating (1-5 stars)")
    size_bytes: Optional[int] = None
    download_count: Optional[int] = None
    author: Optional[str] = None
    requires_auth: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Search result for a model."""
    filename: str
    sources: List[ModelSource]
    selected_source: Optional[str] = None
    custom_url: Optional[str] = None
    search_strategy: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "cute_3d_cartoon.safetensors",
                "sources": [{
                    "url": "https://civitai.com/api/download/models/xxxxx",
                    "platform": "civitai",
                    "name": "Cute 3D Cartoon Style for Flux",
                    "rating": 5,
                    "size_bytes": 150069504,
                    "download_count": 12543,
                    "author": "CivitaiUser123"
                }],
                "selected_source": "https://civitai.com/api/download/models/xxxxx",
                "custom_url": None
            }
        }


class SearchResponse(BaseModel):
    """Search response for multiple models."""
    results: List[SearchResult]
    total_searched: int
    total_found: int
    search_time: float
    platforms_used: List[str]


class ValidateUrlRequest(BaseModel):
    """URL validation request."""
    url: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"
            }
        }


class ValidateUrlResponse(BaseModel):
    """URL validation response."""
    valid: bool
    size: Optional[int] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    error: Optional[str] = None