# PAS 合同冻结与输出治理 / 2026-04-01

> 继承父系统 `01-pas-selected-trace-mainline-governance-charter-20260326.md` 结论，
> 冻结本系统的输出合同、表名口径与 trace 治理规则。

## 1. 正式输出合同（冻结）

### 1.1 PasDetectTrace

单次 trigger 探测的完整 trace，不管是否触发：

| 字段 | 类型 | 含义 |
|---|---|---|
| `signal_id` | `str` | 全局唯一 ID（格式见 §3） |
| `pattern` | `str` | PasTriggerPattern 值 |
| `triggered` | `bool` | 本次是否触发 |
| `strength` | `float \| None` | 触发强度 0~1；未触发时为 None |
| `skip_reason` | `str \| None` | 跳过原因（数据不足、cell gate 拒绝等） |
| `detect_reason` | `str \| None` | 触发或未触发的具体原因说明 |
| `history_days` | `int` | 可用历史天数 |
| `min_history_days` | `int` | 该 trigger 的最小历史要求 |
| `pb_sequence_number` | `int \| None` | 当前上升波段第几个 PB（仅 PB 触发时有意义） |

### 1.2 PasSignal

正式触发信号 — 模块间传递的结果合同：

| 字段 | 类型 | 含义 |
|---|---|---|
| `signal_id` | `str` | 全局唯一 ID |
| `code` | `str` | 股票代码（6 位纯代码） |
| `signal_date` | `date` | 信号日期（T） |
| `pattern` | `str` | PasTriggerPattern 值 |
| `surface_label` | `str` | SurfaceLabel 值（来自 MalfContext） |
| `strength` | `float` | 信号强度 0~1 |
| `signal_low` | `float` | 信号最低价（用于计算 1R 止损） |
| `entry_ref_price` | `float` | 参考入场价（后复权收盘价，研究层口径） |
| `pb_sequence_number` | `int \| None` | 第几个 PB（仅 PB 时有意义） |

**PasSignal 是研究层合同，不是执行层合同。**
执行价格需要通过 `trade` 模块的 raw-execution 对齐后才可用于实盘。

### 1.3 PasBatchResult

批量探测摘要，不落表，供调用方汇总用：

| 字段 | 含义 |
|---|---|
| `run_id` | 本次 run 的唯一标识 |
| `asof_date` | 截止日期 |
| `codes_scanned` | 扫描股票数 |
| `triggered_count` | 触发信号数 |
| `pattern_counts` | 各 pattern 触发数量 |
| `signals` | `tuple[PasSignal, ...]`，全部触发信号 |

## 2. 数据库表名口径（冻结）

正式主线表名：`pas_selected_trace`

| 表名 | 角色 |
|---|---|
| `pas_selected_trace` | 正式主线 trace 表（`status = completed` run 对应） |
| `pas_formal_signal` | 正式主线 signal 表 |
| `pas_registry_run` | run 元数据注册表（含 `status` 字段） |
| `pas_trigger_trace` | 历史兼容视图名（非正式主线，只读） |

**`pas_trigger_trace` 已降级为兼容视图名，不再用于新增设计或新增脚本的正式表名。**

## 3. signal_id 格式（冻结）

```
PAS_{version}_{code}_{signal_date}_{pattern}
```

示例：`PAS_v1_000001_2026-04-01_BOF`

- `version` 当前为 `v1`（`PAS_CONTRACT_VERSION` 常量）
- `code` 为 6 位纯代码格式
- 全局唯一性由 `(version, code, signal_date, pattern)` 四元组保证

## 4. trace 治理规则

### 4.1 主线层规则

以下三个条件同时满足，视为正式主线 trace：

1. 对应 `pas_registry_run` 的 `status = completed`
2. `pas_selected_trace` 中存在对应 `run_id`
3. `triggered = True` 且通过了 `cell_gate_check()`

### 4.2 失败态规则

- `failed` / `running` 状态保留在 `pas_registry_run`，但对应 trace/signal 不进正式主线表
- 出现半成品落库时，必须通过治理脚本清理（`scripts/alpha/` 下）

### 4.3 多 trigger 仲裁规则

同一 `(code, signal_date)` 多 trigger 同时触发时，按以下优先级选出 `selected_pattern`：

```
BOF > PB > TST > CPB > BPB（BPB 永远不进主线）
```

优先级最高的已准入 trigger 作为 `selected_pattern`，其余记录为 trace 但不进 `pas_formal_signal`。

## 5. skip_reason 规范

| skip_reason 值 | 含义 |
|---|---|
| `INSUFFICIENT_HISTORY` | 历史数据不足，未达到 `min_history_days` |
| `MISSING_COLUMNS` | DataFrame 缺少必需列 |
| `CELL_GATE_REJECTED` | 精确 16 格 cell gate 拒绝（monthly_state + weekly_flow 不符合准入格） |
| `BPB_EXCLUDED` | BPB 全局禁止主线 |
| `None` | 正常探测，无跳过 |

## 6. 铁律

1. `PasSignal.signal_id` 全局唯一，格式不允许修改。
2. `pas_selected_trace` 是正式主线表名，新增脚本不得使用 `pas_trigger_trace` 作为写入目标。
3. `alpha` 模块不直接写 `trade_runtime`；`PasSignal` 只能经 `position` 桥接后才进入执行层。
4. `triggered = True` 的 trace 必须同时满足 cell gate 准入，否则不能进入 `pas_formal_signal`。
5. `entry_ref_price` 是后复权研究价格，不能直接用作实盘执行价格。
