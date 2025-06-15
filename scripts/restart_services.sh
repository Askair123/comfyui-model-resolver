#!/bin/bash
# Restart web services for ComfyUI Model Resolver

echo "Restarting ComfyUI Model Resolver services..."

# 1. Stop existing services
echo "Stopping existing services..."
pkill -f 'uvicorn' || true
pkill -f 'python app.py' || true
pkill -f 'gradio' || true

# Wait for processes to stop
sleep 2

# 2. Start services
echo "Starting services..."
cd /workspace

# Start FastAPI backend
echo "Starting FastAPI backend on port 7860..."
nohup uvicorn api.main:app --host 0.0.0.0 --port 7860 > api.log 2>&1 &
echo "FastAPI PID: $!"

# Wait for API to start
sleep 3

# Start Gradio frontend
echo "Starting Gradio frontend on port 7861..."
export GRADIO_SERVER_PORT=7861
nohup python frontend/app.py > frontend.log 2>&1 &
echo "Gradio PID: $!"

# Wait and check status
sleep 5

# Check if services are running
echo ""
echo "Checking service status..."
if pgrep -f "uvicorn" > /dev/null; then
    echo "✅ FastAPI is running on port 7860"
else
    echo "❌ FastAPI failed to start - check api.log"
fi

if pgrep -f "app.py" > /dev/null; then
    echo "✅ Gradio is running on port 7861"
else
    echo "❌ Gradio failed to start - check frontend.log"
fi

echo ""
echo "Services restarted. You can check logs with:"
echo "  tail -f /workspace/api.log"
echo "  tail -f /workspace/frontend.log"