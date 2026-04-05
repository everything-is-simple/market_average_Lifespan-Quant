# CARD-005 filter 不利条件过滤器效果评估 / 2026-04-06

## 目标

评估 filter 模块五类不利条件过滤器对主线信号质量的净效果：
1. 各类不利条件的触发频率
2. 被过滤掉的信号是否确实是低质量信号
3. 整体过滤器对胜率和净收益的提升

## 前置条件

- [ ] card-013 完成：`filter.duckdb` 已填充
- [ ] card-014 完成：`research_lab.duckdb` 已填充
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充

## 执行步骤

1. 从 `filter.duckdb` 统计五类不利条件（`compression_no_direction`、`structural_chaos`、`insufficient_space`、`background_not_supporting`、`volume_anomaly`）的触发频率
2. 分三组对比：
   - A 组（通过过滤）：`tradeable=True` 的日期×股票 → 对应的 BOF/TST 信号 → 交易结果
   - B 组（被过滤）：`tradeable=False` 的日期×股票 → 假设仍入场 → 模拟交易结果
   - C 组（无过滤基线）：全部信号 → 交易结果
3. 各组统计：胜率、平均 R 倍数、净收益
4. 逐类评估：单独关闭每一类过滤器后的信号质量变化

## 验收标准

1. A 组胜率 > C 组胜率（过滤有正效果）
2. B 组胜率 < C 组胜率（被过滤的确实更差）
3. 五类条件中至少 3 类有独立正向贡献
4. 若某类条件无贡献或负贡献，记录并建议移除或调参

## 产出物

- evidence（五类频率表 + 三组对比表 + 逐类贡献表）
- record + conclusion
