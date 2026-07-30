"""
pyhids.watch — 实时文件监控

职责：用 watchdog 监听被监控文件所在的目录，把密集事件去抖动成
     "一波改动一次检查"，然后通过回调交给上层处理。
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pyhids.config import Config

logger = logging.getLogger(__name__)

DEFAULT_QUIET_PERIOD = 1.0
DEFAULT_POLL_INTERVAL = 0.2



class Debouncer:
    """把一串密集事件收敛成一次触发：安静 quiet_period 秒后才算数。"""

    def __init__(self, quiet_period: float = 1.0) -> None:
        self.quiet_period = quiet_period
        self._last_event_at: float | None = None

    def record_event(self, now: float) -> None:
        """收到一个文件系统事件。参数 now 是当前时间戳。"""
        self._last_event_at = now

    def due(self, now: float) -> bool:
        """现在该触发 check 了吗？触发过就要重置状态，不能连续返回两次 True。"""
        if self._last_event_at is None:
            return False
        if now - self._last_event_at >= self.quiet_period:
            self._last_event_at = None
            return True
        return False


class _ChangeHandler(FileSystemEventHandler):
    """watchdog 的事件接收器：把所有事件原封不动喂给 Debouncer。"""

    def __init__(self, debouncer: Debouncer) -> None:
        super().__init__()
        self.debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        logger.debug("文件系统事件 %s %s", event.event_type, event.src_path)
        self.debouncer.record_event(time.monotonic())


def watched_dirs(cfg: Config) -> set[Path]:
    """从配置里的文件路径推导出需要监控的目录集合（去重）。"""
    return {Path(p).parent for p in cfg.paths}


def watch(
    cfg: Config,
    on_change: Callable[[], None],
    quiet_period: float = DEFAULT_QUIET_PERIOD,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> None:
    """
    阻塞式实时监控。每当一波文件改动安静下来，就调一次 on_change()。

    on_change 由调用方（CLI）提供，本模块不关心它做什么 —— 保持领域层
    不依赖 store / alert。
    """
    debouncer = Debouncer(quiet_period=quiet_period)
    handler = _ChangeHandler(debouncer)
    observer = Observer()

    dirs = watched_dirs(cfg)
    for d in dirs:
        observer.schedule(handler, str(d), recursive=False)
        logger.info("开始监控目录 %s", d)

    observer.start()
    print(f"👁  实时监控中（{len(dirs)} 个目录，安静 {quiet_period}s 后触发检查），Ctrl+C 退出")

    try:
        while True:
            time.sleep(poll_interval)
            if debouncer.due(time.monotonic()):
                on_change()
    except KeyboardInterrupt:
        print("\n停止监控")
        logger.info("收到 Ctrl+C，停止监控")
    finally:
        observer.stop()
        observer.join()