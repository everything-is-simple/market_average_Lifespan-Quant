# MALF 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma` 的 `gene` 模块 | 思想原型，仅参考 |
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\malf\` | 正式定型，完整设计 |
| 本系统 | `G:\Lifespan-Quant\src\lq\malf\` | 继承父系统冻结合同，新增 `structure` 前置层 |

本模块直接继承父系统已验证的三层矩阵主轴合同，不重新发明轮子。  
父系统文档是本模块设计的权威参考。若本文档与父系统冻结文档冲突，以父系统 `13 / 14` 号文档为准。

## 2. 模块定位

`malf` 是市场与个股结构背景引擎。

它负责把月线、周线的价格结构转化为三层矩阵主轴快照，
以 `MalfContext` 合同对象输出给 `filter` 与 `alpha/pas` 消费。

本模块只负责背景计算与输出，**不负责**触发信号、交易决策或仓位管理。

## 3. 三层矩阵主轴（冻结）

| 轴 | 字段 | 正式取值 |
|---|---|---|
| 第一层（月线背景） | `monthly_state` | `BULL_FORMING / BULL_PERSISTING / BULL_EXHAUSTING / BULL_REVERSING / BEAR_FORMING / BEAR_PERSISTING / BEAR_EXHAUSTING / BEAR_REVERSING` |
| 第二层（周线顺逆） | `weekly_flow` | `with_flow / against_flow` |
| 派生（表面标签） | `surface_label` | `BULL_MAINSTREAM / BULL_COUNTERTREND / BEAR_MAINSTREAM / BEAR_COUNTERTREND` |

兼容别名规则：`CONFIRMED_BULL → BULL_PERSISTING`，`CONFIRMED_BEAR → BEAR_PERSISTING`；`MAINSTREAM → with_flow`，`COUNTERTREND → against_flow`。

## 4. 正式输入

1. `market_base.duckdb` 中的 `stock_monthly_adjusted`（后复权月线，`adjust_method='backward'`）
2. `market_base.duckdb` 中的 `stock_weekly_adjusted`（后复权周线）
3. `market_base.duckdb` 中的 `index_monthly` / `index_weekly`
4. `market_base.duckdb` 中的 `trade_calendar`

**不接受** old `gene` 的运行期表作为输入。

## 5. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `MalfContext` | `dataclass`（冻结合同） | 传给 `filter` 和 `alpha/pas`，不落库 |
| `MalfContextSnapshot` | `dataclass` | 批量构建摘要，可落 `malf.duckdb` |
| `MALFBuildManifest` | `dataclass` | 运行元数据，可落 `malf.duckdb` |

`MalfContext` 是本模块对外唯一正式合同。模块间只传此对象，不传内部中间特征。

## 6. 模块边界

### 6.1 负责

1. 月线八态计算（趋势方向 + 阶段）
2. 周线顺逆关系计算（相对月线的顺势 / 逆势）
3. 日线节奏计算（新高日计数、新高间距——立花义正「新高日」思想）
4. 表面标签派生（`surface_label`）
5. `MalfContext` 快照批量构建与更新
6. 宽基指数市场背景池（`MARKET_CONTEXT_ENTITY_CODE`）计算

### 6.2 不负责

1. `market_base` 的拥有与构建（属于 `data` 模块）
2. PAS trigger 探测（属于 `alpha/pas` 模块）
3. 结构位识别（属于 `structure` 模块）
4. 不利条件过滤（属于 `filter` 模块）
5. 交易执行与仓位管理（属于 `trade` / `position` 模块）

## 7. 与父系统的核心差异

| 项目 | 父系统 | 本系统 |
|---|---|---|
| 结构分析 | MALF 内部处理 | 外置到独立 `structure` 模块 |
| PAS trigger | 与 MALF 紧耦合 | `alpha/pas` 独立模块，读 `MalfContext` |
| 波段对象链 | `daily K → pivot → wave → event → surface` 完整保留 | 简化为三层主轴快照，波段对象链为可选实现 |
| 包名 | `mlq.malf` | `lq.malf` |

## 8. 铁律

1. `MalfContext` 是唯一对外合同，禁止其他模块读 MALF 内部中间表。
2. 月线八态取值必须是冻结枚举，不允许自造新值。
3. 兼容别名必须在模块内部转换完毕，对外输出只用正式字段名。
4. `monthly_state` 和 `weekly_flow` 必须通过 `__post_init__` 防御校验。
5. MALF 计算必须以 `market_base` 层作为唯一数据来源，不允许直接读原始日线。

## 9. 成功标准

1. `MalfContext` 合同冻结，字段名与父系统兼容
2. 月线八态能正确识别并区分牛市四阶段与熊市四阶段
3. 周线顺逆能正确计算相对月线的方向关系
4. `surface_label` 四值正确派生
5. 批量构建能在 `market_base.duckdb` 覆盖全市场股票后正常运行
6. `MalfContext` 能被 `filter` 与 `alpha/pas` 消费并通过测试

## 10. 本模块设计文档索引

| 文档 | 内容 | 继承父系统来源 |
|---|---|---|
| `00-malf-charter-20260331.md` | 模块章程（本文） | 父系统 `00` |
| `01-malf-full-cycle-layering-frozen-design-20260331.md` | 全周期分层：月线/周线/日线三层职责边界 | 父系统 `10 / 12` |
| `02-malf-three-layer-matrix-frozen-contract-20260331.md` | MALF 矩阵主轴冻结合同（月线×周线=16格）；pas_trigger 已移出 | 父系统 `13 / 14` |
| `03-malf-monthly-state-8-frozen-definition-20260331.md` | 月线八态定义、判定阈值、五指数体系、已知 Gap | 父系统 `04 / 09 / 11` |
| `04-malf-weekly-flow-relation-frozen-definition-20260331.md` | 周线顺逆定义、判定规则、兼容别名 | 父系统 `12 / 13` |
| `05-malf-pipeline-and-contracts-frozen-design-20260331.md` | Pipeline 流程、数据库 Schema、MalfContext 合同 | 父系统 `14` |
| `06-malf-daily-rhythm-new-high-counting-design-20260401.md` | 日线节奏设计：新高日识别、计数、间距（立花义正思想） | 本系统新增 |

## 11. 代码出入修复记录（2026-03-31 / 2026-04-01）

本轮整理中发现并修复的代码出入点：

| 文件 | 问题 | 修复 |
|---|---|---|
| `src/lq/malf/pipeline.py` | `monthly_bar` / `weekly_bar` 表名不存在 | 改为 `stock_monthly_adjusted` / `stock_weekly_adjusted` |
| `src/lq/malf/pipeline.py` | `month_start` / `week_start` 列名与 bootstrap schema 不一致 | 使用 `month_start_date AS month_start` 等别名 |
| `src/lq/malf/pipeline.py` | 无 `adjust_method` 过滤条件 | 补 `AND adjust_method = 'backward'` |

以下已知 Gap 待后续执行卡处理（见文档 `03`）：
- `monthly.py` 的 `classify_monthly_state()` 缺少 `BEAR_REVERSING` 显式返回路径
