#!/usr/bin/env python3
"""
FTK_Bot - Windows桌面应用，用于管理WSL2中的Nanobot AI助手
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "Round"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

from ftk_bot.utils import setup_logger


def main():
    setup_logger("ftk_bot", console=True)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("FTK_Bot")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("FTK_Bot Team")

    app.setStyle("Fusion")

    from ftk_bot.gui import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
