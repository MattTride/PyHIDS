"""
pyhids.ssh_check —— SSH 暴破检测
"""
from __future__ import annotations

from asyncio import events
from collections import defaultdict
from datetime import timedelta
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path

import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class SSHEvent:
    timestamp: datetime
    ip: str
    user: str
    result: str #"Fail or Success"

SSH_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})"
    r"\s+\S+\s+"
    r"sshd\[\d+\]:\s+"
    r"(?P<result>Failed|Accepted)\s+password\s+for\s+"
    r"(?:invalid\s+user\s+)?"
    r"(?P<user>\S+)\s+"
    r"from\s+(?P<ip>\S+)\s+"
    r"port\s+\d+\s+ssh2"
)

def parse_log_line(line: str) -> Optional[SSHEvent]:
    """
    解析一行 sshd 日志。

    Args:
        line: 一行文本，可能是 SSH 登录事件，也可能是别的东西

    Returns:
        SSHEvent 实例（成功解析）；None（不是 SSH 登录事件，或格式不认识）
    """
    match = SSH_LOG_PATTERN.match(line)
    if match is None:
        return None

    timestamp = match.group("timestamp")
    ip = match.group("ip")
    user = match.group("user")
    raw_result = match.group("result")

    clean_timestamp = " ".join(timestamp.split())
    parsed_time = datetime.strptime(clean_timestamp, "%b %d %H:%M:%S")
    current_year = datetime.now().year
    timestamp_str = parsed_time.replace(year=current_year)

    result = "success" if raw_result == "Accepted" else "fail"

    return SSHEvent(timestamp=timestamp_str, ip=ip, user=user, result=result)


@dataclass
class BruteForceAttempt:
    ip: str
    fail_count: int
    window_start: datetime
    window_end: datetime
    # ← 类定义到这就结束了，下面是空行


def detect_brute_force(
        events: list[SSHEvent],
        window_seconds: int = 60,
        threshold: int = 5,
) -> list[BruteForceAttempt]:
    fails_by_ip = defaultdict(list)
    for event in events:
        if event.result == "fail":
            fails_by_ip[event.ip].append(event.timestamp)

    detected = []
    for ip, timestamps in fails_by_ip.items():
        timestamps.sort()
        window = timedelta(seconds=window_seconds)
        for i in range(len(timestamps)):
            window_end = timestamps[i]
            window_start = window_end - window
            count = sum(1 for t in timestamps if window_start <= t <= window_end)
            if count >= threshold:
                detected.append(BruteForceAttempt(
                    ip=ip,
                    fail_count=count,
                    window_start=window_start,
                    window_end=window_end,
                ))
                break
    return detected

def parse_log_file(path: str | Path) -> list[SSHEvent]:
    """逐行读取sshd日志文件，返回所有可以识别的SSH事件。"""
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            event = parse_log_line(line)
            if event is not None:
                events.append(event)

    logger.info("从 %s 解析出 %d 个SSH事件", path, len(events))
    return events

def check_ssh(
        log_path: str | Path,
        window_seconds: int = 60,
        threshold: int = 5,
) -> dict:
    """读 auth.log → 检测暴破 → 打包成 report dict"""
    events = parse_log_file(log_path)
    attempts = detect_brute_force(events, window_seconds, threshold)
    return {
        "attempts": attempts,
        "summary": {
            "total_events": len(events),
            "total_attempts": len(attempts),
            "window_seconds": window_seconds,
            "threshold": threshold,
            "checked_at": datetime.now().isoformat(),
        },
    }


def print_ssh_report(report: dict) -> None:
    """把 SSH 检测报告打印到 stdout。"""
    summary = report["summary"]

    print(f"\n{'=' * 50}")
    print(f"  PyHIDS SSH 暴破检测报告")
    print(f"{'=' * 50}")
    print(f"检查时间: {summary['checked_at']}")
    print(f"扫描事件: {summary['total_events']}")
    print(f"窗口阈值: {summary['threshold']} 次 / {summary['window_seconds']} 秒")
    print(f"检测到攻击: {summary['total_attempts']}")
    print(f"{'=' * 50}\n")

    if summary["total_attempts"] == 0:
        print("未检检测到SSH爆破嫌疑。 \n")
    else:
        for attempt in report["attempts"]:
            print("爆破嫌疑！\n")
            print(f"ip:{attempt.ip}: {attempt.fail_count}次失败")
            print(f"窗口：{attempt.window_start} -> {attempt.window_end}")
