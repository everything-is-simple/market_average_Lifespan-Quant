# position 模块 — Partial-Exit 合同设计 / 2026-04-01

## 1. 设计目标

本文定义 `position` 模块的退出合同结构，包括：

1. Position 状态机与生命周期
2. ID 规则（position_id / exit_plan_id / exit_leg_id）
3. v1 partial-exit 契约（多腿退出）
4. 退出控制策略家族
5. 研究表 schema（`position_exit_plan` / `position_exit_leg`）

本文不回答：
- 哪个 partial-exit 策略最优
- 何时把 partial-exit 升级为主线默认
- 是否对 stop-loss 路径做任何 partial 处理

---

## 2. 退出类型分类

所有退出路径固定分为两类，不允许混合：

### 2.1 硬全平路径（Hard Full Exit）

以下触发条件永远执行整仓清空，**不进 partial-exit 路径**：

| 触发条件 | 动作 | 说明 |
|---|---|---|
| `STOP_LOSS` | 立即全平 | 价格跌破 `initial_stop_price` |
| `FORCE_CLOSE` | 立即全平 | 持仓超时（`time_stop_days`）或回测末日强平 |

铁律：`STOP_LOSS / FORCE_CLOSE` 的执行语义不因任何 partial-exit 策略改变。

### 2.2 非紧急退出路径（Normal Exit，可 partial）

以下触发条件允许使用多腿结构：

| 触发条件 | 允许操作 |
|---|---|
| `TRAILING_STOP` | 可分腿（第一腿止盈 + runner 跟踪止损） |
| `FIRST_TARGET` | 第一腿止盈（partial exit = True） |

---

## 3. Position 状态机

```
                    ┌─────────────────┐
                    │                 │
   BUY FILLED ────> │      OPEN       │
                    │                 │
                    └───────┬─────────┘
                            │
              ┌─────────────┼──────────────────┐
              │             │                  │
              ▼             ▼                  ▼
   STOP_LOSS /       非紧急退出路径        非紧急退出路径
   FORCE_CLOSE       (partial < total)    (全仓最终清仓)
              │             │                  │
              ▼             ▼                  ▼
    FULL_EXIT_        PARTIAL_EXIT_      FULL_EXIT_
    PENDING           PENDING            PENDING
              │             │                  │
              │     腿成交且有剩余              │
              │             │                  │
              │             ▼                  │
              │        OPEN_REDUCED            │
              │             │                  │
              │      最终清仓腿创建             │
              │             │                  │
              │             ▼                  │
              └──> FULL_EXIT_PENDING <─────────┘
                            │
                     最终腿成交
                            │
                            ▼
                         CLOSED
```

### 3.1 状态迁移规则

| 当前状态 | 触发事件 | 目标状态 |
|---|---|---|
| `OPEN` | BUY FILLED | `OPEN` |
| `OPEN` | STOP_LOSS / FORCE_CLOSE | `FULL_EXIT_PENDING` |
| `OPEN` | 非紧急退出腿创建（qty < remaining） | `PARTIAL_EXIT_PENDING` |
| `OPEN` / `OPEN_REDUCED` | 最终清仓腿创建 | `FULL_EXIT_PENDING` |
| `PARTIAL_EXIT_PENDING` | 腿成交且 remaining > 0 | `OPEN_REDUCED` |
| `PARTIAL_EXIT_PENDING` | 腿 REJECTED / EXPIRED | `OPEN` / `OPEN_REDUCED` |
| `FULL_EXIT_PENDING` | 最终腿成交 | `CLOSED` |
| `FULL_EXIT_PENDING` | 腿 REJECTED / EXPIRED | `OPEN` / `OPEN_REDUCED` |

---

## 4. ID 规则

### 4.1 三层 ID 体系

```
position_id   = BUY 订单的 order_id（稳定身份，跨腿可追溯）
exit_plan_id  = f"exitplan-{signal_id[:8]}-{utc_suffix}"（同一 position 的退出计划身份）
exit_leg_id   = f"{exit_plan_id}-leg{leg_seq}"（单腿唯一标识）
```

### 4.2 ID 不变性约束

- `position_id` 在整个 position 生命周期内不变
- `exit_plan_id` 在同一退出计划内不变（允许多腿）
- `exit_leg_id` 全局唯一，不允许复用

---

## 5. v1 Partial-Exit 契约

### 5.1 核心约定

```
v1 partial-exit = 多张 SELL 订单
每张 SELL   = 一个明确的 exit leg
每张 SELL   = 单腿单次撮合（不引入"单张订单内部 partial fill"语义）
```

### 5.2 同一时刻约束

```
同一只股票 / 同一个 position，任意时刻最多只有一张 PENDING SELL 订单
```

### 5.3 A 股整手约束（分腿版）

```
# 第一腿止盈（half lot）
half_shares = floor(total_shares / 2 / lot_size) * lot_size
runner_shares = total_shares - half_shares

# 若 half_shares < lot_size（不满一手），退化为全平
if half_shares < lot_size:
    fallback_to_full_exit = True
    half_shares = total_shares
    runner_shares = 0
```

---

## 6. 退出控制策略家族

### 6.1 FULL_EXIT_CONTROL（当前 operating 基线退出）

```
结构：单腿
腿1 (FULL_EXIT):  TRAILING_STOP 或 STOP_LOSS 或 FORCE_CLOSE 触发，全平
```

这是当前 `trade` 模块主线的默认退出语义，也是 partial-exit 研究的 control 对照组。

### 6.2 NAIVE_TRAIL_SCALE_OUT_50_50_CONTROL（50/50 朴素跟踪分批退出）

**继承父系统（MarketLifespan-Quant）设计**：

```
结构：两腿
腿1 (TRAILING_SCALE_OUT): 第一次 TRAILING_STOP 触发，卖出 50% remaining_quantity
腿2 (TRAILING_CLEANUP):   第二次 TRAILING_STOP 或 FORCE_CLOSE，卖出全部剩余
```

约束：
- `STOP_LOSS` 仍为硬全平，不走此路径
- 若 50% 分腿因 A 股整手约束不成立，退化为全平（`fallback_to_full_exit = True`）

### 6.3 FIRST_TARGET_TRAIL_CONTROL（1R 止盈 + runner，当前 lq 默认）

**本系统（Lifespan-Quant）当前实现**（继承 `sizing.py`）：

```
结构：两腿
腿1 (first_target): entry_price + 1R 触发，卖出 half_lot（50% A股整手约束）
腿2 (runner):       剩余仓位跟踪止损，从持仓最高点回撤 trailing_pct 触发
```

参数：`trailing_pct = 0.08`（8% 回撤触发）

**与 50/50 的区别**：
- 第一腿触发条件是价格绝对目标（1R），不是跟踪止损百分比
- 更适合短期趋势交易（BOF 信号特性）

### 6.4 TRAIL_SCALE_OUT_25_75_CONTROL（爷爷系统 provisional leader）

```
结构：两腿
腿1: 第一次 TRAILING_STOP 触发，卖出 25% remaining_quantity
腿2: 最终清仓（75% 剩余）
```

**爷爷系统历史结论**：在 EQ-gamma positioning S2 实验中为 provisional leader，尚未在本系统正式验证。

---

## 7. 研究表 Schema

### 7.1 position_exit_plan

```sql
CREATE TABLE IF NOT EXISTS position_exit_plan (
    run_id                  VARCHAR NOT NULL,
    signal_id               VARCHAR NOT NULL,
    code                    VARCHAR NOT NULL,
    signal_date             DATE NOT NULL,
    signal_side             VARCHAR NOT NULL,
    pas_pattern             VARCHAR NOT NULL,
    policy_name             VARCHAR NOT NULL,      -- exit policy 名称
    sizing_policy_name      VARCHAR NOT NULL,      -- 对应的 sizing policy
    baseline_role           VARCHAR NOT NULL,      -- OPERATING_CONTROL / FLOOR_SANITY
    position_template_id    VARCHAR NOT NULL,      -- 与 sizing_snapshot 关联的模板 ID
    exit_plan_id            VARCHAR NOT NULL,      -- 稳定退出计划 ID
    entry_timing            VARCHAR NOT NULL,      -- T_PLUS_1_OPEN
    planned_entry_date      DATE,
    planned_entry_price     DOUBLE,
    planned_entry_shares    BIGINT,
    planned_entry_notional  DOUBLE,
    exit_leg_count          INTEGER NOT NULL,      -- 本计划腿数（1=全平，2=分腿）
    contract_status         VARCHAR NOT NULL,      -- CONTRACTED
    fallback_to_full_exit   BOOLEAN NOT NULL DEFAULT FALSE,
    plan_payload_json       VARCHAR,
    created_at              TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (run_id, signal_id)
)
```

### 7.2 position_exit_leg

```sql
CREATE TABLE IF NOT EXISTS position_exit_leg (
    run_id                  VARCHAR NOT NULL,
    signal_id               VARCHAR NOT NULL,
    code                    VARCHAR NOT NULL,
    exit_plan_id            VARCHAR NOT NULL,
    leg_id                  VARCHAR NOT NULL,      -- 全局唯一腿 ID
    exit_leg_seq            INTEGER NOT NULL,      -- 腿序号（从 1 开始）
    exit_leg_count          INTEGER NOT NULL,      -- 本计划总腿数
    leg_role                VARCHAR NOT NULL,      -- FULL_EXIT / TRAILING_SCALE_OUT / TRAILING_CLEANUP
    trigger_guard           VARCHAR NOT NULL,      -- TRAILING_STOP / TRAILING_STOP_FIRST / etc.
    decision_type           VARCHAR NOT NULL,      -- STOP_LOSS / TRAILING_STOP / FORCE_CLOSE
    exit_reason_code        VARCHAR NOT NULL,      -- 人读退出原因码
    is_partial_exit         BOOLEAN NOT NULL DEFAULT FALSE,
    planned_exit_ratio      DOUBLE,               -- 计划退出比例（0.5 = 半仓）
    planned_exit_shares     BIGINT,               -- 计划退出股数
    remaining_qty_before    BIGINT,               -- 本腿执行前剩余股数
    target_qty_after        BIGINT,               -- 本腿执行后预期剩余
    fallback_to_full_exit   BOOLEAN NOT NULL DEFAULT FALSE,
    leg_payload_json        VARCHAR,
    created_at              TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (run_id, signal_id, leg_id)
)
```

---

## 8. 退出腿角色与触发守卫映射

| leg_role | trigger_guard | decision_type | is_partial_exit | 说明 |
|---|---|---|---|---|
| `FULL_EXIT` | `TRAILING_STOP` | `TRAILING_STOP` | False | 单腿全平（FULL_EXIT_CONTROL） |
| `FULL_EXIT` | `TRAILING_STOP` | `STOP_LOSS` | False | 止损硬全平 |
| `FULL_EXIT` | `TRAILING_STOP` | `FORCE_CLOSE` | False | 强平全平 |
| `TRAILING_SCALE_OUT` | `TRAILING_STOP_FIRST` | `TRAILING_STOP` | True | 分腿第一腿（部分减仓） |
| `TRAILING_CLEANUP` | `TRAILING_STOP_SECOND_OR_FORCE_CLOSE` | `TRAILING_STOP_OR_FORCE_CLOSE` | False | 分腿最终清仓腿 |

---

## 9. 当前实现状态与优先级

| 组件 | 状态 | 说明 |
|---|---|---|
| `PositionPlan` / `ExitLeg` / `PositionExitPlan` 合同 | ✅ 已实现 | `src/lq/position/contracts.py` |
| `FIRST_TARGET_TRAIL_CONTROL` 两腿计算 | ✅ 已实现 | `src/lq/position/sizing.py` |
| `position_exit_plan / position_exit_leg` 表 bootstrap | ⬜ 待实现 | 需继承父系统 bootstrap.py |
| `position_run / position_sizing_snapshot` 表 bootstrap | ⬜ 待实现 | 需继承父系统 bootstrap.py |
| `FIXED_NOTIONAL_CONTROL` pipeline 批量运行 | ⬜ 待实现 | 参考父系统 baseline.py / pipeline.py |
| `NAIVE_TRAIL_SCALE_OUT_50_50_CONTROL` | ⬜ 待验证 | S2 赛道，S1 完成前不开 |
| S1 sizing 家族 formal replay | ⬜ 待开卡 | 研究赛道，非当前 P1 债务 |

---

## 10. 禁止操作

1. 把 `STOP_LOSS` 偷渡成 partial-exit 路径
2. 在 S1 sizing 赛道完成前混入 partial-exit 比较
3. 不补 `position_id` 就开始 partial-exit 实现
4. 让上游 `alpha/pas` 直接产生 SELL 信号
5. 用 sizing residual watch 作为 partial-exit 隐含 baseline
