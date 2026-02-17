# FTK_Claw_Bot

FTK_Claw_Bot - Windows 平台最强 openclaw 平替工具，专注 WSL2 环境下 bot 管理与控制，支持单机多 bot 实例并行运行。提供完整 Windows 系统操作桥接（鼠标/键盘/截图/窗口/剪贴板），现代化 PyQt6 图形界面，插件系统支持无限扩展，WSL2 桥接代理实现跨系统协作，是 Windows 开发者必备的 bot 管理利器，WSL 生态系统核心组件。

## 功能特性

### 核心功能
- **WSL2 管理**: 管理 WSL2 分发版本（启动/停止/导入/移除），实时资源监控，IP 地址获取，终端打开
- **Bot 控制**: 启动、停止、重启 bot 实例，支持单机多 bot 并行运行，实时状态监控，日志查看与过滤
- **配置管理**: 可视化配置编辑，多配置管理，默认配置设置，工作空间同步，跨平台路径转换
- **技能管理**: 创建/编辑/删除技能，导入/导出技能包，实时搜索，Markdown 编辑器集成
- **Windows 桥接**: 鼠标控制、键盘模拟、屏幕截图、窗口查找与控制、应用启动、剪贴板同步

### 界面特性
- **现代化 GUI**: 响应式设计，深色主题，系统托盘集成，键盘快捷键支持
- **多面板布局**: 概览面板、配置管理面板、技能管理面板、日志查看面板、聊天面板
- **实时监控**: WSL 资源监控，Bot 状态监控，系统托盘通知

### 扩展功能
- **插件系统**: 模块化插件架构，动态加载，生命周期管理，配置持久化
- **WSL2 桥接代理**: Socket 通信，请求转发，跨系统协作

## 系统要求

- Windows 10 2004+ 或 Windows 11
- WSL2 已安装并配置
- Python 3.10+
- 至少 4GB 可用内存

## 安装

### 方式一：pip 安装

```bash
pip install ftkclawbot
```

### 方式二：源码安装

```bash
git clone https://github.com/zeusftk/FTK_Claw_Bot.git
cd FTK_Claw_Bot
pip install -e .
```

## 运行

```bash
ftkclawbot
```

或者：

```bash
python -m ftk_claw_bot.main
```

## 项目结构

```
FTK_Claw_Bot/
├── ftk_claw_bot/
│   ├── bridge/           # WSL2 桥接代理
│   ├── core/             # 核心业务逻辑
│   │   ├── bridge_manager.py
│   │   ├── config_manager.py
│   │   ├── config_sync_manager.py
│   │   ├── multi_nanobot_gateway_manager.py
│   │   ├── nanobot_controller.py
│   │   ├── nanobot_distro_configurator.py
│   │   ├── nanobot_gateway_manager.py
│   │   ├── port_manager.py
│   │   ├── skill_manager.py
│   │   └── wsl_manager.py
│   ├── gui/              # GUI 界面
│   │   ├── dialogs/      # 对话框
│   │   ├── widgets/      # 控件
│   │   └── resources/    # 资源文件
│   ├── interfaces/       # 抽象接口
│   ├── models/           # 数据模型
│   ├── plugins/          # 插件系统
│   ├── services/         # 服务层
│   ├── utils/            # 工具函数
│   ├── app.py            # 应用程序类
│   ├── constants.py      # 常量定义
│   ├── container.py      # 依赖注入容器
│   ├── events.py         # 事件总线
│   └── main.py           # 应用入口
├── requirements.txt      # 依赖列表
├── setup.py              # 安装配置
└── pyproject.toml        # 项目配置
```

## 技术栈

- **GUI 框架**: PyQt6
- **系统操作**: psutil, pyautogui, pywinauto
- **图像处理**: Pillow
- **加密**: cryptography
- **Windows API**: pywin32
- **文件监控**: watchdog

## 快捷键

- `Ctrl+1~5`: 切换面板
- `Ctrl+S`: 保存当前配置
- `Ctrl+F`: 聚焦搜索
- `Esc`: 取消焦点

## 许可证

MIT License

## 联系方式

- **作者**: FTK Team
- **邮箱**: zeusftk@gmail.com
- **GitHub**: [https://github.com/zeusftk/FTK_Claw_Bot](https://github.com/zeusftk/FTK_Claw_Bot)
