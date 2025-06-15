"""Unit tests for ModelMatcher."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.model_matcher import ModelMatcher, MatchStatus, ModelMatch


class TestModelMatcher:
    """Test cases for ModelMatcher class."""
    
    @pytest.fixture
    def matcher(self):
        """Create a ModelMatcher instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            return ModelMatcher(base_path=temp_dir)
    
    @pytest.fixture
    def mock_local_scanner(self):
        """Create a mock LocalScanner."""
        scanner = Mock()
        return scanner
    
    def test_match_single_model_exact(self, matcher):
        """Test exact model matching."""
        model_info = {
            'filename': 'epicrealism_v5.safetensors',
            'model_type': 'checkpoint',
            'directory': 'checkpoints'
        }
        
        # Mock exact match
        with patch.object(matcher.local_scanner, 'find_model_by_name') as mock_find:
            mock_find.return_value = [{
                'filename': 'epicrealism_v5.safetensors',
                'full_path': '/models/checkpoints/epicrealism_v5.safetensors',
                'size_gb': 2.13
            }]
            
            match = matcher.match_single_model(model_info)
            
            assert match.status == MatchStatus.FOUND
            assert match.similarity_score == 1.0
            assert match.best_match['filename'] == 'epicrealism_v5.safetensors'
    
    def test_match_single_model_partial(self, matcher):
        """Test partial model matching."""
        model_info = {
            'filename': 'epicRealism_naturalSin.safetensors',
            'model_type': 'checkpoint',
            'directory': 'checkpoints'
        }
        
        # Mock no exact match but keyword matches
        with patch.object(matcher.local_scanner, 'find_model_by_name') as mock_exact:
            mock_exact.return_value = []
            
            with patch.object(matcher.local_scanner, 'find_models_by_keywords') as mock_keywords:
                mock_keywords.return_value = [
                    ({
                        'filename': 'epicrealism_v5.safetensors',
                        'full_path': '/models/checkpoints/epicrealism_v5.safetensors',
                        'keywords': ['epicrealism', 'v5']
                    }, 0.75)
                ]
                
                match = matcher.match_single_model(model_info)
                
                assert match.status == MatchStatus.PARTIAL
                assert match.similarity_score == 0.75
                assert len(match.local_matches) == 1
    
    def test_match_single_model_missing(self, matcher):
        """Test missing model detection."""
        model_info = {
            'filename': 'nonexistent_model.safetensors',
            'model_type': 'checkpoint',
            'directory': 'checkpoints'
        }
        
        # Mock no matches
        with patch.object(matcher.local_scanner, 'find_model_by_name') as mock_exact:
            mock_exact.return_value = []
            
            with patch.object(matcher.local_scanner, 'find_models_by_keywords') as mock_keywords:
                mock_keywords.return_value = []
                
                match = matcher.match_single_model(model_info)
                
                assert match.status == MatchStatus.MISSING
                assert match.similarity_score == 0.0
                assert match.best_match is None
    
    def test_match_workflow_models(self, matcher):
        """Test matching all models from a workflow."""
        # Create test workflow
        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "CheckpointLoaderSimple",
                    "widgets_values": ["found_model.safetensors"]
                },
                {
                    "id": 2,
                    "type": "LoraLoader",
                    "widgets_values": ["missing_model.safetensors", 0.8]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(workflow, f)
            workflow_path = f.name
        
        try:
            # Mock scanner responses
            def mock_find_by_name(filename, model_type):
                if filename == "found_model.safetensors":
                    return [{'filename': filename, 'full_path': f'/models/{filename}'}]
                return []
            
            def mock_find_by_keywords(keywords, model_type, threshold):
                return []
            
            with patch.object(matcher.local_scanner, 'find_model_by_name', side_effect=mock_find_by_name):
                with patch.object(matcher.local_scanner, 'find_models_by_keywords', side_effect=mock_find_by_keywords):
                    results = matcher.match_workflow_models(workflow_path)
                    
                    assert results['total_models'] == 2
                    assert len(results['found']) == 1
                    assert len(results['missing']) == 1
                    assert results['summary']['success_rate'] == 0.5
                    
        finally:
            Path(workflow_path).unlink()
    
    def test_generate_report(self, matcher):
        """Test report generation."""
        # Create mock results
        results = {
            'workflow': 'test_workflow.json',
            'total_models': 3,
            'found': [
                ModelMatch(
                    required_model={'filename': 'found.safetensors', 'model_type': 'checkpoint'},
                    status=MatchStatus.FOUND,
                    local_matches=[{'filename': 'found.safetensors', 'full_path': '/models/found.safetensors', 'size_gb': 2.0}],
                    best_match={'filename': 'found.safetensors', 'full_path': '/models/found.safetensors', 'size_gb': 2.0},
                    similarity_score=1.0
                )
            ],
            'partial': [
                ModelMatch(
                    required_model={'filename': 'partial.safetensors', 'model_type': 'lora'},
                    status=MatchStatus.PARTIAL,
                    local_matches=[{'filename': 'similar.safetensors', 'full_path': '/models/similar.safetensors'}],
                    best_match={'filename': 'similar.safetensors', 'full_path': '/models/similar.safetensors'},
                    similarity_score=0.8
                )
            ],
            'missing': [
                ModelMatch(
                    required_model={'filename': 'missing.safetensors', 'model_type': 'vae', 'directory': 'vae'},
                    status=MatchStatus.MISSING,
                    local_matches=[],
                    best_match=None,
                    similarity_score=0.0
                )
            ],
            'summary': {
                'found_count': 1,
                'partial_count': 1,
                'missing_count': 1,
                'success_rate': 0.333
            }
        }
        
        report = matcher.generate_report(results)
        
        assert 'ComfyUI Model Dependency Analysis Report' in report
        assert '✓ Found: 1' in report
        assert '⚠ Partial Matches: 1' in report
        assert '✗ Missing: 1' in report
        assert 'found.safetensors' in report
        assert 'partial.safetensors' in report
        assert 'missing.safetensors' in report
    
    def test_export_missing_models(self, matcher):
        """Test exporting missing models for download."""
        results = {
            'workflow': 'test.json',
            'missing': [
                ModelMatch(
                    required_model={
                        'filename': 'missing1.safetensors',
                        'model_type': 'checkpoint',
                        'directory': 'checkpoints'
                    },
                    status=MatchStatus.MISSING,
                    local_matches=[],
                    best_match=None,
                    similarity_score=0.0
                )
            ],
            'partial': [
                ModelMatch(
                    required_model={
                        'filename': 'partial1.safetensors',
                        'model_type': 'lora',
                        'directory': 'loras'
                    },
                    status=MatchStatus.PARTIAL,
                    local_matches=[
                        {'filename': 'alt1.safetensors', 'full_path': '/models/alt1.safetensors'},
                        {'filename': 'alt2.safetensors', 'full_path': '/models/alt2.safetensors'}
                    ],
                    best_match={'filename': 'alt1.safetensors', 'full_path': '/models/alt1.safetensors'},
                    similarity_score=0.75
                )
            ],
            'found': []
        }
        
        export = matcher.export_missing_models(results)
        
        assert len(export['missing']) == 1
        assert export['missing'][0]['name'] == 'missing1.safetensors'
        assert export['missing'][0]['type'] == 'checkpoint'
        
        assert len(export['partial']) == 1
        assert export['partial'][0]['name'] == 'partial1.safetensors'
        assert len(export['partial'][0]['local_alternatives']) == 2