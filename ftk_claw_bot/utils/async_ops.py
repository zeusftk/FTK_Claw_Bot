import threading
from typing import Callable, TypeVar, Optional, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

T = TypeVar('T')


@dataclass
class AsyncResult:
    """异步操作结果数据类"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class AsyncOperation(QObject):
    """异步操作工具类，用于在后台线程执行阻塞操作并通过信号返回结果"""

    completed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

    def execute(self, operation: Callable[[], T], callback: Callable[[T], None]):
        """在后台线程执行操作，完成后通过回调返回结果"""
        def run():
            try:
                result = operation()
                self.completed.emit(result)
            except Exception as e:
                self.completed.emit(AsyncResult(success=False, error=str(e)))

        def oneshot_callback(result):
            self.completed.disconnect(oneshot_callback)
            callback(result)

        self.completed.connect(oneshot_callback)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def execute_with_callback(self, operation: Callable[[], T], on_success: Callable[[T], None], on_error: Callable[[str], None] = None):
        """执行操作并分别处理成功和失败"""
        def handle_result(result):
            if isinstance(result, AsyncResult) and not result.success:
                if on_error:
                    on_error(result.error)
            else:
                on_success(result)

        self.execute(operation, handle_result)


class AsyncWSLOperations:
    """WSL 异步操作集合"""

    def __init__(self, wsl_manager, parent=None):
        self._wsl_manager = wsl_manager
        self._parent = parent

    def list_distros_async(self, callback: Callable[[list], None], on_error: Callable[[str], None] = None):
        """异步获取 WSL 分发列表"""
        op = AsyncOperation(self._parent)
        op.execute_with_callback(
            lambda: self._wsl_manager.list_distros(),
            callback,
            on_error
        )

    def get_distro_async(self, distro_name: str, callback: Callable[[Any], None], on_error: Callable[[str], None] = None):
        """异步获取 WSL 分发信息"""
        op = AsyncOperation(self._parent)
        op.execute_with_callback(
            lambda: self._wsl_manager.get_distro(distro_name),
            callback,
            on_error
        )

    def start_distro_async(self, distro_name: str, callback: Callable[[bool], None], on_error: Callable[[str], None] = None):
        """异步启动 WSL 分发"""
        op = AsyncOperation(self._parent)
        op.execute_with_callback(
            lambda: self._wsl_manager.start_distro(distro_name),
            callback,
            on_error
        )

    def execute_command_async(self, distro_name: str, command: str, timeout: int, callback: Callable[[Any], None], on_error: Callable[[str], None] = None):
        """异步执行 WSL 命令"""
        op = AsyncOperation(self._parent)
        op.execute_with_callback(
            lambda: self._wsl_manager.execute_command(distro_name, command, timeout),
            callback,
            on_error
        )
