import logging
import os
import socket
import sys
from pathlib import Path

from pyhids import app
from pyhids.log import setup_logging


def _isolated_env(monkeypatch):
    """给测试一份独立的 os.environ，避免 bootstrap 的 setdefault 污染真实环境。"""
    fake: dict[str, str] = {}
    monkeypatch.setattr(os, "environ", fake)
    return fake


# ---------- app_data_dir ----------

def test_app_data_dir_honours_the_override(monkeypatch):
    env = _isolated_env(monkeypatch)
    env["PYHIDS_DATA_DIR"] = "/tmp/somewhere"

    assert app.app_data_dir() == Path("/tmp/somewhere")


def test_app_data_dir_uses_application_support_on_macos(monkeypatch):
    _isolated_env(monkeypatch)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert app.app_data_dir() == Path.home() / "Library" / "Application Support" / "PyHIDS"


def test_app_data_dir_follows_xdg_on_linux(monkeypatch):
    env = _isolated_env(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "name", "posix")
    env["XDG_DATA_HOME"] = "/home/someone/.local/share"

    assert app.app_data_dir() == Path("/home/someone/.local/share/pyhids")


# ---------- resource_path ----------

def test_resource_path_uses_the_pyinstaller_unpack_dir(monkeypatch):
    """打包后资源在 sys._MEIPASS 下，源码运行时该属性不存在。"""
    monkeypatch.setattr(sys, "_MEIPASS", "/unpacked", raising=False)

    assert app.resource_path("config/x.yaml") == Path("/unpacked/config/x.yaml")


def test_resource_path_falls_back_to_the_repo_root(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    resolved = app.resource_path("config/watchlist.default.yaml")

    assert resolved.is_file()


# ---------- bootstrap ----------

def test_bootstrap_creates_the_data_dir_and_seeds_the_config(tmp_path, monkeypatch):
    env = _isolated_env(monkeypatch)
    data_dir = tmp_path / "PyHIDS"

    returned = app.bootstrap(data_dir)

    assert returned == data_dir
    assert (data_dir / "watchlist.yaml").is_file()
    assert env["PYHIDS_DB_PATH"] == str(data_dir / "events.db")
    assert env["PYHIDS_BASELINE_PATH"] == str(data_dir / "baseline.json")
    assert env["PYHIDS_CONFIG_PATH"] == str(data_dir / "watchlist.yaml")


def test_bootstrap_keeps_a_config_the_user_already_edited(tmp_path, monkeypatch):
    _isolated_env(monkeypatch)
    data_dir = tmp_path / "PyHIDS"
    data_dir.mkdir()
    (data_dir / "watchlist.yaml").write_text("algorithm: sha512\n", encoding="utf-8")

    app.bootstrap(data_dir)

    assert (data_dir / "watchlist.yaml").read_text(encoding="utf-8") == "algorithm: sha512\n"


def test_bootstrap_does_not_override_explicit_environment_variables(tmp_path, monkeypatch):
    """用户显式指定过的路径优先，App 只在"没人说"时才填默认值。"""
    env = _isolated_env(monkeypatch)
    env["PYHIDS_DB_PATH"] = "/custom/events.db"

    app.bootstrap(tmp_path / "PyHIDS")

    assert env["PYHIDS_DB_PATH"] == "/custom/events.db"


def test_bootstrap_is_idempotent(tmp_path, monkeypatch):
    _isolated_env(monkeypatch)
    data_dir = tmp_path / "PyHIDS"

    app.bootstrap(data_dir)
    app.bootstrap(data_dir)

    assert (data_dir / "watchlist.yaml").is_file()


# ---------- find_free_port ----------

def test_find_free_port_returns_a_bindable_port():
    port = app.find_free_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))  # 没抛异常就说明真的可用


def test_find_free_port_falls_back_when_the_preferred_one_is_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as taken:
        taken.bind(("127.0.0.1", 0))
        busy = taken.getsockname()[1]
        taken.listen(1)

        port = app.find_free_port(preferred=busy)

    assert port != busy


# ---------- 日志文件 ----------

def test_setup_logging_also_writes_to_a_file(tmp_path):
    log_file = tmp_path / "nested" / "pyhids.log"
    try:
        setup_logging("INFO", log_file=log_file)
        logging.getLogger("pyhids.test").info("落盘测试")
        logging.shutdown()

        assert "落盘测试" in log_file.read_text(encoding="utf-8")
    finally:
        # 还原成只有 stdout 的配置，免得影响后续测试
        setup_logging("INFO")
