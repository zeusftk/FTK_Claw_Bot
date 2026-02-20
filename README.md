# FTK_Claw_Bot - 抓虾机器人

FTK_Claw_Bot - Windows 平台的虾群控制工具，openclaw 平替方案。专注 WSL2 环境下 bot 管理与控制，支持单机多 bot 实例并行运行、bot 群聊。提供完整 Windows 系统操作桥接（鼠标/键盘/截图/窗口/剪贴板），现代化 PyQt6 图形界面，插件系统支持无限扩展，WSL2 桥接代理实现跨系统协作。

## ✨ 功能特性

### 🔧 核心功能

| 功能模块 | 描述 |
|---------|------|
| **WSL2 管理** | 管理 WSL2 分发版本（启动/停止/导入/移除/导出），实时资源监控（CPU/内存/磁盘），IP 地址获取，终端打开 |
| **Bot 控制** | 启动、停止、重启 bot 实例，支持单机多 bot 并行运行，实时状态监控，日志查看与过滤 |
| **配置管理** | 可视化配置编辑，多配置管理，默认配置设置，工作空间同步，跨平台路径转换 |
| **技能管理** | 创建/编辑/删除技能，导入/导出技能包，实时搜索，Markdown 编辑器集成 |
| **Windows 桥接** | 鼠标控制、键盘模拟、屏幕截图、窗口查找与控制、应用启动、剪贴板同步 |
| **聊天面板** | WebSocket 连接 Clawbot Gateway，多 bot 群聊支持，消息转发 |

### 🎨 界面特性

- **现代化 GUI**: 响应式设计，深色主题，系统托盘集成
- **多面板布局**: 概览、配置管理、命令执行、聊天、桥接、日志查看
- **实时监控**: WSL 资源监控，Bot 状态监控，系统托盘通知
- **键盘快捷键**: 快速导航和操作

### 🔌 扩展功能

- **插件系统**: 模块化插件架构，动态加载，生命周期管理，配置持久化
- **WSL2 桥接代理**: Socket 通信，请求转发，跨系统协作
- **事件总线**: 组件间解耦通信，支持订阅/发布模式

## 📋 系统要求

| 要求 | 说明 |
|------|------|
| 操作系统 | Windows 10 2004+ 或 Windows 11 |
| WSL | WSL2 已安装并配置 |
| Python | Python 3.10+ |
| 内存 | 至少 4GB 可用内存 |

## 🚀 安装

### 方式一：源码安装

```bash
# 克隆仓库
git clone https://github.com/zeusftk/FTK_Claw_Bot.git
cd FTK_Claw_Bot

# 安装依赖
pip install -e .
```

### 方式二：使用 requirements.txt

```bash
git clone https://github.com/zeusftk/FTK_Claw_Bot.git
cd FTK_Claw_Bot
pip install -r requirements.txt
```

## 🔧 初始化 WSL 分发

使用 `init_wsl` 目录中的脚本可快速配置 WSL 分发：

```bash
cd init_wsl
make_nanobot_distro.bat
```

详细说明请参阅 [init_wsl/README.md](init_wsl/README.md)。

## 🏃 运行

### 命令行启动

```bash
ftkclawbot
```

### 模块方式启动

```bash
python -m ftk_claw_bot.main
```

## 📁 项目结构

```
FTK_Claw_Bot/
├── ftk_claw_bot/
│   ├── bridge/               # WSL2 桥接协议
│   │   ├── __init__.py
│   │   └── protocol.py
│   ├── core/                 # 核心业务逻辑
│   │   ├── bridge_manager.py           # 桥接管理器
│   │   ├── config_manager.py           # 配置管理器
│   │   ├── config_sync_manager.py      # 配置同步管理器
│   │   ├── multi_nanobot_gateway_manager.py  # 多Bot网关管理
│   │   ├── nanobot_controller.py       # Bot控制器
│   │   ├── nanobot_distro_configurator.py    # 分发配置器
│   │   ├── nanobot_gateway_manager.py  # 网关管理器
│   │   ├── port_manager.py             # 端口管理器
│   │   ├── skill_manager.py            # 技能管理器
│   │   └── wsl_manager.py              # WSL管理器
│   ├── gui/                  # GUI 界面
│   │   ├── dialogs/          # 对话框组件
│   │   │   ├── create_distro_wizard.py # 创建分发向导
│   │   │   ├── message_dialog.py       # 消息对话框
│   │   │   ├── settings_dialog.py      # 设置对话框
│   │   │   ├── skill_editor.py         # 技能编辑器
│   │   │   └── waiting_dialog.py       # 等待对话框
│   │   ├── mixins/           # 混入类
│   │   ├── resources/        # 资源文件
│   │   ├── widgets/          # 控件
│   │   │   ├── channel_config_dialog.py # 频道配置
│   │   │   ├── chat_panel.py           # 聊天面板
│   │   │   ├── command_panel.py        # 命令面板
│   │   │   ├── config_panel.py         # 配置面板
│   │   │   ├── log_panel.py            # 日志面板
│   │   │   ├── overview_panel.py       # 概览面板
│   │   │   ├── skills_config_widget.py # 技能配置控件
│   │   │   ├── splash_screen.py        # 启动画面
│   │   │   └── windows_bridge_panel.py # 桥接面板
│   │   ├── main_window.py    # 主窗口
│   │   └── styles.py         # 样式定义
│   ├── interfaces/           # 抽象接口
│   │   ├── config.py         # 配置接口
│   │   ├── controller.py     # 控制器接口
│   │   └── wsl.py            # WSL接口
│   ├── models/               # 数据模型
│   │   ├── channel_config.py # 频道配置模型
│   │   ├── nanobot_config.py # Bot配置模型
│   │   ├── skill.py          # 技能模型
│   │   ├── skill_config.py   # 技能配置模型
│   │   └── wsl_distro.py     # WSL分发模型
│   ├── plugins/              # 插件系统
│   │   ├── base.py           # 插件基类
│   │   └── manager.py        # 插件管理器
│   ├── services/             # 服务层
│   │   ├── ipc_server.py     # IPC服务器
│   │   ├── monitor_service.py # 监控服务
│   │   ├── nanobot_chat_client.py # 聊天客户端
│   │   ├── windows_bridge.py # Windows桥接
│   │   └── wsl_state_service.py # WSL状态服务
│   ├── utils/                # 工具函数
│   │   ├── async_ops.py      # 异步操作
│   │   ├── logger.py         # 日志工具
│   │   ├── path_converter.py # 路径转换
│   │   ├── path_utils.py     # 路径工具
│   │   ├── performance.py    # 性能工具
│   │   ├── thread_safe.py    # 线程安全
│   │   └── validators.py     # 验证器
│   ├── app.py                # 应用程序类
│   ├── constants.py          # 常量定义
│   ├── container.py          # 依赖注入容器
│   ├── events.py             # 事件总线
│   └── main.py               # 应用入口
├── init_wsl/                 # WSL初始化脚本
│   ├── README.md
│   ├── make_nanobot_distro.bat
│   ├── make_nanobot_distro_manu.bat
│   └── Clawbot-0.1.0.2-py3-none-any.whl
├── docs/                     # 文档
│   ├── spec.md               # 系统规格文档
│   ├── checklist.md          # 功能检查清单
│   └── NAMING_CONVENTIONS.md # 命名规范
├── run.py                    # Nuitka打包入口
├── build_nuitka.py           # Nuitka构建脚本
├── requirements.txt          # 依赖列表
├── setup.py                  # 安装配置
└── pyproject.toml            # 项目配置
```

## 🛠 技术栈

| 类别 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 日志 | Loguru |
| 系统操作 | psutil, pyautogui, pywinauto |
| 图像处理 | Pillow |
| 加密 | cryptography |
| Windows API | pywin32 |
| 文件监控 | watchdog |

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+1` | 切换到概览面板 |
| `Ctrl+2` | 切换到配置管理面板 |
| `Ctrl+3` | 切换到命令执行面板 |
| `Ctrl+4` | 切换到聊天面板 |
| `Ctrl+5` | 切换到桥接面板 |
| `Ctrl+6` | 切换到日志查看面板 |
| `Ctrl+S` | 保存当前配置 |
| `Ctrl+F` | 聚焦搜索 |
| `Esc` | 取消焦点 |

## 🔌 插件开发

创建自定义插件：

```python
from ftk_claw_bot.plugins.base import IPlugin

class MyPlugin(IPlugin):
    @property
    def name(self) -> str:
        return "MyPlugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "My custom plugin"
    
    def initialize(self, app) -> bool:
        # 初始化逻辑
        return True
    
    def shutdown(self) -> bool:
        # 清理逻辑
        return True
```



## 📊 默认端口

| 服务 | 端口 |
|------|------|
| IPC Bridge | 9527 |
| Gateway | 18888 |


## 📜 版本历史

| 版本 | 日期 | 变更描述 |
|------|------|----------|
| 1.0.3 | 2026-02-20 | 文档同步更新、目录结构优化 |
| 1.0.2 | 2026-02-18 | 布局优化、默认提供商调整、进度对话框修复 |
| 1.0.1 | 2026-02-17 | 版本号统一管理、插件系统、命名规范文档 |
| 1.0.0 | 2026-02-14 | 初始版本 |

## 📄 许可证

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

- **作者**: FTK Team
- **邮箱**: zeusftk@gmail.com
- **GitHub**: [https://github.com/zeusftk/FTK_Claw_Bot](https://github.com/zeusftk/FTK_Claw_Bot)
