from PyQt6.QtCore import QObject, pyqtSignal
from typing import Callable, Any


class ThreadSafeSignal(QObject):
    """线程安全的信号类，用于在非Qt线程和Qt主线程之间安全传递数据"""
    signal = pyqtSignal(object, object)

    def __init__(self, callback: Callable):
        super().__init__()
        self.callback = callback
        self.signal.connect(self._on_signal)

    def emit(self, *args: Any, **kwargs: Any):
        """在非Qt线程中调用此方法，安全地传递数据到Qt主线程"""
        self.signal.emit(args, kwargs)

    def _on_signal(self, args: tuple, kwargs: dict):
        """在Qt主线程中执行回调"""
        try:
            self.callback(*args, **kwargs)
        except Exception:
            pass


def make_thread_safe(callback: Callable) -> ThreadSafeSignal:
    """将回调函数包装为线程安全的信号"""
    return ThreadSafeSignal(callback)
