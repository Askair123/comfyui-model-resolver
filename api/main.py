"""
ComfyUI Model Resolver v2.0 - FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from pathlib import Path

from .routers import workflow, search, download, config
from .services.download_service import DownloadService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global download service instance
download_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global download_service
    
    # Startup
    logger.info("Starting ComfyUI Model Resolver API v2.0")
    
    # Initialize download service
    download_service = DownloadService()
    await download_service.start_worker()
    
    # Initialize data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")
    if download_service:
        download_service.is_running = False

# Create FastAPI app
app = FastAPI(
    title="ComfyUI Model Resolver API",
    description="API for analyzing ComfyUI workflows and managing model downloads",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflow.router)
app.include_router(search.router)
app.include_router(download.router)
app.include_router(config.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if the API is running."""
    return {"status": "healthy", "version": "2.0.0"}

# Root endpoint
@app.get("/")
async def root():
    """Welcome message."""
    return {
        "message": "ComfyUI Model Resolver API v2.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=5002,
        reload=True,
        log_level="info"
    )