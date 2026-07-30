# PyHIDS

A lightweight host-based intrusion detection system written in Python.

## Features (WIP)

- [ ✅ ] File integrity monitoring (SHA-256 baseline)
- [ ✅ ] Real-time file watching with debounced re-checks (`pyhids watch`)
- [ ✅ ] SSH brute-force detection via auth log parsing
- [ ✅ ] SQLite-based event persistence
- [ ✅ ] DingTalk + email alerting
- [ ✅ ] Web dashboard with real-time event stream
- [ ✅ ] Docker deployment

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

## Docker

```bash
docker compose up -d          # build + run the dashboard on :8000
docker compose exec pyhids pyhids check
docker compose down
```

Or without compose:

```bash
docker build -t pyhids:0.1.0 .
docker run -d --rm -p 8000:8000 -v "$PWD/data:/data" pyhids:0.1.0
```

**Mount whatever you want monitored read-only.** A container only sees its own
filesystem, so paths listed in `watchlist.yaml` that were never mounted in are
reported as *deleted* — false positives. Mount them with `:ro` so a compromised
PyHIDS still cannot tamper with what it watches:

```yaml
volumes:
  - /etc:/host/etc:ro     # then use /host/etc/... in watchlist.yaml
```

## Status

🚧 Under active development. Started May 2026.

**Requires Python 3.10+** (uses `X | None` / `list[X]` type-hint syntax).

# Chinese⬇️

# PyHIDS
一款使用 Python 编写的轻量级主机入侵检测系统。
## 功能特性(开发中)
- [ ✅ ] 文件完整性监控（基于 SHA-256 基线）
- [ ✅ ] 实时文件监控 + 事件去抖动（`pyhids watch`）
- [ ✅ ] 基于认证日志解析的 SSH 暴力破解检测
- [ ✅ ] 基于 SQLite 的事件持久化存储
- [ ✅ ] 钉钉 + 邮件告警
- [ ✅ ] 具备实时事件流的 Web 仪表盘
- [ ✅ ] Docker 部署支持

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

## Docker 部署

```bash
docker compose up -d          # 构建并启动仪表盘，监听 :8000
docker compose exec pyhids pyhids check
docker compose down
```

不用 compose 的话：

```bash
docker build -t pyhids:0.1.0 .
docker run -d --rm -p 8000:8000 -v "$PWD/data:/data" pyhids:0.1.0
```

**要监控的目录必须只读挂载进容器。** 容器只能看见自己的文件系统，
`watchlist.yaml` 里列了却没挂进去的路径会被报成「文件已删除」—— 全是误报。
用 `:ro` 挂载，这样即使 PyHIDS 自身被攻破，攻击者也改不了它监控的文件：

```yaml
volumes:
  - /etc:/host/etc:ro     # 然后 watchlist.yaml 里写 /host/etc/... 开头的路径
```

# 项目状态
🚧 处于积极开发阶段。项目始于 2026 年 5 月。

**需要 Python 3.10+**（使用了 `X | None` / `list[X]` 等类型注解语法）。
