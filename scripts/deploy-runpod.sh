#!/bin/bash
# ComfyUI Model Resolver v2.0 - RunPod Deployment Script

set -e

echo "========================================="
echo "ComfyUI Model Resolver v2.0"
echo "RunPod Deployment Script"
echo "========================================="

# Configuration for RunPod
export API_PORT=7860      # FastAPI backend
export GRADIO_PORT=7861   # Gradio Web UI
export API_URL="http://localhost:${API_PORT}"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create required directories
echo "Creating directories..."
mkdir -p data logs config

# Create config.yaml if not exists
if [ ! -f config.yaml ]; then
    echo "Creating config.yaml..."
    cp config.example.yaml config.yaml
    
    # Update paths for RunPod
    sed -i 's|"/workspace/comfyui"|"/workspace/comfyui"|g' config.yaml
    sed -i 's|"/workspace/comfyui/models"|"/workspace/comfyui/models"|g' config.yaml
fi

# Start FastAPI backend
echo "Starting FastAPI backend on port ${API_PORT}..."
nohup uvicorn api.main:app \
    --host 0.0.0.0 \
    --port ${API_PORT} \
    --log-level info \
    > logs/backend.log 2>&1 &

BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:${API_PORT}/health > /dev/null 2>&1; then
        echo "✓ Backend started successfully"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "\n✗ Backend failed to start"
    echo "Check logs/backend.log for details"
    exit 1
fi

# Start Gradio frontend
echo "Starting Gradio frontend on port ${GRADIO_PORT}..."
export GRADIO_SERVER_NAME=0.0.0.0
export GRADIO_SERVER_PORT=${GRADIO_PORT}

nohup python -m frontend.app > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

# Display access information
echo -e "\n========================================="
echo "Services are running:"
echo "- FastAPI Backend: http://localhost:${API_PORT}"
echo "- API Documentation: http://localhost:${API_PORT}/docs"
echo "- Gradio Web UI: http://localhost:${GRADIO_PORT}"
echo "========================================="
echo ""
echo "To stop services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "To view logs:"
echo "  tail -f logs/backend.log"
echo "  tail -f logs/frontend.log"
echo "========================================="