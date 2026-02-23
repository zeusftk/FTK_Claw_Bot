"""Embedding Service - FastAPI server for semantic memory.

这是一个无状态的嵌入服务，仅提供推理功能。
所有数据都存储在客户端（nanobot）。
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .embedder import Embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Config(BaseModel):
    """Embedding service configuration."""
    embed_model: str = "Qwen3-Embedding-0.6B-ONNX"
    embed_backend: str = "onnx"
    storage_path: str = "./data"
    host: str = "0.0.0.0"
    port: int = 8765
    dimension: Optional[int] = None
    device: str = "cpu"


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    model: str
    version: str
    dimension: int


class EmbedRequest(BaseModel):
    """嵌入请求"""
    texts: list[str]


class EmbedResponse(BaseModel):
    """嵌入响应"""
    embeddings: list[list[float]]
    dimension: int


def create_app(config: Config) -> FastAPI:
    """创建 FastAPI 应用实例。"""
    embedder: Optional[Embedder] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期处理器。"""
        nonlocal embedder
        
        logger.info(f"加载嵌入模型: {config.embed_model}")
        embedder = Embedder(
            model_name=config.embed_model,
            backend=config.embed_backend,
            dimension=config.dimension,
            device=config.device
        )
        
        logger.info(f"嵌入服务启动 (无状态模式, 维度: {embedder.get_dimension()})")
        yield
        
        logger.info("嵌入服务停止")

    app = FastAPI(
        title="嵌入服务 (无状态)",
        description="nanobot 无状态嵌入服务 - 所有数据存储在客户端",
        version="2.0.0",
        lifespan=lifespan
    )

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """健康检查端点。"""
        if embedder is None:
            raise HTTPException(status_code=503, detail="服务未初始化")
            
        return HealthResponse(
            status="ok",
            model="Qwen3-Embedding-0.6B",
            version="1.0.0",
            dimension=embedder.get_dimension()
        )

    @app.post("/embed", response_model=EmbedResponse)
    async def embed(request: EmbedRequest):
        """文本向量化并返回向量。
        
        这是一个无状态操作 - 向量返回给客户端
        用于本地存储。服务器不存储任何数据。
        """
        if embedder is None:
            raise HTTPException(status_code=503, detail="服务未初始化")
            
        if not request.texts:
            raise HTTPException(status_code=400, detail="未提供文本")
            
        try:
            embeddings = embedder.embed(request.texts)
            return EmbedResponse(
                embeddings=embeddings,
                dimension=embedder.get_dimension()
            )
        except Exception as e:
            logger.error(f"嵌入失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return app


app: Optional[FastAPI] = None


def main(config: Config):
    """运行服务器。"""
    global app
    import uvicorn
    
    app = create_app(config)
    uvicorn.run(
        app,
        host=config.host,
        port=config.port
    )


def run():
    """命令行入口点。"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FTK Embedding Service")
    parser.add_argument("--host", default="0.0.0.0", help="服务监听地址")
    parser.add_argument("--port", type=int, default=8765, help="服务监听端口")
    parser.add_argument("--model", default="Qwen3-Embedding-0.6B-ONNX", help="模型名称")
    parser.add_argument("--backend", default="onnx", help="推理后端")
    parser.add_argument("--device", default="cpu", help="运行设备")
    parser.add_argument("--dimension", type=int, default=None, help="嵌入维度")
    
    args = parser.parse_args()
    
    config = Config(
        embed_model=args.model,
        embed_backend=args.backend,
        host=args.host,
        port=args.port,
        device=args.device,
        dimension=args.dimension
    )
    
    main(config)


if __name__ == "__main__":
    run()
