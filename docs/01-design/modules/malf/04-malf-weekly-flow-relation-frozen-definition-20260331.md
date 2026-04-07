# MALF 周线顺逆关系冻结定义 / 2026-03-31

> 继承来源：父系统 `12-malf-monthly-weekly-coordination-20260324.md` +
> `13-malf-three-layer-matrix-modeling-charter-20260327.md`（已历史化）
>
> **2026-04-07 补注**：父系统 `13` 已于 `281` 卡降级为历史兼容。
> 本文的周线顺逆概念仍然有效——它 feeds into 执行层的 `intermediate_role_2`（`MAINSTREAM / COUNTERTREND`）。
> `with_flow` 映射为 `MAINSTREAM`，`against_flow` 映射为 `COUNTERTREND`。

## 1. 定义（冻结）

`weekly_flow_relation_to_monthly`（代码字段名：`weekly_flow`）

只回答一个问题：

> 当前周线这段运动，相对月线长期背景方向，是顺着走还是逆着走？

| 值 | 含义 | 典型场景 |
|---|---|---|
| `with_flow` | 顺流 | 牛市背景中向上推进；熊市背景中向下下行 |
| `against_flow` | 逆流 | 牛市背景中向下回调；熊市背景中向上反弹 |

## 2. 判定规则（当前实现）

实现入口：`src/lq/malf/weekly.py` → `classify_weekly_flow()`

判定逻辑：
1. 取截止日前最近 N 周（默认 `lookback_weeks=8`）的周线收盘价
2. 对最近 `WEEKLY_MA_PERIOD=5` 周做线性回归，得到斜率
3. 斜率与月线背景方向的关系：

| 月线背景 | 周线斜率 | 判定结果 |
|---|---|---|
| `BULL_*` | `slope > 0`（向上） | `with_flow`（顺势推进） |
| `BULL_*` | `slope ≤ 0`（向下或平） | `against_flow`（逆势回调） |
| `BEAR_*` | `slope ≤ 0`（向下或平） | `with_flow`（顺势下行） |
| `BEAR_*` | `slope > 0`（向上） | `against_flow`（逆势反弹） |

边界处理：
- 无数据时按月线方向给默认值（`BULL_*` → `with_flow`，`BEAR_*` → `against_flow`）
- 数据不足 2 根周 K 时同上

## 3. 周线强度（辅助字段）

`weekly_strength`（0~1）= 当前收盘在近 N 周区间的分位

- 0 = 处于近期低点附近
- 1 = 处于近期高点附近
- 0.5 = 中间位置（或数据不足时默认）

实现：`src/lq/malf/weekly.py` → `compute_weekly_strength()`

## 4. 兼容别名（只允许模块内转换）

| 旧字段名 | 等价正式值 |
|---|---|
| `MAINSTREAM` | `with_flow` |
| `COUNTERTREND` | `against_flow` |
| `wave_role = MAINSTREAM` | `weekly_flow = with_flow` |
| `wave_role = COUNTERTREND` | `weekly_flow = against_flow` |

兼容别名在 `src/lq/malf/contracts.py` 的 `_WEEKLY_FLOW_ALIAS` 字典中定义。  
对外输出的 `MalfContext` 合同只允许出现正式值，不允许输出别名。

## 5. 与 surface_label 的关系

`surface_label` 由 `monthly_state` + `weekly_flow` 派生，规则：

```
BULL_* + with_flow    → BULL_MAINSTREAM
BULL_* + against_flow → BULL_COUNTERTREND
BEAR_* + with_flow    → BEAR_MAINSTREAM
BEAR_* + against_flow → BEAR_COUNTERTREND
```

`surface_label` 是历史兼容读法，是观察字段，不是矩阵主轴。

## 6. 当前边界

本文只负责：`weekly_flow` 的语义定义、当前实现规则、兼容别名。

实现参数（`WEEKLY_MA_PERIOD`、`lookback_weeks`）不在此文档冻结——
若需调整参数，另开执行卡并提供验证证据。
