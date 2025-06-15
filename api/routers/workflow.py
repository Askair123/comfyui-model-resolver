"""
Workflow-related API endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import os
import json
from pathlib import Path
import logging

from ..models.workflow import (
    WorkflowModel, ModelInfo, AnalyzeRequest, AnalyzeResponse,
    ExportScriptRequest, ExportScriptResponse, WorkflowStatus
)
from ..services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Dependency to get workflow service
def get_workflow_service():
    return WorkflowService()

@router.get("/list", response_model=List[WorkflowModel])
async def list_workflows(
    directory: str = Query(..., description="Workflow directory path"),
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    List all workflows in a directory.
    
    Returns workflow files with their analysis status.
    """
    try:
        # Validate directory
        if not os.path.exists(directory):
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")
        
        if not os.path.isdir(directory):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {directory}")
        
        # Scan directory
        workflows = await service.scan_directory(directory)
        return workflows
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_workflows(
    request: AnalyzeRequest,
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Analyze workflows to extract model requirements.
    
    Returns detailed model information for each workflow.
    """
    try:
        # Validate workflow paths
        for path in request.workflow_paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Workflow not found: {path}")
        
        # Analyze workflows
        result = await service.analyze_workflows(
            request.workflow_paths,
            check_local=request.check_local
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{workflow_path:path}", response_model=WorkflowModel)
async def get_workflow_status(
    workflow_path: str,
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get the status of a single workflow.
    
    Returns workflow analysis status from cache or performs new analysis.
    """
    try:
        # Validate path
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_path}")
        
        # Get status
        status = await service.get_workflow_status(workflow_path)
        return status
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-script", response_model=ExportScriptResponse)
async def export_download_script(
    request: ExportScriptRequest,
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Export a download script for workflow models.
    
    Generates a script in the requested format (bash, powershell, python).
    """
    try:
        # Validate workflow paths
        for path in request.workflow_paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Workflow not found: {path}")
        
        # Generate script
        script = await service.export_download_script(
            request.workflow_paths,
            include_existing=request.include_existing,
            output_format=request.output_format
        )
        
        return script
        
    except Exception as e:
        logger.error(f"Error exporting script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{workflow_path:path}", response_model=List[ModelInfo])
async def get_workflow_models(
    workflow_path: str,
    service: WorkflowService = Depends(get_workflow_service)
):
    """
    Get the list of models required by a workflow.
    
    Returns detailed information about each model.
    """
    try:
        # Validate path
        if not os.path.exists(workflow_path):
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_path}")
        
        # Get models
        models = await service.get_workflow_models(workflow_path)
        return models
        
    except Exception as e:
        logger.error(f"Error getting workflow models: {e}")
        raise HTTPException(status_code=500, detail=str(e))