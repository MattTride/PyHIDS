# PyHIDS 项目交接文档

最后更新：2026-07-30
当前进度：**v1.2.0 —— roadmap 全部完成 + 桌面 App 打包**（文件完整性 + 实时监控 + SSH/提权检测 + 持久化 + 告警 + SSE 仪表盘 + 打包与加固过的 Docker 部署）

---

## 1. 项目简介

**PyHIDS** 是一个用 Python 写的轻量级**主机入侵检测系统（HIDS）**，定位类似简化版 OSSEC / Wazuh，运行在单台机器上。

**部署目标**：Linux（生产环境）。开发可以在 macOS / Windows 上做，跑测试时用合成的 auth.log 文件。

**技术栈**：
- Python 3.14
- 第三方依赖：`PyYAML`、`watchdog`、`pytest`（dev）
- 数据库：SQLite（标准库，单文件）

仓库：<https://github.com/MattTride/PyHIDS>

---

## 2. 当前进度

### 已交付的能力（用户可见）

| 命令 | 作用 | 退出码语义 |
|---|---|---|
| `pyhids baseline` | 扫描配置中的文件，生成 SHA-256 指纹基线到 `data/baseline.json` | 0 |
| `pyhids check` | 对比基线，找出 modified / deleted / added 文件；自动落库 | 0 = 无异常，1 = 有异常 |
| `pyhids ssh-check` | 解析 `auth.log`，检测 SSH 暴破（60s/5 次默认）；自动落库 | 0 = 无异常，1 = 有异常 |
| `pyhids events [--limit N] [--source X]` | 查询历史事件（来自上面两个检测的落库结果） | 0 |
| `pyhids --log-level DEBUG <subcmd>` | 全局日志级别 flag，对所有子命令生效 | - |

### 里程碑完成情况

| 里程碑 | 内容 | 状态 |
|---|---|---|
| **M1** 文件完整性监控 | hasher / config / baseline / checker / CLI 双子命令 | ✅ 完成 |
| **M1.6** 测试覆盖 | 9 个 pytest 测试 | ✅ 完成 |
| **M2.0** logging 地基 | `setup_logging` + `--log-level` flag | ✅ 完成 |
| **M2.1** SSH 暴破检测 | 6 个子任务，从单行解析到 CLI 接入 | ✅ 完成 |
| **M2.1.6** 测试覆盖 | 11 个 pytest 测试 | ✅ 完成 |
| **M2.2.1-2.2.5** SQLite 持久化 | 建表 / 写 / 读 / CLI 查询 / 自动落库 | ✅ 完成 |
| **M2.2.6** store 测试 | store.py 的 pytest（5 个） | ✅ 完成 |
| **M2.2.7** 工厂函数测试 | checker + ssh_check 工厂函数测试（4 个） | ✅ 完成 |
| **M2 技术债清理** | 修 strptime / window_start，删 exclude 死字段，补 .gitignore | ✅ 完成 |
| **M3.1-3.2** 告警基础 | `format_alert` 纯函数 + 钉钉 webhook 发送（`alert.py`） | ✅ 完成 |
| **M3.3** 告警接线 | `alert_if_critical` 闸门 + 配置 + CLI 挂载 + 失败不中断 | ✅ 完成 |
| **M4.1-4.4** Web 仪表盘 | FastAPI `/api/events` + HTML 页面 + 5s 自动刷新 + `pyhids serve` | ✅ 完成 |
| **M3.4** 告警去重 | `dedup_key` 指纹 + 时间窗查询 + CLI 闸门（窗口内不重复告警） | ✅ 完成 |
| **M3.5** 邮件渠道 | `send_email`(SMTP) + 配置字段 + `alert_if_critical` 多渠道分发 | ✅ 完成 |
| **M4.5** 仪表盘过滤 | query_events 动态 WHERE(source/severity)+ /api/events 透传 + 前端下拉框 | ✅ 完成 |
| **M5.1** 打包 | `pyproject.toml` + console script，`pip install -e .` 后可直接敲 `pyhids` | ✅ 完成 |
| **M5.2** 路径可配置 | 三个 `PYHIDS_*_PATH` 环境变量，覆盖 cwd 相对的硬编码默认值 | ✅ 完成 |
| **M5.3** 容器化 | `Dockerfile` + `.dockerignore`，slim 基础镜像 + 分层缓存 | ✅ 完成 |
| **M5.4** 编排与文档 | `docker-compose.yml`（挂卷 + 端口）+ README Docker 章节 | ✅ 完成 |
| **M2.3** 实时文件监控 | `Debouncer` 去抖动 + watchdog observer + `pyhids watch` 子命令 + 8 个测试 | ✅ 完成 |
| **M5.5** 容器加固 | 非 root 用户（UID 1000）+ `HEALTHCHECK`（标准库发请求，不装 curl） | ✅ 完成 |
| **M2.4** 提权检测源 | `sudo_check.py`：失败风暴 + 非授权提权 + `pyhids sudo-check` + 15 个测试 | ✅ 完成 |
| **M4.6** 仪表盘增强 | `/api/stream` SSE 推送替代 5s 轮询 + offset 分页 + 上/下页 + 8 个测试 | ✅ 完成 |
| **M6** 桌面 App | `app.py` 应用模式 + PyInstaller 打包成 `PyHIDS.app` + 12 个测试 | ✅ 完成 |

### 测试套件现状

```
$ pytest -v
89 passed in 0.31s
```

| 测试文件 | 测试数 |
|---|---|
| `tests/test_hasher.py` | 4 |
| `tests/test_checker.py` | 5 |
| `tests/test_load_baseline.py` | 2 |
| `tests/test_ssh_check.py` | 13 |
| `tests/test_store.py` | 11 |
| `tests/test_alert.py` | 8 |
| `tests/test_web.py` | 6 |
| `tests/test_watch.py` | 8 |
| `tests/test_sudo_check.py` | 15 |
| `tests/test_app.py` | 12 |

---

## 3. 下一步要做的事（按优先级）

### 🔴 立即（下一步）

**roadmap 上的所有里程碑都已完成**（89 个测试全绿）。已打 tag：`v1.0.0`（M1–M5 + M2.3）、
`v1.1.0`（M5.5 + M2.4 + M4.6）、`v1.2.0`（M6 桌面 App）。

三种分发形态都可用：`pip install -e .` / `docker compose up -d` / 双击 `PyHIDS.app`。

如果以后还想继续，剩下的都是全新方向，不是收尾：

- **存储去重**：目前每次检测都落一行，仪表盘会看到重复行；如需"每个问题一行"
  可在落库层也去重（注意会丢"上次见到"的信息）。这是当前最明显的可改进点。
- **更多检测源**：端口监听变化（`ss -tlnp` 快照对比）、crontab 改动、新增 setuid 文件。
  每加一个都不用改表，只要写一个 `event_from_*` 工厂函数。
- **告警渠道**：Slack / Telegram / syslog，照着 `send_dingtalk` / `send_email` 的形状写。
- **`--daemon` 模式**：把 `watch` + 定时 `ssh-check` / `sudo-check` 合成一个进程，
  配 systemd unit 文件。
- **规则引擎**：现在检测逻辑写死在代码里，可考虑把阈值/模式做成 YAML 规则文件。

### 🟡 M2 里程碑收尾后

参考 [README.md](README.md) 的 roadmap，待办：

| 里程碑 | 内容 | 备注 |
|---|---|---|
| **M3 告警** ✅ | 钉钉 + 邮件双渠道 + 窗口去重（全部完成） | 去重 M3.4、邮件 M3.5 均已做 |
| **M4 Web 仪表盘** ✅ | FastAPI `/api/events` + HTML + 5s 轮询；`pyhids serve`；source/severity 过滤(M4.5) | 已完成。SSE 真推送 / 分页待做 |
| **M5 Docker** ✅ | `pyproject.toml` 打包 + 环境变量路径 + Dockerfile + compose | 已完成 |

### 🟢 技术债 / 优化点

**✅ 已清理（2026-05-30）**：

- `strptime` 年份废弃警告 → 解析前拼接当前年份（`ssh_check.py`）
- `window_start` 不精确 → 改用窗口内最早失败时间 `min(in_window)`（`ssh_check.py:detect_brute_force`）
- `exclude` 死字段 → 已从 `Config` / `watchlist.yaml` / 打印中删除（目录监控留作未来功能）
- Python 版本下限 → 已在 README 标注「需要 Python 3.10+」
- `data/events.db` 未被忽略 → 已补进 `.gitignore`（防安全数据泄到公开仓库）
- `watchdog` 声明但未使用 → M2.3 已真正用上（`watch.py`），并加进 `pyproject.toml` 的 `dependencies`
- 镜像用 root 跑 → M5.5 已改成非 root 用户 `pyhids`（UID 1000）+ `HEALTHCHECK`

**仍待办**：

| 待办 | 出处 | 影响 |
|---|---|---|
| **`output_report` print 风格不统一** | `ssh_check.py` vs `checker.py` | 纯展示层小问题，优先级最低 |
| **`requirements.txt` 与 `pyproject.toml` 并存** | 两处都列依赖，可能漂移 | 短期无害（前者给 `pip install -r`，后者才是权威）；长期可只留 pyproject |

---

## 4. 仓库结构

```
/Users/Tride/PyHIDS/
├── pyhids/                       ← Python 包，所有源代码
│   ├── __init__.py
│   ├── alert.py                  # 告警：format_alert / send_dingtalk / send_email / 多渠道分发
│   ├── app.py                    # 桌面 App 模式：数据目录 / bootstrap / 自启动仪表盘
│   ├── baseline.py               # 文件指纹基线生成与持久化
│   ├── checker.py                # 文件完整性检测 + Event 工厂
│   ├── cli.py                    # argparse 入口（5 个子命令：baseline/check/ssh-check/events/serve）
│   ├── config.py                 # YAML 配置加载（Config / SSHConfig dataclass）
│   ├── hasher.py                 # 文件 SHA-256 计算
│   ├── log.py                    # logging 中央配置
│   ├── ssh_check.py              # SSH 暴破检测 + Event 工厂
│   ├── sudo_check.py             # sudo/su 提权滥用检测 + Event 工厂
│   ├── store.py                  # SQLite 事件持久化（Event / insert / query）
│   ├── watch.py                  # 实时监控：Debouncer 去抖动 + watchdog observer
│   └── web.py                    # FastAPI 仪表盘（/api/events + /api/stream SSE + HTML）
├── tests/                        ← pytest 测试套件
│   ├── test_hasher.py            (4 个测试)
│   ├── test_checker.py           (5 个测试)
│   ├── test_load_baseline.py     (2 个测试)
│   ├── test_ssh_check.py         (13 个测试)
│   ├── test_sudo_check.py        (15 个测试)
│   ├── test_store.py             (11 个测试)
│   ├── test_alert.py             (8 个测试)
│   ├── test_watch.py             (8 个测试)
│   └── test_web.py               (6 个测试)
├── config/
│   ├── watchlist.yaml            # 开发用配置（指向 demo_files）
│   └── watchlist.default.yaml    # App 首次启动复制给用户的默认配置（绝对路径）
├── data/                         ← 运行时数据（基线 + DB），部分入库
│   ├── baseline.json             (跟踪，但每次 baseline 都会更新)
│   └── events.db                 (gitignored，运行时生成)
├── demo_files/                   ← 用于测试的样本数据
│   ├── auth.log                  (合成的 sshd 日志，含 1.2.3.4 暴破场景)
│   ├── etc/{hosts,passwd}
│   └── home/authorized_keys
├── launcher.py                   # PyInstaller 的入口脚本
├── pyhids.spec                   # PyInstaller 打包配置（datas / hiddenimports / BUNDLE）
├── pyproject.toml                # 包元数据 + 依赖 + `pyhids` console script（权威依赖清单）
├── Dockerfile                    # 容器镜像：python:3.13-slim + pip install + serve
├── docker-compose.yml            # 编排：端口映射 + data/config/被监控目录挂卷
├── .dockerignore                 # 构建上下文排除（.venv / .git / data 等）
├── requirements.txt              # 旧依赖清单（保留兼容，权威以 pyproject.toml 为准）
├── .gitignore                    # Python 标准模板 + `!demo_files/*.log` 反向白名单
├── README.md                     # 项目介绍 + roadmap
├── HANDOFF.md                    # 本文件
└── LICENSE
```

---

## 5. 架构与关键设计决策

### 5.1 分层与依赖方向（重要）

```
┌──────────────────────────────────────┐
│  cli.py（适配器层 / Adapter）          │  ← 解析参数，调用领域和基础设施
└────┬──────────┬──────────┬──────────┘
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│checker  │ │ssh_check│ │ ...     │  ← 领域层（Domain），纯逻辑
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     └───────────┴───────────┘
                 ▼
            ┌────────┐
            │store.py│  ← 基础设施（Infrastructure），DB 操作
            └────────┘
```

**规则**：
- 领域层（`checker` / `ssh_check`）**不能** import 基础设施（`store`）逻辑去主动写库
- 领域层**可以**定义 Event 工厂函数（`event_from_*`），是"我能转换成什么 Event"的能力声明
- **CLI** 才是把领域和基础设施粘起来的地方（`event = factory(...)` → `insert_event(event)`）

这样的好处：现有 20 个测试**完全不需要数据库**就能跑，因为它们测的是领域层的纯函数。

### 5.2 配置系统

YAML（`config/watchlist.yaml`）→ `dataclass` 树：

```yaml
algorithm: sha256
paths: [...]
exclude: [...]                    # 已声明，未实现
scan_interval: 60                 # 已声明，未实现
ssh:
  log_path: demo_files/auth.log   # 本地开发；生产 /var/log/auth.log
  window_seconds: 60
  threshold: 5
```

对应：

```python
@dataclass
class SSHConfig:
    log_path: str = "/var/log/auth.log"
    window_seconds: int = 60
    threshold: int = 5

@dataclass
class Config:
    algorithm: str = "sha256"
    paths: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    scan_interval: int = 60
    ssh: SSHConfig = field(default_factory=SSHConfig)
```

**坑**：`yaml.safe_load` 返回的 nested dict 需要在 `load_config()` 里**手动**转 SSHConfig：

```python
ssh_data = data.pop("ssh", {})
data["ssh"] = SSHConfig(**ssh_data)
return Config(**data)
```

### 5.3 事件 Schema（SQLite）

**单表 + JSON payload** 方案（vs 每个事件源一张表）：

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,        -- ISO 时间戳
    source TEXT NOT NULL,              -- 'file_integrity' | 'ssh_brute_force'
    severity TEXT NOT NULL,            -- 'info' | 'warning' | 'critical'
    summary TEXT NOT NULL,             -- 一句话给人看
    payload TEXT NOT NULL              -- JSON 字符串，源专属字段
);
CREATE INDEX idx_events_detected_at ON events(detected_at);
CREATE INDEX idx_events_source ON events(source);
```

**好处**：新事件源（比如 sudo 日志）不用改表，只要新写一个工厂函数。

**对应 Python 数据类**：

```python
@dataclass
class Event:
    detected_at: datetime
    source: str
    severity: str
    summary: str
    payload: dict
```

序列化由 `insert_event` 处理（`datetime.isoformat()` + `json.dumps(payload, ensure_ascii=False)`），反序列化由 `query_events` 对称处理（`datetime.fromisoformat` + `json.loads`）。

### 5.4 日志系统

`pyhids/log.py` 提供 `setup_logging(level)`，CLI 启动时调一次。每个模块开头：

```python
import logging
logger = logging.getLogger(__name__)
logger.info("xxx %s", value)   # 用 % 占位符，不用 f-string
```

**重要**：用 `%s` 占位符而不是 f-string，因为 Python logging 的延迟格式化能在该 level 被静音时跳过字符串构造，性能更优。

### 5.5 退出码语义

跟 Unix 工具惯例对齐：

| 命令 | 检测有问题 | 检测无问题 | 参数错误 |
|---|---|---|---|
| `pyhids baseline` | - | 0 | argparse 接管 |
| `pyhids check` | **1** | 0 | argparse 接管 |
| `pyhids ssh-check` | **1** | 0 | argparse 接管 |
| `pyhids events` | - | 0（只是查询） | argparse 接管 |

这样 cron / systemd / shell 脚本能用 `pyhids check || alert` 自动触发告警。

---

## 6. 如何运行 / 测试

### 6.1 装环境

```bash
git clone https://github.com/MattTride/PyHIDS.git
cd PyHIDS
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # 装完 `pyhids` 命令就能直接用（不必再 python -m pyhids.cli）
```

或者用 Docker，不碰本机 Python 环境：

```bash
docker compose up -d                        # 仪表盘 http://127.0.0.1:8000
docker compose exec pyhids pyhids check
docker compose down
```

> 项目用了 Python 3.10+ 语法（`str | None`、`list[X]` 等），低版本不行。

### 6.2 跑一遍完整 demo

```bash
# 建立基线
python -m pyhids.cli baseline

# 改一个被监控的文件
echo "# 模拟篡改" >> demo_files/etc/hosts

# 检测（应该报告 1 处异常，自动落库）
python -m pyhids.cli check

# SSH 检测（应该报告 1.2.3.4 暴破，自动落库）
python -m pyhids.cli ssh-check

# 查询历史事件
python -m pyhids.cli events

# 还原
git checkout -- demo_files/etc/hosts
```

### 6.3 跑测试

```bash
python -m pytest -v
```

期望 89 passed。

### 6.4 看 DB 内容（调试用）

```bash
sqlite3 data/events.db ".schema"          # 看表结构
sqlite3 data/events.db "SELECT * FROM events;"   # 看所有事件
```

---

## 7. 编码风格 / 约定

- **dataclass** 是默认的数据容器（不要用纯 dict 表示有固定结构的事物）
- **类型注解**所有公开函数，使用 Python 3.10+ 语法（`str | None` 而不是 `Optional[str]`）
- **模块顶部** logger：`logger = logging.getLogger(__name__)`
- **领域 / 展示分离**：每个领域模块（`checker.py` / `ssh_check.py`）有自己的 `output_*` / `print_*_report` 函数；CLI 只负责调度
- **f-string 仅用于格式化**，不用于日志（日志用 `logger.info("...%s...", value)`）
- **测试文件命名**：`tests/test_<module>.py`，一个模块对应一个测试文件
- **DEFAULT_*_PATH** 常量统一在模块顶部定义

### Git 风格

- Commit message 格式：`M{x}.{y}.{z}: <description>`（参考 git log）
- 不 commit `data/baseline.json` 和 `data/events.db`（运行时数据）
- HEREDOC 写多行 commit message：

```bash
git commit -m "$(cat <<'EOF'
M2.2.6: ...

- 第一行
- 第二行
EOF
)"
```

---

## 8. 已知坑点 / 学习记录

下面是开发过程中遇到的实际 bug，留给接手的人参考（避免重蹈覆辙）。

| 类别 | 现象 | 教训 |
|---|---|---|
| **缩进塌方** | 函数体或 `if/for` 块缩进错位，Python 不报错但行为不对 | 嵌套结构先写骨架，不要从上往下顺写 |
| **if/else 写反** | `sys.exit(0)` vs `sys.exit(1)` 颠倒；三元表达式两个分支搭错标签 | 写之前用大白话念一遍："如果 X 那 A 否则 B" |
| **字符串大小写敏感** | `"Failed" != "failed"` 永远 True，导致条件永远走错分支 | 比较前 print(repr(value)) 看实际值 |
| **类 vs 实例** | `BruteForceAttempt.ip` 访问类属性失败 | `for item in list:` 里 item 是**实例**不是类 |
| **dict vs dataclass** | `summary.total_attempts`（点号）vs `summary["total_attempts"]`（方括号）混用 | dict 用 `[]`，dataclass 用 `.` |
| **变量被字符串包住** | `sqlite3.connect("str(db_path)")` 传了字面字符串 | 想用变量就不要加引号 |
| **Python 标识符不能含连字符** | `def f(db-path: Path):` 报 SyntaxError | CLI flag 用 `--log-path`，参数名用 `log_path` |
| **strptime 默认年份是 1900** | datetime 解析没指定年份默认 1900 | 用 `datetime.now().year` 或拼 `%Y` 前缀 |
| **`*.log` 被 gitignore 默认吞掉** | `demo_files/auth.log` 加进仓库时被忽略 | 加 `!demo_files/*.log` 反向白名单 |
| **重复定义同名函数** | 文件里写了两份 `load_config`，后定义的覆盖前面的 | commit 前 grep 一下函数名出现次数 |
| **argparse subparser 加错位置** | `parser.add_argument` vs `parser_ssh.add_argument` | 子命令专属 flag 必须加在子 parser 上 |
| **`args.x(args.y)` 把变量当函数调** | 借鉴函数调用语法误用为"取第一个非空" | 用 `args.x or fallback` |
| **IDE 幽灵 import** | `from asyncio import events` 这种你没主动写的 import | commit 前扫一眼 import 区 |
| **Python logging format 占位符拼写** | `%(messages)s` 多个 s 导致 KeyError | 严格记 4 个核心占位符：`asctime` / `levelname` / `name` / `message` |
| **位置参数 vs 关键字参数** | `query_events(db_path)` 把路径塞给了第一个参数 `limit`，SQLite 报 `PosixPath not supported` | 多参数函数调用一律用关键字：`query_events(db_path=db_path)` |
| **边界条件 `>` vs `>=`** | `len(in_window) > threshold` 让"恰好达阈值"被放过，阈值悄悄 +1 | "达到即触发"用 `>=`；写之前把语义念一遍 |
| **改骨架漏改条件** | 把 `> 0` 改成阈值时只换了数字成 `> threshold`，漏了 `>`→`>=` | 改一处时把整行语义都过一遍，别只盯着改动的那个字 |
| **改错文件** | 把 test_checker 的测试敲进了 test_store.py | 动手前确认 PyCharm 当前标签页就是目标文件 |
| **`@patch` 装饰器与注入参数成对** | 写了 `mock_send` 参数却漏了 `@patch(...)` → pytest 报 `fixture 'mock_send' not found` | 有 mock 参数就必有对应的 `@patch` 装饰器 |
| **mock `side_effect` 模拟失败** | 想测"发送失败被吞掉"，需让替身主动抛错 | `mock.side_effect = RuntimeError(...)`，再断言主流程不崩 |
| **导入位置错** | `from fastapi import TestClient` → NameError；它在子模块 `fastapi.testclient` | 子模块里的东西要从子模块导：`from fastapi.testclient import TestClient` |
| **方法忘加 `()`** | `data = response.json`（没调用）→ `'method' object is not subscriptable` | `json` 是函数本身，`json()` 才是它的返回值 |
| **字典键值搭错** | `"severity": e.summary`（值放错）、还漏了 summary 键 | 只能靠测试抓；断言报错会直接显示"严重等级里装了摘要" |
| **验证要够"真"才算数** | M3.3c ssh-check 漏接告警，因 webhook 为空、跑起来看不出，蒙混过提交 | 验证条件要能真正暴露 bug；旁路功能尤其要构造"会触发"的场景，改完先读文件审一遍再跑 |
| **`Dockerfile` 建成了文件夹** | 在 IDE 里点了 New → Directory，`docker build` 找不到构建文件 | `Dockerfile` 是**无扩展名的文本文件**；建完用 `ls -la` 看开头是 `-` 还是 `d` |
| **环境变量值少写文件名** | `ENV PYHIDS_DB_PATH=/data`（目录），程序 `sqlite3.connect("/data")` 直接炸 | 覆盖一个默认值时，**新值必须和默认值同类型**：默认是 `data/events.db`（文件），就得给文件路径 |
| **相邻两个空填反** | `EXPOSE 127.0.0.1` —— 地址填进了要端口的位置 | 填空前把每行念成大白话：「暴露**端口** 8000」「监听**地址** 0.0.0.0」，一念就发现错位（同「if/else 写反」） |
| **构建时读的文件没拷进镜像** | `pyproject.toml` 里 `readme = "README.md"` / `license = {file=...}`，但 Dockerfile 只 COPY 了 pyproject → `pip install` 报 readme not found | `pip install .` 会**真的去读**这些文件；`.dockerignore` 也别一刀切 `*.md` |
| **核心参数在核心逻辑里没被用到** | `Debouncer.due()` 的判断里完全没出现 `quiet_period`，于是永远返回 False | 写完检查「参数和属性是否都真的用上了」；PyCharm 把变量标灰就是信号 |
| **拿"时刻"和"时刻"比** | `if self._last_event_at > now`（语义=上次事件发生在未来，永远假）；应是 `now - last >= quiet_period` | 「过了多久」在代码里必须是**减法**；比较的两边要同量纲：时长 vs 时长，不是时刻 vs 时刻 |
| **"重置状态"写成了反方向** | 触发后调 `self.record_event(now)`（=又来一个事件，重新武装计时器），本该赋 `None`（解除武装） | 重置就是**把状态还原成初始哨兵值**，直接赋值，别调那个"记录新事件"的方法。此 bug 会导致每秒重复触发、刷爆库和告警群 |
| **长驻进程必须有关闭路径** | `observer.start()` 起的是后台线程，不 `stop()` + `join()` 会留僵尸线程、进程退不掉 | `try / except KeyboardInterrupt / finally` 三件套；`finally` 里做清理，保证任何退出方式都走到 |
| **`>>` 追加时首行被粘到上一行** | 往 `demo_files/auth.log` 追加日志，原文件结尾没换行符，第一条新记录被拼到旧记录末尾，正则匹配不上 → 检测少算一条 | 追加前先确认文件以 `\n` 结尾；追加后 `tail -3` 看一眼行边界 |
| **无限流用 TestClient 测会挂死** | 给 SSE 的 `/api/stream` 写测试，`with client.stream(...)` 退出时要等服务端生成器结束 —— 而它是 `while True`，pytest 直接卡住 | 把生成器提成模块级函数，测试里 `await anext(gen)` 取一条就 `aclose()`，不走 HTTP |
| **窗口时间不能进去重指纹** | `dedup_key` 的兜底分支用 `summary`，而提权事件的 summary 里含窗口时间 → 窗口一挪指纹就变，去重永远失效 | 指纹只取**稳定标识**（谁 + 哪类问题），不要包含会随时间变化的字段 |
| **双击启动时 cwd 是 `/`** | App 里所有相对路径（`data/events.db`）全部失效 | 桌面应用必须把数据写到**用户数据目录**，且配置里的路径要写绝对路径 |
| **模块级常量读环境变量 = 只在 import 那一刻生效** | `app.py` 若照常在文件顶部 `from pyhids.store import ...`，bootstrap() 设的环境变量就来不及生效 | App 入口里对这些模块**延迟 import**（写在函数体内），bootstrap 先跑 |
| **探测条件比真实条件更严格 → 误判** | `find_free_port` 探测时没设 `SO_REUSEADDR`，而 uvicorn 设了；上个实例刚退出、socket 在 TIME_WAIT 时被误判成"端口被占"，白白换随机端口 | 探测某资源可不可用时，**探测方式必须和真实使用方式完全一致** |
| **`pkill -f` 没杀干净导致测试误判** | E2E 测试里泄漏了 3 个 App 实例，旧实例占着 8000，新实例按设计换到随机端口，而我一直 curl 8000 → 以为 App 崩了 | 长驻进程的测试，先 `pgrep` 确认清理干净；端口要从进程日志里读，不要假设 |
| **`console=False` 打包后日志进虚空** | 双击启动没有终端，`print` 和 stdout 日志全看不见，出错无从排查 | App 模式必须额外配一个 `FileHandler` 写日志文件；`basicConfig` 重复调用要加 `force=True` 才生效 |
| **`*.spec` 被 gitignore 默认吞掉** | `pyhids.spec` 是手写的打包配置，却被 Python 模板里"忽略 PyInstaller 自动生成的 spec"那条规则吃了 | 加 `!pyhids.spec` 反向白名单（同 `demo_files/*.log` 那次）；新增关键文件后 `git status` 确认它真的出现了 |
| **`.gitignore` 不支持行尾注释** | 写成 `!pyhids.spec    # 说明文字`，整行被当成一个字面文件名，白名单不生效 | `#` 只有在**行首**才是注释；说明写在上一行 |
| **粘贴出空壳类** | `config.py` 里多了个没有类体的 `class SSHConfig:` → `IndentationError` | 「重复定义同名函数」的变体。commit 前 `grep -c "class Xxx"` 应该是 1 |
| **`Dockerfile` 建成了文件夹** | IDE 里点了 New → Directory；`docker build` 找不到构建文件 | `Dockerfile` 是**无扩展名的普通文件**；`ls -la` 看开头是 `d` 还是 `-` |
| **环境变量填成目录** | `ENV PYHIDS_DB_PATH=/data` → `sqlite3.connect("/data")` 报错 | 覆盖值要和**默认值同类型**：默认是 `data/events.db`（文件），就得填到文件名 |
| **相邻两个空填反** | `EXPOSE 127.0.0.1`（该填端口）而 `--host` 填对了 | 同「if/else 写反」。念一遍："暴露**端口** 8000""监听**地址** 0.0.0.0" |
| **`ENV` 与 `COPY` 指向不同目录** | `COPY config/ ./config/`（落在 /app/config）但 `ENV` 指向 `/config` | 路径出现在两处就必须对账；改一处就 grep 另一处 |
| **打包元数据引用的文件没进镜像** | `pyproject.toml` 写了 `readme`/`license`，Dockerfile 没 COPY → `pip install` 失败 | `COPY pyproject.toml README.md LICENSE ./`；`.dockerignore` 也别写 `*.md` 一刀切 |
| **容器里检测报大量"文件已删除"** | 容器只看得见自己的文件系统，没挂进去的被监控路径全成误报 | 被监控目录要 `-v 宿主路径:容器路径:ro` 挂进去；`:ro` 是安全纪律，不只是习惯 |

---

## 9. 联系

原作者：MattTride（GitHub）  
开发主机：MacBook Pro M1（Mac 开发，Linux 部署）

接手第一件事：
1. clone 仓库，`pip install -e ".[dev]"`，跑 `pytest -v`，确认 46 个测试全绿
2. 跑一遍第 6.2 节的完整 demo
3. `docker compose up -d` 确认容器化这条路也是通的
4. 看一眼 `git log --oneline` 理清里程碑节奏
5. 从第 3 节「立即（下一步）」里挑一个候选里程碑开工

祝你顺利。
