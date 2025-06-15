# ComfyUI Model Resolver API Documentation

## Core Components

### WorkflowAnalyzerV3

The main workflow analyzer that extracts model dependencies from ComfyUI workflows.

```python
from src.core.workflow_analyzer_v3 import WorkflowAnalyzerV3

analyzer = WorkflowAnalyzerV3()
analysis = analyzer.analyze_workflow('workflow.json')

# Returns:
{
    'model_count': 8,
    'models': [
        {
            'filename': 'flux1-dev-fp8.safetensors',
            'model_type': 'unet',
            'node_id': '123',
            'node_type': 'UNETLoader',
            'detection_strategy': 'known_loader'
        },
        ...
    ]
}
```

### MultiPlatformSearcher

Intelligent multi-platform model searcher with routing logic.

```python
from src.integrations.multi_platform_searcher import MultiPlatformSearcher

searcher = MultiPlatformSearcher(
    civitai_token='your-token',
    hf_token='optional-token'
)

# Identify best platform for a model
strategy = searcher.identify_model_type_and_platform('cute_3d_cartoon_flux.safetensors')
# Returns: {'type': 'lora', 'platform_priority': ['civitai', 'huggingface']}

# Search for a model
result = searcher.search_sync('model.safetensors', model_type='lora')
```

### OptimizedModelSearcher

Advanced search term optimization and model name parsing.

```python
from src.integrations.optimized_search import OptimizedModelSearcher

optimizer = OptimizedModelSearcher()

# Parse model name
components = optimizer.parse_model_name('flux1-dev-11gb-fp8.safetensors')
# Returns: {
#     'series': 'flux',
#     'version': 'dev',
#     'quantization': 'fp8',
#     'extension': '.safetensors'
# }

# Generate search terms
terms = optimizer.generate_search_terms('flux1-dev-Q4_0.gguf')
# Returns: ['city96/FLUX.1-dev-gguf', 'Kijai/flux.1-dev-gguf', ...]
```

## Platform Integrations

### HuggingFaceSearcher

```python
from src.integrations.hf_searcher import HuggingFaceSearcher

hf_searcher = HuggingFaceSearcher(api_token='optional')
result = await hf_searcher.search_model('flux1-dev-fp8.safetensors')
```

### CivitaiSearcher

```python
from src.integrations.civitai_searcher import CivitaiSearcher

civitai_searcher = CivitaiSearcher(api_key='required')
result = await civitai_searcher.search_model(
    'cute_3d_cartoon_flux.safetensors',
    model_type='lora'
)
```

## Utilities

### CacheManager

Efficient caching system for search results.

```python
from src.utils.cache_manager import CacheManager

cache = CacheManager(cache_dir='~/.cache/comfyui-model-resolver')

# Set cache
cache.set('key', data, cache_type='search')

# Get cache
data = cache.get('key', cache_type='search')

# Clear cache
cache.clear_all()
```

### Downloader

Parallel download manager with progress tracking.

```python
from src.utils.downloader import Downloader

downloader = Downloader(max_concurrent=3)

# Download single file
await downloader.download_file(
    url='https://...',
    destination='/path/to/file',
    show_progress=True
)

# Batch download
download_plan = [
    {'url': '...', 'destination': '...'},
    ...
]
results = await downloader.download_batch(download_plan)
```

## Complete Resolution Function

The main function that orchestrates the entire resolution process:

```python
from workflow_resolver import complete_workflow_resolution

# Basic usage
report = complete_workflow_resolution('workflow.json')

# With custom base path
import os
os.environ['MODELS_BASE'] = '/custom/path'
report = complete_workflow_resolution('workflow.json')
```

## Model Type Override

For better platform routing, you can override detected model types:

```python
def override_model_type(filename, original_type):
    """Override model type based on filename patterns."""
    lora_indicators = ['lora', 'cute', 'cartoon', 'anime', 'style']
    
    if any(indicator in filename.lower() for indicator in lora_indicators):
        if any(series in filename.lower() for series in ['flux', 'sdxl', 'sd']):
            return 'lora'
    
    return original_type
```

## Error Handling

All API methods include proper error handling:

```python
try:
    result = searcher.search_sync('model.safetensors')
    if result and result.get('url'):
        print(f"Found: {result['url']}")
    else:
        print("Not found")
        if result and 'suggestions' in result:
            print("Suggestions:", result['suggestions'])
except Exception as e:
    print(f"Search error: {e}")
```

## Async Support

Most search operations support both async and sync modes:

```python
# Async
result = await searcher.search_model('model.safetensors')

# Sync wrapper
result = searcher.search_sync('model.safetensors')

# Batch operations
results = await searcher.batch_search(models, max_concurrent=5)
```