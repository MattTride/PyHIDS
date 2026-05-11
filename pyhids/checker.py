"""
pyhids.checker — 文件变化检测模块

职责：把"当前系统状态"和"基线 baseline.json"对比，
     找出哪些文件被改动、删除、新增。
"""
from __future__ import annotations
from pyhids.store import Event

import json
from datetime import datetime
from pathlib import Path

from pyhids.config import Config, load_config
from pyhids.baseline import build_baseline, DEFAULT_BASELINE_PATH

def load_baseline(path: str | Path = DEFAULT_BASELINE_PATH) -> dict:
    """从JSON文件读取出基线字典"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在：{path}")


def compare_baselines(old_baseline: dict, new_baseline: dict) -> dict:
    """对比两份基线，返回差异报告"""
    old_files = set(old_baseline["files"].keys())
    new_files = set(new_baseline["files"].keys())

    added_set = new_files - old_files
    deleted_set = old_files - new_files
    common_set = old_files & new_files

    modified = []
    for file_path in common_set:
        old_hash = old_baseline["files"][file_path]["hash"]
        new_hash = new_baseline["files"][file_path]["hash"]
        if old_hash != new_hash:
            modified.append(file_path)

    unchanged = [f for f in common_set if f not in modified]
    return {
        "modified": modified,
        "deleted": list(deleted_set),  # set 转 list（JSON 不支持 set）
        "added": list(added_set),
        "unchanged": unchanged,
        "summary": {
            "total_checked": len(old_files | new_files),
            "total_issues": len(modified) + len(deleted_set) + len(added_set),
            "checked_at": datetime.now().isoformat()
        }
    }


def check(cfg: Config, baseline_path: str | Path = DEFAULT_BASELINE_PATH) -> dict:
    """加载旧的基线 + 扫取当前状态 + 对比 + 返回报告"""
    old_baseline = load_baseline(baseline_path)
    new_baseline = build_baseline(cfg)
    report = compare_baselines(old_baseline, new_baseline)
    return report


def output_report(report: dict) -> None:
    """把一份检查报告以人类可读的形式打印到 stdout。"""
    summary = report["summary"]
    print(f"\n{'=' * 50}")
    print(f"  PyHIDS 完整性检查报告")
    print(f"{'=' * 50}")
    print(f"检查时间: {summary['checked_at']}")
    print(f"扫描文件: {summary['total_checked']}")
    print(f"发现问题: {summary['total_issues']}")
    print(f"{'=' * 50}\n")

    if report["modified"]:
        print(f"⚠️  被修改的文件 ({len(report['modified'])}):")
        for f in report["modified"]:
            print(f"   - {f}")
        print()

    if report["deleted"]:
        print(f"❌ 被删除的文件 ({len(report['deleted'])}):")
        for f in report["deleted"]:
            print(f"   - {f}")
        print()

    if report["added"]:
        print(f"➕ 新增的文件 ({len(report['added'])}):")
        for f in report["added"]:
            print(f"   - {f}")
        print()

    if summary["total_issues"] == 0:
        print("✅ 一切正常，未发现异常。\n")
    else:
        print(f"🚨 发现 {summary['total_issues']} 个异常，请立即检查！\n")


def event_from_file_change(change_type: str, file_path: str) -> Event:
    """把一条FIM变化转化成Event"""
    severity = "critical" if change_type in ("modified", "deleted") else "warning"
    return Event(
        detected_at=datetime.now(),
        source="file_integrity",
        severity=severity,
        summary=f"{file_path} {change_type}",
        payload={"file_path": file_path, "change": change_type}
    )

if __name__ == "__main__":
    cfg = load_config()
    report = check(cfg)
    output_report(report)