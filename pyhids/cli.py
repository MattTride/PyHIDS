"""
pyhids.cli — 命令行入口模块

职责:解析用户在终端输入的命令和参数,调度 baseline / checker 模块。
"""
from __future__ import annotations

import argparse

from pyhids.baseline import build_baseline, save_baseline
from pyhids.config import load_config
from pyhids.checker import check

def main():
    parser = argparse.ArgumentParser(
        prog="pyhids",
        description="PyHIDS - 轻量级主机入侵检测系统",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    atg = parser.parse_args()

    if __name__ == "__main__":
        main()