# ComfyUI Model Resolver User Guide

## Quick Start

### Installation

1. **On RunPod Pod**:
   ```bash
   # Clone or download the resolver
   cd /workspace
   git clone https://github.com/your-repo/comfyui-model-resolver.git
   
   # Install
   cd comfyui-model-resolver
   ./scripts/deploy.sh
   ```

2. **Local Installation**:
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage

#### 1. Check Missing Models in a Workflow

```bash
# Basic check
comfyui-resolver check /path/to/workflow.json

# With custom threshold for fuzzy matching
comfyui-resolver check workflow.json -t 0.8

# Export missing models list
comfyui-resolver check workflow.json -e missing_models.json
```

#### 2. Resolve All Dependencies Automatically

```bash
# Analyze, search, and download all missing models
comfyui-resolver resolve workflow.json

# Check only, don't download
comfyui-resolver resolve workflow.json --no-download
```

#### 3. Search for Models

```bash
# Search from a missing models list
comfyui-resolver search missing_models.json

# Save search results
comfyui-resolver search missing_models.json -o found_models.json
```

#### 4. Download Models

```bash
# Download from a prepared list
comfyui-resolver download found_models.json

# Dry run to see what would be downloaded
comfyui-resolver download found_models.json --dry-run

# Adjust concurrent downloads
comfyui-resolver download found_models.json -j 5
```

## Common Workflows

### Scenario 1: New Workflow Setup

You've downloaded a new workflow and want to get all required models:

```bash
# One command to do everything
comfyui-resolver resolve amazing_workflow.json
```

Output:
```
Step 1: Analyzing workflow...
Step 2: Checking local models...
  ✓ Found: sdxl_vae.safetensors (100% match)
  ✗ Missing: epicrealism_v5.safetensors
  ✗ Missing: control_openpose.safetensors
Step 3: Searching for missing models...
  ✓ Found: epicrealism_v5.safetensors
  ✓ Found: control_openpose.safetensors
Step 4: Downloading 2 models...
  epicrealism_v5.safetensors: 100% (45.2 MB/s)
  control_openpose.safetensors: 100% (38.7 MB/s)
Download Summary:
  Success: 2/2
```

### Scenario 2: Check Before Downloading

You want to see what's missing before downloading:

```bash
# Step 1: Check what's missing
comfyui-resolver check workflow.json -e missing.json

# Step 2: Review the missing.json file
cat missing.json

# Step 3: Search for download links
comfyui-resolver search missing.json -o downloads.json

# Step 4: Download when ready
comfyui-resolver download downloads.json
```

### Scenario 3: Partial Matches

The resolver found similar models but not exact matches:

```bash
comfyui-resolver check workflow.json
```

Output:
```
Model Matching Report
====================
Total models required: 3
✓ Found: 1
⚠ Partial matches: 1
✗ Missing: 1

Partial Matches:
  Required: epicrealism_naturalSinRC1VAE.safetensors
  Found: epicrealism_naturalSin.safetensors (85% match)
  Suggestion: May work, but verify compatibility
```

### Scenario 4: Working with Claude

When Claude is helping you:

1. **Claude analyzes your workflow**:
   ```bash
   # On Pod
   comfyui-resolver check workflow.json -e missing.json
   ```

2. **Claude searches using MCP tools** for models in missing.json

3. **Claude provides download commands**:
   ```bash
   # Download the models Claude found
   comfyui-resolver download claude_found_models.json
   ```

## Configuration

### Custom Model Paths

Edit `~/.comfyui-resolver/config.yaml`:

```yaml
paths:
  comfyui_base: "/workspace/ComfyUI"
  models_base: "/workspace/ComfyUI/models"
```

Or use command line:
```bash
comfyui-resolver --base-path /custom/path check workflow.json
```

### Environment Variables

```bash
# HuggingFace token for private models
export HF_TOKEN="hf_xxxxxxxxxxxx"

# Civitai token for faster downloads
export CIVITAI_TOKEN="xxxxxxxxxx"
```

### Cache Management

```bash
# View cache statistics
comfyui-resolver cache-stats

# Clear all caches
comfyui-resolver clear-cache

# Clear specific cache
comfyui-resolver clear-cache --type search
```

## Model Type Mapping

The resolver automatically determines where to save models:

| Model Type | Directory | File Types |
|------------|-----------|------------|
| checkpoint | `/models/checkpoints/` | `.safetensors`, `.ckpt` |
| lora | `/models/loras/` | `.safetensors`, `.pt` |
| vae | `/models/vae/` | `.safetensors`, `.pt` |
| controlnet | `/models/controlnet/` | `.safetensors`, `.pth` |
| embeddings | `/models/embeddings/` | `.pt`, `.safetensors` |
| upscale | `/models/upscale_models/` | `.pth`, `.pt` |

## Tips and Best Practices

### 1. Fuzzy Matching Threshold

- **0.9-1.0**: Very strict, only near-exact matches
- **0.7-0.8**: Balanced, catches most variations (default: 0.7)
- **0.5-0.6**: Loose, may have false positives

```bash
# Strict matching for production
comfyui-resolver check workflow.json -t 0.9

# Loose matching for exploration
comfyui-resolver check workflow.json -t 0.6
```

### 2. Handling Large Downloads

```bash
# Reduce concurrent downloads for stability
comfyui-resolver download models.json -j 1

# Use screen/tmux for long downloads
screen -S download
comfyui-resolver resolve workflow.json
# Ctrl+A, D to detach
```

### 3. Verifying Downloads

After downloading, run check again:
```bash
comfyui-resolver check workflow.json
# Should show all models as found
```

### 4. Workflow Organization

Keep workflows organized with their models:
```
workflows/
├── portrait/
│   ├── workflow.json
│   ├── workflow_models.json
│   └── README.md
└── landscape/
    ├── workflow.json
    └── workflow_models.json
```

## Troubleshooting

### "Model not found" but you know it exists

1. Check the exact filename in the workflow
2. Try searching manually with variations:
   ```bash
   # Create a simple JSON with the model
   echo '{"models": [{"name": "model_name.safetensors", "type": "checkpoint"}]}' > test.json
   comfyui-resolver search test.json
   ```

### Downloads failing

1. Check internet connection
2. Verify tokens are set correctly:
   ```bash
   echo $HF_TOKEN
   echo $CIVITAI_TOKEN
   ```
3. Try wget directly:
   ```bash
   wget -P /workspace/ComfyUI/models/checkpoints/ "URL_HERE"
   ```

### Partial matches not working

1. Adjust threshold:
   ```bash
   comfyui-resolver check workflow.json -t 0.5
   ```
2. Check keywords extraction:
   ```bash
   # The tool shows extracted keywords in debug mode
   ```

### Cache issues

```bash
# Clear and retry
comfyui-resolver clear-cache --type all
comfyui-resolver check workflow.json --no-cache
```

## Advanced Usage

### Batch Processing

Process multiple workflows:
```bash
#!/bin/bash
for workflow in workflows/*.json; do
    echo "Processing $workflow"
    comfyui-resolver resolve "$workflow" --no-download
done
```

### Integration with ComfyUI Manager

The resolver complements ComfyUI Manager:
1. Use resolver for workflow-specific models
2. Use Manager for custom nodes and dependencies

### Custom Scripts

Create workflow-specific scripts:
```bash
#!/bin/bash
# download_portrait_models.sh

# Check and download models for portrait workflow
comfyui-resolver resolve portrait_workflow.json \
    --threshold 0.8 \
    --download

# Verify
comfyui-resolver check portrait_workflow.json
```

## Getting Help

### Command Help
```bash
# General help
comfyui-resolver --help

# Command-specific help
comfyui-resolver check --help
```

### Debug Mode
Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
comfyui-resolver check workflow.json
```

### Support

- Check existing issues on GitHub
- Review the [Technical Documentation](TECHNICAL_DOCS.md)
- Contact support with workflow and error logs