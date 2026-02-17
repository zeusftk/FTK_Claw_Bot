# FTK_Claw_Bot

Windows桌面应用，用于管理WSL2中的clawbot助手，并扩展clawbot对windows的操作。

## 功能特性

- **WSL2 管理**: 管理和监控 WSL2 分发版本的运行状态
- **clawbot 控制**: 启动、停止、配置和监控 clawbot 实例
- **Windows 桥接**: 让 clawbot 能够控制 Windows 应用和 GUI
- **配置管理**: 灵活的配置系统，支持多配置切换
- **技能管理**: 完整的技能库 CRUD 操作

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
cd FTK_Claw_Bot/FTK_bot_A
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
FTK_bot_A/
├── ftk_claw_bot/
│   ├── core/           # 核心业务逻辑
│   ├── services/       # 服务层
│   ├── gui/            # GUI 界面
│   ├── models/         # 数据模型
│   ├── utils/          # 工具函数
│   └── main.py         # 应用入口
├── tests/              # 测试目录
├── requirements.txt    # 依赖列表
├── setup.py            # 安装配置
└── pyproject.toml      # 项目配置
```

## 许可证

MIT License
