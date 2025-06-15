"""
Model Downloader Module

Handles downloading models from various sources.
"""

import os
import asyncio
import aiohttp
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Callable
from urllib.parse import urlparse
import time
from concurrent.futures import ThreadPoolExecutor

from ..utils.logger import get_logger
from ..utils.config_loader import ConfigLoader


class DownloadProgress:
    """Tracks download progress."""
    
    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = time.time()
        
    @property
    def progress(self) -> float:
        """Get progress percentage."""
        if self.total_size == 0:
            return 0
        return (self.downloaded / self.total_size) * 100
    
    @property
    def speed(self) -> float:
        """Get download speed in MB/s."""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0
        return (self.downloaded / (1024 * 1024)) / elapsed


class ModelDownloader:
    """Downloads models from various sources."""
    
    def __init__(self, base_path: str = "/workspace/comfyui/models",
                 config: Optional[ConfigLoader] = None):
        """
        Initialize the model downloader.
        
        Args:
            base_path: Base directory for models
            config: Configuration loader
        """
        self.base_path = Path(base_path)
        self.config = config or ConfigLoader()
        self.logger = get_logger(__name__)
        
        # Download settings
        self.chunk_size = self.config.get('download.chunk_size_mb', 4) * 1024 * 1024
        self.max_concurrent = self.config.get('download.max_concurrent_downloads', 3)
        self.use_temp_files = self.config.get('download.use_temp_files', True)
        self.retry_attempts = self.config.get('download.retry_attempts', 3)
        self.retry_delay = self.config.get('download.retry_delay_seconds', 5)
        
        # Platform-specific headers
        self.headers = {
            'User-Agent': 'ComfyUI-Model-Resolver/1.0'
        }
        
        # Tokens
        self.hf_token = os.getenv('HF_TOKEN', '')
        self.civitai_token = os.getenv('CIVITAI_TOKEN', '')
    
    async def download_model(self, url: str, model_type: str, 
                           filename: str,
                           progress_callback: Optional[Callable] = None) -> bool:
        """
        Download a single model.
        
        Args:
            url: Download URL
            model_type: Model type for directory selection
            filename: Target filename
            progress_callback: Optional progress callback
            
        Returns:
            True if successful
        """
        # Determine target directory
        target_dir = self._get_model_directory(model_type)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = target_dir / filename
        
        # Check if already exists
        if output_path.exists():
            self.logger.info(f"File already exists: {filename}")
            return True
        
        # Determine platform and download
        platform = self._detect_platform(url)
        
        for attempt in range(self.retry_attempts):
            try:
                if platform == 'huggingface':
                    success = await self._download_huggingface(
                        url, output_path, progress_callback
                    )
                elif platform == 'civitai':
                    success = await self._download_civitai(
                        url, output_path, progress_callback
                    )
                elif platform == 'github':
                    success = await self._download_github(
                        url, output_path, progress_callback
                    )
                else:
                    success = await self._download_generic(
                        url, output_path, progress_callback
                    )
                
                if success:
                    self.logger.info(f"Successfully downloaded: {filename}")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
        
        return False
    
    async def batch_download(self, download_list: List[Dict],
                           progress_callback: Optional[Callable] = None) -> Dict:
        """
        Download multiple models concurrently.
        
        Args:
            download_list: List of download dictionaries
            progress_callback: Optional progress callback
            
        Returns:
            Results dictionary
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_with_semaphore(item):
            async with semaphore:
                success = await self.download_model(
                    item['url'],
                    item['type'],
                    item['name'],
                    progress_callback
                )
                return item['name'], success
        
        # Run downloads
        tasks = [download_with_semaphore(item) for item in download_list]
        results = await asyncio.gather(*tasks)
        
        # Compile results
        success_count = sum(1 for _, success in results if success)
        failed = [name for name, success in results if not success]
        
        return {
            'total': len(download_list),
            'success': success_count,
            'failed': failed,
            'results': dict(results)
        }
    
    def _detect_platform(self, url: str) -> str:
        """Detect the platform from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'huggingface.co' in domain:
            return 'huggingface'
        elif 'civitai.com' in domain:
            return 'civitai'
        elif 'github.com' in domain:
            return 'github'
        else:
            return 'generic'
    
    def _get_model_directory(self, model_type: str) -> Path:
        """Get the directory for a model type."""
        type_to_dir = {
            'checkpoint': 'checkpoints',
            'controlnet': 'controlnet',
            'lora': 'loras',
            'vae': 'vae',
            'upscale': 'upscale_models',
            'embeddings': 'embeddings',
            'clip': 'clip',
            'unet': 'unet'
        }
        
        dir_name = type_to_dir.get(model_type, model_type)
        return self.base_path / dir_name
    
    async def _download_huggingface(self, url: str, output_path: Path,
                                   progress_callback: Optional[Callable] = None) -> bool:
        """Download from HuggingFace."""
        headers = self.headers.copy()
        if self.hf_token:
            headers['Authorization'] = f'Bearer {self.hf_token}'
        
        return await self._download_with_progress(
            url, output_path, headers, progress_callback
        )
    
    async def _download_civitai(self, url: str, output_path: Path,
                               progress_callback: Optional[Callable] = None) -> bool:
        """Download from Civitai."""
        headers = self.headers.copy()
        if self.civitai_token:
            headers['Authorization'] = f'Bearer {self.civitai_token}'
        
        return await self._download_with_progress(
            url, output_path, headers, progress_callback
        )
    
    async def _download_github(self, url: str, output_path: Path,
                             progress_callback: Optional[Callable] = None) -> bool:
        """Download from GitHub."""
        # GitHub releases may redirect
        headers = self.headers.copy()
        headers['Accept'] = 'application/octet-stream'
        
        return await self._download_with_progress(
            url, output_path, headers, progress_callback
        )
    
    async def _download_generic(self, url: str, output_path: Path,
                              progress_callback: Optional[Callable] = None) -> bool:
        """Generic download method."""
        return await self._download_with_progress(
            url, output_path, self.headers, progress_callback
        )
    
    async def _download_with_progress(self, url: str, output_path: Path,
                                    headers: Dict, 
                                    progress_callback: Optional[Callable] = None) -> bool:
        """Download with progress tracking."""
        temp_path = output_path.with_suffix('.tmp') if self.use_temp_files else output_path
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    
                    # Get total size
                    total_size = int(response.headers.get('Content-Length', 0))
                    progress = DownloadProgress(total_size)
                    
                    # Download with progress
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            f.write(chunk)
                            progress.downloaded += len(chunk)
                            
                            if progress_callback:
                                progress_callback(
                                    filename=output_path.name,
                                    progress=progress.progress,
                                    speed=progress.speed,
                                    downloaded=progress.downloaded,
                                    total=total_size
                                )
            
            # Move temp file to final location
            if self.use_temp_files:
                temp_path.rename(output_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            # Clean up temp file
            if temp_path.exists() and self.use_temp_files:
                temp_path.unlink()
            return False
    
    def download_sync(self, url: str, model_type: str, filename: str) -> bool:
        """
        Synchronous wrapper for download_model.
        
        Args:
            url: Download URL
            model_type: Model type
            filename: Target filename
            
        Returns:
            True if successful
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.download_model(url, model_type, filename)
            )
        finally:
            loop.close()
    
    def batch_download_sync(self, download_list: List[Dict]) -> Dict:
        """
        Synchronous wrapper for batch_download.
        
        Args:
            download_list: List of download dictionaries
            
        Returns:
            Results dictionary
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.batch_download(download_list)
            )
        finally:
            loop.close()
    
    def download_with_wget(self, url: str, output_path: Path) -> bool:
        """
        Download using wget command (fallback method).
        
        Args:
            url: Download URL
            output_path: Output file path
            
        Returns:
            True if successful
        """
        cmd = ['wget', '-q', '--show-progress', url, '-O', str(output_path)]
        
        # Add authentication if needed
        if 'huggingface.co' in url and self.hf_token:
            cmd.extend(['--header', f'Authorization: Bearer {self.hf_token}'])
        elif 'civitai.com' in url and self.civitai_token:
            cmd.extend(['--header', f'Authorization: Bearer {self.civitai_token}'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"wget download failed: {e}")
            return False