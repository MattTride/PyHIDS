# PyHIDS

A lightweight host-based intrusion detection system written in Python.

## Features

- [ ✅ ] File integrity monitoring (SHA-256 baseline)
- [ ✅ ] Real-time file watching with debounced re-checks (`pyhids watch`)
- [ ✅ ] SSH brute-force detection via auth log parsing
- [ ✅ ] sudo / su privilege-escalation detection
- [ ✅ ] SQLite-based event persistence
- [ ✅ ] DingTalk + email alerting
- [ ✅ ] Web dashboard with SSE push, filters and pagination
- [ ✅ ] Docker deployment (non-root, healthchecked)
- [ ✅ ] Standalone desktop app (PyInstaller bundle, no Python needed)

## Install

```bash
pip install -e ".[dev]"   # then the `pyhids` command is on your PATH
pyhids --help
```

Paths can be overridden with environment variables — required when running
outside the repo root, and how the Docker image wires up its volumes:

| Variable | Default |
|---|---|
| `PYHIDS_DB_PATH` | `data/events.db` |
| `PYHIDS_BASELINE_PATH` | `data/baseline.json` |
| `PYHIDS_CONFIG_PATH` | `config/watchlist.yaml` |

## Detection sources

| Command | What it looks for | Exit code |
|---|---|---|
| `pyhids check` | files whose SHA-256 differs from the baseline | 1 if anything changed |
| `pyhids ssh-check` | repeated SSH password failures from one IP | 1 if a burst is found |
| `pyhids sudo-check` | sudo/su auth failure bursts, and users not in sudoers | 1 if abuse is found |

`sudo-check` treats the two cases differently: a burst needs to hit the
threshold (default 3 in 60s), but a *user NOT in sudoers* line is reported on a
single occurrence — someone with no sudo rights trying to escalate is already
suspicious. A lone failed `su` stays quiet; that is just a typo.

All three write to the same `events` table — a new source needs a new factory
function, never a schema change.

## Real-time monitoring

`pyhids check` is a one-shot scan for cron. `pyhids watch` is a long-running
process that reacts the moment a watched file changes:

```bash
pyhids watch                       # Ctrl+C to stop
pyhids watch --quiet-period 2.0    # wait 2s of silence before re-checking
```

It watches the *parent directories* of everything in `watchlist.yaml` (watchdog
cannot watch individual files) and debounces the event stream: one editor save
emits 3–5 filesystem events, so the checker only runs once the burst has been
quiet for `--quiet-period` seconds. Without that, a single save would produce
several duplicate events and alerts — and checks could read a half-written file.

## Dashboard

```bash
pyhids serve                  # http://127.0.0.1:8000
```

Filter by source and severity, page through history, and watch events arrive
live. The page holds one SSE connection to `/api/stream`; the server pushes the
event-id cursor only when it actually moves, and the browser re-fetches the
current page. That replaced a blind 5-second poll, so an idle dashboard makes no
requests at all. Auto-refresh pauses while you are on page 2 or later, so paging
back through history does not yank you to the top.

## Desktop app

Build a self-contained bundle — no Python, no `pip`, nothing to install on the
target machine:

```bash
pip install -e ".[dev]"
pyinstaller pyhids.spec --noconfirm       # -> dist/PyHIDS.app (32 MB)
```

Double-clicking it builds a baseline on first run, starts the real-time file
watcher, serves the dashboard and opens your browser. Everything lives in a
per-user data directory, so the app works from anywhere:

| Platform | Data directory |
|---|---|
| macOS | `~/Library/Application Support/PyHIDS/` |
| Linux | `~/.local/share/pyhids/` |
| Windows | `%APPDATA%\PyHIDS\` |

It holds `watchlist.yaml` (copied from `config/watchlist.default.yaml` on first
run, then yours to edit), `events.db`, `baseline.json` and `pyhids.log`. Set
`PYHIDS_DATA_DIR` to put it somewhere else. A double-clicked app has no terminal,
so `pyhids.log` is the only place startup errors show up — read it first when
something looks wrong.

The bundled binary is still the full CLI:

```bash
dist/PyHIDS.app/Contents/MacOS/PyHIDS check
dist/PyHIDS.app/Contents/MacOS/PyHIDS events --limit 20
```

Port 8000 is preferred; if it is busy the app picks a free one and opens the
browser there rather than failing with no visible error.

## Docker

```bash
docker compose up -d          # build + run the dashboard on :8000
docker compose exec pyhids pyhids check
docker compose down
```

Or without compose:

```bash
docker build -t pyhids:1.2.0 .
docker run -d --rm -p 8000:8000 -v "$PWD/data:/data" pyhids:1.2.0
```

**Mount whatever you want monitored read-only.** A container only sees its own
filesystem, so paths listed in `watchlist.yaml` that were never mounted in are
reported as *deleted* — false positives. Mount them with `:ro` so a compromised
PyHIDS still cannot tamper with what it watches:

```yaml
volumes:
  - /etc:/host/etc:ro     # then use /host/etc/... in watchlist.yaml
```

The container runs as the unprivileged user `pyhids` (UID 1000) and ships a
`HEALTHCHECK` that hits `/api/events`. On Linux, make the mounted `data/`
directory writable by that UID: `sudo chown -R 1000:1000 data`.

## Status

v1.2.0 — feature-complete. Started May 2026. 89 tests passing.

**Requires Python 3.10+** (uses `X | None` / `list[X]` type-hint syntax).

# Chinese⬇️

# PyHIDS
一款使用 Python 编写的轻量级主机入侵检测系统。
## 功能特性
- [ ✅ ] 文件完整性监控（基于 SHA-256 基线）
- [ ✅ ] 实时文件监控 + 事件去抖动（`pyhids watch`）
- [ ✅ ] 基于认证日志解析的 SSH 暴力破解检测
- [ ✅ ] sudo / su 提权滥用检测
- [ ✅ ] 基于 SQLite 的事件持久化存储
- [ ✅ ] 钉钉 + 邮件告警
- [ ✅ ] Web 仪表盘：SSE 实时推送 + 过滤 + 分页
- [ ✅ ] Docker 部署（非 root 运行 + 健康检查）
- [ ✅ ] 独立桌面 App（PyInstaller 打包，目标机器无需 Python）

## 安装

```bash
pip install -e ".[dev]"   # 装完就能直接敲 pyhids 命令
pyhids --help
```

路径可以用环境变量覆盖 —— 在仓库目录之外运行时必须用，Docker 镜像也靠它接挂卷：

| 环境变量 | 默认值 |
|---|---|
| `PYHIDS_DB_PATH` | `data/events.db` |
| `PYHIDS_BASELINE_PATH` | `data/baseline.json` |
| `PYHIDS_CONFIG_PATH` | `config/watchlist.yaml` |

## 检测源

| 命令 | 检测什么 | 退出码 |
|---|---|---|
| `pyhids check` | SHA-256 与基线不符的文件 | 有变化则 1 |
| `pyhids ssh-check` | 同一 IP 反复 SSH 密码失败 | 有暴破则 1 |
| `pyhids sudo-check` | sudo/su 认证失败风暴、不在 sudoers 却提权 | 有滥用则 1 |

`sudo-check` 对两种情况区别对待：失败风暴要达到阈值（默认 60 秒内 3 次）才报，
但 *user NOT in sudoers* **出现一次就报** —— 一个根本没有 sudo 权限的用户尝试提权，
本身就已经可疑。而单次 `su` 失败不报，那多半只是打错密码。

三个检测源共用同一张 `events` 表：加新事件源只需要写一个新的工厂函数，**不用改表结构**。

## 实时监控

`pyhids check` 是给 cron 用的一次性扫描；`pyhids watch` 是长驻进程，
被监控文件一有改动立刻反应：

```bash
pyhids watch                       # Ctrl+C 退出
pyhids watch --quiet-period 2.0    # 改动安静 2 秒后才触发检查
```

它监控的是 `watchlist.yaml` 里各文件所在的**父目录**（watchdog 无法监控单个
文件），并对事件流做去抖动：编辑器保存一次会产生 3~5 个文件系统事件，所以
只有在这波事件安静 `--quiet-period` 秒之后才跑一次检查。没有去抖动的话，
保存一次文件会产生好几条重复事件和告警，而且检查可能读到写了一半的文件。

## 仪表盘

```bash
pyhids serve                  # http://127.0.0.1:8000
```

支持按来源 / 等级过滤、翻页查历史，新事件会自动出现。页面挂着一条到 `/api/stream`
的 SSE 连接，服务端只在事件 id 游标真的变化时才推一次，浏览器收到后重新拉当前页。
这取代了原来每 5 秒一次的盲目轮询 —— 现在没有新事件时，闲置的仪表盘一个请求都不发。
另外翻到第 2 页以后自动刷新会暂停，免得你正在翻历史却被拽回顶部。

## 桌面 App

打包成独立应用 —— 目标机器不需要装 Python、不需要 `pip`、什么都不用装：

```bash
pip install -e ".[dev]"
pyinstaller pyhids.spec --noconfirm       # 产物 dist/PyHIDS.app（32 MB）
```

双击后：首次运行自动建立基线 → 启动实时文件监控 → 打开仪表盘并弹出浏览器。
所有数据放在用户数据目录，所以 App 放在哪儿都能跑：

| 平台 | 数据目录 |
|---|---|
| macOS | `~/Library/Application Support/PyHIDS/` |
| Linux | `~/.local/share/pyhids/` |
| Windows | `%APPDATA%\PyHIDS\` |

里面有 `watchlist.yaml`（首次运行从 `config/watchlist.default.yaml` 复制过来，
之后归你改，不会被覆盖）、`events.db`、`baseline.json` 和 `pyhids.log`。
想换位置就设 `PYHIDS_DATA_DIR`。

**双击启动没有终端，`pyhids.log` 是唯一能看到启动错误的地方** —— 出问题先看它。

打包后的二进制同时也是完整的 CLI：

```bash
dist/PyHIDS.app/Contents/MacOS/PyHIDS check
dist/PyHIDS.app/Contents/MacOS/PyHIDS events --limit 20
```

端口优先用 8000；被占用时会自动换一个空闲端口并把浏览器开到那里，
而不是无声无息地启动失败。

## Docker 部署

```bash
docker compose up -d          # 构建并启动仪表盘，监听 :8000
docker compose exec pyhids pyhids check
docker compose down
```

不用 compose 的话：

```bash
docker build -t pyhids:1.2.0 .
docker run -d --rm -p 8000:8000 -v "$PWD/data:/data" pyhids:1.2.0
```

**要监控的目录必须只读挂载进容器。** 容器只能看见自己的文件系统，
`watchlist.yaml` 里列了却没挂进去的路径会被报成「文件已删除」—— 全是误报。
用 `:ro` 挂载，这样即使 PyHIDS 自身被攻破，攻击者也改不了它监控的文件：

```yaml
volumes:
  - /etc:/host/etc:ro     # 然后 watchlist.yaml 里写 /host/etc/... 开头的路径
```

容器以非特权用户 `pyhids`（UID 1000）运行，并配了访问 `/api/events` 的 `HEALTHCHECK`。
在 Linux 上要让挂进去的 `data/` 目录对该 UID 可写：`sudo chown -R 1000:1000 data`。

# 项目状态
v1.2.0 —— 功能已完整。项目始于 2026 年 5 月，89 个测试全绿。

**需要 Python 3.10+**（使用了 `X | None` / `list[X]` 等类型注解语法）。
