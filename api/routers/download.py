"""
Download-related API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional
import logging
import asyncio
import json

from ..models.download import (
    DownloadRequest, DownloadResponse, DownloadTask,
    DownloadStatusResponse, BatchDownloadRequest, BatchDownloadResponse
)
from ..services.download_service import DownloadService
# from ..main import download_service as global_download_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/download", tags=["download"])

# Dependency to get download service
def get_download_service():
    return global_download_service

@router.post("/add", response_model=DownloadResponse)
async def add_download(
    request: DownloadRequest,
    service: DownloadService = Depends(get_download_service)
):
    """
    Add a model to the download queue.
    
    Returns a task ID for tracking the download.
    """
    try:
        # Add to queue
        task_id = await service.add_to_queue({
            'filename': request.filename,
            'url': request.url,
            'target_path': request.target_path,
            'model_type': request.model_type,
            'size_bytes': request.size_bytes,
            'custom_headers': request.custom_headers
        })
        
        return DownloadResponse(
            task_id=task_id,
            message="Download task added to queue"
        )
        
    except Exception as e:
        logger.error(f"Error adding download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchDownloadResponse)
async def add_batch_download(
    request: BatchDownloadRequest,
    service: DownloadService = Depends(get_download_service)
):
    """
    Add multiple models to the download queue.
    
    Returns task IDs for all downloads.
    """
    try:
        task_ids = []
        
        # Add each download to queue
        for download in request.downloads:
            task_id = await service.add_to_queue({
                'filename': download.filename,
                'url': download.url,
                'target_path': download.target_path,
                'model_type': download.model_type,
                'size_bytes': download.size_bytes,
                'custom_headers': download.custom_headers
            })
            task_ids.append(task_id)
        
        return BatchDownloadResponse(
            task_ids=task_ids,
            total_tasks=len(task_ids),
            message=f"Added {len(task_ids)} downloads to queue"
        )
        
    except Exception as e:
        logger.error(f"Error adding batch download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=DownloadStatusResponse)
async def get_download_status(
    service: DownloadService = Depends(get_download_service)
):
    """
    Get the current download queue status.
    
    Returns active downloads, queue size, and recent completions.
    """
    try:
        status = await service.get_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting download status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}", response_model=DownloadTask)
async def get_task_status(
    task_id: str,
    service: DownloadService = Depends(get_download_service)
):
    """
    Get the status of a specific download task.
    
    Returns detailed task information.
    """
    try:
        task = await service.get_task_status(task_id)
        
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause/{task_id}")
async def pause_download(
    task_id: str,
    service: DownloadService = Depends(get_download_service)
):
    """
    Pause a specific download task.
    """
    try:
        success = await service.pause_download(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task not found or not active: {task_id}")
        
        return {"message": f"Download paused: {task_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/{task_id}")
async def resume_download(
    task_id: str,
    service: DownloadService = Depends(get_download_service)
):
    """
    Resume a paused download task.
    """
    try:
        success = await service.resume_download(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task not found or not paused: {task_id}")
        
        return {"message": f"Download resumed: {task_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{task_id}")
async def cancel_download(
    task_id: str,
    service: DownloadService = Depends(get_download_service)
):
    """
    Cancel a download task.
    """
    try:
        success = await service.cancel_download(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        return {"message": f"Download cancelled: {task_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/progress")
async def download_progress_websocket(
    websocket: WebSocket,
    service: DownloadService = Depends(get_download_service)
):
    """
    WebSocket endpoint for real-time download progress updates.
    """
    await websocket.accept()
    
    try:
        while True:
            # Get current status
            status = await service.get_status()
            
            # Send update
            await websocket.send_json({
                "type": "progress",
                "data": {
                    "queue_size": status["queue_size"],
                    "active": status["active"],
                    "completed_recent": status["completed"][-5:]  # Last 5
                }
            })
            
            # Wait before next update
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()