# -*- coding: utf-8 -*-
import os
import sys
import threading
import multiprocessing
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from loguru import logger

from ..service_registry import (
    ServiceInfo, ServiceStatus, register_service, LocalService
)


def _get_model_path() -> Optional[str]:
    """获取模型路径"""
    import sys
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent.parent
    
    logger.info(f"[EMBEDDING] _get_model_path() base: {base}")
    
    possible_paths = [
        base / "resources" / "models" / "Qwen3-Embedding-0.6B-ONNX",
        base / "models" / "Qwen3-Embedding-0.6B-ONNX",
    ]
    
    for model_path in possible_paths:
        logger.info(f"[EMBEDDING] 检查路径: {model_path}, exists: {model_path.exists()}")
        if model_path.exists():
            logger.info(f"[EMBEDDING] 找到模型路径: {model_path}")
            return str(model_path)
    
    logger.warning(f"[EMBEDDING] 未找到模型文件，已搜索路径: {[str(p) for p in possible_paths]}")
    return None


def _run_server_process(model_path: str, port: int):
    """在独立进程中运行服务器"""
    print(f"[EMBEDDING_PROCESS] 开始执行 _run_server_process")
    print(f"[EMBEDDING_PROCESS] PID: {os.getpid()}")
    print(f"[EMBEDDING_PROCESS] model_path: {model_path}")
    print(f"[EMBEDDING_PROCESS] port: {port}")
    print(f"[EMBEDDING_PROCESS] Python: {sys.executable}")
    print(f"[EMBEDDING_PROCESS] 工作目录: {os.getcwd()}")
    sys.stdout.flush()
    
    try:
        from .server import run_server
        print(f"[EMBEDDING_PROCESS] 导入 run_server 成功")
        sys.stdout.flush()
        
        run_server(model_path, port)
        
    except Exception as e:
        print(f"[EMBEDDING_PROCESS] 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise


class EmbeddingService(LocalService):
    """Embedding 服务"""
    
    def __init__(self, port: int = 18765):
        self._port = port
        self._status = ServiceStatus.STOPPED
        self._error: Optional[str] = None
        self._process: Optional[multiprocessing.Process] = None
        self._start_lock = threading.Lock()
        logger.info(f"[EMBEDDING] EmbeddingService 初始化，port={port}")
    
    @property
    def id(self) -> str:
        return "embedding"
    
    @property
    def name(self) -> str:
        return "Embedding 服务"
    
    @property
    def description(self) -> str:
        return "文本向量化服务 (Qwen3-Embedding-0.6B)"
    
    def start(self) -> bool:
        """启动服务（非阻塞）"""
        logger.info(f"[EMBEDDING] start() 被调用，当前状态: {self._status}")
        
        with self._start_lock:
            if self._status in (ServiceStatus.RUNNING, ServiceStatus.STARTING):
                logger.info(f"[EMBEDDING] 服务已在运行或启动中，跳过")
                return True
            
            if self._process and self._process.is_alive():
                logger.info(f"[EMBEDDING] 进程已存在且存活，跳过")
                return True
            
            try:
                self._status = ServiceStatus.STARTING
                self._error = None
                
                model_path = _get_model_path()
                if not model_path:
                    self._status = ServiceStatus.ERROR
                    self._error = "模型文件不存在"
                    logger.error("[EMBEDDING] 服务启动失败: 模型文件不存在")
                    return False
                
                logger.info(f"[EMBEDDING] 启动服务，端口: {self._port}, 模型: {model_path}")
                
                self._process = multiprocessing.Process(
                    target=_run_server_process,
                    args=(model_path, self._port),
                    daemon=True
                )
                self._process.start()
                
                logger.info(f"[EMBEDDING] 进程已启动，PID: {self._process.pid}")
                return True
                
            except Exception as e:
                self._status = ServiceStatus.ERROR
                self._error = str(e)
                logger.exception(f"[EMBEDDING] 服务启动异常: {e}")
                return False
    
    def check_started(self) -> bool:
        """检查服务是否已启动"""
        if self._status == ServiceStatus.RUNNING:
            return True
        
        if self._health_check():
            with self._start_lock:
                if self._status != ServiceStatus.RUNNING:
                    self._status = ServiceStatus.RUNNING
                    logger.info(f"[EMBEDDING] 服务已就绪，端口: {self._port}")
            return True
        
        if self._process and not self._process.is_alive():
            with self._start_lock:
                if self._status != ServiceStatus.ERROR:
                    self._status = ServiceStatus.ERROR
                    self._error = "进程已退出"
            return False
        
        return False
    
    def stop(self) -> bool:
        with self._start_lock:
            if self._process and self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=5)
                if self._process.is_alive():
                    self._process.kill()
            self._process = None
            self._status = ServiceStatus.STOPPED
            logger.info("[EMBEDDING] 服务已停止")
        return True
    
    def get_status(self) -> ServiceInfo:
        return ServiceInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            status=self._status,
            port=self._port,
            error=self._error
        )
    
    def get_config(self) -> Dict[str, Any]:
        return {"port": self._port}
    
    def set_config(self, config: Dict[str, Any]) -> bool:
        if "port" in config and self._status == ServiceStatus.STOPPED:
            self._port = config["port"]
        return True
    
    def _health_check(self) -> bool:
        try:
            r = requests.get(f"http://localhost:{self._port}/health", timeout=2)
            return r.status_code == 200
        except:
            return False


_service_instance: Optional[EmbeddingService] = None


def register_embedding_service(port: int = 18765) -> EmbeddingService:
    """注册 Embedding 服务"""
    global _service_instance
    if _service_instance is None:
        logger.info(f"[EMBEDDING] 创建 EmbeddingService 实例，port={port}")
        _service_instance = EmbeddingService(port=port)
        register_service(_service_instance)
        logger.info("[EMBEDDING] EmbeddingService 已注册到 ServiceRegistry")
        
        from ..service_registry import ServiceRegistry
        ServiceRegistry.register_auto_start("embedding")
        logger.info("[EMBEDDING] EmbeddingService 已注册为自启动服务")
    return _service_instance
