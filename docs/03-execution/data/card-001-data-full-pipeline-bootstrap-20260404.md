# CARD-001 data 全链路 bootstrap（txt 全量灌入 + 路径修正）/ 2026-04-04

## 目标

完成 data 模块从零到可用的全链路初始化：
1. 修正五目录路径常量（对齐实际磁盘结构）
2. 实现 TDX 导出 txt 文件全量灌入（L1 + L2 一次性填充）
3. 验证灌入数据与通达信软件显示一致

## 前置条件

- [x] 新版 data 章程已冻结（`00-data-charter-20260404.md`）
- [x] txt 灌入设计文档已冻结（`02-data-l1-tdx-txt-bulk-import-design-20260404.md`）
- [x] `H:\tdx_offline_Data` 目录已准备好（通达信导出完成）
- [x] `H:\new_tdx64` 通达信已安装
- [x] `H:\Lifespan-Quant-data` 目录已创建（含 raw/base/malf/research/trade 子目录）

## 执行步骤

### P0 — 路径修正

1. 修改 `src/lq/core/paths.py`：
   - `_DATA_DIRNAME` → `"Lifespan-Quant-data"`
   - `_TEMP_DIRNAME` → `"Lifespan-Quant-temp"`
   - `_REPORT_DIRNAME` → `"Lifespan-Quant-report"`
   - `_VALIDATED_DIRNAME` → `"Lifespan-Quant-Validated"`
   - `_DEFAULT_TDX_ROOT` → `Path(r"H:\new_tdx64")`
   - 新增 `_DEFAULT_TDX_OFFLINE_DATA_ROOT` + `tdx_offline_data_root()` 函数

2. 修改 `src/lq/data/contracts.py`：
   - `DataSourceType` 新增 `TDX_OFFLINE_TXT = "tdx_offline_txt"`

3. 清理脚本 docstring 中的旧路径 `G:\new-tdx\new-tdx`

### P1 — txt 解析器

4. 新建 `src/lq/data/providers/tdx_txt_reader.py`：
   - `discover_txt_files(root, adjust_type, market)` — 扫描文件列表
   - `parse_txt_file(path)` — 解析单个 txt 文件为 DataFrame
   - `extract_metadata(first_line)` — 提取元信息（代码、名称、周期、调整类型）

### P2 — 全量灌入脚本

5. 新建 `scripts/data/bootstrap_from_txt.py`：
   - 参数：`--data-root`、`--adjust-types`、`--markets`、`--limit`、`--dry-run`
   - 流程：schema 初始化 → L1 灌入 → L2 灌入 → 周月线聚合 → manifest 写入

### P3 — 验证

6. 抽样 10 只股票验证：
   - `raw_stock_daily` 行数与 txt 文件行数一致
   - `stock_daily_adjusted`（backward）价格与通达信软件一致
   - 停牌日未出现在 L2
   - 北交所股票正确入库

## 验收标准

1. `bootstrap_from_txt.py --dry-run` 正确打印计划
2. 全量灌入完成，无报错
3. 抽样 10 只股票价格一致
4. `fetch_daily.py` 增量追加不破坏历史
5. `paths.py` 解析出的路径与实际磁盘目录一致

## 产出物

- `src/lq/core/paths.py`（修改）
- `src/lq/data/contracts.py`（修改）
- `src/lq/data/providers/tdx_txt_reader.py`（新建）
- `scripts/data/bootstrap_from_txt.py`（新建）
- evidence + record + conclusion（执行后补）
