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
3. 表面标签派生（`surface_label`）
4. `MalfContext` 快照批量构建与更新
5. 宽基指数市场背景池（`MARKET_CONTEXT_ENTITY_CODE`）计算

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
