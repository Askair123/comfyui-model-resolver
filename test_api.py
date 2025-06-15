#!/usr/bin/env python3
"""
Quick API test script
"""

import asyncio
import httpx
import json


async def test_api():
    """Test basic API endpoints."""
    base_url = "http://localhost:5002"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("Testing health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"Health: {response.status_code} - {response.json()}")
        
        # Test root endpoint
        print("\nTesting root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"Root: {response.status_code} - {response.json()}")
        
        # Test workflow list (will fail without valid directory)
        print("\nTesting workflow list...")
        try:
            response = await client.get(
                f"{base_url}/api/workflow/list",
                params={"directory": "/workspace/ComfyUI/workflows"}
            )
            print(f"Workflow list: {response.status_code}")
            if response.status_code == 200:
                workflows = response.json()
                print(f"Found {len(workflows)} workflows")
        except Exception as e:
            print(f"Workflow list error: {e}")
        
        # Test config endpoint
        print("\nTesting config endpoint...")
        response = await client.get(f"{base_url}/api/config/")
        print(f"Config: {response.status_code} - {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    print("ComfyUI Model Resolver API Test")
    print("=" * 40)
    asyncio.run(test_api())