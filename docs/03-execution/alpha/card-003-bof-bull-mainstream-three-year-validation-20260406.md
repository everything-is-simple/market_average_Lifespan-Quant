# CARD-003 BOF 在 BULL_MAINSTREAM 格的独立三年验证 / 2026-04-06

## 目标

独立验证 BOF trigger 在 BULL_MAINSTREAM 表面标签下的三年期（2020-2022）表现，确认：
1. 信号检出率、胜率、R 倍数分布与 v0.01 量级一致
2. BOF 作为 MAINLINE 策略的定位成立

## 前置条件

- [ ] card-011 完成：`malf.duckdb` 已填充（`surface_label` 可读）
- [ ] card-012 完成：`structure.duckdb` 已填充
- [ ] card-013 完成：`filter.duckdb` 已填充
- [ ] card-014 完成：`research_lab.duckdb` 已填充（BOF 信号可读）
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充（BOF 交易记录可读）

## 执行步骤

1. 从 `research_lab` 筛选 2020-2022 年 `pattern=BOF AND surface_label=BULL_MAINSTREAM` 的全部信号
2. 从 `trade_runtime` 匹配对应交易记录
3. 统计：
   - 信号总数、入场率（有 position_plan 的比例）
   - 胜率（`r_multiple > 0` 的比例）
   - 平均 R 倍数、中位 R 倍数
   - 最大连败次数
   - 净收益（R 倍数 × 单位风险金额累加）
4. 与 v0.01 同期 BOF 保留段对比（v0.01 BOF 保留段胜率 56.5%，净收益 511 万）
5. 按年度拆分（2020/2021/2022），确认无单年度巨亏

## 验收标准

1. 胜率 ≥ 50%（v0.01 保留段 56.5%）
2. 平均 R 倍数 > 0
3. 各年度净收益均为正或亏损可控（单年度最大亏损 < 年均收益的 50%）
4. 与 v0.01 同期差异可解释（参数差异、结构位语义差异等）

## 产出物

- evidence（统计数据表 + 年度拆分图）
- record + conclusion
