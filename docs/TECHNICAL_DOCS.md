# Technical Documentation

## Architecture Overview

The ComfyUI Model Resolver is designed with a modular architecture:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CLI Interface │────▶│  Core Modules    │────▶│  Integrations   │
│  (Click-based)  │     │  (Analysis/Match)│     │  (HF/Download)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                        │                         │
         └────────────────────────┴─────────────────────────┘
                                  │
                          ┌───────▼────────┐
                          │     Utils      │
                          │ (Cache/Config) │
                          └────────────────┘
```

## Core Modules

### WorkflowAnalyzer

**Purpose**: Extracts model dependencies from ComfyUI workflow JSON files.

```python
from src.core.workflow_analyzer import WorkflowAnalyzer

analyzer = WorkflowAnalyzer()
result = analyzer.analyze_workflow("workflow.json")

# Result structure:
{
    "total_nodes": 10,
    "model_count": 3,
    "models": [
        {
            "node_id": 1,
            "node_type": "CheckpointLoaderSimple",
            "model_type": "checkpoint",
            "filename": "model.safetensors",
            "original_value": "model.safetensors"
        }
    ],
    "workflow_name": "workflow.json"
}
```

**Node Type Mapping**:
- `CheckpointLoaderSimple` → checkpoint
- `LoraLoader` → lora
- `VAELoader` → vae
- `ControlNetLoader` → controlnet
- `CLIPLoader` → clip
- `UpscaleModelLoader` → upscale

### KeywordExtractor

**Purpose**: Extracts meaningful keywords from model filenames for fuzzy matching.

```python
from src.core.keyword_extractor import KeywordExtractor

extractor = KeywordExtractor()
keywords = extractor.extract_keywords("epicRealism_naturalSinRC1VAE.safetensors")
# Result: ['epic', 'realism', 'natural', 'sin', 'rc', 'vae']
```

**Filtering Rules**:
1. Removes file extensions
2. Splits on separators: `_`, `-`, `.`, ` `
3. Filters version identifiers: `v1`, `q4`, `fp16`, etc.
4. Converts camelCase to separate words
5. Converts to lowercase
6. Removes duplicates

### LocalScanner

**Purpose**: Scans local directories for models and performs fuzzy matching.

```python
from src.core.local_scanner import LocalScanner

scanner = LocalScanner("/workspace/ComfyUI/models")
models = scanner.scan_directory("checkpoints")

# Find by keywords
matches = scanner.find_models_by_keywords(
    ["epic", "realism"], 
    model_type="checkpoint",
    threshold=0.7
)
```

**Features**:
- Recursive directory scanning
- File metadata extraction
- Keyword-based fuzzy matching
- Similarity scoring
- Results caching

### ModelMatcher

**Purpose**: Orchestrates matching workflow requirements against local models.

```python
from src.core.model_matcher import ModelMatcher

matcher = ModelMatcher("/workspace/ComfyUI/models")
results = matcher.match_workflow_models("workflow.json")

# Results structure:
{
    "found": [MatchResult(...)],
    "partial": [MatchResult(...)],
    "missing": [MatchResult(...)]
}
```

**Match Categories**:
- **Found**: 100% match or file exists
- **Partial**: Similarity ≥ threshold (default 0.7)
- **Missing**: No match found

## Integration Modules

### HuggingFaceSearcher

**Purpose**: Searches HuggingFace for models using their API.

```python
from src.integrations.hf_searcher import HuggingFaceSearcher

searcher = HuggingFaceSearcher()

# Async usage
result = await searcher.search_model("sd_xl_base_1.0.safetensors")

# Sync wrapper
result = searcher.search_sync("model.safetensors")
```

**Search Strategy**:
1. Direct filename search
2. Keyword-based search
3. Model type filtering
4. Result ranking by relevance

**Caching**:
- 24-hour cache by default
- Reduces API calls
- Configurable expiry

### ModelDownloader

**Purpose**: Downloads models from multiple platforms with progress tracking.

```python
from src.integrations.downloader import ModelDownloader

downloader = ModelDownloader("/workspace/ComfyUI/models")

# Single download
success = await downloader.download_model(
    url="https://huggingface.co/...",
    model_type="checkpoint",
    filename="model.safetensors",
    progress_callback=progress_fn
)

# Batch download
results = await downloader.batch_download(download_list)
```

**Supported Platforms**:
- HuggingFace (with token support)
- Civitai (with token support)  
- GitHub releases
- Direct URLs

**Features**:
- Concurrent downloads
- Progress tracking
- Retry logic
- Temporary files for safety
- Platform-specific headers

## Utility Modules

### ConfigLoader

**Purpose**: Manages configuration with defaults and overrides.

```python
from src.utils.config_loader import ConfigLoader

config = ConfigLoader("custom_config.yaml")

# Access nested values
models_path = config.get("paths.models_base", "/default/path")

# Override values
config.set("download.max_concurrent", 5)
```

**Default Configuration Structure**:
```yaml
paths:
  comfyui_base: "/workspace/ComfyUI"
  models_base: "/workspace/ComfyUI/models"

cache:
  enabled: true
  directory: "~/.comfyui-resolver/cache"
  ttl_hours: 24

download:
  chunk_size_mb: 4
  max_concurrent_downloads: 3
  use_temp_files: true
  retry_attempts: 3
```

### CacheManager

**Purpose**: Provides persistent caching for various operations.

```python
from src.utils.cache_manager import CacheManager

cache = CacheManager()

# Set cache entry
cache.set("key", data, cache_type="search", ttl_hours=24)

# Get cache entry
data = cache.get("key", cache_type="search")

# Cache statistics
stats = cache.get_stats()
```

**Cache Types**:
- `search`: API search results
- `model`: Model metadata
- `general`: General purpose

### Logger

**Purpose**: Colored logging with configurable levels.

```python
from src.utils.logger import setup_colored_logger

logger = setup_colored_logger(level="INFO")
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
```

## API Reference

### CLI Commands

#### `analyze`
```bash
comfyui-resolver analyze <workflow_file> [options]

Options:
  -o, --output PATH  Output file for analysis results
```

#### `check`
```bash
comfyui-resolver check <workflow_file> [options]

Options:
  --no-cache         Disable cache usage
  -t, --threshold    Similarity threshold (0.0-1.0)
  -e, --export PATH  Export missing models to JSON
```

#### `search`
```bash
comfyui-resolver search <models_file> [options]

Options:
  --use-cache/--no-cache  Use cached results
  -o, --output PATH       Output file for results
```

#### `download`
```bash
comfyui-resolver download <download_file> [options]

Options:
  --dry-run         Show what would be downloaded
  -j, --concurrent  Number of concurrent downloads
```

#### `resolve`
```bash
comfyui-resolver resolve <workflow_file> [options]

Options:
  --download/--no-download  Auto-download missing models
  -t, --threshold          Similarity threshold
```

### Python API

#### Basic Usage

```python
# Direct module usage
from comfyui_model_resolver import (
    WorkflowAnalyzer,
    ModelMatcher,
    HuggingFaceSearcher,
    ModelDownloader
)

# Analyze workflow
analyzer = WorkflowAnalyzer()
models = analyzer.analyze_workflow("workflow.json")

# Check local models
matcher = ModelMatcher("/workspace/ComfyUI/models")
results = matcher.match_workflow_models("workflow.json")

# Search online
searcher = HuggingFaceSearcher()
found = searcher.search_sync("model.safetensors")

# Download
downloader = ModelDownloader("/workspace/ComfyUI/models")
success = downloader.download_sync(url, "checkpoint", "model.safetensors")
```

#### Advanced Integration

```python
import asyncio
from comfyui_model_resolver import ModelResolver

async def resolve_workflow(workflow_path):
    resolver = ModelResolver()
    
    # Full pipeline
    analysis = await resolver.analyze(workflow_path)
    matches = await resolver.match(analysis)
    search_results = await resolver.search(matches['missing'])
    download_results = await resolver.download(search_results)
    
    return download_results

# Run
asyncio.run(resolve_workflow("workflow.json"))
```

## Extension Points

### Custom Model Types

Add new model types in `WorkflowAnalyzer`:

```python
# In src/core/workflow_analyzer.py
self.node_type_mapping = {
    "YourCustomLoader": "your_type",
    # ...
}
```

And in `ModelDownloader`:

```python
# In src/integrations/downloader.py
type_to_dir = {
    'your_type': 'your_directory',
    # ...
}
```

### Custom Search Providers

Implement the search interface:

```python
class CustomSearcher:
    async def search_model(self, filename: str) -> Optional[Dict]:
        # Your implementation
        return {
            'url': 'download_url',
            'filename': filename,
            'source': 'custom',
            'metadata': {}
        }
```

### Custom Matchers

Extend the matching algorithm:

```python
class CustomMatcher(ModelMatcher):
    def calculate_similarity(self, keywords1, keywords2):
        # Your similarity algorithm
        return score
```

## Performance Considerations

### Caching Strategy

- **Search results**: 24-hour TTL
- **Model scans**: 1-hour TTL  
- **Invalidation**: Manual or on file changes

### Concurrent Operations

- **Downloads**: Default 3, max 10
- **API calls**: Rate limited by platform
- **File I/O**: Async where beneficial

### Memory Usage

- **Large workflows**: Streamed parsing
- **Model lists**: Paginated results
- **Download buffers**: 4MB chunks

## Error Handling

### Common Exceptions

```python
# Workflow parsing
WorkflowParseError: Invalid JSON or format

# File operations  
ModelDirectoryError: Directory not found/accessible

# Network operations
DownloadError: Connection or transfer failure

# API errors
SearchAPIError: Rate limit or service error
```

### Recovery Strategies

1. **Automatic retry**: Network operations retry 3 times
2. **Fallback search**: Multiple search strategies
3. **Partial results**: Continue despite individual failures
4. **Graceful degradation**: Cache-only mode on API failure