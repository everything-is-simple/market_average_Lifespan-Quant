# data L1 TDX 导出 txt 全量灌入设计 / 2026-04-04

> 本文档定义通达信离线导出 txt 文件的一次性全量灌入方案，作为两步走架构的 Step 1。

## 1. 问题陈述

当前 L1（`raw_stock_daily`）和 L2（`stock_daily_adjusted`）的数据来源是 `.day` 二进制文件 + `gbbq` 除权除息计算。
该路径存在以下痛点：

1. **首次灌入耗时长**：需逐文件解析 ~5000 个 `.day` 文件，再全量计算复权因子
2. **复权精度依赖 gbbq 完整性**：若 gbbq 文件缺失或损坏，复权价不准确
3. **无法获得前复权数据**：当前管道只输出后复权

通达信软件提供"数据导出"功能，可将全市场历史数据导出为 txt 文件，
包含未复权、前复权、后复权三种调整类型。这些数据由通达信官方计算，精度与软件显示一致。

## 2. 数据源规格

### 2.1 目录结构

```
TDX_OFFLINE_DATA_ROOT/          # 默认 H:\tdx_offline_Data
  stock/
    Non-Adjusted/               # 未复权
      SH#600000.txt
      SZ#000001.txt
      BJ#430047.txt
      ...
    Forward-Adjusted/           # 前复权
      SH#600000.txt
      ...
    Backward-Adjusted/          # 后复权
      SH#600000.txt
      ...
  index/                        # 指数（可选，仅未复权）
    Non-Adjusted/
      SH#000001.txt
      ...
```

### 2.2 文件命名规则

- 格式：`{MARKET}#{CODE}.txt`
- MARKET：`SH`（上海）、`SZ`（深圳）、`BJ`（北京）
- CODE：6 位纯数字代码
- 标准化后：`{CODE}.{MARKET}`，如 `600000.SH`、`000001.SZ`、`430047.BJ`

### 2.3 文件内部格式（TSV）

```
600000 浦发银行 日线 不复权          ← 第1行：元信息（代码 名称 周期 调整类型）
      日期	    开盘	    最高	    最低	    收盘	    成交量	    成交额    ← 第2行：列头
1999/11/10	29.50	29.80	27.00	27.75	174085000	4859102208.00   ← 第3行起：数据
1999/11/11	27.58	28.38	27.53	27.71	29403400	821582208.00
...
```

| 字段 | 类型 | 说明 |
|---|---|---|
| 日期 | `YYYY/MM/DD` | 交易日期 |
| 开盘 | float | 开盘价 |
| 最高 | float | 最高价 |
| 最低 | float | 最低价 |
| 收盘 | float | 收盘价 |
| 成交量 | int | 成交量（股） |
| 成交额 | float | 成交额（元） |

### 2.4 元信息行解析

第1行格式：`{code} {name} {period} {adjust_type}`

| adjust_type 文本 | 映射 |
|---|---|
| `不复权` | `non_adjusted` |
| `前复权` | `forward` |
| `后复权` | `backward` |

## 3. 灌入策略

### 3.1 映射关系

| txt 子目录 | adjust_type | 目标表 | 层级 | 优先级 |
|---|---|---|---|---|
| `Non-Adjusted` | `non_adjusted` | `raw_stock_daily` | L1 | P0（必须） |
| `Backward-Adjusted` | `backward` | `stock_daily_adjusted` | L2 | P0（必须） |
| `Forward-Adjusted` | `forward` | `stock_daily_adjusted` | L2 | P1（可选） |

### 3.2 字段映射

**Non-Adjusted → raw_stock_daily：**

| txt 字段 | 目标字段 | 转换 |
|---|---|---|
| 文件名 | `code` | `{CODE}.{MARKET}` |
| 日期 | `trade_date` | `YYYY/MM/DD` → `DATE` |
| 开盘 | `open` | float |
| 最高 | `high` | float |
| 最低 | `low` | float |
| 收盘 | `close` | float |
| 成交量 | `volume` | float |
| 成交额 | `amount` | float |
| — | `provider_name` | 固定 `'tdx_offline_txt'` |
| — | `is_suspended` | `volume == 0` 判定 |
| — | `ingest_run_id` | 运行时生成 |

**Backward-Adjusted / Forward-Adjusted → stock_daily_adjusted：**

| txt 字段 | 目标字段 | 转换 |
|---|---|---|
| 文件名 | `code` | `{CODE}.{MARKET}` |
| 日期 | `trade_date` | `YYYY/MM/DD` → `DATE` |
| 开盘 | `open` | float（已复权） |
| 最高 | `high` | float（已复权） |
| 最低 | `low` | float（已复权） |
| 收盘 | `close` | float（已复权） |
| — | `volume` | 从对应 Non-Adjusted 取原始值 |
| — | `amount` | 从对应 Non-Adjusted 取原始值 |
| — | `adjust_method` | `'backward'` 或 `'forward'` |
| — | `adjustment_factor` | `adj_close / raw_close`（从两表关联计算） |
| — | `build_run_id` | 运行时生成 |

### 3.3 停牌日处理

- `volume == 0` 的交易日视为停牌日
- 停牌日写入 `raw_stock_daily`（`is_suspended = TRUE`）
- 停牌日**不写入** `stock_daily_adjusted`（继承 L2 铁律）

### 3.4 幂等性

- 使用 `INSERT OR REPLACE`，以 PRIMARY KEY 去重
- 重复运行相同数据不产生重复记录
- 支持断点续传：记录已完成的文件列表到 checkpoint

## 4. 执行流程

```
bootstrap_from_txt.py
  │
  ├─ 1. 解析参数（data_root、adjust_types、markets、limit 等）
  ├─ 2. 确保 schema 存在（调用 bootstrap_data_storage）
  ├─ 3. 扫描 Non-Adjusted 目录 → 获取文件列表
  ├─ 4. 逐文件解析 → 批量写入 raw_stock_daily（L1）
  ├─ 5. 扫描 Backward-Adjusted 目录 → 获取文件列表
  ├─ 6. 逐文件解析 → 与 L1 关联计算 adjustment_factor → 批量写入 stock_daily_adjusted（L2）
  ├─ 7.（可选）扫描 Forward-Adjusted → 同上
  ├─ 8. 聚合周/月线（复用 compute/aggregate.py）
  └─ 9. 写 ingest_manifest / build_manifest
```

## 5. 性能预估

| 指标 | 预估值 |
|---|---|
| 全市场股票数 | ~5,500 只 |
| 平均每文件行数 | ~5,000 行（20 年历史） |
| 总行数 | ~2,750 万行 × 3 调整类型 |
| 单文件解析耗时 | ~10ms（pandas read_csv） |
| 总灌入耗时（L1+L2） | ~15-30 分钟 |

优化手段：
- 批量 INSERT（每 500 只股票一批）
- 使用 `pandas.read_csv` + `sep='\t'` 直接解析
- DuckDB 的 `INSERT INTO ... SELECT FROM df`（零拷贝注册）

## 6. 代码落点

| 文件 | 职责 |
|---|---|
| `src/lq/data/providers/tdx_txt_reader.py` | txt 文件发现、解析、标准化 |
| `scripts/data/bootstrap_from_txt.py` | 一次性全量灌入脚本入口 |
| `src/lq/core/paths.py` | 新增 `tdx_offline_data_root()` 函数 |
| `src/lq/data/contracts.py` | 新增 `TDX_OFFLINE_TXT` 数据源类型 |

## 7. 验证标准

1. `raw_stock_daily` 行数 ≥ 全市场历史总交易日数（抽样 10 只确认完整）
2. `stock_daily_adjusted`（backward）价格与通达信软件"后复权"模式显示一致
3. 停牌日不出现在 `stock_daily_adjusted` 中
4. `adjustment_factor = adj_close / raw_close` 误差 < 0.01%（数值精度）
5. 北交所（BJ）股票正确入库
6. 灌入后 `fetch_daily.py` 增量追加不影响历史数据
