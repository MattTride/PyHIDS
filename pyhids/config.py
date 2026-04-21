"""
pyhids.config — 配置加载模块

职责：读取 watchlist.yaml，转成 Python 对象，校验合法性。
"""
from __future__ import annotations

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


DEFAULT_CONFIG_PATH = Path("config/watchlist.yaml")


@dataclass
class Config:
    algorithm: str = "sha256"
    paths: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    scan_interval: int = 60


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """
    从 YAML 文件加载配置。

    Args:
        path: 配置文件路径

    Returns:
        Config 对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置文件格式错误
    """
    # 第 1 步：统一转成 Path 对象
    path = Path(path)

    # 第 2 步：Fail-Fast 检查 - 文件不存在就立刻抛异常
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    # 第 3 步：打开并解析 YAML
    # 用 "r" 文本模式 + utf-8 编码（YAML 是文本，不是二进制）
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        # YAML 语法错误（比如缩进不对、冒号后没空格）
        raise ValueError(f"配置文件格式错误: {e}")

    # 第 4 步：处理空文件的边界情况
    # 如果 YAML 文件是空的，safe_load 返回 None，不是空字典
    # 这种情况我们让它用全部默认值
    if data is None:
        data = {}

    # 第 5 步：把字典转成 Config 对象
    return Config(**data)


if __name__ == "__main__":
    # 自测
    cfg = load_config()
    print(f"算法: {cfg.algorithm}")
    print(f"监控路径 ({len(cfg.paths)} 个):")
    for p in cfg.paths:
        print(f"  - {p}")
    print(f"排除规则: {cfg.exclude}")
    print(f"扫描间隔: {cfg.scan_interval}s")