"""
OpenAI-Compatible API Router
提供完全兼容 OpenAI 规范的 API 接口，无需 API key
支持 OpenAI SDK 直接调用

Usage:
    python router.py --opencode-port 4096 --router-port 8000
"""

import sys
import subprocess


def check_and_install_deps():
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "requests": "requests",
    }
    
    missing = []
    for import_name, pip_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"[router] Installing missing dependencies: {', '.join(missing)}")
        import subprocess
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--break-system-packages", *missing
        ])
        print("[router] Dependencies installed successfully")


check_and_install_deps()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Union, Literal
import time
import json
import requests
import os
import signal
import uuid

OPENCODE_PORT = 4096
ROUTER_PORT = 8000
OPENCODE_URL = f"http://127.0.0.1:{OPENCODE_PORT}"
_server_process = None

FREE_MODELS = {
    "glm-5-free": {"id": "glm-5-free", "name": "GLM 5 Free", "provider": "opencode"},
    "kimi-k2.5-free": {"id": "kimi-k2.5-free", "name": "Kimi K2.5 Free", "provider": "opencode"},
    "minimax-m2.5-free": {"id": "minimax-m2.5-free", "name": "MiniMax M2.5 Free", "provider": "opencode"},
    "gpt-5-nano": {"id": "gpt-5-nano", "name": "GPT-5 Nano", "provider": "opencode"},
    "big-pickle": {"id": "big-pickle", "name": "Big Pickle", "provider": "opencode"},
}


def start_opencode_server():
    global _server_process
    
    if is_server_running():
        return
    
    cmd = ["opencode", "serve", "--port", str(OPENCODE_PORT), "--hostname", "127.0.0.1"]
    
    try:
        _server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except FileNotFoundError:
        raise RuntimeError("'opencode' command not found")
    
    for _ in range(30):
        if is_server_running():
            return
        if _server_process.poll() is not None:
            raise RuntimeError(f"Server exited with code {_server_process.returncode}")
        time.sleep(0.5)
    
    raise RuntimeError("Server failed to start")


def stop_opencode_server():
    global _server_process
    if _server_process:
        try:
            os.killpg(os.getpgid(_server_process.pid), signal.SIGTERM)
            _server_process.wait(timeout=5)
        except:
            try:
                os.killpg(os.getpgid(_server_process.pid), signal.SIGKILL)
            except:
                pass
        _server_process = None


def is_server_running() -> bool:
    try:
        resp = requests.get(f"{OPENCODE_URL}/global/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def parse_model(model: str) -> tuple:
    model = model.lower().strip()
    if model.startswith("opencode/"):
        model = model[9:]
    if model in FREE_MODELS:
        return "opencode", model
    if "/" in model:
        provider, model_id = model.split("/", 1)
        return provider, model_id
    return "opencode", model


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="OpenAI-Compatible API",
    description="OpenAI 兼容的 API 接口，无需 API key，可直接使用 OpenAI SDK",
    version="1.0.0",
    lifespan=lifespan
)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "glm-5-free"
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    user: Optional[str] = None


class ChatCompletionMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "content_filter"] = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage


class ModelObject(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "opencode"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelObject]


class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class StreamChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length"]] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]


def _build_system_message(messages: List[ChatMessage]) -> Optional[str]:
    for msg in messages:
        if msg.role == "system":
            return msg.content
    return None


def _build_user_message(messages: List[ChatMessage]) -> str:
    parts = []
    for msg in messages:
        if msg.role == "user":
            parts.append(msg.content)
    return "\n\n".join(parts) if parts else messages[-1].content


def _build_conversation(messages: List[ChatMessage]) -> str:
    lines = []
    for msg in messages:
        if msg.role == "system":
            lines.append(f"[System]: {msg.content}")
        elif msg.role == "user":
            lines.append(f"[User]: {msg.content}")
        elif msg.role == "assistant":
            lines.append(f"[Assistant]: {msg.content}")
    return "\n".join(lines)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@app.get("/")
async def root():
    return {
        "message": "OpenAI-Compatible API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models"
        },
        "free_models": list(FREE_MODELS.keys()),
        "opencode_port": OPENCODE_PORT,
        "router_port": ROUTER_PORT
    }


@app.get("/health")
async def health():
    return {"status": "ok", "opencode_running": is_server_running(), "opencode_port": OPENCODE_PORT, "router_port": ROUTER_PORT}


@app.get("/v1/models", response_model=ModelList)
@app.get("/models", response_model=ModelList)
async def list_models():
    now = int(time.time())
    models = []
    for model_id, info in FREE_MODELS.items():
        models.append(ModelObject(
            id=model_id,
            created=now,
            owned_by=info["provider"]
        ))
    return ModelList(data=models)


@app.get("/v1/models/{model_id}", response_model=ModelObject)
@app.get("/models/{model_id}", response_model=ModelObject)
async def get_model(model_id: str):
    model_id = model_id.lower().strip()
    if model_id.startswith("opencode/"):
        model_id = model_id[9:]
    
    if model_id not in FREE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    
    info = FREE_MODELS[model_id]
    return ModelObject(
        id=model_id,
        created=int(time.time()),
        owned_by=info["provider"]
    )


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    if not is_server_running():
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    provider_id, model_id = parse_model(request.model)
    
    session_resp = requests.post(f"{OPENCODE_URL}/session", json={})
    if session_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to create session")
    session_id = session_resp.json()["id"]
    
    system_prompt = _build_system_message(request.messages)
    user_message = _build_user_message(request.messages)
    
    body = {
        "parts": [{"type": "text", "text": user_message}],
        "model": {
            "providerID": provider_id,
            "modelID": model_id
        }
    }
    if system_prompt:
        body["system"] = system_prompt
    
    if request.stream:
        return StreamingResponse(
            _generate_stream(session_id, body, request.model),
            media_type="text/event-stream"
        )
    
    resp = requests.post(
        f"{OPENCODE_URL}/session/{session_id}/message",
        json=body
    )
    
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    
    result = resp.json()
    content = ""
    for part in result.get("parts", []):
        if part.get("type") == "text":
            content = part.get("text", "")
            break
    
    prompt_tokens = _estimate_tokens(user_message + (system_prompt or ""))
    completion_tokens = _estimate_tokens(content)
    
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatCompletionMessage(content=content),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )


async def _generate_stream(session_id: str, body: dict, model: str):
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                delta=DeltaMessage(role="assistant", content=""),
                finish_reason=None
            )
        ]
    )
    yield f"data: {chunk.model_dump_json()}\n\n"
    
    resp = requests.post(
        f"{OPENCODE_URL}/session/{session_id}/message",
        json=body,
        stream=True
    )
    
    full_content = ""
    for line in resp.iter_lines():
        if line:
            try:
                data = json.loads(line.decode("utf-8"))
                for part in data.get("parts", []):
                    if part.get("type") == "text":
                        text = part.get("text", "")
                        if text and text != full_content:
                            new_text = text[len(full_content):]
                            full_content = text
                            
                            chunk = ChatCompletionChunk(
                                id=completion_id,
                                created=created,
                                model=model,
                                choices=[
                                    StreamChoice(
                                        delta=DeltaMessage(content=new_text),
                                        finish_reason=None
                                    )
                                ]
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"
            except json.JSONDecodeError:
                continue
    
    chunk = ChatCompletionChunk(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            StreamChoice(
                delta=DeltaMessage(),
                finish_reason="stop"
            )
        ]
    )
    yield f"data: {chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/completions")
async def completions():
    raise HTTPException(
        status_code=400,
        detail="Legacy /v1/completions is not supported. Use /v1/chat/completions"
    )


@app.post("/v1/embeddings")
async def embeddings():
    raise HTTPException(
        status_code=400,
        detail="Embeddings API is not supported"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI-Compatible API Router")
    parser.add_argument("--opencode-port", type=int, default=4096,
                        help="Port for opencode serve (default: 4096)")
    parser.add_argument("--router-port", type=int, default=8000,
                        help="Port for router API server (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--skip-deps-check", action="store_true",
                        help="Skip dependency check on startup")
    
    args = parser.parse_args()
    
    OPENCODE_PORT = args.opencode_port
    ROUTER_PORT = args.router_port
    OPENCODE_URL = f"http://127.0.0.1:{OPENCODE_PORT}"
    
    print(f"[router] Starting with opencode_port={OPENCODE_PORT}, router_port={ROUTER_PORT}")
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=ROUTER_PORT)
