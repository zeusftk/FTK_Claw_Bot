import logging
import os
from datetime import datetime
from typing import Optional


_loggers: dict = {}


def setup_logger(
    name: str = "ftk_bot",
    level: int = logging.INFO,
    log_dir: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir,
            f"ftk_bot_{datetime.now().strftime('%Y%m%d')}.log"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def get_logger(name: str = "ftk_bot") -> logging.Logger:
    if name in _loggers:
        return _loggers[name]
    return setup_logger(name)
