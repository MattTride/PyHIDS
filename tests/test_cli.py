from datetime import datetime

from pyhids import cli
from pyhids.config import Config
from pyhids.store import Event


def test_persist_events_deduplicates_alerts_within_the_current_batch(monkeypatch):
    event = Event(
        detected_at=datetime(2026, 5, 21, 20, 30, 0),
        source="ssh_brute_force",
        severity="critical",
        summary="duplicate attack",
        payload={"ip": "1.2.3.4"},
    )
    inserted = []
    alerted = []
    monkeypatch.setattr(cli, "dedup_keys_since", lambda cutoff: set())
    monkeypatch.setattr(cli, "insert_event", inserted.append)
    monkeypatch.setattr(cli, "alert_if_critical", lambda current, config: alerted.append(current))

    cli.persist_events([event, event], Config())

    assert inserted == [event, event]
    assert alerted == [event]
