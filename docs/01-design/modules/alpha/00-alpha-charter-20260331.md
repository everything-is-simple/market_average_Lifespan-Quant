# alpha / PAS 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma` 的 `normandy` 模块（PAS 五形态原型） | 思想原型，仅参考 |
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\alpha\` | 正式定型，完整设计 |
| 本系统 | `G:\Lifespan-Quant\src\lq\alpha\` | 继承父系统 PAS 五 trigger，新增 `structure` 前置层与第一 PB 追踪 |

## 2. 模块定位

`alpha` 是研究信号模块。
它负责把通过过滤器的候选股票与冻结后的 MALF 背景，转化为可验证、可审计的 PAS 触发信号。

当前正式范围：

1. `selector`（最小候选集筛选）
2. `PAS`（五 trigger 探测，当前主线只用 BOF + PB）
3. `IRS-minimal`（行业分桶约束，避免组合过度集中）

## 3. PAS 五 Trigger 状态（冻结）

| Trigger | 状态 | 说明 |
|---|---|---|
| `BOF` | **主线启用** | 突破失败（Break of Failure），三年验证通过 |
| `PB` | **主线启用** | 拉回入场（Pullback），三年验证通过 |
| `BPB` | **主线拒绝** | 突破后拉回，三年验证未通过，代码保留但 system 层不启用 |
| `TST` | 待独立验证 | 测试支撑/阻力，代码存在标记 PENDING |
| `CPB` | 待独立验证 | 复合拉回，代码存在标记 PENDING |

**BPB 禁止进入主线**，只作历史记录。TST / CPB 待独立三年窗口验证后才可启用。

## 4. 正式输入

1. 日线 `DataFrame`（来自 `market_base.duckdb`，已通过 `filter` 模块的不利条件检查）
2. `MalfContext`（来自 `malf` 模块，三层主轴快照）
3. `StructureSnapshot`（来自 `structure` 模块，结构位识别结果）

**必须先经过 `filter` 模块的不利条件过滤，才能进入 trigger 探测。**

## 5. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `PasSignal` | `dataclass`（冻结合同） | 落入 `research_lab.duckdb`（L3） |

`PasSignal` 是本模块对外唯一正式合同。包含信号日期、trigger 类型、MALF 表面标签、第一 PB 序号等。

## 6. 与父系统的核心差异

| 项目 | 父系统 | 本系统 |
|---|---|---|
| 前置过滤 | 月线背景过滤（局部） | 独立 `filter` 模块（五类不利条件） |
| 结构位 | trigger 内部隐含 | 独立 `structure` 模块，统一 `BreakoutEvent` 合同 |
| 第一 PB 追踪 | 未实现 | `pb_sequence_number` 字段，区分初次 / 二次入场 |
| 突破语义 | 各 trigger 自定义 | `BreakoutType` 枚举统一分类 |
| 包名 | `mlq.alpha` | `lq.alpha.pas` |

## 7. 模块边界

### 7.1 负责

1. 候选集初步筛选（selector）
2. PAS 五 trigger 探测与状态机
3. 第一 PB 序号追踪
4. 研究 trace、signal registry 与 run 元数据
5. IRS 行业分桶约束（最小化）

### 7.2 不负责

1. `market_base` 的拥有与构建（属于 `data`）
2. MALF 三层矩阵计算（属于 `malf`）
3. 结构位识别（属于 `structure`）
4. 不利条件过滤（属于 `filter`）
5. 仓位规划与退出（属于 `position`）
6. 直接写 `trade_runtime`（必须经过 `position` 桥接）

## 8. 铁律

1. 任何 trigger 探测必须在通过 `filter` 之后，不允许绕过过滤器。
2. `BPB` 禁止在 `system` 层启用，无论测试结果如何。
3. `PasSignal` 的 `signal_id` 必须全局唯一（格式：`PAS_{version}_{code}_{date}_{pattern}`）。
4. `alpha` 不直接写 `trade_runtime`；研究结果只能经冻结桥接后才进入正式交易。
5. `TST` / `CPB` 启用前必须有独立三年窗口验证证据。

## 9. 成功标准

1. `BOF` 和 `PB` trigger 在三年历史窗口的信号质量测试通过
2. `PasSignal` 合同冻结，含 `pb_sequence_number` 字段
3. `filter` 前置通过后的股票才触发 trigger 探测
4. IRS 行业分桶约束能防止组合过度集中单一行业
5. 研究结果可追溯到具体 run、窗口、参数和证据
