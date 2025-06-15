"""
Download Service - Business logic for download queue management
"""

import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
import aiofiles
import os
from datetime import datetime
from pathlib import Path
import logging
import hashlib
from dataclasses import dataclass, field
from enum import Enum

from ..models.download import DownloadStatus, DownloadTask, DownloadStatusResponse

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Track download progress."""
    task_id: str
    filename: str
    url: str
    target_path: str
    status: DownloadStatus = DownloadStatus.QUEUED
    progress: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_download_task(self) -> DownloadTask:
        """Convert to DownloadTask model."""
        return DownloadTask(
            id=self.task_id,
            filename=self.filename,
            url=self.url,
            target_path=self.target_path,
            status=self.status,
            progress=self.progress,
            speed_mbps=self.speed_mbps,
            eta_seconds=self.eta_seconds,
            downloaded_bytes=self.downloaded_bytes,
            total_bytes=self.total_bytes,
            error=self.error,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at
        )


class DownloadService:
    """Service for managing model downloads."""
    
    def __init__(self):
        self.download_queue = asyncio.Queue()
        self.active_downloads: Dict[str, DownloadProgress] = {}
        self.completed_downloads: List[DownloadProgress] = []
        self.is_running = False
        self.worker_task = None
        self.pause_events: Dict[str, asyncio.Event] = {}
        self.cancel_events: Dict[str, bool] = {}
    
    async def start_worker(self):
        """Start the download worker."""
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("Download worker started")
    
    async def stop_worker(self):
        """Stop the download worker."""
        self.is_running = False
        if self.worker_task:
            await self.worker_task
            logger.info("Download worker stopped")
    
    async def _worker(self):
        """Background worker to process downloads."""
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.download_queue.get(),
                    timeout=1.0
                )
                
                # Process download
                await self._process_download(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    async def add_to_queue(self, download_info: Dict) -> str:
        """Add a download to the queue."""
        # Generate task ID
        task_id = f"{download_info['filename']}_{datetime.now().timestamp()}"
        
        # Create progress tracker
        progress = DownloadProgress(
            task_id=task_id,
            filename=download_info['filename'],
            url=download_info['url'],
            target_path=download_info['target_path'],
            total_bytes=download_info.get('size_bytes')
        )
        
        # Add to queue
        download_info['task_id'] = task_id
        await self.download_queue.put(download_info)
        
        logger.info(f"Added to queue: {download_info['filename']}")
        return task_id
    
    async def _process_download(self, task: Dict):
        """Process a single download task."""
        task_id = task['task_id']
        
        # Create progress tracker
        progress = DownloadProgress(
            task_id=task_id,
            filename=task['filename'],
            url=task['url'],
            target_path=task['target_path'],
            total_bytes=task.get('size_bytes'),
            status=DownloadStatus.DOWNLOADING,
            started_at=datetime.now()
        )
        
        self.active_downloads[task_id] = progress
        
        # Create pause event
        self.pause_events[task_id] = asyncio.Event()
        self.pause_events[task_id].set()  # Not paused initially
        
        try:
            # Ensure target directory exists
            os.makedirs(os.path.dirname(task['target_path']), exist_ok=True)
            
            # Download file
            await self._download_file(
                task['url'],
                task['target_path'],
                task_id,
                custom_headers=task.get('custom_headers', {})
            )
            
            # Mark as completed
            progress.status = DownloadStatus.COMPLETED
            progress.completed_at = datetime.now()
            progress.progress = 100.0
            
            self.completed_downloads.append(progress)
            logger.info(f"Download completed: {task['filename']}")
            
        except asyncio.CancelledError:
            progress.status = DownloadStatus.CANCELLED
            progress.error = "Download cancelled"
            self.completed_downloads.append(progress)
            logger.info(f"Download cancelled: {task['filename']}")
            
        except Exception as e:
            progress.status = DownloadStatus.FAILED
            progress.error = str(e)
            progress.completed_at = datetime.now()
            self.completed_downloads.append(progress)
            logger.error(f"Download failed: {task['filename']} - {e}")
            
        finally:
            # Cleanup
            self.active_downloads.pop(task_id, None)
            self.pause_events.pop(task_id, None)
            self.cancel_events.pop(task_id, None)
    
    async def _download_file(self, url: str, target_path: str, 
                           task_id: str, custom_headers: Dict = None):
        """Download a file with progress tracking."""
        headers = custom_headers or {}
        
        # Check if file already exists
        if os.path.exists(target_path):
            file_size = os.path.getsize(target_path)
            headers['Range'] = f'bytes={file_size}-'
            mode = 'ab'
            initial_size = file_size
        else:
            mode = 'wb'
            initial_size = 0
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                # Check if partial content is supported
                if response.status == 206:
                    logger.info(f"Resuming download from {initial_size} bytes")
                elif response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                # Get total size
                total_size = int(response.headers.get('content-length', 0))
                if response.status == 206:
                    # Partial content
                    content_range = response.headers.get('content-range', '')
                    if '/' in content_range:
                        total_size = int(content_range.split('/')[-1])
                
                # Update progress
                progress = self.active_downloads[task_id]
                progress.total_bytes = total_size
                progress.downloaded_bytes = initial_size
                
                # Download with progress
                chunk_size = 8192
                start_time = asyncio.get_event_loop().time()
                last_update = start_time
                
                async with aiofiles.open(target_path, mode) as file:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        # Check for cancellation
                        if self.cancel_events.get(task_id):
                            raise asyncio.CancelledError()
                        
                        # Wait if paused
                        await self.pause_events[task_id].wait()
                        
                        # Write chunk
                        await file.write(chunk)
                        progress.downloaded_bytes += len(chunk)
                        
                        # Update progress
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_update >= 0.5:  # Update every 0.5s
                            # Calculate progress
                            if total_size > 0:
                                progress.progress = (progress.downloaded_bytes / total_size) * 100
                            
                            # Calculate speed
                            elapsed = current_time - start_time
                            if elapsed > 0:
                                speed_bps = (progress.downloaded_bytes - initial_size) / elapsed
                                progress.speed_mbps = (speed_bps * 8) / (1024 * 1024)
                                
                                # Calculate ETA
                                if speed_bps > 0 and total_size > progress.downloaded_bytes:
                                    remaining_bytes = total_size - progress.downloaded_bytes
                                    progress.eta_seconds = int(remaining_bytes / speed_bps)
                            
                            last_update = current_time
    
    async def get_status(self) -> Dict:
        """Get download queue status."""
        return {
            "queue_size": self.download_queue.qsize(),
            "active": [
                progress.to_download_task()
                for progress in self.active_downloads.values()
            ],
            "completed": [
                progress.to_download_task()
                for progress in self.completed_downloads[-10:]  # Last 10
            ]
        }
    
    async def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get status of a specific task."""
        # Check active
        if task_id in self.active_downloads:
            return self.active_downloads[task_id].to_download_task()
        
        # Check completed
        for progress in self.completed_downloads:
            if progress.task_id == task_id:
                return progress.to_download_task()
        
        return None
    
    async def pause_download(self, task_id: str) -> bool:
        """Pause a download."""
        if task_id in self.pause_events:
            self.pause_events[task_id].clear()
            if task_id in self.active_downloads:
                self.active_downloads[task_id].status = DownloadStatus.PAUSED
            return True
        return False
    
    async def resume_download(self, task_id: str) -> bool:
        """Resume a paused download."""
        if task_id in self.pause_events:
            self.pause_events[task_id].set()
            if task_id in self.active_downloads:
                self.active_downloads[task_id].status = DownloadStatus.DOWNLOADING
            return True
        return False
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel a download."""
        if task_id in self.active_downloads:
            self.cancel_events[task_id] = True
            return True
        return False