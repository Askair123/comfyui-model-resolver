#!/bin/bash
# ComfyUI Model Resolver v2.0 - Startup Script

echo "Starting ComfyUI Model Resolver v2.0..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data directory if not exists
mkdir -p data

# Export environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment variables..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start FastAPI backend
echo "Starting FastAPI backend..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "Error: Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "Backend started successfully"

# Start Gradio frontend
echo "Starting Gradio frontend..."
python frontend/app.py

# Cleanup on exit
echo "Shutting down..."
kill $BACKEND_PID 2>/dev/null
echo "Shutdown complete"