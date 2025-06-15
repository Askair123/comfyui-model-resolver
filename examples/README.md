# ComfyUI Workflow Examples

This directory contains example ComfyUI workflows for testing the model resolver.

## flux-workflow-example.json

A complex Flux workflow that includes:
- **UNET Models**: flux1-dev-11gb-fp8.safetensors, flux1-dev-Q4_0.gguf
- **CLIP Models**: t5xxl_fp8_e4m3fn.safetensors, clip_l.safetensors
- **VAE Model**: ae.safetensors
- **LoRA Model**: Cute_3d_Cartoon_Flux.safetensors
- **GGUF Models**: Multiple quantized models from city96

### Usage

```bash
# From project root
./resolve_models.py examples/flux-workflow-example.json

# With Civitai API key for LoRA models
./resolve_models.py examples/flux-workflow-example.json --civitai-key YOUR_KEY

# Generate download script
./resolve_models.py examples/flux-workflow-example.json --download-script download-flux.sh
```

### Expected Results

This workflow should find all 8 models:
- 7 models from HuggingFace
- 1 LoRA model from Civitai (Cute_3d_Cartoon_Flux)

The resolver will:
1. Detect all models using V3 analyzer
2. Route LoRA to Civitai platform
3. Find GGUF models in city96/Kijai repositories
4. Generate complete download commands