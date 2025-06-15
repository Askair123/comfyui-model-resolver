# ComfyUI Workflow Model Dependency Resolver - PRD

## 1. 项目概述

### 1.1 产品名称
ComfyUI Workflow Model Dependency Resolver (WMDR)

### 1.2 产品定位
一个自动化工具，用于识别、搜索和下载 ComfyUI 工作流所需的模型文件，解决工作流分享时的依赖问题。

### 1.3 核心价值
- **自动化**：一键解决模型依赖问题
- **智能匹配**：处理模型命名差异
- **多源支持**：覆盖主流模型托管平台

### 1.4 参考实现
本方案借鉴了以下开源项目的部分实现：
- [ComfyUI-Model-Downloader](https://github.com/reference-link-1) - 工作流扫描机制
- [Asset-Downloader](https://github.com/reference-link-2) - 下载进度反馈
- [ComfyDownloader](https://github.com/reference-link-3) - Token管理方式

## 2. 背景与目标

### 2.1 问题背景
- ComfyUI 工作流分享时，接收者经常缺少必要的模型文件
- 模型文件命名不一致（版本、格式差异）
- 手动查找和下载模型耗时且容易出错
- 不同平台的下载方式各异

### 2.2 产品目标
1. **简化流程**：用户只需提供工作流文件，系统自动完成所有操作
2. **提高成功率**：智能匹配算法处理命名差异
3. **节省时间**：批量并行下载，自动重试
4. **用户友好**：清晰的进度反馈和错误提示

## 3. 功能架构

### 3.1 系统架构
```
用户输入 → 工作流分析 → 本地检查 → 模型搜索 → 自动下载 → 结果报告
              ↓              ↓            ↓            ↓
           [脚本处理]    [脚本处理]    [MCP工具]    [脚本处理]
```

### 3.2 核心模块

#### 3.2.1 工作流分析模块
- **输入**：ComfyUI workflow JSON 文件
- **功能**：
  - 解析 JSON 结构，提取 nodes 数组
  - 识别模型加载节点类型
  - 提取 widgets_values 中的模型文件名
  - 分类模型类型（checkpoint/controlnet/lora/vae等）
- **输出**：结构化的模型需求列表

#### 3.2.2 本地检查模块
- **输入**：模型需求列表
- **功能**：
  - 扫描 `/workspace/comfyui/models/` 目录树
  - 关键词提取与匹配算法
  - 版本标识过滤（q4, q5, fp16, pruned等）
  - 匹配度分类（完全/部分/无匹配）
- **输出**：分类后的模型状态

#### 3.2.3 模型搜索模块
- **输入**：缺失模型列表
- **功能**：
  - HuggingFace API 搜索（通过 MCP）
  - Tavily 综合搜索（Civitai、GitHub等）
  - 结果评分与筛选
  - 多源链接获取
- **输出**：带下载链接的模型信息

#### 3.2.4 下载执行模块
- **输入**：模型链接信息
- **功能**：
  - 平台适配（HuggingFace/GitHub/Civitai）
  - 断点续传支持
  - 并行下载管理
  - 文件完整性验证
- **输出**：下载结果和统计

## 4. 详细设计

### 4.1 模型类型映射
```python
MODEL_TYPE_MAPPING = {
    'CheckpointLoaderSimple': ('checkpoint', 'checkpoints/'),
    'ControlNetLoader': ('controlnet', 'controlnet/'),
    'LoraLoader': ('lora', 'loras/'),
    'VAELoader': ('vae', 'vae/'),
    'UpscaleModelLoader': ('upscale', 'upscale_models/'),
    'CLIPLoader': ('clip', 'clip/'),
    'UNETLoader': ('unet', 'unet/')
}
```

### 4.2 关键词匹配算法
```python
def extract_keywords(filename):
    # 1. 移除扩展名
    # 2. 转换小写
    # 3. 按分隔符拆分（-, _, 空格）
    # 4. 过滤版本标识
    # 5. 返回核心关键词列表
    
def match_level(required_keywords, found_keywords):
    # 完全匹配：所有 required 都在 found 中
    # 部分匹配：部分 required 在 found 中
    # 无匹配：没有交集
```

### 4.3 多平台搜索策略

#### 4.3.1 平台智能路由
```python
PLATFORM_ROUTING = {
    'lora': {
        'indicators': ['lora', 'style', 'anime', 'cartoon', 'cute'],
        'platforms': ['civitai', 'huggingface'],
        'confidence': 'high'
    },
    'official': {
        'patterns': ['flux1-dev', 'sdxl-base', 'stable-diffusion'],
        'platforms': ['huggingface'],
        'confidence': 'high'
    },
    'quantized': {
        'extensions': ['.gguf'],
        'platforms': ['huggingface'],  # city96 repos
        'confidence': 'high'
    }
}
```

#### 4.3.2 Civitai API 集成
```python
class CivitaiSearcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://civitai.com/api/v1"
    
    async def search_model(self, filename, model_type=None):
        # 提取风格关键词
        # 搜索Civitai模型库
        # 返回匹配结果和下载链接
```

### 4.4 优化搜索策略

#### 4.3.1 模型系列标准化
```python
MODEL_SERIES = {
    'flux': {
        'variants': ['flux1', 'flux-1', 'flux_1'],
        'versions': ['dev', 'schnell', 'pro'],
        'official_format': 'flux1-{version}'
    },
    'wan': {
        'variants': ['wan', 'wan2', 'wan21', 'wan2.1', 'wan2_1'],
        'versions': ['2.1'],
        'official_format': 'Wan2.1'
    },
    'hunyuan': {
        'variants': ['hunyuan', 'hy'],
        'versions': ['dit', 'video'],
        'official_format': 'HunyuanDiT'
    }
}
```

#### 4.3.2 智能搜索词生成
```python
def generate_search_terms(filename):
    # 策略1：保留技术规格的精确匹配
    # flux1-dev-11gb-fp8.safetensors → flux1-dev-fp8.safetensors
    # 仅移除文件大小标记（11gb），保留所有技术规格
    
    # 策略2：完整组件组合
    # 保留：模型系列、版本、功能类型、量化格式、分辨率、参数量
    # 过滤：文件大小（11gb）、个人标记（my-version）
    
    # 策略3：多种格式尝试
    # Wan21_CausVid_14B_T2V_lora_rank32 生成：
    # - Wan2.1_CausVid_14B_T2V_lora_rank32
    # - Wan2.1-CausVid-14B-T2V-lora-rank32
    # - Wan2.1 CausVid 14B T2V lora rank32
```

#### 4.3.3 关键词优先级
- **高优先级**：模型系列、版本、量化格式
- **中优先级**：功能类型（T2V, I2V, VAE）、分辨率
- **低优先级**：参数量、其他描述符

### 4.4 借鉴的技术细节

#### 4.4.1 搜索结果缓存（借鉴自 Auto Model Downloader）
```python
_model_cache = {}

async def search_with_cache(filename):
    cache_key = filename.lower()
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    result = await search_model(filename)
    _model_cache[cache_key] = result
    return result
```

#### 4.4.2 临时文件下载（借鉴自 Asset Downloader）
```bash
# 下载到临时文件，确保完整性
wget "$url" -O "$output_path.tmp"
if [ $? -eq 0 ]; then
    mv "$output_path.tmp" "$output_path"
else
    rm -f "$output_path.tmp"
fi
```

#### 4.4.3 环境变量Token支持（借鉴自 ComfyDownloader）
```python
def resolve_token(token):
    if token.startswith("$"):
        return os.getenv(token[1:], token)
    return token
```

### 4.5 下载策略
```bash
# HuggingFace
wget -q --show-progress "$url" -O "$output"

# GitHub
curl -L -# -o "$output" "$url"

# Civitai
wget --content-disposition "$url" -O "$output"
# 可选：--header="Authorization: Bearer $CIVITAI_TOKEN"
```

## 5. 数据流设计

### 5.1 数据格式演进

#### 阶段1：工作流分析输出
```json
{
  "models": [
    {
      "name": "epicRealism.safetensors",
      "type": "checkpoint",
      "node_type": "CheckpointLoaderSimple",
      "keywords": ["epic", "realism"]
    }
  ]
}
```

#### 阶段2：本地检查输出
```json
{
  "missing": [
    {
      "name": "epicRealism.safetensors",
      "type": "checkpoint",
      "keywords": ["epic", "realism"]
    }
  ],
  "partial": [
    {
      "name": "4x-UltraSharp.pth",
      "type": "upscale",
      "matches": ["4xUltraSharp.pth", "4x_ultrasharp_v1.pth"]
    }
  ]
}
```

#### 阶段3：搜索结果输出
```json
{
  "models": [
    {
      "name": "epicRealism.safetensors",
      "type": "checkpoint",
      "url": "https://huggingface.co/...",
      "size": "2.13 GB",
      "alternatives": ["https://civitai.com/..."]
    }
  ]
}
```

## 6. 用户交互流程

### 6.1 理想使用流程
```
用户："下载 workflow-outfit.json 的模型到 Pod xxx"
     ↓
系统：1. 连接 Pod 并上传脚本
     2. 分析工作流
     3. 检查本地模型
     4. 搜索缺失模型
     5. 执行批量下载
     6. 返回结果报告
```

### 6.2 交互示例
```
用户输入：
"帮我下载 /ComfyUI/user/default/workflows/outfit-workflow.json 的缺失模型"

系统输出：
=== 模型依赖分析 ===
✓ 找到 5 个模型依赖
✓ 本地已有 2 个
✗ 缺失 3 个

=== 搜索模型 ===
✓ epicRealism.safetensors - 找到 HuggingFace 链接
✓ control_v11p_sd15_openpose.fp16.safetensors - 找到官方仓库
⚠ outfit2outfi-ControlNet.safetensors - 找到可能的匹配

=== 开始下载 ===
[1/3] epicRealism.safetensors (2.13 GB)
[████████████████████] 100% 完成

[2/3] control_v11p_sd15_openpose.fp16.safetensors (723 MB)
[████████████████████] 100% 完成

=== 最终报告 ===
✅ 成功：2/3
⚠️ 需确认：1/3
  - outfit2outfi-ControlNet.safetensors
    可能是：outfit2outfit_v2.safetensors
```

## 11. 技术栈

- **脚本语言**：Python 3.8+
- **依赖工具**：wget, curl, ssh
- **MCP 工具**：HuggingFace、Tavily
- **支持平台**：Linux (RunPod环境)

## 12. 成功指标

1. **自动化率**：>90% 的模型可自动下载
2. **匹配准确率**：>85% 的模糊匹配正确
3. **用户操作**：从多步简化到1步
4. **处理时间**：平均每个模型 <2分钟

---

本PRD基于实际使用场景和技术验证编写，将随着使用反馈持续更新优化。