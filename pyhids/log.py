"""
pyhids.log —— 统一的日志配置
"""
from __future__ import annotations

import logging

def setup_logging(level: str = "INFO") -> None:
    """初始化root logger 的格式和级别"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",)