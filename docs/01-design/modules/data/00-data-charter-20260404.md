# data 模块章程 / 2026-04-04（v2）

> 取代 `00-data-charter-20260331.md`。反映两步走架构、五目录命名修正、TDX 离线数据源新增。

## 1. 血统与定位

- **爷爷系统**：EmotionQuant-gamma — 原始 mootdx 读取 + gbbq 除权
- **父系统**：MarketLifespan-Quant — 成熟的 5 库架构、pipeline、双源审计
- **本系统**：Lifespan-Quant — 继承父系统数据管道，新增 TDX 导出 txt 全量灌入

### 1.1 核心变更（相比 v1 章程）

| 变更项 | v1（20260331） | v2（本文） |
|---|---|---|
| L1/L2 初始数据来源 | 仅 .day 二进制 + gbbq | **新增 TDX 导出 txt 文件全量灌入** |
| 增量更新 | .day + gbbq | 不变（.day + gbbq） |
| TDX 默认路径 | `G:\new-tdx\new-tdx` | `H:\new_tdx64`（环境变量 `TDX_ROOT`） |
| 离线数据路径 | 无 | `H:\tdx_offline_Data`（环境变量 `TDX_OFFLINE_DATA_ROOT`） |
| 五目录命名 | `Lifespan-data` 等 | `Lifespan-Quant-data` 等（修正） |
| 前复权数据 | 不支持 | 可选灌入（adjust_method='forward'） |

## 2. 两步走架构

### Step 1：一次性全量灌入（bootstrap）

数据来源：`TDX_OFFLINE_DATA_ROOT`（默认 `H:\tdx_offline_Data`）下的导出 txt 文件。

```
tdx_offline_Data/
  stock/
    Non-Adjusted/       → SH#600000.txt, SZ#000001.txt, BJ#...
    Forward-Adjusted/   → 同上命名
    Backward-Adjusted/  → 同上命名
  index/
    Non-Adjusted/       → ...
```

txt 文件格式（TSV，每文件单只股票全历史）：

```
600000 浦发银行 日线 不复权
      日期	    开盘	    最高	    最低	    收盘	    成交量	    成交额
1999/11/10	29.50	29.80	27.00	27.75	174085000	4859102208.00
```

灌入策略：

| txt 子目录 | 目标表 | 层级 | adjust_method |
|---|---|---|---|
| `Non-Adjusted` | `raw_stock_daily` | L1 | — |
| `Backward-Adjusted` | `stock_daily_adjusted` | L2 | `'backward'` |
| `Forward-Adjusted` | `stock_daily_adjusted` | L2 | `'forward'`（可选） |

**关键优势**：txt 文件包含通达信已计算好的完美除权除息价格（精度与通达信软件一致），
一次灌入即同时完成 L1（原始行情）和 L2（复权行情）的初始化，无需自行计算复权因子。

### Step 2：日增量更新（daily incremental）

数据来源：`TDX_ROOT`（默认 `H:\new_tdx64`）下的 `.day` 二进制文件 + `gbbq` 除权除息文件。

- 每日通达信软件自动同步行情 → `.day` 文件更新
- 解析 `.day` → 追加至 `raw_stock_daily`（L1）
- 解析 `gbbq` → 更新 `raw_xdxr_event`（L1）
- 基于 L1 增量计算 → 更新 `stock_daily_adjusted`（L2）
- 支持断点续传（checkpoint 机制）

## 3. 数据源矩阵

| 源 | 类型 | 角色 | 环境变量 |
|---|---|---|---|
| TDX 导出 txt | 离线文件 | **主线 — 一次性全量灌入** | `TDX_OFFLINE_DATA_ROOT` |
| TDX 本地 .day | 离线文件 | **主线 — 日增量** | `TDX_ROOT` |
| TDX 本地 gbbq | 离线文件 | **主线 — 除权除息事件** | `TDX_ROOT` |
| mootdx | Python 包 | .day 解析加速（可选，有二进制兜底） | — |
| tushare | HTTP API | 第一校准源（仅审计） | `TUSHARE_TOKEN_PATH` |
| baostock | Python 包 | 第二校准源（仅审计） | — |

## 4. 数据分层

### L1 — raw_market.duckdb

| 表 | 来源 | 说明 |
|---|---|---|
| `raw_stock_daily` | txt（全量）/ .day（增量） | 未复权 OHLCV |
| `raw_index_daily` | txt（全量）/ .day（增量） | 指数日线 |
| `raw_xdxr_event` | gbbq | 14 类企业行动事件 |
| `raw_asset_snapshot` | tushare | 资产快照（审计用） |
| `raw_ingest_manifest` | 自动生成 | 入库流水 |

### L2 — market_base.duckdb

| 表 | 来源 | 说明 |
|---|---|---|
| `stock_daily_adjusted` | txt（全量）/ compute（增量） | 复权日线（backward / forward） |
| `stock_weekly_adjusted` | 聚合 | 复权周线 |
| `stock_monthly_adjusted` | 聚合 | 复权月线 |
| `index_daily` | 清洗 | 指数日线 |
| `index_weekly / index_monthly` | 聚合 | 指数周/月线 |
| `trade_calendar` | tushare | 交易日历 |
| `asset_master` | raw_asset_snapshot | 资产主表 |
| `block_master / block_membership_snapshot` | TDX block | 板块分类 |
| `base_build_manifest` | 自动生成 | 构建流水 |

## 5. 五目录纪律（修正）

| 目录 | 实际路径 | 用途 |
|---|---|---|
| repo | `H:\Lifespan-Quant` | 代码、文档、测试、治理 |
| data | `H:\Lifespan-Quant-data` | 正式七数据库、数据产物 |
| temp | `H:\Lifespan-temp` | 临时文件、pytest、中间产物 |
| report | `H:\Lifespan-Quant-report` | 报表、图表、正式导出 |
| validated | `H:\Lifespan-Quant-Validated` | 跨版本验证资产快照 |

对应 `paths.py` 当前默认常量：

```python
_DATA_DIRNAME      = "Lifespan-Quant-data"
_TEMP_DIRNAME      = "Lifespan-temp"
_REPORT_DIRNAME    = "Lifespan-Quant-report"
_VALIDATED_DIRNAME = "Lifespan-Quant-Validated"
_DEFAULT_TDX_ROOT  = Path(r"H:\new_tdx64")
_DEFAULT_TDX_OFFLINE_DATA_ROOT = Path(r"H:\tdx_offline_Data")
```

## 6. 模块边界

### data 模块拥有

- `raw_market.duckdb`（L1）的全部表写权
- `market_base.duckdb`（L2）的全部表写权
- `providers/` 下所有数据源适配器
- `compute/` 下所有 L1→L2 转换逻辑
- `audit/` 下所有双源校验探针

### data 模块不做

- 不计算 MALF（属于 `malf` 模块）
- 不产生交易信号（属于 `alpha/pas` 模块）
- 不写 `research_lab` / `malf` / `trade_runtime` 数据库
- 不直接依赖 `alpha`、`position`、`trade` 模块

## 7. 市场覆盖

| 市场 | vipdoc 子目录 | 代码后缀 | 说明 |
|---|---|---|---|
| 上海 | `sh/lday/` | `.SH` | 主板 + 科创板 |
| 深圳 | `sz/lday/` | `.SZ` | 主板 + 中小板 + 创业板 |
| 北京 | `bj/lday/` | `.BJ` | 北交所 |

txt 文件命名：`{MARKET}#{CODE}.txt`，如 `SH#600000.txt`、`BJ#430047.txt`。

## 8. 代码落点

| 文件 | 职责 | 状态 |
|---|---|---|
| `src/lq/data/bootstrap.py` | L1/L2 schema 定义 | ✅ 已建 |
| `src/lq/data/contracts.py` | 数据合同（DataSourceType 等） | ✅ 已建（已含 `TDX_OFFLINE_TXT`） |
| `src/lq/data/providers/tdx_local.py` | .day 二进制解析 | ✅ 已建 |
| `src/lq/data/providers/tdx_txt_reader.py` | **txt 全量灌入解析器** | ✅ 已建 |
| `src/lq/data/providers/tushare_http.py` | Tushare HTTP 审计客户端 | ✅ 已建 |
| `src/lq/data/providers/baostock.py` | BaoStock 审计 provider | ✅ 已建 |
| `src/lq/data/compute/adjust.py` | 后复权因子计算 | ✅ 已建 |
| `src/lq/data/compute/aggregate.py` | 周/月线聚合 | ✅ 已建 |
| `src/lq/data/compute/pipeline.py` | L1→L2 构建管道 | ✅ 已建 |
| `src/lq/data/audit/baostock_probe.py` | BaoStock 差异探针 | ✅ 已建 |
| `scripts/data/bootstrap_from_txt.py` | **一次性 txt 全量灌入脚本** | ✅ 已建 |
| `scripts/data/bootstrap_storage.py` | 存储初始化 | ✅ 已建 |
| `scripts/data/fetch_daily.py` | .day 增量获取 | ✅ 已建 |
| `scripts/data/ingest_xdxr.py` | gbbq 入库 | ✅ 已建 |
| `scripts/data/build_l2_adjusted.py` | L2 后复权构建 | ✅ 已建 |
| `scripts/data/run_baostock_probe.py` | BaoStock 审计脚本 | ✅ 已建 |

## 9. TDXQuant 定位与 mootdx 澄清（2026-04-04 增补）

### 9.1 TDXQuant 官方 API（已评估，不纳入）

通达信（财富趋势，上市公司）官方发布了 Python 量化客户端 TDXQuant，核心模块为 `tqcenter`。

**致命约束**：`tqcenter` 必须通达信终端进程在运行才能工作。

**不纳入的理由**：
1. 本系统主线管道是无人值守批量任务（盘后定时更新），不能依赖终端进程
2. 系统当前没有实时行情消费模块——既无需求也无消费方
3. mootdx + 兜底二进制解析器已完全覆盖 .day 解析需求

**结论**：TDXQuant 不纳入系统设计。`pyproject.toml` 不列入 `tqcenter`。

### 9.2 mootdx 定位澄清

mootdx **不是**"数据来源"，而是"通达信 .day 二进制格式解析器"。

- 系统的数据来源始终是**通达信本地文件**（上市公司维护，格式 20 年稳定）
- mootdx 只是读取 `.day` 文件的 Python 工具，功能等价于手写二进制解析
- 即使 mootdx 停更，本系统已有二进制兜底解析器（`tdx_local.py`）
- mootdx 的风险等级**远低于** tushare/baostock（后者依赖第三方服务器）

### 9.3 数据源可信度分层

| 数据源 | 维护方 | 可信度 | 本系统角色 |
|---|---|---|---|
| 通达信本地文件（.day / gbbq / txt） | 财富趋势（上市公司） | ⭐⭐⭐⭐⭐ | 主线 |
| TDXQuant `tqcenter` | 财富趋势（官方） | ⭐⭐⭐⭐ | 不纳入（需终端，无消费方） |
| mootdx | 个人开源 | ⭐⭐⭐ | 格式解析器（可替换） |
| tushare | 个人项目 | ⭐⭐ | 仅审计 |
| baostock | 个人项目 | ⭐⭐ | 仅审计 |

---

## 10. 铁律

1. **主线完全本地化**：L1/L2 数据不依赖任何网络 API **或终端进程**。tushare / baostock 仅审计。
2. **raw_market 只存原始事实**：不存计算中间值。
3. **复权价写入 L2 必须标注 adjust_method**：`'backward'` 或 `'forward'`，不允许空值。
4. **baostock 禁止替代主线**：不可作为主数据源直接写入正式库。
5. **路径禁止硬编码**：统一经 `core/paths.py` + 环境变量注入。
6. **txt 灌入为一次性操作**：日常增量只走 .day + gbbq 路径。
7. **增量更新必须幂等**：同参数重复运行不产生重复记录。
8. **TDXQuant 不纳入系统设计**：`tqcenter` 不进入 `pyproject.toml`，不进入任何模块的 import。

## 11. 成功标准

1. `bootstrap_from_txt.py` 能在 30 分钟内完成全市场 txt 灌入（~5000 只股票 × 3 调整类型）
2. 灌入后 `raw_stock_daily` 行数 ≥ 全市场历史总交易日数
3. `stock_daily_adjusted`（backward）价格与通达信软件显示一致（抽样 10 只验证）
4. `fetch_daily.py` 增量追加新行后，不影响历史数据
5. gbbq 解析后除权因子与 tushare 审计差异 < 0.5%
6. 五目录路径解析正确（`paths.py` 单测覆盖）

---

## 变更记录

| 日期 | 变更内容 |
|---|---|
| 2026-04-04 v1 | 初版 v2 章程（两步走架构、TDX txt 灌入） |
| 2026-04-04 v2 | 增补 §9 TDXQuant 定位与 mootdx 澄清、铁律追加第8条 |
