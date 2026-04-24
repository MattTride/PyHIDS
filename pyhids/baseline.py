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
    """
    根据配置扫描所有监控文件，生成基线字典。

    Args:
        cfg: 配置对象，从 watchlist.yaml 加载而来

    Returns:
        基线字典，结构为 {"metadata": {...}, "files": {...}}
    """
    #初始化字典，用来存储文件的指纹信息
    files_info = {}

    #遍历文件里的监控路径
    for file_path in cfg.paths:
        path = Path(file_path)
        file_hash = hash_file(path, algorithm=cfg.algorithm)

        if file_hash is None:
            print(f"跳过文件：{file_path}")
            continue

        #获得文件大小，然后塞进info字典
        file_size = path.stat().st_size
        files_info[file_path] = {
            "hash": file_hash,
            "size": file_size
        }

    #构建metadata部分
    metadata = {
        "version": BASELINE_VERSION,
        "created_at": datetime.now().isoformat(),
        "algorithm": cfg.algorithm,
        "total_files": len(files_info)
    }

    #组装字典，然后返回
    baseline = {
        "metadata": metadata,
        "files": files_info
    }

    return baseline


def save_baseline(baseline: dict, path: str | Path = DEFAULT_BASELINE_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    print(f"基线已经保存到{path}")


if __name__ == "__main__":
    from pyhids.config import Config
    cfg = load_config()
    baseline = build_baseline(cfg)
    save_baseline(baseline)
    print(f"✅ 基线已保存，共 {baseline['metadata']['total_files']} 个文件")
