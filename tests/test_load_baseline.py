import json

import pytest

from pyhids.baseline import save_baseline
from pyhids.checker import load_baseline


def test_load_baseline_reads_valid_json(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    fake_baseline = {"metadata": {"version": "1.0"}, "files": {"a.txt": {"hash": "h1", "size": 10}}}
    baseline_path.write_text(json.dumps(fake_baseline))

    result = load_baseline(baseline_path)
    assert result == fake_baseline

def test_load_baseline_raises_on_missing_file(tmp_path):
    baseline_path_missing = tmp_path / "nonexistent,json"
    with pytest.raises(FileNotFoundError):
        load_baseline(baseline_path_missing)


def test_save_baseline_creates_parent_directories(tmp_path):
    baseline_path = tmp_path / "nested" / "data" / "baseline.json"
    baseline = {"metadata": {"version": "1.0"}, "files": {}}

    save_baseline(baseline, baseline_path)

    assert load_baseline(baseline_path) == baseline


def test_save_baseline_keeps_previous_file_if_serialization_fails(tmp_path):
    baseline_path = tmp_path / "baseline.json"
    previous = {"metadata": {"version": "1.0"}, "files": {}}
    save_baseline(previous, baseline_path)

    with pytest.raises(TypeError):
        save_baseline({"not_json": object()}, baseline_path)

    assert load_baseline(baseline_path) == previous
    assert list(tmp_path.glob(".baseline.json.*.tmp")) == []
