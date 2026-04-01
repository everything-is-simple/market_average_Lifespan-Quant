# alpha/pas 合同与 pipeline 规格 / 2026-04-01

> 对应设计文档 `docs/01-design/modules/alpha/03-pas-contracts-and-output-governance-20260401.md`。

## 1. 范围

本规格冻结：

1. `PasDetectTrace / PasSignal / PasBatchResult` 合同字段约束
2. `research_lab.duckdb` alpha 表域 schema（对应 `src/lq/alpha/pas/bootstrap.py`）
3. `run_all_detectors` 批量执行合同
4. 写权边界

本规格不覆盖：

1. 各 trigger 的探测算法细节（见 `detectors.py`）
2. 16 格准入裁决更新（见 `02-pas-cell-gate-and-16cell-admission-design-20260401.md`）

## 2. 合同字段约束

### 2.1 PasDetectTrace

| 字段 | 类型 | 约束 |
|---|---|---|
| `signal_id` | str | `{code}_{signal_date}_{pattern}` 格式 |
| `pattern` | str | BOF / PB / BPB / TST / CPB |
| `triggered` | bool | 必须明确 |
| `strength` | float or None | triggered=True 时必须有值，[0.0, 1.0] |
| `skip_reason` | str or None | triggered=False 时说明原因 |
| `history_days` | int | 实际可用历史天数 |
| `min_history_days` | int | 最小所需历史天数 |

### 2.2 PasSignal

| 字段 | 类型 | 约束 |
|---|---|---|
| `signal_id` | str | 与 PasDetectTrace 对应 |
| `code` | str | 6 位纯代码（L2+层） |
| `signal_date` | date | 信号日（T日） |
| `pattern` | str | BOF / PB / TST / CPB（BPB 不写正式信号表） |
| `surface_label` | str | 四值枚举 |
| `strength` | float | [0.0, 1.0] |
| `signal_low` | float | 后复权价，止损参考 |
| `entry_ref_price` | float | 后复权价，T+1 开盘参考 |
| `pb_sequence_number` | int or None | 仅 PB 触发时有值 |

### 2.3 PasBatchResult

| 字段 | 约束 |
|---|---|
| `run_id` | UUID，每次 batch 唯一 |
| `traces` | list[PasDetectTrace] |
| `signals` | list[PasSignal]，只含 triggered=True 且准入格的信号 |
| `total_candidates` | 本次扫描候选股数 |

## 3. research_lab.duckdb 表域（冻结）

由 `src/lq/alpha/pas/bootstrap.py` 建立：

| 表名 | 说明 |
|---|---|
| `pas_registry_run` | 每次批量扫描的 run 元数据 |
| `pas_selected_trace` | 所有探测 trace（含未触发） |
| `pas_formal_signal` | 正式触发信号（仅 triggered=True） |
| `pas_condition_matrix_run` | 16 格验证 run 元数据 |
| `pas_condition_matrix_cell` | 16 格每格统计结果 |
| `research_lab_build_manifest` | alpha 模块构建 manifest |

## 4. 写权边界

### 允许

- alpha/pas 写 `research_lab.duckdb` 中以上六张表
- alpha/pas 读 `market_base.duckdb`
- alpha/pas 读冻结后的 malf 输出（MalfContext 对象）

### 禁止

- 写 `market_base.duckdb`
- 写 `malf.duckdb`
- 写 `trade_runtime.duckdb`
- 让未通过 cell_gate_check 的信号进入正式信号表

## 5. 执行合同

### 5.1 单股单日探测

```python
traces = run_all_detectors(code, signal_date, df)
```

返回 5 个 `PasDetectTrace`（每个 trigger 各一个）。

### 5.2 批量扫描（待建）

```python
result = run_pas_batch(
    codes: list[str],
    window_start: date,
    window_end: date,
    malf_context_provider: Callable,
    market_base_conn: duckdb.Connection,
) -> PasBatchResult
```

批量结果写入 `research_lab.duckdb`，同时写 `pas_registry_run`。

## 6. 代码落点

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/lq/alpha/pas/contracts.py` | ✅ 已有 | PasDetectTrace / PasSignal / PasBatchResult |
| `src/lq/alpha/pas/detectors.py` | ✅ 已有（5 trigger） | 探测器实现 |
| `src/lq/alpha/pas/validation.py` | ✅ 已有（cell_gate_check） | 16 格准入 + cell_gate |
| `src/lq/alpha/pas/bootstrap.py` | ✅ 已建 | research_lab schema |
| batch pipeline runner | ❌ 待建 | 批量扫描 + 落表 |
| `scripts/alpha/run_pas_batch.py` | ❌ 待建 | 脚本入口 |
