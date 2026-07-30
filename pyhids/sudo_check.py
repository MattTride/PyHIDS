"""
pyhids.sudo_check —— sudo / su 提权滥用检测

和 ssh_check 同构：解析 auth.log → 找出可疑模式 → 打包 report → 转 Event。
两类可疑行为：
  1. 提权失败风暴：同一用户在时间窗内多次认证失败（猜 sudo 密码）
  2. 非授权提权：用户根本不在 sudoers 里却尝试提权 —— 一次就够可疑，不看阈值
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pyhids.store import Event

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SECONDS = 60
DEFAULT_THRESHOLD = 3


@dataclass
class SudoEvent:
    timestamp: datetime
    user: str
    kind: str      # "sudo" | "su"
    result: str    # "fail" | "success"
    reason: str    # "auth_failure" | "not_in_sudoers" | "failed_su" | "command"
    target: str | None = None   # 提权到哪个用户（成功的 sudo/su）
    command: str | None = None  # 执行了什么命令（成功的 sudo）


# 时间戳前缀：`Jul 30 10:00:01 hostname `
_PREFIX = r"^(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+\S+\s+"

# 1) PAM 认证失败（sudo 和 su 共用同一种格式）
#    Jul 30 10:00:01 host sudo: pam_unix(sudo:auth): authentication failure; logname=bob uid=1000 ...
PAM_FAILURE_PATTERN = re.compile(
    _PREFIX
    + r"(?P<kind>sudo|su)(?:\[\d+\])?:\s+"
    + r"pam_unix\((?:sudo|su):auth\):\s+authentication failure;.*?\blogname=(?P<user>\S+)"
)

# 2) 用户不在 sudoers 名单里
#    Jul 30 10:02:00 host sudo:      eve : user NOT in sudoers ; TTY=pts/0 ; ...
NOT_IN_SUDOERS_PATTERN = re.compile(
    _PREFIX + r"sudo(?:\[\d+\])?:\s+(?P<user>\S+)\s*:\s+user NOT in sudoers"
)

# 3) su 切换失败
#    Jul 30 10:03:10 host su: FAILED SU (to root) bob on pts/0
FAILED_SU_PATTERN = re.compile(
    _PREFIX + r"su(?:\[\d+\])?:\s+FAILED SU\s+\(to (?P<target>\S+)\)\s+(?P<user>\S+)"
)

# 4) sudo 成功执行命令（只记录，不告警 —— 和 ssh_check 解析 Accepted 但只检测 fail 一致）
#    Jul 30 10:01:00 host sudo:      bob : TTY=pts/0 ; PWD=/home/bob ; USER=root ; COMMAND=/usr/bin/apt update
SUDO_COMMAND_PATTERN = re.compile(
    _PREFIX
    + r"sudo(?:\[\d+\])?:\s+(?P<user>\S+)\s*:\s+TTY=\S*\s*;\s*PWD=\S*\s*;\s*"
    # USER= 不是所有发行版都记，做成可选
    + r"(?:USER=(?P<target>\S+)\s*;\s*)?COMMAND=(?P<command>.+?)\s*$"
)


def _parse_timestamp(raw: str) -> datetime:
    """syslog 时间戳没有年份，拼上当前年份再解析（否则 strptime 默认 1900）。"""
    clean = " ".join(raw.split())
    return datetime.strptime(f"{datetime.now().year} {clean}", "%Y %b %d %H:%M:%S")


def parse_log_line(line: str) -> Optional[SudoEvent]:
    """解析一行 auth.log。不是 sudo/su 事件就返回 None。

    注意：`N incorrect password attempts` 那种汇总行**故意不解析** —— 每次失败
    本来就有一条 pam_unix 记录，再算一次会重复计数。
    """
    match = NOT_IN_SUDOERS_PATTERN.match(line)
    if match:
        return SudoEvent(
            timestamp=_parse_timestamp(match.group("timestamp")),
            user=match.group("user"),
            kind="sudo",
            result="fail",
            reason="not_in_sudoers",
        )

    match = FAILED_SU_PATTERN.match(line)
    if match:
        return SudoEvent(
            timestamp=_parse_timestamp(match.group("timestamp")),
            user=match.group("user"),
            kind="su",
            result="fail",
            reason="failed_su",
            target=match.group("target"),
        )

    match = PAM_FAILURE_PATTERN.match(line)
    if match:
        return SudoEvent(
            timestamp=_parse_timestamp(match.group("timestamp")),
            user=match.group("user"),
            kind=match.group("kind"),
            result="fail",
            reason="auth_failure",
        )

    match = SUDO_COMMAND_PATTERN.match(line)
    if match:
        return SudoEvent(
            timestamp=_parse_timestamp(match.group("timestamp")),
            user=match.group("user"),
            kind="sudo",
            result="success",
            reason="command",
            target=match.group("target"),
            command=match.group("command"),
        )

    return None


@dataclass
class PrivilegeAbuse:
    user: str
    kind: str            # "burst"（失败风暴）| "not_in_sudoers"（非授权提权）
    fail_count: int
    window_start: datetime
    window_end: datetime


def detect_privilege_abuse(
        events: list[SudoEvent],
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        threshold: int = DEFAULT_THRESHOLD,
) -> list[PrivilegeAbuse]:
    """找出提权失败风暴 + 非授权提权尝试。"""
    detected: list[PrivilegeAbuse] = []

    # ── 1) 非授权提权：一次就报，不看阈值 ──
    for event in events:
        if event.reason == "not_in_sudoers":
            detected.append(PrivilegeAbuse(
                user=event.user,
                kind="not_in_sudoers",
                fail_count=1,
                window_start=event.timestamp,
                window_end=event.timestamp,
            ))

    # ── 2) 失败风暴：滑动窗口，逻辑与 detect_brute_force 一致 ──
    fails_by_user = defaultdict(list)
    for event in events:
        if event.result == "fail" and event.reason != "not_in_sudoers":
            fails_by_user[event.user].append(event.timestamp)

    window = timedelta(seconds=window_seconds)
    for user, timestamps in fails_by_user.items():
        timestamps.sort()
        for window_end in timestamps:
            window_start = window_end - window
            in_window = [t for t in timestamps if window_start <= t <= window_end]
            if len(in_window) >= threshold:
                detected.append(PrivilegeAbuse(
                    user=user,
                    kind="burst",
                    fail_count=len(in_window),
                    window_start=min(in_window),
                    window_end=window_end,
                ))
                break

    return detected


def parse_log_file(path: str | Path) -> list[SudoEvent]:
    """逐行读取 auth.log，返回所有能识别的 sudo/su 事件。"""
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            event = parse_log_line(line)
            if event is not None:
                events.append(event)

    logger.info("从 %s 解析出 %d 个 sudo/su 事件", path, len(events))
    return events


def check_sudo(
        log_path: str | Path,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        threshold: int = DEFAULT_THRESHOLD,
) -> dict:
    """读 auth.log → 检测提权滥用 → 打包成 report dict。"""
    events = parse_log_file(log_path)
    abuses = detect_privilege_abuse(events, window_seconds, threshold)
    return {
        "abuses": abuses,
        "summary": {
            "total_events": len(events),
            "total_abuses": len(abuses),
            "window_seconds": window_seconds,
            "threshold": threshold,
            "checked_at": datetime.now().isoformat(),
        },
    }


def print_sudo_report(report: dict) -> None:
    """把提权检测报告打印到 stdout。"""
    summary = report["summary"]

    print(f"\n{'=' * 50}")
    print(f"  PyHIDS 提权滥用检测报告")
    print(f"{'=' * 50}")
    print(f"检查时间: {summary['checked_at']}")
    print(f"扫描事件: {summary['total_events']}")
    print(f"窗口阈值: {summary['threshold']} 次 / {summary['window_seconds']} 秒")
    print(f"检测到滥用: {summary['total_abuses']}")
    print(f"{'=' * 50}\n")

    if summary["total_abuses"] == 0:
        print("✅ 未检测到提权滥用。\n")
        return

    for abuse in report["abuses"]:
        if abuse.kind == "not_in_sudoers":
            print(f"🚨 非授权提权！用户 {abuse.user} 不在 sudoers 名单里")
            print(f"   时间：{abuse.window_end}\n")
        else:
            print(f"⚠️  提权失败风暴！用户 {abuse.user}：{abuse.fail_count} 次失败")
            print(f"   窗口：{abuse.window_start} → {abuse.window_end}\n")


def event_from_privilege_abuse(abuse: PrivilegeAbuse) -> Event:
    """把一个 PrivilegeAbuse 转成 Event。"""
    if abuse.kind == "not_in_sudoers":
        summary = f"{abuse.user} 非授权提权尝试（不在 sudoers 名单）"
    else:
        summary = (f"{abuse.user} 提权失败风暴（{abuse.fail_count} 次 / "
                   f"窗口 {abuse.window_start} → {abuse.window_end}）")

    return Event(
        detected_at=datetime.now(),
        source="privilege_escalation",
        severity="critical",
        summary=summary,
        payload={
            "user": abuse.user,
            "kind": abuse.kind,
            "fail_count": abuse.fail_count,
            "window_start": abuse.window_start.isoformat(),
            "window_end": abuse.window_end.isoformat(),
        },
    )
