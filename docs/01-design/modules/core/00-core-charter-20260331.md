# core 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\core\` | 正式定型 |
| 本系统 | `G:\Lifespan-Quant\src\lq\core\` | 继承父系统核心合同与路径注入机制 |

## 2. 模块定位

`core` 是系统基础设施层。

它负责：
1. 路径与密钥注入（`paths.py`）
2. 全局枚举与跨模块合同（`contracts.py`）
3. 公共工具函数

`core` 是所有其他模块的唯一允许基础依赖，**不依赖任何其他业务模块**。

## 3. 核心枚举（冻结）

以下枚举在 `core/contracts.py` 定义，全局共享：

| 枚举 | 用途 |
|---|---|
| `MonthlyState8` | 月线八态（BULL_FORMING / BULL_PERSISTING / ... / BEAR_REVERSING） |
| `WeeklyFlowRelation` | 周线顺逆（with_flow / against_flow） |
| `SurfaceLabel` | 四张表面标签（BULL_MAINSTREAM / ... / BEAR_COUNTERTREND） |
| `PasTriggerPattern` | PAS 五 trigger（BOF / PB / BPB / TST / CPB） |

这些枚举是三层矩阵主轴的基础语义，所有模块直接从 `core.contracts` 导入，禁止各自定义。

## 4. 路径注入（`paths.py`）

| 变量 | 来源 | 用途 |
|---|---|---|
| `TDX_ROOT` | 环境变量 | 通达信本地目录 |
| `TUSHARE_TOKEN_PATH` | 环境变量 | tushare token 文件（可选） |
| `RAW_MARKET_DB` | `paths.py` 计算 | `raw_market.duckdb` 路径 |
| `MARKET_BASE_DB` | `paths.py` 计算 | `market_base.duckdb` 路径 |
| `MALF_DB` | `paths.py` 计算 | `malf.duckdb` 路径 |
| `RESEARCH_LAB_DB` | `paths.py` 计算 | `research_lab.duckdb` 路径 |
| `TRADE_RUNTIME_DB` | `paths.py` 计算 | `trade_runtime.duckdb` 路径 |

所有数据库文件位于 `G:\Lifespan-data\` 目录下，通过 `paths.py` 统一管理。

## 5. 模块边界

### 5.1 负责

1. 全局枚举定义（MonthlyState8、WeeklyFlowRelation 等）
2. 路径注入与数据库路径计算
3. 跨模块基础 dataclass（合同基类）
4. 公共工具函数（日期处理、格式转换等）

### 5.2 不负责

1. 任何业务逻辑
2. 数据读写
3. 信号计算或触发判断

## 6. 铁律

1. `core` 禁止导入任何其他业务模块（data / malf / alpha 等）。
2. 路径/密钥禁止硬编码，必须通过环境变量注入。
3. 枚举值一旦冻结不允许随意新增，必须更新章程后才能变更。
4. `core` 中不允许出现副作用（如启动时自动连接数据库）。

## 7. 成功标准

1. 所有业务模块能正确从 `core` 导入枚举，无需各自重新定义
2. `paths.py` 能通过环境变量正确解析所有数据库路径
3. `core` 无任何业务模块依赖，`import lq.core` 不触发副作用
