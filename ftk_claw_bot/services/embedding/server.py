import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='[EMBEDDING_SERVER] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    model: str
    version: str
    dimension: int


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dimension: int


def create_app(model_path: str, port: int = 18765) -> FastAPI:
    logger.info(f"create_app() called with model_path={model_path}, port={port}")
    
    embedder: Optional['Embedder'] = None
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal embedder
        
        logger.info(f"lifespan: 开始加载嵌入模型: {model_path}")
        
        try:
            from .embedder import Embedder
            embedder = Embedder(model_path=model_path)
            logger.info(f"lifespan: 嵌入服务启动成功，维度: {embedder.get_dimension()}")
        except Exception as e:
            logger.error(f"lifespan: 加载模型失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        yield
        
        logger.info("lifespan: 嵌入服务停止")
    
    app = FastAPI(
        title="嵌入服务",
        description="FTK Claw Bot 嵌入服务",
        version="2.0.0",
        lifespan=lifespan
    )
    
    @app.get("/health", response_model=HealthResponse)
    async def health():
        if embedder is None:
            raise HTTPException(status_code=503, detail="服务未初始化")
        
        return HealthResponse(
            status="ok",
            model="Qwen3-Embedding-0.6B",
            version="2.0.0",
            dimension=embedder.get_dimension()
        )
    
    @app.post("/embed", response_model=EmbedResponse)
    async def embed(request: EmbedRequest):
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
    
    logger.info("create_app() 完成，返回 FastAPI app")
    return app


def run_server(model_path: str, port: int):
    """运行服务器（在独立进程中调用）"""
    print(f"[EMBEDDING_SERVER] run_server() 开始执行")
    print(f"[EMBEDDING_SERVER] PID: {os.getpid()}")
    print(f"[EMBEDDING_SERVER] model_path: {model_path}")
    print(f"[EMBEDDING_SERVER] port: {port}")
    print(f"[EMBEDDING_SERVER] Python: {sys.executable}")
    print(f"[EMBEDDING_SERVER] 工作目录: {os.getcwd()}")
    sys.stdout.flush()
    
    try:
        import uvicorn
        print(f"[EMBEDDING_SERVER] uvicorn 导入成功")
        sys.stdout.flush()
        
        print(f"[EMBEDDING_SERVER] 创建 FastAPI app...")
        sys.stdout.flush()
        
        app = create_app(model_path, port)
        
        print(f"[EMBEDDING_SERVER] 启动 uvicorn 服务器...")
        sys.stdout.flush()
        
        server = uvicorn.Server(uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        ))
        server.run()
        
    except Exception as e:
        print(f"[EMBEDDING_SERVER] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise
