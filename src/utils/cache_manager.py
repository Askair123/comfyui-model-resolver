"""
Cache Manager Module

Manages caching for search results and other data.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import pickle


class CacheManager:
    """Manages application caching with TTL support."""
    
    def __init__(self, cache_dir: Optional[str] = None,
                default_ttl_hours: int = 168):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Cache directory path
            default_ttl_hours: Default time-to-live in hours
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "comfyui-model-resolver"
        self.default_ttl = timedelta(hours=default_ttl_hours)
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Different cache files for different purposes
        self.search_cache_file = self.cache_dir / "search_cache.json"
        self.model_cache_file = self.cache_dir / "model_cache.json"
        self.general_cache_file = self.cache_dir / "general_cache.json"
    
    def _get_cache_key(self, key: Union[str, dict]) -> str:
        """
        Generate a cache key from input.
        
        Args:
            key: Key string or dictionary
            
        Returns:
            Hashed cache key
        """
        if isinstance(key, dict):
            # Sort keys for consistent hashing
            key_str = json.dumps(key, sort_keys=True)
        else:
            key_str = str(key)
        
        # Create hash for long keys
        if len(key_str) > 50:
            return hashlib.md5(key_str.encode()).hexdigest()
        return key_str
    
    def get(self, key: Union[str, dict], cache_type: str = "general") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache (search, model, general)
            
        Returns:
            Cached value or None if not found or expired
        """
        cache_file = self._get_cache_file(cache_type)
        cache_key = self._get_cache_key(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if cache_key not in cache_data:
                return None
            
            entry = cache_data[cache_key]
            
            # Check expiration
            expires_at = datetime.fromisoformat(entry['expires_at'])
            if datetime.now() > expires_at:
                # Remove expired entry
                self._remove_entry(cache_key, cache_type)
                return None
            
            return entry['value']
            
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
    
    def set(self, key: Union[str, dict], value: Any, 
            cache_type: str = "general",
            ttl_hours: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache
            ttl_hours: Time-to-live in hours (uses default if None)
        """
        cache_file = self._get_cache_file(cache_type)
        cache_key = self._get_cache_key(key)
        
        # Calculate expiration
        ttl = timedelta(hours=ttl_hours) if ttl_hours else self.default_ttl
        expires_at = datetime.now() + ttl
        
        # Load existing cache or create new
        try:
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
            else:
                cache_data = {}
        except:
            cache_data = {}
        
        # Add entry
        cache_data[cache_key] = {
            'value': value,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Save cache
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")
    
    def delete(self, key: Union[str, dict], cache_type: str = "general"):
        """Delete a specific cache entry."""
        cache_key = self._get_cache_key(key)
        self._remove_entry(cache_key, cache_type)
    
    def clear(self, cache_type: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            cache_type: Specific cache type to clear, or None for all
        """
        if cache_type:
            cache_file = self._get_cache_file(cache_type)
            if cache_file.exists():
                cache_file.unlink()
        else:
            # Clear all caches
            for cache_file in [self.search_cache_file, 
                             self.model_cache_file, 
                             self.general_cache_file]:
                if cache_file.exists():
                    cache_file.unlink()
    
    def cleanup_expired(self):
        """Remove all expired entries from all caches."""
        for cache_type in ['search', 'model', 'general']:
            self._cleanup_cache_file(cache_type)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'cache_dir': str(self.cache_dir),
            'caches': {}
        }
        
        for cache_type in ['search', 'model', 'general']:
            cache_file = self._get_cache_file(cache_type)
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    total_entries = len(cache_data)
                    expired_entries = 0
                    
                    for entry in cache_data.values():
                        expires_at = datetime.fromisoformat(entry['expires_at'])
                        if datetime.now() > expires_at:
                            expired_entries += 1
                    
                    stats['caches'][cache_type] = {
                        'file': str(cache_file),
                        'size_kb': cache_file.stat().st_size / 1024,
                        'total_entries': total_entries,
                        'expired_entries': expired_entries,
                        'active_entries': total_entries - expired_entries
                    }
                except Exception as e:
                    stats['caches'][cache_type] = {'error': f'Failed to read cache: {str(e)}'}
            else:
                stats['caches'][cache_type] = {'status': 'not_found'}
        
        return stats
    
    def _get_cache_file(self, cache_type: str) -> Path:
        """Get the cache file path for a specific cache type."""
        cache_files = {
            'search': self.search_cache_file,
            'model': self.model_cache_file,
            'general': self.general_cache_file
        }
        return cache_files.get(cache_type, self.general_cache_file)
    
    def _remove_entry(self, cache_key: str, cache_type: str):
        """Remove a specific entry from cache."""
        cache_file = self._get_cache_file(cache_type)
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if cache_key in cache_data:
                del cache_data[cache_key]
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
        except:
            pass
    
    def _cleanup_cache_file(self, cache_type: str):
        """Remove expired entries from a specific cache file."""
        cache_file = self._get_cache_file(cache_type)
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Filter out expired entries
            now = datetime.now()
            cleaned_data = {}
            
            for key, entry in cache_data.items():
                expires_at = datetime.fromisoformat(entry['expires_at'])
                if now <= expires_at:
                    cleaned_data[key] = entry
            
            # Save cleaned cache
            with open(cache_file, 'w') as f:
                json.dump(cleaned_data, f, indent=2)
                
        except Exception as e:
            print(f"Cache cleanup error: {e}")


class BinaryCache(CacheManager):
    """Cache manager for binary data using pickle."""
    
    def __init__(self, cache_dir: Optional[str] = None,
                default_ttl_hours: int = 168):
        """Initialize binary cache manager."""
        super().__init__(cache_dir, default_ttl_hours)
        self.binary_cache_dir = self.cache_dir / "binary"
        self.binary_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_binary(self, key: str) -> Optional[Any]:
        """Get binary data from cache."""
        cache_key = self._get_cache_key(key)
        cache_file = self.binary_cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            # Check expiration
            if datetime.now() > data['expires_at']:
                cache_file.unlink()
                return None
            
            return data['value']
        except:
            return None
    
    def set_binary(self, key: str, value: Any, ttl_hours: Optional[int] = None):
        """Set binary data in cache."""
        cache_key = self._get_cache_key(key)
        cache_file = self.binary_cache_dir / f"{cache_key}.pkl"
        
        ttl = timedelta(hours=ttl_hours) if ttl_hours else self.default_ttl
        expires_at = datetime.now() + ttl
        
        data = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Binary cache write error: {e}")