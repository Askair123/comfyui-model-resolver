"""
Multi-Platform Model Searcher

Intelligently routes searches between HuggingFace and Civitai based on model characteristics.
"""

import asyncio
from typing import List, Dict, Optional, Tuple
import re

from .hf_searcher import HuggingFaceSearcher
from .civitai_searcher import CivitaiSearcher
from .optimized_search import OptimizedModelSearcher
from ..utils.cache_manager import CacheManager
from ..utils.logger import get_logger


class MultiPlatformSearcher:
    """Searches across multiple platforms with intelligent routing."""
    
    def __init__(self, 
                 hf_token: Optional[str] = None,
                 civitai_token: Optional[str] = None,
                 cache_manager: Optional[CacheManager] = None):
        """
        Initialize the multi-platform searcher.
        
        Args:
            hf_token: HuggingFace API token (optional)
            civitai_token: Civitai API token
            cache_manager: Shared cache manager
        """
        self.cache_manager = cache_manager or CacheManager()
        self.logger = get_logger(__name__)
        
        # Initialize searchers
        self.hf_searcher = HuggingFaceSearcher(
            cache_manager=self.cache_manager,
            api_token=hf_token
        )
        
        self.civitai_searcher = None
        if civitai_token:
            self.civitai_searcher = CivitaiSearcher(
                api_key=civitai_token,
                cache_manager=self.cache_manager
            )
        
        self.optimized_searcher = OptimizedModelSearcher()
    
    def identify_model_type_and_platform(self, filename: str) -> Dict:
        """
        Identify model type and recommend search platforms.
        
        Args:
            filename: Model filename
            
        Returns:
            Dictionary with type, platform priority, and strategy
        """
        filename_lower = filename.lower()
        
        # Parse model components
        components = self.optimized_searcher.parse_model_name(filename)
        
        # LoRA indicators
        lora_indicators = [
            'lora', 'locon', 'lycoris',
            # Style names often indicate LoRA
            'style', 'anime', 'cartoon', 'cute', 'realistic',
            '3d', '2d', 'pixel', 'chibi', 'artwork',
            # Character/concept LoRAs
            'character', 'person', 'face', 'girl', 'boy',
            # Common LoRA patterns
            'detail', 'enhance', 'lighting', 'color'
        ]
        
        # Check if likely LoRA
        is_likely_lora = any(indicator in filename_lower for indicator in lora_indicators)
        
        # Check for model series
        has_base_model = components['series'] is not None
        
        # Check function
        is_lora_function = components.get('function') == 'lora'
        
        # Decision logic
        if is_lora_function or (is_likely_lora and has_base_model):
            # LoRA models: try Civitai first
            return {
                'type': 'lora',
                'platform_priority': ['civitai', 'huggingface'],
                'search_strategy': 'style_based',
                'confidence': 'high'
            }
        
        # Additional check: if has LoRA indicators but no base model detected
        # (e.g., "Cute_3d_Cartoon_Flux" where Flux is capitalized)
        if is_likely_lora:
            # Check for model series in original case
            for series in ['flux', 'sdxl', 'sd']:
                if series in filename_lower:
                    return {
                        'type': 'lora',
                        'platform_priority': ['civitai', 'huggingface'],
                        'search_strategy': 'style_based',
                        'confidence': 'medium'
                    }
        
        # Official model patterns
        official_patterns = [
            'flux1-dev', 'flux1-schnell', 'flux1-pro',
            'sdxl-base', 'stable-diffusion',
            'sd-v1-', 'sd-v2-'
        ]
        
        if any(pattern in filename_lower for pattern in official_patterns):
            return {
                'type': 'checkpoint',
                'platform_priority': ['huggingface'],
                'search_strategy': 'official',
                'confidence': 'high'
            }
        
        # GGUF quantized models
        if filename.endswith('.gguf'):
            return {
                'type': 'quantized',
                'platform_priority': ['huggingface'],  # city96, Kijai repos
                'search_strategy': 'repository_specific',
                'confidence': 'high',
                'notes': 'Quantization experts: city96, Kijai'
            }
        
        # VAE/CLIP models
        if components.get('function') in ['vae', 'clip']:
            return {
                'type': components['function'],
                'platform_priority': ['huggingface'],
                'search_strategy': 'component',
                'confidence': 'medium'
            }
        
        # ControlNet models
        if 'controlnet' in filename_lower or 'control' in filename_lower:
            return {
                'type': 'controlnet',
                'platform_priority': ['huggingface', 'civitai'],
                'search_strategy': 'general',
                'confidence': 'medium'
            }
        
        # Default: try both platforms
        return {
            'type': 'unknown',
            'platform_priority': ['huggingface', 'civitai'],
            'search_strategy': 'general',
            'confidence': 'low'
        }
    
    async def search_model(self, filename: str, 
                          model_type: Optional[str] = None,
                          use_cache: bool = True) -> Optional[Dict]:
        """
        Search for a model across platforms.
        
        Args:
            filename: Model filename
            model_type: Optional model type hint
            use_cache: Whether to use cache
            
        Returns:
            Model information with platform details
        """
        # Check unified cache first
        cache_key = f"multi_{filename}"
        if use_cache:
            cached = self.cache_manager.get(cache_key, cache_type='search')
            if cached is not None:
                self.logger.debug(f"Multi-platform cache hit: {filename}")
                return cached
        
        # Identify search strategy
        strategy = self.identify_model_type_and_platform(filename)
        self.logger.info(f"Search strategy for {filename}: {strategy['type']} "
                        f"({strategy['confidence']} confidence)")
        
        # Override type if provided
        if model_type:
            strategy['type'] = model_type
        
        result = None
        search_attempts = []
        
        # Try platforms in priority order
        for platform in strategy['platform_priority']:
            self.logger.debug(f"Trying {platform} for {filename}")
            
            if platform == 'huggingface':
                try:
                    hf_result = await self.hf_searcher.search_model(filename, use_cache=False)
                    if hf_result:
                        result = {
                            **hf_result,
                            'platform': 'huggingface',
                            'search_strategy': strategy
                        }
                        break
                    else:
                        search_attempts.append({'platform': 'huggingface', 'status': 'not_found'})
                except Exception as e:
                    self.logger.error(f"HuggingFace search error: {e}")
                    search_attempts.append({'platform': 'huggingface', 'status': 'error', 'error': str(e)})
            
            elif platform == 'civitai' and self.civitai_searcher:
                try:
                    civitai_result = await self.civitai_searcher.search_model(
                        filename, 
                        model_type=strategy['type'],
                        use_cache=False
                    )
                    if civitai_result:
                        result = {
                            **civitai_result,
                            'search_strategy': strategy
                        }
                        break
                    else:
                        search_attempts.append({'platform': 'civitai', 'status': 'not_found'})
                except Exception as e:
                    self.logger.error(f"Civitai search error: {e}")
                    search_attempts.append({'platform': 'civitai', 'status': 'error', 'error': str(e)})
        
        # Add search metadata
        if result:
            result['search_attempts'] = search_attempts
        else:
            # Return detailed failure info
            result = {
                'found': False,
                'filename': filename,
                'search_strategy': strategy,
                'search_attempts': search_attempts,
                'suggestions': self._generate_suggestions(filename, strategy)
            }
        
        # Cache the result
        self.cache_manager.set(cache_key, result, cache_type='search')
        
        return result
    
    def _generate_suggestions(self, filename: str, strategy: Dict) -> List[str]:
        """Generate helpful suggestions for models not found."""
        suggestions = []
        
        # Parse components
        components = self.optimized_searcher.parse_model_name(filename)
        
        # Generic names
        if filename.lower() in ['clip_l.safetensors', 'clip_g.safetensors']:
            suggestions.append("Try downloading from: openai/clip-vit-large-patch14")
            suggestions.append("Or extract from: stabilityai/stable-diffusion-2-1")
        
        # GGUF models
        elif filename.endswith('.gguf'):
            if components['series'] == 'flux':
                suggestions.append(f"Check city96/FLUX.1-{components['version']}-gguf repository")
            else:
                suggestions.append("Search for GGUF repositories on HuggingFace")
        
        # LoRA models
        elif strategy['type'] == 'lora':
            suggestions.append("This appears to be a LoRA model - check Civitai directly")
            suggestions.append("Search Civitai with style keywords from the filename")
        
        # Custom models
        else:
            suggestions.append("This may be a custom or renamed model")
            suggestions.append("Try searching with partial name or keywords")
        
        return suggestions
    
    async def batch_search(self, models: List[Dict], 
                          max_concurrent: int = 3) -> List[Dict]:
        """
        Search for multiple models concurrently.
        
        Args:
            models: List of model dictionaries with 'filename' and optional 'model_type'
            max_concurrent: Maximum concurrent searches
            
        Returns:
            List of search results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_with_semaphore(model_info):
            async with semaphore:
                filename = model_info['filename']
                model_type = model_info.get('model_type')
                result = await self.search_model(filename, model_type)
                return {
                    **model_info,
                    'search_result': result
                }
        
        tasks = [search_with_semaphore(m) for m in models]
        return await asyncio.gather(*tasks)
    
    def search_sync(self, filename: str, 
                   model_type: Optional[str] = None,
                   use_cache: bool = True) -> Optional[Dict]:
        """Synchronous wrapper for search_model."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.search_model(filename, model_type, use_cache)
            )
        finally:
            loop.close()
    
    def batch_search_sync(self, models: List[Dict]) -> List[Dict]:
        """Synchronous wrapper for batch_search."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.batch_search(models))
        finally:
            loop.close()