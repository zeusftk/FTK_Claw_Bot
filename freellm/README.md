# FreeLLM Client

Python LLM 客户端，通过本地 FreeLLM server 调用 LLM，无需配置 API key。

## 功能特性

- 🚀 **零配置启动** - 自动启动本地 LLM 服务
- 🔌 **OpenAI 兼容 API** - 提供标准的 OpenAI API 接口
- 🖥️ **图形界面** - PyQt6 现代化深色主题界面
- 📦 **WSL 支持** - 在 WSL 分发中管理多个 LLM 服务
- 🔄 **自动端口分配** - 自动为每个服务分配独立端口

## 安装

```bash
pip install -e .
```

## 使用

### 命令行

```bash
# 启动图形界面
freellm-client

# 或
python -m freellm
```

### Python API

```python
from freellm import FreeLLMClient

# 创建客户端
client = FreeLLMClient()

# 发送消息
result = client.chat("你好！")
print(result.message.text)

# 使用指定模型
result = client.chat("Hello!", model="freellm/glm-5-free")

# 流式输出
for chunk in client.chat_stream("写一首诗"):
    print(chunk.get("text", ""), end="")

# 使用上下文
with FreeLLMClient() as client:
    result = client.chat("你好")
    print(result.message.text)
```

## 服务管理

### 端口分配

| 服务 | 端口范围 |
|------|----------|
| LLM 服务 | 20100-20199 |
| Router 服务 | 20200-20299 |

### 图形界面

1. 选择 WSL 分发
2. 配置端口（可选）
3. 点击"启动"按钮
4. 通过 `http://127.0.0.1:20200` 访问 OpenAI 兼容 API

## API 端点

Router 服务提供以下端点：

- `GET /health` - 健康检查
- `POST /v1/chat/completions` - OpenAI 兼容聊天接口
- `GET /v1/models` - 列出可用模型

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black .
ruff check .
```

## 许可证

MIT License
