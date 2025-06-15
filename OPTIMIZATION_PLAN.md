# ComfyUI Model Resolver 部署优化方案

## 1. 依赖优化

### 分离依赖文件
```
requirements-core.txt      # 核心运行依赖
requirements-dev.txt       # 开发工具
requirements-full.txt      # 完整依赖（包含可选功能）
```

### 使用依赖分组（pyproject.toml）
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "httpx>=0.24.0",
    "pyyaml>=6.0",
    "tqdm>=4.65.0",
]

[project.optional-dependencies]
ui = ["gradio>=4.0.0"]
dev = ["pytest>=7.3.0", "black>=23.3.0", "mypy>=1.3.0"]
hf = ["huggingface-hub>=0.16.0"]
```

## 2. 启动优化

### 环境变量统一管理
```python
# config/env_config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 5002
    
    # Gradio配置
    gradio_host: str = "0.0.0.0"
    gradio_port: int = 5001
    gradio_share: bool = False
    
    # 路径配置
    comfyui_root: str = "/workspace/comfyui"
    
    # API Keys
    civitai_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    
    # 性能配置
    max_workers: int = 3
    enable_cache: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "CMR_"  # ComfyUI Model Resolver prefix

settings = Settings()
```

### 改进的启动脚本
```bash
#!/bin/bash
# start-optimized.sh

set -e  # Exit on error

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 健康检查函数
check_service() {
    local url=$1
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url/health" > /dev/null; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    return 1
}

# 启动API服务
echo "Starting API service..."
python -m uvicorn api.main:app \
    --host ${CMR_API_HOST:-0.0.0.0} \
    --port ${CMR_API_PORT:-5002} \
    --workers ${CMR_MAX_WORKERS:-1} &
API_PID=$!

# 等待API启动
if check_service "http://localhost:${CMR_API_PORT:-5002}"; then
    echo "API service started successfully"
else
    echo "API service failed to start"
    kill $API_PID 2>/dev/null
    exit 1
fi

# 启动Gradio UI（如果需要）
if [ "${CMR_ENABLE_UI:-true}" = "true" ]; then
    echo "Starting Gradio UI..."
    python frontend/app.py &
    UI_PID=$!
fi

# 等待退出信号
trap "kill $API_PID $UI_PID 2>/dev/null" EXIT
wait
```

## 3. 部署流程优化

### Docker多阶段构建
```dockerfile
# Dockerfile.optimized
# 构建阶段 - 安装所有依赖
FROM python:3.10-slim as builder
WORKDIR /build
COPY requirements-core.txt .
RUN pip install --user --no-cache-dir -r requirements-core.txt

# 运行阶段 - 最小化镜像
FROM python:3.10-slim
WORKDIR /app

# 复制依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY config/ ./config/

# 运行时配置
ENV CMR_API_HOST=0.0.0.0
ENV CMR_API_PORT=5002

EXPOSE 5002 5001

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5002"]
```

### RunPod专用部署脚本
```bash
#!/bin/bash
# deploy-runpod.sh

# RunPod环境检测
if [ -n "$RUNPOD_POD_ID" ]; then
    echo "Detected RunPod environment: $RUNPOD_POD_ID"
    
    # 设置RunPod特定配置
    export CMR_COMFYUI_ROOT="/workspace/comfyui"
    export CMR_API_PORT="${API_PORT:-5002}"
    export CMR_GRADIO_PORT="${GRADIO_PORT:-5001}"
    
    # 安装最小依赖
    pip install --no-cache-dir -r requirements-core.txt
    
    # 如果需要UI，安装Gradio
    if [ "${ENABLE_UI:-true}" = "true" ]; then
        pip install --no-cache-dir gradio>=4.0.0
    fi
else
    # 标准环境
    pip install -r requirements-core.txt
fi

# 启动服务
./start-optimized.sh
```

## 4. 性能优化

### 延迟加载
```python
# api/utils/lazy_imports.py
class LazyImport:
    def __init__(self, module_name):
        self.module_name = module_name
        self._module = None
    
    def __getattr__(self, name):
        if self._module is None:
            self._module = importlib.import_module(self.module_name)
        return getattr(self._module, name)

# 使用示例
hf_hub = LazyImport('huggingface_hub')  # 只在需要时导入
```

### 连接池管理
```python
# api/utils/http_client.py
from httpx import AsyncClient, Limits

class HTTPClientManager:
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = AsyncClient(
                limits=Limits(max_keepalive_connections=5, max_connections=10),
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()

# 全局实例
http_client = HTTPClientManager()
```

## 5. 监控和日志

### 结构化日志
```python
# config/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# 配置日志
def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
```

### 健康检查端点增强
```python
# api/routers/health.py
from fastapi import APIRouter
from datetime import datetime
import psutil

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "metrics": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "active_downloads": download_service.active_downloads,
        }
    }
```

## 6. 部署命令简化

### 一键部署
```bash
# 开发环境
./deploy.sh dev

# 生产环境（最小依赖）
./deploy.sh prod --no-ui

# RunPod环境
./deploy.sh runpod --port 5002

# Docker部署
docker run -d \
  -e CMR_COMFYUI_ROOT=/workspace/comfyui \
  -p 5002:5002 \
  comfyui-resolver:optimized
```

## 实施步骤

1. **第一阶段**：分离依赖文件，创建 requirements-core.txt
2. **第二阶段**：实现环境变量统一管理
3. **第三阶段**：优化启动脚本，解决循环导入
4. **第四阶段**：实现延迟加载和性能优化
5. **第五阶段**：添加监控和日志系统

## 预期效果

- 安装时间减少 60%（只安装核心依赖）
- 启动时间减少 40%（优化导入和初始化）
- 内存使用减少 30%（延迟加载）
- 部署复杂度降低（统一配置管理）
- 故障排查更容易（结构化日志）