"""
pyhids.config — 配置加载模块

职责：读取 watchlist.yaml，转成 Python 对象，校验合法性。
"""
from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(os.getenv("PYHIDS_CONFIG_PATH", "config/watchlist.yaml"))


@dataclass
class SSHConfig:
    """SSH 爆破检测的配置子结构。"""
    log_path: str = "/var/log/auth.log"
    window_seconds: int = 60
    threshold: int = 5

@dataclass
class SudoConfig:
    """sudo / su 提权滥用检测的配置子结构。"""
    log_path: str = "/var/log/auth.log"
    window_seconds: int = 60
    threshold: int = 3

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
    paths: list[str] = field(default_factory=list)
    scan_interval: int = 60
    ssh: SSHConfig = field(default_factory=SSHConfig)
    sudo: SudoConfig = field(default_factory=SudoConfig)
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

    if not isinstance(data, Mapping):
        raise ValueError("配置文件顶层必须是键值映射")

    data = dict(data)

    def load_section(name: str, config_type: type):
        section = data.pop(name, {})
        if section is None:
            section = {}
        if not isinstance(section, Mapping):
            raise ValueError(f"配置项 {name} 必须是键值映射")
        try:
            return config_type(**section)
        except TypeError as e:
            raise ValueError(f"配置项 {name} 包含未知或无效字段: {e}") from e

    # 第 5 步：把 ssh 子字典转成 SSHConfig 实例
    # （YAML 加载出来的 ssh 字段是普通 dict，需要手动构造成 dataclass）
    data["alert"] = load_section("alert", AlertConfig)
    data["ssh"] = load_section("ssh", SSHConfig)
    data["sudo"] = load_section("sudo", SudoConfig)

    # 第 6 步：把字典转成 Config 对象
    try:
        cfg = Config(**data)
    except TypeError as e:
        raise ValueError(f"配置文件包含未知或无效字段: {e}") from e

    if not isinstance(cfg.paths, list) or not all(isinstance(item, str) for item in cfg.paths):
        raise ValueError("配置项 paths 必须是字符串列表")
    try:
        hasher = hashlib.new(cfg.algorithm)
        # SHAKE 等可变长度摘要要求 hexdigest(length)，当前哈希接口不支持。
        hasher.hexdigest()
    except (TypeError, ValueError) as e:
        raise ValueError(f"未知或不支持的哈希算法: {cfg.algorithm}") from e

    positive_values = {
        "scan_interval": cfg.scan_interval,
        "ssh.window_seconds": cfg.ssh.window_seconds,
        "ssh.threshold": cfg.ssh.threshold,
        "sudo.window_seconds": cfg.sudo.window_seconds,
        "sudo.threshold": cfg.sudo.threshold,
    }
    for name, value in positive_values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"配置项 {name} 必须是正整数")

    dedup_window = cfg.alert.dedup_window_seconds
    if isinstance(dedup_window, bool) or not isinstance(dedup_window, int) or dedup_window < 0:
        raise ValueError("配置项 alert.dedup_window_seconds 必须是非负整数")
    email_port = cfg.alert.email_port
    if isinstance(email_port, bool) or not isinstance(email_port, int) or not 1 <= email_port <= 65535:
        raise ValueError("配置项 alert.email_port 必须是 1 到 65535 之间的整数")

    return cfg


if __name__ == "__main__":
    cfg = load_config()
    print(f"算法: {cfg.algorithm}")
    print(f"监控路径 ({len(cfg.paths)} 个):")
    for p in cfg.paths:
        print(f"  - {p}")
    print(f"扫描间隔: {cfg.scan_interval}s")
    print("SSH 配置:")
    print(f"  log_path:       {cfg.ssh.log_path}")
    print(f"  window_seconds: {cfg.ssh.window_seconds}")
    print(f"  threshold:      {cfg.ssh.threshold}")
    print("sudo 配置:")
    print(f"  log_path:       {cfg.sudo.log_path}")
    print(f"  window_seconds: {cfg.sudo.window_seconds}")
    print(f"  threshold:      {cfg.sudo.threshold}")
    print(f"告警webhook:       {cfg.alert.dingtalk_webhook or '(未配置)'}" )
