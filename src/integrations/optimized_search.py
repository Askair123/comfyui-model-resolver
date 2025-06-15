#!/usr/bin/env python3
"""
Optimized Search Strategy for AI Model Names

Based on comprehensive research of AI model naming conventions:
- Quantization formats: fp8_e4m3fn, Q4_K_S, fp16, bf16
- Model functions: T2V, I2V, InP, VAE
- Model series: Flux, Wan/Wan2.1, Hunyuan, LTXV
- Special variants: CausVid, SkyReels
- Important markers: resolution (480P, 720P), parameters (14B, 1.3B)
"""

import re
from typing import List, Set, Tuple
import logging

class OptimizedModelSearcher:
    """Intelligent model name parser and search term generator."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Model series with known variants
        self.model_series = {
            'flux': {
                'variants': ['flux1', 'flux-1', 'flux_1'],
                'versions': ['dev', 'schnell', 'pro'],
                'official_format': 'flux1-{version}'
            },
            'wan': {
                'variants': ['wan', 'wan2', 'wan21', 'wan2.1', 'wan2_1'],
                'versions': ['2.1'],
                'official_format': 'Wan2.1'
            },
            'hunyuan': {
                'variants': ['hunyuan', 'hy'],
                'versions': ['dit', 'video'],
                'official_format': 'HunyuanDiT'
            },
            'ltxv': {
                'variants': ['ltxv', 'ltx-v', 'ltx_v'],
                'versions': ['2b'],
                'official_format': 'LTXV'
            }
        }
        
        # Function mappings
        self.model_functions = {
            'text2video': ['t2v', 'text2video', 'txt2vid'],
            'image2video': ['i2v', 'img2vid', 'image2video'],
            'inpainting': ['inp', 'inpaint', 'inpainting'],
            'vae': ['vae', 'variational'],
            'unet': ['unet', 'diffusion'],
            'lora': ['lora', 'locon', 'lycoris']
        }
        
        # Special model types
        self.special_types = {
            'causvid': 'Causal Video Acceleration',
            'skyreels': 'Hunyuan SkyReels Optimization',
            'gguf': 'GGML Universal Format',
            'reactor': 'Face Swap Model',
            'ipadapter': 'Image Prompt Adapter'
        }
        
        # Quantization formats to preserve
        self.quantization_formats = {
            # Floating point quantizations
            'fp8_e4m3fn': '8-bit float (4-bit exponent, 3-bit mantissa)',
            'fp8_e5m2': '8-bit float (5-bit exponent, 2-bit mantissa)',
            'fp8': 'Generic 8-bit float',
            'fp16': '16-bit float',
            'bf16': 'Brain float 16',
            'fp32': '32-bit float',
            
            # GGUF quantizations
            'q2_k': '2-bit quantization',
            'q3_k_s': '3-bit small quantization',
            'q3_k_m': '3-bit medium quantization',
            'q3_k_l': '3-bit large quantization',
            'q4_0': '4-bit legacy quantization',
            'q4_1': '4-bit quantization v1',
            'q4_k_s': '4-bit small quantization',
            'q4_k_m': '4-bit medium quantization',
            'q5_0': '5-bit legacy quantization',
            'q5_1': '5-bit quantization v1',
            'q5_k_s': '5-bit small quantization',
            'q5_k_m': '5-bit medium quantization',
            'q6_k': '6-bit quantization',
            'q8_0': '8-bit quantization'
        }
        
        # Important markers to preserve
        self.preserve_markers = {
            'resolution': re.compile(r'\d{3,4}[pP]'),  # 480P, 720P, 1080P
            'parameters': re.compile(r'\d+\.?\d*[bB]'),  # 14B, 1.3B
            'version': re.compile(r'v\d+(?:\.\d+)*'),  # v1, v2.1
            'rank': re.compile(r'rank\d+'),  # rank32, rank64
            'channels': re.compile(r'\d+ch'),  # 4ch, 8ch
        }
        
        # Personal/custom markers to filter
        self.filter_patterns = [
            re.compile(r'\d+gb', re.I),  # File sizes: 11gb, 23gb
            re.compile(r'\d+mb', re.I),  # File sizes: 500mb
            re.compile(r'by[-_]\w+', re.I),  # Creator tags: by-artist
            re.compile(r'my[-_]\w+', re.I),  # Personal tags: my-version
            re.compile(r'test[-_]?\w*', re.I),  # Test versions
            re.compile(r'final[-_]?\w*', re.I),  # Personal markers
            re.compile(r'backup[-_]?\w*', re.I),  # Backup copies
            re.compile(r'old[-_]?\w*', re.I),  # Old versions
            re.compile(r'new[-_]?\w*', re.I),  # New versions
            re.compile(r'custom[-_]?\w*', re.I),  # Custom versions
        ]
    
    def parse_model_name(self, filename: str) -> dict:
        """Parse model filename into structured components."""
        # Remove extension
        name = filename.lower()
        extension = ''
        for ext in ['.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.onnx']:
            if name.endswith(ext):
                extension = ext
                name = name[:-len(ext)]
                break
        
        components = {
            'original': filename,
            'base_name': name,
            'extension': extension,
            'series': None,
            'version': None,
            'function': None,
            'quantization': None,
            'resolution': None,
            'parameters': None,
            'special_type': None,
            'custom_markers': []
        }
        
        # Detect model series
        for series, info in self.model_series.items():
            for variant in info['variants']:
                if variant in name:
                    components['series'] = series
                    # Extract version if present
                    for ver in info['versions']:
                        if ver in name:
                            components['version'] = ver
                    break
        
        # Detect function
        for func_type, variants in self.model_functions.items():
            for variant in variants:
                if variant in name:
                    components['function'] = func_type
                    break
        
        # Detect special types
        for special, desc in self.special_types.items():
            if special in name:
                components['special_type'] = special
        
        # Detect quantization
        for quant in self.quantization_formats:
            if quant in name:
                components['quantization'] = quant
                break
        
        # Extract preserved markers
        res_match = self.preserve_markers['resolution'].search(name)
        if res_match:
            components['resolution'] = res_match.group(0)
        
        param_match = self.preserve_markers['parameters'].search(name)
        if param_match:
            components['parameters'] = param_match.group(0)
        
        # Identify custom markers
        for pattern in self.filter_patterns:
            matches = pattern.findall(name)
            components['custom_markers'].extend(matches)
        
        return components
    
    def generate_search_terms(self, filename: str) -> List[str]:
        """Generate optimized search terms for a model filename."""
        components = self.parse_model_name(filename)
        search_terms = []
        
        # Special handling for known generic names
        if components['base_name'] == 'clip_l':
            search_terms.extend([
                'openai/clip-vit-large-patch14',
                'stabilityai/stable-diffusion clip_l',
                'CLIP ViT-L/14'
            ])
            return search_terms
        
        # Strategy 1: Try to find exact match first (remove only file size markers)
        # flux1-dev-11gb-fp8.safetensors → flux1-dev-fp8.safetensors
        clean_name = components['base_name']
        
        # Remove only file size markers (11gb, 23gb, etc.)
        size_pattern = re.compile(r'[-_]?\d+gb', re.I)
        clean_name = size_pattern.sub('', clean_name)
        
        # Add with original extension
        if components['extension']:
            search_terms.append(clean_name + components['extension'])
        search_terms.append(clean_name)
        
        # Strategy 2: Build comprehensive search with all important components
        if components['series']:
            # For known series, try official format WITH technical specs
            if components['series'] == 'flux' and components['version'] and components['quantization']:
                # flux1-dev-11gb-fp8 → flux1-dev-fp8
                search_terms.append(f"flux1-{components['version']}-{components['quantization']}")
                search_terms.append(f"flux1 {components['version']} {components['quantization']}")
                
                # For GGUF files, add specialized repository searches
                if components['extension'] == '.gguf':
                    # city96's repository
                    search_terms.append(f"city96/FLUX.1-{components['version']}-gguf")
                    # Kijai's repository patterns
                    search_terms.append(f"Kijai/flux.1-{components['version']}-gguf")
                    search_terms.append(f"Kijai/Flux.1-{components['version']}-GGUF")
                    # Generic searches
                    search_terms.append(f"flux1-{components['version']} gguf")
                    search_terms.append(f"city96 flux")
                    search_terms.append(f"Kijai flux")
            
            elif components['series'] == 'wan':
                # Keep all technical components
                parts = ['Wan2.1']
                if components['special_type'] == 'causvid':
                    parts.append('CausVid')
                if components['parameters']:
                    parts.append(components['parameters'].upper())
                if components['function'] == 'text2video':
                    parts.append('T2V')
                if components['function'] and 'lora' in components['function']:
                    parts.append('lora')
                    # Check for rank
                    rank_match = re.search(r'rank(\d+)', components['base_name'])
                    if rank_match:
                        parts.append(f'rank{rank_match.group(1)}')
                
                # Generate various combinations
                search_terms.append('_'.join(parts))
                search_terms.append(' '.join(parts))
                search_terms.append('-'.join(parts))
                
                # For GGUF quantized versions, add repository searches
                if components['extension'] == '.gguf' and components['quantization']:
                    # Kijai's repository patterns for Wan models
                    search_terms.append(f"Kijai/Wan2.1-{components['quantization']}")
                    search_terms.append(f"Kijai/wan2.1-gguf")
                    # city96's patterns
                    search_terms.append(f"city96/wan2.1-gguf")
        
        # Strategy 3: Component-based search (preserving all technical specs)
        base_components = []
        
        # Add series
        if components['series']:
            base_components.append(components['series'])
        
        # Add version
        if components['version']:
            base_components.append(components['version'])
        
        # Add ALL technical specifications
        if components['quantization']:
            base_components.append(components['quantization'])
        
        if components['parameters']:
            base_components.append(components['parameters'])
        
        if components['function']:
            if components['function'] == 'text2video':
                base_components.append('t2v')
            elif components['function'] == 'image2video':
                base_components.append('i2v')
            else:
                base_components.append(components['function'])
        
        if components['resolution']:
            base_components.append(components['resolution'])
        
        # Generate component-based search
        if base_components:
            search_terms.append(' '.join(base_components))
            search_terms.append('_'.join(base_components))
        
        # Strategy 4: Original name without only personal/size markers
        original_clean = components['base_name']
        # Remove only truly personal markers, keep technical ones
        for marker in ['my', 'test', 'final', 'backup', 'old', 'new', 'custom']:
            pattern = re.compile(rf'[-_]?{marker}[-_]?\w*', re.I)
            original_clean = pattern.sub('', original_clean)
        
        # Clean up multiple separators
        original_clean = re.sub(r'[-_]+', '-', original_clean).strip('-')
        
        if original_clean and original_clean not in [s.replace(' ', '-') for s in search_terms]:
            search_terms.append(original_clean)
        
        # Strategy 5: Special handling for likely LoRA/custom models
        base_lower = components['base_name'].lower()
        if any(keyword in base_lower for keyword in ['lora', 'cute', 'cartoon', 'style', 'anime']):
            # This is likely a LoRA model - should search on Civitai
            # Add a special marker for the search system
            search_terms.append(f"CIVITAI_SEARCH: {components['base_name']}")
            
            # Extract style/theme keywords for Civitai search
            style_keywords = []
            for word in ['cute', '3d', 'cartoon', 'anime', 'realistic', 'style']:
                if word in base_lower:
                    style_keywords.append(word)
            
            if style_keywords:
                # Civitai search terms
                if components['series']:
                    search_terms.append(f"CIVITAI: {' '.join(style_keywords)} LoRA {components['series']}")
                else:
                    search_terms.append(f"CIVITAI: {' '.join(style_keywords)} LoRA")
        
        # Strategy 6: Handle complex custom model names
        if 'vit' in base_lower and 'clip' not in base_lower:
            # Likely a CLIP variant
            search_terms.extend([
                'CLIP ViT-L',
                'ViT-L-14 text encoder'
            ])
        
        # Strategy 6.5: General GGUF repository search
        if components['extension'] == '.gguf' and components['quantization']:
            # Extract base model name for repository search
            base_model = components['base_name']
            # Remove quantization info to get base
            for quant in self.quantization_formats:
                base_model = base_model.replace(f'-{quant}', '').replace(f'_{quant}', '')
            
            # Add known quantization expert repositories
            if base_model:
                # Kijai's patterns (often uses lowercase with hyphens)
                search_terms.append(f"Kijai/{base_model}-gguf")
                search_terms.append(f"Kijai/{base_model}-GGUF")
                search_terms.append(f"Kijai/{base_model}-{components['quantization']}")
                
                # city96's patterns (often uses dots and different casing)
                search_terms.append(f"city96/{base_model}-gguf")
                search_terms.append(f"city96/{base_model.replace('-', '.')}-gguf")
                
                # Generic patterns
                search_terms.append(f"{base_model} gguf quantized")
                search_terms.append(f"{base_model} {components['quantization']} gguf")
        
        # Strategy 7: Fallback - use mostly complete original name
        if len(search_terms) < 2:
            # Just remove file size, keep everything else
            size_pattern_fb = re.compile(r'[-_]?\d+gb', re.I)
            fallback = size_pattern_fb.sub('', components['base_name'])
            if fallback not in search_terms:
                search_terms.append(fallback)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term and term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    def extract_keywords(self, filename: str) -> List[str]:
        """Extract keywords for fuzzy matching."""
        components = self.parse_model_name(filename)
        keywords = []
        
        # Priority 1: Model series
        if components['series']:
            keywords.append(components['series'])
        
        # Priority 2: Version
        if components['version']:
            keywords.append(components['version'])
        
        # Priority 3: Quantization (important for compatibility)
        if components['quantization']:
            # Normalize quantization format
            quant = components['quantization'].lower()
            if quant.startswith('fp'):
                keywords.append('fp' + quant[2:].split('_')[0])  # fp8_e4m3fn → fp8
            elif quant.startswith('q'):
                keywords.append(quant.split('_')[0])  # q4_k_s → q4
            else:
                keywords.append(quant)
        
        # Priority 4: Important functions
        if components['function'] in ['text2video', 'image2video', 'vae']:
            keywords.append(components['function'])
        
        # Priority 5: Resolution if present
        if components['resolution']:
            keywords.append(components['resolution'].lower())
        
        # Priority 6: Parameter count
        if components['parameters']:
            keywords.append(components['parameters'].lower())
        
        # Filter and clean keywords
        cleaned_keywords = []
        for kw in keywords:
            # Skip very short keywords
            if len(kw) <= 1:
                continue
            # Skip pure numbers
            if kw.isdigit():
                continue
            # Skip common separators
            if kw in ['by', 'my', 'the', 'and', 'or', 'for']:
                continue
            
            cleaned_keywords.append(kw)
        
        return cleaned_keywords
    
    def match_score(self, search_name: str, target_name: str) -> float:
        """Calculate match score between search and target model names."""
        search_kw = set(self.extract_keywords(search_name))
        target_kw = set(self.extract_keywords(target_name))
        
        if not search_kw or not target_kw:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(search_kw & target_kw)
        union = len(search_kw | target_kw)
        
        if union == 0:
            return 0.0
        
        score = intersection / union
        
        # Boost score for exact series match
        search_comp = self.parse_model_name(search_name)
        target_comp = self.parse_model_name(target_name)
        
        if (search_comp['series'] and target_comp['series'] and 
            search_comp['series'] == target_comp['series']):
            score *= 1.5
        
        # Boost for matching quantization
        if (search_comp['quantization'] and target_comp['quantization'] and
            search_comp['quantization'] == target_comp['quantization']):
            score *= 1.2
        
        return min(score, 1.0)  # Cap at 1.0