#!/bin/bash
# ComfyUI Model Download Script
# Supports HuggingFace, GitHub, and Civitai downloads

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to download from HuggingFace
download_huggingface() {
    local url=$1
    local output_path=$2
    local filename=$(basename "$output_path")
    local temp_path="${output_path}.tmp"
    
    echo -e "${GREEN}Downloading from HuggingFace: ${filename}${NC}"
    wget -q --show-progress "$url" -O "$temp_path"
    
    if [ $? -eq 0 ] && [ -f "$temp_path" ]; then
        mv "$temp_path" "$output_path"
        return 0
    else
        rm -f "$temp_path"
        return 1
    fi
}

# Function to download from GitHub
download_github() {
    local url=$1
    local output_path=$2
    local filename=$(basename "$output_path")
    local temp_path="${output_path}.tmp"
    
    echo -e "${GREEN}Downloading from GitHub: ${filename}${NC}"
    curl -L -# -o "$temp_path" "$url"
    
    if [ $? -eq 0 ] && [ -f "$temp_path" ]; then
        mv "$temp_path" "$output_path"
        return 0
    else
        rm -f "$temp_path"
        return 1
    fi
}

# Function to download from Civitai
download_civitai() {
    local url=$1
    local output_path=$2
    local filename=$(basename "$output_path")
    local temp_path="${output_path}.tmp"
    local token=$CIVITAI_TOKEN
    
    echo -e "${GREEN}Downloading from Civitai: ${filename}${NC}"
    
    if [ -n "$token" ]; then
        # With token for faster downloads
        wget -q --show-progress --content-disposition \
             --header="Authorization: Bearer ${token}" \
             "$url" -O "$temp_path"
    else
        # Without token (may have rate limits)
        wget -q --show-progress --content-disposition \
             "$url" -O "$temp_path"
    fi
    
    if [ $? -eq 0 ] && [ -f "$temp_path" ]; then
        mv "$temp_path" "$output_path"
        return 0
    else
        rm -f "$temp_path"
        return 1
    fi
}

# Function to determine platform and download
download_model() {
    local url=$1
    local model_type=$2
    local filename=$3
    local base_path="/workspace/comfyui/models"
    
    # Determine target directory based on model type
    case $model_type in
        "checkpoint")
            target_dir="${base_path}/checkpoints"
            ;;
        "controlnet")
            target_dir="${base_path}/controlnet"
            ;;
        "lora")
            target_dir="${base_path}/loras"
            ;;
        "vae")
            target_dir="${base_path}/vae"
            ;;
        "upscale")
            target_dir="${base_path}/upscale_models"
            ;;
        "embeddings")
            target_dir="${base_path}/embeddings"
            ;;
        *)
            echo -e "${RED}Unknown model type: ${model_type}${NC}"
            return 1
            ;;
    esac
    
    # Create directory if it doesn't exist
    mkdir -p "$target_dir"
    
    # Full output path
    output_path="${target_dir}/${filename}"
    
    # Check if file already exists
    if [ -f "$output_path" ]; then
        echo -e "${YELLOW}File already exists: ${output_path}${NC}"
        return 0
    fi
    
    # Determine platform and download
    if [[ $url == *"huggingface.co"* ]]; then
        download_huggingface "$url" "$output_path"
    elif [[ $url == *"github.com"* ]]; then
        download_github "$url" "$output_path"
    elif [[ $url == *"civitai.com"* ]]; then
        download_civitai "$url" "$output_path"
    else
        echo -e "${RED}Unsupported platform for URL: ${url}${NC}"
        return 1
    fi
    
    # Verify download
    if [ -f "$output_path" ]; then
        size=$(ls -lh "$output_path" | awk '{print $5}')
        echo -e "${GREEN}✓ Downloaded successfully: ${filename} (${size})${NC}"
    else
        echo -e "${RED}✗ Download failed: ${filename}${NC}"
        return 1
    fi
}

# Main execution
if [ $# -eq 0 ]; then
    echo "Usage: $0 <url> <model_type> <filename>"
    echo "Model types: checkpoint, controlnet, lora, vae, upscale, embeddings"
    echo ""
    echo "Example:"
    echo "  $0 'https://huggingface.co/model.safetensors' checkpoint 'model.safetensors'"
    exit 1
fi

# Download the model
download_model "$1" "$2" "$3"