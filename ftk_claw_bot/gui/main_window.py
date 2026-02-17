import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QStatusBar, QSystemTrayIcon, QMenu, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap, QColor, QPainter

from ..core import (
    WSLManager, NanobotController, ConfigManager,
    NanobotGatewayManager, BridgeManager, GatewayStatus
)
from ..services import WindowsBridge, MonitorService, NanobotChatClient, ConnectionStatus
from ..utils import make_thread_safe
from ..constants import Bridge
from .widgets import ConfigPanel, LogPanel, OverviewPanel, ChatPanel, WindowsBridgePanel, CommandPanel, NanobotPanel


class MainWindow(QMainWindow):
    def __init__(
        self,
        wsl_manager=None,
        config_manager=None,
        nanobot_controller=None,
        monitor_service=None,
        windows_bridge=None,
        skip_init=False
    ):
        super().__init__()
        
        if skip_init and wsl_manager and config_manager and nanobot_controller:
            self._wsl_manager = wsl_manager
            self._config_manager = config_manager
            self._nanobot_controller = nanobot_controller
            self._monitor_service = monitor_service
            self._windows_bridge = windows_bridge
            self._gateway_manager: Optional[NanobotGatewayManager] = None
            self._bridge_manager: Optional[BridgeManager] = None
            self._chat_clients: dict[str, NanobotChatClient] = {}
            self._client_count_timer = QTimer()
            self._client_count_timer.timeout.connect(self._update_client_count)
            
            self._init_ui()
            self._init_managers_skip()
            self._init_connections()
            self._init_tray()
            self._init_chat()
        else:
            self._wsl_manager = WSLManager()
            self._config_manager = ConfigManager()
            self._nanobot_controller = NanobotController(self._wsl_manager)
            self._windows_bridge = WindowsBridge()
            self._monitor_service = MonitorService(self._wsl_manager, self._nanobot_controller)

            self._gateway_manager: Optional[NanobotGatewayManager] = None
            self._bridge_manager: Optional[BridgeManager] = None
            self._chat_clients: dict[str, NanobotChatClient] = {}
            self._client_count_timer = QTimer()
            self._client_count_timer.timeout.connect(self._update_client_count)
            
            self._init_ui()
            self._init_managers()
            self._init_connections()
            self._init_tray()
            self._init_chat()

    def _init_ui(self):
        self.setWindowTitle("FTK_Claw_Bot")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav_frame = QFrame()
        nav_frame.setFixedWidth(200)
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel("FTK_Claw_Bot")
        title_label.setObjectName("navTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        nav_layout.addWidget(title_label)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setSpacing(5)
        self.nav_list.addItem(QListWidgetItem("概览"))
        self.nav_list.addItem(QListWidgetItem("配置管理"))
        self.nav_list.addItem(QListWidgetItem("命令执行"))
        self.nav_list.addItem(QListWidgetItem("聊天"))
        self.nav_list.addItem(QListWidgetItem("桥接"))
        self.nav_list.addItem(QListWidgetItem("日志查看"))
        self.nav_list.setCurrentRow(0)
        nav_layout.addWidget(self.nav_list)

        nav_layout.addStretch()

        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setObjectName("versionLabel")
        nav_layout.addWidget(version_label)

        main_layout.addWidget(nav_frame)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")

        self.overview_panel = OverviewPanel(
            self._wsl_manager,
            self._nanobot_controller,
            self._config_manager
        )
        self.config_panel = ConfigPanel(
            self._config_manager,
            self._wsl_manager,
            self._nanobot_controller
        )
        self.nanobot_panel = NanobotPanel(
            self._wsl_manager,
            self._nanobot_controller,
            self._config_manager
        )
        self.command_panel = CommandPanel(self._wsl_manager)
        self.chat_panel = ChatPanel(self._config_manager, self._nanobot_controller, self._wsl_manager)
        self.bridge_panel = WindowsBridgePanel(
            windows_bridge=self._windows_bridge,
            wsl_manager=self._wsl_manager
        )
        self.log_panel = LogPanel()

        self.content_stack.addWidget(self.overview_panel)
        self.content_stack.addWidget(self.config_panel)
        self.content_stack.addWidget(self.command_panel)
        self.content_stack.addWidget(self.chat_panel)
        self.content_stack.addWidget(self.bridge_panel)
        self.content_stack.addWidget(self.log_panel)

        main_layout.addWidget(self.content_stack, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.wsl_status_label = QLabel("WSL: 未检测")
        self.nanobot_status_label = QLabel("Nanobot: 未运行")
        self.resource_label = QLabel("CPU: -- | MEM: --")

        self.status_bar.addWidget(self.wsl_status_label)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.nanobot_status_label)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.resource_label)
        self.status_bar.addPermanentWidget(QLabel("FTK_Claw_Bot v0.1.0"))

        self._apply_styles()

    def _apply_styles(self):
        from .styles import get_stylesheet
        self.setStyleSheet(get_stylesheet())

    def _init_managers(self):
        from loguru import logger
        
        distros = self._wsl_manager.list_distros()
        valid_distro_names = {d.name for d in distros} if distros else set()
        
        logger.info(f"有效的 WSL 分发: {valid_distro_names}")
        
        if distros:
            self._config_manager.load_and_sync_from_wsl(
                self._wsl_manager, 
                self._nanobot_controller, 
                valid_distro_names
            )
            
            all_configs = self._config_manager.get_all()
            if all_configs:
                config_names = list(all_configs.keys())
                self._config_manager.set_default(config_names[0])

        self._monitor_service.start()
        self._windows_bridge.start()
    
    def _init_managers_skip(self):
        all_configs = self._config_manager.get_all()
        if all_configs:
            config_names = list(all_configs.keys())
            default_config = self._config_manager.get_default()
            if not default_config:
                self._config_manager.set_default(config_names[0])
        
        self.bridge_panel.set_bridge_status(self._windows_bridge.is_running)

    def _init_connections(self):
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # 使用线程安全的信号包装回调
        self._safe_wsl_callback = make_thread_safe(self._on_wsl_status_changed)
        self._safe_nanobot_callback = make_thread_safe(self._on_nanobot_status_changed)
        self._safe_resources_callback = make_thread_safe(self._on_resources_updated)

        self._monitor_service.register_callback("wsl_status", self._safe_wsl_callback.emit)
        self._monitor_service.register_callback("nanobot_status", self._safe_nanobot_callback.emit)
        self._monitor_service.register_callback("resources", self._safe_resources_callback.emit)

        self.overview_panel.distro_started.connect(self._on_distro_started)
        self.overview_panel.distro_stopped.connect(self._on_distro_stopped)
        self.overview_panel.distro_imported.connect(self._on_distro_imported)
        self.config_panel.config_saved.connect(self._on_config_saved)
        
        self.nanobot_panel.instance_started.connect(self._on_nanobot_instance_started)
        self.nanobot_panel.instance_stopped.connect(self._on_nanobot_instance_stopped)
        self.nanobot_panel.instance_restarted.connect(self._on_nanobot_instance_restarted)

        # Register log callback to forward nanobot logs to log panel
        self._nanobot_controller.register_log_callback(self._on_nanobot_log)

        # Chat panel connections
        self.chat_panel.message_sent.connect(self._on_chat_message_sent)
        self.chat_panel.connect_clicked.connect(self._on_chat_connect)
        self.chat_panel.disconnect_clicked.connect(self._on_chat_disconnect)
        self.chat_panel.clear_clicked.connect(self._on_chat_clear)
        # 新增：单个bot的连接/断开信号
        self.chat_panel.nanobot_connect_requested.connect(self._on_single_nanobot_connect)
        self.chat_panel.nanobot_disconnect_requested.connect(self._on_single_nanobot_disconnect)
        
        # Bridge panel connections
        self.bridge_panel.start_bridge.connect(self._on_start_bridge)
        self.bridge_panel.stop_bridge.connect(self._on_stop_bridge)
        self.bridge_panel.port_changed.connect(self._on_bridge_port_changed)
        self.bridge_panel.restart_wsl.connect(self._on_restart_wsl)
        self.bridge_panel.refresh_distros.connect(self._on_refresh_distros)
        self.bridge_panel.start_wsl_distro.connect(self._on_start_wsl_distro)
        self.bridge_panel.stop_wsl_distro.connect(self._on_stop_wsl_distro)
        self.bridge_panel.refresh_wsl_status.connect(self._on_refresh_wsl_status)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 120, 212))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setBrush(QColor(255, 255, 255))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(16)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F")
        painter.end()

        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("FTK_Claw_Bot")

        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.showNormal)
        show_action.triggered.connect(self.activateWindow)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _init_chat(self):
        default_config = self._config_manager.get_default()
        if default_config:
            self._gateway_manager = NanobotGatewayManager(
                self._wsl_manager,
                port=default_config.gateway_port
            )
            self._gateway_manager.register_status_callback(self._on_gateway_status)

            bridge_port = default_config.bridge_port or Bridge.DEFAULT_WINDOWS_PORT

            self._bridge_manager = BridgeManager(
                self._wsl_manager,
                windows_port=bridge_port
            )
            self.bridge_panel.set_bridge_port(bridge_port)

    def _on_gateway_status(self, status: GatewayStatus):
        pass

    def _update_client_count(self):
        from loguru import logger
        if self._windows_bridge and self._windows_bridge.is_running:
            clients_info = self._windows_bridge.get_connected_clients_info()
            distros = self._wsl_manager.list_distros()
            logger.debug(f"[Bridge] 客户端信息: {clients_info}")
            self.bridge_panel.update_clients_info(clients_info)
            self.bridge_panel.update_wsl_connection_status(distros, clients_info)
        else:
            logger.debug(f"[Bridge] 桥接未运行: windows_bridge={self._windows_bridge is not None}, is_running={self._windows_bridge.is_running if self._windows_bridge else False}")

    def _on_start_bridge(self):
        """处理启动桥接服务"""
        from loguru import logger
        logger.info("=== 开始启动桥接服务 ===")
        
        if self._windows_bridge:
            if not self._windows_bridge.is_running:
                success = self._windows_bridge.start()
                if success:
                    logger.info("✅ 桥接服务启动成功")
                    self._client_count_timer.start(2000)
                else:
                    logger.error("❌ 桥接服务启动失败")
            else:
                logger.info("桥接服务已经在运行")
        else:
            logger.error("桥接服务未初始化")

    def _on_stop_bridge(self):
        """处理停止桥接服务"""
        from loguru import logger
        logger.info("=== 开始停止桥接服务 ===")
        
        self._client_count_timer.stop()
        
        if self._windows_bridge:
            if self._windows_bridge.is_running:
                self._windows_bridge.stop()
                logger.info("✅ 桥接服务停止成功")
            else:
                logger.info("桥接服务已经停止")
        else:
            logger.error("桥接服务未初始化")

    def _on_bridge_port_changed(self, port: int):
        """处理桥接端口变更 - 自动同步配置并重启 IPC Server"""
        from loguru import logger
        logger.info(f"桥接端口变更为: {port}")
        
        default_config = self._config_manager.get_default()
        if default_config:
            default_config.bridge_port = port
            self._config_manager.save(default_config)
            
            from ..core.config_sync_manager import ConfigSyncManager
            sync_manager = ConfigSyncManager(self._wsl_manager)
            
            for config in self._config_manager.get_all().values():
                config.bridge_port = port
                self._config_manager.save(config)
                sync_manager.sync_ftk_to_wsl(config)
            
            logger.info("配置已同步到所有 WSL 发行版")
        
        if self._bridge_manager:
            self._bridge_manager.update_port(port)
        
        if self._windows_bridge and self._windows_bridge.is_running:
            logger.info("通知已连接的客户端端口变更...")
            self._windows_bridge.notify_port_change(port)
            
            logger.info("重启 IPC Server...")
            self._windows_bridge.stop()
            self._windows_bridge = WindowsBridge(port=port)
            self._windows_bridge.start()
            logger.info(f"IPC Server 已重启，监听端口: {port}")

    def _on_restart_wsl(self, distro_name: str):
        """处理重启 WSL 分发"""
        from loguru import logger
        logger.info(f"重启 WSL 分发: {distro_name}")
        
        distro = self._wsl_manager.get_distro(distro_name)
        if distro:
            if distro.is_running:
                self._wsl_manager.stop_distro(distro_name)
            self._wsl_manager.start_distro(distro_name)
            logger.info(f"✅ WSL 分发已重启: {distro_name}")
        else:
            logger.error(f"❌ 未找到 WSL 分发: {distro_name}")

    def _on_refresh_distros(self):
        """处理刷新 WSL 分发列表"""
        from loguru import logger
        logger.info("刷新 WSL 分发列表")
        
        distros = self._wsl_manager.list_distros()
        self.bridge_panel.update_distro_list(distros)
        logger.info(f"✅ 已刷新分发列表，共 {len(distros)} 个")

    def _on_start_wsl_distro(self, distro_name: str):
        """处理启动 WSL 分发"""
        from loguru import logger
        logger.info(f"启动 WSL 分发: {distro_name}")
        
        success = self._wsl_manager.start_distro(distro_name)
        if success:
            logger.info(f"✅ WSL 分发已启动: {distro_name}")
            distros = self._wsl_manager.list_distros()
            self.bridge_panel.update_distro_list(distros)
        else:
            logger.error(f"❌ WSL 分发启动失败: {distro_name}")

    def _on_stop_wsl_distro(self, distro_name: str):
        """处理停止 WSL 分发"""
        from loguru import logger
        logger.info(f"停止 WSL 分发: {distro_name}")
        
        success = self._wsl_manager.stop_distro(distro_name)
        if success:
            logger.info(f"✅ WSL 分发已停止: {distro_name}")
            distros = self._wsl_manager.list_distros()
            self.bridge_panel.update_distro_list(distros)
        else:
            logger.error(f"❌ WSL 分发停止失败: {distro_name}")

    def _on_refresh_wsl_status(self):
        """刷新 WSL 连通状态"""
        from loguru import logger
        logger.info("刷新 WSL 连通状态")
        
        distros = self._wsl_manager.list_distros()
        clients_info = []
        if self._windows_bridge and self._windows_bridge.is_running:
            clients_info = self._windows_bridge.get_connected_clients_info()
        
        self.bridge_panel.update_wsl_connection_status(distros, clients_info)
        self.bridge_panel.update_clients_info(clients_info)
        self.bridge_panel._add_log(f"✓ WSL 连通状态已刷新，共 {len(distros)} 个分发")

    def _on_chat_connect(self):
        from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
        from loguru import logger
        
        logger.info("=== 开始聊天连接流程 ===")
        
        # 获取选中的 nanobots
        selected_nanobots = list(self.chat_panel._selected_nanobots)
        if not selected_nanobots:
            # 如果没有选中，使用默认配置
            default_config = self._config_manager.get_default()
            if not default_config:
                logger.error("连接失败: 没有配置")
                self.chat_panel.show_error("请先配置 nanobot")
                return
            selected_nanobots = [default_config.name]
        
        logger.info(f"准备连接到 nanobots: {selected_nanobots}")
        
        self.chat_panel.set_connecting()

        if not self._gateway_manager:
            logger.error("连接失败: Gateway 管理器未初始化")
            self.chat_panel.show_error("Gateway 管理器未初始化")
            return
        
        # 创建确认对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("连接 Gateway")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # 构建连接信息显示
        info_text = "即将连接到以下 Nanobot:\n\n"
        valid_bots = []
        
        for nanobot_name in selected_nanobots:
            config = self._config_manager.get(nanobot_name)
            if not config:
                logger.warning(f"未找到 {nanobot_name} 的配置，跳过")
                continue
            
            # 检查 WSL 分发是否运行
            distro = self._wsl_manager.get_distro(config.distro_name)
            if not distro or not distro.is_running:
                info_text += f"❌ {nanobot_name}: WSL 分发未运行\n"
                continue
            
            # 获取 WSL 分发的 IP 地址
            wsl_ip = self._wsl_manager.get_distro_ip(config.distro_name)
            if not wsl_ip:
                info_text += f"❌ {nanobot_name}: 无法获取 WSL IP 地址\n"
                continue
            
            valid_bots.append({
                "name": nanobot_name,
                "config": config,
                "wsl_ip": wsl_ip,
                "distro_name": config.distro_name
            })
            
            info_text += f"✅ {nanobot_name}:\n"
            info_text += f"   WSL: {config.distro_name}\n"
            info_text += f"   IP: {wsl_ip}\n"
            info_text += f"   Port: {config.gateway_port}\n\n"
        
        if not valid_bots:
            self.chat_panel.show_error("没有可连接的 Nanobot，请确保 WSL 分发正在运行")
            self.chat_panel.set_connection_status(False)
            return
        
        info_label = QLabel(info_text)
        layout.addWidget(info_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        connect_btn = QPushButton("连接")
        cancel_btn = QPushButton("取消")
        button_layout.addWidget(connect_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        result = {"action": "cancel"}
        
        def on_connect():
            result["action"] = "connect"
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        connect_btn.clicked.connect(on_connect)
        cancel_btn.clicked.connect(on_cancel)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.chat_panel.set_connection_status(False)
            return
        
        # 开始连接每个有效的 bot
        connected_count = 0
        connected_info = []
        
        for bot_info in valid_bots:
            nanobot_name = bot_info["name"]
            config = bot_info["config"]
            wsl_ip = bot_info["wsl_ip"]
            
            # 如果已经连接了，跳过
            if nanobot_name in self._chat_clients:
                logger.info(f"{nanobot_name} 已经连接，跳过")
                connected_count += 1
                connected_info.append(f"{nanobot_name}(已连接)")
                continue
            
            # 使用 WSL 分发的 IP + bot 配置的 gateway_port
            gateway_url = f"ws://{wsl_ip}:{config.gateway_port}/ws"
            logger.info(f"开始连接到 {nanobot_name}: {gateway_url}")
            
            # 使用闭包创建专用的消息回调，绑定 nanobot_name
            def create_message_callback(name):
                def callback(message):
                    self._on_chat_message_received(message, name)
                return callback
            
            chat_client = NanobotChatClient(
                gateway_url,
                on_message=create_message_callback(nanobot_name),
                on_status_changed=self._on_chat_status_changed
            )
            
            if chat_client.connect():
                logger.info(f"✅ {nanobot_name} 连接成功！(ws://{wsl_ip}:{config.gateway_port})")
                self._chat_clients[nanobot_name] = chat_client
                connected_count += 1
                connected_info.append(f"{nanobot_name}({wsl_ip}:{config.gateway_port})")
            else:
                logger.error(f"❌ {nanobot_name} 连接失败！(ws://{wsl_ip}:{config.gateway_port})")
        
        if connected_count > 0:
            logger.info(f"✅ 成功连接 {connected_count} 个 nanobot")
            # 更新每个bot的连接状态
            for bot_info in valid_bots:
                nanobot_name = bot_info["name"]
                if nanobot_name in self._chat_clients:
                    wsl_ip = bot_info["wsl_ip"]
                    config = bot_info["config"]
                    self.chat_panel.set_connection_status(
                        nanobot_name, 
                        True, 
                        f"{wsl_ip}:{config.gateway_port}"
                    )
        else:
            logger.error("❌ 没有成功连接任何 nanobot")
            self.chat_panel.show_error(f"无法连接到 gateways，请检查每个 Bot 的 gateway 是否正在运行")

    def _on_single_nanobot_connect(self, nanobot_name: str):
        """处理单个bot的连接请求"""
        from PyQt6.QtWidgets import QMessageBox
        from loguru import logger
        
        logger.info(f"=== 开始连接单个 Bot: {nanobot_name} ===")
        
        config = self._config_manager.get(nanobot_name)
        if not config:
            logger.error(f"未找到 {nanobot_name} 的配置")
            self.chat_panel.show_error(f"未找到 {nanobot_name} 的配置")
            self.chat_panel.set_connection_status(nanobot_name, False)
            return
        
        distro = self._wsl_manager.get_distro(config.distro_name)
        if not distro or not distro.is_running:
            logger.error(f"{nanobot_name}: WSL 分发未运行")
            self.chat_panel.show_error(f"{config.distro_name} WSL 分发未运行")
            self.chat_panel.set_connection_status(nanobot_name, False)
            return
        
        wsl_ip = self._wsl_manager.get_distro_ip(config.distro_name)
        if not wsl_ip:
            logger.error(f"{nanobot_name}: 无法获取 WSL IP 地址")
            self.chat_panel.show_error(f"无法获取 {config.distro_name} 的 IP 地址")
            self.chat_panel.set_connection_status(nanobot_name, False)
            return
        
        if nanobot_name in self._chat_clients:
            logger.info(f"{nanobot_name} 已经连接，跳过")
            self.chat_panel.set_connection_status(nanobot_name, True, f"{wsl_ip}:{config.gateway_port}")
            return
        
        gateway_url = f"ws://{wsl_ip}:{config.gateway_port}/ws"
        logger.info(f"开始连接到 {nanobot_name}: {gateway_url}")
        
        def create_message_callback(name):
            def callback(message):
                self._on_chat_message_received(message, name)
            return callback
        
        chat_client = NanobotChatClient(
            gateway_url,
            on_message=create_message_callback(nanobot_name),
            on_status_changed=self._on_chat_status_changed
        )
        
        if chat_client.connect():
            logger.info(f"✅ {nanobot_name} 连接成功！({gateway_url})")
            self._chat_clients[nanobot_name] = chat_client
            self.chat_panel.set_connection_status(
                nanobot_name, 
                True, 
                f"{wsl_ip}:{config.gateway_port}"
            )
        else:
            logger.error(f"❌ {nanobot_name} 连接失败！({gateway_url})")
            self.chat_panel.show_error(f"无法连接到 {nanobot_name} 的 gateway")
            self.chat_panel.set_connection_status(nanobot_name, False)
    
    def _on_single_nanobot_disconnect(self, nanobot_name: str):
        """处理单个bot的断开请求"""
        from loguru import logger
        
        logger.info(f"[MainWindow] 断开 {nanobot_name} 连接")
        
        if nanobot_name in self._chat_clients:
            try:
                chat_client = self._chat_clients[nanobot_name]
                chat_client.disconnect()
                del self._chat_clients[nanobot_name]
                logger.info(f"[MainWindow] {nanobot_name} 已断开连接")
                self.chat_panel.set_connection_status(nanobot_name, False)
            except Exception as e:
                logger.error(f"[MainWindow] 断开 {nanobot_name} 连接时出错: {e}")
                self.chat_panel.set_connection_status(nanobot_name, False)
    
    def _on_chat_disconnect(self, bot_name: str = ""):
        from loguru import logger
        
        if bot_name:
            logger.info(f"[MainWindow] 断开 {bot_name} 连接")
            if bot_name in self._chat_clients:
                try:
                    chat_client = self._chat_clients[bot_name]
                    chat_client.disconnect()
                    del self._chat_clients[bot_name]
                    logger.info(f"[MainWindow] {bot_name} 已断开连接")
                    self.chat_panel.set_connection_status(bot_name, False)
                except Exception as e:
                    logger.error(f"[MainWindow] 断开 {bot_name} 连接时出错: {e}")
        else:
            logger.info("[MainWindow] 断开所有连接")
            for nanobot_name, chat_client in list(self._chat_clients.items()):
                try:
                    chat_client.disconnect()
                    logger.info(f"[MainWindow] {nanobot_name} 已断开连接")
                    self.chat_panel.set_connection_status(nanobot_name, False)
                except Exception as e:
                    logger.error(f"[MainWindow] 断开 {nanobot_name} 连接时出错: {e}")
            
            self._chat_clients.clear()

    def _on_chat_clear(self):
        self.chat_panel.clear_messages()

    def _on_chat_message_sent(self, message: str, selected_nanobots: list):
        from loguru import logger
        logger.info(f"[MainWindow] 聊天消息发送: {message[:100]}..., 目标: {selected_nanobots}")
        
        if not self._chat_clients:
            logger.warning("[MainWindow] 没有连接任何 nanobot")
            return
        
        # 向所有已连接且被选中的 nanobot 发送消息
        sent_count = 0
        for nanobot_name in selected_nanobots:
            if nanobot_name in self._chat_clients:
                chat_client = self._chat_clients[nanobot_name]
                if chat_client.is_connected:
                    logger.debug(f"[MainWindow] 向 {nanobot_name} 发送消息")
                    chat_client.send_message(message)
                    sent_count += 1
        
        if sent_count == 0:
            logger.warning("[MainWindow] 没有成功向任何 nanobot 发送消息")

    def _on_chat_message_received(self, message: str, nanobot_name: Optional[str] = None):
        from loguru import logger
        logger.info(f"[MainWindow] 收到聊天消息: {message[:100]}...")
        self.chat_panel.add_message("assistant", message, nanobot_name)

    def _on_chat_status_changed(self, status: ConnectionStatus, bot_name: str = ""):
        # 注意：此方法目前未使用，因为我们直接在连接/断开时更新状态
        # 保留以备将来使用
        pass

    def _on_nav_changed(self, index: int):
        self.content_stack.setCurrentIndex(index)

    def _on_wsl_status_changed(self, data: dict):
        distro_name = data.get("distro_name", "")
        status = data.get("status", "Unknown")
        is_running = data.get("is_running", False)

        self.wsl_status_label.setText(f"WSL ({distro_name}): {status}")

        if is_running:
            self.overview_panel.update_wsl_status(distro_name, True)
        else:
            self.overview_panel.update_wsl_status(distro_name, False)

    def _on_resources_updated(self, data: dict):
        cpu = data.get("cpu_usage", 0.0)
        mem = data.get("memory_usage", 0)
        mem_total = data.get("memory_total", 0)

        mem_mb = mem / (1024 * 1024) if mem else 0
        mem_total_mb = mem_total / (1024 * 1024) if mem_total else 0

        self.resource_label.setText(f"CPU: {cpu:.1f}% | MEM: {mem_mb:.0f}MB / {mem_total_mb:.0f}MB")
        
        # 更新概览面板上的资源显示
        self.overview_panel.update_system_resources(cpu, mem, mem_total)

    def _on_distro_started(self, distro_name: str):
        self.status_bar.showMessage(f"已启动 WSL 分发: {distro_name}", 3000)

    def _on_distro_stopped(self, distro_name: str):
        self.status_bar.showMessage(f"已停止 WSL 分发: {distro_name}", 3000)

    def _on_distro_imported(self, distro_name: str):
        self.config_panel.refresh_distros()
        self.status_bar.showMessage(f"已导入 WSL 分发: {distro_name}", 3000)

    def _on_config_saved(self, config_name: str):
        self.status_bar.showMessage(f"已保存配置: {config_name}", 3000)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def keyPressEvent(self, event):
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtCore import Qt

        modifiers = event.modifiers()
        key = event.key()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_1:
                self.nav_list.setCurrentRow(0)
                return
            elif key == Qt.Key.Key_2:
                self.nav_list.setCurrentRow(1)
                return
            elif key == Qt.Key.Key_3:
                self.nav_list.setCurrentRow(2)
                return
            elif key == Qt.Key.Key_4:
                self.nav_list.setCurrentRow(3)
                return
            elif key == Qt.Key.Key_5:
                self.nav_list.setCurrentRow(4)
                return
            elif key == Qt.Key.Key_6:
                self.nav_list.setCurrentRow(5)
                return
            elif key == Qt.Key.Key_S:
                self._save_current_config()
                return

        if key == Qt.Key.Key_Escape:
            focused = self.focusWidget()
            if focused and hasattr(focused, 'clearFocus'):
                focused.clearFocus()
            else:
                focused = self.focusWidget()
                if focused:
                    focused.parent().setFocus() if focused.parent() else None

        super().keyPressEvent(event)

    def _save_current_config(self):
        current_row = self.content_stack.currentIndex()
        if current_row == 1:
            self.config_panel.save_current_config()

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.hide()
                self.tray_icon.showMessage(
                    "FTK_Claw_Bot",
                    "程序已最小化到系统托盘",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        super().changeEvent(event)

    def closeEvent(self, event):
        self._quit_app()
        event.accept()

    def _quit_app(self):
        for nanobot_name, chat_client in list(self._chat_clients.items()):
            try:
                chat_client.disconnect()
            except Exception:
                pass
        self._chat_clients.clear()

        if self._gateway_manager:
            self._gateway_manager.stop_gateway()

        self._monitor_service.stop()
        self._windows_bridge.stop()
        self._wsl_manager.stop_monitoring()
        self.tray_icon.hide()
        QApplication.quit()

    def _on_nanobot_status_changed(self, data: dict):
        """Handle nanobot status changes from monitor service."""
        instance_name = data.get("instance_name", "")
        status = data.get("status", "unknown")
        is_running = data.get("is_running", False)

        self.nanobot_status_label.setText(f"Nanobot ({instance_name}): {status}")

        if is_running:
            self.overview_panel.update_nanobot_status(instance_name, True)
            self.nanobot_panel.update_nanobot_status(instance_name, True)
            self.log_panel.add_log("INFO", "Nanobot", f"Instance '{instance_name}' started")
        else:
            self.overview_panel.update_nanobot_status(instance_name, False)
            self.nanobot_panel.update_nanobot_status(instance_name, False)
            error = data.get("last_error")
            if error:
                self.log_panel.add_log("ERROR", "Nanobot", f"Instance '{instance_name}' error: {error}")
            else:
                self.log_panel.add_log("INFO", "Nanobot", f"Instance '{instance_name}' stopped")
                
    def _on_nanobot_instance_started(self, instance_name: str):
        self.status_bar.showMessage(f"Nanobot '{instance_name}' 已启动", 3000)
        
    def _on_nanobot_instance_stopped(self, instance_name: str):
        self.status_bar.showMessage(f"Nanobot '{instance_name}' 已停止", 3000)
        
    def _on_nanobot_instance_restarted(self, instance_name: str):
        self.status_bar.showMessage(f"Nanobot '{instance_name}' 已重启", 3000)

    def _on_nanobot_log(self, instance_name: str, log_type: str, message: str):
        """Handle nanobot log messages."""
        level = "INFO" if log_type == "stdout" else "DEBUG"
        self.log_panel.add_log(level, f"Nanobot:{instance_name}", message)
