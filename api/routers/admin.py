"""
Admin router for remote management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os

router = APIRouter(prefix="/api/admin", tags=["admin"])

class CommandRequest(BaseModel):
    command: str
    cwd: str = "/workspace"

class CommandResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int

@router.post("/execute", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """Execute a shell command (for debugging purposes)."""
    try:
        # Security: Only allow in development
        if os.getenv("ENVIRONMENT", "development") != "development":
            raise HTTPException(status_code=403, detail="Not allowed in production")
        
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=request.cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return CommandResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart-frontend")
async def restart_frontend():
    """Restart the frontend service."""
    try:
        # Kill existing frontend
        subprocess.run("pkill -f 'python app' || true", shell=True)
        
        # Start new frontend
        subprocess.run(
            "cd /workspace/frontend && GRADIO_SERVER_PORT=7861 nohup python app.py > frontend.log 2>&1 &",
            shell=True
        )
        
        return {"message": "Frontend restart initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))