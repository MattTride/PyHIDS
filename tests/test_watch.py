from pathlib import Path

from pyhids.config import Config
from pyhids.watch import Debouncer, watched_dirs


# ---------- Debouncer ----------
# 注意：所有测试都把"现在几点"当参数传进去，一次 sleep 都不用。

def test_debouncer_not_due_without_any_event():
    d = Debouncer(quiet_period=1.0)

    assert d.due(now=100.0) is False


def test_debouncer_not_due_before_quiet_period_elapses():
    d = Debouncer(quiet_period=1.0)
    d.record_event(now=100.0)

    assert d.due(now=100.5) is False


def test_debouncer_due_exactly_at_quiet_period_boundary():
    """安静"满"1 秒就该触发（>= 而不是 >）。"""
    d = Debouncer(quiet_period=1.0)
    d.record_event(now=100.0)

    assert d.due(now=101.0) is True


def test_debouncer_new_event_restarts_the_quiet_period():
    """事件风暴的核心行为：每个新事件都让计时重新开始。"""
    d = Debouncer(quiet_period=1.0)
    d.record_event(now=100.0)
    d.record_event(now=100.8)

    # 距第一个事件已过 1.0 秒，但距最后一个只过了 0.2 秒
    assert d.due(now=101.0) is False
    assert d.due(now=101.8) is True


def test_debouncer_fires_only_once_per_burst():
    """触发后必须重置，否则主循环会反复触发同一波改动。"""
    d = Debouncer(quiet_period=1.0)
    d.record_event(now=100.0)

    assert d.due(now=101.0) is True
    assert d.due(now=102.0) is False
    assert d.due(now=999.0) is False


def test_debouncer_fires_again_for_a_later_burst():
    d = Debouncer(quiet_period=1.0)
    d.record_event(now=100.0)
    assert d.due(now=101.0) is True

    d.record_event(now=200.0)
    assert d.due(now=201.0) is True


# ---------- watched_dirs ----------

def test_watched_dirs_dedups_shared_parent_directories():
    cfg = Config(paths=[
        "demo_files/etc/passwd",
        "demo_files/etc/hosts",
        "demo_files/home/authorized_keys",
    ])

    assert watched_dirs(cfg) == {Path("demo_files/etc"), Path("demo_files/home")}


def test_watched_dirs_is_empty_when_no_paths_configured():
    assert watched_dirs(Config(paths=[])) == set()
