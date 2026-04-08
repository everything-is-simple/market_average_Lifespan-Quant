# data L2 后复权计算管道设计 / 2026-04-01

> 继承父系统 data 模块设计（49/50/51/137 号卡冻结口径），在 `00-data-charter-20260404.md` 的两步走架构下，定义本系统 Step 2（`.day + gbbq` 日增量路径）的 L1→L2 后复权计算边界。

## 1. 问题陈述

当前 `bootstrap.py` 已建立 `stock_daily_adjusted / stock_weekly_adjusted / stock_monthly_adjusted` 的 schema，
`compute/adjust.py`、`compute/aggregate.py`、`compute/pipeline.py` 与 `scripts/data/build_l2_adjusted.py` 也已落地。

因此，本文当前不再回答“L2 后复权是否已有实现”，而是冻结 Step 2（日增量）这条正式计算路径的边界、公式与约束，作为 `014 / 015` 的 design 锚点。

两步走架构下：

1. Step 1（`TDX_OFFLINE_DATA_ROOT` txt 全量灌入）由 `02-data-l1-tdx-txt-bulk-import-design-20260404.md` 覆盖
2. 本文只覆盖 Step 2（`TDX_ROOT` 下 `.day + gbbq`）的 L1→L2 本地计算路径

## 2. 后复权因子计算口径（冻结）

### 2.1 数据来源

- `raw_stock_daily`：原始 OHLCV（未复权）
- `raw_xdxr_event`：通达信 gbbq 文件中的除权除息事件（category 字段，14 种类型）

### 2.2 后复权公式（向前追溯法）

```
backward_factor(T) = ∏ (factor_i)  for all xdxr events i where event_date > T
```

对每个 xdxr 事件，factor_i 计算：

| gbbq category | factor_i 公式 |
|---|---|
| 1（除权除息） | `(qianzongguben + songzhuangu × qianzongguben + peigu × qianzongguben - fenhong / houzongguben × houzongguben) / (qianzongguben + ...)`（标准除权公式） |
| 简化口径 | `(前收盘 - 每股分红 + 配股价 × 配股数) / (1 + 送转股数 + 配股数) / 前收盘` |

**本系统采用的简化口径**（与父系统 137 号卡对齐）：

```
factor_i = (close_prev - fenhong/10 + peigujia × peigu/10) / (1 + (songzhuangu + peigu)/10) / close_prev
```

当 category=1 且相关字段为 0 时，factor_i = 1.0（跳过）。

### 2.3 调整后价格

```
adj_close(T) = raw_close(T) × backward_factor(T)
adj_open(T)  = raw_open(T)  × backward_factor(T)
adj_high(T)  = raw_high(T)  × backward_factor(T)
adj_low(T)   = raw_low(T)   × backward_factor(T)
```

成交量不做复权（父系统口径）。

### 2.4 精度约定

- 复权因子保留 8 位小数
- 调整后价格保留 4 位小数
- 复权因子存入 `stock_daily_adjusted.adjustment_factor` 字段

## 3. 周线 / 月线聚合规则

周线 = 该周交易日的聚合（`trade_date` 为周最后一个交易日）：

| 字段 | 聚合方式 |
|---|---|
| open | 周第一个交易日的 adj_open |
| high | max(adj_high) |
| low | min(adj_low) |
| close | 周最后一个交易日的 adj_close |
| volume | sum(volume) |
| amount | sum(amount) |

月线同理（月最后交易日为 trade_date，`month_start_date` 为月第一个交易日）。

## 4. 缺口与停牌处理

- 停牌日（`is_suspended=True`）：不写入 `stock_daily_adjusted`
- 除权日前后的因子跳跃：只影响调整因子，不过滤
- xdxr 事件缺失时：factor = 1.0（等于未复权）

## 5. 增量更新语义

1. 每次构建以 `window_start / window_end` 为边界（幂等）
2. 先检测 `raw_xdxr_event` 是否有新事件 → 若有，对受影响股票全量重算复权因子（从最早事件日开始）
3. 若 xdxr 无变化，只追加 `window_start → window_end` 日期段的新增日线

## 6. asset_master / block_master（标准化资产主数据）

父系统 data spec §5.1 要求的 L2 标准表，当前已补入 `bootstrap.py`：

| 表名 | 来源 | 用途 |
|---|---|---|
| `asset_master` | `raw_asset_snapshot` 去重/标准化 | 全系统统一资产基础表（code/name/exchange/type/status） |
| `block_master` | TDX `tdxhy.cfg / tdxzs.cfg` | 行业/板块分类主表 |
| `block_membership_snapshot` | TDX block 文件 | 股票-板块从属关系快照 |

**当前状态**：相关 schema 已进入 `bootstrap.py` 的 `MARKET_BASE_SCHEMA_STATEMENTS`。

## 7. 代码落点

| 文件 | 职责 |
|---|---|
| `src/lq/data/bootstrap.py` | L2 schema（已含 asset_master / block_master / block_membership_snapshot） |
| `src/lq/data/compute/adjust.py` | 后复权因子计算核心逻辑（已建） |
| `src/lq/data/compute/aggregate.py` | 周线/月线聚合（已建） |
| `src/lq/data/compute/pipeline.py` | 完整 L1→L2 构建管道入口（已建） |
| `scripts/data/build_l2_adjusted.py` | Step 2 构建脚本入口（已建） |

## 8. 验证标准（对齐父系统 137 号卡）

1. 选取 5 只有代表性的股票（含分红/送股/配股）
2. `stock_daily_adjusted.adjustment_factor` 与 tushare `adj_factor` 接口读数差异 < 0.5%
3. `stock_monthly_adjusted` 聚合结果与 tushare `monthly(adj=hfq)` 差异 < 0.5%
4. 停牌股不产生多余记录

## 9. 铁律

1. 后复权因子只从 L1 本地计算，禁止直接用 tushare / baostock 复权价写入 L2。
2. `stock_daily_adjusted.adjust_method` 固定为 `'backward'`，不允许存其他值。
3. 增量重算时必须覆盖受影响股票的全量历史，不能只算新增日期。
4. `build_l2_adjusted.py` 必须幂等，重复运行不产生重复记录。
