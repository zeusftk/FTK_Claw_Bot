#!/usr/bin/env python3
"""
FTK_Bot - Windows桌面应用，用于管理WSL2中的Nanobot AI助手
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ftk_bot.utils import setup_logger


def main():
    setup_logger("ftk_bot", console=True)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from ftk_bot.gui import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("FTK_Bot")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("FTK_Bot Team")

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
