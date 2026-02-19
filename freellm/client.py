"""
FreeLLM Client - Python 封装
通过 freellm 本地 server 调用 LLM，无需配置 API key
"""

import subprocess
import time
import json
import requests
import os
import signal
import atexit
from typing import Optional, Generator, Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class FreeLLMError(Exception):
    pass


class ServerNotRunningError(FreeLLMError):
    pass


class ServerStartError(FreeLLMError):
    pass


class APIError(FreeLLMError):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class Model:
    id: str
    name: str
    provider: str
    
    def __str__(self):
        return f"{self.provider}/{self.id}"


@dataclass
class Message:
    role: str
    content: str
    parts: List[Dict[str, Any]] = None
    
    @property
    def text(self) -> str:
        return self.content


@dataclass
class ChatResult:
    session_id: str
    message: Message
    raw: Dict[str, Any]


class FreeLLMClient:
    DEFAULT_PORT = 20100
    DEFAULT_HOSTNAME = "127.0.0.1"
    DEFAULT_MODEL = "freellm/glm-5-free"
    
    FREE_MODELS = [
        "freellm/glm-5-free",
        "freellm/kimi-k2.5-free", 
        "freellm/minimax-m2.5-free",
        "freellm/gpt-5-nano",
        "freellm/big-pickle",
    ]
    
    def __init__(
        self,
        port: int = None,
        hostname: str = None,
        auto_start: bool = True,
        auto_stop: bool = True,
        default_model: str = None,
    ):
        self.port = port or self.DEFAULT_PORT
        self.hostname = hostname or self.DEFAULT_HOSTNAME
        self.base_url = f"http://{self.hostname}:{self.port}"
        self._server_process: Optional[subprocess.Popen] = None
        self._auto_stop = auto_stop
        self._default_model = default_model or self.DEFAULT_MODEL
        self._managed_server = False
        
        if auto_start:
            self.start_server()
        
        if auto_stop:
            atexit.register(self.stop_server)
    
    def _check_server(self):
        if not self.is_running():
            raise ServerNotRunningError("FreeLLM server is not running")
    
    def start_server(self, timeout: int = 30) -> bool:
        if self.is_running():
            return True
        
        cmd = ["freellm", "serve", "--port", str(self.port), "--hostname", self.hostname]
        
        try:
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self._managed_server = True
        except FileNotFoundError:
            raise ServerStartError("'freellm' command not found. Please install freellm first.")
        except Exception as e:
            raise ServerStartError(f"Failed to start server: {e}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running():
                return True
            if self._server_process.poll() is not None:
                raise ServerStartError(f"Server process exited with code {self._server_process.returncode}")
            time.sleep(0.5)
        
        raise ServerStartError(f"Server failed to start within {timeout} seconds")
    
    def stop_server(self):
        if self._server_process and self._managed_server:
            try:
                os.killpg(os.getpgid(self._server_process.pid), signal.SIGTERM)
                self._server_process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self._server_process.pid), signal.SIGKILL)
                except:
                    pass
            self._server_process = None
            self._managed_server = False
    
    def is_running(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/global/health", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def health(self) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}/global/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def list_providers(self) -> Dict[str, Any]:
        self._check_server()
        resp = requests.get(f"{self.base_url}/provider")
        if resp.status_code != 200:
            raise APIError(f"Failed to list providers: {resp.text}", resp.status_code)
        return resp.json()
    
    def list_models(self, provider: str = None) -> List[Model]:
        self._check_server()
        resp = requests.get(f"{self.base_url}/config/providers")
        if resp.status_code != 200:
            raise APIError(f"Failed to list models: {resp.text}", resp.status_code)
        
        data = resp.json()
        models = []
        providers = data.get("providers", [])
        
        for p in providers:
            provider_id = p.get("id", "") if isinstance(p, dict) else str(p)
            if provider and provider != provider_id:
                continue
            provider_models = p.get("models", []) if isinstance(p, dict) else []
            for m in provider_models:
                if isinstance(m, dict):
                    model_id = m.get("id", "")
                    model_name = m.get("name", model_id)
                else:
                    model_id = str(m)
                    model_name = model_id
                models.append(Model(id=model_id, name=model_name, provider=provider_id))
        
        return models
    
    def get_free_models(self) -> List[Model]:
        return [m for m in self.list_models() if str(m) in self.FREE_MODELS]
    
    def create_session(self, title: Optional[str] = None, parent_id: Optional[str] = None) -> Dict[str, Any]:
        self._check_server()
        body = {}
        if title:
            body["title"] = title
        if parent_id:
            body["parentID"] = parent_id
        resp = requests.post(f"{self.base_url}/session", json=body)
        if resp.status_code != 200:
            raise APIError(f"Failed to create session: {resp.text}", resp.status_code)
        return resp.json()
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        self._check_server()
        resp = requests.get(f"{self.base_url}/session/{session_id}")
        if resp.status_code != 200:
            raise APIError(f"Failed to get session: {resp.text}", resp.status_code)
        return resp.json()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        self._check_server()
        resp = requests.get(f"{self.base_url}/session")
        if resp.status_code != 200:
            raise APIError(f"Failed to list sessions: {resp.text}", resp.status_code)
        return resp.json()
    
    def delete_session(self, session_id: str) -> bool:
        self._check_server()
        resp = requests.delete(f"{self.base_url}/session/{session_id}")
        return resp.status_code == 200
    
    def get_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        self._check_server()
        url = f"{self.base_url}/session/{session_id}/message"
        if limit:
            url += f"?limit={limit}"
        resp = requests.get(url)
        if resp.status_code != 200:
            raise APIError(f"Failed to get messages: {resp.text}", resp.status_code)
        return resp.json()
    
    def chat(
        self,
        message: str,
        model: str = None,
        session_id: Optional[str] = None,
        system: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> ChatResult:
        self._check_server()
        
        model = model or self._default_model
        provider_id, model_id = self._parse_model(model)
        
        if not session_id:
            session = self.create_session()
            session_id = session["id"]
        
        body = {
            "parts": [{"type": "text", "text": message}],
            "model": {
                "providerID": provider_id,
                "modelID": model_id
            }
        }
        
        if system:
            body["system"] = system
        if agent:
            body["agent"] = agent
        
        resp = requests.post(
            f"{self.base_url}/session/{session_id}/message",
            json=body
        )
        
        if resp.status_code != 200:
            raise APIError(f"Chat request failed: {resp.text}", resp.status_code)
        
        result = resp.json()
        parts = result.get("parts", [])
        
        text_content = ""
        for part in parts:
            if part.get("type") == "text":
                text_content = part.get("text", "")
                break
        
        msg = Message(
            role="assistant",
            content=text_content,
            parts=parts
        )
        
        return ChatResult(
            session_id=session_id,
            message=msg,
            raw=result
        )
    
    def chat_stream(
        self,
        message: str,
        model: str = None,
        session_id: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        self._check_server()
        
        model = model or self._default_model
        provider_id, model_id = self._parse_model(model)
        
        if not session_id:
            session = self.create_session()
            session_id = session["id"]
        
        body = {
            "parts": [{"type": "text", "text": message}],
            "model": {
                "providerID": provider_id,
                "modelID": model_id
            }
        }
        
        resp = requests.post(
            f"{self.base_url}/session/{session_id}/message",
            json=body,
            stream=True
        )
        
        if resp.status_code != 200:
            raise APIError(f"Chat stream request failed: {resp.text}", resp.status_code)
        
        for line in resp.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    yield data
                except json.JSONDecodeError:
                    continue
    
    def run_command(
        self,
        command: str,
        args: List[str] = None,
        session_id: Optional[str] = None,
        model: str = None,
    ) -> Dict[str, Any]:
        self._check_server()
        
        model = model or self._default_model
        provider_id, model_id = self._parse_model(model)
        
        if not session_id:
            session = self.create_session()
            session_id = session["id"]
        
        body = {
            "command": command,
            "arguments": args or [],
            "model": {
                "providerID": provider_id,
                "modelID": model_id
            }
        }
        
        resp = requests.post(
            f"{self.base_url}/session/{session_id}/command",
            json=body
        )
        
        if resp.status_code != 200:
            raise APIError(f"Command failed: {resp.text}", resp.status_code)
        
        return resp.json()
    
    def abort_session(self, session_id: str) -> bool:
        self._check_server()
        resp = requests.post(f"{self.base_url}/session/{session_id}/abort")
        return resp.status_code == 200
    
    def _parse_model(self, model: str) -> tuple:
        if "/" in model:
            provider, model_id = model.split("/", 1)
            return provider, model_id
        return "freellm", model
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._auto_stop:
            self.stop_server()
        return False
    
    def __repr__(self):
        status = "running" if self.is_running() else "stopped"
        return f"<FreeLLMClient {self.base_url} ({status})>"


def chat(
    message: str,
    model: str = "freellm/glm-5-free",
    **kwargs
) -> str:
    with FreeLLMClient(auto_start=True, auto_stop=True) as client:
        result = client.chat(message, model=model, **kwargs)
        return result.message.text


def chat_with_session(
    message: str,
    session_id: str,
    model: str = "freellm/glm-5-free",
    **kwargs
) -> ChatResult:
    with FreeLLMClient(auto_start=True, auto_stop=True) as client:
        return client.chat(message, model=model, session_id=session_id, **kwargs)


def list_free_models() -> List[Model]:
    with FreeLLMClient(auto_start=True, auto_stop=True) as client:
        return client.get_free_models()
