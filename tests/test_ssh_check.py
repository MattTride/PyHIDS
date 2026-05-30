"""
pyhids.ssh_check 的测试套件
"""
from datetime import datetime, timedelta
from pyhids.store import Event

import pytest

from pyhids.ssh_check import (
    SSHEvent,
    parse_log_line,
    parse_log_file,
    detect_brute_force,
    check_ssh,
    BruteForceAttempt,
    event_from_brute_force,
)


# ============================================================
# parse_log_line
# ============================================================

def test_parse_log_line_failed_existing_user():
    line = "May  8 10:15:32 server sshd[1234]: Failed password for admin from 192.168.1.50 port 54321 ssh2"
    event = parse_log_line(line)
    assert event is not None
    assert event.ip == "192.168.1.50"
    assert event.user == "admin"
    assert event.result == "fail"


def test_parse_log_line_failed_invalid_user():
    line = "May  8 10:15:35 server sshd[1234]: Failed password for invalid user nouser from 10.0.0.99 port 41234 ssh2"
    event = parse_log_line(line)
    assert event is not None
    assert event.ip == "10.0.0.99"
    assert event.user == "nouser"
    assert event.result == "fail"


def test_parse_log_line_accepted():
    line = "May  8 10:16:02 server sshd[1234]: Accepted password for ubuntu from 10.0.0.5 port 22000 ssh2"
    event = parse_log_line(line)
    assert event is not None
    assert event.ip == "10.0.0.5"
    assert event.user == "ubuntu"
    assert event.result == "success"


def test_parse_log_line_returns_none_for_non_ssh():
    line = "May  8 10:20:00 server sudo: ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; COMMAND=/bin/ls"
    assert parse_log_line(line) is None


def test_parse_log_line_returns_none_for_empty_string():
    assert parse_log_line("") is None


# ============================================================
# detect_brute_force
# ============================================================

def _make_fail_events(ip: str, count: int, interval_seconds: int) -> list[SSHEvent]:
    """造 count 个 fail 事件，每个间隔 interval_seconds 秒。"""
    base = datetime(2026, 5, 8, 10, 0, 0)
    return [
        SSHEvent(
            timestamp=base + timedelta(seconds=i * interval_seconds),
            ip=ip,
            user="x",
            result="fail",
        )
        for i in range(count)
    ]


def test_detect_brute_force_no_events():
    assert detect_brute_force([]) == []


def test_detect_brute_force_below_threshold():
    events = _make_fail_events("1.1.1.1", count=3, interval_seconds=5)
    assert detect_brute_force(events, window_seconds=60, threshold=5) == []


def test_detect_brute_force_at_threshold_triggers():
    events = _make_fail_events("1.2.3.4", count=5, interval_seconds=5)
    result = detect_brute_force(events, window_seconds=60, threshold=5)
    assert len(result) == 1
    assert result[0].ip == "1.2.3.4"
    assert result[0].fail_count == 5


def test_detect_brute_force_slow_attack_does_not_trigger():
    # 5 次失败 + 每次间隔 30s → 总跨度 120s，超出 60s 窗口
    events = _make_fail_events("9.9.9.9", count=5, interval_seconds=30)
    assert detect_brute_force(events, window_seconds=60, threshold=5) == []

def test_detect_brute_force_window_start_is_first_failure():
    events = _make_fail_events("1.2.3.4", count=5, interval_seconds=5)
    result = detect_brute_force(events, window_seconds=60, threshold=5)

    assert len(result) == 1
    assert result[0].window_start == datetime(2026, 5, 8, 10, 0, 0)


# ============================================================
# parse_log_file
# ============================================================

def test_parse_log_file_filters_non_ssh_lines(tmp_path):
    log_path = tmp_path / "auth.log"
    log_path.write_text(
        "May  8 09:55:01 server CRON[12345]: pam_unix(cron:session): session opened\n"
        "May  8 10:00:00 server sshd[1001]: Failed password for admin from 1.2.3.4 port 50001 ssh2\n"
        "May  8 10:05:00 server sudo: ubuntu : TTY=pts/0\n"
        "May  8 10:01:00 server sshd[1002]: Accepted password for ubuntu from 10.0.0.5 port 22 ssh2\n"
    )
    events = parse_log_file(log_path)
    assert len(events) == 2
    ips = {ev.ip for ev in events}
    assert ips == {"1.2.3.4", "10.0.0.5"}


# ============================================================
# check_ssh（集成测试）
# ============================================================

def test_check_ssh_returns_complete_report(tmp_path):
    log_path = tmp_path / "auth.log"
    log_path.write_text(
        "May  8 10:00:00 server sshd[1001]: Failed password for admin from 1.2.3.4 port 50001 ssh2\n"
        "May  8 10:00:05 server sshd[1002]: Failed password for admin from 1.2.3.4 port 50002 ssh2\n"
        "May  8 10:00:10 server sshd[1003]: Failed password for admin from 1.2.3.4 port 50003 ssh2\n"
        "May  8 10:00:15 server sshd[1004]: Failed password for admin from 1.2.3.4 port 50004 ssh2\n"
        "May  8 10:00:20 server sshd[1005]: Failed password for admin from 1.2.3.4 port 50005 ssh2\n"
    )

    report = check_ssh(log_path, window_seconds=60, threshold=5)

    assert report["summary"]["total_events"] == 5
    assert report["summary"]["total_attempts"] == 1
    assert report["summary"]["window_seconds"] == 60
    assert report["summary"]["threshold"] == 5
    assert len(report["attempts"]) == 1
    assert report["attempts"][0].ip == "1.2.3.4"
    assert report["attempts"][0].fail_count == 5

def test_event_from_brute_force_serializes_datetimes():
    attempt = BruteForceAttempt(
        ip = "1.2.3.4",
        fail_count = 5,
        window_start = datetime(2026, 5, 21, 20, 0, 0),
        window_end = datetime(2026, 5, 21, 20, 1, 0),
    )

    event = event_from_brute_force(attempt)

    assert event.source == "ssh_brute_force"
    assert event.severity == "critical"
    assert event.payload['ip'] == "1.2.3.4"
    assert isinstance(event.payload['window_start'] , str)
    assert event.payload['window_start'] == attempt.window_start.isoformat()