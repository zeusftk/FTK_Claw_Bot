import os
import sys
from typing import Optional

from loguru import logger

from .constants import VERSION, APP_NAME, APP_AUTHOR, UI
from .container import container
from .events import event_bus, EventType
from .plugins import PluginManager


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
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "Round"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    
    def setup_logging(self, console: bool = True):
        from .utils import setup_logger
        setup_logger("ftk_claw_bot", console=console)
    
    def create_qt_app(self):
        from PyQt6.QtWidgets import QApplication
        
        self._app = QApplication(sys.argv)
        self._app.setApplicationName(APP_NAME)
        self._app.setApplicationVersion(VERSION)
        self._app.setOrganizationName(APP_AUTHOR)
        self._app.setStyle("Fusion")
        
        return self._app
    
    def init_services(self, progress_callback=None):
        from .core import WSLManager, NanobotController, ConfigManager
        from .services import MonitorService, WindowsBridge
        
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
                    from .models import NanobotConfig
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
        
        # 加载内置插件
        plugin_manager.load_from_dir(os.path.join(os.path.dirname(__file__), "plugins"))
        
        # 初始化所有插件
        plugin_manager.initialize_all(self)
        
        monitor_service.start()
        windows_bridge.start()
        
        event_bus.publish(EventType.APP_STARTED, {"distros": len(distros) if distros else 0, "plugins": len(plugin_manager.get_all())})
    
    def init_services_async(self, progress_callback=None, completion_callback=None):
        """异步初始化服务
        
        Args:
            progress_callback: 进度回调函数，接收 (message, progress) 参数
            completion_callback: 完成回调函数，接收 (success, error_message) 参数
        """
        import threading
        
        def init():
            from .core import WSLManager, NanobotController, ConfigManager
            from .services import MonitorService, WindowsBridge
            
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
                            from .models import NanobotConfig
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
                
                plugin_manager.load_from_dir(os.path.join(os.path.dirname(__file__), "plugins"))
                
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
        from .gui import MainWindow
        
        self._window = MainWindow(
            wsl_manager=container.wsl_manager,
            config_manager=container.config_manager,
            nanobot_controller=container.nanobot_controller,
            monitor_service=container.monitor_service,
            windows_bridge=container.windows_bridge,
            skip_init=True
        )
        
        return self._window
    
    def show_splash(self, progress_callback=None):
        from .gui.widgets import SplashScreen
        
        self._splash = SplashScreen()
        self._splash.show()
        self._app.processEvents()
        
        return self._splash
    
    def close_splash(self):
        if self._splash:
            self._splash.close()
    
    def run(self):
        if self._window:
            self._window.show()
        
        event_bus.publish(EventType.APP_STARTED, {})
        return self._app.exec()
    
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
