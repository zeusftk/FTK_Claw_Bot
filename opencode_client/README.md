# OpenCode Client

Python 客户端库和 HTTP API 服务，通过 [opencode](https://opencode.ai) 调用 LLM，**无需配置 API key**。

## 特性

- 零配置：使用 opencode 内置免费模型，无需申请 API key
- OpenAI 兼容：可直接使用 OpenAI SDK 调用
- 多种免费模型：GLM-5、Kimi K2.5、MiniMax M2.5、GPT-5 Nano、Big Pickle
- 多种使用方式：Python 客户端、OpenAI SDK、HTTP API
- 多轮对话：支持会话上下文
- 流式响应：支持 SSE 流式输出

## 安装

### 前置要求

1. 安装 [opencode CLI](https://opencode.ai)：
```bash
npm install -g opencode-ai
# 或
curl -fsSL https://opencode.ai/install | bash
```

2. 安装 opencode-client：
```bash
cd opencode_client
pip install -e .

# 如需 HTTP API 服务功能
pip install -e ".[server]"
```

## 快速开始

### 方式一：使用 OpenAI SDK（推荐）

启动服务：
```bash
cd opencode_client
python router.py
# 或
uvicorn router:app --host 0.0.0.0 --port 8000
```

Python 调用：
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # 任意值，无需真实 key
)

# 列出模型
models = client.models.list()
for m in models.data:
    print(m.id)

# Chat
response = client.chat.completions.create(
    model="glm-5-free",
    messages=[
        {"role": "system", "content": "你是一个友好的助手"},
        {"role": "user", "content": "你好"}
    ]
)
print(response.choices[0].message.content)

# 多轮对话
response = client.chat.completions.create(
    model="kimi-k2.5-free",
    messages=[
        {"role": "user", "content": "我叫小明"},
        {"role": "assistant", "content": "你好小明！"},
        {"role": "user", "content": "我叫什么？"}
    ]
)
print(response.choices[0].message.content)

# 流式输出
stream = client.chat.completions.create(
    model="glm-5-free",
    messages=[{"role": "user", "content": "讲个笑话"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

curl 调用：
```bash
# 列出模型
curl http://localhost:8000/v1/models

# Chat Completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5-free",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 方式二：Python 客户端库

```python
from opencode_client import chat, OpenCodeClient

# 简单调用
reply = chat("你好")
print(reply)

# 完整客户端
with OpenCodeClient() as client:
    # 查看免费模型
    models = client.get_free_models()
    for m in models:
        print(f"  {m}")
    
    # 单次对话
    result = client.chat("写一个 Python hello world")
    print(result.message.text)
    
    # 多轮对话
    result1 = client.chat("我叫小明")
    result2 = client.chat("我叫什么？", session_id=result1.session_id)
    print(result2.message.text)
```

## OpenAI 兼容 API

提供完全兼容 OpenAI 规范的 API 接口：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/models` | GET | 列出模型 |
| `/v1/models/{id}` | GET | 获取模型信息 |
| `/v1/chat/completions` | POST | Chat Completion |
| `/v1/chat/completions` | POST | 流式输出 (stream=true) |

响应格式完全兼容 OpenAI：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "glm-5-free",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## 免费模型

| 模型 ID | 提供商 | 说明 |
|---------|--------|------|
| `glm-5-free` | 智谱 | GLM-5 免费 |
| `kimi-k2.5-free` | 月之暗面 | Kimi K2.5 免费 |
| `minimax-m2.5-free` | MiniMax | M2.5 免费 |
| `gpt-5-nano` | OpenAI | GPT-5 Nano 免费 |
| `big-pickle` | - | Big Pickle 免费 |

> 注：也可使用 `opencode/` 前缀，如 `opencode/glm-5-free`

## 与其他工具集成

### LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy",
    model="glm-5-free"
)
response = llm.invoke("你好")
```

### LlamaIndex
```python
from llama_index.llms.openai import OpenAI

llm = OpenAI(
    api_base="http://localhost:8000/v1",
    api_key="dummy",
    model="glm-5-free"
)
response = llm.complete("你好")
```

## 架构

```
┌─────────────────┐
│ OpenAI SDK /    │
│ LangChain / curl│
└────────┬────────┘
         │ HTTP (OpenAI 格式)
         ▼
┌─────────────────┐     HTTP      ┌─────────────────┐
│ opencode-client │ ◄──────────► │ opencode serve  │
│ (router:8000)   │   localhost   │ (4096端口)      │
└─────────────────┘              └────────┬────────┘
                                          │
                                          │ HTTPS
                                          ▼
                                 ┌─────────────────┐
                                 │ opencode.internal│
                                 │ (云端 API 网关)  │
                                 └────────┬────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │ LLM Provider    │
                                 │ (智谱/MiniMax等) │
                                 └─────────────────┘
```

## 常见问题

### Q: 真的不需要 API key 吗？

A: 是的。opencode 内置的免费模型由云端网关处理认证，无需配置任何 API key。

### Q: 免费模型有限制吗？

A: 免费模型可能有请求频率限制。如需更高额度：
1. 在 [opencode.ai/auth](https://opencode.ai/auth) 注册获取 Zen API key
2. 配置其他 LLM 提供商的 API key

### Q: opencode serve 启动失败？

A: 确保：
1. opencode CLI 已正确安装
2. 端口 4096 未被占用
3. 运行 `opencode serve --port 4096` 测试

## License

MIT
