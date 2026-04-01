# system 模块 — 编排设计 / 2026-04-01

## 1. 设计目标

本文定义 `system` 模块的编排内核，包括：

1. 三级 Runner 的完整接口与伪代码
2. run_id 生成规范与 RunMetadata 合同
3. `_meta_runs` 表 schema
4. 全链路（scan / backtest / closeout）调用序列图
5. 错误捕获与 error_summary 规范

本文不回答：
- 上线成熟度评估（见 §02 文档）
- 治理脚本实现细节
- report 可视化

---

## 2. RunMode 枚举

```python
from enum import Enum

class RunMode(str, Enum):
    SCAN      = "scan"       # 每日信号扫描
    BACKTEST  = "backtest"   # 时间窗全链路回测
    CLOSEOUT  = "closeout"   # 主线 smoke 验证
```

---

## 3. run_id 生成规范

```python
import hashlib
from datetime import date, datetime
from uuid import uuid4

def build_run_id(
    scope: str,
    run_mode: RunMode,
    signal_date: date | None = None,
    start: date | None = None,
    end: date | None = None,
    now: datetime | None = None,
) -> str:
    """
    格式：{scope}_{runmode}_{date_tag}_{time_tag}_{hex8}

    date_tag 优先级：
      1. signal_date 不为空 → d{YYYYMMDD}
      2. start + end 不为空  → w{YYYYMMDD}_{YYYYMMDD}
      3. 其他               → n{YYYYMMDD}
    """
    current = now or datetime.utcnow()
    mode_slug = run_mode.value
    hex8 = uuid4().hex[:8]

    if signal_date is not None:
        date_tag = f"d{signal_date:%Y%m%d}"
    elif start is not None and end is not None:
        date_tag = f"w{start:%Y%m%d}_{end:%Y%m%d}"
    else:
        date_tag = f"n{current:%Y%m%d}"

    time_tag = f"t{current:%H%M%S}"
    return f"{scope}_{mode_slug}_{date_tag}_{time_tag}_{hex8}"
```

---

## 4. RunMetadata 合同与 _meta_runs 表

### 4.1 RunMetadata 数据合同

```python
@dataclass(frozen=True)
class RunMetadata:
    """单次 runner 运行的元数据合同，写入 _meta_runs。"""
    run_id: str
    scope: str                  # scan / backtest / closeout
    run_mode: str               # RunMode.value
    status: str                 # RUNNING | COMPLETED | FAILED
    signal_date: date | None
    start_date: date | None
    end_date: date | None
    strategy_name: str
    enabled_patterns: list[str]
    codes_count: int
    error_summary: str | None
    start_time: datetime
    end_time: datetime | None
    workspace_root: str
    summary_json_path: str | None
```

### 4.2 _meta_runs 表 DDL

```sql
CREATE TABLE IF NOT EXISTS _meta_runs (
    run_id          VARCHAR PRIMARY KEY,
    scope           VARCHAR NOT NULL,
    run_mode        VARCHAR NOT NULL,
    status          VARCHAR NOT NULL,       -- RUNNING | COMPLETED | FAILED
    signal_date     DATE,
    start_date      DATE,
    end_date        DATE,
    strategy_name   VARCHAR NOT NULL,
    enabled_patterns VARCHAR NOT NULL,      -- JSON 数组序列化
    codes_count     INTEGER NOT NULL DEFAULT 0,
    error_summary   VARCHAR,
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP,
    workspace_root  VARCHAR NOT NULL,
    summary_json_path VARCHAR,
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
)
```

### 4.3 生命周期写入

```python
def start_run_metadata(conn, metadata: RunMetadata) -> None:
    """运行开始时写入 RUNNING 状态。"""
    conn.execute(INSERT OR REPLACE INTO _meta_runs ...)

def finish_run_metadata(
    conn,
    run_id: str,
    *,
    status: str,
    end_time: datetime,
    summary_json_path: str | None = None,
    error_summary: str | None = None,
) -> None:
    """运行结束时更新为 COMPLETED 或 FAILED。"""
    conn.execute(UPDATE _meta_runs SET status=?, end_time=?, ... WHERE run_id=?)
```

---

## 5. Runner 1：run_daily_signal_scan（已实现）

### 5.1 接口

```python
def run_daily_signal_scan(
    signal_date: date,
    codes: list[str],
    workspace: WorkspaceRoots | None = None,
    enabled_patterns: list[str] | None = None,
    top_n: int = 20,
) -> SystemScanSummary:
```

### 5.2 调用序列

```
for code in codes:
    1. 读取日线 OHLCV（market_base.adj_daily_bar）
    2. build_malf_context_for_stock()          → MalfContext
    3. build_structure_snapshot()              → StructureSnapshot
    4. check_adverse_conditions()              → AdverseResult
       ├─ tradeable=False → filtered_out++, continue
    5. run_all_detectors(patterns=enabled_patterns)  → list[PasTrace]
    6. 过滤 triggered=True 的 trace → PasSignal
    7. 追加 signals[]
按 strength 降序排列 signals
```

### 5.3 输出合同

```python
@dataclass(frozen=True)
class SystemScanSummary:
    run_id: str
    signal_date: date
    codes_scanned: int
    codes_filtered_out: int
    signals_found: int
    pattern_counts: dict[str, int]  # pattern → count
    top_signals: list[dict]         # 前 N 个信号的 as_dict()
```

### 5.4 BPB 禁止实现

```python
# BPB 在 system 层永久禁止（已正式研究但不进入主线执行）
FORBIDDEN_PATTERNS = {"BPB"}

if enabled_patterns is None:
    enabled_patterns = [
        p.value for p, status in PAS_TRIGGER_STATUS.items()
        if status in (PasTriggerStatus.MAINLINE, PasTriggerStatus.CONDITIONAL)
        and p.value not in FORBIDDEN_PATTERNS   # 明确排除 BPB
    ]
```

---

## 6. Runner 2：run_backtest_window（待实现）

### 6.1 接口

```python
def run_backtest_window(
    start_date: date,
    end_date: date,
    codes: list[str],
    workspace: WorkspaceRoots | None = None,
    enabled_patterns: list[str] | None = None,
    initial_cash: float = 1_000_000,
    strategy_name: str = "system_backtest_v1",
) -> SystemBacktestSummary:
```

### 6.2 调用序列（全链路串联）

```
run_id = build_run_id("backtest", RunMode.BACKTEST, start=start_date, end=end_date)
start_run_metadata(conn, ...)        # 写 RUNNING

Step 1: PAS 信号扫描（批量，覆盖 [start_date, end_date]）
    for signal_date in trade_calendar(start_date, end_date):
        scan_result = run_daily_signal_scan(signal_date, codes, ...)
        pas_signals.extend(scan_result.signals)

Step 2: position 规划（批量）
    for signal in pas_signals:
        plan = compute_position_plan(signal, market_base_conn)
        exit_plan = build_exit_plan(plan)
        position_plans.append(plan)
        exit_plans[plan.code] = exit_plan

Step 3: trade 回测引擎
    backtest_summary = BacktestEngine(
        plans=position_plans,
        exit_plans=exit_plans,
        market_db=market_base_conn,
        initial_cash=initial_cash,
        run_id=run_id,
    ).run(start=start_date, end=end_date)

Step 4: 生成系统级摘要
    system_summary = SystemBacktestSummary(
        run_id=run_id,
        backtest_trade_run_id=backtest_summary.run_id,
        signal_count=len(pas_signals),
        trade_count=backtest_summary.trade_count,
        net_return_pct=backtest_summary.net_return_pct,
        max_drawdown_pct=backtest_summary.max_drawdown_pct,
        ...
    )

Step 5: 写 JSON + markdown report
    _write_json(report_dir / "backtest_summary.json", system_summary.as_dict())
    _write_markdown_report(report_dir / "backtest_report.md", system_summary)

finish_run_metadata(conn, run_id, status="COMPLETED", ...)
```

### 6.3 输出合同

```python
@dataclass(frozen=True)
class SystemBacktestSummary:
    run_id: str
    strategy_name: str
    start_date: date
    end_date: date
    codes_count: int
    enabled_patterns: list[str]
    initial_cash: float
    # child run IDs（可追溯）
    backtest_trade_run_id: str
    # 核心统计
    signal_count: int
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float | None
    avg_r_multiple: float | None
    net_return_pct: float | None
    max_drawdown_pct: float | None
    # 产物路径
    report_markdown_path: str
    report_json_path: str
```

---

## 7. Runner 3：run_system_closeout（待实现）

### 7.1 目的

`closeout` 不是生产运行，而是**主线可重跑验证**：

证明当前仓库代码能够从头独立重建一次完整的信号→持仓→回测闭环，且结果无 blocking items。

### 7.2 接口

```python
def run_system_closeout(
    stock_code: str = "000001",          # 用单只股票快速验证
    signal_date: date | None = None,     # 默认取最近可用交易日
    workspace: WorkspaceRoots | None = None,
    strategy_name: str = "system_closeout_v1",
) -> SystemCloseoutSummary:
```

### 7.3 调用序列

```
run_id = build_run_id("closeout", RunMode.CLOSEOUT, signal_date=signal_date)
start_run_metadata(conn, ...)

Step 1: 单股信号扫描
    scan_result = run_daily_signal_scan(signal_date, [stock_code], ...)
    → 检查 signals_found > 0（如无信号，记录为 WARNING，不 blocking）

Step 2: position 规划
    plan = compute_position_plan(scan_result.top_signals[0], ...)
    exit_plan = build_exit_plan(plan)
    → 检查 plan.lot_count >= 1（sanity check）

Step 3: 最小回测（单股 30 日窗口）
    backtest_summary = BacktestEngine([plan], {plan.code: exit_plan}, ...).run(
        start=signal_date, end=signal_date + timedelta(days=30)
    )
    → 检查 trade_count >= 1

Step 4: 计算 blocking_items
    blocking_items = []
    if scan_result.signals_found == 0:   blocking_items.append("无信号产生")
    if not plan:                          blocking_items.append("position 规划失败")
    if backtest_summary.trade_count == 0: blocking_items.append("无成交记录")

Step 5: 输出 SystemCloseoutSummary
    closeout_ready = len(blocking_items) == 0
    mainline_status = "FORMALLY_CLOSED" if closeout_ready else "PARTIALLY_CLOSED"

finish_run_metadata(conn, run_id, status="COMPLETED", ...)
```

### 7.4 输出合同

```python
@dataclass(frozen=True)
class SystemCloseoutSummary:
    closeout_run_id: str
    strategy_name: str
    closeout_date: date | None
    mainline_status: str             # FORMALLY_CLOSED | PARTIALLY_CLOSED
    closeout_ready: bool
    signal_count: int
    trade_count: int
    blocking_items: list[str]
    current_l1_capabilities: list[str]   # 已达到 L1 的能力清单
    pending_l2_items: list[str]          # 升到 L2 需要补齐的项
    workspace_root: str
    report_markdown_path: str
    report_json_path: str
```

---

## 8. 错误捕获规范

```python
def _safe_run_step(
    step_name: str,
    fn: Callable,
    *args,
    **kwargs,
) -> tuple[Any | None, str | None]:
    """
    统一步骤包装：捕获异常，返回 (result, error_msg)。
    result=None 且 error_msg 非空 = 步骤失败。
    """
    try:
        return fn(*args, **kwargs), None
    except Exception as e:
        error_msg = f"[{step_name}] {type(e).__name__}: {e}"
        return None, error_msg
```

### 8.1 error_summary 格式

```
[step_name] ExceptionType: 错误描述
[step_name] ExceptionType: 错误描述
...
```

每个失败步骤一行，多步骤失败则多行拼接，最终写入 `_meta_runs.error_summary`。

### 8.2 禁止行为

- 用 `pass` 或 `continue` 静默吞掉模块级异常
- 在业务模块异常时仍写 `status=COMPLETED`
- `error_summary` 为空字符串时视为无错（必须为 None 才算无错）

---

## 9. 全链路依赖图

```
run_daily_signal_scan()
    ├── lq.data (read_only)
    ├── lq.malf.pipeline.build_malf_context_for_stock()
    ├── lq.structure.detector.build_structure_snapshot()
    ├── lq.filter.adverse.check_adverse_conditions()
    └── lq.alpha.pas.detectors.run_all_detectors()

run_backtest_window()
    ├── run_daily_signal_scan() × N 日
    ├── lq.position.sizing.compute_position_plan()
    ├── lq.position.sizing.build_exit_plan()
    └── lq.trade.BacktestEngine.run()

run_system_closeout()
    ├── run_daily_signal_scan() × 1 日
    ├── lq.position.sizing.compute_position_plan()
    ├── lq.position.sizing.build_exit_plan()
    └── lq.trade.BacktestEngine.run() × 30 日窗口
```

---

## 10. 禁止操作

1. `system` 层直接查询 DuckDB 业务表做计算（只允许读 `_meta_runs` 表）
2. 在 BPB 被允许的 `enabled_patterns` 参数下运行任何 runner
3. 在子模块调用失败后继续执行后续步骤（必须 fail-fast 或记录 blocking item）
4. 生成没有 run_id 的运行记录（每次 runner 必须有 run_id）
5. `system` 层直接写 `research_lab / market_base`（只写 `trade_runtime._meta_runs` 和 temp/report 文件）
