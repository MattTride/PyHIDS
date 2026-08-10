import pytest

from pyhids.config import load_config


def _write_config(tmp_path, text: str):
    path = tmp_path / "watchlist.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_rejects_non_mapping_root(tmp_path):
    path = _write_config(tmp_path, "- /etc/hosts\n")

    with pytest.raises(ValueError, match="顶层必须是键值映射"):
        load_config(path)


def test_load_config_rejects_scalar_paths(tmp_path):
    path = _write_config(tmp_path, "paths: /etc/hosts\n")

    with pytest.raises(ValueError, match="paths 必须是字符串列表"):
        load_config(path)


def test_load_config_rejects_invalid_nested_section(tmp_path):
    path = _write_config(tmp_path, "ssh: enabled\n")

    with pytest.raises(ValueError, match="ssh 必须是键值映射"):
        load_config(path)


@pytest.mark.parametrize(
    "text, message",
    [
        ("algorithm: definitely-not-a-hash\n", "未知或不支持的哈希算法"),
        ("algorithm: shake_128\n", "未知或不支持的哈希算法"),
        ("scan_interval: 0\n", "scan_interval 必须是正整数"),
        ("ssh:\n  threshold: -1\n", "ssh.threshold 必须是正整数"),
        ("alert:\n  email_port: 70000\n", "email_port 必须是"),
    ],
)
def test_load_config_rejects_invalid_values(tmp_path, text, message):
    path = _write_config(tmp_path, text)

    with pytest.raises(ValueError, match=message):
        load_config(path)
