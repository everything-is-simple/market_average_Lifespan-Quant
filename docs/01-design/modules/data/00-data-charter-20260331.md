# data 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\data\` | 正式定型，mootdx/gbbq/tushare 三层架构 |
| 本系统 | `G:\Lifespan-Quant\src\lq\data\` | 继承父系统架构，主线完全本地化 |

父系统 data 模块设计文档是本模块的权威参考。

## 2. 模块定位

`data` 是数据基础设施层。

它负责数据采集、清洗、存储和增量更新，向上游模块提供可信的市场数据基础库（`market_base`）。

**设计原则：主线完全本地化，零网络依赖即可运行。** tushare（第一校准源）与 baostock（第二校准源）仅用于 cross-source 审计，均不参与 L2 主链构建。

## 3. 数据来源（四层，冻结）

| 来源 | 类型 | 角色 |
|---|---|---|
| mootdx + `.day` 文件 | 本地离线 | **主线**，日线 OHLCV 原始数据 |
| TDX gbbq 文件 | 本地离线 | **主线**，除权除息事件（分红/送股/配股） |
| tushare HTTP API | 在线辅助 | **第一校准源**，复权因子 cross-check、基本面快照、交易日历 |
| baostock API | 在线辅助 | **第二校准源 / fallback**，`adjust_factor` + `dividend_data` 双校验 |

路径注入：
- `TDX_ROOT` 环境变量 → 通达信本地目录（默认 `G:\new-tdx\new-tdx`）
- `TUSHARE_TOKEN_PATH` 环境变量 → token 文件路径（可选，仅审计用）

### 3.1 双源校准五类事件规则（继承父系统 139 号卡冻结，不可随意修改）

| 类别 | 规则状态 | 说明 |
|---|---|---|
| category 1 | `provisional_dual_source_comparable_with_mild_drift_watch` | 主体双源可比，但 mild drift 会重复出现，保持观察 |
| category 2 | `conditional_comparable_with_mild_drift_watch` | 条件可比，mild drift watch |
| category 3 | `stable_baostock_boundary_use_tushare_fill` | 最稳定，baostock boundary + tushare 补填 |
| category 5 | `boundary_fill_with_mild_drift_watch` | boundary fill 主导，mild drift watch |
| category 9 | `holdout_pending_factor_path_resolution` | 悬置，factor path 问题未解决前不纳入正式链 |

BaoStock 在本系统中永远是**第二校准源**，不是主源，不是第一校准源的替代。
若要升级 BaoStock 的使用深度（如全量 batch audit、阈值冻结），必须另开独立执行卡，不允许在现有脚本中静默扩展。

## 4. 数据分层（冻结）

| 层 | 数据集 | 来源 | 存储 |
|---|---|---|---|
| L1（原始） | `raw_stock_daily` / `raw_index_daily` | mootdx 本地 | `raw_market.duckdb` |
| L1（原始） | `raw_xdxr_event` | TDX gbbq | `raw_market.duckdb` |
| L1（原始） | `raw_asset_snapshot` | tushare `stock_basic`（低频） | `raw_market.duckdb` |
| L2（标准） | `stock_daily_adjusted` | L1 本地计算（后复权） | `market_base.duckdb` |
| L2（标准） | `stock_weekly_adjusted` / `stock_monthly_adjusted` | L2 聚合 | `market_base.duckdb` |
| L2（标准） | `index_daily` / `index_weekly` / `index_monthly` | L1 聚合 | `market_base.duckdb` |
| L2（标准） | `trade_calendar` | tushare `trade_cal`（低频） | `market_base.duckdb` |

复权因子 = 由 `raw_stock_daily` + `raw_xdxr_event` 本地计算（后复权，backward adjusted），不使用外部复权接口。

## 5. 正式输入输出

- **输入**：`TDX_ROOT` 指向的通达信目录（本地文件系统）
- **输出**：`raw_market.duckdb`（L1）、`market_base.duckdb`（L2）

## 6. 增量更新语义

1. 每次运行扫描 `window_start → window_end` 范围内的新增 `.day` 数据
2. 已存在的日期不重复写入（幂等）
3. 断点续传：通过 `base_incremental_entity` 跟踪每个资产的最后成功更新日期
4. gbbq 事件增量同步：检测 gbbq 文件 mtime，变更时触发重新解析

## 7. 模块边界

### 7.1 负责

1. L1 原始数据采集（mootdx + gbbq）
2. L2 标准库构建（复权 + 聚合）
3. 增量更新与断点续传
4. tushare 审计探针（第一校准，低频，可选）
5. baostock 审计探针（第二校准，低频，按五类事件规则使用）
6. schema bootstrap（DuckDB 建表）

### 7.2 不负责

1. MALF 计算（属于 `malf`）
2. 任何信号研究或 trigger 探测
3. 直接输出给 `trade_runtime`

## 8. 铁律

1. `raw_market` 层只做原始事实存储，不做任何调整或推断。
2. `market_base` 层的复权因子只能从 L1 本地计算，禁止直接用 tushare 或 baostock 复权价。
3. tushare 只能写审计表，禁止写 `raw_market` 或 `market_base` 正式表。
4. baostock 永远是第二校准源，禁止替代 tdx_local 主链，禁止未经审计反写正式五库。
5. 若要升级 baostock 的使用深度（全量 batch audit / 阈值冻结），必须另开独立执行卡，不允许静默扩展。
6. 所有路径通过 `core/paths.py` 注入，禁止硬编码路径或 token。
7. 增量更新必须幂等，重复运行不产生重复记录。

## 9. 成功标准

1. 能从本地通达信目录完整读取全市场日线数据
2. gbbq 解析后除权因子与 tushare 审计差异在允许阈值内
3. `stock_daily_adjusted` 后复权价格计算结果可重现
4. 增量更新在 `window_start/window_end` 语义下正确运行
5. 所有 DuckDB schema 通过 bootstrap 脚本正确创建

## 10. 本模块设计文档索引

| 文档 | 内容 | 继承父系统来源 |
|---|---|---|
| `00-data-charter-20260331.md` | 模块章程（本文） | 父系统 `00` |
| `01-data-l2-backward-adjustment-compute-design-20260401.md` | L2 后复权计算管道：复权公式、聚合规则、asset_master、验证阈值 | 父系统 `49/50/137` |
