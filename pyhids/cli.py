"""
pyhids.cli — 命令行入口模块

职责:解析用户在终端输入的命令和参数,调度 baseline / checker 模块。
"""
from __future__ import annotations

import argparse
import sys

from datetime import datetime, timedelta
from pyhids.store import query_events, print_events_table, init_db, insert_event
from pyhids.log import setup_logging
from pyhids.baseline import build_baseline, save_baseline
from pyhids.config import load_config
from pyhids.checker import check, output_report, event_from_file_change
from pyhids.ssh_check import check_ssh, print_ssh_report, event_from_brute_force
from pyhids.alert import alert_if_critical
from pyhids.store import dedup_key, dedup_keys_since



def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pyhids",
        description="PyHIDS - 轻量级主机入侵检测系统",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别（默认 INFO）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ================== 窗口 A：baseline 业务 ==================
    parser_baseline = subparsers.add_parser("baseline", help="生成文件指纹基线", )
    parser_baseline.add_argument("--config", type=str, default=None, help="默认文件路径(config/watchlist.yaml)")
    parser_baseline.add_argument("--baseline", type=str, default=None, help="基线保存路径(data/baseline.json)")

    # ================== 窗口 B：check 业务 ==================
    parser_check = subparsers.add_parser("check", help="检查文件完整性", )
    parser_check.add_argument("--config", type=str, default=None, help="默认文件路径(config/watchlist.yaml)")
    parser_check.add_argument("--baseline", type=str, default=None, help="基线保存路径(data/baseline.json)")
    # ================== 窗口 C：ssh-check 业务 ==================
    parser_ssh = subparsers.add_parser("ssh-check", help="SSH爆破检测")
    parser_ssh.add_argument("--config", type=str, default=None, help="配置文件路径(config/watchlist.yaml)")
    parser_ssh.add_argument("--log-path", type=str, default=None, help="auth.log 路径（覆盖 watchlist.yaml 里的 ssh.log_path）")
    # ================== 窗口 D：events 业务 ==================
    parser_events = subparsers.add_parser("events", help="查询历史事件")
    parser_events.add_argument("--limit", type=int, default=50, help="最多显示条数（默认 50）")
    parser_events.add_argument("--source", type=str, default=None,help="按事件源过滤（file_integrity / ssh_brute_force）")
    # ================== 窗口 E：serve 业务 ==================
    parser_serve = subparsers.add_parser("serve", help="启动 Web 仪表盘")
    parser_serve.add_argument("--host", type=str, default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser_serve.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")

    args = parser.parse_args()
    setup_logging(args.log_level)
    init_db()

    # 【分支 A】：如果用户终端输入的是 `python cli.py baseline
    if args.command == "baseline":
        if args.config is None:
            cfg = load_config()
        else:
            cfg = load_config(args.config)

    #使用baseline干活，生成基线字典
        baseline = build_baseline(cfg)

    #使用baseline干活，保存到硬盘
        if args.baseline is None:
            save_baseline(baseline)
        else:
            save_baseline(baseline, args.baseline)

        print(f"基线已经保存，一共{baseline['metadata']['total_files']}个文件")

    # 【分支 B】：如果用户终端输入的是 `python cli.py check
    elif args.command == "check":
        if args.config is None:
            cfg = load_config()
        else:
            cfg = load_config(args.config)

    #使用check干活
        if args.baseline is None:
            report = check(cfg)
        else:
            report = check(cfg, baseline_path=args.baseline)

        output_report(report)

        # 把每个 FIM 变化落库；告警前先按窗口去重
        cutoff = datetime.now() - timedelta(seconds=cfg.alert.dedup_window_seconds)
        seen = dedup_keys_since(cutoff)
        for change_type in ("modified", "deleted", "added"):
            for file_path in report[change_type]:
                event = event_from_file_change(change_type, file_path)
                insert_event(event)
                if dedup_key(event) not in seen:
                    alert_if_critical(event, cfg.alert.dingtalk_webhook)


        if report["summary"]["total_issues"] > 0:
            sys.exit(1)

    elif args.command == "ssh-check":
        if args.config is None:
            cfg = load_config()
        else:
            cfg = load_config(args.config)

        log_path = args.log_path or cfg.ssh.log_path

        report = check_ssh(
            log_path,
            window_seconds=cfg.ssh.window_seconds,
            threshold=cfg.ssh.threshold,
        )

        print_ssh_report(report)

        # 把每个暴破嫌疑落库，并触发告警
        cutoff = datetime.now() - timedelta(seconds=cfg.alert.dedup_window_seconds)
        seen = dedup_keys_since(cutoff)
        for attempt in report["attempts"]:
            event = event_from_brute_force(attempt)
            insert_event(event)
            if dedup_key(event) not in seen:
                alert_if_critical(event, cfg.alert.dingtalk_webhook)

        if report["summary"]["total_attempts"] > 0:
            sys.exit(1)

    elif args.command == "events":
        events = query_events(limit=args.limit, source=args.source)
        print_events_table(events)

    elif args.command == "serve":
        import uvicorn
        print(f"启动仪表盘 http://{args.host}:{args.port} （Ctrl+C 退出）")
        uvicorn.run("pyhids.web:app", host=args.host, port=args.port)

if __name__ == "__main__":
    main()
