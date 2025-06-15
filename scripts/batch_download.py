#!/usr/bin/env python3
"""
Batch download models based on JSON input from workflow analysis
"""

import json
import subprocess
import sys
import os
from pathlib import Path

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color

def download_model(url, model_type, filename):
    """Call the download script for a single model"""
    script_path = Path(__file__).parent / "download-models.sh"
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    try:
        result = subprocess.run(
            [str(script_path), url, model_type, filename],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{GREEN}✓ {filename}{NC}")
        else:
            print(f"{RED}✗ {filename}: {result.stderr}{NC}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"{RED}✗ {filename}: {str(e)}{NC}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 batch-download-models.py <models.json>")
        print("\nExpected JSON format:")
        print("""{
    "models": [
        {
            "name": "epicRealism.safetensors",
            "type": "checkpoint",
            "url": "https://huggingface.co/...",
            "status": "missing"
        }
    ]
}""")
        sys.exit(1)
    
    # Load models JSON
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    models = data.get('models', [])
    missing_models = [m for m in models if m.get('status') == 'missing']
    
    print(f"\n{YELLOW}Found {len(missing_models)} missing models to download{NC}\n")
    
    success_count = 0
    failed_models = []
    
    for model in missing_models:
        name = model.get('name')
        model_type = model.get('type')
        url = model.get('url')
        
        if not all([name, model_type, url]):
            print(f"{RED}Skipping incomplete model entry: {model}{NC}")
            continue
            
        print(f"\nDownloading {name}...")
        
        if download_model(url, model_type, name):
            success_count += 1
        else:
            failed_models.append(name)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"{GREEN}Successfully downloaded: {success_count}{NC}")
    
    if failed_models:
        print(f"{RED}Failed downloads: {len(failed_models)}{NC}")
        for model in failed_models:
            print(f"  - {model}")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()