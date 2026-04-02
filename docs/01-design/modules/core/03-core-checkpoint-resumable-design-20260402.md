# core 模块 — checkpoint + resumable 设计 / 2026-04-02

## 1. 设计背景

### 1.1 来源

从父系统（MarketLifespan-Quant）`mlq.core.checkpoint` 和 `mlq.core.resumable` 移植，适配 `lq.core` 命名空间。

原设计决策（父系统）：
- 长任务（data 全量构建、MALF 批量、PAS 批量扫描）运行时间长（数分钟到数十分钟），中途中断后必须能续跑
- checkpoint 存储格式选 JSON（人可读、易调试）而非数据库
- fingerprint 机制防止参数变化后误复用旧 checkpoint
- 统一落到 `temp_root/domain/resume/` 而非各自散落的临时路径

### 1.2 引入时间

v0.1.0 初期（2026-04-02），从"按需增补"状态正式引入 core 层。

---

## 2. 两个文件的职责划分

| 文件 | 职责 | 依赖 |
|---|---|---|
| `checkpoint.py` | JSON 文件的 load/save/update/clear，不含业务逻辑 | 仅 stdlib（json, pathlib） |
| `resumable.py` | 路径推断、fingerprint 计算、加载校验、统一注入 | checkpoint.py + paths.py + stdlib |

`checkpoint.py` 是最底层的文件操作封装；`resumable.py` 在其上增加治理语义（fingerprint、三种拒绝规则、默认路径推断）。

---

## 3. checkpoint.py — JsonCheckpointStore

### 3.1 接口清单

```python
@dataclass
class JsonCheckpointStore:
    path: Path

    @property
    def exists(self) -> bool          # 文件是否存在

    def load(self) -> dict | None     # 加载内容；不存在时返回 None

    def save(payload: dict) -> dict   # 覆盖写入（自动创建父目录）

    def update(**changes) -> dict     # 在已有内容基础上增量更新字段

    def clear() -> None               # 删除文件（不存在时静默跳过）
```

### 3.2 设计约定

- `save()` 使用 `ensure_ascii=False, indent=2`，文件人可读
- `save()` 内部调用 `mkdir(parents=True, exist_ok=True)`，无需调用方提前创建目录
- `update()` 是 load → merge → save 的原子组合（非真正原子，但长任务中已足够）
- 不做内容校验，调用方负责 payload 结构

---

## 4. resumable.py — 续跑工具函数

### 4.1 函数清单

```python
def stable_json_dumps(payload: object) -> str
    # sort_keys=True 的稳定 JSON 序列化，保证相同 dict 总生成相同字符串

def build_resume_digest(fingerprint: dict) -> str
    # SHA-256 前 16 位 hex，用于 checkpoint 文件命名

def resolve_default_checkpoint_path(
    *, settings_root, domain, runner_name, fingerprint
) -> Path
    # 默认路径：temp_root / domain / "resume" / "{runner_name}_{digest}.json"

def prepare_resumable_checkpoint(
    *, checkpoint_path, settings_root, domain, runner_name,
       fingerprint, resume, reset_checkpoint
) -> tuple[JsonCheckpointStore, dict | None]
    # 加载并校验 checkpoint，统一处理三种治理规则（见 4.2）

def save_resumable_checkpoint(
    store, *, fingerprint, payload
) -> dict
    # 统一写回 fingerprint 字段，避免各 runner 漏写

def parse_optional_date(value: object) -> date | None
    # None / "" → None；ISO 字符串 → date 对象
```

### 4.2 prepare_resumable_checkpoint 三种治理规则

| 触发条件 | 行为 | 目的 |
|---|---|---|
| `reset_checkpoint=True` | 先清空已有 checkpoint，再返回 `(store, None)` | 强制全量重跑 |
| checkpoint 存在 + fingerprint 不匹配 | `raise ValueError("不匹配...")` | 防止参数变化后误续跑 |
| checkpoint 存在 + `status="running"` + `resume=False` | `raise ValueError("未完成...")` | 防止意外覆盖未完成 run |

其余情况（无 checkpoint / resume=True 且 fingerprint 匹配）正常返回 `(store, state_or_None)`。

### 4.3 fingerprint 设计原则

fingerprint 应包含所有影响 runner **输出结果**的参数，不应包含运行时元数据（如时间戳、run_id）：

```python
# 好的 fingerprint（参数决定结果）
fingerprint = {
    "window_start": "2024-01-01",
    "window_end":   "2024-12-31",
    "codes_hash":   build_resume_digest({"codes": sorted(codes)}),
}

# 不应放入 fingerprint
# run_id / timestamp / 日志路径等
```

---

## 5. 默认 checkpoint 路径规范

```
<temp_root>/<domain>/resume/<runner_name>_<digest16>.json
```

**示例**（本机环境）：

```
G:\Lifespan-temp\data\resume\build_l2_adjusted_a3f7b2c1d4e5f601.json
G:\Lifespan-temp\malf\resume\run_malf_batch_9b2c3d4e5f6a7b8c.json
G:\Lifespan-temp\alpha\resume\run_pas_batch_1a2b3c4d5e6f7890.json
```

- `domain` 对应 runner 所在的业务模块（`data / malf / alpha / position / trade`）
- `runner_name` 用函数名，如 `build_l2_adjusted`、`run_malf_batch`
- digest 确保不同参数组合各自独立的 checkpoint 文件

---

## 6. 典型使用模式

```python
from lq.core.checkpoint import JsonCheckpointStore
from lq.core.resumable import (
    prepare_resumable_checkpoint,
    save_resumable_checkpoint,
)
from lq.core.paths import default_settings

def run_my_batch(
    codes: list[str],
    window_start: str,
    resume: bool = False,
    reset_checkpoint: bool = False,
) -> None:
    ws = default_settings()
    fingerprint = {"codes_count": len(codes), "window_start": window_start}

    store, state = prepare_resumable_checkpoint(
        checkpoint_path=None,           # 使用默认路径
        settings_root=ws,
        domain="malf",
        runner_name="run_my_batch",
        fingerprint=fingerprint,
        resume=resume,
        reset_checkpoint=reset_checkpoint,
    )

    # 从 checkpoint 恢复已完成的进度
    done_codes = set(state.get("done_codes", [])) if state else set()

    for code in codes:
        if code in done_codes:
            continue
        _process_one(code)
        done_codes.add(code)
        save_resumable_checkpoint(
            store,
            fingerprint=fingerprint,
            payload={"status": "running", "done_codes": sorted(done_codes)},
        )

    save_resumable_checkpoint(
        store,
        fingerprint=fingerprint,
        payload={"status": "done", "done_codes": sorted(done_codes)},
    )
```

---

## 7. 铁律

1. **fingerprint 只含输出决定性参数**：不含时间戳、run_id、日志路径
2. **checkpoint 文件落到 temp_root**：不允许写入 repo_root 或 data_root
3. **checkpoint 文件不提交 git**：`.gitignore` 中需包含 `Lifespan-temp/` 或对应路径
4. **不用于分布式协调**：此工具只适用于单进程续跑，不做跨进程/跨机器的分布式协调
5. **runner 完成后写 `status="done"`**：便于下次运行检测是否真正完成

---

## 8. 与父系统的对比

| 特征 | 父系统（mlq.core） | 本系统（lq.core） |
|---|---|---|
| checkpoint 文件 | JSON | JSON（相同） |
| 接口名称 | 相同 | 相同（直接移植） |
| 导入路径 | `mlq.core.checkpoint` | `lq.core.checkpoint` |
| resumable 导入 | `mlq.core.resumable` | `lq.core.resumable` |
| `WorkspaceRoots` 引用 | `mlq.core.paths` | `lq.core.paths` |
| 测试覆盖 | 无独立单测（内联在 runner 测试中） | **有独立单测**（20 个测试，`tests/unit/test_core.py`） |
