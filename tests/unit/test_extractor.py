"""Unit tests for KeywordExtractor."""

import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.keyword_extractor import KeywordExtractor


class TestKeywordExtractor:
    """Test cases for KeywordExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a KeywordExtractor instance."""
        return KeywordExtractor()
    
    def test_extract_keywords_basic(self, extractor):
        """Test basic keyword extraction."""
        # Test simple filename
        keywords = extractor.extract_keywords("epicrealism_naturalSin.safetensors")
        assert "epicrealism" in keywords
        assert "natural" in keywords
        assert "sin" in keywords
        
        # Test with version
        keywords = extractor.extract_keywords("model_v1.5.ckpt")
        assert "model" in keywords
        assert "v1.5" not in keywords  # Version should be filtered
        assert "5" not in keywords  # Version parts filtered
    
    def test_extract_keywords_complex(self, extractor):
        """Test complex filename parsing."""
        # Test with multiple separators
        keywords = extractor.extract_keywords("sd_xl_base_1.0-vae-fp16-pruned.safetensors")
        assert "sd" in keywords
        assert "xl" in keywords
        assert "base" in keywords
        assert "fp16" not in keywords  # Precision filtered
        assert "pruned" not in keywords  # Variant filtered
        
        # Test camelCase
        keywords = extractor.extract_keywords("epicRealismNaturalSin.safetensors")
        assert "epic" in keywords
        assert "realism" in keywords
        assert "natural" in keywords
        assert "sin" in keywords
    
    def test_preserve_keywords(self, extractor):
        """Test that preserved keywords are kept."""
        keywords = extractor.extract_keywords("sdxl_turbo_v2.safetensors")
        assert "sdxl" in keywords  # Should be preserved
        assert "turbo" in keywords
        assert "v2" not in keywords  # Version still filtered
    
    def test_calculate_similarity(self, extractor):
        """Test similarity calculation."""
        # Identical lists
        sim = extractor.calculate_similarity(['a', 'b', 'c'], ['a', 'b', 'c'])
        assert sim == 1.0
        
        # Completely different
        sim = extractor.calculate_similarity(['a', 'b'], ['x', 'y'])
        assert sim == 0.0
        
        # Partial overlap
        sim = extractor.calculate_similarity(['a', 'b', 'c'], ['b', 'c', 'd'])
        assert 0.4 < sim < 0.6  # Should be around 0.5
        
        # Empty lists
        sim = extractor.calculate_similarity([], ['a', 'b'])
        assert sim == 0.0
    
    def test_match_keywords(self, extractor):
        """Test keyword matching."""
        # Full match
        match_type, score = extractor.match_keywords(
            ['epic', 'realism'],
            ['epic', 'realism', 'natural', 'sin']
        )
        assert match_type == 'full'
        assert score == 1.0
        
        # Partial match
        match_type, score = extractor.match_keywords(
            ['epic', 'realism', 'v5'],
            ['epic', 'natural'],
            threshold=0.3
        )
        assert match_type == 'partial'
        assert 0 < score < 1
        
        # No match
        match_type, score = extractor.match_keywords(
            ['anime', 'style'],
            ['realistic', 'photo'],
            threshold=0.7
        )
        assert match_type == 'none'
        assert score < 0.7
    
    def test_extract_model_info(self, extractor):
        """Test comprehensive model info extraction."""
        info = extractor.extract_model_info("epicRealism_naturalSinRC1VAE-fp16-pruned-v5.safetensors")
        
        assert info['filename'] == "epicRealism_naturalSinRC1VAE-fp16-pruned-v5.safetensors"
        assert info['format'] == 'safetensors'
        assert info['precision'] == 'fp16'
        assert info['variant'] == 'pruned'
        assert info['version'] == '5'
        assert 'epic' in info['keywords']
        assert 'realism' in info['keywords']
        
    def test_special_characters(self, extractor):
        """Test handling of special characters."""
        keywords = extractor.extract_keywords("4x-UltraSharp.pth")
        assert "4x" in keywords or "4" in keywords
        assert "ultra" in keywords
        assert "sharp" in keywords
        
    def test_version_filtering(self, extractor):
        """Test that version variants are properly filtered."""
        # Test various version formats
        test_cases = [
            ("model_q4_k_m.gguf", ["model"]),
            ("model_fp16.safetensors", ["model"]),
            ("model_pruned_ema.ckpt", ["model"]),
            ("model_v1.0_final.pt", ["model"]),
        ]
        
        for filename, expected in test_cases:
            keywords = extractor.extract_keywords(filename)
            # Should not contain version identifiers
            assert not any(kw in ['q4', 'fp16', 'pruned', 'ema', 'v1.0', 'final'] 
                          for kw in keywords)
            # Should contain base keywords
            for exp in expected:
                assert exp in keywords