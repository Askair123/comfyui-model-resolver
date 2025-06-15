# ComfyUI Model Resolver

A powerful tool for automatically finding and downloading AI models required by ComfyUI workflows. Now with a complete web interface for easier model management!

## 🎉 Version 2.0 - Web Interface Release

**New in v2.0:**
- 🌐 **Web Interface**: User-friendly Gradio interface for all operations
- ⚡ **Real-time Updates**: Live download progress with WebSocket support
- 🚀 **FastAPI Backend**: RESTful API for integration with other tools
- 🐳 **Docker Support**: Easy deployment with Docker/Docker Compose
- 📊 **Batch Operations**: Analyze multiple workflows simultaneously

[Quick Start with Web UI →](#web-interface-v20)

## Features

### Core Features (v1.0)
- 🔍 **100% Model Detection**: Advanced V3 analyzer with 6 detection strategies
- 🌐 **Multi-Platform Search**: Intelligent routing between HuggingFace and Civitai
- 🚀 **Optimized Search**: Smart search term generation and caching
- 🎯 **Type-Aware Routing**: LoRA models → Civitai, Official models → HuggingFace
- 📦 **GGUF Support**: Specialized search for quantized models (city96, Kijai)
- 💾 **Download Planning**: Generate wget commands or shell scripts
- 🔧 **Flexible Configuration**: YAML config with environment variable support

### New in v2.0
- 🖥️ **Web Dashboard**: Analyze workflows and manage downloads from browser
- 📡 **API Access**: Full REST API with automatic documentation
- 🔄 **Live Progress**: Real-time download status and queue management
- 📋 **Export Scripts**: Generate bash/powershell/python download scripts
- 🎨 **Chinese UI**: Localized interface for better user experience

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/comfyui-model-resolver.git
cd comfyui-model-resolver
pip install -r requirements.txt
```

### Basic Usage

```bash
# Analyze a workflow and find all models
./resolve_models.py workflow.json

# With Civitai API key
./resolve_models.py workflow.json --civitai-key YOUR_API_KEY

# Generate download script
./resolve_models.py workflow.json --download-script download.sh
./download.sh  # Run the generated script
```

### Configuration

Copy `config.example.yaml` to `config.yaml` and update:

```yaml
api_keys:
  civitai: "your-civitai-api-key"
  huggingface: "optional-hf-token"

paths:
  comfyui_base: "/workspace/comfyui"
  models_base: "/workspace/comfyui/models"
```

## Advanced Usage

### Command Line Options

```bash
# Use custom config
./resolve_models.py workflow.json --config my-config.yaml

# Override models path
./resolve_models.py workflow.json --models-path /custom/path/models

# Show only missing models
./resolve_models.py workflow.json --missing-only

# Disable cache for fresh search
./resolve_models.py workflow.json --no-cache

# Verbose output
./resolve_models.py workflow.json -v
```

### Python API

```python
from workflow_resolver import complete_workflow_resolution

# Set API keys
import os
os.environ['CIVITAI_API_KEY'] = 'your-key'

# Run resolution
report = complete_workflow_resolution('workflow.json')

# Access results
for model in report['models']:
    if model['search_result']['status'] == 'found':
        print(f"{model['filename']} -> {model['search_result']['url']}")
```

## Web Interface (v2.0)

### Starting the Web UI

The easiest way to use ComfyUI Model Resolver is through the web interface:

```bash
# Start the web interface
./start.sh

# Or manually start backend and frontend
python -m api.main &  # Start API backend
python -m frontend.app  # Start Gradio UI
```

Visit http://localhost:7860 in your browser to access the interface.

### Docker Deployment

For production deployment, use Docker:

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t comfyui-model-resolver .
docker run -p 7860:7860 -p 8000:8000 \
  -v /workspace/comfyui:/workspace/comfyui \
  comfyui-model-resolver
```

### Web UI Features

The web interface provides four main tabs:

1. **工作流分析 (Workflow Analysis)**
   - Select and analyze multiple workflows
   - View detected models and their status
   - Batch selection for missing models

2. **模型搜索 (Model Search)**
   - Search models across HuggingFace and Civitai
   - View model details and download links
   - Smart platform routing based on model type

3. **下载管理 (Download Manager)**
   - Queue-based download system
   - Real-time progress tracking
   - Pause/resume/cancel support

4. **批量导出 (Batch Export)**
   - Generate download scripts (bash/powershell/python)
   - Export model lists as JSON
   - Custom script templates

### API Documentation

The FastAPI backend provides a complete REST API:

- **API Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

Example API usage:

```python
import requests

# Analyze workflows
response = requests.post(
    "http://localhost:8000/api/workflow/analyze",
    json={
        "workflow_paths": ["/path/to/workflow.json"],
        "check_local": True
    }
)

# Search for models
response = requests.post(
    "http://localhost:8000/api/search",
    json={
        "model_names": ["flux1-dev-Q4_0.gguf"],
        "model_types": ["unet"]
    }
)
```

### Configuration for Web UI

The web interface uses the same `config.yaml` file. Additional settings:

```yaml
# Web UI specific settings
web:
  host: "0.0.0.0"
  port: 7860
  api_port: 8000
  
# Download settings
download:
  max_concurrent: 3
  chunk_size: 8192
  resume_enabled: true
```

## Platform Routing Logic

The resolver intelligently routes searches based on model characteristics:

| Model Type | Primary Platform | Fallback | Examples |
|------------|------------------|----------|----------|
| LoRA | Civitai | HuggingFace | cute_3d_cartoon_flux.safetensors |
| Official | HuggingFace | - | flux1-dev, sdxl-base-1.0 |
| GGUF Quantized | HuggingFace | - | flux1-dev-Q4_0.gguf |
| VAE/CLIP | HuggingFace | Civitai | ae.safetensors, clip_l.safetensors |

## Model Type Detection

The V3 analyzer uses multiple strategies to detect models:

1. **Known Loaders**: CheckpointLoaderSimple, LoraLoader, etc.
2. **Flux-Specific**: UNETLoader, DualCLIPLoader
3. **Path-Based**: Detects models in path strings
4. **Widget Values**: Scans all widget configurations
5. **GGUF Support**: Specialized GGUF model detection
6. **Custom Nodes**: Supports various custom node types

## Quantization Experts

For GGUF models, the resolver searches specialized repositories:

- **city96**: FLUX.1-dev-gguf, t5-encoder-gguf
- **Kijai**: flux.1-dev-gguf, Wan2.1-gguf

## API Keys

### Civitai API Key (Required for LoRA models)
Get your API key from: https://civitai.com/user/account

### HuggingFace Token (Optional)
For private repositories: https://huggingface.co/settings/tokens

## Output Format

The resolver generates a comprehensive JSON report:

```json
{
  "metadata": {
    "workflow": "workflow.json",
    "analysis_date": "2024-01-14T10:30:00",
    "resolver_version": "2.1"
  },
  "summary": {
    "total_models": 8,
    "found": 8,
    "not_found": 0,
    "success_rate": "100%"
  },
  "models": [...],
  "download_plan": [
    {
      "filename": "flux1-dev-Q4_0.gguf",
      "url": "https://huggingface.co/city96/FLUX.1-dev-gguf/resolve/main/flux1-dev-Q4_0.gguf",
      "platform": "huggingface",
      "target_path": "/workspace/comfyui/models/unet/flux1-dev-Q4_0.gguf"
    }
  ]
}
```

## Troubleshooting

### Models Not Found

1. **LoRA models classified as checkpoint**: The resolver includes type override logic for common LoRA patterns
2. **Missing Civitai models**: Ensure your API key is set correctly
3. **GGUF models not found**: Check if the model exists in city96 or Kijai repositories

### Cache Issues

Clear cache if getting stale results:
```bash
rm -rf ~/.cache/comfyui-model-resolver
```

## Project Structure

```
comfyui-model-resolver/
├── resolve_models.py          # Main CLI entry point
├── workflow_resolver.py       # Core resolution logic
├── config.example.yaml        # Example configuration
├── src/
│   ├── core/                  # Core functionality
│   │   ├── workflow_analyzer_v3.py
│   │   └── model_matcher.py
│   ├── integrations/          # Platform integrations
│   │   ├── hf_searcher.py
│   │   ├── civitai_searcher.py
│   │   ├── multi_platform_searcher.py
│   │   └── optimized_search.py
│   └── utils/                 # Utilities
│       ├── cache_manager.py
│       ├── downloader.py
│       └── logger.py
├── examples/                  # Example workflows
└── docs/                      # Documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ComfyUI community for workflow examples
- city96 and Kijai for GGUF model repositories
- HuggingFace and Civitai for model hosting