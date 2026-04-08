# 015. 复权因子单测补全 证据

## 对应关系

1. 对应卡：`docs/03-execution/015-unit-test-adjust-factor-card-20260406.md`
2. 对应记录：`docs/03-execution/records/015-unit-test-adjust-factor-record-20260408.md`
3. 对应结论：`docs/03-execution/015-unit-test-adjust-factor-conclusion-20260408.md`

## 文档证据

1. 已将 `015` 卡纠偏为当前系统口径的复权因子单测补全卡。
2. 已在卡内明确：本卡只补最小必要单测，不改 data 主线来源路线。
3. 已在卡内明确：测试必须使用固定输入数据，不依赖正式数据库与网络。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖待测函数、固定输入样例与 pytest 运行结果。
2. 本卡关注的是复权因子关键路径的最小稳定保护，而非完整测试体系扩建。
3. 本卡与 `014` 形成上下游关系：`014` 发现抽样异常时，应能借由 `015` 的单测快速定位根因。

## 与当前 data spec 对齐的正式锚点

1. 当前正式补测入口已收敛为 `src/lq/data/compute/adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()`。
2. 当前仓库中未确认现成的 `adjust_factor` 单测文件，因此真实执行的第一步是新建 `tests/unit/data/` 下的测试文件。
3. 因此，本卡的 evidence 不应写成“补跑已有测试”，而应写成“创建测试文件 + 执行 pytest + 记录覆盖场景”。

## 待执行证据

本轮已生成并确认：

1. 新增测试文件：`tests/unit/data/test_adjust_factor.py`。
2. 新增 5 个最小关键路径用例：
   - 无除权事件 → 因子全为 `1.0`
   - 单一分红事件 → 因子计算正确
   - 单一复合事件（分红 + 配股 + 送转）→ 因子计算正确
   - 多事件累乘 → 历史日因子按事件链累积，最新日为 `1.0`
   - `apply_backward_adjustment()` → 停牌过滤、生效 `adjustment_factor` 与 OHLC 调整正确
3. pytest 命令与结果：`python -m pytest tests/unit/data/test_adjust_factor.py -q` → `5 passed in 2.17s`

## 当前结论性证据

1. 本轮已经完成 `015` 的真实最小补测，而不再只是卡面准备。
2. 当前可以确认的结论是：`compute_backward_factors()` 与 `apply_backward_adjustment()` 已具备最小关键路径单测保护。

## 真实执行模板（基于已确认入口）

1. 目标函数已确认位于 `src/lq/data/compute/adjust.py`：`compute_backward_factors()` 与 `apply_backward_adjustment()`。
2. 当前仓库中先前**未发现现成的 `adjust_factor` 单测文件**，因此本轮真实执行已先创建新的测试文件。
3. 按当前测试目录规范，优先落点应为 `tests/unit/data/` 下的新测试文件，并围绕以下最小路径建例：
   - 无除权事件 → 因子全为 `1.0`
   - 单一分红 / 配股 / 送转事件 → 因子计算正确
   - 多事件累乘 → 最新日为 `1.0`，历史日因子按事件链累积
   - `apply_backward_adjustment()` 能正确写出 `adjustment_factor` 并同步调整 OHLC
4. 真实 evidence 已包含三部分：新增测试文件清单、pytest 运行结果、覆盖场景说明。
5. 本卡现已满足创建 conclusion 的事实基础。
