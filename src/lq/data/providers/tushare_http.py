"""Tushare HTTP provider 最小客户端。

角色定位：
  仅用于审计辅助（复权因子对比、basic 基本面、交易日历），
  不参与主线 L2 构建，不得在主要数据流中直接替代 mootdx/gbbq。

Token 读取规则：
  通过 load_tushare_token_from_file(path) 从本地配置文件读取，
  禁止在代码中硬编码 token。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request


TUSHARE_PRO_API_URL = "http://api.tushare.pro"
# token 通常是 32-64 位十六进制字符串
_TOKEN_PATTERN = re.compile(r"\b([0-9a-fA-F]{32,64})\b")


@dataclass(frozen=True)
class TushareApiResponse:
    """封装 tushare 单次接口调用结果。"""

    api_name: str
    code: int
    msg: str
    fields: tuple[str, ...]
    items: tuple[tuple[object, ...], ...]
    elapsed_sec: float

    @property
    def row_count(self) -> int:
        return len(self.items)

    @property
    def ok(self) -> bool:
        return self.code == 0

    def as_rows(self) -> list[dict[str, object]]:
        """将 fields/items 还原为字典行列表，便于后续落库或审计。"""
        return [dict(zip(self.fields, row)) for row in self.items]


def extract_tushare_token(text: str) -> str:
    """从 markdown 或纯文本中提取 tushare token（32-64 位十六进制）。"""
    matched = _TOKEN_PATTERN.search(text)
    if matched is None:
        raise ValueError("未在配置文本中找到可用的 tushare token。")
    return matched.group(1)


def load_tushare_token_from_file(config_path: Path) -> str:
    """从本地 markdown 或文本配置文件中读取 tushare token。

    Args:
        config_path: token 配置文件路径（如 docs/04-reference/tushare/tushare-xxx.md）
    """
    text = Path(config_path).read_text(encoding="utf-8")
    return extract_tushare_token(text)


def _normalize_fields(
    fields: str | list[str] | tuple[str, ...] | None,
) -> str | None:
    """将字段列表标准化为逗号分隔字符串。"""
    if fields is None:
        return None
    if isinstance(fields, str):
        return fields
    normalized = [str(f).strip() for f in fields if str(f).strip()]
    return ",".join(normalized) if normalized else None


def call_tushare_api(
    token: str,
    api_name: str,
    params: dict[str, object] | None = None,
    fields: str | list[str] | tuple[str, ...] | None = None,
    *,
    timeout_sec: float = 15.0,
    api_url: str = TUSHARE_PRO_API_URL,
) -> TushareApiResponse:
    """通过 tushare 官方 HTTP 接口发起一次调用。

    Args:
        token:       tushare API token
        api_name:    接口名，如 "adj_factor" / "daily_basic" / "trade_cal"
        params:      接口参数字典
        fields:      返回字段（None 表示全字段）
        timeout_sec: HTTP 超时秒数
        api_url:     接口地址（默认 pro API）

    Raises:
        RuntimeError: HTTP 失败或接口返回非 0 状态码
    """
    payload: dict[str, object] = {
        "api_name": api_name,
        "token": token,
        "params": params or {},
    }
    normalized_fields = _normalize_fields(fields)
    if normalized_fields:
        payload["fields"] = normalized_fields

    started_at = time.perf_counter()
    req = request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            raw_payload = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(f"tushare HTTP 调用失败: status={exc.code}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"tushare 网络调用失败: {exc.reason}") from exc

    elapsed_sec = time.perf_counter() - started_at
    parsed = json.loads(raw_payload)
    data_block = parsed.get("data") or {}
    fields_block = tuple(str(f) for f in (data_block.get("fields") or []))
    items_block = tuple(tuple(row) for row in (data_block.get("items") or []))
    return TushareApiResponse(
        api_name=api_name,
        code=int(parsed.get("code", -1)),
        msg=str(parsed.get("msg", "")),
        fields=fields_block,
        items=items_block,
        elapsed_sec=elapsed_sec,
    )
