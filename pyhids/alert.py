"""
pyhids.alert - 把检测到的事件格式化成告警，并发送出去。
"""

from __future__ import annotations
from pyhids.store import Event

import logging
import json
import urllib.request

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

def send_dingtalk(text: str, webhook_url: str) -> None:
    """通过钉钉自定义机器人 webhook 发送一条文本告警。"""
    payload = {"msgtype": "text", "text": {"content": text}}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=5)
    logger.info("已发送钉钉告警到 %s", webhook_url)

def alert_if_critical(event: Event, webhook_url: str) -> None:
    """"仅当critical事件且配置webhook的时候，才发送告警"""
    if event.severity == "critical" and webhook_url:
        try:
            send_dingtalk(format_alert(event), webhook_url)
        except Exception as e:
            logger.warning("发送告警失败(已忽略，不影响检测) : %s", e)