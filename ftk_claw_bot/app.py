import os
import sys
import threading
from typing import Optional
from pathlib import Path
from datetime import datetime

from loguru import logger

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .constants import VERSION, APP_NAME, APP_AUTHOR, UI
from .container import container
from .events import event_bus, EventType
from .plugins import PluginManager
from .utils import setup_logger
from .core import WSLManager, NanobotController, ConfigManager
from .services import MonitorService, WindowsBridge
from .models import NanobotConfig
from .gui import MainWindow
from .gui.widgets import SplashScreen


def _debug_log(msg: str):
    """调试日志 - 同时输出到日志文件和控制台"""
    try:
        print(f"[DEBUG] {msg}")
        logger.info(msg)
    except Exception:
        pass


def get_app_dir() -> Path:
    """获取应用目录，兼容打包和开发环境
    
    Nuitka onefile 模式下，资源被解压到临时目录，
    __file__ 会正确指向临时目录中的模块路径
    """
    return Path(__file__).parent


def get_exe_dir() -> Path:
    """获取 exe 所在目录（用于存放用户数据）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


class Application:
    _instance: Optional["Application"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._app = None
        self._window = None
        self._splash = None
    
    def setup_environment(self):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor
        )
    
    def setup_logging(self, console: bool = True):
        setup_logger("ftk_claw_bot", console=console)
    
    def create_qt_app(self):
        self._app = QApplication(sys.argv)
        self._app.setApplicationName(APP_NAME)
        self._app.setApplicationVersion(VERSION)
        self._app.setOrganizationName(APP_AUTHOR)
        self._app.setStyle("Fusion")
        
        return self._app
    
    def init_services(self, progress_callback=None):
        _debug_log("[INIT-01] 开始初始化服务...")
        
        if progress_callback:
            progress_callback("正在初始化 WSL 管理器...", 10)
        
        _debug_log("[INIT-02] 创建 WSLManager...")
        wsl_manager = WSLManager()
        container.wsl_manager = wsl_manager
        _debug_log("[INIT-02] WSLManager 创建成功")
        
        if progress_callback:
            progress_callback("正在加载配置...", 20)
        
        _debug_log("[INIT-03] 创建 ConfigManager...")
        config_manager = ConfigManager()
        container.config_manager = config_manager
        _debug_log("[INIT-03] ConfigManager 创建成功")
        
        _debug_log("[INIT-04] 创建 NanobotController...")
        nanobot_controller = NanobotController(wsl_manager)
        container.nanobot_controller = nanobot_controller
        _debug_log("[INIT-04] NanobotController 创建成功")
        
        if progress_callback:
            progress_callback("正在获取 WSL 分发列表...", 30)
        
        _debug_log("[INIT-05] 获取 WSL 分发列表...")
        distros = wsl_manager.list_distros()
        valid_distro_names = {d.name for d in distros} if distros else set()
        logger.info(f"有效的 WSL 分发: {valid_distro_names}")
        _debug_log(f"[INIT-05] 获取到 {len(distros) if distros else 0} 个 WSL 分发")
        
        if distros:
            total_distros = len(distros)
            for i, distro in enumerate(distros):
                progress = 30 + int((i + 1) / total_distros * 40)
                if progress_callback:
                    progress_callback(f"正在初始化 WSL 分发: {distro.name}...", progress)
                
                config = config_manager.get(distro.name)
                if not config:
                    config = NanobotConfig(
                        name=distro.name,
                        distro_name=distro.name
                    )
                    config_manager.save(config)
                    logger.info(f"为 WSL 分发 '{distro.name}' 创建新配置")
        
        if progress_callback:
            progress_callback("正在同步配置...", 75)
        
        _debug_log("[INIT-06] 同步配置...")
        if distros:
            config_manager.load_and_sync_from_wsl(
                wsl_manager, 
                nanobot_controller, 
                valid_distro_names
            )
        _debug_log("[INIT-06] 配置同步完成")
        
        if progress_callback:
            progress_callback("正在启动监控服务...", 85)
        
        _debug_log("[INIT-07] 创建 MonitorService...")
        monitor_service = MonitorService(wsl_manager, nanobot_controller)
        container.monitor_service = monitor_service
        _debug_log("[INIT-07] MonitorService 创建成功")
        
        _debug_log("[INIT-08] 获取默认配置...")
        default_config = config_manager.get_default()
        bridge_port = default_config.bridge_port if default_config else None
        _debug_log(f"[INIT-08] 默认配置获取完成, bridge_port: {bridge_port}")
        
        _debug_log("[INIT-09] 创建 WindowsBridge...")
        windows_bridge = WindowsBridge(port=bridge_port)
        container.windows_bridge = windows_bridge
        _debug_log("[INIT-09] WindowsBridge 创建成功")
        
        if progress_callback:
            progress_callback("正在初始化插件管理器...", 90)
        
        _debug_log("[INIT-10] 创建 PluginManager...")
        plugin_manager = PluginManager()
        container.plugin_manager = plugin_manager
        _debug_log("[INIT-10] PluginManager 创建成功")
        
        _debug_log(f"[INIT-11] 获取插件目录, get_app_dir()={get_app_dir()}...")
        plugin_dir = get_app_dir() / "plugins"
        logger.info(f"插件目录: {plugin_dir}")
        _debug_log(f"[INIT-11] 插件目录: {plugin_dir}, exists: {plugin_dir.exists()}")
        
        if plugin_dir.exists():
            _debug_log("[INIT-12] 加载插件...")
            plugin_manager.load_from_dir(str(plugin_dir))
            _debug_log("[INIT-12] 插件加载完成")
        else:
            logger.warning(f"插件目录不存在: {plugin_dir}")
            _debug_log(f"[INIT-12] 插件目录不存在: {plugin_dir}")
        
        _debug_log("[INIT-13] 初始化所有插件...")
        try:
            plugin_manager.initialize_all(self)
            _debug_log("[INIT-13] 插件初始化完成")
        except Exception as e:
            _debug_log(f"[INIT-13] 插件初始化异常: {e}")
            logger.error(f"插件初始化异常: {e}")
        
        _debug_log("[INIT-14] 启动 MonitorService...")
        try:
            monitor_service.start()
            _debug_log("[INIT-14] MonitorService 启动成功")
        except Exception as e:
            _debug_log(f"[INIT-14] MonitorService 启动失败: {e}")
            logger.error(f"MonitorService 启动失败: {e}")
        
        _debug_log("[INIT-15] 启动 WindowsBridge...")
        try:
            windows_bridge.start()
            _debug_log("[INIT-15] WindowsBridge 启动成功")
        except Exception as e:
            _debug_log(f"[INIT-15] WindowsBridge 启动失败: {e}")
            logger.error(f"WindowsBridge 启动失败: {e}")
        
        _debug_log("[INIT-16] 发布 APP_STARTED 事件...")
        try:
            event_bus.publish(EventType.APP_STARTED, {"distros": len(distros) if distros else 0, "plugins": len(plugin_manager.get_all())})
            _debug_log("[INIT-16] 事件发布完成")
        except Exception as e:
            _debug_log(f"[INIT-16] 事件发布失败: {e}")
            logger.error(f"事件发布失败: {e}")
        
        _debug_log("[INIT] 服务初始化全部完成!")
    
    def init_services_async(self, progress_callback=None, completion_callback=None):
        """异步初始化服务
        
        Args:
            progress_callback: 进度回调函数，接收 (message, progress) 参数
            completion_callback: 完成回调函数，接收 (success, error_message) 参数
        """
        def init():
            
            try:
                if progress_callback:
                    progress_callback("正在初始化 WSL 管理器...", 10)
                
                wsl_manager = WSLManager()
                container.wsl_manager = wsl_manager
                
                if progress_callback:
                    progress_callback("正在加载配置...", 20)
                
                config_manager = ConfigManager()
                container.config_manager = config_manager
                
                nanobot_controller = NanobotController(wsl_manager)
                container.nanobot_controller = nanobot_controller
                
                if progress_callback:
                    progress_callback("正在获取 WSL 分发列表...", 30)
                
                distros = wsl_manager.list_distros()
                valid_distro_names = {d.name for d in distros} if distros else set()
                logger.info(f"有效的 WSL 分发: {valid_distro_names}")
                
                if distros:
                    total_distros = len(distros)
                    for i, distro in enumerate(distros):
                        progress = 30 + int((i + 1) / total_distros * 40)
                        if progress_callback:
                            progress_callback(f"正在初始化 WSL 分发: {distro.name}...", progress)
                        
                        config = config_manager.get(distro.name)
                        if not config:
                            config = NanobotConfig(
                                name=distro.name,
                                distro_name=distro.name
                            )
                            config_manager.save(config)
                            logger.info(f"为 WSL 分发 '{distro.name}' 创建新配置")
                
                if progress_callback:
                    progress_callback("正在同步配置...", 75)
                
                if distros:
                    config_manager.load_and_sync_from_wsl(
                        wsl_manager, 
                        nanobot_controller, 
                        valid_distro_names
                    )
                
                if progress_callback:
                    progress_callback("正在启动监控服务...", 85)
                
                monitor_service = MonitorService(wsl_manager, nanobot_controller)
                container.monitor_service = monitor_service
                
                default_config = config_manager.get_default()
                bridge_port = default_config.bridge_port if default_config else None
                
                windows_bridge = WindowsBridge(port=bridge_port)
                container.windows_bridge = windows_bridge
                
                if progress_callback:
                    progress_callback("正在初始化插件管理器...", 90)
                
                plugin_manager = PluginManager()
                container.plugin_manager = plugin_manager
                
                plugin_dir = get_app_dir() / "plugins"
                logger.info(f"插件目录: {plugin_dir}")
                
                if plugin_dir.exists():
                    plugin_manager.load_from_dir(str(plugin_dir))
                else:
                    logger.warning(f"插件目录不存在: {plugin_dir}")
                
                plugin_manager.initialize_all(self)
                
                monitor_service.start()
                windows_bridge.start()
                
                event_bus.publish(EventType.APP_STARTED, {"distros": len(distros) if distros else 0, "plugins": len(plugin_manager.get_all())})
                
                if completion_callback:
                    completion_callback(True, None)
            except Exception as e:
                logger.error(f"服务初始化失败: {e}")
                if completion_callback:
                    completion_callback(False, str(e))
        
        thread = threading.Thread(target=init, daemon=True)
        thread.start()
    
    def create_main_window(self):
        _debug_log("[WINDOW-01] 开始创建主窗口...")
        try:
            self._window = MainWindow(
                wsl_manager=container.wsl_manager,
                config_manager=container.config_manager,
                nanobot_controller=container.nanobot_controller,
                monitor_service=container.monitor_service,
                windows_bridge=container.windows_bridge,
                skip_init=True
            )
            _debug_log(f"[WINDOW-01] 主窗口创建成功, type: {type(self._window)}")
        except Exception as e:
            _debug_log(f"[WINDOW-01] 主窗口创建失败: {e}")
            import traceback
            _debug_log(f"[WINDOW-01] 堆栈: {traceback.format_exc()}")
            raise
        
        return self._window
    
    def show_splash(self, progress_callback=None):
        _debug_log("[SPLASH-01] 创建启动画面...")
        self._splash = SplashScreen()
        _debug_log("[SPLASH-02] 显示启动画面...")
        self._splash.show()
        self._app.processEvents()
        _debug_log("[SPLASH-02] 启动画面显示成功")
        
        return self._splash
    
    def close_splash(self):
        _debug_log("[SPLASH-03] 关闭启动画面...")
        if self._splash:
            self._splash.close()
            _debug_log("[SPLASH-03] 启动画面已关闭")
        else:
            _debug_log("[SPLASH-03] 无启动画面需要关闭")
    
    def run(self):
        _debug_log("[RUN-01] 进入事件循环...")
        if self._window:
            _debug_log("[RUN-02] 显示主窗口...")
            self._window.show()
            _debug_log("[RUN-02] 主窗口已显示")
        else:
            _debug_log("[RUN-02] 警告: 主窗口为 None!")
        
        _debug_log("[RUN-03] 发布 APP_STARTED 事件...")
        event_bus.publish(EventType.APP_STARTED, {})
        _debug_log("[RUN-03] 事件发布完成")
        
        _debug_log("[RUN-04] 调用 QApplication.exec()...")
        result = self._app.exec()
        _debug_log(f"[RUN-04] QApplication.exec() 返回, exit_code: {result}")
        return result
    
    def shutdown(self):
        event_bus.publish(EventType.APP_SHUTDOWN, {})
        
        if container.plugin_manager:
            container.plugin_manager.shutdown_all()
        
        if container.monitor_service:
            container.monitor_service.stop()
        
        if container.windows_bridge:
            container.windows_bridge.stop()
        
        logger.info("应用已关闭")
    
    @property
    def app(self):
        return self._app
    
    @property
    def window(self):
        return self._window
