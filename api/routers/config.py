"""
Configuration-related API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import os
import json
from pathlib import Path
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])

# Configuration models
class ConfigUpdate(BaseModel):
    """Configuration update request."""
    civitai_api_key: Optional[str] = None
    huggingface_token: Optional[str] = None
    comfyui_root: Optional[str] = None
    models_dir: Optional[str] = None
    auto_skip_existing: Optional[bool] = None
    verify_downloads: Optional[bool] = None
    max_concurrent_downloads: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "civitai_api_key": "your-api-key",
                "comfyui_root": "/workspace/ComfyUI",
                "auto_skip_existing": True
            }
        }


class ConfigResponse(BaseModel):
    """Configuration response."""
    civitai_api_key: Optional[str]
    huggingface_token: Optional[str]
    comfyui_root: str
    models_dir: str
    auto_skip_existing: bool
    verify_downloads: bool
    max_concurrent_downloads: int
    config_file: str


# Config file path
CONFIG_FILE = Path("data/config.json")


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    
    # Default configuration
    return {
        "civitai_api_key": os.getenv("CIVITAI_API_KEY"),
        "huggingface_token": os.getenv("HF_TOKEN"),
        "comfyui_root": "/workspace/ComfyUI",
        "models_dir": "/workspace/ComfyUI/models",
        "auto_skip_existing": True,
        "verify_downloads": False,
        "max_concurrent_downloads": 3
    }


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    Get current configuration.
    
    Returns all configuration values (API keys are masked).
    """
    try:
        config = load_config()
        
        # Mask sensitive values
        masked_config = config.copy()
        if masked_config.get("civitai_api_key"):
            masked_config["civitai_api_key"] = "***" + masked_config["civitai_api_key"][-4:]
        if masked_config.get("huggingface_token"):
            masked_config["huggingface_token"] = "***" + masked_config["huggingface_token"][-4:]
        
        return ConfigResponse(
            **masked_config,
            config_file=str(CONFIG_FILE)
        )
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    """
    Update configuration values.
    
    Only provided values will be updated.
    """
    try:
        # Load current config
        config = load_config()
        
        # Update only provided values
        update_dict = update.dict(exclude_none=True)
        config.update(update_dict)
        
        # Validate paths
        if "comfyui_root" in update_dict:
            if not os.path.exists(config["comfyui_root"]):
                raise HTTPException(
                    status_code=400, 
                    detail=f"ComfyUI root not found: {config['comfyui_root']}"
                )
        
        # Save updated config
        save_config(config)
        
        # Return masked config
        return await get_config()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_config():
    """
    Reset configuration to defaults.
    """
    try:
        # Remove config file
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        
        return {"message": "Configuration reset to defaults"}
        
    except Exception as e:
        logger.error(f"Error resetting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-paths", response_model=Dict[str, str])
async def get_model_paths():
    """
    Get configured model directory paths.
    
    Returns paths for each model type.
    """
    try:
        config = load_config()
        models_dir = Path(config["models_dir"])
        
        # Standard ComfyUI model directories
        model_paths = {
            "checkpoints": str(models_dir / "checkpoints"),
            "clip": str(models_dir / "clip"),
            "clip_vision": str(models_dir / "clip_vision"),
            "controlnet": str(models_dir / "controlnet"),
            "loras": str(models_dir / "loras"),
            "upscale_models": str(models_dir / "upscale_models"),
            "vae": str(models_dir / "vae"),
            "embeddings": str(models_dir / "embeddings"),
            "hypernetworks": str(models_dir / "hypernetworks"),
            "unet": str(models_dir / "unet"),
            "ipadapter": str(models_dir / "ipadapter"),
            "instantid": str(models_dir / "instantid")
        }
        
        return model_paths
        
    except Exception as e:
        logger.error(f"Error getting model paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))