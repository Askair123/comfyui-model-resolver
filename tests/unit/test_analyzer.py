"""Unit tests for WorkflowAnalyzer."""

import json
import os
import tempfile
import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.workflow_analyzer import WorkflowAnalyzer


class TestWorkflowAnalyzer:
    """Test cases for WorkflowAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a WorkflowAnalyzer instance."""
        return WorkflowAnalyzer()
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing."""
        return {
            "nodes": [
                {
                    "id": 1,
                    "type": "CheckpointLoaderSimple",
                    "widgets_values": ["epicrealism_v5.safetensors"]
                },
                {
                    "id": 2,
                    "type": "LoraLoader",
                    "widgets_values": ["detail_tweaker.safetensors", 0.8, 1.0]
                },
                {
                    "id": 3,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["beautiful landscape"]
                },
                {
                    "id": 4,
                    "type": "VAELoader",
                    "widgets_values": ["vae-ft-mse.safetensors"]
                }
            ]
        }
    
    def test_analyze_workflow_extracts_models(self, analyzer, sample_workflow):
        """Test that analyzer correctly extracts models from workflow."""
        # Create temporary workflow file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_workflow, f)
            temp_path = f.name
        
        try:
            result = analyzer.analyze_workflow(temp_path)
            
            assert result['workflow_file'] == temp_path
            assert result['total_nodes'] == 4
            assert result['model_count'] == 3  # CLIPTextEncode should be skipped
            
            # Check extracted models
            models = result['models']
            assert len(models) == 3
            
            # Verify checkpoint model
            checkpoint = next(m for m in models if m['model_type'] == 'checkpoint')
            assert checkpoint['filename'] == 'epicrealism_v5.safetensors'
            assert checkpoint['directory'] == 'checkpoints'
            
            # Verify lora model
            lora = next(m for m in models if m['model_type'] == 'lora')
            assert lora['filename'] == 'detail_tweaker.safetensors'
            assert lora['directory'] == 'loras'
            
            # Verify vae model
            vae = next(m for m in models if m['model_type'] == 'vae')
            assert vae['filename'] == 'vae-ft-mse.safetensors'
            assert vae['directory'] == 'vae'
            
        finally:
            os.unlink(temp_path)
    
    def test_skip_non_model_nodes(self, analyzer):
        """Test that non-model nodes are skipped."""
        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["test prompt"]
                },
                {
                    "id": 2,
                    "type": "KSampler",
                    "widgets_values": [123456, "fixed", 20, 8.0]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(workflow, f)
            temp_path = f.name
        
        try:
            result = analyzer.analyze_workflow(temp_path)
            assert result['model_count'] == 0
            assert len(result['models']) == 0
        finally:
            os.unlink(temp_path)
    
    def test_handle_duplicate_models(self, analyzer):
        """Test that duplicate models are handled correctly."""
        workflow = {
            "nodes": [
                {
                    "id": 1,
                    "type": "CheckpointLoaderSimple",
                    "widgets_values": ["same_model.safetensors"]
                },
                {
                    "id": 2,
                    "type": "CheckpointLoaderSimple",
                    "widgets_values": ["same_model.safetensors"]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(workflow, f)
            temp_path = f.name
        
        try:
            result = analyzer.analyze_workflow(temp_path)
            assert result['model_count'] == 1  # Duplicates should be removed
            assert len(result['models']) == 1
        finally:
            os.unlink(temp_path)
    
    def test_invalid_workflow_file(self, analyzer):
        """Test handling of invalid workflow files."""
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            analyzer.analyze_workflow("non_existent_file.json")
        
        # Test invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError):
                analyzer.analyze_workflow(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_analyze_directory(self, analyzer):
        """Test analyzing multiple workflow files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple workflow files
            for i in range(3):
                workflow = {
                    "nodes": [{
                        "id": 1,
                        "type": "CheckpointLoaderSimple",
                        "widgets_values": [f"model_{i}.safetensors"]
                    }]
                }
                
                with open(os.path.join(temp_dir, f"workflow_{i}.json"), 'w') as f:
                    json.dump(workflow, f)
            
            # Add a non-workflow file
            with open(os.path.join(temp_dir, "not_a_workflow.txt"), 'w') as f:
                f.write("some text")
            
            results = analyzer.analyze_directory(temp_dir)
            
            assert len(results) == 3  # Should only process JSON files
            for i, result in enumerate(results):
                assert result['model_count'] == 1