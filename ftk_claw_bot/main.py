# -*- coding: utf-8 -*-
"""
FTK_Claw_Bot - Windows桌面应用，用于管理WSL2中的clawbot助手，并扩展clawbot对windows的操作
"""

import os
import sys
import traceback
from datetime import datetime
from ftk_claw_bot.app import Application
from ftk_claw_bot.constants import VERSION, APP_NAME
from loguru import logger


def _debug_log(msg: str):
    """调试日志 - 同时输出到日志文件和控制台"""
    try:
        print(f"[DEBUG] {msg}")
        logger.info(msg)
    except Exception:
        pass


def main():
    _debug_log("=" * 50)
    _debug_log(">>> 进入 main() 函数 <<<")
    
    try:
        _debug_log("[MAIN-01] 创建 Application 实例...")
        try:
            app = Application()
            _debug_log("[MAIN-01] Application 实例创建成功")
        except Exception as e:
            _debug_log(f"[MAIN-01] Application 创建失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-02] 设置环境...")
        try:
            app.setup_environment()
            _debug_log("[MAIN-02] 环境设置完成")
        except Exception as e:
            _debug_log(f"[MAIN-02] 环境设置失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-03] 设置日志...")
        try:
            app.setup_logging()
            _debug_log("[MAIN-03] 日志设置完成")
        except Exception as e:
            _debug_log(f"[MAIN-03] 日志设置失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-04] 创建 Qt 应用...")
        try:
            qt_app = app.create_qt_app()
            _debug_log(f"[MAIN-04] Qt 应用创建成功, type: {type(qt_app)}")
        except Exception as e:
            _debug_log(f"[MAIN-04] Qt 应用创建失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-05] 显示启动画面...")
        try:
            splash = app.show_splash()
            _debug_log(f"[MAIN-05] 启动画面显示成功, splash: {splash}")
        except Exception as e:
            _debug_log(f"[MAIN-05] 启动画面显示失败: {e}\n{traceback.format_exc()}")
            raise
        
        def update_progress(message: str, progress: int):
            _debug_log(f"[PROGRESS] {message} ({progress}%)")
            if splash:
                try:
                    splash.set_status(message, progress)
                    qt_app.processEvents()
                except Exception as e:
                    _debug_log(f"[PROGRESS] 更新进度失败: {e}")
        
        _debug_log("[MAIN-06] 初始化服务...")
        try:
            app.init_services(progress_callback=update_progress)
            _debug_log("[MAIN-06] 服务初始化完成")
        except Exception as e:
            _debug_log(f"[MAIN-06] 服务初始化失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-07] 创建主窗口...")
        try:
            window = app.create_main_window()
            _debug_log(f"[MAIN-07] 主窗口创建成功, window: {window}")
        except Exception as e:
            _debug_log(f"[MAIN-07] 主窗口创建失败: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-08] 关闭启动画面...")
        try:
            app.close_splash()
            _debug_log("[MAIN-08] 启动画面已关闭")
        except Exception as e:
            _debug_log(f"[MAIN-08] 关闭启动画面失败: {e}")
        
        _debug_log("[MAIN-09] 进入事件循环...")
        try:
            exit_code = app.run()
            _debug_log(f"[MAIN-09] 事件循环结束, exit_code: {exit_code}")
        except Exception as e:
            _debug_log(f"[MAIN-09] 事件循环异常: {e}\n{traceback.format_exc()}")
            raise
        
        _debug_log("[MAIN-10] 执行关闭清理...")
        try:
            app.shutdown()
            _debug_log("[MAIN-10] 关闭清理完成")
        except Exception as e:
            _debug_log(f"[MAIN-10] 关闭清理失败: {e}")
        
        _debug_log(f">>> main() 正常返回, exit_code: {exit_code} <<<")
        return exit_code
        
    except Exception as e:
        error_msg = f"!!! main() 异常 !!!\n异常类型: {type(e).__name__}\n异常信息: {e}\n堆栈跟踪:\n{traceback.format_exc()}"
        _debug_log(error_msg)
        print(error_msg)
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("初始化错误", f"应用初始化失败:\n{e}\n\n详细信息请查看 logs 目录")
            root.destroy()
        except Exception:
            pass
        
        return 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
