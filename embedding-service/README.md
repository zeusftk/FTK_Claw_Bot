# Embedding Service (Stateless)

无状态的语义嵌入服务，为 nanobot 提供向量推理能力。

**关键特性：**
- 🚀 **无状态** - 不存储任何数据，仅提供推理
- 🔒 **数据安全** - 所有数据存储在客户端 (nanobot)
- 🔄 **可替换** - 服务可随时重启/替换，不影响数据
- 📦 **轻量级** - 支持 Qwen3-Embedding-0.6B 等小模型

## 快速开始

### 方式一：直接运行

```bash
pip install -r requirements.txt
python -m app.main
```

### 方式二：Docker

```bash
docker build -t embedding-service .
docker run -d -p 8765:8765 embedding-service
```

## API 接口

### 健康检查

```bash
GET /health

# Response
{
  "status": "ok",
  "model": "Qwen/Qwen3-Embedding-0.6B",
  "version": "2.0.0",
  "dimension": 1024
}
```

### 文本向量化

```bash
POST /embed
Content-Type: application/json

{
  "texts": ["文本1", "文本2"]
}

# Response
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "dimension": 1024
}
```

## 配置

环境变量：

| 变量 | 默认值 | 说明 |
|-----|-------|------|
| `EMBED_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | 嵌入模型 |
| `EMBED_BACKEND` | `sentence_transformer` | 后端类型 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8765` | 监听端口 |

## 模型选择

### 推荐：Qwen3-Embedding-0.6B

```bash
EMBED_MODEL=Qwen/Qwen3-Embedding-0.6B
```

### GGUF 量化版本

```bash
EMBED_BACKEND=llama_cpp
EMBED_MODEL=./models/qwen3-embedding-0.6b-q8_0.gguf
```

### 国内镜像

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 与 nanobot 集成

在 nanobot 的 `config.json` 中配置：

```json
{
  "memory": {
    "embeddingApi": {
      "enabled": true,
      "baseUrl": "http://localhost:8765",
      "timeout": 30
    }
  }
}
```

**数据存储：** 所有向量数据存储在 nanobot 本地的 `workspace/memory/vectors/` 目录。

## License

MIT
