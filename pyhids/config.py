"""
pyhids.config — 配置加载模块

职责：读取 watchlist.yaml，转成 Python 对象，校验合法性。
"""
from __future__ import annotations

import os

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

DEFAULT_CONFIG_PATH = Path(os.getenv("PYHIDS_CONFIG_PATH", "config/watchlist.yaml"))


@dataclass
class SSHConfig:
    """SSH 爆破检测的配置子结构。"""
    log_path: str = "/var/log/auth.log"
    window_seconds: int = 60
    threshold: int = 5

@dataclass
class AlertConfig:
    """告警渠道设置"""
    dingtalk_webhook: str = ""
    dedup_window_seconds: int = 3600
    email_host: str = ""
    email_port: int = 587
    email_user: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: str = ""


@dataclass
class Config:
    algorithm: str = "sha256"
    paths: List[str] = field(default_factory=list)
    scan_interval: int = 60
    ssh: SSHConfig = field(default_factory=SSHConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)


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
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")

    # 第 4 步：处理空文件的边界情况
    if data is None:
        data = {}

    # 第 5 步：把 ssh 子字典转成 SSHConfig 实例
    # （YAML 加载出来的 ssh 字段是普通 dict，需要手动构造成 dataclass）
    alert_data = data.pop("alert", {})
    data["alert"] = AlertConfig(**alert_data)

    ssh_data = data.pop("ssh", {})
    data["ssh"] = SSHConfig(**ssh_data)

    # 第 6 步：把字典转成 Config 对象
    return Config(**data)


if __name__ == "__main__":
    cfg = load_config()
    print(f"算法: {cfg.algorithm}")
    print(f"监控路径 ({len(cfg.paths)} 个):")
    for p in cfg.paths:
        print(f"  - {p}")
    print(f"扫描间隔: {cfg.scan_interval}s")
    print(f"SSH 配置:")
    print(f"  log_path:       {cfg.ssh.log_path}")
    print(f"  window_seconds: {cfg.ssh.window_seconds}")
    print(f"  threshold:      {cfg.ssh.threshold}")
    print(f"告警webhook:       {cfg.alert.dingtalk_webhook or '(未配置)'}" )
