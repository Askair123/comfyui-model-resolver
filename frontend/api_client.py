"""
API Client for Gradio Frontend
"""

import httpx
from typing import List, Dict, Optional, Any
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with FastAPI backend."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def list_workflows(self, directory: str) -> List[Dict]:
        """Get list of workflows in a directory."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/workflow/list",
                params={"directory": directory}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return []
    
    async def analyze_workflows(self, paths: List[str]) -> Dict:
        """Analyze multiple workflows."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/workflow/analyze",
                json={"workflow_paths": paths, "check_local": True}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error analyzing workflows: {e}")
            return {
                "workflows": [],
                "models": [],
                "total_models": 0,
                "missing_models": 0,
                "analysis_time": 0
            }
    
    async def search_models(self, models: List[str]) -> Dict:
        """Search for models across platforms."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/search/models",
                json={"models": models}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return {
                "results": [],
                "total_searched": 0,
                "total_found": 0,
                "search_time": 0,
                "platforms_used": []
            }
    
    async def add_download(self, download_info: Dict) -> str:
        """Add a download to the queue."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/download/add",
                json=download_info
            )
            response.raise_for_status()
            return response.json()['task_id']
        except Exception as e:
            logger.error(f"Error adding download: {e}")
            return ""
    
    async def add_batch_download(self, downloads: List[Dict]) -> List[str]:
        """Add multiple downloads to the queue."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/download/batch",
                json={"downloads": downloads}
            )
            response.raise_for_status()
            return response.json()['task_ids']
        except Exception as e:
            logger.error(f"Error adding batch download: {e}")
            return []
    
    async def get_download_status(self) -> Dict:
        """Get current download queue status."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/download/status"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting download status: {e}")
            return {
                "queue_size": 0,
                "active_downloads": [],
                "completed_recent": []
            }
    
    async def pause_download(self, task_id: str) -> bool:
        """Pause a download."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/download/pause/{task_id}"
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error pausing download: {e}")
            return False
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel a download."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/download/cancel/{task_id}"
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error cancelling download: {e}")
            return False
    
    async def validate_url(self, url: str) -> Dict:
        """Validate a custom URL."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/search/validate-url",
                json={"url": url}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error validating URL: {e}")
            return {"valid": False, "error": str(e)}
    
    async def export_download_script(self, workflow_paths: List[str], 
                                   format: str = "bash") -> Dict:
        """Export download script for workflows."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/workflow/export-script",
                json={
                    "workflow_paths": workflow_paths,
                    "include_existing": False,
                    "output_format": format
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error exporting script: {e}")
            return {
                "script_content": "",
                "total_models": 0,
                "total_size_gb": 0,
                "output_format": format
            }
    
    async def get_config(self) -> Dict:
        """Get current configuration."""
        try:
            response = await self.client.get(f"{self.base_url}/api/config/")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return {}
    
    async def update_config(self, config: Dict) -> Dict:
        """Update configuration."""
        try:
            response = await self.client.put(
                f"{self.base_url}/api/config/",
                json=config
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if API is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False


# Synchronous wrapper for Gradio
class SyncAPIClient:
    """Synchronous wrapper for APIClient."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            self._client = APIClient(self.base_url)
        return self._client
    
    def _run_async(self, coro):
        """Run async function in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)
    
    def list_workflows(self, directory: str) -> List[Dict]:
        """Sync wrapper for list_workflows."""
        return self._run_async(self._get_client().list_workflows(directory))
    
    def analyze_workflows(self, paths: List[str]) -> Dict:
        """Sync wrapper for analyze_workflows."""
        return self._run_async(self._get_client().analyze_workflows(paths))
    
    def search_models(self, models: List[str]) -> Dict:
        """Sync wrapper for search_models."""
        return self._run_async(self._get_client().search_models(models))
    
    def add_download(self, download_info: Dict) -> str:
        """Sync wrapper for add_download."""
        return self._run_async(self._get_client().add_download(download_info))
    
    def add_batch_download(self, downloads: List[Dict]) -> List[str]:
        """Sync wrapper for add_batch_download."""
        return self._run_async(self._get_client().add_batch_download(downloads))
    
    def get_download_status(self) -> Dict:
        """Sync wrapper for get_download_status."""
        return self._run_async(self._get_client().get_download_status())
    
    def pause_download(self, task_id: str) -> bool:
        """Sync wrapper for pause_download."""
        return self._run_async(self._get_client().pause_download(task_id))
    
    def cancel_download(self, task_id: str) -> bool:
        """Sync wrapper for cancel_download."""
        return self._run_async(self._get_client().cancel_download(task_id))
    
    def validate_url(self, url: str) -> Dict:
        """Sync wrapper for validate_url."""
        return self._run_async(self._get_client().validate_url(url))
    
    def export_download_script(self, workflow_paths: List[str], 
                             format: str = "bash") -> Dict:
        """Sync wrapper for export_download_script."""
        return self._run_async(
            self._get_client().export_download_script(workflow_paths, format)
        )
    
    def get_config(self) -> Dict:
        """Sync wrapper for get_config."""
        return self._run_async(self._get_client().get_config())
    
    def update_config(self, config: Dict) -> Dict:
        """Sync wrapper for update_config."""
        return self._run_async(self._get_client().update_config(config))
    
    def health_check(self) -> bool:
        """Sync wrapper for health_check."""
        return self._run_async(self._get_client().health_check())