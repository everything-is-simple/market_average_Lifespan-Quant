# 021. PAS / position execution_context_snapshot 消费迁移 证据

## 文档证据

1. 新增执行卡：`docs/03-execution/021-pas-position-execution-context-consumer-migration-card-20260407.md`
2. 新增执行证据：`docs/03-execution/evidence/021-pas-position-execution-context-consumer-migration-evidence-20260407.md`
3. 新增执行记录：`docs/03-execution/records/021-pas-position-execution-context-consumer-migration-record-20260407.md`
4. 新增执行结论：`docs/03-execution/021-pas-position-execution-context-consumer-migration-conclusion-20260407.md`
5. 修订文档：
   - `docs/01-design/modules/alpha/03-pas-contracts-and-output-governance-20260401.md`
   - `docs/02-spec/modules/alpha/01-alpha-pas-contracts-and-pipeline-spec-20260401.md`
   - `docs/01-design/modules/position/00-position-charter-20260331.md`

## 代码证据

1. 修订 `src/lq/alpha/pas/contracts.py`
   - `PasSignal` 新增正式上下文与生命周期字段
   - 保留 `monthly_state / weekly_flow` 作为兼容字段
2. 修订 `src/lq/alpha/pas/bootstrap.py`
   - `pas_formal_signal` schema 新增正式生命周期列
   - 为已有库补 migration
3. 修订 `src/lq/alpha/pas/pipeline.py`
   - 正式读取源切到 `execution_context_snapshot`
   - `cell_gate_check()` 仍通过 `monthly_state / weekly_flow` 兼容字段执行
   - `PasSignal` 与 `pas_formal_signal` 写入正式生命周期字段
4. 修订 `src/lq/system/orchestration.py`
   - 系统路径构造 `PasSignal` 时透传正式字段
5. 修订 `src/lq/trade/pipeline.py`
   - 从信号表重建 `PasSignal` 时同步读取正式字段
6. 修订测试：
   - `tests/patches/alpha/test_pas_gate_bridge.py`
   - `tests/integration/test_mainline_pipeline.py`

## 测试证据

命令 1：

```bash
pytest tests/patches/alpha/test_pas_gate_bridge.py tests/unit/test_position.py -q --basetemp H:\Lifespan-temp\pytest_pas_position_bridge
```

结果：

```text
11 passed in 3.99s
```

命令 2：

```bash
pytest tests/integration/test_mainline_pipeline.py -q --basetemp H:\Lifespan-temp\pytest_mainline_pas_contract
```

结果：

```text
33 passed in 3.26s
```

## 边界证据

1. 本卡没有修改 `cell_gate_check()` 的业务矩阵。
2. 本卡没有修改 position sizing 公式。
3. 本卡没有实现 active wave / 历史样本池 / 真实 ranking 算法。
4. 当前 markdownlint 警告主要来自既有文档排版风格，本卡未做无关格式清扫。
