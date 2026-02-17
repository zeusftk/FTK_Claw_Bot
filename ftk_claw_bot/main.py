"""
FTK_Claw_Bot - Windows桌面应用，用于管理WSL2中的clawbot助手，并扩展clawbot对windows的操作
"""

from ftk_claw_bot.app import Application
from ftk_claw_bot.constants import VERSION, APP_NAME


def main():
    app = Application()
    
    app.setup_environment()
    app.setup_logging()
    
    qt_app = app.create_qt_app()
    
    splash = app.show_splash()
    
    def update_progress(message: str, progress: int):
        if splash:
            splash.set_status(message, progress)
            qt_app.processEvents()
    
    app.init_services(progress_callback=update_progress)
    
    window = app.create_main_window()
    
    app.close_splash()
    
    exit_code = app.run()
    
    app.shutdown()
    
    return exit_code


if __name__ == "__main__":
    main()
