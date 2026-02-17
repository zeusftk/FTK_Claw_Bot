#!/usr/bin/env python3
"""检查导入是否成功"""

print("检查 ConfigSyncManager 导入...")
try:
    from ftk_claw_bot.core.config_sync_manager import ConfigSyncManager
    print("✓ ConfigSyncManager 导入成功")
except Exception as e:
    print(f"✗ ConfigSyncManager 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n检查 NanobotConfig 导入...")
try:
    from ftk_claw_bot.models.nanobot_config import NanobotConfig
    print("✓ NanobotConfig 导入成功")
except Exception as e:
    print(f"✗ NanobotConfig 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n检查 NanobotController 导入...")
try:
    from ftk_claw_bot.core.nanobot_controller import NanobotController
    print("✓ NanobotController 导入成功")
except Exception as e:
    print(f"✗ NanobotController 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("\n检查 core 模块导出...")
try:
    from ftk_claw_bot.core import ConfigSyncManager
    print("✓ ConfigSyncManager 在 core 模块中导出成功")
except Exception as e:
    print(f"✗ ConfigSyncManager 在 core 模块中导出失败: {e}")

print("\n检查完成!")
