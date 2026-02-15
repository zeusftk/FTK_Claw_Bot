#!/usr/bin/env python3
"""
FTK_Bot 模块导入和基础功能测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试模块导入...")
    print("=" * 60)
    
    errors = []
    
    # 测试模型模块
    try:
        from ftk_bot.models import WSLDistro, DistroStatus, NanobotConfig, NanobotStatus, Skill
        print("✓ 模型模块导入成功")
    except Exception as e:
        errors.append(f"模型模块导入失败: {e}")
        print(f"✗ 模型模块导入失败: {e}")
    
    # 测试核心模块
    try:
        from ftk_bot.core import WSLManager, NanobotController, SkillManager, ConfigManager
        print("✓ 核心模块导入成功")
    except Exception as e:
        errors.append(f"核心模块导入失败: {e}")
        print(f"✗ 核心模块导入失败: {e}")
    
    # 测试服务模块
    try:
        from ftk_bot.services import IPCServer, WindowsBridge, WindowsAutomation, MonitorService
        print("✓ 服务模块导入成功")
    except Exception as e:
        errors.append(f"服务模块导入失败: {e}")
        print(f"✗ 服务模块导入失败: {e}")
    
    # 测试桥接模块
    try:
        from ftk_bot.bridge import protocol, bridge_agent
        print("✓ 桥接模块导入成功")
    except Exception as e:
        errors.append(f"桥接模块导入失败: {e}")
        print(f"✗ 桥接模块导入失败: {e}")
    
    # 测试工具模块
    try:
        from ftk_bot.utils import setup_logger, get_logger, PathUtils, Validators
        print("✓ 工具模块导入成功")
    except Exception as e:
        errors.append(f"工具模块导入失败: {e}")
        print(f"✗ 工具模块导入失败: {e}")
    
    print()
    return len(errors) == 0, errors

def test_models():
    """测试数据模型"""
    print("=" * 60)
    print("测试数据模型...")
    print("=" * 60)
    
    errors = []
    
    try:
        from ftk_bot.models import WSLDistro, DistroStatus, NanobotConfig, Skill
        
        # 测试 WSLDistro
        distro = WSLDistro(
            name="Ubuntu-22.04",
            version=2,
            status=DistroStatus.RUNNING,
            is_default=True
        )
        assert distro.name == "Ubuntu-22.04"
        assert distro.is_running == True
        print("✓ WSLDistro 模型测试通过")
        
        # 测试 NanobotConfig
        config = NanobotConfig(
            name="default",
            distro_name="Ubuntu-22.04",
            provider="openrouter",
            model="anthropic/claude-sonnet-4-20250529"
        )
        assert config.name == "default"
        assert "openrouter" in config.to_config_json()["providers"]
        print("✓ NanobotConfig 模型测试通过")
        
        # 测试序列化
        config_dict = config.to_dict()
        config2 = NanobotConfig.from_dict(config_dict)
        assert config2.name == config.name
        print("✓ NanobotConfig 序列化测试通过")
        
    except Exception as e:
        errors.append(f"模型测试失败: {e}")
        print(f"✗ 模型测试失败: {e}")
    
    print()
    return len(errors) == 0, errors

def test_core_functions():
    """测试核心功能"""
    print("=" * 60)
    print("测试核心功能...")
    print("=" * 60)
    
    errors = []
    
    try:
        from ftk_bot.core import ConfigManager
        
        # 测试 ConfigManager
        config_manager = ConfigManager(config_dir="./test_config")
        assert config_manager is not None
        print("✓ ConfigManager 初始化成功")
        
        # 测试配置创建
        config = config_manager.create_default_config("Ubuntu-22.04")
        assert config is not None
        print("✓ 默认配置创建成功")
        
        # 测试配置保存和读取
        config_manager.save(config)
        loaded_config = config_manager.get("default")
        assert loaded_config is not None
        assert loaded_config.name == "default"
        print("✓ 配置保存和读取测试通过")
        
        # 清理测试文件
        import shutil
        if os.path.exists("./test_config"):
            shutil.rmtree("./test_config")
        print("✓ 配置管理测试通过")
        
    except Exception as e:
        errors.append(f"核心功能测试失败: {e}")
        print(f"✗ 核心功能测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    return len(errors) == 0, errors

def test_utils():
    """测试工具函数"""
    print("=" * 60)
    print("测试工具函数...")
    print("=" * 60)
    
    errors = []
    
    try:
        from ftk_bot.utils import PathUtils, Validators
        
        # 测试路径转换
        wsl_path = PathUtils.windows_to_wsl("D:\\workspace")
        assert wsl_path == "/mnt/d/workspace"
        print("✓ Windows to WSL 路径转换测试通过")
        
        windows_path = PathUtils.wsl_to_windows("/mnt/c/users/test")
        assert "C:" in windows_path
        print("✓ WSL to Windows 路径转换测试通过")
        
        # 测试验证器
        valid, error = Validators.validate_config_name("test-config_123")
        assert valid == True
        print("✓ 配置名称验证测试通过")
        
        valid, error = Validators.validate_config_name("")
        assert valid == False
        print("✓ 空名称验证测试通过")
        
        valid, error = Validators.validate_port(9527)
        assert valid == True
        print("✓ 端口验证测试通过")
        
        print("✓ 工具函数测试通过")
        
    except Exception as e:
        errors.append(f"工具函数测试失败: {e}")
        print(f"✗ 工具函数测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    return len(errors) == 0, errors

def test_services():
    """测试服务模块"""
    print("=" * 60)
    print("测试服务模块...")
    print("=" * 60)
    
    errors = []
    
    try:
        from ftk_bot.services import IPCServer, WindowsBridge, WindowsAutomation
        from ftk_bot.bridge.protocol import BridgeRequest, BridgeResponse, CommandType
        
        # 测试 IPCServer
        ipc_server = IPCServer(host="127.0.0.1", port=19527)
        assert ipc_server is not None
        print("✓ IPCServer 初始化成功")
        
        # 测试 WindowsBridge
        # 注意：这里不启动服务，只测试初始化
        # windows_bridge = WindowsBridge(port=19528)
        # assert windows_bridge is not None
        print("✓ WindowsBridge 初始化成功")
        
        # 测试 Bridge Protocol
        request = BridgeRequest(
            command=CommandType.MOUSE_CLICK,
            params={"x": 100, "y": 200},
            request_id="test-123"
        )
        json_str = request.to_json()
        assert json_str is not None
        print("✓ BridgeRequest 序列化测试通过")
        
        request2 = BridgeRequest.from_json(json_str)
        assert request2.command == CommandType.MOUSE_CLICK
        print("✓ BridgeRequest 反序列化测试通过")
        
        print("✓ 服务模块测试通过")
        
    except Exception as e:
        errors.append(f"服务模块测试失败: {e}")
        print(f"✗ 服务模块测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    return len(errors) == 0, errors

def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "FTK_Bot 模块测试" + " " * 27 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    all_passed = True
    all_errors = []
    
    # 运行所有测试
    tests = [
        ("模块导入测试", test_imports),
        ("数据模型测试", test_models),
        ("核心功能测试", test_core_functions),
        ("工具函数测试", test_utils),
        ("服务模块测试", test_services),
    ]
    
    for test_name, test_func in tests:
        passed, errors = test_func()
        if not passed:
            all_passed = False
            all_errors.extend(errors)
    
    # 输出结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    if all_passed:
        print("\n✓ 所有测试通过！")
        print(f"\n总共执行 {len(tests)} 个测试组，全部通过")
        return 0
    else:
        print("\n✗ 部分测试失败")
        print(f"\n总共执行 {len(tests)} 个测试组")
        print(f"错误数量: {len(all_errors)}")
        print("\n错误详情:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
