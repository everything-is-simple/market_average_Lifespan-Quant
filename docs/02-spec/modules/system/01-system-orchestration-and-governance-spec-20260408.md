# system 编排与治理规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/system/00-system-charter-20260331.md`。

## 1. 范围

本规格冻结：

1. `SystemRunSummary` 与 `StockScanTrace` 的当前合同字段约束
2. `run_daily_signal_scan()` 的最小执行合同与模块边界
3. `system` 对主线其他模块的读取边界与治理约束
4. `run_backtest_window / run_system_closeout / _meta_runs` 的**设计目标状态**

本规格不覆盖：

1. 未来 report 可视化
2. 完整 run metadata 持久化实现
3. 未落地治理脚本的具体实现细节

## 2. 当前实现状态

当前已核实到的 system 代码落点：

1. `src/lq/system/orchestration.py` — 已实现
2. `src/lq/system/__init__.py` — 已导出 `run_daily_signal_scan` 与 `SystemRunSummary`

当前**已实现**能力：

1. `run_daily_signal_scan()`
2. `SystemRunSummary`
3. `StockScanTrace`

当前**仅存在于 design、未在代码中核实到**的能力：

1. `run_backtest_window()`
2. `run_system_closeout()`
3. `_meta_runs` 表与 run metadata 生命周期写入
4. `scripts/system/` 治理脚本集合

因此，本规格的定位是：

- 冻结当前**已实现**的单日扫描编排合同
- 对未实现 runner 明确标注为**目标态，不冒充既成实现**

## 3. 合同字段约束

### 3.1 `StockScanTrace`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `run_id` | str | 本次扫描 run 标识 |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `long_background_2` | str | MALF 长期背景 |
| `intermediate_role_2` | str | MALF 中期角色 |
| `monthly_state` | str | 兼容细粒度月线状态 |
| `malf_context_4` | str | MALF 四格上下文 |
| `tradeable` | bool | 是否通过 filter |
| `adverse_conditions` | `tuple[str, ...]` | 触发的不利条件 |
| `adverse_notes` | str | 不利条件说明 |
| `structure_summary` | `dict[str, Any]` | 结构位轻量摘要 |
| `pas_traces` | `tuple[dict, ...]` | PAS trace 列表 |

说明：

1. `StockScanTrace` 是 system 层的解释链摘要，不是正式业务主表合同。
2. 当前它存在于返回摘要中，未核实有独立持久化表。

### 3.2 `SystemRunSummary`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `run_id` | str | 本次扫描 run 标识 |
| `signal_date` | date | 单日扫描日期 |
| `codes_scanned` | int | 扫描股票数 |
| `codes_filtered_out` | int | 被 filter 拦截的股票数 |
| `signals_found` | int | 发现信号数 |
| `pattern_counts` | `dict[str, int]` | 各 trigger 的信号计数 |
| `top_signals` | `list[dict[str, Any]]` | 按强度排序后的前 N 个信号 |
| `scan_errors` | `list[dict[str, Any]]` | 扫描失败记录 |
| `stock_traces` | `list[dict[str, Any]]` | 每股解释链 |

## 4. 当前已实现 runner：`run_daily_signal_scan()`

### 4.1 接口

```python
summary = run_daily_signal_scan(
    signal_date,
    codes,
    workspace=None,
    enabled_patterns=None,
    top_n=20,
)
```

### 4.2 当前真实调用链

1. 从 `workspace.databases.market_base` 读取日线、周线、月线数据
2. 调用 `build_malf_context_for_stock()` 构建 `MalfContext`
3. 调用 `build_structure_snapshot()` 构建 `StructureSnapshot`
4. 调用 `check_adverse_conditions()` 进行 filter 检查
5. 若 `tradeable=False`，记录解释链并过滤掉该股票
6. 若 `tradeable=True`，调用 `run_all_detectors()` 运行 PAS 探测
7. 将 triggered trace 组装为 `PasSignal`
8. 汇总为 `SystemRunSummary`

### 4.3 当前输入边界

1. `signal_date`
2. `codes`
3. `workspace`（默认 `default_settings()`）
4. `enabled_patterns`
5. `top_n`

### 4.4 当前输出边界

1. 当前已核实输出是内存中的 `SystemRunSummary`
2. 当前未在代码中核实到 JSON 落盘
3. 当前未在代码中核实到 `_meta_runs` 写入

## 5. 模块读取与写权边界

允许：

1. `system` 读取 `market_base`
2. `system` 读取 / 调用 `malf`
3. `system` 读取 / 调用 `structure`
4. `system` 读取 / 调用 `filter`
5. `system` 读取 / 调用 `alpha/pas`
6. `system` 可调用 `position.sizing` 与 `trade` 的公开入口

禁止：

1. `system` 自己实现业务计算，绕过模块公开接口
2. `system` 反向写上游业务数据库，伪造业务结果
3. `system` 在调用链中允许 `REJECTED` trigger 进入主线

## 6. BPB 治理与 trigger 边界

1. `system` 层不得让 `REJECTED` trigger 进入主线调用路径；当前至少包括 `BPB / CPB`。
2. 当前 `run_daily_signal_scan()` 的默认 `enabled_patterns` 来自 `PAS_TRIGGER_STATUS` 中 `MAINLINE / CONDITIONAL` 的 trigger。
3. 若未来 `PAS_TRIGGER_STATUS` 口径变化，system spec 仍要求所有 `REJECTED` trigger 继续被排除在正式主线之外，其中 `BPB` 继续视为永久禁止。

## 7. 设计目标但尚未核实实现的能力

### 7.1 `run_backtest_window()`

当前状态：**设计存在，代码未核实到实现**

设计目标：

1. 在窗口期内串联 scan → position → trade
2. 输出系统级回测摘要
3. 具备可追溯的 child run 关系

### 7.2 `run_system_closeout()`

当前状态：**设计存在，代码未核实到实现**

设计目标：

1. 做主线 smoke 验证
2. 产出 closeout 级摘要
3. 识别 blocking items

### 7.3 `_meta_runs`

当前状态：**设计存在，代码未核实到实现**

设计目标：

1. 写入 run lifecycle
2. 记录 `RUNNING / COMPLETED / FAILED`
3. 记录 `error_summary`

## 8. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/system/orchestration.py` | ✅ 已有 | `run_daily_signal_scan()`、`SystemRunSummary`、`StockScanTrace` |
| `src/lq/system/__init__.py` | ✅ 已有 | 模块导出入口 |
| `scripts/system/*` | 未核实存在 | design 目标态，不在本规格中冒充已实现 |

## 9. 当前与 design 目标的差异

1. design 中的三级 runner，目前只核实到 `run_daily_signal_scan()` 已实现。
2. design 中的 `_meta_runs` 与 JSON / markdown summary 落盘，目前未在代码中核实。
3. 当前真实的 system 主线更接近“单日扫描编排层”，而不是完整三 runner 编排层。
