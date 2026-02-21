#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FTK_Claw_Bot - Nuitka 打包入口文件

此文件用于 Nuitka 打包为 exe 可执行文件。
"""

import sys
import os


def setup_frozen_env():
    """设置打包后的环境"""
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
        os.environ['FTK_CLAW_BOT_FROZEN'] = '1'
        
        if hasattr(sys, '_MEIPASS'):
            sys.path.insert(0, sys._MEIPASS)


def redirect_stdio():
    """重定向标准输入输出，防止无控制台模式下崩溃"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    if sys.stdin is None:
        sys.stdin = open(os.devnull, 'r', encoding='utf-8')


def main():
    """主入口函数"""
    redirect_stdio()
    setup_frozen_env()
    
    from ftk_claw_bot.main import main as app_main
    return app_main()


if __name__ == '__main__':
    sys.exit(main())
