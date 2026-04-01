# MALF 三层矩阵合同规格 / 2026-04-01

> 对应设计文档 `docs/01-design/modules/malf/02-malf-three-layer-matrix-frozen-contract-20260331.md`。

## 1. 范围

本规格冻结 `MalfContext` 合同的可执行约束，及 malf.duckdb 的 schema 合同。

## 2. MalfContext 字段合同

| 字段 | 类型 | 合法值 | 说明 |
|---|---|---|---|
| `entity_code` | str | 任意股票/指数代码 | 计算对象 |
| `asof_date` | date | 有效交易日 | 快照日期 |
| `monthly_state` | str | 见下方八态枚举 | 月线状态 |
| `weekly_flow` | str | `with_flow / against_flow` | 周线顺逆 |
| `surface_label` | str | 见下方四值枚举 | 派生标签 |
| `monthly_strength` | float | [0.0, 1.0] | 月线强度分位 |

### 月线八态枚举（冻结）

```
BULL_FORMING / BULL_PERSISTING / BULL_EXHAUSTING / BULL_REVERSING
BEAR_FORMING / BEAR_PERSISTING / BEAR_EXHAUSTING / BEAR_REVERSING
```

兼容别名：`CONFIRMED_BULL → BULL_PERSISTING`，`CONFIRMED_BEAR → BEAR_PERSISTING`

### surface_label 四值枚举（冻结，派生规则）

| monthly_state 前缀 | weekly_flow | surface_label |
|---|---|---|
| BULL_* | with_flow | BULL_MAINSTREAM |
| BULL_* | against_flow | BULL_COUNTERTREND |
| BEAR_* | with_flow | BEAR_MAINSTREAM |
| BEAR_* | against_flow | BEAR_COUNTERTREND |

## 3. malf.duckdb schema 合同

### 3.1 malf_context_snapshot（批量构建落表）

| 字段 | 类型 | 说明 |
|---|---|---|
| `snapshot_id` | VARCHAR PK | UUID |
| `entity_code` | VARCHAR | 股票/指数代码 |
| `asof_date` | DATE | 快照日期 |
| `monthly_state` | VARCHAR | 月线八态 |
| `weekly_flow` | VARCHAR | 周线顺逆 |
| `surface_label` | VARCHAR | 派生标签 |
| `monthly_strength` | DOUBLE | 月线强度 |
| `build_run_id` | VARCHAR | 关联 malf_build_manifest |
| `created_at` | TIMESTAMP | |

### 3.2 malf_build_manifest

| 字段 | 类型 | 说明 |
|---|---|---|
| `run_id` | VARCHAR PK | 构建 run ID |
| `window_start` | DATE | |
| `window_end` | DATE | |
| `entity_count` | INTEGER | 本次计算实体数 |
| `status` | VARCHAR | completed / failed |
| `created_at` | TIMESTAMP | |

## 4. 输入输出合同

输入（只读）：
- `market_base.duckdb / stock_monthly_adjusted`（adjust_method='backward'）
- `market_base.duckdb / stock_weekly_adjusted`（adjust_method='backward'）

输出（可写）：
- `malf.duckdb / malf_context_snapshot`
- `malf.duckdb / malf_build_manifest`

`MalfContext` 对象（内存合同，不直接落库）供 `filter` / `alpha/pas` 消费。

## 5. 铁律

1. `MalfContext` 是唯一对外合同，下游不可读 malf 内部中间表。
2. `monthly_state` 只能取八态枚举值，其他值视为 bug。
3. `surface_label` 只能由 `monthly_state + weekly_flow` 派生，禁止外部直接设置。
4. malf.duckdb schema 通过 `scripts/data/bootstrap_storage.py` 同步初始化（待补）。

## 6. 代码落点

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/lq/malf/contracts.py` | ✅ 已有 | MalfContext / MalfContextSnapshot 合同 |
| `src/lq/malf/monthly.py` | ✅ 已有（已修 BEAR_REVERSING） | 月线八态计算 |
| `src/lq/malf/weekly.py` | ✅ 已有 | 周线顺逆计算 |
| `src/lq/malf/pipeline.py` | ✅ 已有 | 批量构建管道 |
| malf.duckdb bootstrap | ❌ 待建 | malf_context_snapshot 等建表逻辑 |
| `scripts/data/bootstrap_storage.py` | ⚠️ 已有，需补 malf 部分 | 当前只建 raw_market + market_base |
