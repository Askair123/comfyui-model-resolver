"""
Workflow-related data models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow status enum."""
    READY = "ready"
    PARTIAL = "partial"
    MISSING = "missing"
    UNANALYZED = "unanalyzed"


class WorkflowModel(BaseModel):
    """Workflow model."""
    path: str
    name: str
    status: WorkflowStatus
    total_models: int = 0
    missing_count: int = 0
    last_analyzed: Optional[datetime] = None
    size_bytes: Optional[int] = None


class ModelInfo(BaseModel):
    """Model information."""
    filename: str
    model_type: str = "unknown"
    exists_locally: bool = False
    size: Optional[int] = None
    local_path: Optional[str] = None
    selected: bool = False
    detection_sources: List[str] = Field(default_factory=list)
    node_types: List[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """Workflow analysis request."""
    workflow_paths: List[str]
    check_local: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_paths": [
                    "/workspace/ComfyUI/workflows/flux_portrait.json",
                    "/workspace/ComfyUI/workflows/sdxl_anime.json"
                ],
                "check_local": True
            }
        }


class AnalyzeResponse(BaseModel):
    """Workflow analysis response."""
    workflows: List[WorkflowModel]
    models: List[ModelInfo]
    total_models: int
    missing_models: int
    analysis_time: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflows": [{
                    "path": "/workspace/ComfyUI/workflows/flux_portrait.json",
                    "name": "flux_portrait.json",
                    "status": "partial",
                    "total_models": 8,
                    "missing_count": 2,
                    "last_analyzed": "2024-01-14T10:30:00"
                }],
                "models": [{
                    "filename": "flux1-dev-Q4_0.gguf",
                    "model_type": "unet",
                    "exists_locally": True,
                    "size": 6871947673,
                    "local_path": "/workspace/ComfyUI/models/unet/flux1-dev-Q4_0.gguf",
                    "selected": False
                }],
                "total_models": 8,
                "missing_models": 2,
                "analysis_time": 0.523
            }
        }


class ExportScriptRequest(BaseModel):
    """Export download script request."""
    workflow_paths: List[str]
    include_existing: bool = False
    output_format: str = "bash"  # bash, powershell, python
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_paths": ["/workspace/ComfyUI/workflows/flux_portrait.json"],
                "include_existing": False,
                "output_format": "bash"
            }
        }


class ExportScriptResponse(BaseModel):
    """Export download script response."""
    script_content: str
    total_models: int
    total_size_gb: float
    output_format: str