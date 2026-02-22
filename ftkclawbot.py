#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTK_Claw_Bot - Nuitka 打包入口文件

此文件用于 Nuitka 打包为 exe 可执行文件。
"""

import sys
import os
import traceback
from datetime import datetime


def get_log_file():
    """获取日志文件路径"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "startup.log")


def log_message(msg: str):
    """写入日志消息"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(get_log_file(), "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
        print(f"[STARTUP] {msg}")
    except Exception as e:
        print(f"[STARTUP ERROR] 无法写入日志: {e}")


def log_environment():
    """记录环境信息"""
    log_message("=" * 50)
    log_message("环境信息:")
    log_message(f"  sys.frozen: {getattr(sys, 'frozen', False)}")
    log_message(f"  sys.executable: {sys.executable}")
    log_message(f"  sys.argv: {sys.argv}")
    log_message(f"  当前工作目录: {os.getcwd()}")
    log_message(f"  Python 版本: {sys.version}")
    log_message(f"  平台: {sys.platform}")
    
    if getattr(sys, 'frozen', False):
        log_message(f"  exe 目录: {os.path.dirname(sys.executable)}")
    
    log_message("=" * 50)


def setup_frozen_env():
    """设置打包后的环境"""
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
        os.environ['FTK_CLAW_BOT_FROZEN'] = '1'
        log_message(f"设置工作目录: {application_path}")
        
        if hasattr(sys, '_MEIPASS'):
            sys.path.insert(0, sys._MEIPASS)
            log_message(f"添加 MEIPASS 到 sys.path: {sys._MEIPASS}")


def redirect_stdio():
    """重定向标准输入输出，防止无控制台模式下崩溃"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        log_message("stdout 已重定向到 /dev/null")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        log_message("stderr 已重定向到 /dev/null")
    if sys.stdin is None:
        sys.stdin = open(os.devnull, 'r', encoding='utf-8')
        log_message("stdin 已重定向到 /dev/null")


def main():
    """主入口函数"""
    log_message(">>> 应用启动 <<<")
    
    try:
        log_environment()
        
        log_message("[步骤1] 重定向标准IO...")
        try:
            redirect_stdio()
            log_message("[步骤1] 完成")
        except Exception as e:
            log_message(f"[步骤1] 失败: {e}")
        
        log_message("[步骤2] 设置打包环境...")
        try:
            setup_frozen_env()
            log_message("[步骤2] 完成")
        except Exception as e:
            log_message(f"[步骤2] 失败: {e}")
        
        log_message("[步骤3] 导入主模块...")
        try:
            from ftk_claw_bot.main import main as app_main
            log_message("[步骤3] 主模块导入成功")
        except Exception as e:
            log_message(f"[步骤3] 主模块导入失败: {e}\n{traceback.format_exc()}")
            raise
        
        log_message("[步骤4] 执行主函数...")
        try:
            result = app_main()
            log_message(f"[步骤4] 主函数返回，退出码: {result}")
        except Exception as e:
            log_message(f"[步骤4] 主函数执行失败: {e}\n{traceback.format_exc()}")
            raise
        
        log_message(">>> 应用正常退出 <<<")
        return result
        
    except Exception as e:
        error_msg = f"!!! 启动失败 !!!\n异常类型: {type(e).__name__}\n异常信息: {e}\n堆栈跟踪:\n{traceback.format_exc()}"
        log_message(error_msg)
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动错误", f"应用启动失败:\n{e}\n\n详细信息请查看 logs/startup.log")
            root.destroy()
        except Exception as tk_err:
            log_message(f"无法显示错误对话框: {tk_err}")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
