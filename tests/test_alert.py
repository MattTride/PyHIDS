import json
from datetime import datetime
from unittest.mock import patch

from pyhids.store import Event
from pyhids.alert import format_alert, send_dingtalk
from pyhids.alert import alert_if_critical

def test_format_alert_contains_key_fields():
    event = Event(
        detected_at = datetime(2026, 5, 21, 20, 30, 0),
        source = "ssh_brute_force",
        severity = "critical",
        summary = "1.2.3.4 暴力破解嫌疑",
        payload = {"ip": "1.2.3.4"},
    )

    text = format_alert(event)

    assert "CRITICAL" in text
    assert "ssh_brute_force" in text
    assert "1.2.3.4 暴力破解嫌疑" in text
    assert "2026-05-21 20:30:00" in text

def test_send_dingtalk_posts_correct_payload():
    # patch 把真正的 urlopen 换成一个“替身”，with 块内有效，出块自动还原
    with patch("urllib.request.urlopen") as mock_urlopen:
        send_dingtalk("hello PyHIDS", "https://example.com/robot")

        # ① 确认我们确实发起了恰好一次请求（替身被调用了 1 次）
        mock_urlopen.assert_called_once()

        # ② 取出当时传给 urlopen 的第一个参数（那个 Request 对象），检查 URL
        request = mock_urlopen.call_args.args[0]
        assert request.full_url == "https://example.com/robot"

        # ③ 检查请求体：解码回字典，确认格式和内容都对
        body = json.loads(request.data.decode("utf-8"))
        assert body["msgtype"] == "text"
        assert body["text"]["content"] == "hello PyHIDS"

@patch("pyhids.alert.send_dingtalk")
def test_alert_if_critical_sends_for_critical(mock_send):
    event = Event(
        detected_at = datetime(2026, 5, 21, 20, 30, 0),
        source = "ssh_brute_force",
        severity = "critical",
        summary="1.2.3.4 暴力破解嫌疑",
        payload = {"ip": "1.2.3.4"},
    )

    alert_if_critical(event, "https://example.com/robot")

    mock_send.assert_called_once()

@patch("pyhids.alert.send_dingtalk")
def test_alert_if_critical_skips_warning(mock_send):
    event = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="warning",
        summary="1.2.3.4 暴力破解嫌疑",
        payload={"ip": "1.2.3.4"},
    )

    alert_if_critical(event, "https://example.com/robot")

    mock_send.assert_not_called()

@patch("pyhids.alert.send_dingtalk")
def test_alert_if_critical_skips_when_no_webhook(mock_send):
    event = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="1.2.3.4 暴力破解嫌疑",
        payload={"ip": "1.2.3.4"},
    )

    alert_if_critical(event, "")

    mock_send.assert_not_called()