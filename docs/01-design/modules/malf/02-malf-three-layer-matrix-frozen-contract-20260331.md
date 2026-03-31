# MALF 三层矩阵主轴冻结合同 / 2026-03-31

> 继承来源：父系统 `13-malf-three-layer-matrix-modeling-charter-20260327.md` +
> `14-malf-matrix-axis-contract-implementation-20260327.md`
> 本文是当前系统最终定型口径，不允许在未另开执行卡的前提下修改主轴字段名或取值。

## 1. 三层主轴（冻结）

```
monthly_state_8  ×  weekly_flow_relation_to_monthly  ×  pas_trigger
      ↓                         ↓                           ↓
   主状态轴                  关系轴                        执行轴
（月线长期背景）          （周线顺逆关系）             （PAS 触发类型）
```

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

### 1.3 执行轴（第三层）

字段名：`pas_trigger`

只回答：**具体发生的是哪一种 PAS 触发？**

| 值 | 当前状态 |
|---|---|
| `BOF` | ✅ 主线，已验证 |
| `PB` | ✅ 主线，已验证 |
| `TST` | 🔲 待独立验证 |
| `CPB` | 🔲 待独立验证 |
| `BPB` | ❌ 已拒绝主线 |

执行轴由 `alpha/pas` 模块输出，不由 `malf` 模块计算。

## 2. 主矩阵

```
当前主矩阵 = monthly_state_8 × weekly_flow_relation_to_monthly
= 8 × 2 = 16 格
```

16 格示例：
- `BULL_PERSISTING + with_flow` — 长期牛市持续，周线当前也是顺势推进
- `BULL_PERSISTING + against_flow` — 长期牛市持续，但周线当前是牛市里的逆势回调
- `BEAR_PERSISTING + with_flow` — 长期熊市持续，周线当前顺势下行
- `BEAR_PERSISTING + against_flow` — 长期熊市持续，周线当前是熊市里的反弹

加上执行轴后：`16 × 触发器数 = N 格总结论`（当前 BOF/PB 主线已验证 16 格）

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

正式解释顺序固定为：

1. 先看 `monthly_state_8`
2. 再看 `weekly_flow_relation_to_monthly`
3. 最后看 `pas_trigger`

观察字段（`surface_label / wave_role / scene_id` 等）只能放在附加列或附录，不能替代上述三轴作为解释入口。

## 6. 与父系统 BOF 16 格验证的关系

父系统已完成 BOF 在 16 格 (`monthly_state_8 × weekly_flow_relation`) 中的正式验证。  
新系统继承此验证结论，无需重跑。  
下一步 PB 的 16 格验证，当条件具备时另开执行卡推进。

## 7. 铁律

1. 主轴字段名冻结，不允许单方面修改或新造轴名。
2. 每个新 PAS 触发器进入主线前，必须先独立完成 `monthly_state_8 × weekly_flow` 16 格验证。
3. 主矩阵解释不允许跳过 16 格验证直接发布"80 格总结论"。
