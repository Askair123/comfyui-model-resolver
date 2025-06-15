# ComfyUI Model Resolver - Dependency Analysis

## Summary of Actual Dependencies Used in Production Code

Based on analysis of all Python files in `api/`, `frontend/`, and `src/` directories:

### Core Dependencies (Required)

1. **FastAPI Stack** (API framework)
   - `fastapi` - Used in all API routers and main.py
   - `uvicorn` - ASGI server for running FastAPI
   - `pydantic` - Data validation for API models
   - `python-multipart` - For file uploads

2. **HTTP Clients** (Different parts use different clients)
   - `httpx` - Used in API services (search_service.py)
   - `aiohttp` - Used in integrations (hf_searcher.py, civitai_searcher.py, downloader.py)
   - `aiofiles` - For async file operations

3. **Frontend**
   - `gradio` - Required for all frontend apps (app.py, app_fixed.py, etc.)

4. **Data & Configuration**
   - `pyyaml` - For reading YAML configuration files
   - `python-dotenv` - For environment variables

5. **Utilities**
   - `tqdm` - Progress bars (likely in download operations)

### Optional Dependencies

1. **huggingface-hub** 
   - NOT directly imported in any file
   - Only mentioned in requirements.txt as optional
   - The HuggingFace searcher uses direct API calls via aiohttp instead

2. **requests**
   - NOT imported anywhere in the codebase
   - Only appears in generated download scripts (as a string in workflow_service.py)
   - Not needed for the application itself

### Production Requirements (Minimal)

```txt
# Core API dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
python-multipart>=0.0.6

# HTTP clients (both needed - different parts use different ones)
httpx>=0.24.0
aiohttp>=3.8.0
aiofiles>=23.0.0

# Frontend
gradio>=4.0.0

# Configuration and utilities
pyyaml>=6.0
python-dotenv>=1.0.0
tqdm>=4.65.0
```

### Key Findings

1. **No requests library needed** - The app uses async HTTP clients (httpx and aiohttp)
2. **huggingface-hub is optional** - The HF searcher uses direct API calls
3. **Two HTTP clients are used** - httpx in API services, aiohttp in integrations
4. **Gradio is heavy but required** - All frontend apps depend on it

### Recommendations

1. Consider standardizing on one HTTP client (either httpx or aiohttp) to reduce dependencies
2. huggingface-hub can be removed unless specific features are needed
3. requests library is not needed and can be removed
4. The minimal requirements file accurately reflects actual usage

## Dependency Comparison Table

| Package | In requirements.txt | Actually Used | Notes |
|---------|-------------------|---------------|-------|
| fastapi | ✅ | ✅ | Core API framework |
| uvicorn | ✅ | ✅ | ASGI server |
| pydantic | ✅ | ✅ | Data validation |
| httpx | ✅ | ✅ | Used in API services |
| aiohttp | ❌ | ✅ | Used in integrations (should add) |
| aiofiles | ✅ | ✅ | Async file operations |
| gradio | ✅ | ✅ | Frontend UI |
| pyyaml | ✅ | ✅ | Config files |
| python-dotenv | ✅ | ✅ | Environment variables |
| tqdm | ✅ | ✅ | Progress bars |
| python-multipart | ✅ | ✅ | File uploads |
| huggingface-hub | ✅ (optional) | ❌ | Not imported anywhere |
| requests | ❌ | ❌ | Not needed |

### Missing from requirements.txt
- **aiohttp** - Actually used in multiple integration modules but missing from requirements.txt