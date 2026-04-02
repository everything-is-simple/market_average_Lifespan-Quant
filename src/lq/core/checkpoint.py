"""长任务 JSON checkpoint 存储工具。

只依赖标准库（json / pathlib），不引入任何第三方库。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class JsonCheckpointStore:
    """统一管理长任务的 JSON checkpoint 文件。

    典型用法：
        store = JsonCheckpointStore(path)
        state = store.load()            # 加载已有状态（不存在时返回 None）
        store.save({"status": "done"})  # 覆盖写入
        store.update(stage="step2")     # 增量更新
        store.clear()                   # 删除文件
    """

    path: Path

    @property
    def exists(self) -> bool:
        """checkpoint 文件是否存在。"""
        return self.path.exists()

    def load(self) -> dict[str, Any] | None:
        """加载 checkpoint 内容；文件不存在时返回 None。"""
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        """覆盖写入 checkpoint（自动创建父目录）。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def update(self, **changes: Any) -> dict[str, Any]:
        """在已有内容基础上增量更新指定字段。"""
        current = self.load() or {}
        current.update(changes)
        return self.save(current)

    def clear(self) -> None:
        """删除 checkpoint 文件（文件不存在时静默跳过）。"""
        if self.path.exists():
            self.path.unlink()
