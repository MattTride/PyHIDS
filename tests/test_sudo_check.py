from datetime import datetime, timedelta

from pyhids.sudo_check import (
    PrivilegeAbuse,
    SudoEvent,
    detect_privilege_abuse,
    event_from_privilege_abuse,
    parse_log_line,
)


# ---------- parse_log_line ----------

def test_parse_pam_authentication_failure():
    line = ("May  8 12:00:00 server sudo: pam_unix(sudo:auth): authentication failure; "
            "logname=bob uid=1000 euid=0 tty=/dev/pts/1 ruser=bob rhost=  user=bob")

    event = parse_log_line(line)

    assert event is not None
    assert event.user == "bob"
    assert event.kind == "sudo"
    assert event.result == "fail"
    assert event.reason == "auth_failure"


def test_parse_user_not_in_sudoers():
    line = ("May  8 12:05:00 server sudo:      eve : user NOT in sudoers ; "
            "TTY=pts/2 ; PWD=/home/eve ; USER=root ; COMMAND=/bin/bash")

    event = parse_log_line(line)

    assert event is not None
    assert event.user == "eve"
    assert event.reason == "not_in_sudoers"
    assert event.result == "fail"


def test_parse_failed_su():
    line = "May  8 12:10:00 server su[3001]: FAILED SU (to root) mallory on pts/3"

    event = parse_log_line(line)

    assert event is not None
    assert event.user == "mallory"
    assert event.kind == "su"
    assert event.target == "root"
    assert event.reason == "failed_su"


def test_parse_successful_sudo_command():
    line = ("May  8 12:15:00 server sudo:      ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; "
            "USER=root ; COMMAND=/usr/bin/apt update")

    event = parse_log_line(line)

    assert event is not None
    assert event.user == "ubuntu"
    assert event.result == "success"
    assert event.target == "root"
    assert event.command == "/usr/bin/apt update"


def test_parse_sudo_command_without_user_field():
    """有些发行版不记 USER=，target 应为 None 而不是解析失败。"""
    line = "May  8 10:05:00 server sudo: ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; COMMAND=/bin/ls"

    event = parse_log_line(line)

    assert event is not None
    assert event.command == "/bin/ls"
    assert event.target is None


def test_parse_returns_none_for_unrelated_lines():
    assert parse_log_line("May  8 10:00:00 server sshd[1]: Failed password for bob from 1.2.3.4 port 1 ssh2") is None
    assert parse_log_line("完全不是日志的一行") is None
    assert parse_log_line("") is None


def test_incorrect_password_attempts_summary_is_ignored():
    """汇总行不解析，否则会和逐条 pam_unix 记录重复计数。"""
    line = ("May  8 12:00:20 server sudo:      bob : 3 incorrect password attempts ; "
            "TTY=pts/1 ; PWD=/home/bob ; USER=root ; COMMAND=/bin/bash")

    assert parse_log_line(line) is None


# ---------- detect_privilege_abuse ----------

def _fail(user: str, offset_seconds: int, reason: str = "auth_failure") -> SudoEvent:
    base = datetime(2026, 5, 8, 12, 0, 0)
    return SudoEvent(
        timestamp=base + timedelta(seconds=offset_seconds),
        user=user,
        kind="sudo",
        result="fail",
        reason=reason,
    )


def test_detect_reports_burst_when_threshold_is_reached():
    events = [_fail("bob", 0), _fail("bob", 8), _fail("bob", 16)]

    abuses = detect_privilege_abuse(events, window_seconds=60, threshold=3)

    assert len(abuses) == 1
    assert abuses[0].user == "bob"
    assert abuses[0].kind == "burst"
    assert abuses[0].fail_count == 3


def test_detect_ignores_burst_below_threshold():
    events = [_fail("bob", 0), _fail("bob", 8)]

    assert detect_privilege_abuse(events, window_seconds=60, threshold=3) == []


def test_detect_ignores_failures_spread_beyond_the_window():
    events = [_fail("bob", 0), _fail("bob", 100), _fail("bob", 200)]

    assert detect_privilege_abuse(events, window_seconds=60, threshold=3) == []


def test_detect_reports_not_in_sudoers_on_a_single_occurrence():
    """不在 sudoers 却尝试提权，一次就够可疑，不受阈值约束。"""
    events = [_fail("eve", 0, reason="not_in_sudoers")]

    abuses = detect_privilege_abuse(events, window_seconds=60, threshold=3)

    assert len(abuses) == 1
    assert abuses[0].kind == "not_in_sudoers"
    assert abuses[0].user == "eve"


def test_detect_counts_each_user_separately():
    events = [_fail("bob", 0), _fail("bob", 5), _fail("carol", 10)]

    assert detect_privilege_abuse(events, window_seconds=60, threshold=3) == []


def test_detect_ignores_successful_events():
    base = datetime(2026, 5, 8, 12, 0, 0)
    events = [
        SudoEvent(timestamp=base, user="ubuntu", kind="sudo", result="success",
                  reason="command", target="root", command="/bin/ls")
        for _ in range(5)
    ]

    assert detect_privilege_abuse(events, window_seconds=60, threshold=3) == []


# ---------- event_from_privilege_abuse ----------

def test_event_from_burst_abuse():
    abuse = PrivilegeAbuse(
        user="bob", kind="burst", fail_count=3,
        window_start=datetime(2026, 5, 8, 12, 0, 0),
        window_end=datetime(2026, 5, 8, 12, 0, 16),
    )

    event = event_from_privilege_abuse(abuse)

    assert event.source == "privilege_escalation"
    assert event.severity == "critical"
    assert "bob" in event.summary
    assert event.payload["user"] == "bob"
    assert event.payload["kind"] == "burst"
    assert event.payload["fail_count"] == 3


def test_event_from_not_in_sudoers_abuse_mentions_sudoers():
    abuse = PrivilegeAbuse(
        user="eve", kind="not_in_sudoers", fail_count=1,
        window_start=datetime(2026, 5, 8, 12, 5, 0),
        window_end=datetime(2026, 5, 8, 12, 5, 0),
    )

    event = event_from_privilege_abuse(abuse)

    assert event.severity == "critical"
    assert "sudoers" in event.summary
    assert event.payload["kind"] == "not_in_sudoers"
