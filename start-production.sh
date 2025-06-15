#!/bin/bash
# ComfyUI Model Resolver - Production Startup Script

set -e  # Exit on error

# 默认配置
API_HOST="${CMR_API_HOST:-0.0.0.0}"
API_PORT="${CMR_API_PORT:-5002}"
GRADIO_HOST="${CMR_GRADIO_HOST:-0.0.0.0}"
GRADIO_PORT="${CMR_GRADIO_PORT:-5001}"
ENABLE_UI="${CMR_ENABLE_UI:-true}"
LOG_LEVEL="${CMR_LOG_LEVEL:-INFO}"

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    set -a
    source .env
    set +a
fi

# 创建必要的目录
mkdir -p logs data

# 健康检查函数
check_health() {
    local url=$1
    local service=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $service to start"
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo " ✓"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    echo " ✗"
    return 1
}

# 启动 API 服务
echo "==========================================="
echo "ComfyUI Model Resolver - Production Mode"
echo "==========================================="
echo "API: http://$API_HOST:$API_PORT"

# 启动 FastAPI
echo "Starting API service..."
LOG_LEVEL=$LOG_LEVEL python -m uvicorn api.main:app \
    --host $API_HOST \
    --port $API_PORT \
    --log-level ${LOG_LEVEL,,} \
    > logs/api.log 2>&1 &
API_PID=$!

# 检查 API 健康状态
if ! check_health "http://localhost:$API_PORT/health" "API"; then
    echo "ERROR: API service failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

# 启动 UI（如果启用）
if [ "$ENABLE_UI" = "true" ]; then
    echo "UI: http://$GRADIO_HOST:$GRADIO_PORT"
    echo "Starting Gradio UI..."
    
    API_URL="http://localhost:$API_PORT" \
    GRADIO_SERVER_PORT=$GRADIO_PORT \
    python frontend/app.py > logs/ui.log 2>&1 &
    UI_PID=$!
    
    if ! check_health "http://localhost:$GRADIO_PORT/" "UI"; then
        echo "WARNING: UI service failed to start, but API is running"
    fi
else
    echo "UI is disabled. Set CMR_ENABLE_UI=true to enable."
fi

echo "==========================================="
echo "Services started successfully!"
echo "API logs: logs/api.log"
[ "$ENABLE_UI" = "true" ] && echo "UI logs: logs/ui.log"
echo "Press Ctrl+C to stop"
echo "==========================================="

# 清理函数
cleanup() {
    echo -e "\nShutting down services..."
    [ -n "$API_PID" ] && kill $API_PID 2>/dev/null || true
    [ -n "$UI_PID" ] && kill $UI_PID 2>/dev/null || true
    echo "Services stopped."
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 等待进程
if [ "$ENABLE_UI" = "true" ]; then
    wait $API_PID $UI_PID
else
    wait $API_PID
fi