"""日志配置模块"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str = "cloud_price_index") -> logging.Logger:
    """初始化并返回日志器"""
    # 配置根日志器，使所有子模块日志都能输出
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        return logging.getLogger(name)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    root.addHandler(console_handler)

    # 文件 Handler
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(str(log_dir / "cloud-price-index.log"), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    return logging.getLogger(name)


def get_logger(name: str = "cloud_price_index") -> logging.Logger:
    """获取已存在的日志器"""
    return logging.getLogger(name)
