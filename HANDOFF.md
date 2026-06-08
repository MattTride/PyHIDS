# PyHIDS 项目交接文档

最后更新：2026-05-30
当前进度：M2 全部完成（文件完整性 + SSH 检测 + SQLite 持久化 + 测试覆盖 + 技术债清理）

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

### 测试套件现状

```
$ pytest -v
42 passed in 0.26s
```

| 测试文件 | 测试数 |
|---|---|
| `tests/test_hasher.py` | 4 |
| `tests/test_checker.py` | 5 |
| `tests/test_load_baseline.py` | 2 |
| `tests/test_ssh_check.py` | 13 |
| `tests/test_store.py` | 10 |
| `tests/test_alert.py` | 6 |
| `tests/test_web.py` | 2 |

---

## 3. 下一步要做的事（按优先级）

### 🔴 立即（下一步）

**M2、M3、M4 + 告警去重(M3.4) 均已完成**（共 42 个测试全绿）。告警去重已上线：
check/ssh-check 在 `alert.dedup_window_seconds`（默认 3600s）窗口内对同一指纹不重复告警
（仍照常落库；超窗口可再报，不漏二次攻击）。

下一个里程碑可选 **M5 Docker**（见下表），或先补这几个增强：

- **邮件渠道**：当前只做了钉钉，可加 SMTP。
- **仪表盘增强**：分页 / 按 source、severity 过滤 / 用 SSE 真推送替代 5s 轮询。
- **存储去重（可选）**：目前每次检测都落一行，仪表盘会看到重复行；如需"每个问题一行"
  可在落库层也去重（注意会丢"上次见到"的信息）。

### 🟡 M2 里程碑收尾后

参考 [README.md](README.md) 的 roadmap，待办：

| 里程碑 | 内容 | 备注 |
|---|---|---|
| **M3 告警** ✅ | 钉钉 webhook + 窗口去重（已完成；邮件待加） | 去重已做（M3.4，按时间窗）；邮件待加 |
| **M4 Web 仪表盘** ✅ | FastAPI `/api/events` + HTML + 5s 轮询；`pyhids serve` 启动 | 已完成。SSE 真推送 / 过滤 / 分页待做 |
| **M5 Docker** | 容器化部署 | 需要先把 `requirements.txt` 锁完整、配置改成挂卷 |

### 🟢 技术债 / 优化点

**✅ 已清理（2026-05-30）**：

- `strptime` 年份废弃警告 → 解析前拼接当前年份（`ssh_check.py`）
- `window_start` 不精确 → 改用窗口内最早失败时间 `min(in_window)`（`ssh_check.py:detect_brute_force`）
- `exclude` 死字段 → 已从 `Config` / `watchlist.yaml` / 打印中删除（目录监控留作未来功能）
- Python 版本下限 → 已在 README 标注「需要 Python 3.10+」
- `data/events.db` 未被忽略 → 已补进 `.gitignore`（防安全数据泄到公开仓库）

**仍待办**：

| 待办 | 出处 | 影响 |
|---|---|---|
| **`watchdog` 已声明但未使用** | `requirements.txt` | 有意保留：为将来"文件实时监控"预留（用户决定留着） |
| **`output_report` print 风格不统一** | `ssh_check.py` vs `checker.py` | 纯展示层小问题，优先级最低 |
| **没有 `setup.py` / `pyproject.toml`** | - | 现在只能 `python -m pyhids.cli`，没法 `pip install -e .` 后直接 `pyhids ...` |

---

## 4. 仓库结构

```
/Users/Tride/PyHIDS/
├── pyhids/                       ← Python 包，所有源代码
│   ├── __init__.py
│   ├── alert.py                  # 告警：format_alert / send_dingtalk / alert_if_critical
│   ├── baseline.py               # 文件指纹基线生成与持久化
│   ├── checker.py                # 文件完整性检测 + Event 工厂
│   ├── cli.py                    # argparse 入口（5 个子命令：baseline/check/ssh-check/events/serve）
│   ├── config.py                 # YAML 配置加载（Config / SSHConfig dataclass）
│   ├── hasher.py                 # 文件 SHA-256 计算
│   ├── log.py                    # logging 中央配置
│   ├── ssh_check.py              # SSH 暴破检测 + Event 工厂
│   ├── store.py                  # SQLite 事件持久化（Event / insert / query）
│   └── web.py                    # FastAPI 仪表盘（/api/events + HTML + 自动刷新）
├── tests/                        ← pytest 测试套件
│   ├── test_hasher.py            (4 个测试)
│   ├── test_checker.py           (5 个测试)
│   ├── test_load_baseline.py     (2 个测试)
│   ├── test_ssh_check.py         (13 个测试)
│   ├── test_store.py             (5 个测试)
│   ├── test_alert.py             (6 个测试)
│   └── test_web.py               (2 个测试)
├── config/
│   └── watchlist.yaml            # 用户配置（监控路径、SSH 阈值等）
├── data/                         ← 运行时数据（基线 + DB），部分入库
│   ├── baseline.json             (跟踪，但每次 baseline 都会更新)
│   └── events.db                 (gitignored，运行时生成)
├── demo_files/                   ← 用于测试的样本数据
│   ├── auth.log                  (合成的 sshd 日志，含 1.2.3.4 暴破场景)
│   ├── etc/{hosts,passwd}
│   └── home/authorized_keys
├── requirements.txt              # 依赖：PyYAML + watchdog + pytest + fastapi + uvicorn + httpx
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
pip install -r requirements.txt
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

期望 20 passed。

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

---

## 9. 联系

原作者：MattTride（GitHub）  
开发主机：MacBook Pro M1（Mac 开发，Linux 部署）

接手第一件事：
1. clone 仓库，跑 `pytest -v`，确认 20 个测试全绿
2. 跑一遍第 6.2 节的完整 demo
3. 看一眼 `git log --oneline` 理清里程碑节奏
4. 从 **M2.2.6（写 store 的 pytest）** 开始干

祝你顺利。
