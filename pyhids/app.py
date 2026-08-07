"""
pyhids.app —— 桌面 App 模式入口

双击 PyHIDS.app 时走这里：准备用户数据目录 → 建基线 → 后台起实时监控
→ 启动仪表盘 → 打开浏览器。

和 CLI 模式的关键差别：
  * 双击启动时进程的工作目录是 `/`，所有相对路径都没有意义，
    因此数据和配置必须落在用户数据目录里；
  * `store` / `config` / `baseline` 三个模块在 **import 时** 就把
    `PYHIDS_*_PATH` 环境变量读成模块级常量了，所以 bootstrap() 必须在
    import 它们之前跑完 —— 本模块所有对它们的 import 都是延迟的（写在函数体内）。
"""
from __future__ import annotations

import logging
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "PyHIDS"
DEFAULT_CONFIG_RESOURCE = "config/watchlist.default.yaml"


def app_data_dir() -> Path:
    """各平台约定的用户数据目录（PYHIDS_DATA_DIR 可覆盖）。"""
    override = os.getenv("PYHIDS_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        base = os.getenv("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    # Linux / BSD：遵循 XDG 规范
    base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME.lower()


def resource_path(relative: str) -> Path:
    """定位打包进来的只读资源。

    PyInstaller 运行时会把资源解到临时目录，路径放在 sys._MEIPASS；
    直接从源码跑时该属性不存在，回退到仓库根目录。
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = Path(__file__).resolve().parent.parent
    return Path(base) / relative


def bootstrap(data_dir: Path | None = None) -> Path:
    """准备用户数据目录并设置环境变量，返回该目录。

    用 setdefault 而不是直接赋值：外部已经显式指定过的环境变量优先级更高，
    App 只在"用户没说"的时候才填默认值。
    """
    data_dir = data_dir or app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    config_path = data_dir / "watchlist.yaml"
    if not config_path.exists():
        shutil.copy(resource_path(DEFAULT_CONFIG_RESOURCE), config_path)
        logger.info("已生成默认配置 %s", config_path)

    os.environ.setdefault("PYHIDS_DB_PATH", str(data_dir / "events.db"))
    os.environ.setdefault("PYHIDS_BASELINE_PATH", str(data_dir / "baseline.json"))
    os.environ.setdefault("PYHIDS_CONFIG_PATH", str(config_path))

    return data_dir


def find_free_port(preferred: int = 8000) -> int:
    """优先用 preferred，被占了就让系统随便分一个。

    双击启动没有终端可以报错，端口冲突必须自己绕过去而不是崩掉。
    """
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # SO_REUSEADDR 在两个平台上语义完全不同，只能在 Unix 上设：
            #   Unix    —— 允许重用处于 TIME_WAIT 的端口。必须和 uvicorn 保持
            #              一致，否则上一个实例刚退出时探测会误判"端口被占"，
            #              白白退到随机端口（探测条件比真实绑定条件更严格）。
            #   Windows —— 允许绑定到另一个 socket 正在监听的端口，探测会永远
            #              成功，把已被占用的端口当成空闲的返回。
            if os.name != "nt":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("找不到可用端口")


def ensure_baseline() -> None:
    """没有基线就先建一份 —— 否则首次启动 check 会全部报成"文件已删除"。"""
    from pyhids.baseline import DEFAULT_BASELINE_PATH, build_baseline, save_baseline
    from pyhids.config import load_config

    if DEFAULT_BASELINE_PATH.exists():
        return

    cfg = load_config()
    save_baseline(build_baseline(cfg))
    logger.info("首次启动，已建立基线 %s", DEFAULT_BASELINE_PATH)


def start_watcher() -> None:
    """在后台线程里跑实时文件监控。

    守护线程：主线程（仪表盘）退出时它跟着消失，不会拖住进程。
    监控失败不能拖垮整个 App —— 仪表盘照样要能看历史事件。
    """
    from pyhids.cli import handle_fim_report
    from pyhids.checker import check
    from pyhids.config import load_config
    from pyhids.watch import watch

    def run() -> None:
        try:
            cfg = load_config()
            watch(cfg, lambda: handle_fim_report(check(cfg), cfg))
        except Exception:
            logger.exception("实时监控启动失败，仪表盘不受影响")

    threading.Thread(target=run, daemon=True, name="pyhids-watch").start()


def open_browser_when_ready(port: int, timeout: float = 15.0) -> None:
    """轮询端口，服务真的起来了再开浏览器。

    固定 sleep 是不可靠的：机器慢的时候浏览器会先打开、撞上"无法连接"。
    """
    def wait() -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    return
            time.sleep(0.2)
        logger.warning("等了 %.0f 秒仪表盘还没起来，不自动开浏览器了", timeout)

    threading.Thread(target=wait, daemon=True, name="pyhids-browser").start()


def run_app() -> None:
    """App 模式主流程。"""
    from pyhids.log import setup_logging

    data_dir = bootstrap()
    setup_logging("INFO", log_file=data_dir / "pyhids.log")
    logger.info("%s 启动，数据目录 %s", APP_NAME, data_dir)

    from pyhids.store import init_db
    init_db()

    try:
        ensure_baseline()
    except Exception:
        logger.exception("建立基线失败，跳过（仪表盘仍可用）")

    start_watcher()

    port = find_free_port()
    open_browser_when_ready(port)

    # 传 app 对象而不是 "pyhids.web:app" 字符串：字符串形式要靠运行时按名字
    # import，PyInstaller 的静态分析看不到这条依赖，打包后会找不到模块。
    import uvicorn
    from pyhids.web import app

    print(f"{APP_NAME} 仪表盘：http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def main() -> None:
    """打包后的统一入口：不带参数=App 模式，带参数=原来的 CLI。"""
    if len(sys.argv) > 1:
        bootstrap()
        from pyhids.cli import main as cli_main
        cli_main()
    else:
        run_app()


if __name__ == "__main__":
    main()
