"""
Keyword Extractor Module

Extracts and processes keywords from model filenames for fuzzy matching.
"""

import re
import yaml
from typing import List, Set, Tuple, Optional
from pathlib import Path


class KeywordExtractor:
    """Extracts meaningful keywords from model filenames."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the keyword extractor.
        
        Args:
            config_path: Path to version filters configuration
        """
        self.config_path = config_path or self._get_default_config_path()
        self.version_variants, self.preserve_keywords = self._load_filters()
        
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent
        config_path = current_dir.parent.parent / "config" / "version_filters.yaml"
        return str(config_path)
    
    def _load_filters(self) -> Tuple[Set[str], Set[str]]:
        """Load version filters from configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                version_variants = set(config.get('version_variants', []))
                preserve_keywords = set(config.get('preserve_keywords', []))
                return version_variants, preserve_keywords
        except FileNotFoundError:
            # Fallback to minimal filters
            return self._get_default_filters()
    
    def _get_default_filters(self) -> Tuple[Set[str], Set[str]]:
        """Get default filters if config not available."""
        version_variants = {
            'q4', 'q5', 'q8', 'fp16', 'fp32', 'pruned', 'ema',
            'v1', 'v2', 'v3', 'v1.0', 'v2.0', 'final', 'latest'
        }
        preserve_keywords = {
            'sdxl', 'sd15', 'sd21', 'flux', 'controlnet', 'openpose'
        }
        return version_variants, preserve_keywords
    
    def extract_keywords(self, filename: str) -> List[str]:
        """
        Extract meaningful keywords from a filename.
        
        Args:
            filename: Model filename to process
            
        Returns:
            List of extracted keywords
        """
        # Remove file extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Convert to lowercase for processing
        name_lower = name_without_ext.lower()
        
        # Split by common separators
        # First split by underscores and hyphens
        parts = re.split(r'[-_]', name_lower)
        
        # Further split camelCase and numbers
        all_parts = []
        for part in parts:
            # Split camelCase (e.g., "epicRealism" -> "epic", "realism")
            camel_parts = re.findall(r'[a-z]+|[A-Z][a-z]*|\d+', part)
            all_parts.extend(camel_parts)
        
        # Filter out empty strings
        all_parts = [p for p in all_parts if p]
        
        # Process keywords
        keywords = []
        for part in all_parts:
            # Skip if it's a version variant (unless preserved)
            if part in self.preserve_keywords:
                keywords.append(part)
            elif part not in self.version_variants:
                # Only include if it's meaningful (not too short)
                if len(part) >= 2 or part.isdigit():
                    keywords.append(part)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    def calculate_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """
        Calculate similarity score between two keyword lists.
        
        Args:
            keywords1: First keyword list
            keywords2: Second keyword list
            
        Returns:
            Similarity score between 0 and 1
        """
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(keywords1)
        set2 = set(keywords2)
        
        # Calculate Jaccard similarity
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def match_keywords(self, required_keywords: List[str], 
                      candidate_keywords: List[str],
                      threshold: float = 0.7) -> Tuple[str, float]:
        """
        Match required keywords against candidate keywords.
        
        Args:
            required_keywords: Keywords from the required model
            candidate_keywords: Keywords from a candidate model
            threshold: Minimum similarity threshold for partial match
            
        Returns:
            Tuple of (match_type, similarity_score)
            match_type: 'full', 'partial', or 'none'
        """
        required_set = set(required_keywords)
        candidate_set = set(candidate_keywords)
        
        # Check for full match (all required keywords present)
        if required_set.issubset(candidate_set):
            return 'full', 1.0
        
        # Calculate similarity for partial match
        similarity = self.calculate_similarity(required_keywords, candidate_keywords)
        
        if similarity >= threshold:
            return 'partial', similarity
        else:
            return 'none', similarity
    
    def extract_model_info(self, filename: str) -> dict:
        """
        Extract structured information from model filename.
        
        Args:
            filename: Model filename
            
        Returns:
            Dictionary with extracted information
        """
        keywords = self.extract_keywords(filename)
        
        # Try to identify specific attributes
        info = {
            'filename': filename,
            'keywords': keywords,
            'base_name': None,
            'version': None,
            'format': None,
            'precision': None,
            'variant': None
        }
        
        # Extract file extension
        if '.' in filename:
            info['format'] = filename.rsplit('.', 1)[1].lower()
        
        # Look for version patterns
        version_pattern = r'v(\d+(?:\.\d+)*)'
        version_match = re.search(version_pattern, filename.lower())
        if version_match:
            info['version'] = version_match.group(1)
        
        # Look for precision indicators
        precision_indicators = ['fp16', 'fp32', 'bf16', 'int8', 'f16', 'f32']
        for precision in precision_indicators:
            if precision in filename.lower():
                info['precision'] = precision
                break
        
        # Look for variant indicators
        variant_indicators = ['pruned', 'ema', 'inpainting', 'refiner', 'vae', 'novae']
        for variant in variant_indicators:
            if variant in filename.lower():
                info['variant'] = variant
                break
        
        # Estimate base name (first few keywords)
        if keywords:
            # Take first 2-3 keywords as base name
            base_parts = []
            for kw in keywords[:3]:
                if kw not in self.version_variants:
                    base_parts.append(kw)
            if base_parts:
                info['base_name'] = '_'.join(base_parts)
        
        return info