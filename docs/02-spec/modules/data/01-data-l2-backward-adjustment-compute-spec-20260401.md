# data L2 后复权计算管道规格 / 2026-04-01

> 本规格落地设计文档 `docs/01-design/modules/data/01-data-l2-backward-adjustment-compute-design-20260401.md`，定义可执行的合同约束。

## 1. 范围

本规格覆盖：

1. `stock_daily_adjusted` 的计算合同（字段、精度、来源）
2. `stock_weekly_adjusted / stock_monthly_adjusted` 的聚合合同
3. `asset_master / block_master / block_membership_snapshot` 的 schema 合同
4. `build_l2_adjusted.py` 脚本的执行合同
5. 验证标准与阈值

本规格不覆盖：

1. baostock 审计链（另开独立卡）
2. full market rebuild（需先通过 smoke 验证）

## 2. 输入合同

| 来源表 | 数据库 | 说明 |
|---|---|---|
| `raw_stock_daily` | `raw_market.duckdb` | 原始 OHLCV，未复权 |
| `raw_xdxr_event` | `raw_market.duckdb` | gbbq 除权除息事件 |
| `raw_asset_snapshot` | `raw_market.duckdb` | tushare 资产快照，用于构建 asset_master |
| `raw_index_daily` | `raw_market.duckdb` | 指数日线，无复权需求 |

## 3. 输出合同（对应 bootstrap.py schema）

### 3.1 stock_daily_adjusted

| 字段 | 类型 | 合同约束 |
|---|---|---|
| `code` | VARCHAR | 标准化代码，如 `000001.SZ` |
| `trade_date` | DATE | 交易日 |
| `adjust_method` | VARCHAR | 固定为 `'backward'` |
| `open / high / low / close` | DOUBLE | 后复权价，保留 4 位小数 |
| `volume / amount` | DOUBLE | 原始值，不复权 |
| `adjustment_factor` | DOUBLE | 后复权因子，保留 8 位小数 |
| `build_run_id` | VARCHAR | 关联 base_build_manifest |

禁止：停牌日写入此表。

### 3.2 stock_weekly_adjusted / stock_monthly_adjusted

| 字段 | 聚合规则 |
|---|---|
| `open` | 周/月第一个交易日的 adj_open |
| `high` | max(adj_high) |
| `low` | min(adj_low) |
| `close` | 周/月最后一个交易日的 adj_close |
| `volume / amount` | sum() |
| `trade_date` | 周/月最后一个交易日 |
| `week_start_date / month_start_date` | 周/月第一个交易日 |

### 3.3 asset_master（从 raw_asset_snapshot 构建）

取 `snapshot_date` 最新的记录，去重为唯一 `code`。
`status = 'L'` 为在市，`'D'` 为退市，`'P'` 为暂停。

### 3.4 index_daily / index_weekly / index_monthly

直接从 `raw_index_daily` 清洗（无复权）；周/月聚合规则与股票相同。

## 4. 执行合同

### 4.1 build_l2_adjusted.py 脚本参数

```
--window-start  DATE  # L2 构建起始日（含）
--window-end    DATE  # L2 构建终止日（含）
--force-rebuild       # 可选：忽略幂等检查，强制全量重算
```

### 4.2 幂等性保证

1. 以 `(code, trade_date, adjust_method)` 为 PRIMARY KEY，重复运行不产生重复记录。
2. 若 `raw_xdxr_event` 有新事件，对受影响股票从事件最早日期全量重算复权因子。
3. 每次运行写一条 `base_build_manifest`，状态为 `completed` 或 `failed`。

### 4.3 复权因子计算口径（冻结）

对每个 gbbq category=1 事件：

```
factor_i = (prev_close - fenhong/10 + peigujia × peigu/10)
           / ((1 + (songzhuangu + peigu)/10) × prev_close)
```

后复权因子 = 从当前日期往后所有事件的 factor_i 连乘积，历史越早值越小。

xdxr 缺失时 factor=1.0，不影响非除权股票。

## 5. 验证阈值（对齐父系统 137 号卡基线）

| 验证项 | 阈值 | 方法 |
|---|---|---|
| adj_factor vs tushare adj_factor | < 0.5% 差异 | 抽样 5 只代表性股票 |
| monthly close vs tushare hfq monthly | < 0.5% 差异 | 同上 |
| 停牌日记录数 | = 0 | 全量检查 |
| 重复记录 | = 0 | PRIMARY KEY 约束保证 |

## 6. 代码落点

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/lq/data/bootstrap.py` | ✅ 已有（已补 asset_master 等表） | schema |
| `src/lq/data/compute/adjust.py` | ✅ 已建（2026-04-01） | 复权因子计算核心 |
| `src/lq/data/compute/aggregate.py` | ✅ 已建（2026-04-01） | 周/月线聚合 |
| `src/lq/data/compute/pipeline.py` | ✅ 已建（2026-04-01） | L1→L2 完整构建管道 |
| `scripts/data/build_l2_adjusted.py` | ✅ 已建（2026-04-01） | 脚本入口 |

## 7. 下一步执行卡

本规格已冻结。代码实现已完成（2026-04-01）。

后续执行卡：
1. ~~实现 `compute/adjust.py`~~ ✅
2. ~~实现 `compute/aggregate.py`~~ ✅
3. ~~实现 `scripts/data/build_l2_adjusted.py`~~ ✅
4. 按验证阈值抽样验证（待 L1 数据灌入后执行）
5. 补 `tests/unit/data/test_adjust_factor.py`（待开卡）
