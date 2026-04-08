# 012. CPB 语义收敛 + 独立正式验证 证据（历史追溯态）

## 对应关系

1. 对应卡：`docs/03-execution/012-cpb-semantic-convergence-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/012-cpb-semantic-convergence-validation-record-20260408.md`

## 文档证据

1. 已将 `012` 卡纠偏为历史追溯页，而非当前待执行验证卡。
2. 已在卡内明确：当前正式口径仍是 `CPB = REJECTED`。
3. 已在卡内明确：`system` 层不应调用 `CPB` 作为正式策略路径。
4. 已补入追溯文件段，明确 evidence / record 路径，以及独立历史 conclusion 的后续约定。

## 历史处理证据

1. 本卡当前要保存的是“为什么 `CPB` 被拒绝、在哪些条件下未来才有资格重开”。
2. 本卡当前不要求启用 `CPB` detector，不要求生成新的正式交易统计。
3. 若未来重开，必须先回到 design / spec 层重新立项，而不能直接沿用旧执行卡继续推进。

## 当前结论性证据

1. 本轮完成的是历史追溯页重写与闭环准备，不是 `CPB` 的重新验证。
2. 当前可以确认的结论是：`012` 已被稳定收口为历史追溯页，且正式口径仍为 `REJECTED`。
