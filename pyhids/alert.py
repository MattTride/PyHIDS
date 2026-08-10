"""
pyhids.alert - 把检测到的事件格式化成告警，并发送出去。
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
from email.message import EmailMessage

from pyhids.config import AlertConfig
from pyhids.store import Event

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
    with urllib.request.urlopen(request, timeout=5):
        pass
    # webhook URL 通常含有密钥，不能写进日志。
    logger.info("已发送钉钉告警")

def alert_if_critical(event: Event, alert_cfg: AlertConfig) -> None:
    """critical 事件 → 分发到所有已配置的渠道。某渠道失败不影响其它渠道/检测。"""
    if event.severity != "critical":
        return

    text = format_alert(event)

    if alert_cfg.dingtalk_webhook:
        try:
            send_dingtalk(text, alert_cfg.dingtalk_webhook)
        except Exception as e:
            logger.warning("发送告警失败(已忽略，不影响检测) : %s", e)

    if alert_cfg.email_host:
        try:
            send_email(text, host=alert_cfg.email_host, port=alert_cfg.email_port, username=alert_cfg.email_user, password=alert_cfg.email_password, from_addr=alert_cfg.email_from, to_addr=alert_cfg.email_to)
        except Exception as e:
            logger.warning("发送告警失败: %s", e)

def send_email(
        text: str,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addr: str,
) -> None:
    """通过SMTP发送一封纯文件告警文件"""
    msg = EmailMessage()
    msg["Subject"] = "PyHIDS告警"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(text)

    smtp = smtplib.SMTP(host, port, timeout=10)
    smtp.starttls()
    smtp.login(username, password)
    smtp.send_message(msg)
    smtp.quit()
