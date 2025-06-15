"""Integration tests for full pipeline."""

import pytest
import tempfile
import json
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.workflow_analyzer import WorkflowAnalyzer
from src.core.model_matcher import ModelMatcher
from src.integrations.hf_searcher import HuggingFaceSearcher
from src.utils.cache_manager import CacheManager


class TestFullPipeline:
    """Test the complete workflow resolution pipeline."""
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow with known models."""
        return {
            "nodes": [
                {
                    "id": 1,
                    "type": "CheckpointLoaderSimple",
                    "widgets_values": ["sd_xl_base_1.0.safetensors"]
                },
                {
                    "id": 2,
                    "type": "LoraLoader", 
                    "widgets_values": ["add-detail-xl.safetensors", 0.8]
                },
                {
                    "id": 3,
                    "type": "VAELoader",
                    "widgets_values": ["sdxl_vae.safetensors"]
                }
            ]
        }
    
    @pytest.fixture
    def temp_model_dir(self):
        """Create temporary model directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create model subdirectories
            for subdir in ['checkpoints', 'loras', 'vae']:
                Path(temp_dir) / subdir).mkdir(parents=True)
            
            # Create one existing model
            (Path(temp_dir) / 'vae' / 'sdxl_vae.safetensors').touch()
            
            yield temp_dir
    
    def test_analyze_workflow(self, sample_workflow):
        """Test workflow analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_workflow, f)
            workflow_path = f.name
        
        try:
            analyzer = WorkflowAnalyzer()
            result = analyzer.analyze_workflow(workflow_path)
            
            assert result['model_count'] == 3
            assert len(result['models']) == 3
            
            # Check model types
            model_types = {m['model_type'] for m in result['models']}
            assert model_types == {'checkpoint', 'lora', 'vae'}
            
        finally:
            os.unlink(workflow_path)
    
    def test_match_models(self, sample_workflow, temp_model_dir):
        """Test model matching against local files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_workflow, f)
            workflow_path = f.name
        
        try:
            matcher = ModelMatcher(temp_model_dir)
            results = matcher.match_workflow_models(workflow_path)
            
            # Should find 1 model (vae), miss 2 (checkpoint, lora)
            assert len(results['found']) == 1
            assert len(results['missing']) == 2
            
            # Check found model
            found_model = results['found'][0]
            assert found_model.required_model['filename'] == 'sdxl_vae.safetensors'
            assert found_model.status.value == 'found'
            
        finally:
            os.unlink(workflow_path)
    
    @pytest.mark.asyncio
    async def test_search_models(self):
        """Test HuggingFace search functionality."""
        # Use a known model that should exist
        searcher = HuggingFaceSearcher()
        
        # Search for SDXL base model
        result = await searcher.search_model("sd_xl_base_1.0.safetensors")
        
        # May or may not find depending on API availability
        if result:
            assert 'repo_id' in result
            assert 'url' in result
            assert result['filename'] == 'sd_xl_base_1.0.safetensors'
    
    def test_cache_functionality(self):
        """Test caching system."""
        cache = CacheManager()
        
        # Test set and get
        test_data = {'model': 'test.safetensors', 'url': 'http://example.com'}
        cache.set('test_key', test_data, cache_type='search')
        
        retrieved = cache.get('test_key', cache_type='search')
        assert retrieved == test_data
        
        # Test cache miss
        assert cache.get('nonexistent_key') is None
        
        # Clean up
        cache.delete('test_key', cache_type='search')
    
    def test_keyword_extraction(self):
        """Test keyword extraction for fuzzy matching."""
        from src.core.keyword_extractor import KeywordExtractor
        
        extractor = KeywordExtractor()
        
        # Test various filename patterns
        test_cases = [
            ("epicRealism_naturalSinRC1VAE.safetensors", ['epic', 'realism', 'natural', 'sin', 'rc', 'vae']),
            ("sd_xl_base_1.0.safetensors", ['sd', 'xl', 'base']),
            ("4x-UltraSharp.pth", ['4x', 'ultra', 'sharp']),
        ]
        
        for filename, expected_keywords in test_cases:
            keywords = extractor.extract_keywords(filename)
            # Check that expected keywords are present (order may vary)
            for kw in expected_keywords:
                assert kw in keywords, f"Expected '{kw}' in keywords for {filename}"
    
    def test_end_to_end_workflow(self, sample_workflow, temp_model_dir):
        """Test complete workflow from analysis to export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_workflow, f)
            workflow_path = f.name
        
        try:
            # 1. Analyze
            analyzer = WorkflowAnalyzer()
            analysis = analyzer.analyze_workflow(workflow_path)
            assert analysis['model_count'] == 3
            
            # 2. Match
            matcher = ModelMatcher(temp_model_dir)
            match_results = matcher.match_workflow_models(workflow_path)
            
            # 3. Export missing
            export_data = matcher.export_missing_models(match_results)
            assert len(export_data['missing']) == 2
            
            # 4. Verify export format
            for model in export_data['missing']:
                assert 'name' in model
                assert 'type' in model
                assert 'directory' in model
                assert 'keywords' in model
            
        finally:
            os.unlink(workflow_path)