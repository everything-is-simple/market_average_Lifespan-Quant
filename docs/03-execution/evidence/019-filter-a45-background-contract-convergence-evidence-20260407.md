# 019. filter A4-5 背景合同收敛 证据

## 文档证据

1. 新增执行卡：`docs/03-execution/019-filter-a45-background-contract-convergence-card-20260407.md`
2. 新增执行证据：`docs/03-execution/evidence/019-filter-a45-background-contract-convergence-evidence-20260407.md`
3. 新增执行记录：`docs/03-execution/records/019-filter-a45-background-contract-convergence-record-20260407.md`
4. 新增执行结论：`docs/03-execution/019-filter-a45-background-contract-convergence-conclusion-20260407.md`
5. 修订设计文档：
   - `docs/01-design/modules/filter/00-filter-charter-20260401.md`
   - `docs/01-design/modules/filter/01-filter-adverse-conditions-design-20260401.md`

## 代码证据

1. 修订 `src/lq/filter/adverse.py`
   - A4-5 先以 `long_background_2 == "BEAR"` 判断正式长期背景
   - 将“逆势反弹”判断从 `weekly_flow == "against_flow"` 收敛为 `intermediate_role_2 == "COUNTERTREND"`
   - `monthly_state` 仅保留 BEAR_FORMING / BEAR_PERSISTING 的兼容细粒度用途
2. 修订 `tests/patches/filter/test_bear_forming_block.py`
   - 新增 `BEAR_PERSISTING + COUNTERTREND` 的回归测试

## 测试证据

命令：

```bash
pytest tests/patches/filter/test_bear_forming_block.py -q --basetemp H:\Lifespan-temp\pytest_filter_a45
```

结果：

```text
5 passed in 0.98s
```

## 边界证据

1. 本卡未实现生命周期三轴过滤。
2. 本卡未改 PAS gate。
3. 本卡未改 position sizing。
4. 当前仓库中的 markdownlint 警告大多为设计文档既有排版风格问题，本卡未额外做格式化清扫。
