# ComfyUI Model Resolver v2.0 - Web Interface

## 新功能

v2.0 带来了全新的 Web 界面，让模型管理更加简单直观：

- 🌐 **Web 界面**: 基于 Gradio 的友好用户界面
- ⚡ **实时更新**: WebSocket 支持的下载进度实时显示
- 🔍 **智能搜索**: 同时搜索 HuggingFace 和 Civitai
- 📦 **批量操作**: 同时分析多个工作流
- 💾 **导出脚本**: 生成 bash/powershell/python 下载脚本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

创建 `.env` 文件：

```bash
CIVITAI_API_KEY=your_civitai_api_key
HF_TOKEN=your_huggingface_token  # 可选
```

### 3. 启动应用

```bash
./start.sh
```

或者分别启动：

```bash
# 启动后端 API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 启动前端界面
python frontend/app.py
```

### 4. 访问界面

打开浏览器访问: http://localhost:7860

## 界面功能

### 工作流分析

1. 输入工作流目录路径
2. 选择要分析的工作流
3. 查看所需模型列表
4. 自动标识缺失的模型

### 模型搜索

- 自动在多个平台搜索
- 显示推荐度评分（1-5星）
- 支持自定义下载链接
- 智能路由：LoRA → Civitai，官方模型 → HuggingFace

### 下载管理

- 队列式下载管理
- 实时进度显示
- 支持暂停/继续/取消
- 自动跳过已存在文件

### 批量导出

支持导出为多种格式的下载脚本：
- Bash (Linux/Mac)
- PowerShell (Windows)
- Python (跨平台)

## API 文档

后端 API 文档: http://localhost:8000/docs

## 架构说明

```
┌─────────────────┐     HTTP/WebSocket    ┌─────────────────┐
│  Gradio Client  │ ◄──────────────────► │  FastAPI Server │
│   (Frontend)    │                       │   (Backend API)  │
└─────────────────┘                       └─────────────────┘
                                                    │
                                          ┌─────────┴─────────┐
                                          │   Core Modules    │
                                          │  (已有的核心功能)  │
                                          └───────────────────┘
```

## 故障排除

### API 连接失败

确保后端正在运行：
```bash
curl http://localhost:8000/health
```

### 找不到模型

1. 检查 ComfyUI 路径设置
2. 确保模型目录结构正确
3. 尝试刷新本地缓存

### 下载失败

1. 检查 API Key 配置
2. 确认网络连接
3. 查看日志文件

## 开发说明

### 项目结构

```
comfyui-model-resolver/
├── api/                    # FastAPI 后端
│   ├── routers/           # API 路由
│   ├── models/            # 数据模型
│   └── services/          # 业务逻辑
├── frontend/              # Gradio 前端
│   └── app.py            # 主应用
├── src/                   # 核心功能模块
│   ├── core/             # 工作流分析等
│   └── integrations/     # 平台集成
└── data/                  # 数据存储
```

### 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License