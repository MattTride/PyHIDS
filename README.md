# PyHIDS 主机入侵检测系统

一个用 Python 编写的轻量级主机入侵检测系统（HIDS），定位类似简化版的 OSSEC / Wazuh，运行在单台主机上。它持续核对关键文件的 SHA-256 指纹、解析系统认证日志，检测文件篡改、SSH 暴力破解和 sudo / su 提权滥用三类风险，发现异常后写入本地数据库、推送告警，并在网页仪表盘上实时展示。项目提供命令行、Docker 容器和双击即用的桌面应用三种使用方式。

![PyHIDS 仪表盘](docs/dashboard.png)

## 下载

根据操作系统点击下载（链接指向最新 Release，会自动跳转到对应安装包）：

[![Download for macOS](https://img.shields.io/badge/Download-macOS-111111?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-macOS.zip)
[![Download for Windows](https://img.shields.io/badge/Download-Windows-0067b8?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-Windows.zip)

- **macOS**：[下载 PyHIDS-macOS.zip](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-macOS.zip)。解压后双击 `PyHIDS.app`；若提示「来自未识别的开发者」，右键点图标选「打开」。
- **Windows**：[下载 PyHIDS-Windows.zip](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-Windows.zip)。解压后进入 `PyHIDS` 目录双击 `PyHIDS.exe`；若 SmartScreen 拦截，点「更多信息」→「仍要运行」。

双击启动后应用会自动建立基线、开启实时文件监控、启动仪表盘并打开浏览器，目标机器不需要安装 Python。

> 安装包由 GitHub Actions 在推送 `v*` 版本标签时自动在 macOS / Windows 机器上构建（见 [`.github/workflows/release.yml`](.github/workflows/release.yml)），二进制不提交进仓库。首个 Release 生成后，上述链接即生效。

## 项目特点

- 三类检测能力：文件完整性、SSH 暴力破解、sudo / su 提权滥用。
- 文件完整性基于 SHA-256 指纹基线比对，可识别被修改、被删除和新增的文件。
- 支持一次性扫描（适合 cron 定时任务）和常驻实时监控两种工作模式。
- 实时监控内置事件去抖动，一次文件保存产生的多个系统事件只会触发一次检查。
- 认证日志解析支持 sshd、sudo 和 su 三种记录格式，可识别失败风暴与非授权提权。
- 所有事件写入单文件 SQLite 数据库，随时可回查历史。
- 告警支持钉钉机器人和 SMTP 邮件双渠道，并按事件指纹做时间窗去重，避免重复轰炸。
- 告警发送失败不会中断检测主流程。
- 内置 FastAPI 网页仪表盘，支持按来源和等级过滤、翻页查看历史。
- 仪表盘使用 SSE 服务端推送，仅在出现新事件时更新，空闲时不产生任何请求。
- 检测命令在发现异常时返回退出码 1，可直接接入 shell 脚本和监控系统。
- 数据与配置路径均可用环境变量覆盖，便于容器挂卷和多环境部署。
- 提供非 root 运行、带健康检查的 Docker 镜像。
- 可用 PyInstaller 打包成独立桌面应用，目标机器无需安装 Python。
- 核心逻辑由 89 个 pytest 单元测试覆盖，运行时不联网、不依赖数据库。

## 检测能力

| 子命令 | 检测对象 | 判定条件 | 事件等级 |
|---|---|---|---|
| `check` | 配置中列出的文件 | SHA-256 与基线不符（修改 / 删除） | critical |
| `check` | 配置中新增的文件 | 基线中不存在（新增） | warning |
| `ssh-check` | auth.log 中的 sshd 记录 | 同一 IP 在 60 秒内登录失败 5 次 | critical |
| `sudo-check` | auth.log 中的 sudo / su 记录 | 同一用户在 60 秒内认证失败 3 次 | critical |
| `sudo-check` | auth.log 中的 sudo 记录 | 出现 `user NOT in sudoers` | critical |

阈值均可在配置文件中调整。`user NOT in sudoers` 不受阈值约束，出现一次即判定为异常——不具备 sudo 权限的账号尝试提权，本身即属可疑行为。单次 `su` 失败不触发告警，避免把输错密码误判成攻击。

## 运行要求

- macOS、Linux 或 Windows。
- Python 3.10 及以上版本（使用了 `X | None`、`list[X]` 等新版类型注解语法）。
- 运行依赖：`PyYAML`、`fastapi`、`uvicorn`、`watchdog`，均会随安装自动装好。

> SSH 与提权检测依赖文本格式的认证日志。Debian / Ubuntu 对应 `/var/log/auth.log`，RHEL / CentOS 对应 `/var/log/secure`。macOS 没有该文件，因此在 macOS 上只有文件完整性监控和仪表盘可用。

## 快速开始

在项目目录中运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

安装完成后 `pyhids` 命令即可直接使用：

```bash
pyhids --help
```

不想装 Python 环境？用打包好的桌面版，见下面的 [打包说明](#打包说明)。

## 使用方法

1. 修改 `config/watchlist.yaml`，填入需要监控的文件路径和认证日志位置。
2. 在系统处于可信状态时建立基线：`pyhids baseline`。
3. 需要时执行检测：`pyhids check`、`pyhids ssh-check`、`pyhids sudo-check`。
4. 若希望文件改动被立即发现，改用常驻模式：`pyhids watch`（按 Ctrl+C 退出）。
5. 查看历史事件：`pyhids events --limit 20`，或启动仪表盘 `pyhids serve` 后访问 <http://127.0.0.1:8000>。
6. 在仪表盘上可按来源和等级筛选，并翻页查看更早的记录。

全部子命令：

| 命令 | 说明 |
|---|---|
| `pyhids baseline` | 扫描配置中的文件，生成 SHA-256 指纹基线 |
| `pyhids check` | 对比基线，找出被修改 / 删除 / 新增的文件 |
| `pyhids ssh-check` | 解析认证日志，检测 SSH 暴力破解 |
| `pyhids sudo-check` | 解析认证日志，检测 sudo / su 提权滥用 |
| `pyhids events` | 查询历史事件，支持 `--limit` 和 `--source` |
| `pyhids watch` | 常驻实时监控文件改动 |
| `pyhids serve` | 启动网页仪表盘 |

`check`、`ssh-check`、`sudo-check` 三个命令在发现异常时返回退出码 1，因此可以直接接入脚本：

```bash
pyhids check || echo "检测到文件被篡改"
```

> 建立基线的时机决定了整个系统是否有意义。基线是「正常状态」的定义，若在已被入侵的主机上建立基线，后门文件会被记录为正常状态并永久放行。

## 配置说明

配置文件为 `config/watchlist.yaml`：

```yaml
algorithm: sha256

paths:                              # 需要监控完整性的文件
  - /etc/passwd
  - /etc/ssh/sshd_config
  - /root/.ssh/authorized_keys

ssh:
  log_path: /var/log/auth.log
  window_seconds: 60
  threshold: 5                      # 60 秒内失败 5 次判定为暴力破解

sudo:
  log_path: /var/log/auth.log
  window_seconds: 60
  threshold: 3

alert:
  dingtalk_webhook: ""              # 填入钉钉机器人地址即启用推送
  dedup_window_seconds: 3600        # 同一问题在该时间窗内只告警一次
  email_host: ""                    # 填入 SMTP 服务器即启用邮件告警
  email_port: 587
  email_user: ""
  email_password: ""
  email_from: ""
  email_to: ""
```

数据与配置路径可用环境变量覆盖，Docker 镜像和桌面应用均通过该机制接管数据位置：

| 环境变量 | 默认值 |
|---|---|
| `PYHIDS_DB_PATH` | `data/events.db` |
| `PYHIDS_BASELINE_PATH` | `data/baseline.json` |
| `PYHIDS_CONFIG_PATH` | `config/watchlist.yaml` |
| `PYHIDS_DATA_DIR` | 桌面应用的数据目录 |

桌面应用首次启动时会在用户数据目录生成一份配置，此后修改不会被覆盖：

| 平台 | 数据目录 |
|---|---|
| macOS | `~/Library/Application Support/PyHIDS/` |
| Linux | `~/.local/share/pyhids/` |
| Windows | `%APPDATA%\PyHIDS\` |

该目录包含 `watchlist.yaml`、`events.db`、`baseline.json` 和 `pyhids.log`。桌面应用双击启动时没有终端窗口，`pyhids.log` 是唯一能看到启动错误的位置。

## 事件存储格式

所有事件写入同一张 SQLite 表，源专属字段以 JSON 存放在 `payload` 列中。新增检测源不需要修改表结构：

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,      -- ISO 8601 时间戳
    source      TEXT NOT NULL,      -- file_integrity | ssh_brute_force | privilege_escalation
    severity    TEXT NOT NULL,      -- info | warning | critical
    summary     TEXT NOT NULL,      -- 给人看的一句话
    payload     TEXT NOT NULL       -- JSON 字符串，源专属字段
);
```

`/api/events` 返回的单条事件结构大致如下：

```json
{
  "detected_at": "2026-08-03T19:11:41.594062",
  "source": "privilege_escalation",
  "severity": "critical",
  "summary": "bob 提权失败风暴（3 次 / 窗口 2026-05-08 12:00:00 → 2026-05-08 12:00:16）",
  "payload": {
    "user": "bob",
    "kind": "burst",
    "fail_count": 3,
    "window_start": "2026-05-08T12:00:00",
    "window_end": "2026-05-08T12:00:16"
  }
}
```

调试时可直接查看数据库：

```bash
sqlite3 data/events.db "SELECT detected_at, source, severity, summary FROM events;"
```

## 仪表盘说明

```bash
pyhids serve --host 127.0.0.1 --port 8000
```

- 表格按时间倒序展示事件，critical 显示为红色，warning 显示为橙色。
- 顶部可按事件来源和严重等级筛选，并选择每页显示条数。
- 底部提供上一页 / 下一页按钮，右下角显示实时连接状态。
- 新事件通过 SSE 推送自动出现，无需刷新页面；翻到第 2 页之后自动刷新会暂停，避免打断正在查看历史的操作。
- 提供 `/api/events` 和 `/api/stream` 两个接口，可供外部系统集成。

> 仪表盘没有任何登录认证，默认只监听 `127.0.0.1`。请勿直接暴露到公网；需要远程访问时应使用 SSH 隧道，或在前端部署带认证的反向代理。

## 项目文件

```text
.
├── pyhids/
│   ├── hasher.py               # 文件 SHA-256 计算
│   ├── config.py               # YAML 配置加载
│   ├── baseline.py             # 指纹基线生成与持久化
│   ├── checker.py              # 文件完整性比对 + 事件工厂
│   ├── ssh_check.py            # SSH 暴力破解检测 + 事件工厂
│   ├── sudo_check.py           # sudo / su 提权滥用检测 + 事件工厂
│   ├── watch.py                # 实时监控：去抖动器 + watchdog 观察者
│   ├── store.py                # SQLite 事件持久化与去重指纹
│   ├── alert.py                # 钉钉 / 邮件告警发送
│   ├── web.py                  # FastAPI 仪表盘与 SSE 推送
│   ├── app.py                  # 桌面应用模式入口
│   ├── log.py                  # 日志统一配置
│   └── cli.py                  # 命令行入口（7 个子命令）
├── tests/                      # pytest 单元测试（89 个）
├── config/
│   ├── watchlist.yaml          # 开发用配置
│   └── watchlist.default.yaml  # 桌面应用的默认配置
├── demo_files/                 # 演示用样本数据（含合成 auth.log）
├── data/                       # 运行时数据（数据库不入库）
├── docs/dashboard.png          # 仪表盘截图
├── launcher.py                 # PyInstaller 入口脚本
├── pyhids.spec                 # PyInstaller 打包配置
├── .github/workflows/          # GitHub Actions：打 tag 自动构建 macOS/Windows 安装包
├── Dockerfile                  # 容器镜像定义
├── docker-compose.yml          # 容器编排（端口与挂卷）
├── pyproject.toml              # 包元数据与依赖
├── HANDOFF.md                  # 开发交接文档
├── README.md                   # 项目说明
├── LICENSE                     # MIT License
└── .gitignore                  # Git 忽略规则
```

## 开发说明

项目按三层组织，依赖方向自上而下，不允许反向：

- **领域层**（`checker.py`、`ssh_check.py`、`sudo_check.py`、`watch.py`）：纯检测逻辑，不导入存储层，只对外暴露 `event_from_*` 工厂函数声明「能产出什么事件」。
- **基础设施层**（`store.py`、`alert.py`、`web.py`）：负责数据库读写、告警发送和网页服务。
- **适配层**（`cli.py`、`app.py`）：解析参数，把领域层产出的事件交给基础设施层落库和告警。

这样划分的直接收益是绝大多数单元测试不需要数据库即可运行，整套 89 个测试在 0.3 秒内跑完。实时监控模块同样通过 `on_change` 回调把落库与告警交给上层，自身不感知下游行为。

几个关键实现细节：

- 去抖动器把「当前时间」作为参数传入而非在函数内部读取，使时序逻辑无需 `sleep` 即可单元测试。
- 告警去重指纹只取稳定标识（用户名、IP、问题类型），不包含时间窗边界，避免窗口滑动导致指纹变化、去重失效。
- SSE 只推送事件 id 游标而不推送事件内容，筛选与分页逻辑仍由前端既有函数处理，无需在推送通道中重复实现。
- 路径常量在模块导入时读取环境变量，因此桌面应用入口对相关模块采用延迟导入，确保数据目录先于导入完成初始化。

## 运行测试

```bash
python3 -m pytest -v
```

预期 89 个测试全部通过。测试不联网、不写入真实数据库，全部使用 pytest 的临时目录。

## 打包说明

### 桌面应用

使用 PyInstaller 打包为独立应用，目标机器无需安装 Python：

```bash
pip install -e ".[dev]"
pyinstaller pyhids.spec --noconfirm
```

产物为 `dist/PyHIDS.app`（macOS，约 32 MB）。双击后会自动建立基线、启动实时监控、开启仪表盘并打开浏览器。打包后的二进制同时保留完整命令行功能：

```bash
dist/PyHIDS.app/Contents/MacOS/PyHIDS check
```

`dist/` 和 `build/` 属于生成文件，默认不会提交到 Git。

发布带下载包的版本：推送一个 `v` 开头的标签，即可触发 GitHub Actions 在 macOS 与 Windows 上分别构建，并发布到对应的 GitHub Release：

```bash
git tag v1.2.1
git push origin v1.2.1
```

也可以在 GitHub 仓库的 Actions 页面手动运行「Build release packages」。构建流程会先执行完整测试，测试不通过则不会产出安装包。

> 打包产物没有代码签名。在本机运行不受影响，但分发给他人时 macOS 会提示「来自未识别的开发者」，需右键点图标选「打开」。彻底解决需要 Apple 开发者账号进行签名与公证。

### Docker

```bash
docker compose up -d --build
```

镜像以非特权用户 `pyhids`（UID 1000）运行，并配置了访问 `/api/events` 的健康检查。在 Linux 上需让挂载的 `data/` 目录对该 UID 可写：

```bash
sudo chown -R 1000:1000 data
```

被监控的目录必须只读挂载进容器。容器只能看到自身的文件系统，配置中列出却未挂载的路径会被判定为「文件已删除」：

```yaml
volumes:
  - /etc:/host/etc:ro     # 配置中相应改写为 /host/etc/... 开头的路径
```

只读挂载（`:ro`）不仅是习惯：即便 PyHIDS 自身被攻破，攻击者也无法篡改其监控的目标。

## 服务器部署

在系统可信状态下建立基线，然后通过 cron 定时执行检测（cron 的 PATH 极为精简，必须使用绝对路径）：

```bash
sudo pyhids baseline
```

```bash
*/10 * * * * /opt/pyhids/.venv/bin/pyhids check      >> /var/log/pyhids.log 2>&1
*/5  * * * * /opt/pyhids/.venv/bin/pyhids ssh-check  >> /var/log/pyhids.log 2>&1
*/5  * * * * /opt/pyhids/.venv/bin/pyhids sudo-check >> /var/log/pyhids.log 2>&1
```

文件监控建议改用常驻服务，响应速度从分钟级提升到秒级。示例 systemd 单元：

```ini
[Unit]
Description=PyHIDS real-time file monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/pyhids
ExecStart=/opt/pyhids/.venv/bin/pyhids watch
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now pyhids-watch
```

## 注意事项

- 基线必须在系统可信状态下建立，否则已存在的后门会被记录为正常状态。
- `baseline.json` 本身是攻击目标。攻击者植入后门后重新执行 `pyhids baseline` 即可掩盖痕迹，生产环境应将其设为 root 只读，并定期备份到独立主机比对。
- 读取 `/var/log/auth.log` 需要相应权限，定时任务应配置在 root 的 crontab 中，或将运行用户加入 `adm` 组。
- 仪表盘没有认证机制，不应直接暴露到公网。
- 认证日志解析依赖文本格式日志文件，仅使用 systemd-journald 而无文本日志的系统暂不支持。
- 同一问题每次检测都会新增一条记录，仪表盘上会出现重复行。告警层已按时间窗去重，存储层未做去重。
- 当前版本不包含进程监控、端口监听变化检测和 rootkit 检测。

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

# PyHIDS — Host-based Intrusion Detection System

*English version. 中文说明见上方。*

A lightweight host-based intrusion detection system (HIDS) written in Python — a
simplified take on OSSEC / Wazuh, designed to run on a single host. It verifies
SHA-256 fingerprints of critical files and parses system authentication logs to
detect three classes of risk: file tampering, SSH brute-force attempts, and
sudo / su privilege abuse. Findings are written to a local database, pushed as
alerts, and displayed live on a web dashboard. It ships as a command-line tool,
a Docker container, and a double-clickable desktop application.

![PyHIDS dashboard](docs/dashboard.png)

## Download

Pick the package for your operating system (links resolve to the latest release):

[![Download for macOS](https://img.shields.io/badge/Download-macOS-111111?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-macOS.zip)
[![Download for Windows](https://img.shields.io/badge/Download-Windows-0067b8?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-Windows.zip)

- **macOS**: [PyHIDS-macOS.zip](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-macOS.zip). Unzip and double-click `PyHIDS.app`. If macOS reports an unidentified developer, right-click the icon and choose "Open".
- **Windows**: [PyHIDS-Windows.zip](https://github.com/MattTride/PyHIDS/releases/latest/download/PyHIDS-Windows.zip). Unzip, enter the `PyHIDS` folder and run `PyHIDS.exe`. If SmartScreen blocks it, click "More info" → "Run anyway".

On launch the app builds a baseline, starts the real-time file watcher, serves
the dashboard and opens your browser. No Python installation is required.

> Packages are built by GitHub Actions on real macOS and Windows runners whenever
> a `v*` tag is pushed (see [`.github/workflows/release.yml`](.github/workflows/release.yml));
> binaries are not committed to the repository. The links above become active
> once the first release has been produced.

## Features

- Three detection sources: file integrity, SSH brute force, and sudo / su privilege abuse.
- File integrity is based on SHA-256 baseline diffing, reporting modified, deleted and added files.
- Two working modes: one-shot scans for cron, and a resident real-time monitor.
- The real-time monitor debounces events, so one file save triggers exactly one check.
- Authentication log parsing covers sshd, sudo and su records, detecting failure bursts and unauthorised escalation.
- All events are stored in a single-file SQLite database and remain queryable.
- Alerting supports DingTalk webhooks and SMTP email, deduplicated by event fingerprint within a time window.
- A failing alert never interrupts the detection pipeline.
- Built-in FastAPI dashboard with source and severity filters and pagination.
- The dashboard uses SSE push and issues no requests at all while idle.
- Detection commands exit with status 1 on findings, so they compose into shell scripts and monitoring systems.
- Data and configuration paths are overridable by environment variable, for container volumes and multi-environment deploys.
- A non-root, health-checked Docker image is provided.
- PyInstaller packaging produces a standalone desktop app requiring no Python on the target machine.
- Core logic is covered by 89 pytest unit tests that neither touch the network nor require a database.

## Detection rules

| Subcommand | Subject | Trigger | Severity |
|---|---|---|---|
| `check` | files listed in the config | SHA-256 differs from baseline (modified / deleted) | critical |
| `check` | files newly added to the config | absent from the baseline (added) | warning |
| `ssh-check` | sshd records in auth.log | 5 failed logins from one IP within 60s | critical |
| `sudo-check` | sudo / su records in auth.log | 3 authentication failures from one user within 60s | critical |
| `sudo-check` | sudo records in auth.log | any `user NOT in sudoers` line | critical |

All thresholds are configurable. `user NOT in sudoers` bypasses the threshold and
is reported on a single occurrence — an account with no sudo rights attempting to
escalate is suspicious on its own. A lone failed `su` is ignored, so a mistyped
password is not mistaken for an attack.

## Requirements

- macOS, Linux or Windows.
- Python 3.10 or newer (the code uses `X | None` and `list[X]` type-hint syntax).
- Runtime dependencies `PyYAML`, `fastapi`, `uvicorn` and `watchdog` are installed automatically.

> SSH and privilege detection require a text-format authentication log:
> `/var/log/auth.log` on Debian / Ubuntu, `/var/log/secure` on RHEL / CentOS.
> macOS has no such file, so only file integrity monitoring and the dashboard
> are available there.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pyhids --help
```

Don't want a Python environment? Use the packaged desktop build — see
[Download](#download).

## Usage

1. Edit `config/watchlist.yaml` with the files to monitor and the authentication log path.
2. Build a baseline while the system is trusted: `pyhids baseline`.
3. Run detections as needed: `pyhids check`, `pyhids ssh-check`, `pyhids sudo-check`.
4. For immediate reaction to file changes, use the resident mode: `pyhids watch` (Ctrl+C to stop).
5. Review history with `pyhids events --limit 20`, or start `pyhids serve` and open <http://127.0.0.1:8000>.
6. Filter by source and severity on the dashboard, and page back through older records.

| Command | Description |
|---|---|
| `pyhids baseline` | Scan the configured files and record SHA-256 fingerprints |
| `pyhids check` | Diff against the baseline: modified / deleted / added |
| `pyhids ssh-check` | Parse the auth log for SSH brute force |
| `pyhids sudo-check` | Parse the auth log for sudo / su privilege abuse |
| `pyhids events` | Query stored events, supports `--limit` and `--source` |
| `pyhids watch` | Resident real-time file monitoring |
| `pyhids serve` | Start the web dashboard |

`check`, `ssh-check` and `sudo-check` exit 1 when they find something:

```bash
pyhids check || echo "file tampering detected"
```

> When the baseline is built decides whether any of this means anything. The
> baseline *is* the definition of "normal", so building it on an
> already-compromised host permanently whitelists the backdoor.

## Configuration

See `config/watchlist.yaml`:

```yaml
algorithm: sha256

paths:                              # files to monitor for integrity
  - /etc/passwd
  - /etc/ssh/sshd_config
  - /root/.ssh/authorized_keys

ssh:
  log_path: /var/log/auth.log
  window_seconds: 60
  threshold: 5

sudo:
  log_path: /var/log/auth.log
  window_seconds: 60
  threshold: 3

alert:
  dingtalk_webhook: ""              # set to enable DingTalk push
  dedup_window_seconds: 3600        # same issue alerts at most once per window
  email_host: ""                    # set to enable SMTP email
  email_port: 587
  email_user: ""
  email_password: ""
  email_from: ""
  email_to: ""
```

Paths can be overridden by environment variables — the mechanism Docker and the
desktop app use to relocate their data:

| Variable | Default |
|---|---|
| `PYHIDS_DB_PATH` | `data/events.db` |
| `PYHIDS_BASELINE_PATH` | `data/baseline.json` |
| `PYHIDS_CONFIG_PATH` | `config/watchlist.yaml` |
| `PYHIDS_DATA_DIR` | desktop app data directory |

The desktop app seeds a configuration in the user data directory on first launch
and never overwrites it afterwards:

| Platform | Directory |
|---|---|
| macOS | `~/Library/Application Support/PyHIDS/` |
| Linux | `~/.local/share/pyhids/` |
| Windows | `%APPDATA%\PyHIDS\` |

It holds `watchlist.yaml`, `events.db`, `baseline.json` and `pyhids.log`. A
double-clicked app has no terminal, so `pyhids.log` is the only place startup
errors appear.

## Event storage format

Every event goes into one SQLite table, with source-specific fields kept as JSON
in the `payload` column. Adding a detection source requires no schema change:

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,      -- ISO 8601 timestamp
    source      TEXT NOT NULL,      -- file_integrity | ssh_brute_force | privilege_escalation
    severity    TEXT NOT NULL,      -- info | warning | critical
    summary     TEXT NOT NULL,      -- one human-readable line
    payload     TEXT NOT NULL       -- JSON string, source-specific fields
);
```

A single event from `/api/events` looks roughly like this:

```json
{
  "detected_at": "2026-08-03T19:11:41.594062",
  "source": "privilege_escalation",
  "severity": "critical",
  "summary": "bob 提权失败风暴（3 次 / 窗口 2026-05-08 12:00:00 → 2026-05-08 12:00:16）",
  "payload": {
    "user": "bob",
    "kind": "burst",
    "fail_count": 3,
    "window_start": "2026-05-08T12:00:00",
    "window_end": "2026-05-08T12:00:16"
  }
}
```

## Dashboard

```bash
pyhids serve --host 127.0.0.1 --port 8000
```

- Events are listed newest first; critical is red, warning is orange.
- Filter by source and severity, and choose the page size, from the header.
- Previous / next buttons sit at the bottom, with the live-connection indicator on the right.
- New events arrive over SSE without a page refresh; auto-refresh pauses past page 1 so browsing history is not interrupted.
- `/api/events` and `/api/stream` are available for external integration.

> The dashboard has no authentication and binds `127.0.0.1` by default. Do not
> expose it publicly — use an SSH tunnel, or an authenticating reverse proxy.

## Architecture

The project is organised in three layers with a strict downward dependency:

- **Domain** (`checker.py`, `ssh_check.py`, `sudo_check.py`, `watch.py`): pure detection logic. It never imports the storage layer; it exposes `event_from_*` factories declaring what events it can produce.
- **Infrastructure** (`store.py`, `alert.py`, `web.py`): database access, alert delivery, web serving.
- **Adapter** (`cli.py`, `app.py`): parses arguments and hands domain-produced events to infrastructure for storage and alerting.

The immediate payoff is that almost every unit test runs without a database —
all 89 finish in 0.3 seconds. The real-time monitor follows the same rule,
delegating storage and alerting through an `on_change` callback.

A few implementation details worth noting:

- The debouncer takes "now" as a parameter instead of reading the clock itself, which makes the timing logic testable without sleeping.
- Alert dedup fingerprints use only stable identifiers (user, IP, problem type) and deliberately exclude window boundaries, which would change as the window slides and silently break dedup.
- SSE pushes only the event-id cursor rather than event content, so filtering and pagination stay in the existing frontend code instead of being reimplemented in the stream.
- Path constants read their environment variables at import time, so the desktop app entry point defers those imports until after the data directory has been initialised.

## Running tests

```bash
python3 -m pytest -v
```

89 tests are expected to pass. They neither use the network nor write to a real
database — everything goes through pytest temporary directories.

## Packaging

### Desktop app

```bash
pip install -e ".[dev]"
pyinstaller pyhids.spec --noconfirm
```

The result is `dist/PyHIDS.app` on macOS (about 32 MB). The bundled binary keeps
the full command-line interface:

```bash
dist/PyHIDS.app/Contents/MacOS/PyHIDS check
```

`dist/` and `build/` are generated and stay out of Git.

To publish downloadable packages, push a `v` tag — GitHub Actions builds on both
macOS and Windows and attaches the results to the matching GitHub Release:

```bash
git tag v1.2.1
git push origin v1.2.1
```

The workflow runs the full test suite before packaging, so a failing test means
no installer is produced. It can also be started manually from the Actions tab.

> The packages are not code-signed. Running them locally is unaffected, but
> macOS will warn recipients about an unidentified developer — right-click the
> icon and choose "Open". Signing and notarisation require an Apple developer
> account.

### Docker

```bash
docker compose up -d --build
```

The image runs as the unprivileged user `pyhids` (UID 1000) with a healthcheck
against `/api/events`. On Linux, make the mounted `data/` writable by that UID:

```bash
sudo chown -R 1000:1000 data
```

Mount monitored directories read-only. A container only sees its own filesystem,
so configured paths that were never mounted are reported as deleted:

```yaml
volumes:
  - /etc:/host/etc:ro     # then use /host/etc/... paths in the config
```

The `:ro` is not decoration: if PyHIDS itself is compromised, the attacker still
cannot tamper with what it watches.

## Server deployment

Build the baseline while the system is trusted, then schedule the checks with
cron (absolute paths — cron's PATH is nearly empty):

```bash
sudo pyhids baseline
```

```bash
*/10 * * * * /opt/pyhids/.venv/bin/pyhids check      >> /var/log/pyhids.log 2>&1
*/5  * * * * /opt/pyhids/.venv/bin/pyhids ssh-check  >> /var/log/pyhids.log 2>&1
*/5  * * * * /opt/pyhids/.venv/bin/pyhids sudo-check >> /var/log/pyhids.log 2>&1
```

For file monitoring, a resident service beats cron by a wide margin — seconds
instead of minutes. Example systemd unit:

```ini
[Unit]
Description=PyHIDS real-time file monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/pyhids
ExecStart=/opt/pyhids/.venv/bin/pyhids watch
Restart=always

[Install]
WantedBy=multi-user.target
```

## Caveats

- The baseline must be built on a trusted system, or existing backdoors are recorded as normal.
- `baseline.json` is itself a target: an attacker who plants a backdoor and reruns `pyhids baseline` has erased the evidence. Make it root-owned and read-only in production, and diff it against a copy on a separate host.
- Reading `/var/log/auth.log` requires privileges — use root's crontab, or add the running user to the `adm` group.
- The dashboard has no authentication and should not be exposed publicly.
- Log parsing requires text-format log files; systems with only systemd-journald are not supported yet.
- Every check inserts a new row, so the dashboard shows repeats. Alerting is deduplicated by time window; storage is not.
- This version does not include process monitoring, listening-port change detection, or rootkit detection.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
