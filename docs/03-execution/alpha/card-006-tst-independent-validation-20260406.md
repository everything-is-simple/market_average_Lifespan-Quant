# CARD-006 TST 独立正式验证卡 / 2026-04-06

## 目标

独立验证 TST（Test of Supply/Demand）trigger 的表现，确认其 CONDITIONAL 策略定位：
1. 2020-2023 年全量信号统计
2. 确认 TST 在 2020 年后持续正收益（v0.01 结论：保留段 108 万）
3. 确定 TST 的最优表面标签组合

## 前置条件

- [ ] card-014 完成：`research_lab.duckdb` 已填充（TST 信号可读）
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充

## 执行步骤

1. 从 `research_lab` 筛选 `pattern=TST` 的全部信号
2. 从 `trade_runtime` 匹配交易记录
3. 全量统计：信号总数、胜率、平均 R 倍数、净收益
4. 按表面标签（16 格）拆分，找出 TST 最强的格子
5. 按年度拆分（2020/2021/2022/2023），确认"2020 后持续正收益"
6. 与 v0.01 TST 保留段对比（保留段 108 万）

## 验收标准

1. 2020 年后每年净收益 ≥ 0
2. 至少 2 个表面标签格子的 TST 有独立正收益
3. 整体胜率 ≥ 45%
4. 与 v0.01 差异可解释

## 产出物

- evidence（年度统计表 + 16 格拆分表）
- record + conclusion
