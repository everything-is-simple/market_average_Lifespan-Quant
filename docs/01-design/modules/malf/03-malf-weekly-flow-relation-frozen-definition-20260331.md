# MALF 周线顺逆计算规格 / 2026-03-31（重构版）

> 继承来源：父系统 `12-malf-monthly-weekly-coordination-20260324.md`

## 1. 定位

周线顺逆直接输出 `intermediate_role_2`（`MAINSTREAM / COUNTERTREND`），参与四格上下文分类。

无计算层/执行层之分——周线只有一个判定结果。

## 2. 定义

`intermediate_role_2` 只回答一个问题：

> 当前周线运动，相对月线背景，是顺着走还是逆着走？

| 值 | 含义 | 典型场景 |
|-----|------|----------|
| `MAINSTREAM` | 顺流 | 牛市中向上推进；熊市中向下下行 |
| `COUNTERTREND` | 逆流 | 牛市中向下回调；熊市中向上反弹 |

## 3. 判定规则

实现入口：`src/lq/malf/weekly.py` → `classify_weekly_flow()`

判定逻辑：

1. 取截止日前最近 N 周（默认 `lookback_weeks=8`）的周线收盘价
2. 对最近 `WEEKLY_MA_PERIOD=5` 周做线性回归，得到斜率
3. 斜率与月线背景方向的关系：

| 月线背景 | 周线斜率 | 判定结果 |
|----------|----------|----------|
| `BULL` | `slope > 0` | `MAINSTREAM` |
| `BULL` | `slope ≤ 0` | `COUNTERTREND` |
| `BEAR` | `slope ≤ 0` | `MAINSTREAM` |
| `BEAR` | `slope > 0` | `COUNTERTREND` |

边界处理：无数据或不足 2 根周 K 时，按月线方向给默认值（`BULL` → `MAINSTREAM`，`BEAR` → `COUNTERTREND`）。

## 4. 周线强度（辅助字段）

`weekly_strength`（0~1）= 当前收盘在近 N 周区间的分位。

- 0 = 近期低点；1 = 近期高点；0.5 = 中间（或数据不足默认）

实现：`src/lq/malf/weekly.py` → `compute_weekly_strength()`

## 5. 实现入口

- `src/lq/malf/weekly.py` → `classify_weekly_flow()`
- `src/lq/malf/weekly.py` → `compute_weekly_strength()`
- `src/lq/malf/contracts.py` → 常量与别名定义

## 6. 历史化说明

- `weekly_flow` / `weekly_flow_relation_to_monthly` 允许继续保留为计算层命名或兼容别名。
- 但本系统当前正式执行口径中，周线只对外输出 `intermediate_role_2`（`MAINSTREAM / COUNTERTREND`）。
- 放弃旧命名作为正式输出的原因是：下游真正需要的是“中级波段相对长期背景的顺逆角色”，而不是历史命名本身。
