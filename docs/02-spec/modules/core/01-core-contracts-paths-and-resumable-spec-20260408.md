# core 合同、路径与续跑规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/core/00-core-charter-20260401.md`。

## 1. 范围

本规格以 `docs/01-design/modules/core/00-core-charter-20260401.md`、
`docs/01-design/modules/core/01-core-contracts-design-20260401.md`、
`docs/01-design/modules/core/02-core-paths-design-20260401.md`
和 `016` 执行结论为上位设计锚点，只记录**当前代码中已落地的正式公共合同**。

本规格冻结：

1. `core.contracts` 中跨模块公共枚举与常量
2. `core.paths` 中 `WorkspaceRoots / DatabasePaths / default_settings()` 路径合同
3. `core.calendar` 中交易日历最小合同
4. `core.checkpoint / core.resumable` 中长任务 checkpoint 与续跑 helper 的最小合同

本规格不覆盖：

1. 任一业务模块的内部逻辑
2. 业务数据库 schema
3. `system` 的 `_meta_runs` run metadata 目标态

## 2. 当前实现状态

当前已核实到的 core 代码落点：

1. `src/lq/core/contracts.py` — 已实现
2. `src/lq/core/paths.py` — 已实现
3. `src/lq/core/calendar.py` — 已实现
4. `src/lq/core/checkpoint.py` — 已实现
5. `src/lq/core/resumable.py` — 已实现
6. `src/lq/core/__init__.py` — 已导出部分公共入口（当前未覆盖全部 `paths` helper）

说明：

1. `core` 是所有模块共享的基础层。
2. `core` 当前不拥有任何业务数据库。
3. `core` 当前不负责业务 run metadata 落库。

## 3. `contracts.py` 公共合同

### 3.1 背景层枚举

按 `016` 执行结论，`MALF` 当前正式主轴已重定向为
`四格上下文 + 生命周期三轴原始排位 + 四分位辅助表达`。
因此 `core.contracts` 中三组背景枚举的当前地位是：

1. `MonthlyState8`：计算层诊断状态，保留兼容与追溯用途
2. `WeeklyFlowRelation`：计算层顺逆辅助状态，保留兼容推导入口
3. `MalfContext4`：执行层正式主轴
4. `monthly_state_8 × weekly_flow_relation` 不再是执行层主读数

| 枚举 | 当前值域 | 用途 |
| --- | --- | --- |
| `MonthlyState8` | `BULL_* / BEAR_*` 八态 | MALF 计算层诊断状态 |
| `WeeklyFlowRelation` | `with_flow / against_flow` | 周线与月线顺逆辅助状态；兼容桥接输入 |
| `MalfContext4` | `BULL_MAINSTREAM / BULL_COUNTERTREND / BEAR_MAINSTREAM / BEAR_COUNTERTREND` | MALF 执行层四格上下文 |

已实现辅助行为：

1. `MonthlyState8.is_bull`
2. `MonthlyState8.is_bear`
3. `MonthlyState8.is_trending`
4. `MalfContext4.from_monthly_weekly()`

`from_monthly_weekly()` 当前映射口径：

| 月线大类 | 周线关系 | 推导结果 |
| --- | --- | --- |
| `MonthlyState8.is_bull = True` | `with_flow` | `BULL_MAINSTREAM` |
| `MonthlyState8.is_bull = True` | `against_flow` | `BULL_COUNTERTREND` |
| `MonthlyState8.is_bear = True` | `with_flow` | `BEAR_MAINSTREAM` |
| `MonthlyState8.is_bear = True` | `against_flow` | `BEAR_COUNTERTREND` |

说明：四格只负责执行层分类；生命周期主读数不编码在 `core.contracts` 中，而由 `MALF` 输出的三轴原始排位与四分位辅助表达承担。

### 3.2 PAS 触发层枚举与治理字典

| 对象 | 当前值域 / 作用 |
| --- | --- |
| `PasTriggerPattern` | `BOF / BPB / PB / TST / CPB` |
| `PasTriggerStatus` | `MAINLINE / CONDITIONAL / REJECTED / PENDING` |
| `PAS_TRIGGER_STATUS` | 当前 trigger 治理状态字典 |

当前代码中 `PAS_TRIGGER_STATUS`：

1. `BOF → MAINLINE`
2. `BPB → REJECTED`
3. `PB → CONDITIONAL`
4. `TST → CONDITIONAL`
5. `CPB → REJECTED`

规则：

1. 业务模块不得自定义重复 trigger 状态判断。
2. `system` 层不得绕过该字典自行放行 `BPB`。

### 3.3 结构位与过滤枚举

| 枚举 | 当前值域 |
| --- | --- |
| `StructureLevelType` | `SUPPORT / RESISTANCE / PIVOT_LOW / PIVOT_HIGH / POST_BREAKOUT_SUPPORT / POST_BREAKDOWN_RESISTANCE / TEST_POINT` |
| `BreakoutType` | `VALID_BREAKOUT / FALSE_BREAKOUT / TEST / PULLBACK_CONFIRMATION / UNKNOWN` |
| `AdverseConditionType` | `COMPRESSION_NO_DIRECTION / STRUCTURAL_CHAOS / INSUFFICIENT_SPACE / SIGNAL_CONFLICT / BACKGROUND_NOT_SUPPORTING` |

### 3.4 交易管理枚举

| 枚举 | 当前值域 |
| --- | --- |
| `TradeLifecycleState` | `PENDING_ENTRY / ACTIVE_INITIAL_STOP / FIRST_TARGET_HIT / TRAILING_RUNNER / CLOSED_WIN / CLOSED_LOSS / CLOSED_TIME / CANCELLED` |

### 3.5 公共常量

| 常量组 | 当前内容 |
| --- | --- |
| 指数标识 | `PRIMARY_INDEX_CODE`、`VALIDATION_INDEX_CODES`、`MARKET_CONTEXT_ENTITY_CODE` |
| 交易费率 | `COMMISSION_RATE=0.0003`、`STAMP_DUTY_RATE=0.0005`、`TRANSFER_FEE_RATE=0.00002` |
| 默认资金合同 | `DEFAULT_CAPITAL_BASE=1_000_000.0`、`DEFAULT_FIXED_NOTIONAL=100_000.0`、`DEFAULT_LOT_SIZE=100` |
| PAS 方向 | `PAS_SIGNAL_SIDE="LONG"`、`PAS_SIGNAL_ACTION="BUY"` |

说明：

1. 本规格只确认当前代码中的实际常量值。
2. 业务模块不得在本地重复硬编码这些常量。

## 4. `paths.py` 路径合同

### 4.1 `DatabasePaths`

当前 `DatabasePaths` 冻结的是**正式七数据库**路径合同。

| 字段 | 含义 |
| --- | --- |
| `raw_market` | L1 原始市场库：原始日线（TDX txt / `.day`）与 `raw_xdxr_event` |
| `market_base` | L2 基础市场库：后复权日/周/月线、均线、量比 |
| `malf` | L3 MALF 库：计算层输出与 `execution_context` 快照 |
| `structure` | L3 structure 库：结构位快照 |
| `filter` | L3 filter 库：不利条件检查结果 |
| `research_lab` | L3 研究库：PAS 信号与仓位计划 |
| `trade_runtime` | L4 交易运行库：交易记录与权益曲线 |

### 4.2 `WorkspaceRoots`

| 字段 | 含义 |
| --- | --- |
| `repo_root` | 仓库根目录 |
| `data_root` | 数据根目录 |
| `temp_root` | 临时目录根 |
| `report_root` | 报告目录根 |
| `validated_root` | 验证资产根目录 |

已实现行为：

1. `WorkspaceRoots.databases`
2. `WorkspaceRoots.ensure_directories()`

### 4.3 `default_settings()`

当前支持的环境变量：

1. `LQ_REPO_ROOT`
2. `LQ_DATA_ROOT`
3. `LQ_TEMP_ROOT`
4. `LQ_REPORT_ROOT`
5. `LQ_VALIDATED_ROOT`
6. `TDX_ROOT`
7. `TDX_OFFLINE_DATA_ROOT`
8. `TUSHARE_TOKEN_PATH`

当前默认目录名约定：

1. `Lifespan-Quant-data`
2. `Lifespan-temp`
3. `Lifespan-Quant-report`
4. `Lifespan-Quant-Validated`

说明：以上四项是仓库同级目录默认名；`repo_root` 默认通过 `discover_repo_root()` 向上定位 `pyproject.toml` 解析。

### 4.4 其他路径 helper

| 函数 | 作用 |
| --- | --- |
| `discover_repo_root()` | 向上定位含 `pyproject.toml` 的仓库根目录 |
| `tdx_root()` | 解析通达信目录 |
| `tdx_offline_data_root()` | 解析通达信离线导出目录 |
| `tushare_token_path()` | 解析 tushare token 文件路径 |

当前稳定导入路径说明：

1. 以上 helper 的正式定义位置是 `lq.core.paths`。
2. 当前规格不承诺这些 helper 必须全部由 `lq.core` 顶层 re-export；需要稳定导入时，应优先使用 `from lq.core.paths import ...`。

当前默认值口径：

1. `tdx_root()` 默认返回 `H:\new_tdx64`
2. `tdx_offline_data_root()` 默认返回 `H:\tdx_offline_Data`
3. `tushare_token_path()` 未设置时返回 `None`
4. `tdx_offline_data_root()` 仅用于离线导出目录，不替代 `TDX_ROOT` 下的 `.day / gbbq` 主线来源

## 5. `calendar.py` 交易日历合同

当前已实现：

1. `is_trading_day(d)`
2. `next_trading_day(d)`

当前代码口径：

1. 跳过周末
2. 使用内置节假日表覆盖 2024-2027
3. 若年份超过支持上限，会在 `_is_holiday()` fail fast 抛 `ValueError`

说明：

1. 这是最小交易日历合同。
2. 业务模块可依赖其 `T+1` 语义，但不得假定它已经是全历史完整交易所日历。

## 6. `checkpoint.py / resumable.py` 续跑合同

### 6.1 `JsonCheckpointStore`

当前已实现方法：

1. `exists`
2. `load()`
3. `save(payload)`
4. `update(**changes)`
5. `clear()`

### 6.2 `resumable.py` helper

| 函数 | 作用 |
| --- | --- |
| `stable_json_dumps()` | 稳定 JSON 序列化 |
| `build_resume_digest()` | 基于 fingerprint 生成短摘要 |
| `resolve_default_checkpoint_path()` | 解析默认 checkpoint 路径 |
| `prepare_resumable_checkpoint()` | 加载与校验 checkpoint |
| `save_resumable_checkpoint()` | 写回带 fingerprint 的 checkpoint |
| `parse_optional_date()` | 解析可选日期参数 |

### 6.3 当前治理规则

`prepare_resumable_checkpoint()` 当前已实现以下规则：

1. `reset_checkpoint=True` 时先清空旧 checkpoint
2. 若 fingerprint 不匹配，则拒绝复用旧 checkpoint
3. 若存在 `running` 状态 checkpoint 且本次未显式 `resume=True`，则拒绝直接重跑

## 7. 写权与依赖边界

允许：

1. 所有业务模块 import `lq.core.*`
2. 各模块通过 `WorkspaceRoots / DatabasePaths` 获取路径
3. 各 runner 通过 `JsonCheckpointStore / resumable` 使用统一 checkpoint 机制

禁止：

1. `core` import 任一业务模块
2. 业务模块重复定义已存在于 `core.contracts` 的枚举
3. 业务模块硬编码外部目录路径，绕过 `default_settings()`
4. 把业务数据库 schema、业务 run metadata 或业务计算塞进 `core`

## 8. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/core/contracts.py` | ✅ 已有 | 公共枚举与常量 |
| `src/lq/core/paths.py` | ✅ 已有 | 路径合同与环境变量解析 |
| `src/lq/core/calendar.py` | ✅ 已有 | 最小交易日历 |
| `src/lq/core/checkpoint.py` | ✅ 已有 | JSON checkpoint 存储 |
| `src/lq/core/resumable.py` | ✅ 已有 | 续跑 helper |
| `src/lq/core/__init__.py` | ✅ 已有 | 部分公共导出入口（非全部 `paths` helper 均顶层 re-export） |

## 9. 当前与 design 目标的关系

1. `core` 当前已基本具备 design 中定义的五类基础能力。
2. 本规格只记录**已在代码中核实到**的公共合同，不把 design 中尚未必要的治理 manifest 直接写入正式 spec。
3. `016` 已把 `MALF` 正式主轴重定向到四格上下文与生命周期三轴表达；本规格已按该结论收敛 `core` 层可见的公共合同语义。
