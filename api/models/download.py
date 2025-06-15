"""
Download-related data models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DownloadStatus(str, Enum):
    """Download task status."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadRequest(BaseModel):
    """Download task request."""
    filename: str
    url: str
    target_path: str
    model_type: str = "unknown"
    size_bytes: Optional[int] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "cute_3d_cartoon.safetensors",
                "url": "https://civitai.com/api/download/models/xxxxx",
                "target_path": "/workspace/ComfyUI/models/loras/cute_3d_cartoon.safetensors",
                "model_type": "lora",
                "size_bytes": 150069504
            }
        }


class DownloadTask(BaseModel):
    """Download task information."""
    id: str
    filename: str
    url: str
    target_path: str
    status: DownloadStatus
    progress: float = Field(ge=0, le=100)
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DownloadResponse(BaseModel):
    """Download task creation response."""
    task_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "cute_3d_cartoon.safetensors_1705228200.123",
                "message": "Download task added to queue"
            }
        }


class DownloadStatusResponse(BaseModel):
    """Download queue status response."""
    queue_size: int
    active_downloads: List[DownloadTask]
    completed_recent: List[DownloadTask]
    total_completed: int
    total_failed: int


class BatchDownloadRequest(BaseModel):
    """Batch download request."""
    downloads: List[DownloadRequest]
    concurrent_limit: int = Field(default=3, ge=1, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "downloads": [{
                    "filename": "model1.safetensors",
                    "url": "https://example.com/model1",
                    "target_path": "/workspace/ComfyUI/models/loras/model1.safetensors",
                    "model_type": "lora"
                }],
                "concurrent_limit": 3
            }
        }


class BatchDownloadResponse(BaseModel):
    """Batch download response."""
    task_ids: List[str]
    total_tasks: int
    message: str