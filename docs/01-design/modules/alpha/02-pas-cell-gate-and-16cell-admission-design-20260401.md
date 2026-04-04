# PAS 16 格准入表与 cell_gate_check 设计 / 2026-04-01

> 继承父系统 110/121/126/129/131 结论，冻结本系统准入判断规范。

## 1. 两层准入判断结构

PAS 准入使用两层递进判断：

```
第一层（surface_label，4格粗筛）
  ↓ 通过后
第二层（monthly_state × weekly_flow，精确 16 格）
  ↓ 通过后
进入 trigger 探测
```

第一层用于快速排除明显无效组合（如 BPB 全拒，非 persisting 态下 BOF 以外的 trigger）。
第二层确认具体月线状态是否符合条件格要求。

**两层都必须通过，才允许进行 trigger 探测。**

## 2. 第一层：surface_label 准入表（ADMISSION_TABLE）

`surface_label` 由 `monthly_state` 和 `weekly_flow` 派生：

| surface_label | monthly_state 特征 | weekly_flow |
|---|---|---|
| `BULL_MAINSTREAM` | 任意 BULL_* | `with_flow` |
| `BULL_COUNTERTREND` | 任意 BULL_* | `against_flow` |
| `BEAR_MAINSTREAM` | 任意 BEAR_* | `with_flow` |
| `BEAR_COUNTERTREND` | 任意 BEAR_* | `against_flow` |

第一层准入表（`ADMISSION_TABLE`，位于 `validation.py`）：

| | BULL_MAINSTREAM | BULL_COUNTERTREND | BEAR_MAINSTREAM | BEAR_COUNTERTREND |
|---|---|---|---|---|
| BOF | True | True | True | True |
| BPB | False | False | False | False |
| PB | True | False | False | True |
| TST | True | False | False | True |
| CPB | False | False | False | False |

## 3. 第二层：精确 16 格准入（CELL_GATE_TABLE）

`monthly_state_8` 取值（8 个）：

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

> CPB 三段回测保留段负收益（-33万），降为 REJECTED（父系统卡 258）。

## 4. cell_gate_check() 函数规范

位于 `src/lq/alpha/pas/validation.py`：

```python
def cell_gate_check(pattern: str, monthly_state: str, weekly_flow: str) -> bool:
    """16 格精确准入判断（父系统冻结结论）。"""
    admitted_cells = CELL_GATE_TABLE.get(pattern)
    if admitted_cells is None:
        return False
    return (monthly_state, weekly_flow) in admitted_cells
```

调用规范：

```python
# 在 trigger 探测前调用
if not cell_gate_check(pattern, malf_ctx.monthly_state, malf_ctx.weekly_flow):
    # 跳过，记录 skip_reason = "CELL_GATE_REJECTED"
    return _skip_trace(...)

# 通过后才进入探测器
trace = detect_bof(code, signal_date, df)
```

## 5. 设计说明

### 为什么 BOF 是全 persisting 四格，而 PB/TST/CPB 只有两格？

- BOF 是趋势持续的主力 trigger，在牛市主流和熊市逆流中均能发挥作用（"顺势 BOF" + "熊市中逆势 BOF"）。
- PB/TST/CPB 是辅助工具，父系统三年验证发现它们只在 "牛市顺势" 和 "熊市逆势" 两个最纯净的方向格中有稳定效果。
- 这与交易直觉吻合：PB/TST/CPB 在方向不纯的格中容易误判。

### surface_label 为什么不够用？

- `surface_label` 把 BULL_FORMING / BULL_PERSISTING / BULL_EXHAUSTING / BULL_REVERSING 混合为同一个 `BULL_MAINSTREAM`。
- 但 BOF 只在 persisting 态主力，在 forming/exhausting 态样本稀疏。
- 因此必须用第二层精确 16 格判断，而不能只依赖 surface_label。

## 6. 铁律

1. `cell_gate_check()` 结果必须在 trigger 探测前调用，不允许探测后再过滤。
2. TST 和 CPB 的准入格与 PB 完全相同（对角两格），不得擅自扩展。
3. BOF 的 forming/exhausting/reversing 格样本稀疏，不作为正式主力格，但不禁止探测（可用于研究）。
4. `CELL_GATE_TABLE` 字段名冻结，不允许改名或调整 key 结构。
