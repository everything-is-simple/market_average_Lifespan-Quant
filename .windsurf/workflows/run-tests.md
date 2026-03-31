---
description: 运行单元测试（全量或指定模块）
---

运行全部单元测试：

// turbo
1. 全量单元测试：

```bash
pytest tests/unit -q
```

2. 只跑某个模块的测试（例如 data）：

```bash
pytest tests/unit/data -q
```

3. 只跑某个模块的测试（例如 trade）：

```bash
pytest tests/unit/trade -q
```

4. 全量测试含集成测试：

```bash
pytest -q
```
