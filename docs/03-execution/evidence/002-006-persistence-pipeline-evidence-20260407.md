# 002-006 七库持久化 pipeline 合并证据 / 2026-04-07

## 覆盖卡

- `002` — malf 持久化 bootstrap
- `003` — structure 持久化 bootstrap
- `004` — filter 持久化 bootstrap
- `005` — research_lab 持久化 bootstrap（alpha/pas）
- `006` — trade_runtime 持久化 bootstrap

## 证据 1：新增代码文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `src/lq/structure/pipeline.py` | ~310 | structure schema + bootstrap + run_structure_build() |
| `src/lq/filter/pipeline.py` | ~380 | filter schema + bootstrap + run_filter_build() |
| `src/lq/alpha/pas/pipeline.py`（增量） | +186 | run_pas_build() 多日期批量 + 断点续传 |
| `src/lq/trade/pipeline.py` | ~367 | trade schema + bootstrap + run_trade_build() |
| `scripts/structure/build_structure_snapshot.py` | ~108 | structure 入口脚本 |
| `scripts/filter/build_filter_snapshot.py` | ~121 | filter 入口脚本 |
| `scripts/alpha/build_pas_signals.py` | ~155 | PAS 信号构建入口脚本 |
| `scripts/trade/build_trade_backtest.py` | ~136 | trade 回测入口脚本 |
| `scripts/data/bootstrap_storage.py`（增量） | +20 | 集成 structure/filter/trade bootstrap |

## 证据 2：__init__.py 导出更新

- `src/lq/structure/__init__.py` — 导出 `bootstrap_structure_storage`, `run_structure_build`, `StructureBuildResult`
- `src/lq/filter/__init__.py` — 导出 `bootstrap_filter_storage`, `run_filter_build`, `FilterBuildResult`
- `src/lq/alpha/pas/__init__.py` — 导出 `run_pas_build`, `PasBuildResult`, `list_stock_codes`
- `src/lq/trade/__init__.py` — 导出 `bootstrap_trade_storage`, `run_trade_build`, `TradeBuildResult`

## 证据 3：设计文档更新

| 文档 | 更新内容 |
|---|---|
| `core/00-core-charter` | DatabasePaths 5→7 库 |
| `malf/00-malf-charter` | §8 持久化 pipeline 章节 |
| `structure/00-structure-charter` | §6 持久化 pipeline 章节 |
| `filter/00-filter-charter` | §6 持久化 pipeline 章节 |
| `trade/00-trade-charter` | pipeline.py 已实现状态 |
| `trade/02-trade-runtime-schema-design` | §9 当前 3 表实现状态 + §10 扩展路径 |
| `system/01-system-orchestration-design` | §9 七库持久化 pipeline 总览 |

## 证据 4：测试结果

```
# 修复前（pre-existing failure）
169 passed, 1 failed (test_has_clear_structure — Timestamp vs date)

# 修复后
169 passed, 0 failed
```

修复方式：`detector.py` 第 202 行新增 `df["date"] = pd.to_datetime(df["date"])`，统一 date 列类型。

## 证据 5：提交记录

```
9e87c53 fix(structure): 修复 classify_breakout_event 中 date 列类型不一致导致比较失败
3f673b2 feat: 七库全持久化 pipeline 完成 — alpha/pas 多日期批量 + trade schema/bootstrap/pipeline + 入口脚本 + 设计文档更新
aecde46 feat(malf): 重写 pipeline 支持分批构建+断点续传+日增量更新
```

## 证据 6：导入验证

```python
python -c "from lq.alpha.pas import run_pas_build, PasBuildResult, list_stock_codes; print('alpha/pas OK'); from lq.trade import bootstrap_trade_storage, run_trade_build, TradeBuildResult; print('trade OK')"
# 输出：
# alpha/pas OK
# trade OK
```

## 证据 7：统一 bootstrap 集成

`scripts/data/bootstrap_storage.py` 现在调用：
1. `bootstrap_raw_market()`
2. `bootstrap_market_base()`
3. `bootstrap_malf_storage()`
4. `bootstrap_structure_storage()`
5. `bootstrap_filter_storage()`
6. `bootstrap_research_lab()`
7. `bootstrap_trade_storage()`

七库 schema 一键幂等初始化。
