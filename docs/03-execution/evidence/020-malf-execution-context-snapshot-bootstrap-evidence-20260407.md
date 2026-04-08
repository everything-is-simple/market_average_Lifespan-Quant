# 020. MALF execution_context_snapshot bootstrap 证据

## 文档证据

1. 新增执行卡：`docs/03-execution/020-malf-execution-context-snapshot-bootstrap-card-20260407.md`
2. 新增执行证据：`docs/03-execution/evidence/020-malf-execution-context-snapshot-bootstrap-evidence-20260407.md`
3. 新增执行记录：`docs/03-execution/records/020-malf-execution-context-snapshot-bootstrap-record-20260407.md`
4. 新增执行结论：`docs/03-execution/020-malf-execution-context-snapshot-bootstrap-conclusion-20260407.md`

## 代码证据

1. 修订 `src/lq/malf/contracts.py`
   - 新增 `EXECUTION_CONTEXT_CONTRACT_VERSION = "v1"`
2. 修订 `src/lq/malf/pipeline.py`
   - 新增 `execution_context_snapshot` schema
   - 新增 `_EXECUTION_CONTEXT_COLS`
   - 新增 `_build_execution_context_df()`
   - 在 `_flush_batch()` 中同步写入 bridge table
3. 新增补丁测试：`tests/patches/malf/test_execution_context_snapshot_bridge.py`

## 测试证据

命令：

```bash
pytest tests/patches/malf/test_execution_context_snapshot_bridge.py -q --basetemp H:\Lifespan-temp\pytest_exec_ctx_bridge
```

结果：

```text
1 passed in 1.09s
```

## 边界证据

1. `execution_context_snapshot` 当前是 `malf_context_snapshot` 的第一版执行桥镜像，不包含真实 active wave 样本池推导。
2. `active_wave_id` / `historical_sample_count` 目前显式落 `NULL`，没有伪造业务含义。
3. 下游 `PAS / position` 还未在本卡内切换到 bridge table。
