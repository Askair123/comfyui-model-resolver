#!/usr/bin/env python3
"""
Model search script with caching support
Borrowed caching mechanism from ComfyUI-Model-Downloader
"""

import json
import os
import asyncio
import aiohttp
from typing import Dict, List, Optional
from pathlib import Path

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "comfyui-model-resolver"
CACHE_FILE = CACHE_DIR / "search_cache.json"

# Create cache directory if not exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache
_search_cache = {}

def load_cache():
    """Load cache from disk"""
    global _search_cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                _search_cache = json.load(f)
        except:
            _search_cache = {}

def save_cache():
    """Save cache to disk"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(_search_cache, f, indent=2)

async def search_huggingface(filename: str) -> Optional[Dict]:
    """Search HuggingFace for a model file"""
    # Check cache first
    cache_key = filename.lower()
    if cache_key in _search_cache:
        print(f"Cache hit for: {filename}")
        return _search_cache[cache_key]
    
    # Extract model name from filename
    model_name = filename.rsplit('.', 1)[0]
    base_url = "https://huggingface.co/api/models"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Search by model name
            async with session.get(f"{base_url}?search={model_name}&full=true") as response:
                if response.status == 200:
                    repos = await response.json()
                    
                    # Look for exact filename match
                    for repo in repos:
                        for sibling in repo.get("siblings", []):
                            if sibling["rfilename"] == filename:
                                result = {
                                    "repo_id": repo["modelId"],
                                    "filename": filename,
                                    "url": f"https://huggingface.co/{repo['modelId']}/resolve/main/{filename}",
                                    "size": sibling.get("size", "Unknown")
                                }
                                
                                # Cache the result
                                _search_cache[cache_key] = result
                                save_cache()
                                
                                return result
        except Exception as e:
            print(f"Error searching HuggingFace: {e}")
    
    # Cache negative result
    _search_cache[cache_key] = None
    save_cache()
    return None

async def batch_search(models: List[Dict]) -> Dict[str, List[Dict]]:
    """Search for multiple models concurrently"""
    results = {
        "found": [],
        "not_found": []
    }
    
    # Load cache
    load_cache()
    
    # Create search tasks
    tasks = []
    for model in models:
        task = search_huggingface(model['name'])
        tasks.append((model, task))
    
    # Execute searches concurrently
    for model, task in tasks:
        result = await task
        if result:
            model['url'] = result['url']
            model['repo_id'] = result['repo_id']
            results['found'].append(model)
        else:
            results['not_found'].append(model)
    
    return results

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 search-models.py <models.json>")
        print("\nExpected JSON format:")
        print("""{
    "missing": [
        {"name": "model.safetensors", "type": "checkpoint"}
    ]
}""")
        sys.exit(1)
    
    # Load models
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    models = data.get('missing', [])
    if not models:
        print("No missing models to search")
        sys.exit(0)
    
    print(f"Searching for {len(models)} models...")
    
    # Run async search
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(batch_search(models))
    
    # Print results
    print(f"\n✓ Found: {len(results['found'])}")
    for model in results['found']:
        print(f"  - {model['name']} -> {model['repo_id']}")
    
    print(f"\n✗ Not found: {len(results['not_found'])}")
    for model in results['not_found']:
        print(f"  - {model['name']}")
    
    # Save results
    output_file = sys.argv[1].replace('.json', '_search_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()