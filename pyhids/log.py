"""
pyhids.log —— 统一的日志配置
"""
from __future__ import annotations

import logging
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """初始化 root logger 的格式和级别。

    log_file 不为空时**额外**写一份到文件。App 模式必须给这个参数 —— 双击启动
    没有终端，stdout 直接进虚空，出问题只能靠日志文件排查。
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
        # 不加 force，第二次调用会被 basicConfig 静默忽略（它发现已有 handler
        # 就直接返回），App 模式想补的文件 handler 就永远加不上
        force=True,
    )