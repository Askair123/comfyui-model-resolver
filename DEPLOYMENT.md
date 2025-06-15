# ComfyUI Model Resolver v2.0 - 部署指南

## 部署方式

### 1. Docker 部署（推荐）

#### 使用 Docker Compose

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/comfyui-model-resolver.git
cd comfyui-model-resolver

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加你的 API keys

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

#### 使用 Docker 直接运行

```bash
# 构建镜像
docker build -t comfyui-resolver:v2.0 .

# 运行容器
docker run -d \
  -p 5001:5001 \
  -p 5002:5002 \
  -v /workspace:/workspace \
  -v $(pwd)/data:/app/data \
  -e CIVITAI_API_KEY=your_key \
  comfyui-resolver:v2.0
```

### 2. RunPod 部署

#### 方式一：使用 RunPod 模板

1. 在 RunPod 创建新的 Pod
2. 选择 GPU 类型（建议 RTX 3090 或更高）
3. 使用以下启动命令：

```bash
cd /workspace && \
git clone https://github.com/yourusername/comfyui-model-resolver.git && \
cd comfyui-model-resolver && \
pip install -r requirements.txt && \
./start.sh
```

#### 方式二：集成到现有 ComfyUI Pod

```bash
# SSH 进入你的 Pod
ssh root@your-pod-ip -p your-ssh-port

# 安装 Model Resolver
cd /workspace
git clone https://github.com/yourusername/comfyui-model-resolver.git
cd comfyui-model-resolver

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export CIVITAI_API_KEY=your_key
export COMFYUI_ROOT=/workspace/ComfyUI

# 启动服务
./start.sh
```

### 3. 本地开发部署

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 启动服务
./start.sh
```

## 配置说明

### 必需配置

- `COMFYUI_ROOT`: ComfyUI 安装目录
- `CIVITAI_API_KEY`: Civitai API 密钥（用于搜索 LoRA 模型）

### 可选配置

- `HF_TOKEN`: HuggingFace Token（访问私有模型）
- `MAX_CONCURRENT_DOWNLOADS`: 最大并发下载数
- `AUTO_SKIP_EXISTING`: 是否自动跳过已存在文件

## 网络要求

### 端口

- `8000`: FastAPI 后端
- `7860`: Gradio 前端

### 防火墙配置

```bash
# 开放端口
sudo ufw allow 7860/tcp
sudo ufw allow 8000/tcp
```

### Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Gradio 前端
    location / {
        proxy_pass http://localhost:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # FastAPI 后端
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 性能优化

### 1. 使用 Redis 缓存（可选）

编辑 `docker-compose.yml`，取消 Redis 服务的注释：

```yaml
services:
  redis:
    image: redis:alpine
    container_name: model-resolver-redis
    ports:
      - "6379:6379"
    restart: unless-stopped
```

### 2. 增加下载并发数

编辑 `.env` 文件：

```bash
MAX_CONCURRENT_DOWNLOADS=5  # 根据网络情况调整
```

### 3. 使用 SSD 存储

将数据目录映射到 SSD：

```bash
docker run -v /mnt/ssd/resolver-data:/app/data ...
```

## 故障排除

### 问题：无法连接到 API

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs api

# 测试 API
curl http://localhost:8000/health
```

### 问题：Gradio 界面无法访问

```bash
# 检查端口占用
sudo lsof -i :7860

# 重启前端
docker-compose restart
```

### 问题：下载速度慢

1. 检查网络连接
2. 使用代理（如果需要）
3. 减少并发下载数

## 监控

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 特定服务日志
docker-compose logs -f model-resolver
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 下载队列状态
curl http://localhost:8000/api/download/status
```

## 备份与恢复

### 备份数据

```bash
# 备份配置和缓存
tar -czf resolver-backup-$(date +%Y%m%d).tar.gz data/
```

### 恢复数据

```bash
# 恢复备份
tar -xzf resolver-backup-20240114.tar.gz
```

## 安全建议

1. **不要暴露端口到公网**：使用 VPN 或 SSH 隧道
2. **定期更新**：`git pull && pip install -r requirements.txt`
3. **保护 API Keys**：使用环境变量，不要提交到代码库
4. **限制访问**：使用防火墙规则限制访问来源

## 支持

- GitHub Issues: https://github.com/yourusername/comfyui-model-resolver/issues
- 文档: https://github.com/yourusername/comfyui-model-resolver/wiki