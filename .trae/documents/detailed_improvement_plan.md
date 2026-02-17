# FTK_claw_bot 详细改进计划

## 计划信息

| 项目 | 内容 |
|------|------|
| 项目名称 | FTK_claw_bot |
| 计划版本 | 1.0 |
| 创建日期 | 2026-02-16 |
| 目标状态 | 生产就绪 |

---

## 一、计划概述

本计划基于三份分析文档综合制定：
1. `chat_windows_bridge_optimization_plan.md` - 聊天功能与Windows桥接优化
2. `project_analysis_and_improvement_plan.md` - 项目全面分析
3. `PROJECT_IMPROVEMENTS.md` - 项目缺陷与改进建议

### 核心目标

- **代码结构清晰**：消除冗余，统一规范，提高可维护性
- **功能明确**：完善缺失功能，优化用户体验
- **生产标准**：建立测试体系，确保稳定性和安全性

---

## 二、阶段一：立即修复（1-2天）

### 任务清单

#### 2.1 清理冗余文件
- [ ] **删除 wsl_panel.py** - 功能已整合到 overview_panel.py
- [ ] **清理 __init__.py** - 移除对 WSLPanel 的引用
- [ ] **合并检查清单** - 保留 checklist.md，删除 ftk_bot_features_checklist.md

#### 2.2 修复依赖问题
- [ ] **补充 pyproject.toml** - 添加缺失的依赖：
  - websockets
  - loguru
  - pydantic
  - pydantic-settings
- [ ] **验证依赖安装** - 确保所有依赖正确安装

#### 2.3 完善桥接面板功能
- [ ] **连接桥接服务** - 使 GUI 按钮实际调用 WindowsBridge
- [ ] **添加状态反馈** - 显示操作执行结果
- [ ] **完善日志记录** - 记录所有桥接操作

#### 2.4 完善线程安全
- [ ] **全面审查** - 检查所有跨线程调用
- [ ] **统一使用 ThreadSafeSignal** - 确保所有 GUI 回调线程安全
- [ ] **测试验证** - 确保没有线程安全错误

### 验收标准

- ✅ 无冗余文件
- ✅ 所有依赖正确安装
- ✅ 桥接面板功能完整可用
- ✅ 无 Qt 线程安全错误

---

## 三、阶段二：短期改进（1周）

### 任务清单

#### 3.1 建立测试体系
- [ ] **创建 tests 目录结构**
  ```
  tests/
  ├── __init__.py
  ├── unit/          # 单元测试
  │   ├── test_wsl_manager.py
  │   ├── test_config_manager.py
  │   └── ...
  ├── integration/   # 集成测试
  │   ├── test_chat_flow.py
  │   └── test_bridge.py
  └── e2e/          # 端到端测试
      └── test_app.py
  ```

- [ ] **配置 pytest** - 在 pyproject.toml 中添加测试配置
- [ ] **编写核心测试** - 为核心模块编写单元测试（目标覆盖率 > 60%）
- [ ] **运行测试** - 确保所有测试通过

#### 3.2 添加代码规范工具
- [ ] **配置 ruff** - 代码检查工具
- [ ] **配置 black** - 代码格式化工具
- [ ] **配置 mypy** - 类型检查工具
- [ ] **应用规范** - 修复所有规范问题
- [ ] **添加 pre-commit 钩子** - 提交前自动检查

#### 3.3 完善错误处理
- [ ] **替换空 pass** - 为所有异常添加有意义的处理
- [ ] **统一错误提示** - 建立统一的错误处理机制
- [ ] **添加错误恢复** - 关键操作添加重试机制

#### 3.4 添加文档字符串
- [ ] **核心类** - 为所有核心类添加文档
- [ ] **公共方法** - 为所有公共方法添加文档
- [ ] **复杂逻辑** - 为复杂逻辑添加行内注释

### 验收标准

- ✅ 测试目录完整，测试覆盖率 > 60%
- ✅ 代码通过 ruff、black、mypy 检查
- ✅ 所有异常都有妥善处理
- ✅ 核心代码都有文档字符串

---

## 四、阶段三：中期改进（2-4周）

### 任务清单

#### 4.1 架构改进

##### 4.1.1 统一配置管理
- [ ] **创建 config 模块**
  ```
  ftk_bot/config/
  ├── __init__.py
  ├── settings.py      # 使用 pydantic-settings
  ├── loader.py        # 配置加载器
  └── validator.py     # 配置验证器
  ```

- [ ] **定义设置类** - 使用 pydantic-settings
- [ ] **迁移硬编码** - 将所有硬编码值移到配置中
- [ ] **支持环境变量** - 支持通过环境变量覆盖配置

##### 4.1.2 引入状态管理
- [ ] **创建 StateManager** - 全局状态管理器
- [ ] **定义状态结构** - 使用 dataclass 定义应用状态
- [ ] **状态变更通知** - 实现状态变更的事件机制
- [ ] **迁移状态代码** - 将分散的状态管理迁移到 StateManager

##### 4.1.3 引入事件总线
- [ ] **创建 EventBus** - 模块间松耦合通信
- [ ] **定义事件类型** - 标准化事件格式
- [ ] **迁移信号槽** - 将部分信号槽改为事件总线

#### 4.2 功能完善

##### 4.2.1 聊天功能增强
- [ ] **消息持久化** - 保存聊天历史到数据库或文件
- [ ] **消息管理** - 支持编辑和删除消息
- [ ] **消息搜索** - 添加历史消息搜索功能
- [ ] **消息导出** - 支持导出聊天记录

##### 4.2.2 配置管理改进
- [ ] **配置验证** - 添加完整的配置验证
- [ ] **配置导入导出** - 支持 JSON/YAML 格式
- [ ] **配置模板** - 提供常用配置模板
- [ ] **配置备份** - 自动备份配置

##### 4.2.3 用户体验优化
- [ ] **主题切换** - 支持深色/浅色主题
- [ ] **初始化向导** - 首次使用引导流程
- [ ] **快捷键提示** - 显示快捷键帮助
- [ ] **状态栏提示** - 非关键错误在状态栏显示

#### 4.3 安全改进
- [ ] **API 密钥加密** - 使用 cryptography 加密存储
- [ ] **输入验证** - 完善所有用户输入验证
- [ ] **审计日志** - 记录敏感操作
- [ ] **权限验证** - 为桥接服务添加访问控制

### 验收标准

- ✅ 统一的配置管理系统
- ✅ 全局状态管理
- ✅ 事件总线机制
- ✅ 聊天功能完整增强
- ✅ 配置管理完善
- ✅ 安全措施到位

---

## 五、阶段四：长期改进（1-2月）

### 任务清单

#### 5.1 架构演进

##### 5.1.1 引入 MVVM 架构
- [ ] **创建 ViewModel 层** - 分离 GUI 和业务逻辑
- [ ] **迁移现有代码** - 逐步将代码迁移到 MVVM
- [ ] **数据绑定** - 使用 PyQt6 的数据绑定机制

##### 5.1.2 添加插件系统
- [ ] **定义插件接口** - 标准化插件 API
- [ ] **插件加载器** - 实现插件动态加载
- [ ] **示例插件** - 提供插件开发示例

##### 5.1.3 拆分大组件
- [ ] **overview_panel.py** - 拆分为多个小组件
- [ ] **main_window.py** - 简化主窗口逻辑
- [ ] **其他大文件** - 超过 500 行的文件都要拆分

#### 5.2 功能增强

##### 5.2.1 多语言支持
- [ ] **国际化框架** - 引入 gettext 或类似框架
- [ ] **提取字符串** - 将所有 UI 字符串提取到翻译文件
- [ ] **中文/英文** - 首先支持中英文切换

##### 5.2.2 自动化测试
- [ ] **CI/CD 配置** - 配置 GitHub Actions 或类似 CI
- [ ] **端到端测试** - 编写完整的 E2E 测试
- [ ] **性能测试** - 添加性能基准测试

##### 5.2.3 数据分析
- [ ] **使用数据收集** - 匿名收集使用数据
- [ ] **数据分析面板** - 显示使用统计
- [ ] **用户行为优化** - 基于数据优化 UX

#### 5.3 性能优化
- [ ] **缓存机制** - 缓存 WSL 命令结果
- [ ] **错误恢复** - 自动检测和重启崩溃的进程
- [ ] **资源管理** - 实现资源自动清理
- [ ] **启动优化** - 优化应用启动时间

### 验收标准

- ✅ MVVM 架构实施完成
- ✅ 插件系统可用
- ✅ 所有组件都合理拆分
- ✅ 多语言支持
- ✅ CI/CD 流水线
- ✅ 性能显著提升

---

## 六、具体实施细节

### 6.1 测试配置示例 (pyproject.toml 补充)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short --cov=ftk_bot --cov-report=term-missing"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.coverage.run]
source = ["ftk_bot"]
omit = ["ftk_bot/gui/*"]
```

### 6.2 配置管理示例

```python
# ftk_bot/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

class AppSettings(BaseSettings):
    """应用全局配置"""
    app_name: str = "FTK_bot"
    app_version: str = "0.2.0"
    
    # 路径配置
    config_dir: Path = Path.home() / ".ftk_bot"
    workspace_dir: Optional[Path] = None
    
    # WSL 配置
    default_distro: str = "Ubuntu"
    wsl_timeout: int = 30
    
    # 桥接配置
    bridge_port: int = 9527
    bridge_host: str = "0.0.0.0"
    
    # Gateway 配置
    gateway_port: int = 18888
    
    # 监控配置
    monitor_interval: float = 5.0
    
    # 安全配置
    encrypt_apiKeys: bool = True
    
    model_config = {
        "env_prefix": "FTK_BOT_",
        "env_file": ".env",
    }
```

### 6.3 状态管理示例

```python
# ftk_bot/core/state.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from enum import Enum

class AppStateChange(Enum):
    WSL_DISTROS = "wsl_distros"
    NANOBOT_INSTANCES = "nanobot_instances"
    SELECTED_CONFIG = "selected_config"
    CHAT_CONNECTIONS = "chat_connections"
    BRIDGE_RUNNING = "bridge_running"

@dataclass
class AppState:
    """应用状态数据类"""
    wsl_distros: Dict[str, Any] = field(default_factory=dict)
    nanobot_instances: Dict[str, Any] = field(default_factory=dict)
    selected_config: Optional[str] = None
    chat_connections: Dict[str, bool] = field(default_factory=dict)
    bridge_running: bool = False

class StateManager(QObject):
    """状态管理器"""
    state_changed = pyqtSignal(str, object)  # 变更类型, 新值
    
    def __init__(self):
        super().__init__()
        self._state = AppState()
    
    def get(self, key: str) -> Any:
        """获取状态值"""
        return getattr(self._state, key)
    
    def set(self, key: str, value: Any):
        """设置状态值并通知变更"""
        old_value = getattr(self._state, key)
        if old_value != value:
            setattr(self._state, key, value)
            self.state_changed.emit(key, value)
    
    def get_state(self) -> AppState:
        """获取完整状态"""
        return self._state
```

---

## 七、里程碑与交付物

### 里程碑 1：立即修复（第 2 天）
- **交付物**：
  - 清理后的代码库
  - 完整的依赖配置
  - 功能完整的桥接面板
- **验证**：应用正常启动，无线程安全错误

### 里程碑 2：短期改进（第 7 天）
- **交付物**：
  - 完整的测试套件
  - 代码规范配置
  - 改进的错误处理
  - 完整的文档字符串
- **验证**：测试通过率 100%，代码通过规范检查

### 里程碑 3：中期改进（第 28 天）
- **交付物**：
  - 统一的配置管理系统
  - 全局状态管理
  - 事件总线
  - 增强的聊天功能
  - 安全改进
- **验证**：所有新功能可用，安全措施到位

### 里程碑 4：长期改进（第 56 天）
- **交付物**：
  - MVVM 架构
  - 插件系统
  - 多语言支持
  - CI/CD 流水线
  - 性能优化
- **验证**：生产就绪，性能显著提升

---

## 八、风险评估与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 架构重构影响现有功能 | 中 | 高 | 充分测试，逐步迁移 |
| 测试编写耗时较长 | 高 | 中 | 优先核心模块，逐步覆盖 |
| 依赖升级兼容性问题 | 中 | 中 | 仔细测试，准备回滚方案 |
| 用户习惯改变 | 低 | 中 | 保持向后兼容，提供迁移指南 |
| 性能优化过度设计 | 低 | 低 | 先测量，再优化 |

---

## 九、成功标准

### 9.1 代码质量
- [ ] 测试覆盖率 > 80%（核心模块）
- [ ] 代码通过 ruff、black、mypy 检查
- [ ] 无严重的代码规范问题
- [ ] 所有公共 API 都有文档

### 9.2 功能完整性
- [ ] 所有核心功能都实现
- [ ] 初始化向导可用
- [ ] 主题切换可用
- [ ] 配置导入导出可用

### 9.3 用户体验
- [ ] 应用启动时间 < 3 秒
- [ ] 界面响应流畅
- [ ] 错误提示友好
- [ ] 用户满意度 > 4/5

### 9.4 稳定性
- [ ] 连续运行 24 小时无崩溃
- [ ] 内存泄漏检测通过
- [ ] 错误恢复机制有效
- [ ] 自动保活机制正常

### 9.5 安全性
- [ ] API 密钥加密存储
- [ ] 输入验证完善
- [ ] 审计日志完整
- [ ] 权限验证到位

---

## 十、后续维护

### 10.1 持续集成
- 每次提交运行测试
- 每日构建
- 性能基准测试

### 10.2 代码审查
- 所有代码变更需要审查
- 使用 Pull Request 流程
- 自动化检查作为审查的一部分

### 10.3 文档维护
- 保持用户文档更新
- 保持开发文档更新
- 记录架构决策

---

## 附录

### A. 参考文档
- [PyQt6 官方文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pytest 官方文档](https://docs.pytest.org/)
- [pydantic 官方文档](https://docs.pydantic.dev/)
- [架构模式](https://martinfowler.com/architecture/)

### B. 相关工具
- **测试**：pytest, pytest-qt, pytest-cov
- **代码规范**：ruff, black, isort
- **类型检查**：mypy
- **文档**：sphinx, mkdocs

---

*计划创建日期：2026-02-16*
*最后更新：2026-02-16*