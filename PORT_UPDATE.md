# Port Configuration Update

## Changed Ports
- **FastAPI Backend**: 7860 → 5002
- **Gradio Frontend**: 7861 → 5001

## Files Updated
1. **frontend/app.py**: Updated GRADIO_SERVER_PORT default to 5001
2. **frontend/api_client.py**: Updated API_URL default to http://localhost:5002
3. **api/main.py**: Updated uvicorn port to 5002
4. **start.sh**: Updated API_PORT to 5002, GRADIO_PORT to 5001
5. **docker-compose.yml**: Updated port mappings to 5002:5002 and 5001:5001
6. **Dockerfile**: Updated EXPOSE ports and health check URL
7. **DEPLOYMENT.md**: Updated Docker run command ports
8. **test_api.py**: Updated base_url to http://localhost:3002

## Environment Variables
You can still override these ports using environment variables:
- `API_PORT` for FastAPI (default: 5002)
- `GRADIO_PORT` or `GRADIO_SERVER_PORT` for Gradio (default: 5001)

## RunPod Deployment
When deploying on RunPod, ensure ports 5001 and 5002 are exposed in the Pod configuration.

## Port Conflict Note
Ports 3000 and 3001 are commonly used by ComfyUI on RunPod, which is why we chose 5001/5002 instead.