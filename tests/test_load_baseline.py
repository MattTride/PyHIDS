import json
import pytest
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