"""
Workflow Service - Business logic for workflow operations
"""

from typing import List, Dict, Any, Optional
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import logging
import time

# Import from existing core modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3
from src.core.local_scanner import LocalModelScanner

from ..models.workflow import (
    WorkflowModel, ModelInfo, WorkflowStatus,
    AnalyzeResponse, ExportScriptResponse
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow analysis and management."""
    
    def __init__(self):
        self.analyzer = WorkflowAnalyzerV3()
        self.local_scanner = LocalModelScanner()
        self.data_file = Path("data/resolver_data.json")
        self._init_data_file()
    
    def _init_data_file(self):
        """Initialize data file if not exists."""
        self.data_file.parent.mkdir(exist_ok=True)
        if not self.data_file.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save data to JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    async def scan_directory(self, directory: str) -> List[WorkflowModel]:
        """Scan directory for workflow files."""
        workflows = []
        data = self._load_data()
        
        try:
            # List all JSON files
            for file in os.listdir(directory):
                if file.endswith('.json') and not file.startswith('.'):
                    filepath = os.path.join(directory, file)
                    
                    # Get file stats
                    stat = os.stat(filepath)
                    
                    # Check cached status
                    cached = data.get('workflows', {}).get(filepath, {})
                    
                    # Determine status
                    if cached and cached.get('last_analyzed'):
                        status = WorkflowStatus(cached.get('status', 'unanalyzed'))
                        total_models = cached.get('total_models', 0)
                        missing_count = cached.get('missing_count', 0)
                        last_analyzed = datetime.fromisoformat(cached['last_analyzed'])
                    else:
                        status = WorkflowStatus.UNANALYZED
                        total_models = 0
                        missing_count = 0
                        last_analyzed = None
                    
                    workflows.append(WorkflowModel(
                        path=filepath,
                        name=file,
                        status=status,
                        total_models=total_models,
                        missing_count=missing_count,
                        last_analyzed=last_analyzed,
                        size_bytes=stat.st_size
                    ))
            
            # Sort by name
            workflows.sort(key=lambda w: w.name)
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return workflows
    
    async def analyze_workflows(self, workflow_paths: List[str], 
                               check_local: bool = True) -> AnalyzeResponse:
        """Analyze multiple workflows."""
        start_time = time.time()
        all_workflows = []
        all_models = {}
        
        for path in workflow_paths:
            try:
                # Analyze workflow
                result = self.analyzer.analyze_workflow(path)
                
                # Process models
                for model_data in result['models']:
                    filename = model_data['filename']
                    
                    # Check if already processed
                    if filename not in all_models:
                        model_info = ModelInfo(
                            filename=filename,
                            model_type=model_data.get('model_type', 'unknown'),
                            exists_locally=False,
                            detection_sources=model_data.get('sources', []),
                            node_types=model_data.get('node_types', [])
                        )
                        
                        # Check local existence if requested
                        if check_local:
                            local_info = await self._check_local_model(filename, model_data.get('model_type'))
                            if local_info:
                                model_info.exists_locally = True
                                model_info.local_path = local_info['path']
                                model_info.size = local_info.get('size')
                        
                        # Default selection based on existence
                        model_info.selected = not model_info.exists_locally
                        
                        all_models[filename] = model_info
                
                # Calculate workflow status
                total_models = len(result['models'])
                missing_count = sum(1 for m in all_models.values() if not m.exists_locally)
                
                if missing_count == 0:
                    status = WorkflowStatus.READY
                elif missing_count == total_models:
                    status = WorkflowStatus.MISSING
                else:
                    status = WorkflowStatus.PARTIAL
                
                # Create workflow model
                workflow = WorkflowModel(
                    path=path,
                    name=os.path.basename(path),
                    status=status,
                    total_models=total_models,
                    missing_count=missing_count,
                    last_analyzed=datetime.now()
                )
                all_workflows.append(workflow)
                
                # Update cache
                await self._update_workflow_cache(path, workflow, list(all_models.values()))
                
            except Exception as e:
                logger.error(f"Error analyzing workflow {path}: {e}")
        
        # Prepare response
        total_models = len(all_models)
        missing_models = sum(1 for m in all_models.values() if not m.exists_locally)
        
        return AnalyzeResponse(
            workflows=all_workflows,
            models=list(all_models.values()),
            total_models=total_models,
            missing_models=missing_models,
            analysis_time=time.time() - start_time
        )
    
    async def _check_local_model(self, filename: str, model_type: str) -> Optional[Dict]:
        """Check if model exists locally."""
        try:
            # Use local scanner to find model
            results = self.local_scanner.scan_for_model(filename, model_type)
            if results:
                # Return first match
                return {
                    'path': results[0]['path'],
                    'size': results[0].get('size')
                }
        except Exception as e:
            logger.error(f"Error checking local model {filename}: {e}")
        
        return None
    
    async def _update_workflow_cache(self, workflow_path: str, 
                                   workflow: WorkflowModel,
                                   models: List[ModelInfo]):
        """Update workflow cache."""
        data = self._load_data()
        
        if 'workflows' not in data:
            data['workflows'] = {}
        
        data['workflows'][workflow_path] = {
            'status': workflow.status.value,
            'total_models': workflow.total_models,
            'missing_count': workflow.missing_count,
            'last_analyzed': workflow.last_analyzed.isoformat() if workflow.last_analyzed else None,
            'models': [
                {
                    'filename': m.filename,
                    'model_type': m.model_type,
                    'exists_locally': m.exists_locally,
                    'local_path': m.local_path
                }
                for m in models
            ]
        }
        
        self._save_data(data)
    
    async def get_workflow_status(self, workflow_path: str) -> WorkflowModel:
        """Get workflow status from cache or analyze."""
        data = self._load_data()
        cached = data.get('workflows', {}).get(workflow_path)
        
        if cached:
            return WorkflowModel(
                path=workflow_path,
                name=os.path.basename(workflow_path),
                status=WorkflowStatus(cached['status']),
                total_models=cached['total_models'],
                missing_count=cached['missing_count'],
                last_analyzed=datetime.fromisoformat(cached['last_analyzed']) if cached.get('last_analyzed') else None
            )
        
        # Not cached, analyze it
        result = await self.analyze_workflows([workflow_path])
        return result.workflows[0]
    
    async def get_workflow_models(self, workflow_path: str) -> List[ModelInfo]:
        """Get models for a specific workflow."""
        # Check cache first
        data = self._load_data()
        cached = data.get('workflows', {}).get(workflow_path)
        
        if cached and cached.get('models'):
            return [
                ModelInfo(**model)
                for model in cached['models']
            ]
        
        # Analyze if not cached
        result = await self.analyze_workflows([workflow_path])
        return result.models
    
    async def export_download_script(self, workflow_paths: List[str],
                                   include_existing: bool = False,
                                   output_format: str = "bash") -> ExportScriptResponse:
        """Export download script for workflows."""
        # Analyze all workflows
        result = await self.analyze_workflows(workflow_paths)
        
        # Filter models
        models_to_download = []
        for model in result.models:
            if include_existing or not model.exists_locally:
                models_to_download.append(model)
        
        # Generate script based on format
        if output_format == "bash":
            script = self._generate_bash_script(models_to_download)
        elif output_format == "powershell":
            script = self._generate_powershell_script(models_to_download)
        elif output_format == "python":
            script = self._generate_python_script(models_to_download)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Calculate total size
        total_size = sum(m.size or 0 for m in models_to_download)
        total_size_gb = total_size / (1024 ** 3)
        
        return ExportScriptResponse(
            script_content=script,
            total_models=len(models_to_download),
            total_size_gb=round(total_size_gb, 2),
            output_format=output_format
        )
    
    def _generate_bash_script(self, models: List[ModelInfo]) -> str:
        """Generate bash download script."""
        lines = [
            "#!/bin/bash",
            "# ComfyUI Model Resolver - Download Script",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Total models: {len(models)}",
            "",
            "# Create directories",
            "COMFYUI_ROOT=/workspace/ComfyUI",
            "mkdir -p $COMFYUI_ROOT/models/{checkpoints,loras,vae,controlnet,clip,unet,upscale_models,embeddings}",
            "",
            "# Download models",
        ]
        
        for model in models:
            # Determine target directory based on model type
            type_to_dir = {
                'checkpoint': 'checkpoints',
                'lora': 'loras',
                'vae': 'vae',
                'controlnet': 'controlnet',
                'clip': 'clip',
                'unet': 'unet',
                'upscale': 'upscale_models',
                'embeddings': 'embeddings'
            }
            
            target_dir = type_to_dir.get(model.model_type, 'checkpoints')
            target_path = f"$COMFYUI_ROOT/models/{target_dir}/{model.filename}"
            
            lines.extend([
                "",
                f"# {model.filename} ({model.model_type})",
                f"if [ ! -f \"{target_path}\" ]; then",
                f"    echo \"Downloading {model.filename}...\"",
                f"    # wget -c \"URL_HERE\" -O \"{target_path}\"",
                f"    echo \"Please search for {model.filename} and add download URL\"",
                f"else",
                f"    echo \"{model.filename} already exists\"",
                f"fi"
            ])
        
        lines.extend([
            "",
            "echo \"Download script completed!\""
        ])
        
        return "\n".join(lines)
    
    def _generate_powershell_script(self, models: List[ModelInfo]) -> str:
        """Generate PowerShell download script."""
        lines = [
            "# ComfyUI Model Resolver - Download Script",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Total models: {len(models)}",
            "",
            "# Create directories",
            "$ComfyUIRoot = \"C:\\ComfyUI\"",
            "@('checkpoints','loras','vae','controlnet','clip','unet','upscale_models','embeddings') | ForEach-Object {",
            "    New-Item -ItemType Directory -Path \"$ComfyUIRoot\\models\\$_\" -Force | Out-Null",
            "}",
            "",
            "# Download models",
        ]
        
        for model in models:
            type_to_dir = {
                'checkpoint': 'checkpoints',
                'lora': 'loras',
                'vae': 'vae',
                'controlnet': 'controlnet',
                'clip': 'clip',
                'unet': 'unet',
                'upscale': 'upscale_models',
                'embeddings': 'embeddings'
            }
            
            target_dir = type_to_dir.get(model.model_type, 'checkpoints')
            target_path = f"$ComfyUIRoot\\models\\{target_dir}\\{model.filename}"
            
            lines.extend([
                "",
                f"# {model.filename} ({model.model_type})",
                f"if (-Not (Test-Path \"{target_path}\")) {{",
                f"    Write-Host \"Downloading {model.filename}...\"",
                f"    # Invoke-WebRequest -Uri \"URL_HERE\" -OutFile \"{target_path}\"",
                f"    Write-Host \"Please search for {model.filename} and add download URL\"",
                f"}} else {{",
                f"    Write-Host \"{model.filename} already exists\"",
                f"}}"
            ])
        
        lines.extend([
            "",
            "Write-Host \"Download script completed!\""
        ])
        
        return "\n".join(lines)
    
    def _generate_python_script(self, models: List[ModelInfo]) -> str:
        """Generate Python download script."""
        lines = [
            "#!/usr/bin/env python3",
            "\"\"\"",
            "ComfyUI Model Resolver - Download Script",
            f"Generated: {datetime.now().isoformat()}",
            f"Total models: {len(models)}",
            "\"\"\"",
            "",
            "import os",
            "import requests",
            "from pathlib import Path",
            "",
            "# Configuration",
            "COMFYUI_ROOT = Path('/workspace/ComfyUI')",
            "",
            "# Create directories",
            "dirs = ['checkpoints', 'loras', 'vae', 'controlnet', 'clip', 'unet', 'upscale_models', 'embeddings']",
            "for dir_name in dirs:",
            "    (COMFYUI_ROOT / 'models' / dir_name).mkdir(parents=True, exist_ok=True)",
            "",
            "# Model download list",
            "models = ["
        ]
        
        for model in models:
            type_to_dir = {
                'checkpoint': 'checkpoints',
                'lora': 'loras',
                'vae': 'vae',
                'controlnet': 'controlnet',
                'clip': 'clip',
                'unet': 'unet',
                'upscale': 'upscale_models',
                'embeddings': 'embeddings'
            }
            
            target_dir = type_to_dir.get(model.model_type, 'checkpoints')
            
            lines.append(f"    {{")
            lines.append(f"        'filename': '{model.filename}',")
            lines.append(f"        'type': '{model.model_type}',")
            lines.append(f"        'dir': '{target_dir}',")
            lines.append(f"        'url': None  # Add URL here")
            lines.append(f"    }},")
        
        lines.extend([
            "]",
            "",
            "# Download models",
            "for model in models:",
            "    target_path = COMFYUI_ROOT / 'models' / model['dir'] / model['filename']",
            "    ",
            "    if not target_path.exists():",
            "        print(f\"Downloading {model['filename']}...\")",
            "        if model['url']:",
            "            # Download logic here",
            "            # response = requests.get(model['url'], stream=True)",
            "            # with open(target_path, 'wb') as f:",
            "            #     for chunk in response.iter_content(chunk_size=8192):",
            "            #         f.write(chunk)",
            "            print(f\"Please add download URL for {model['filename']}\")",
            "        else:",
            "            print(f\"No URL provided for {model['filename']}\")",
            "    else:",
            "        print(f\"{model['filename']} already exists\")",
            "",
            "print(\"Download script completed!\")"
        ])
        
        return "\n".join(lines)