---
description: 运行开发治理检查（文件长度 / 中文化 / 仓库卫生）
---

## 运行全仓治理扫描

// turbo
1. 运行全仓三类治理检查，输出到终端：

```
python scripts/system/check_development_governance.py
```

## 只检查本次改动文件

2. 传入 pre-commit 提供的文件列表（手动测试时也可以指定单个文件）：

```
python scripts/system/check_development_governance.py src/lq/data/bootstrap.py
```

## 运行所有 pre-commit hooks

// turbo
3. 对全仓所有已跟踪文件跑一遍 pre-commit：

```
pre-commit run --all-files
```

## 生成治理报告

4. 把扫描结果写入报告文件（输出到 Lifespan-temp）：

```
python scripts/system/check_development_governance.py --report-path H:/Lifespan-temp/governance/governance-report-latest.md
```
