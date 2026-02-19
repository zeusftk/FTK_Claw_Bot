"""
FreeLLM Client 独立运行入口
"""

import sys
import os

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


def check_dependencies():
    """检查并安装依赖"""
    required_packages = {
        "PyQt6": "PyQt6",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "requests": "requests",
    }
    
    missing = []
    for import_name, pip_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        print(f"[freellm] Installing missing dependencies: {', '.join(missing)}")
        import subprocess
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--quiet", *missing
        ])
        print("[freellm] Dependencies installed successfully")


def main():
    """独立运行入口"""
    check_dependencies()
    
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setApplicationName("FreeLLM Client")
    app.setApplicationVersion("1.0.0")
    
    from freellm.gui.main_window import FreeLLMServiceWindow
    window = FreeLLMServiceWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
