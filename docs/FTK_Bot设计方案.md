# FTK_Bot 设计方案

## 1. 项目概述

### 1.1 项目背景

FTK_Bot 是一个运行在 Windows 平台上的 Python 桌面应用程序，旨在为 WSL2 环境中的 Nanobot AI 助手提供完整的管理和控制能力。通过 FTK_Bot，用户可以方便地管理 WSL2 分发、配置 Nanobot 参数、管理技能库，并实现 Nanobot 对 Windows 应用和 GUI 的控制。

### 1.2 项目目标

- 提供 WSL2 分发的运行管理和监控功能
- 实现 Nanobot 的参数配置和技能管理
- 支持 Nanobot 控制 Windows 应用和 GUI
- 提供友好的图形用户界面

### 1.3 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| GUI框架 | PyQt6 / PySide6 | 现代化跨平台GUI框架 |
| WSL管理 | wsl.exe / pywsl | Windows Subsystem for Linux 管理接口 |
| 进程管理 | subprocess / psutil | 进程监控和管理 |
| IPC通信 | Named Pipe / Socket | Windows-WSL2 进程间通信 |
| 配置存储 | JSON / SQLite | 配置和状态持久化 |
| Windows自动化 | pyautogui / pywinauto | Windows GUI 自动化控制 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FTK_Bot (Windows)                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   GUI层     │  │   业务层    │  │   服务层    │  │   数据层    │ │
│  │  (PyQt6)    │  │ (Core)      │  │ (Services)  │  │ (Storage)   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │        │
│  ┌──────┴────────────────┴────────────────┴────────────────┴──────┐ │
│  │                    IPC Bridge (Named Pipe/Socket)              │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WSL2 Environment                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  Nanobot    │  │   Skills    │  │  Workspace  │                  │
│  │   Agent     │  │   Library   │  │   (/mnt)    │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分

```
FTK_Bot/
├── ftk_bot/
│   ├── __init__.py
│   ├── main.py                    # 应用入口
│   ├── core/                      # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── wsl_manager.py         # WSL2 管理器
│   │   ├── nanobot_controller.py  # Nanobot 控制器
│   │   ├── skill_manager.py       # 技能管理器
│   │   └── config_manager.py      # 配置管理器
│   ├── services/                  # 服务层
│   │   ├── __init__.py
│   │   ├── ipc_server.py          # IPC 服务端
│   │   ├── windows_bridge.py      # Windows 自动化桥接
│   │   └── monitor_service.py     # 监控服务
│   ├── gui/                       # GUI 界面
│   │   ├── __init__.py
│   │   ├── main_window.py         # 主窗口
│   │   ├── widgets/               # 自定义控件
│   │   │   ├── __init__.py
│   │   │   ├── wsl_panel.py       # WSL 管理面板
│   │   │   ├── config_panel.py    # 配置面板
│   │   │   ├── skill_panel.py     # 技能管理面板
│   │   │   └── log_panel.py       # 日志面板
│   │   ├── dialogs/               # 对话框
│   │   │   ├── __init__.py
│   │   │   ├── skill_editor.py    # 技能编辑器
│   │   │   └── settings_dialog.py # 设置对话框
│   │   └── resources/             # 资源文件
│   │       ├── styles.qss         # 样式表
│   │       └── icons/             # 图标资源
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── wsl_distro.py          # WSL 分发模型
│   │   ├── nanobot_config.py      # Nanobot 配置模型
│   │   └── skill.py               # 技能模型
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── logger.py              # 日志工具
│   │   ├── path_utils.py          # 路径工具
│   │   └── validators.py          # 验证器
│   └── bridge/                    # WSL2 桥接模块
│       ├── __init__.py
│       ├── bridge_agent.py        # 桥接代理（部署到WSL2）
│       └── protocol.py            # 通信协议
├── tests/                         # 测试目录
├── docs/                          # 文档目录
├── requirements.txt               # 依赖列表
├── setup.py                       # 安装配置
└── README.md                      # 项目说明
```

---

## 3. 功能模块详细设计

### 3.1 WSL2 管理模块

#### 3.1.1 功能描述

管理和监控 WSL2 分发版本的运行状态，提供启动、停止、重启等操作。

#### 3.1.2 核心功能

| 功能 | 描述 | 实现方式 |
|------|------|----------|
| 分发列表 | 获取所有 WSL2 分发版本 | `wsl.exe --list --verbose` |
| 启动分发 | 启动指定的 WSL2 分发 | `wsl.exe -d <distro>` |
| 停止分发 | 停止指定的 WSL2 分发 | `wsl.exe --terminate <distro>` |
| 关闭所有 | 关闭所有 WSL2 实例 | `wsl.exe --shutdown` |
| 状态监控 | 实时监控分发运行状态 | 定时轮询 + 事件通知 |
| 资源监控 | CPU/内存使用监控 | 通过 WSL2 内部命令获取 |

#### 3.1.3 类设计

```python
class WSLManager:
    def __init__(self):
        self._distros: Dict[str, WSLDistro] = {}
        self._monitor_thread: Optional[Thread] = None
        self._callbacks: List[Callable] = []
    
    def list_distros(self) -> List[WSLDistro]:
        """获取所有WSL分发列表"""
        pass
    
    def start_distro(self, distro_name: str) -> bool:
        """启动指定分发"""
        pass
    
    def stop_distro(self, distro_name: str) -> bool:
        """停止指定分发"""
        pass
    
    def shutdown_all(self) -> bool:
        """关闭所有WSL实例"""
        pass
    
    def get_distro_status(self, distro_name: str) -> DistroStatus:
        """获取分发状态"""
        pass
    
    def execute_command(self, distro_name: str, command: str) -> CommandResult:
        """在指定分发中执行命令"""
        pass
    
    def register_callback(self, callback: Callable):
        """注册状态变化回调"""
        pass
```

#### 3.1.4 数据模型

```python
from dataclasses import dataclass
from enum import Enum

class DistroStatus(Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    INSTALLING = "Installing"
    ERROR = "Error"

@dataclass
class WSLDistro:
    name: str
    version: int  # 1 or 2
    status: DistroStatus
    is_default: bool
    wsl_path: str  # WSL内路径前缀
    
    @property
    def is_running(self) -> bool:
        return self.status == DistroStatus.RUNNING
```

### 3.2 Nanobot 控制模块

#### 3.2.1 功能描述

控制 WSL2 中的 Nanobot 实例，包括启动、停止、状态监控和命令执行。

#### 3.2.2 核心功能

| 功能 | 描述 | 实现方式 |
|------|------|----------|
| 启动 Nanobot | 在指定 WSL2 分发中启动 Nanobot | 通过 WSL 执行 `nanobot` 命令 |
| 停止 Nanobot | 停止运行中的 Nanobot 实例 | 发送终止信号 |
| 状态监控 | 监控 Nanobot 运行状态 | 进程检测 + 日志解析 |
| 命令发送 | 向 Nanobot 发送命令 | IPC 通信 |
| 日志收集 | 收集 Nanobot 输出日志 | 文件监控 + 流重定向 |

#### 3.2.3 类设计

```python
class NanobotController:
    def __init__(self, wsl_manager: WSLManager, config: NanobotConfig):
        self._wsl_manager = wsl_manager
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._ipc_client: Optional[IPCClient] = None
    
    def start(self) -> bool:
        """启动Nanobot实例"""
        pass
    
    def stop(self) -> bool:
        """停止Nanobot实例"""
        pass
    
    def restart(self) -> bool:
        """重启Nanobot实例"""
        pass
    
    def get_status(self) -> NanobotStatus:
        """获取运行状态"""
        pass
    
    def send_message(self, message: str) -> str:
        """发送消息到Nanobot"""
        pass
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """获取日志"""
        pass
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        pass
```

### 3.3 Windows 桥接模块

#### 3.3.1 功能描述

实现 Nanobot 对 Windows 应用和 GUI 的控制能力，通过 IPC 机制桥接 WSL2 和 Windows。

#### 3.3.2 架构设计

```
┌──────────────────┐         Named Pipe         ┌──────────────────┐
│  WSL2 Nanobot    │ ◄─────────────────────────► │  FTK_Bot Bridge  │
│  (Bridge Agent)  │         / Socket           │    (Windows)     │
└──────────────────┘                            └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │ Windows Automation│
                                                │  (pyautogui/     │
                                                │   pywinauto)     │
                                                └──────────────────┘
```

#### 3.3.3 支持的操作

| 操作类型 | 具体操作 | 说明 |
|----------|----------|------|
| 窗口管理 | 打开/关闭/最小化/最大化窗口 | 窗口基础操作 |
| 鼠标控制 | 移动/点击/拖拽/滚动 | 模拟鼠标操作 |
| 键盘控制 | 输入文本/快捷键/特殊键 | 模拟键盘操作 |
| 屏幕操作 | 截图/屏幕识别 | 获取屏幕信息 |
| 应用启动 | 启动Windows应用 | 打开指定程序 |
| 文件操作 | 打开/编辑/保存文件 | 文件系统操作 |
| 剪贴板 | 读取/写入剪贴板 | 剪贴板操作 |

#### 3.3.4 类设计

```python
class WindowsBridge:
    def __init__(self):
        self._ipc_server: Optional[IPCServer] = None
        self._automation: WindowsAutomation = None
    
    def start_server(self, port: int = 9527):
        """启动IPC服务端"""
        pass
    
    def stop_server(self):
        """停止IPC服务端"""
        pass
    
    def handle_request(self, request: BridgeRequest) -> BridgeResponse:
        """处理来自WSL2的请求"""
        pass

class WindowsAutomation:
    def mouse_click(self, x: int, y: int, button: str = "left"):
        """鼠标点击"""
        pass
    
    def mouse_move(self, x: int, y: int):
        """鼠标移动"""
        pass
    
    def keyboard_type(self, text: str):
        """键盘输入"""
        pass
    
    def keyboard_hotkey(self, *keys: str):
        """快捷键"""
        pass
    
    def screenshot(self, region: Optional[Tuple] = None) -> bytes:
        """截图"""
        pass
    
    def find_window(self, title: str) -> Optional[WindowHandle]:
        """查找窗口"""
        pass
    
    def launch_app(self, app_path: str, args: List[str] = None):
        """启动应用"""
        pass
    
    def get_clipboard(self) -> str:
        """获取剪贴板内容"""
        pass
    
    def set_clipboard(self, text: str):
        """设置剪贴板内容"""
        pass
```

#### 3.3.5 通信协议

```python
from dataclasses import dataclass
from enum import Enum
import json

class CommandType(Enum):
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_HOTKEY = "keyboard_hotkey"
    SCREENSHOT = "screenshot"
    FIND_WINDOW = "find_window"
    LAUNCH_APP = "launch_app"
    GET_CLIPBOARD = "get_clipboard"
    SET_CLIPBOARD = "set_clipboard"

@dataclass
class BridgeRequest:
    command: CommandType
    params: dict
    request_id: str
    
    def to_json(self) -> str:
        return json.dumps({
            "command": self.command.value,
            "params": self.params,
            "request_id": self.request_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BridgeRequest':
        data = json.loads(json_str)
        return cls(
            command=CommandType(data["command"]),
            params=data["params"],
            request_id=data["request_id"]
        )

@dataclass
class BridgeResponse:
    success: bool
    result: any
    error: Optional[str]
    request_id: str
    
    def to_json(self) -> str:
        return json.dumps({
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "request_id": self.request_id
        })
```

### 3.4 配置管理模块

#### 3.4.1 功能描述

管理 Nanobot 的配置参数，包括 CLI 参数、工作空间设置和技能配置。

#### 3.4.2 Nanobot CLI 参数配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--workspace` | str | `~/.nanobot` | 工作目录路径 |
| `--config` | str | `~/.nanobot/config.json` | 配置文件路径 |
| `--model` | str | `anthropic/claude-sonnet-4-20250529` | LLM 模型 |
| `--provider` | str | `openrouter` | LLM 提供商 |
| `--api-key` | str | - | API 密钥 |
| `--skills-dir` | str | `~/.nanobot/skills` | 技能目录 |
| `--log-level` | str | `INFO` | 日志级别 |
| `--no-memory` | bool | False | 禁用记忆功能 |
| `--no-web-search` | bool | False | 禁用网络搜索 |

#### 3.4.3 工作空间配置

支持将工作空间配置到 WSL 的 `/mnt` 目录下，实现 Windows 和 WSL2 的数据共享：

```
Windows路径: D:\nanobot_workspace
WSL路径:     /mnt/d/nanobot_workspace
```

#### 3.4.4 类设计

```python
@dataclass
class NanobotConfig:
    distro_name: str
    workspace: str
    config_path: str
    provider: str
    model: str
    api_key: str
    skills_dir: str
    log_level: str
    enable_memory: bool
    enable_web_search: bool
    brave_api_key: Optional[str]
    
    def to_nanobot_args(self) -> List[str]:
        """转换为nanobot命令行参数"""
        args = []
        if self.workspace:
            args.extend(["--workspace", self.workspace])
        if self.config_path:
            args.extend(["--config", self.config_path])
        if self.model:
            args.extend(["--model", self.model])
        if self.provider:
            args.extend(["--provider", self.provider])
        if self.log_level:
            args.extend(["--log-level", self.log_level])
        if not self.enable_memory:
            args.append("--no-memory")
        if not self.enable_web_search:
            args.append("--no-web-search")
        return args
    
    def to_config_json(self) -> dict:
        """生成nanobot配置文件内容"""
        return {
            "providers": {
                self.provider: {
                    "api_key": self.api_key,
                    "model": self.model
                }
            },
            "web_search": {
                "enabled": self.enable_web_search,
                "api_key": self.brave_api_key
            } if self.enable_web_search else None
        }

class ConfigManager:
    def __init__(self, config_path: str):
        self._config_path = config_path
        self._configs: Dict[str, NanobotConfig] = {}
    
    def load(self) -> Dict[str, NanobotConfig]:
        """加载所有配置"""
        pass
    
    def save(self, config: NanobotConfig):
        """保存配置"""
        pass
    
    def delete(self, config_name: str):
        """删除配置"""
        pass
    
    def get_default(self) -> NanobotConfig:
        """获取默认配置"""
        pass
    
    def set_default(self, config_name: str):
        """设置默认配置"""
        pass
    
    def convert_windows_to_wsl_path(self, windows_path: str) -> str:
        """将Windows路径转换为WSL路径"""
        pass
    
    def convert_wsl_to_windows_path(self, wsl_path: str) -> str:
        """将WSL路径转换为Windows路径"""
        pass
```

### 3.5 技能管理模块

#### 3.5.1 功能描述

管理 Nanobot 的技能库，支持技能的增删改查操作。

#### 3.5.2 技能文件格式

技能采用 Markdown 格式存储：

```markdown
# 技能名称

## 描述
技能的详细描述，说明该技能的用途和使用场景。

## 使用说明
1. 步骤一
2. 步骤二
3. 步骤三

## 示例
用户: 帮我执行某个任务
助手: [执行技能中的步骤]

## 依赖
- 依赖的其他技能或工具
- 需要的API或环境变量
```

#### 3.5.3 核心功能

| 功能 | 描述 | 实现方式 |
|------|------|----------|
| 技能列表 | 显示所有可用技能 | 扫描技能目录 |
| 创建技能 | 创建新的技能文件 | Markdown 编辑器 |
| 编辑技能 | 修改现有技能 | Markdown 编辑器 |
| 删除技能 | 删除技能文件 | 文件删除操作 |
| 导入技能 | 从外部导入技能 | 文件复制 |
| 导出技能 | 导出技能到外部 | 文件导出 |
| 技能预览 | 预览技能内容 | Markdown 渲染 |
| 技能验证 | 验证技能格式 | 格式检查 |

#### 3.5.4 类设计

```python
@dataclass
class Skill:
    name: str
    file_path: str
    description: str
    content: str
    dependencies: List[str]
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_markdown(cls, file_path: str) -> 'Skill':
        """从Markdown文件加载技能"""
        pass
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        pass

class SkillManager:
    def __init__(self, skills_dir: str):
        self._skills_dir = skills_dir
        self._skills: Dict[str, Skill] = {}
    
    def list_skills(self) -> List[Skill]:
        """获取所有技能列表"""
        pass
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """获取指定技能"""
        pass
    
    def create_skill(self, name: str, content: str) -> Skill:
        """创建新技能"""
        pass
    
    def update_skill(self, name: str, content: str) -> Skill:
        """更新技能"""
        pass
    
    def delete_skill(self, name: str) -> bool:
        """删除技能"""
        pass
    
    def import_skill(self, file_path: str) -> Skill:
        """导入技能"""
        pass
    
    def export_skill(self, name: str, export_path: str) -> bool:
        """导出技能"""
        pass
    
    def validate_skill(self, content: str) -> Tuple[bool, List[str]]:
        """验证技能格式"""
        pass
    
    def search_skills(self, keyword: str) -> List[Skill]:
        """搜索技能"""
        pass
```

---

## 4. GUI 界面设计

### 4.1 主界面布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  FTK_Bot                                                    [─][□][×] │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────┬──────────────────────────────────────────────────┐  │
│  │           │                                                  │  │
│  │  导航栏   │                   主内容区                       │  │
│  │           │                                                  │  │
│  │  ◉ 概览   │  ┌────────────────────────────────────────────┐  │  │
│  │           │  │                                            │  │  │
│  │  ○ WSL    │  │                                            │  │  │
│  │  管理     │  │          根据选中导航项显示                 │  │  │
│  │           │  │              对应的功能面板                 │  │  │
│  │  ○ 配置   │  │                                            │  │  │
│  │  管理     │  │                                            │  │  │
│  │           │  │                                            │  │  │
│  │  ○ 技能   │  │                                            │  │  │
│  │  管理     │  │                                            │  │  │
│  │           │  └────────────────────────────────────────────┘  │  │
│  │  ○ 日志   │                                                  │  │
│  │  查看     │                                                  │  │
│  │           │                                                  │  │
│  └───────────┴──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  状态栏: WSL状态: Running | Nanobot: Running | CPU: 15% | MEM: 256MB│
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 各功能面板设计

#### 4.2.1 概览面板

```
┌─────────────────────────────────────────────────────────────────────┐
│                           系统概览                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │   WSL 状态          │  │   Nanobot 状态      │                   │
│  │   ┌───────────┐     │  │   ┌───────────┐     │                   │
│  │   │  ● 运行中  │     │  │   │  ● 运行中  │     │                   │
│  │   └───────────┘     │  │   └───────────┘     │                   │
│  │   Ubuntu-22.04      │  │   运行时间: 2h 15m  │                   │
│  │   WSL2 | 默认分发   │  │   消息数: 156       │                   │
│  │                     │  │                     │                   │
│  │   [启动] [停止]      │  │   [启动] [停止]      │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      快速操作                                  │  │
│  │  [发送消息]  [查看日志]  [打开工作空间]  [编辑配置]            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      最近活动                                  │  │
│  │  • 10:30: 收到用户消息: "帮我分析一下数据"                    │  │
│  │  • 10:28: 执行技能: data_analysis                             │  │
│  │  • 10:25: 启动 Nanobot                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.2 WSL 管理面板

```
┌─────────────────────────────────────────────────────────────────────┐
│  WSL 分发管理                                    [刷新] [关闭所有]  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 名称          │ 版本 │ 状态   │ 默认 │ 操作                    │  │
│  ├───────────────┼──────┼────────┼──────┼─────────────────────────┤  │
│  │ Ubuntu-22.04  │  2   │ ● 运行 │  ✓   │ [停止][终端][设置]      │  │
│  │ Debian        │  2   │ ○ 停止 │      │ [启动][终端][设置]      │  │
│  │ kali-linux    │  2   │ ○ 停止 │      │ [启动][终端][设置]      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 分发详情: Ubuntu-22.04                                         │  │
│  │ ─────────────────────────────────────────────────────────────  │  │
│  │ CPU 使用: ████████░░ 78%                                       │  │
│  │ 内存使用: █████░░░░░ 512MB / 4GB                               │  │
│  │ 磁盘使用: ███░░░░░░░ 15GB / 50GB                               │  │
│  │ 运行时间: 2小时 15分钟                                         │  │
│  │ IP 地址: 172.18.0.2                                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.3 配置管理面板

```
┌─────────────────────────────────────────────────────────────────────┐
│  Nanobot 配置                                         [新建] [导入]  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┬────────────────────────────────────────────────┤
│  │ 配置列表       │ 配置详情                                      │  │
│  │                │                                                │  │
│  │ ● 默认配置     │ 名称: [默认配置        ]                      │  │
│  │   production   │                                                │  │
│  │   development  │ WSL 分发: [Ubuntu-22.04 ▼]                     │  │
│  │   testing      │                                                │  │
│  │                │ ─── 工作空间 ───                              │  │
│  │                │ Windows: [D:\nanobot_workspace    ] [浏览]     │  │
│  │                │ WSL:     [/mnt/d/nanobot_workspace]            │  │
│  │                │ ☑ 同步到 /mnt 目录                            │  │
│  │                │                                                │  │
│  │                │ ─── LLM 配置 ───                              │  │
│  │                │ 提供商: [OpenRouter ▼]                         │  │
│  │                │ 模型:   [claude-sonnet-4 ▼]                    │  │
│  │                │ API Key: [•••••••••••••] [显示]                │  │
│  │                │                                                │  │
│  │                │ ─── 功能开关 ───                              │  │
│  │                │ ☑ 启用记忆功能                                │  │
│  │                │ ☑ 启用网络搜索                                │  │
│  │                │ Brave API Key: [••••••••••]                    │  │
│  │                │                                                │  │
│  │                │              [保存] [重置] [删除]              │  │
│  └────────────────┴────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.4 技能管理面板

```
┌─────────────────────────────────────────────────────────────────────┐
│  技能管理                              [新建] [导入] [刷新]         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┬────────────────────────────────────────────────┤
│  │ 技能列表       │ 技能详情 / 编辑                               │  │
│  │                │                                                │  │
│  │ 🔍 搜索...     │ ┌──────────────────────────────────────────┐  │  │
│  │                │ │ # data_analysis                          │  │  │
│  │ ● data_analysis│ │                                          │  │  │
│  │   web_scraper  │ │ ## 描述                                  │  │  │
│  │   file_manager │ │ 数据分析技能，用于处理和分析各类数据...   │  │  │
│  │   email_helper │ │                                          │  │  │
│  │   code_review  │ │ ## 使用说明                              │  │  │
│  │                │ │ 1. 首先确认数据格式                      │  │  │
│  │                │ │ 2. 选择合适的分析方法                    │  │  │
│  │                │ │ 3. 生成分析报告                          │  │  │
│  │                │ │ ...                                      │  │  │
│  │                │ └──────────────────────────────────────────┘  │  │
│  │                │                                                │  │
│  │                │ ─── 元信息 ───                                │  │
│  │                │ 创建时间: 2024-01-15 10:30                    │  │
│  │                │ 更新时间: 2024-01-20 14:22                    │  │
│  │                │ 依赖: pandas, numpy                           │  │
│  │                │                                                │  │
│  │                │        [编辑] [保存] [导出] [删除]            │  │
│  └────────────────┴────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2.5 日志查看面板

```
┌─────────────────────────────────────────────────────────────────────┐
│  日志查看                              [清空] [导出] [实时刷新: ✓]  │
├─────────────────────────────────────────────────────────────────────┤
│  日志级别: [全部 ▼]  来源: [全部 ▼]  时间范围: [最近1小时 ▼]       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ [INFO]  2024-01-20 14:30:15  [Nanobot] 收到用户消息          │  │
│  │ [INFO]  2024-01-20 14:30:16  [Nanobot] 正在处理请求...        │  │
│  │ [DEBUG] 2024-01-20 14:30:17  [Nanobot] 调用工具: read_file    │  │
│  │ [INFO]  2024-01-20 14:30:18  [Nanobot] 读取文件: data.csv     │  │
│  │ [WARN]  2024-01-20 14:30:20  [Bridge] 连接重试中...           │  │
│  │ [INFO]  2024-01-20 14:30:22  [Bridge] 连接成功                │  │
│  │ [ERROR] 2024-01-20 14:30:25  [Nanobot] 执行失败: 权限不足     │  │
│  │ [INFO]  2024-01-20 14:30:30  [Nanobot] 任务完成               │  │
│  │ ...                                                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 数据存储设计

### 5.1 配置文件结构

```
%APPDATA%/FTK_Bot/
├── config.json              # 应用主配置
├── nanobot_configs/         # Nanobot 配置目录
│   ├── default.json
│   ├── production.json
│   └── development.json
├── skills/                  # 技能库（可同步到WSL）
│   ├── data_analysis.md
│   ├── web_scraper.md
│   └── ...
└── logs/                    # 日志目录
    ├── ftk_bot.log
    └── nanobot/
        ├── 2024-01-20.log
        └── ...
```

### 5.2 主配置文件格式

```json
{
    "version": "1.0.0",
    "default_distro": "Ubuntu-22.04",
    "default_config": "default",
    "bridge": {
        "enabled": true,
        "port": 9527,
        "host": "0.0.0.0"
    },
    "workspace": {
        "windows_path": "D:\\nanobot_workspace",
        "sync_to_mnt": true
    },
    "ui": {
        "theme": "dark",
        "language": "zh_CN",
        "auto_start": false,
        "minimize_to_tray": true
    },
    "monitor": {
        "refresh_interval": 5000,
        "log_max_lines": 1000
    }
}
```

### 5.3 Nanobot 配置文件格式

```json
{
    "name": "default",
    "distro": "Ubuntu-22.04",
    "workspace": {
        "windows": "D:\\nanobot_workspace",
        "wsl": "/mnt/d/nanobot_workspace"
    },
    "nanobot": {
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4-20250529",
        "api_key": "${OPENROUTER_API_KEY}",
        "log_level": "INFO",
        "enable_memory": true,
        "enable_web_search": true,
        "brave_api_key": "${BRAVE_API_KEY}"
    },
    "skills_dir": "/mnt/d/nanobot_workspace/skills"
}
```

---

## 6. IPC 通信设计

### 6.1 通信架构

FTK_Bot 与 WSL2 中的 Nanobot 通过以下方式通信：

1. **Named Pipe（命名管道）**
   - Windows 端创建命名管道 `\\.\pipe\ftk_bot_bridge`
   - WSL2 端通过 `/mnt/pipe/ftk_bot_bridge` 或 Socket 连接

2. **TCP Socket**
   - 备选方案，通过 localhost 端口通信
   - 需要配置 WSL2 端口转发

### 6.2 消息流程

```
┌──────────────┐     1. 请求      ┌──────────────┐
│   Nanobot    │ ───────────────► │   FTK_Bot    │
│  (WSL2)      │                  │  (Windows)   │
│              │ ◄─────────────── │              │
└──────────────┘     2. 响应      └──────────────┘
                       │
                       ▼
              ┌──────────────┐
              │   Windows    │
              │   自动化操作  │
              └──────────────┘
```

### 6.3 消息格式

```json
{
    "version": "1.0",
    "type": "request|response|event",
    "id": "uuid",
    "timestamp": "2024-01-20T14:30:00Z",
    "payload": {
        "action": "mouse_click",
        "params": {
            "x": 100,
            "y": 200,
            "button": "left"
        }
    }
}
```

---

## 7. 安全设计

### 7.1 安全考虑

| 安全项 | 措施 |
|--------|------|
| API密钥存储 | 使用 Windows Credential Manager 或加密存储 |
| IPC通信 | 仅允许本地连接，验证客户端身份 |
| 命令执行 | 白名单机制，限制可执行的命令 |
| 文件访问 | 限制可访问的目录范围 |
| 日志脱敏 | 不记录敏感信息（API密钥等） |

### 7.2 权限控制

```python
class SecurityManager:
    ALLOWED_COMMANDS = [
        "mouse_click", "mouse_move", "keyboard_type",
        "screenshot", "launch_app", "get_clipboard"
    ]
    
    RESTRICTED_PATHS = [
        "/etc", "/root", "/home",
        "C:\\Windows\\System32",
        "C:\\Users\\*\\AppData\\Local\\*"
    ]
    
    def validate_command(self, command: str, params: dict) -> bool:
        """验证命令是否允许执行"""
        pass
    
    def validate_path(self, path: str) -> bool:
        """验证路径是否允许访问"""
        pass
```

---

## 8. 部署与安装

### 8.1 系统要求

- Windows 10 2004+ 或 Windows 11
- WSL2 已安装并配置
- Python 3.10+
- 至少 4GB 可用内存

### 8.2 安装方式

**方式一：pip 安装**
```bash
pip install ftk-bot
```

**方式二：源码安装**
```bash
git clone https://github.com/your-org/FTK_Bot.git
cd FTK_Bot
pip install -e .
```

**方式三：打包安装**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed ftk_bot/main.py
```

### 8.3 首次运行配置

1. 检测 WSL2 环境
2. 选择默认 WSL 分发
3. 配置 Nanobot 工作空间
4. 设置 LLM 提供商和 API 密钥
5. 安装 WSL2 桥接代理

---

## 9. 开发计划

### 9.1 版本规划

| 版本 | 功能 | 预计时间 |
|------|------|----------|
| v0.1.0 | 基础框架、WSL管理 | 第1-2周 |
| v0.2.0 | Nanobot控制、配置管理 | 第3-4周 |
| v0.3.0 | 技能管理、日志查看 | 第5-6周 |
| v0.4.0 | Windows桥接功能 | 第7-8周 |
| v1.0.0 | 完整功能、文档、测试 | 第9-10周 |

### 9.2 依赖列表

```
# requirements.txt
PyQt6>=6.5.0
psutil>=5.9.0
pyautogui>=0.9.54
pywinauto>=0.6.8
Pillow>=10.0.0
cryptography>=41.0.0
pywin32>=306
watchdog>=3.0.0
```

---

## 10. 附录

### 10.1 Nanobot CLI 完整参数

| 参数 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--workspace` | `-w` | str | `~/.nanobot` | 工作目录 |
| `--config` | `-c` | str | `~/.nanobot/config.json` | 配置文件路径 |
| `--model` | `-m` | str | - | LLM 模型名称 |
| `--provider` | `-p` | str | `openrouter` | LLM 提供商 |
| `--log-level` | `-l` | str | `INFO` | 日志级别 |
| `--no-memory` | | flag | False | 禁用记忆 |
| `--no-web-search` | | flag | False | 禁用网络搜索 |
| `--version` | `-v` | flag | False | 显示版本 |
| `--help` | `-h` | flag | False | 显示帮助 |

### 10.2 WSL 常用命令参考

```bash
# 列出所有分发
wsl --list --verbose

# 启动指定分发
wsl -d Ubuntu-22.04

# 在指定分发中执行命令
wsl -d Ubuntu-22.04 -- command

# 停止指定分发
wsl --terminate Ubuntu-22.04

# 关闭所有WSL
wsl --shutdown

# 导出分发
wsl --export Ubuntu-22.04 ubuntu.tar

# 导入分发
wsl --import Ubuntu-Custom D:\WSL ubuntu.tar
```

### 10.3 技能模板

```markdown
# {技能名称}

## 描述
{技能的详细描述}

## 使用说明
1. {步骤一}
2. {步骤二}
3. {步骤三}

## 示例
用户: {示例用户输入}
助手: {示例助手响应}

## 依赖
- {依赖项列表}

## 注意事项
- {注意事项}
```

---

## 11. 总结

FTK_Bot 是一个功能完整的 Windows 桌面应用，为 WSL2 环境中的 Nanobot AI 助手提供了全面的管理和控制能力。通过模块化的设计，FTK_Bot 实现了：

1. **WSL2 管理**：完整的分发版本管理、状态监控和资源监控
2. **Nanobot 控制**：启动、停止、配置和监控 Nanobot 实例
3. **Windows 桥接**：让 Nanobot 能够控制 Windows 应用和 GUI
4. **配置管理**：灵活的配置系统，支持多配置切换
5. **技能管理**：完整的技能库 CRUD 操作

该设计方案为后续开发提供了清晰的架构指导和实现细节。
