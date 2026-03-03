# -*- coding: utf-8 -*-
import json
import subprocess
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import uuid

from loguru import logger


@dataclass
class AppSession:
    session_id: str
    process: Optional[subprocess.Popen] = None
    app_path: str = ""
    started_at: datetime = None
    window_handle: Optional[int] = None
    window_title: Optional[str] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()


@dataclass 
class SessionInfo:
    session_id: str
    session_type: str
    created_at: str
    last_accessed: str
    expires_at: str
    state: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionStore:
    MAX_WEB_SESSIONS = 5
    MAX_APP_SESSIONS = 10
    SESSION_TIMEOUT = 3600
    IDLE_TIMEOUT = 600
    
    def __init__(self, user_data_dir: Union[str, Path] = None):
        if user_data_dir is None:
            from ftk_claw_bot.utils.user_data_dir import user_data
            user_data_dir = user_data.base
        
        self._user_data_dir = Path(user_data_dir)
        self._sessions_db = self._user_data_dir / "sessions.db"
        self._web_sessions: Dict[str, Any] = {}
        self._app_sessions: Dict[str, AppSession] = {}
        self._session_info: Dict[str, SessionInfo] = {}
        self._lock = threading.Lock()
        
        self._init_db()
        self._start_cleanup_thread()
    
    def _init_db(self):
        import sqlite3
        conn = sqlite3.connect(self._sessions_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                metadata TEXT,
                state TEXT DEFAULT 'active'
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state)')
        conn.commit()
        conn.close()
    
    def _start_cleanup_thread(self):
        def cleanup_loop():
            while True:
                import time
                time.sleep(60)
                self._cleanup_expired_sessions()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def generate_session_id(self, session_type: str) -> str:
        uuid_str = str(uuid.uuid4())[:8]
        return f"sess_{session_type}_{uuid_str}"
    
    def create_web_session(self, session_id: str = None, web_automation=None) -> Dict[str, Any]:
        with self._lock:
            if len(self._web_sessions) >= self.MAX_WEB_SESSIONS:
                return {"success": False, "error": "session_limit_reached", 
                        "message": f"Maximum web sessions ({self.MAX_WEB_SESSIONS}) reached"}
            
            session_id = session_id or self.generate_session_id("web")
            now = datetime.now()
            expires_at = now + timedelta(seconds=self.SESSION_TIMEOUT)
            
            info = SessionInfo(
                session_id=session_id,
                session_type="web",
                created_at=now.isoformat(),
                last_accessed=now.isoformat(),
                expires_at=expires_at.isoformat(),
                state="active"
            )
            
            self._session_info[session_id] = info
            if web_automation:
                self._web_sessions[session_id] = web_automation
            
            self._save_session_to_db(info)
            
            logger.info(f"[SessionStore] Created web session: {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "expires_at": expires_at.isoformat()
            }
    
    def create_app_session(self, session_id: str = None, app_path: str = "", 
                           process: subprocess.Popen = None) -> Dict[str, Any]:
        with self._lock:
            if len(self._app_sessions) >= self.MAX_APP_SESSIONS:
                return {"success": False, "error": "session_limit_reached",
                        "message": f"Maximum app sessions ({self.MAX_APP_SESSIONS}) reached"}
            
            session_id = session_id or self.generate_session_id("app")
            now = datetime.now()
            expires_at = now + timedelta(seconds=self.SESSION_TIMEOUT)
            
            app_session = AppSession(
                session_id=session_id,
                process=process,
                app_path=app_path
            )
            
            info = SessionInfo(
                session_id=session_id,
                session_type="app",
                created_at=now.isoformat(),
                last_accessed=now.isoformat(),
                expires_at=expires_at.isoformat(),
                state="active",
                metadata={"app_path": app_path}
            )
            
            self._app_sessions[session_id] = app_session
            self._session_info[session_id] = info
            
            self._save_session_to_db(info)
            
            logger.info(f"[SessionStore] Created app session: {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "expires_at": expires_at.isoformat()
            }
    
    def get_session(self, session_id: str) -> Optional[Any]:
        with self._lock:
            info = self._session_info.get(session_id)
            if info is None:
                return None
            
            if info.session_type == "web":
                session = self._web_sessions.get(session_id)
            else:
                session = self._app_sessions.get(session_id)
            
            if session:
                info.last_accessed = datetime.now().isoformat()
                self._update_session_accessed(info)
            
            return session
    
    def get_or_create_web_session(self, session_id: str, web_automation_class=None):
        with self._lock:
            if session_id and session_id in self._web_sessions:
                info = self._session_info.get(session_id)
                if info:
                    info.last_accessed = datetime.now().isoformat()
                    self._update_session_accessed(info)
                return self._web_sessions[session_id], session_id, False
            
            result = self.create_web_session(session_id)
            if not result.get("success"):
                return None, None, False
            
            new_session_id = result["session_id"]
            
            if web_automation_class:
                web_automation = web_automation_class()
                self._web_sessions[new_session_id] = web_automation
                return web_automation, new_session_id, True
            
            return None, new_session_id, True
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            info = self._session_info.get(session_id)
            if info is None:
                return {"success": False, "error": "session_not_found",
                        "message": f"Session '{session_id}' not found"}
            
            if info.session_type == "web":
                web = self._web_sessions.pop(session_id, None)
                if web:
                    try:
                        web.stop()
                    except Exception as e:
                        logger.warning(f"[SessionStore] Error stopping web session: {e}")
            
            elif info.session_type == "app":
                app = self._app_sessions.pop(session_id, None)
                if app and app.process:
                    try:
                        app.process.terminate()
                        app.process.wait(timeout=5)
                    except Exception as e:
                        logger.warning(f"[SessionStore] Error terminating app: {e}")
            
            info.state = "closed"
            self._update_session_state(info)
            del self._session_info[session_id]
            
            logger.info(f"[SessionStore] Closed session: {session_id}")
            return {"success": True, "session_id": session_id}
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for session_id, info in self._session_info.items():
                result.append(asdict(info))
            return result
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            info = self._session_info.get(session_id)
            return asdict(info) if info else None
    
    def keepalive(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            info = self._session_info.get(session_id)
            if info is None:
                return {"success": False, "error": "session_not_found"}
            
            now = datetime.now()
            info.last_accessed = now.isoformat()
            info.expires_at = (now + timedelta(seconds=self.SESSION_TIMEOUT)).isoformat()
            self._update_session_accessed(info)
            
            return {"success": True, "session_id": session_id}
    
    def _save_session_to_db(self, info: SessionInfo):
        import sqlite3
        try:
            conn = sqlite3.connect(self._sessions_db)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_id, session_type, created_at, last_accessed, expires_at, metadata, state)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (info.session_id, info.session_type, info.created_at, 
                  info.last_accessed, info.expires_at, json.dumps(info.metadata), info.state))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SessionStore] Failed to save session to DB: {e}")
    
    def _update_session_accessed(self, info: SessionInfo):
        import sqlite3
        try:
            conn = sqlite3.connect(self._sessions_db)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions SET last_accessed = ?, expires_at = ? WHERE session_id = ?
            ''', (info.last_accessed, info.expires_at, info.session_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SessionStore] Failed to update session: {e}")
    
    def _update_session_state(self, info: SessionInfo):
        import sqlite3
        try:
            conn = sqlite3.connect(self._sessions_db)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sessions SET state = ? WHERE session_id = ?
            ''', (info.state, info.session_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[SessionStore] Failed to update session state: {e}")
    
    def _cleanup_expired_sessions(self):
        now = datetime.now()
        expired_ids = []
        
        with self._lock:
            for session_id, info in self._session_info.items():
                expires_at = datetime.fromisoformat(info.expires_at)
                if now > expires_at:
                    expired_ids.append(session_id)
        
        for session_id in expired_ids:
            logger.info(f"[SessionStore] Cleaning up expired session: {session_id}")
            self.close_session(session_id)
    
    def close_all_sessions(self):
        session_ids = list(self._session_info.keys())
        for session_id in session_ids:
            self.close_session(session_id)
