# MALF Pipeline 与输出合同冻结设计 / 2026-03-31

> 继承来源：父系统 `14-malf-matrix-axis-contract-implementation-20260327.md`
> 本文冻结：pipeline 流程、输出表 schema、MalfContext 合同字段。

## 1. Pipeline 总流程

```
market_base.duckdb
  stock_monthly_adjusted (backward, 按 month_start_date 排序)
  stock_weekly_adjusted  (backward, 按 week_start_date 排序)
          ↓
  monthly.classify_monthly_state()   → monthly_state
  monthly.compute_monthly_strength() → monthly_strength
          ↓
  weekly.classify_weekly_flow()      → weekly_flow
  weekly.compute_weekly_strength()   → weekly_strength
          ↓
  contracts.build_surface_label()    → surface_label（派生）
          ↓
  MalfContext（冻结合同对象）
          ↓
  malf.duckdb → malf_context_snapshot（批量落库）
```

入口：`src/lq/malf/pipeline.py` → `run_malf_batch()` / `build_malf_context_for_stock()`

## 2. 数据库 Schema

### 2.1 malf_context_snapshot（主输出合同表）

存储路径：`Lifespan-data/malf/malf.duckdb`

| 列 | 类型 | 说明 |
|---|---|---|
| `code` | VARCHAR | 股票代码 |
| `signal_date` | DATE | 信号日期（T 日） |
| `monthly_state` | VARCHAR | 月线八态（枚举值） |
| `weekly_flow` | VARCHAR | 周线顺逆（`with_flow / against_flow`） |
| `surface_label` | VARCHAR | 派生表面标签（四值） |
| `monthly_strength` | DOUBLE | 月线强度 0~1（可 NULL） |
| `weekly_strength` | DOUBLE | 周线强度 0~1（可 NULL） |
| `run_id` | VARCHAR | 构建批次 ID |
| `created_at` | TIMESTAMP | 落库时间 |
| PRIMARY KEY | — | `(code, signal_date)` |

幂等规则：写入前先 `DELETE WHERE signal_date = ?`，再 INSERT。

### 2.2 malf_build_manifest（构建元数据表）

| 列 | 类型 | 说明 |
|---|---|---|
| `run_id` | VARCHAR PRIMARY KEY | 批次唯一 ID |
| `status` | VARCHAR | `SUCCESS / PARTIAL / FAILED` |
| `asof_date` | DATE | 构建日期 |
| `index_count` | INTEGER | 指数数量 |
| `stock_count` | INTEGER | 股票数量 |
| `created_at` | TIMESTAMP | 落库时间 |

## 3. MalfContext 合同（冻结）

不可变 `dataclass`，是本模块对外唯一正式合同：

```python
@dataclass(frozen=True)
class MalfContext:
    code: str
    signal_date: date
    monthly_state: str       # MonthlyState8 枚举值
    weekly_flow: str         # WeeklyFlowRelation 枚举值
    surface_label: str       # SurfaceLabel 枚举值（派生）
    monthly_strength: float | None = None
    weekly_strength: float | None = None
```

防御规则（`__post_init__` 强制执行）：
- `monthly_state` 必须在 `MONTHLY_STATE_8_VALUES` 中
- `weekly_flow` 必须在 `WEEKLY_FLOW_RELATION_VALUES` 中

## 4. 输入数据来源约束

| 输入 | 来源表 | 过滤条件 | 代码中的列别名 |
|---|---|---|---|
| 月线 | `stock_monthly_adjusted` | `adjust_method = 'backward'` | `month_start_date AS month_start` |
| 周线 | `stock_weekly_adjusted` | `adjust_method = 'backward'` | `week_start_date AS week_start` |
| 指数月线 | `index_monthly` | — | 同上 |
| 指数周线 | `index_weekly` | — | 同上 |

**严禁**读 `raw_market.duckdb` 的原始日线数据作为 MALF 输入。

## 5. 模块间合同传递规则

| 输出对象 | 类型 | 目标模块 | 落库 |
|---|---|---|---|
| `MalfContext` | frozen dataclass | `filter`、`alpha/pas` | 否（内存传递） |
| `MalfContextSnapshot` | frozen dataclass | 批量摘要 | 可选，写 `malf.duckdb` |
| `MALFBuildManifest` | frozen dataclass | 运行元数据 | 写 `malf.duckdb` |

**`filter` 和 `alpha/pas` 只能消费 `MalfContext` 对象，禁止直接读 `malf.duckdb` 内部表。**

## 6. 错误处理规则

`run_malf_batch()` 的当前处理规则：
- 单只股票异常时跳过，`error_count` 累加
- 全部完成后若 `error_count > 0`，`status = "PARTIAL"`，否则 `status = "SUCCESS"`
- 错误不向外抛出，通过 `MALFBuildManifest.status` 报告

后续若需要更细粒度的错误追踪，另开执行卡添加错误日志表。

## 7. 铁律

1. `MalfContext` 字段名冻结，不允许修改。
2. Pipeline 输入只能是 `market_base.duckdb` 的 L2 复权数据。
3. 写库幂等，相同 `signal_date` 的数据覆盖写入不产生重复行。
4. 合同别名（`MAINSTREAM` 等）在 pipeline 内消化完毕后，`MalfContext` 只含正式值。
