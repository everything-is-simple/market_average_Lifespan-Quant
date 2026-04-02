"""正式 runner 共用的最小续跑 helper。

只依赖标准库（hashlib / json / pathlib / datetime），不引入任何第三方库。
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from lq.core.checkpoint import JsonCheckpointStore
from lq.core.paths import WorkspaceRoots


def stable_json_dumps(payload: object) -> str:
    """把指纹与 checkpoint 统一序列化成稳定 JSON。

    sort_keys=True 保证相同内容的字典始终生成相同字符串，避免 key 顺序抖动导致摘要不一致。
    """
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_resume_digest(fingerprint: dict[str, Any]) -> str:
    """根据指纹 dict 生成 16 位 hex 短摘要，用于 checkpoint 文件命名。"""
    return hashlib.sha256(stable_json_dumps(fingerprint).encode("utf-8")).hexdigest()[:16]


def resolve_default_checkpoint_path(
    *,
    settings_root: WorkspaceRoots,
    domain: str,
    runner_name: str,
    fingerprint: dict[str, Any],
) -> Path:
    """未显式指定 checkpoint 路径时，统一落到 temp_root/domain/resume/ 目录下。

    参数：
        settings_root — WorkspaceRoots 实例（提供 temp_root）
        domain        — 所属业务域，如 "data" / "malf" / "alpha"
        runner_name   — runner 函数名或标识，如 "build_l2_adjusted"
        fingerprint   — 唯一标识本次 run 参数的 dict（用于生成文件名摘要）

    返回：
        Path 对象，形如 <temp_root>/<domain>/resume/<runner_name>_<digest>.json
    """
    return (
        settings_root.temp_root
        / domain
        / "resume"
        / f"{runner_name}_{build_resume_digest(fingerprint)}.json"
    )


def prepare_resumable_checkpoint(
    *,
    checkpoint_path: Path | None,
    settings_root: WorkspaceRoots,
    domain: str,
    runner_name: str,
    fingerprint: dict[str, Any],
    resume: bool,
    reset_checkpoint: bool,
) -> tuple[JsonCheckpointStore, dict[str, Any] | None]:
    """加载并校验正式 checkpoint，统一处理三种治理规则：

    1. ``reset_checkpoint=True``：先清空旧 checkpoint，从头重跑。
    2. 发现未完成 checkpoint 且本次 ``resume=False``：拒绝整链重跑，要求显式 resume 或 reset。
    3. 发现指纹不匹配：要求 reset，防止误复用旧 run 的 checkpoint。

    参数：
        checkpoint_path  — 显式指定的 checkpoint 文件路径；None 时自动推断
        settings_root    — WorkspaceRoots 实例
        domain           — 所属业务域
        runner_name      — runner 标识
        fingerprint      — 本次 run 的唯一参数指纹
        resume           — True = 尝试从已有 checkpoint 续跑
        reset_checkpoint — True = 强制清空并重跑

    返回：
        (store, state)
        - store  — JsonCheckpointStore 实例（始终返回，无论是否已有 checkpoint）
        - state  — 已有 checkpoint 内容（resume=True 且有效时）；否则为 None
    """
    resolved_path = (
        Path(checkpoint_path)
        if checkpoint_path is not None
        else resolve_default_checkpoint_path(
            settings_root=settings_root,
            domain=domain,
            runner_name=runner_name,
            fingerprint=fingerprint,
        )
    )
    store = JsonCheckpointStore(resolved_path)
    if reset_checkpoint:
        store.clear()
    state = store.load() if store.exists else None
    if state is None:
        return store, None
    if state.get("fingerprint") != fingerprint:
        raise ValueError(
            "检测到与当前输入不匹配的 checkpoint；请先 reset_checkpoint=True 再重跑。"
        )
    if not resume and state.get("status") == "running":
        raise ValueError(
            "检测到未完成 checkpoint；请使用 resume=True 续跑或 reset_checkpoint=True 重置。"
        )
    return store, state if resume else None


def save_resumable_checkpoint(
    store: JsonCheckpointStore,
    *,
    fingerprint: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """统一把 fingerprint 写回 checkpoint，避免各 runner 漏写。

    参数：
        store       — JsonCheckpointStore 实例
        fingerprint — 本次 run 的唯一参数指纹（合并进 payload 后保存）
        payload     — runner 当前要保存的状态内容

    返回：
        合并后写入磁盘的完整 payload dict
    """
    merged = dict(payload)
    merged["fingerprint"] = fingerprint
    return store.save(merged)


def parse_optional_date(value: object) -> date | None:
    """把可空日期字段统一解析为 ``date | None``。

    接受 None、空字符串（""）、或 ISO 格式字符串（"2026-03-31"）。
    """
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))
