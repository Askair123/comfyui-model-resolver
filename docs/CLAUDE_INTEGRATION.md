# Claude Integration Guide

This guide explains how to use the ComfyUI Model Resolver with Claude's MCP tools.

## Overview

The ComfyUI Model Resolver is designed to work in two modes:

1. **Standalone Mode**: Use the CLI scripts directly on the Pod
2. **Claude-Assisted Mode**: Claude handles model search using MCP tools

## Claude Workflow

When a user asks Claude to help download missing models for a ComfyUI workflow:

### Step 1: Upload Scripts to Pod

Claude should first ensure the resolver scripts are available on the Pod:

```bash
# Create directory
ssh user@pod "mkdir -p /workspace/comfyui-model-resolver"

# Upload the resolver
scp -r /path/to/comfyui-model-resolver/* user@pod:/workspace/comfyui-model-resolver/
```

### Step 2: Analyze and Check Workflow

Run the analysis on the Pod:

```bash
# Analyze workflow
python /workspace/comfyui-model-resolver/scripts/model_resolver.py analyze /path/to/workflow.json -o analysis.json

# Check against local models
python /workspace/comfyui-model-resolver/scripts/model_resolver.py check /path/to/workflow.json -e missing.json
```

### Step 3: Claude Searches for Models

Claude reads the `missing.json` file and uses MCP tools to search:

1. **Use HuggingFace MCP** (`mcp__hf-mcp-server__model_search`):
   ```
   - Search for each missing model by name
   - Try variations of the name if exact match fails
   ```

2. **Use Tavily MCP** (`mcp__tavily__tavily-search`):
   ```
   - For models not found on HuggingFace
   - Search: "ComfyUI model [model_name] download"
   - Look for Civitai or GitHub links
   ```

### Step 4: Generate Download List

Claude creates a JSON file with download URLs:

```json
{
  "models": [
    {
      "name": "epicrealism_v5.safetensors",
      "type": "checkpoint",
      "url": "https://huggingface.co/...",
      "source": "huggingface"
    },
    {
      "name": "control_openpose.safetensors",
      "type": "controlnet",
      "url": "https://civitai.com/...",
      "source": "civitai"
    }
  ]
}
```

### Step 5: Execute Downloads

Send the download list to the Pod and execute:

```bash
# Upload download list
scp downloads.json user@pod:/workspace/

# Execute downloads
python /workspace/comfyui-model-resolver/scripts/model_resolver.py download /workspace/downloads.json
```

## Claude Command Examples

### Simple Request
```
User: "Help me download missing models for workflow-outfit.json on Pod xyz"

Claude:
1. Analyzes the workflow
2. Checks local models
3. Searches for missing models using MCP
4. Downloads the found models
```

### Manual Control
```
User: "Check what models are missing from my workflow but don't download yet"

Claude:
1. Runs analysis and check
2. Shows the missing models list
3. Waits for user confirmation
```

### Search Only
```
User: "Find download links for these models: epicrealism.safetensors, controlnet_openpose.pth"

Claude:
1. Uses HuggingFace MCP to search
2. Falls back to Tavily for not found
3. Provides downloadable links
```

## MCP Tool Usage Tips

### HuggingFace MCP
```python
# Best for official model names
result = mcp__hf-mcp-server__model_search(
    query="epicrealism",
    task="text-to-image"
)
```

### Tavily Search
```python
# Best for Civitai and community models
result = mcp__tavily__tavily-search(
    query="ComfyUI epicrealism model download civitai",
    search_depth="advanced",
    max_results=5
)
```

## Error Handling

### Model Not Found
- Try alternative search terms
- Check for typos or version numbers
- Search for similar models as alternatives

### Download Failed
- Verify URL is accessible
- Check if authentication is needed
- Try alternative download sources

### Path Issues
- Ensure models go to correct directories
- Verify ComfyUI can read the locations
- Check file permissions

## Integration Script

Claude can use this template to handle requests:

```python
# 1. Get workflow from user
workflow_path = "/path/to/workflow.json"

# 2. Run analysis on Pod
analysis_cmd = f"python /workspace/resolver/scripts/model_resolver.py check {workflow_path} -e /tmp/missing.json"
# Execute via SSH

# 3. Read missing models
# Read /tmp/missing.json from Pod

# 4. Search using MCP tools
for model in missing_models:
    # Try HuggingFace first
    hf_result = search_huggingface(model['name'])
    
    if not hf_result:
        # Try Tavily
        tavily_result = search_tavily(f"ComfyUI {model['name']} download")
    
    # Add to download list

# 5. Execute downloads
# Send download list to Pod and run download command
```

## Best Practices

1. **Always verify paths**: Ensure models go to the correct directories
2. **Check file sizes**: Verify downloads completed successfully
3. **Cache searches**: Results are cached to avoid repeated API calls
4. **Batch operations**: Download multiple models concurrently
5. **Provide feedback**: Show progress to the user

## Limitations

- Some models may require authentication
- Civitai links may need special handling
- Large models (>5GB) may timeout
- Not all models are publicly available