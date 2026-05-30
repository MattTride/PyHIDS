"""
pyhids.alert - 把检测到的事件格式化成告警，并发送出去。
"""

from __future__ import annotations
from pyhids.store import Event

import logging

logger = logging.getLogger(__name__)

def format_alert(event: Event) -> str:
    """把一条Event事件转化成人类可读的告警文本"""
    time_str = event.detected_at.strftime("%Y-%m-%d %H:%M:%S")
    return(
        f"PyHIDS 告警 [{event.severity.upper()}]\n"
        f"来源: {event.source}\n"
        f"时间: {time_str}\n"
        f"摘要: {event.summary}\n"
    )