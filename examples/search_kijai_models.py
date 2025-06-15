#!/usr/bin/env python3
"""
Example: Search for models in Kijai's repositories

This example demonstrates how the resolver searches for quantized models
in repositories from quantization experts like Kijai and city96.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.integrations.optimized_search import OptimizedModelSearcher
from src.integrations.multi_platform_searcher import MultiPlatformSearcher


def search_kijai_models():
    """Example of searching for models that might be in Kijai's repos."""
    
    # Initialize searchers
    optimizer = OptimizedModelSearcher()
    searcher = MultiPlatformSearcher()
    
    # Example GGUF models that might be in Kijai's repository
    example_models = [
        {
            'name': 'flux1-dev-Q4_0.gguf',
            'description': 'Flux Dev model with Q4_0 quantization'
        },
        {
            'name': 'Wan2.1-14B-Q4_K_M.gguf',
            'description': 'Wan 2.1 14B model with Q4_K_M quantization'
        },
        {
            'name': 't5-v1_1-xxl-encoder-Q8_0.gguf',
            'description': 'T5 XXL encoder with Q8_0 quantization'
        }
    ]
    
    print("=== Searching for Quantized Models ===")
    print("Demonstrating search in Kijai and city96 repositories\n")
    
    for model_info in example_models:
        model_name = model_info['name']
        print(f"\nModel: {model_name}")
        print(f"Description: {model_info['description']}")
        print("-" * 60)
        
        # Show how search terms are generated
        search_terms = optimizer.generate_search_terms(model_name)
        
        print("Generated search terms:")
        # Filter and show repository-specific terms
        repo_terms = [t for t in search_terms if any(r in t for r in ['Kijai', 'city96'])]
        for term in repo_terms[:5]:
            print(f"  - {term}")
        
        # Identify platform strategy
        strategy = searcher.identify_model_type_and_platform(model_name)
        print(f"\nPlatform strategy:")
        print(f"  Type: {strategy['type']}")
        print(f"  Platform: {strategy['platform_priority'][0]}")
        if 'notes' in strategy:
            print(f"  Notes: {strategy['notes']}")
        
        print("\nExpected search behavior:")
        print("  1. First checks HuggingFace for:")
        print(f"     - Kijai/{model_name.replace('.gguf', '')}-gguf")
        print(f"     - city96/{model_name.replace('.gguf', '').replace('-', '.')}-gguf")
        print("  2. Falls back to general GGUF searches if not found")
        print("  3. Returns download link from the first matching repository")
    
    print("\n\n=== Key Points ===")
    print("1. GGUF files trigger repository-specific searches")
    print("2. Both Kijai and city96 patterns are generated")
    print("3. Search order prioritizes known quantization experts")
    print("4. Different naming conventions are handled:")
    print("   - Kijai: Often uses hyphens (flux-1-dev-gguf)")
    print("   - city96: Often uses dots (FLUX.1-dev-gguf)")


def search_specific_kijai_model():
    """Search for a specific model to demonstrate the process."""
    
    print("\n\n=== Live Search Example ===")
    
    # Use the multi-platform searcher
    searcher = MultiPlatformSearcher()
    
    test_model = "flux1-dev-Q4_0.gguf"
    print(f"Searching for: {test_model}")
    
    try:
        result = searcher.search_sync(test_model, use_cache=False)
        
        if result and result.get('url'):
            print(f"\n✓ Found!")
            print(f"  Platform: {result.get('platform', 'unknown')}")
            print(f"  Repository: {result.get('repo_id', 'N/A')}")
            print(f"  URL: {result['url']}")
            
            if 'Kijai' in result.get('repo_id', ''):
                print("\n  This model was found in Kijai's repository!")
            elif 'city96' in result.get('repo_id', ''):
                print("\n  This model was found in city96's repository!")
        else:
            print("\n✗ Not found")
            if result and 'suggestions' in result:
                print("\nSuggestions:")
                for suggestion in result['suggestions']:
                    print(f"  - {suggestion}")
    
    except Exception as e:
        print(f"\n⚠ Search error: {e}")


if __name__ == "__main__":
    # Show how search terms are generated
    search_kijai_models()
    
    # Try an actual search (requires network)
    if '--live' in sys.argv:
        search_specific_kijai_model()
    else:
        print("\n\nTo run a live search, use: python search_kijai_models.py --live")