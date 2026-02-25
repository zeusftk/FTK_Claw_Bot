from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt, pyqtSlot

from ..events import EventBus, EventType
from ..models import WSLDistro


@dataclass
class WSLState:
    distros: List[WSLDistro] = field(default_factory=list)
    running_count: int = 0
    stopped_count: int = 0
    total_count: int = 0
    
    def update(self, distros: List[WSLDistro]):
        self.distros = distros
        self.running_count = sum(1 for d in distros if d.is_running)
        self.stopped_count = len(distros) - self.running_count
        self.total_count = len(distros)


class WSLStateService(QObject):
    _instance = None
    
    state_changed = pyqtSignal()
    distro_started = pyqtSignal(str)
    distro_stopped = pyqtSignal(str)
    distro_removed = pyqtSignal(str)
    distro_imported = pyqtSignal(str)
    
    def __new__(cls, wsl_manager=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, wsl_manager=None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        super().__init__()
        self._wsl_manager = wsl_manager
        self._state = WSLState()
        self._event_bus = EventBus()
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_state)
        self._previous_distro_names: set = set()
        self._previous_running_names: set = set()
        self._initialized = True
        self._pending_refresh = False
        logger.info("WSLStateService 初始化完成")
    
    @classmethod
    def get_instance(cls) -> 'WSLStateService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def start_monitoring(self, interval_ms: int = 3000):
        self._refresh_state()
        self._timer.start(interval_ms)
        logger.info(f"WSLStateService 开始监控，间隔: {interval_ms}ms")
    
    def stop_monitoring(self):
        self._timer.stop()
        logger.info("WSLStateService 停止监控")

    def request_refresh_from_thread(self):
        """从非Qt线程安全地请求刷新状态
        
        此方法可从任何线程调用，会自动将刷新操作调度到Qt主线程执行。
        使用防抖机制避免频繁刷新。
        """
        if self._pending_refresh:
            return
        self._pending_refresh = True
        QMetaObject.invokeMethod(self, "_do_thread_safe_refresh", Qt.ConnectionType.QueuedConnection)

    @pyqtSlot()
    def _do_thread_safe_refresh(self):
        """在Qt主线程中执行的实际刷新操作"""
        self._pending_refresh = False
        self._refresh_state()

    def _refresh_state(self):
        if not self._wsl_manager:
            return
        
        distros = self._wsl_manager.list_distros()
        current_names = {d.name for d in distros}
        current_running_names = {d.name for d in distros if d.is_running}
        
        removed = self._previous_distro_names - current_names
        added = current_names - self._previous_distro_names
        newly_running = current_running_names - self._previous_running_names
        newly_stopped = self._previous_running_names - current_running_names
        
        self._state.update(distros)
        
        for name in removed:
            self._publish_event(EventType.WSL_DISTRO_REMOVED, {"distro_name": name})
            self.distro_removed.emit(name)
            logger.info(f"WSL 分发已移除: {name}")
        
        for name in added:
            self._publish_event(EventType.WSL_DISTRO_IMPORTED, {"distro_name": name})
            self.distro_imported.emit(name)
            logger.info(f"WSL 分发已导入: {name}")
        
        for name in newly_running:
            self._publish_event(EventType.WSL_DISTRO_STARTED, {"distro_name": name})
            self.distro_started.emit(name)
            logger.info(f"WSL 分发已启动: {name}")
        
        for name in newly_stopped:
            self._publish_event(EventType.WSL_DISTRO_STOPPED, {"distro_name": name})
            self.distro_stopped.emit(name)
            logger.info(f"WSL 分发已停止: {name}")
        
        if removed or added:
            self._publish_event(EventType.WSL_LIST_CHANGED, {
                "distros": [self._distro_to_dict(d) for d in distros],
                "added": list(added),
                "removed": list(removed)
            })
        
        self._publish_event(EventType.WSL_STATUS_CHANGED, {
            "distros": [self._distro_to_dict(d) for d in distros],
            "running_count": self._state.running_count,
            "stopped_count": self._state.stopped_count,
            "total_count": self._state.total_count
        })
        
        self.state_changed.emit()
        self._previous_distro_names = current_names
        self._previous_running_names = current_running_names
    
    def _distro_to_dict(self, distro: WSLDistro) -> Dict[str, Any]:
        return {
            "name": distro.name,
            "version": distro.version,
            "status": distro.status.value,
            "is_running": distro.is_running,
            "is_default": distro.is_default
        }
    
    def _publish_event(self, event_type: EventType, data: Dict[str, Any]):
        self._event_bus.publish(event_type, data, source="WSLStateService")
    
    def get_state(self) -> WSLState:
        return self._state
    
    def get_distros(self) -> List[WSLDistro]:
        return self._state.distros
    
    def get_running_distros(self) -> List[WSLDistro]:
        return [d for d in self._state.distros if d.is_running]
    
    def force_refresh(self):
        self._refresh_state()


wsl_state_service = None

def init_wsl_state_service(wsl_manager) -> WSLStateService:
    global wsl_state_service
    wsl_state_service = WSLStateService(wsl_manager)
    return wsl_state_service

def get_wsl_state_service() -> Optional[WSLStateService]:
    return wsl_state_service
