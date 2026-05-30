from datetime import datetime

from pyhids.store import Event
from pyhids.alert import format_alert

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