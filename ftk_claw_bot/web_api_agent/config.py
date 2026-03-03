"""Web API Agent 配置模块"""
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Web API Agent 配置类"""
    HEADLESS: bool = False  # 无头模式（False = 显示浏览器窗口）
    MAX_ACTIONS_PER_MINUTE: int = 60  # 每分钟最大操作数

    class Config:
        env_file = ".env"


config = Config()
