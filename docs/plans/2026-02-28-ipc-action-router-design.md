# IPC 操作分层路由设计

## 概述

将 IPC 请求按 `target_type` 分类路由到不同的执行器，并支持失败降级到通用方案。

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    WindowsBridge (IPC :9527)                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    IPCServer                            │   │
│  │                    (接收请求)                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  ActionRouter (新增)                    │   │
│  │                  (请求路由 + 降级逻辑)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│           │                      │                      │       │
│           ▼                      ▼                      ▼       │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │   WebAgent   │    │  (将来预留位置)   │    │  WindowsAuto │  │
│  │  (Playwright)│    │  DesktopAgent    │    │  (pyautogui) │  │
│  │              │    │                  │    │              │  │
│  │  懒加载启动   │    │     未实现       │    │  当前方案    │  │
│  └──────────────┘    └──────────────────┘    └──────────────┘  │
│         │                                            ▲          │
│         │ 失败/超时/空结果                            │          │
│         └────────────────────────────────────────────┘          │
│                         降级                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 消息协议扩展

### 请求消息

```python
{
    "version": "1.0",
    "type": "request",
    "id": "uuid",
    "timestamp": "ISO时间",
    "payload": {
        "target_type": "browser",      # browser | desktop | generic
        "action": "click",
        "params": {
            "selector": "#submit-btn", # 浏览器: CSS选择器
            "x": 100, "y": 200,        # 降级时使用的坐标
            "timeout": 10              # 可选超时时间(秒)
        }
    }
}
```

### 响应消息

```python
{
    "version": "1.0",
    "type": "response",
    "id": "uuid",
    "timestamp": "ISO时间",
    "payload": {
        "success": true,
        "result": {...},
        "executor": "webagent",        # webagent | automation
        "fallback": false              # 是否使用了降级
    }
}
```

## target_type 分类

| 值 | 说明 | 执行器 | 降级 |
|---|---|---|---|
| `browser` | 浏览器操作 | WebAgent (Playwright) | WindowsAutomation |
| `desktop` | 桌面应用操作 | (未实现) | WindowsAutomation |
| `generic` | 通用操作 | WindowsAutomation | 无 |

## 降级触发条件

以下任一情况触发降级：

1. **异常** - WebAgent 抛出异常（元素未找到、超时、页面加载失败等）
2. **空结果** - WebAgent 返回 None 或空结果
3. **超时** - WebAgent 超过指定时间未响应（默认 10 秒）

## WebAgent 集成方式

- **集成模式**: 直接集成到 WindowsBridge 进程，避免 HTTP 开销
- **初始化**: 懒加载，首次收到 `browser` 请求时启动 Playwright
- **生命周期**: 随 WindowsBridge 启动/关闭

## 核心组件

### ActionRouter

职责：
- 解析 `target_type` 字段
- 路由请求到对应执行器
- 处理降级逻辑
- 记录执行日志

### WebAgentExecutor

职责：
- 封装 WebAgent，提供统一接口
- 管理懒加载初始化
- 处理超时控制

### WindowsAutomation

职责：
- 现有实现，作为兜底方案
- 保持不变

## 处理流程

```
请求到达
    │
    ▼
解析 target_type
    │
    ├── "browser" ──→ WebAgentExecutor 执行
    │                      │
    │                      ├── 成功 → 返回结果 (executor=webagent)
    │                      │
    │                      └── 失败/超时/空 → 降级到 automation
    │
    ├── "desktop" ──→ (未实现) → 直接使用 automation
    │
    └── "generic" ──→ WindowsAutomation 执行
                           │
                           └── 返回结果 (executor=automation)
```

## 文件变更

| 文件 | 变更 |
|------|------|
| `ftk_claw_bot/services/action_router.py` | 新增 - 请求路由器 |
| `ftk_claw_bot/services/web_agent_executor.py` | 新增 - WebAgent 执行器 |
| `ftk_claw_bot/services/windows_bridge.py` | 修改 - 集成 ActionRouter |
| `ftk_claw_bot/bridge/protocol.py` | 修改 - 扩展消息协议 |

## 扩展性

将来添加 DesktopAgent 时：

1. 创建 `DesktopAgentExecutor`
2. 在 `ActionRouter` 中添加 `desktop` 分支
3. 实现降级逻辑

无需修改现有架构。
