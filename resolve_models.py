#!/usr/bin/env python3
"""
ComfyUI Model Resolver - Main CLI Entry Point

Analyzes ComfyUI workflows and resolves all required models from multiple sources.
"""

import argparse
import sys
import os
import json
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow_resolver import complete_workflow_resolution


def load_config(config_path=None):
    """Load configuration from file or use defaults."""
    defaults = {
        'api_keys': {
            'huggingface': os.getenv('HF_TOKEN', ''),
            'civitai': os.getenv('CIVITAI_API_KEY', '')
        },
        'paths': {
            'comfyui_base': '/workspace/comfyui',
            'models_base': '/workspace/comfyui/models',
            'cache_dir': '~/.cache/comfyui-model-resolver'
        },
        'search': {
            'max_concurrent': 3,
            'cache_ttl': 86400
        }
    }
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f)
            # Merge with defaults
            for key in user_config:
                if isinstance(user_config[key], dict):
                    defaults[key].update(user_config[key])
                else:
                    defaults[key] = user_config[key]
    
    return defaults


def main():
    parser = argparse.ArgumentParser(
        description='ComfyUI Model Resolver - Find and download all models from a workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a workflow and generate download commands
  %(prog)s workflow.json
  
  # Use custom config file
  %(prog)s workflow.json --config my-config.yaml
  
  # Save report to specific location
  %(prog)s workflow.json --output report.json
  
  # Show only missing models
  %(prog)s workflow.json --missing-only
  
  # Generate download script
  %(prog)s workflow.json --download-script download.sh
"""
    )
    
    parser.add_argument('workflow', 
                       help='Path to ComfyUI workflow JSON file')
    
    parser.add_argument('-c', '--config',
                       help='Path to configuration file (default: config.yaml)')
    
    parser.add_argument('-o', '--output',
                       default='workflow_resolution_report.json',
                       help='Output report file (default: workflow_resolution_report.json)')
    
    parser.add_argument('--civitai-key',
                       help='Civitai API key (overrides config/env)')
    
    parser.add_argument('--hf-token',
                       help='HuggingFace token (overrides config/env)')
    
    parser.add_argument('--models-path',
                       help='ComfyUI models directory (default: /workspace/comfyui/models)')
    
    parser.add_argument('-m', '--missing-only',
                       action='store_true',
                       help='Show only missing models')
    
    parser.add_argument('-d', '--download-script',
                       help='Generate download script to specified file')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Enable verbose output')
    
    parser.add_argument('--no-cache',
                       action='store_true',
                       help='Disable cache for searches')
    
    args = parser.parse_args()
    
    # Validate workflow file
    if not os.path.exists(args.workflow):
        print(f"Error: Workflow file not found: {args.workflow}")
        sys.exit(1)
    
    # Load configuration
    config_path = args.config or 'config.yaml'
    config = load_config(config_path if os.path.exists(config_path) else None)
    
    # Override with CLI arguments
    if args.civitai_key:
        config['api_keys']['civitai'] = args.civitai_key
    if args.hf_token:
        config['api_keys']['huggingface'] = args.hf_token
    if args.models_path:
        config['paths']['models_base'] = args.models_path
    
    # Set environment variables for the resolver
    if config['api_keys']['civitai']:
        os.environ['CIVITAI_API_KEY'] = config['api_keys']['civitai']
    if config['api_keys']['huggingface']:
        os.environ['HF_TOKEN'] = config['api_keys']['huggingface']
    
    # Run resolution
    print(f"Analyzing workflow: {args.workflow}")
    report = complete_workflow_resolution(args.workflow)
    
    # Save report
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {args.output}")
    
    # Generate download script if requested
    if args.download_script and report.get('download_plan'):
        generate_download_script(report['download_plan'], args.download_script)
        print(f"Download script saved to: {args.download_script}")
    
    # Show summary
    if not args.missing_only:
        print("\n" + "="*50)
        print("Resolution Summary:")
        print(f"Total models: {report['summary']['total_models']}")
        print(f"Found locally: {report['summary']['local_found']}")
        print(f"Found online: {report['summary']['online_found']}")
        print(f"Not found: {report['summary']['not_found']}")
        print(f"Success rate: {report['summary']['success_rate']['overall']}")


def generate_download_script(download_plan, output_file):
    """Generate a shell script for downloading all models."""
    script_content = """#!/bin/bash
# ComfyUI Model Download Script
# Generated by ComfyUI Model Resolver

set -e  # Exit on error

echo "Starting model downloads..."
echo "Total models to download: {count}"
echo ""

# Create directories if they don't exist
DIRS=(
{dirs}
)

for dir in "${{DIRS[@]}}"; do
    mkdir -p "$dir"
done

# Download models
{downloads}

echo ""
echo "All downloads completed!"
""".format(
        count=len(download_plan),
        dirs='\n'.join(f'    "{os.path.dirname(item["target_path"])}"' 
                      for item in download_plan),
        downloads='\n'.join(
            f"""
# {item['filename']} (from {item['platform']})
echo "Downloading {item['filename']}..."
wget -c '{item['url']}' \\
    -O '{item['target_path']}' || echo "Failed to download {item['filename']}"
"""
            for item in download_plan
        )
    )
    
    with open(output_file, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(output_file, 0o755)


if __name__ == '__main__':
    main()