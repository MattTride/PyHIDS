"""
pyhids.baseline — 基线生成与持久化模块

职责：根据配置扫描所有监控文件，生成"指纹快照"，保存到 JSON。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pyhids.config import Config, DEFAULT_CONFIG_PATH, load_config
from pyhids.hasher import hash_file

DEFAULT_BASELINE_PATH = Path("data/baseline.json")
BASELINE_VERSION = "1.0"

def build_baseline(cfg: Config) -> dict:
    ...



def save_baseline(baseline: dict, path: str | Path = DEFAULT_BASELINE_PATH) -> None:
    ...


if __name__ == "__main__":
    from pyhids.config import Config
    cfg = load_config()
    baseline = build_baseline(cfg)
    save_baseline(baseline)
    print(f"✅ 基线已保存，共 {baseline['metadata']['total_files']} 个文件")
