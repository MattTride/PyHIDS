"""
pyhids.cli — 命令行入口模块

职责:解析用户在终端输入的命令和参数,调度 baseline / checker 模块。
"""
from __future__ import annotations

import argparse

from pyhids.baseline import build_baseline, save_baseline
from pyhids.config import load_config
from pyhids.checker import check


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyhids",
        description="PyHIDS - 轻量级主机入侵检测系统",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_baseline = subparsers.add_parser("baseline", help="生成文件指纹基线", )
    parser_baseline.add_argument("--config", type=str, default=None, help="默认文件路径(config/watchlist.yaml)")
    parser_baseline.add_argument("--baseline", type=str, default=None, help="基线保存路径(data/baseline.json)")

    parser_check = subparsers.add_parser("check", help="检查文件完整性", )
    parser_check.add_argument("--config", type=str, default=None, help="默认文件路径(config/watchlist.yaml)")
    parser_check.add_argument("--baseline", type=str, default=None, help="基线保存路径(data/baseline.json)")

    args = parser.parse_args()

    if args.command == "baseline":
        if args.config is None:
            cfg = load_config()
        else:
            cfg = load_config(args.config)

        baseline = build_baseline(cfg)
        if args.baseline is None:
            save_baseline(baseline)
        else:
            save_baseline(baseline, args.baseline)

        print(f"基线已经保存，一共{baseline['metadata']["total_files"]}个文件")


if __name__ == "__main__":
    main()
