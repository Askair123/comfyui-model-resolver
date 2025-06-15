#!/bin/bash
# ComfyUI Model Resolver v2.0 - Startup Script

set -e  # Exit on error

echo "========================================="
echo "ComfyUI Model Resolver v2.0"
echo "========================================="

# Function to handle cleanup
cleanup() {
    echo -e "\n\nShutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    echo "Shutdown complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running in Docker container"
    VENV_PATH=""
else
    echo "Running on host system"
    VENV_PATH="venv"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        echo "Creating virtual environment..."
        python3 -m venv $VENV_PATH
    fi
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source $VENV_PATH/bin/activate
fi

# Install/upgrade dependencies
echo "Checking dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create required directories
echo "Creating directories..."
mkdir -p data data/cache logs

# Export environment variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -a
    source .env
    set +a
fi

# Set default values if not provided
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-5002}      # FastAPI on 5002 for RunPod
export GRADIO_HOST=${GRADIO_HOST:-0.0.0.0}
export GRADIO_PORT=${GRADIO_PORT:-5001}  # Gradio on 5001 for RunPod

# Start FastAPI backend
echo -e "\nStarting FastAPI backend on port $API_PORT..."
uvicorn api.main:app \
    --host $API_HOST \
    --port $API_PORT \
    --log-level info \
    --access-log \
    > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:$API_PORT/health > /dev/null 2>&1; then
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
    cleanup
    exit 1
fi

# Display access information
echo -e "\n========================================="
echo "Services are running:"
echo "- API Documentation: http://localhost:$API_PORT/docs"
echo "- Web Interface: http://localhost:$GRADIO_PORT"
echo "========================================="
echo -e "\nPress Ctrl+C to stop\n"

# Start Gradio frontend
echo "Starting Gradio frontend on port $GRADIO_PORT..."
python frontend/app.py

# This will only be reached if frontend exits
cleanup