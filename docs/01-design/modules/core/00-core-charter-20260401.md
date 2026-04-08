# core 模块章程 / 2026-04-01

## 1. 血统与来源

| 层代 | 系统 | 核心位置 | 主要吸收点 |
|---|---|---|---|
| 爷爷系统 | EQ-gamma | `src/config.py` + `src/contracts.py` | pydantic Settings 思想（轻量化取舍）、ID 构造规则、ActionType/OrderStatusType 枚举风格 |
| 父系统 | MarketLifespan-Quant | `src/mlq/core/` | `WorkspaceRoots/DatabasePaths` 路径合同模式、env var 覆盖机制、`run_output_families` 治理清单、`table_ownership_manifest` 表级 ownership |
| 本系统 | Lifespan-Quant | `src/lq/core/` | 继承并演进：5 目录（新增 `validated_root`）、大幅扩充枚举层（新增 structure/filter/trade 相关枚举）、精简为纯环境变量注入（去掉 pydantic） |

### 1.1 从各代系统吸收的核心结论

**爷爷系统（EQ-gamma）：**
1. `Settings`（pydantic）承载了所有配置——路径、API token、交易参数、开关——**过重**；本系统取其分层思想，去掉 pydantic，改用纯环境变量注入
2. `contracts.py` 的 ID 构造函数（`build_signal_id`、`build_order_id`）是跨模块追溯的基础，格式一旦固定不允许变更
3. 枚举类型（`ActionType / OrderStatusType / PositionStateType`）放在顶层 contracts 是正确的设计——消除各模块自己定义一套魔法字符串

**父系统（MarketLifespan）：**
1. `WorkspaceRoots + DatabasePaths` 两层 dataclass 是路径合同的正确抽象，本系统直接继承
2. `discover_repo_root()`（向上找 `pyproject.toml`）比 `__file__.parents[N]` 更稳健，本系统沿用
3. `run_output_families.py + table_ownership_manifest.py` 是**治理合同**，当前阶段 Lifespan-Quant 先不引入，等主线跑通后按需增补
4. 父系统 `core` 只有 4 个 workspace 根（无 `validated_root`），本系统增加第 5 个

**本系统当前实现（v0.1.0）：**
1. `contracts.py`：4 组枚举（其中 `MonthlyState8 / WeeklyFlowRelation` 为计算层诊断与兼容字段，`MalfContext4` 为执行层主轴）+ 5 类常量，**已完成**
2. `paths.py`：WorkspaceRoots（5 根）+ DatabasePaths（**7 库**）+ `default_settings()` + `tdx_root()` + `tdx_offline_data_root()` + `tushare_token_path()`，**已完成**
3. `calendar.py`：A 股最小交易日历（`is_trading_day` / `next_trading_day`，2024-2027 节假日硬编码），**已完成**
4. `checkpoint.py`：`JsonCheckpointStore` 长任务 checkpoint 存储，**已完成（2026-04-02）**
5. `resumable.py`：6 个续跑 helper（`stable_json_dumps / build_resume_digest / resolve_default_checkpoint_path / prepare_resumable_checkpoint / save_resumable_checkpoint / parse_optional_date`），**已完成（2026-04-02）**

### 1.2 与父系统的主要差异

| 差异点 | 父系统（MarketLifespan） | 本系统（Lifespan-Quant） |
|---|---|---|
| workspace 根数 | 4（repo/data/temp/report） | **5**（+validated_root） |
| 数据库路径数 | 5 | **7**（+structure / filter） |
| 枚举定义位置 | 各模块 contracts 自己定义 | **统一在 core.contracts** |
| 结构位/filter 枚举 | 无（无此模块） | **有**（StructureLevelType/BreakoutType/AdverseConditionType） |
| 配置机制 | pydantic 部分，env var 覆盖 | **纯 env var 注入**，无 pydantic |
| 治理 manifest | run_output_families + table_ownership | 当前不引入，主线跑通后增补 |
| checkpoint store | JsonCheckpointStore | **已引入**（`checkpoint.py` + `resumable.py`，2026-04-02）|

---

## 2. 模块定位

`core` 是**全系统合同基础层**，不参与数据流水线，被所有其他模块依赖。

**五个文件，四类职责**：
```
core/
├── contracts.py    — 枚举、类型、常量（所有跨模块共用的语义定义）
├── paths.py        — 路径合同（工作区根目录 + 数据库路径 + 环境变量解析）
├── calendar.py     — A 股最小交易日历（is_trading_day / next_trading_day）
├── checkpoint.py   — JsonCheckpointStore（长任务 JSON checkpoint 文件管理）
└── resumable.py    — 续跑工具（digest 计算 / 路径推断 / checkpoint 加载校验）
```

`core` 不做任何业务计算，不读写任何数据库，不承载流水线逻辑。它是所有模块对话时共用的"词汇表"与"基础设施工具箱"。

---

## 3. 模块边界

### 3.1 负责

1. **枚举与类型**：跨模块共用的枚举（背景层 / PAS / 结构位 / 交易管理）；其中 `MalfContext4` 是当前 `MALF` 执行层主轴，`MonthlyState8 / WeeklyFlowRelation` 保留为计算层诊断与兼容字段
2. **业务常量**：A 股交易费率、默认资金参数、指数代码、LOT_SIZE
3. **路径合同**：WorkspaceRoots（5 目录）、DatabasePaths（**7 数据库**：raw_market / market_base / malf / structure / filter / research_lab / trade_runtime）
4. **路径解析**：`default_settings()`、`discover_repo_root()`、`tdx_root()`、`tdx_offline_data_root()`、`tushare_token_path()`
5. **PAS 治理状态**：`PAS_TRIGGER_STATUS` 字典（冻结当前每个触发器的治理状态）
6. **交易日历**：`is_trading_day()`、`next_trading_day()`（A 股节假日，2024-2027）
7. **Checkpoint 存储**：`JsonCheckpointStore`（长任务 JSON checkpoint 文件的 load/save/update/clear）
8. **续跑工具**：`build_resume_digest()`、`resolve_default_checkpoint_path()`、`prepare_resumable_checkpoint()`、`save_resumable_checkpoint()`、`parse_optional_date()`、`stable_json_dumps()`

### 3.2 不负责

1. 任何业务计算（属于各业务模块）
2. 读写任何数据库（无 duckdb 依赖）
3. MALF 逻辑、PAS 探测逻辑、仓位计算
4. 运行元数据（_meta_runs，属于 system/trade）
5. 治理 manifest（run_output_families / table_ownership，当前暂不引入）
6. API token 存储（tushare token 只返回路径，不读取内容）

---

## 4. 九模块依赖关系

```
core（基础层，所有模块依赖）
  ↑
data / malf / structure / filter / alpha / position / trade / system
```

**core 自身无上游依赖**，禁止 core 反向 import 任何业务模块。

| 模块 | 从 core 消费的内容 |
|---|---|
| data | DatabasePaths, WorkspaceRoots, default_settings |
| malf | MonthlyState8, WeeklyFlowRelation, MalfContext4, DatabasePaths |
| structure | StructureLevelType, BreakoutType, WorkspaceRoots |
| filter | AdverseConditionType, WorkspaceRoots |
| alpha | PasTriggerPattern, PasTriggerStatus, PAS_TRIGGER_STATUS |
| position | DEFAULT_FIXED_NOTIONAL, DEFAULT_LOT_SIZE, WorkspaceRoots |
| trade | TradeLifecycleState, COMMISSION_RATE, STAMP_DUTY_RATE, DatabasePaths |
| system | WorkspaceRoots, DatabasePaths, default_settings, PAS_TRIGGER_STATUS |

---

## 5. 铁律

1. **core 无依赖**：`core` 的 import 只允许标准库（`os / pathlib / enum / dataclasses`），禁止 import 任何第三方库或业务模块
2. **core 无数据库**：core 不拥有任何 DuckDB 文件，不执行任何 SQL
3. **枚举格式冻结**：已发布的枚举值（字符串）不允许变更，新增值必须向后兼容
4. **常量不硬编码到业务模块**：A股费率、默认资金参数等必须从 `core.contracts` 引用，不允许在业务模块内写死数值
5. **PAS_TRIGGER_STATUS 是治理源头**：所有触发器状态判断必须通过此字典，不允许各模块自己写 `if pattern == "BPB"`
6. **路径不硬编码**：所有数据库路径必须通过 `default_settings().databases` 获取，禁止在业务代码中写死 Path 字符串

---

## 6. 成功标准

1. `contracts.py` 枚举覆盖所有主线跨模块共用类型，无跨模块重复定义
2. `paths.py` 能在 Windows / Linux 环境下均正确解析 5 个工作区根目录
3. `core` 本身可独立 `import`，无需安装任何第三方库
4. 所有模块均通过 `from lq.core.contracts import ...` 引用枚举，无魔法字符串散落
5. `default_settings()` 在 env var 缺失时使用约定目录名（`Lifespan-Quant-data` / `Lifespan-temp` / `Lifespan-Quant-report` / `Lifespan-Quant-Validated`）

---

## 7. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-core-charter-20260401.md`（本文） | 模块章程、血统、边界、铁律 |
| `01-core-contracts-design-20260401.md` | 4 组枚举 + 5 类常量的设计依据与使用规则 |
| `02-core-paths-design-20260401.md` | WorkspaceRoots / DatabasePaths / env var 规范 |
| `03-core-checkpoint-resumable-design-20260402.md` | JsonCheckpointStore + resumable 工具设计与使用规范 |
