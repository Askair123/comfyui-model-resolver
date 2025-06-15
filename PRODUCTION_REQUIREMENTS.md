# ComfyUI Model Resolver - 生产环境部署要求

## 一、核心服务架构

### 1. API 服务（必需）
- **框架**: FastAPI
- **服务器**: Uvicorn (ASGI)
- **端口**: 5002
- **功能**:
  - 工作流分析
  - 模型搜索（HuggingFace、Civitai）
  - 下载管理
  - 配置管理

### 2. Web UI 服务（可选但推荐）
- **框架**: Gradio
- **端口**: 5001
- **功能**:
  - 用户友好的界面
  - 实时进度显示
  - 批量操作

## 二、必需的生产依赖

### 核心依赖（requirements-production.txt）
```txt
# API 框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
python-multipart>=0.0.6

# HTTP 客户端
httpx>=0.24.0        # API 层使用
aiohttp>=3.8.0       # 集成层使用（搜索器、下载器）
aiofiles>=23.0.0     # 异步文件操作

# 数据处理
pyyaml>=6.0          # 配置文件
python-dotenv>=1.0.0 # 环境变量
tqdm>=4.65.0         # 进度条
```

### UI 依赖（requirements-ui.txt）
```txt
# 前端框架
gradio>=4.0.0        # Web UI
```

## 三、可选依赖

### 增强功能（requirements-optional.txt）
```txt
# HuggingFace 集成（如果需要使用 HF Token 访问私有模型）
huggingface-hub>=0.16.0

# 性能监控
psutil>=5.9.0        # 系统资源监控

# 缓存加速
redis>=4.5.0         # Redis 缓存支持
```

## 四、环境变量配置

### 必需配置
```bash
# API 配置
CMR_API_HOST=0.0.0.0
CMR_API_PORT=5002

# 路径配置
CMR_COMFYUI_ROOT=/workspace/comfyui

# 日志级别
CMR_LOG_LEVEL=INFO
```

### 可选配置
```bash
# UI 配置
CMR_ENABLE_UI=true
CMR_GRADIO_HOST=0.0.0.0
CMR_GRADIO_PORT=5001

# API Keys（用于模型搜索）
CMR_CIVITAI_API_KEY=your_key
CMR_HF_TOKEN=your_token

# 性能配置
CMR_MAX_CONCURRENT_DOWNLOADS=3
CMR_DOWNLOAD_TIMEOUT=300
```

## 五、部署命令

### 最小部署（仅 API）
```bash
# 安装核心依赖
pip install -r requirements-production.txt

# 启动 API 服务
python -m uvicorn api.main:app --host 0.0.0.0 --port 5002
```

### 完整部署（API + UI）
```bash
# 安装所有生产依赖
pip install -r requirements-production.txt
pip install -r requirements-ui.txt

# 启动服务
./start-production.sh
```

### Docker 部署
```bash
# 使用生产镜像
docker run -d \
  -e CMR_COMFYUI_ROOT=/workspace/comfyui \
  -p 5002:5002 \
  -p 5001:5001 \
  -v /workspace:/workspace \
  comfyui-resolver:production
```

## 六、服务依赖关系

```
用户请求
    ↓
Gradio UI (5001)  ←→  FastAPI (5002)
                           ↓
                    ┌──────┴──────┐
                    │             │
              工作流分析      模型搜索
                    │             │
                    │      ┌──────┴──────┐
                    │      │             │
                    │   HuggingFace   Civitai
                    │      API         API
                    │
                下载管理器
                    │
                文件系统
```

## 七、资源需求

### 最小配置
- CPU: 1 核心
- 内存: 512MB
- 存储: 100MB（应用）

### 推荐配置
- CPU: 2 核心
- 内存: 1GB
- 存储: 1GB（包含缓存）

## 八、健康检查

### API 健康检查
```bash
curl http://localhost:5002/health
```

### UI 健康检查
```bash
curl http://localhost:5001/
```

## 九、注意事项

1. **HTTP 客户端冗余**: 目前同时使用 httpx 和 aiohttp，未来可以统一
2. **Gradio 依赖重**: Gradio 会带来额外的依赖（pandas、numpy等）
3. **开发依赖分离**: pytest、black、mypy 等仅在开发环境需要
4. **可选功能按需安装**: HuggingFace Hub 只在需要访问私有模型时安装