# MALF 矩阵主轴冻结合同（月线 × 周线 = 16 格）/ 2026-03-31

> 继承来源：父系统 `13-malf-three-layer-matrix-modeling-charter-20260327.md` +
> `14-malf-matrix-axis-contract-implementation-20260327.md`
> 本文是当前系统最终定型口径，不允许在未另开执行卡的前提下修改主轴字段名或取值。
>
> **2026-04-01 修订说明**：PAS 五形态原则上不是 MALF 内容。
> 原"执行轴（第三层）pas_trigger"已从本文移除。
> 80 格地图（`monthly_state_8 × weekly_flow × pas_trigger`）属于 `alpha/pas` 模块研究层，不在 MALF 矩阵合同范围内。

## 1. MALF 矩阵主轴（冻结）

```
monthly_state_8  ×  weekly_flow_relation_to_monthly
      ↓                         ↓
   主状态轴                  关系轴
（月线长期背景）          （周线顺逆关系）
```

MALF 矩阵 = 8 × 2 = **16 格**，这是 MALF 模块输出的全部矩阵内容。

### 1.1 主状态轴（第一层）

字段名：`monthly_state_8`（代码中用 `monthly_state`）

只回答：**这只股票现在处在什么长期背景状态里？**

| 值 | 含义 |
|---|---|
| `BULL_FORMING` | 牛市形成中 |
| `BULL_PERSISTING` | 牛市持续中 |
| `BULL_EXHAUSTING` | 牛市衰竭中 |
| `BULL_REVERSING` | 牛市反转中 |
| `BEAR_FORMING` | 熊市形成中 |
| `BEAR_PERSISTING` | 熊市持续中 |
| `BEAR_EXHAUSTING` | 熊市衰竭中 |
| `BEAR_REVERSING` | 熊市反转中 |

兼容别名（只允许在模块内部转换，对外只输出正式值）：
- `CONFIRMED_BULL` → `BULL_PERSISTING`
- `CONFIRMED_BEAR` → `BEAR_PERSISTING`

### 1.2 关系轴（第二层）

字段名：`weekly_flow_relation_to_monthly`（代码中用 `weekly_flow`）

只回答：**当前周线这段，相对月线长期背景，是顺着走还是逆着走？**

| 值 | 含义 |
|---|---|
| `with_flow` | 顺流（周线方向与月线长期背景一致） |
| `against_flow` | 逆流（周线方向与月线长期背景相反） |

兼容别名（只允许在模块内部转换，对外只输出正式值）：
- `MAINSTREAM` → `with_flow`
- `COUNTERTREND` → `against_flow`

## 2. MALF 主矩阵（16 格）

16 格 = `monthly_state_8 × weekly_flow_relation_to_monthly`，这是 MALF 输出的完整矩阵。

代表性格子示例：
- `BULL_PERSISTING + with_flow` — 长期牛市持续，周线当前顺势推进
- `BULL_PERSISTING + against_flow` — 长期牛市持续，周线当前是牛市内逆势回调
- `BEAR_PERSISTING + with_flow` — 长期熊市持续，周线当前顺势下行
- `BEAR_PERSISTING + against_flow` — 长期熊市持续，周线当前是熊市内逆势反弹

**关于 80 格地图的边界声明**：

`alpha/pas` 模块在研究层使用 `monthly_state_8 × weekly_flow × pas_trigger` = 80 格地图，
这是 `alpha/pas` 自己的研究矩阵，消费 MALF 的 16 格作为背景输入。
**80 格地图属于 `alpha/pas`，不属于 MALF 矩阵合同。**

## 3. 派生字段（观察字段，不是主轴）

`surface_label` 是派生字段，由主状态轴 + 关系轴组合推导：

| `monthly_state_8` | `weekly_flow` | `surface_label` |
|---|---|---|
| `BULL_*` | `with_flow` | `BULL_MAINSTREAM` |
| `BULL_*` | `against_flow` | `BULL_COUNTERTREND` |
| `BEAR_*` | `with_flow` | `BEAR_MAINSTREAM` |
| `BEAR_*` | `against_flow` | `BEAR_COUNTERTREND` |

**`surface_label` 只能作为兼容字段或观察字段，不能替代主轴。**

以下字段继续保留为观察/审计/兼容字段，不得冒充主矩阵主轴：
- `background_label`
- `background_state`
- `wave_role`（历史别名，等价于 `weekly_flow`）
- `scene_id`
- `quartile`

## 4. MalfContext 合同字段映射

| 文档字段名 | 代码字段名 | 说明 |
|---|---|---|
| `monthly_state_8` | `monthly_state` | 主状态轴，枚举值 |
| `weekly_flow_relation_to_monthly` | `weekly_flow` | 关系轴，`with_flow/against_flow` |
| `surface_label` | `surface_label` | 派生观察字段 |
| `monthly_strength` | `monthly_strength` | 月线强度 0~1，可选 |
| `weekly_strength` | `weekly_strength` | 周线强度 0~1，可选 |

代码字段名略短，是文档字段名的合法缩写，两者等价，不存在口径冲突。

## 5. 报表解释入口（冻结）

MALF 矩阵正式解释顺序：

1. 先看 `monthly_state_8`（月线长期背景在哪个阶段）
2. 再看 `weekly_flow_relation_to_monthly`（周线当前顺流还是逆流）

观察字段（`surface_label / wave_role / scene_id` 等）只能放在附加列或附录，
不能替代两轴作为解释入口。

**注**：若需进一步看触发器，应查 `alpha/pas` 模块的 80 格地图输出，不在 MALF 报表层面。

## 6. 与父系统验证结论的继承关系

父系统已完成 BOF 和 PB 在 `monthly_state_8 × weekly_flow` 16 格中的正式验证，结论摘要：

| 触发器 | 地位 | 有效格 |
|---|---|---|
| `BOF` | core / primary_trend_driver | persisting 四格为主力 |
| `PB` | conditional / conditional_assist_driver | `BULL_PERSISTING__MAINSTREAM` 和 `BEAR_PERSISTING__COUNTERTREND` |
| `BPB` | excluded / not_for_long_alpha | — |

新系统继承此验证结论。上述内容由 `alpha/pas` 模块消费，MALF 仅提供 16 格背景输入。

## 7. 铁律

1. MALF 主轴字段名冻结（`monthly_state` + `weekly_flow`），不允许单方面新造轴名。
2. `pas_trigger` 不是 MALF 矩阵轴，MALF 对外合同中不含 `pas_trigger` 字段。
3. `alpha/pas` 消费 `MalfContext`（16 格背景），自行维护 80 格地图，不得反向要求 MALF 输出触发器。
4. 观察字段不得冒充主轴。
