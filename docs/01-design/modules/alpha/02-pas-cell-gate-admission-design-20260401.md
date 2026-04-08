# PAS 四格准入表与 cell_gate_check 设计 / 2026-04-07（重写）

> 继承父系统 110/121/126/129/131 结论，冻结本系统准入判断规范。

## 1. 两层准入判断结构

PAS 准入使用两层递进判断：
```
第一层（malf_context_4，四格粗筛）
  ↓ 通过后
第二层（monthly_state_8 × weekly_flow，精确 cell gate）
  ↓ 通过后
进入正式信号主线
```
第一层用于快速排除明显无效组合（如 BPB 全拒，非 persisting 态下 BOF 以外的 trigger）。
第二层确认具体月线状态是否符合条件格要求。

**两层都必须通过，才允许进入正式信号主线。** 当前 `run_pas_batch()` 的实现顺序是：先由 detector 产生 `PasDetectTrace`，再在写入 `pas_formal_signal` 前应用 `cell_gate_check()`；因此本设计约束的是正式信号准入，而不是 detector 的调用顺序。

## 2. 第一层：malf_context_4 准入表（ADMISSION_TABLE）

`malf_context_4` 由 `long_background_2`（BULL/BEAR）和 `intermediate_role_2`（MAINSTREAM/COUNTERTREND）组合：

| malf_context_4 | long_background_2 | intermediate_role_2 |
|---|---|---|
| `BULL_MAINSTREAM` | `BULL` | `MAINSTREAM` |
| `BULL_COUNTERTREND` | `BULL` | `COUNTERTREND` |
| `BEAR_MAINSTREAM` | `BEAR` | `MAINSTREAM` |
| `BEAR_COUNTERTREND` | `BEAR` | `COUNTERTREND` |

第一层准入表（`ADMISSION_TABLE`，位于 `validation.py`）：

| | BULL_MAINSTREAM | BULL_COUNTERTREND | BEAR_MAINSTREAM | BEAR_COUNTERTREND |
|---|---|---|---|---|
| BOF | True | True | True | True |
| BPB | False | False | False | False |
| PB | True | False | False | True |
| TST | True | False | False | True |
| CPB | False | False | False | False |

## 3. 第二层：精确 cell gate 准入（CELL_GATE_TABLE）

`monthly_state_8` 取值（8 个，计算层诊断状态）：

```
BULL_FORMING, BULL_PERSISTING, BULL_EXHAUSTING, BULL_REVERSING,
BEAR_FORMING, BEAR_PERSISTING, BEAR_EXHAUSTING, BEAR_REVERSING
```

`weekly_flow` 取值（2 个）：`with_flow`，`against_flow`

精确准入格（通过 `cell_gate_check()` 实现）：

### BOF（core）— 持续态四格

| monthly_state | weekly_flow | 准入 |
|---|---|---|
| `BULL_PERSISTING` | `with_flow` | ✅ |
| `BULL_PERSISTING` | `against_flow` | ✅ |
| `BEAR_PERSISTING` | `with_flow` | ✅ |
| `BEAR_PERSISTING` | `against_flow` | ✅ |
| 其他所有态 | 任意 | ❌（sparse，研究可跑但非主力） |

### PB / TST（conditional）— 对角两格

| monthly_state | weekly_flow | 准入 |
|---|---|---|
| `BULL_PERSISTING` | `with_flow` | ✅ |
| `BEAR_PERSISTING` | `against_flow` | ✅ |
| 其他所有组合 | — | ❌ |

### BPB / CPB — 全拒绝

任意 `(monthly_state, weekly_flow)` 组合 → ❌

> CPB 已在父系统三段回测后冻结为 `REJECTED`，不再属于条件格准入讨论。

## 4. cell_gate_check() 函数规范

位于 `src/lq/alpha/pas/validation.py`：

```python
def cell_gate_check(pattern: str, monthly_state: str, weekly_flow: str) -> bool:
    """精确 cell gate 准入判断（父系统冻结结论）。"""
    admitted_cells = CELL_GATE_TABLE.get(pattern)
    if admitted_cells is None:
        return False
    return (monthly_state, weekly_flow) in admitted_cells
```

调用规范：

```python
# 当前 run_pas_batch() 先运行 detector，生成 trace
traces = run_all_detectors(code, signal_date, df, patterns=active_patterns)
for trace in traces:
    if not trace.triggered:
        continue
    if trace.pattern == "BPB":
        continue
    if monthly_state and weekly_flow and not cell_gate_check(trace.pattern, monthly_state, weekly_flow):
        continue
    sig = _build_signal(trace, code, signal_date, malf_snapshot, df)
```

## 5. 设计说明

### 为什么 BOF 是全 persisting 四格，而 PB/TST 只有两格？

- BOF 是趋势持续的主力 trigger，在牛市主流和熊市逆流中均能发挥作用（"顺势 BOF" + "熊市中逆势 BOF"）。
- PB/TST 是辅助工具，父系统三年验证发现它们只在 "牛市顺势" 和 "熊市逆势" 两个最纯净的方向格中有稳定效果。
- 这与交易直觉吻合：PB/TST 在方向不纯的格中容易误判。
- CPB 已在父系统三段回测后冻结为 `REJECTED`，不再属于条件格准入讨论。

### malf_context_4 为什么不够用？

- `malf_context_4` 把 BULL_FORMING / BULL_PERSISTING / BULL_EXHAUSTING / BULL_REVERSING 混合为同一个 `BULL_MAINSTREAM`。
- 但 BOF 只在 persisting 态主力，在 forming/exhausting 态样本稀疏。
- 因此必须用第二层精确 cell gate 判断，而不能只依赖 malf_context_4。

## 6. 铁律

1. `cell_gate_check()` 结果必须在信号进入 `pas_formal_signal` 前生效，不允许让未通过 gate 的信号进入正式主线。
2. TST 的准入格与 PB 完全相同（对角两格）；CPB 当前全拒绝，不得擅自恢复为条件格。
3. BOF 的 forming/exhausting/reversing 格样本稀疏，不作为正式主力格，但不禁止探测（可用于研究）。
4. `CELL_GATE_TABLE` 字段名冻结，不允许改名或调整 key 结构。
