from pyhids.checker import compare_baselines, event_from_file_change



#对比完全相同的情况下-完好无缺
def test_compare_baselines_all_unchanged():
    old = {"files": {"a.txt": {"hash": "h1", "size": 10}}}
    new = {"files": {"a.txt": {"hash": "h1", "size": 10}}}

    result = compare_baselines(old, new)
    assert result["modified"] == []
    assert result["added"] == []
    assert result["deleted"] == []
    assert result["unchanged"] == ["a.txt"]
    assert result["summary"]["total_issues"] == 0

#被改的情况下
def test_compare_baselines_detects_modified():
    old = {"files": {"a.txt": {"hash": "h1", "size": 10}}}
    new = {"files": {"a.txt": {"hash": "h2", "size": 10}}}

    result = compare_baselines(old, new)
    assert result["modified"] == ["a.txt"]
    assert result["added"] == []
    assert result["deleted"] == []
    assert result["unchanged"] == []
    assert result["summary"]["total_issues"] == 1

def test_compare_baselines_detects_added_and_deleted():
    old = {"files": {"a.txt": {"hash": "h1", "size": 10},"b.txt": {"hash": "h2", "size": 10}}}
    new = {"files": {"b.txt": {"hash": "h2", "size": 10},"c.txt": {"hash": "h3", "size": 10}}}

    result = compare_baselines(old, new)
    assert sorted(result["added"]) == ["c.txt"]
    assert sorted(result["deleted"]) == ["a.txt"]
    assert sorted(result["unchanged"]) == ["b.txt"]
    assert result["summary"]["total_issues"] == 2


def test_event_from_file_change_modified_is_critical():
    event = event_from_file_change("modified", "/etc/passwd")

    assert event.severity == "critical"
    assert event.source == "file_integrity"
    assert event.payload["change"] == "modified"


def test_event_from_file_change_added_is_warning():
    event = event_from_file_change("added", "/tmp/newfile.txt")

    assert event.severity == "warning"