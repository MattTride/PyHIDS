"""
pyhids.ssh_check —— SSH 暴破检测
"""
from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from collections import defaultdict
from datetime import timedelta
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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