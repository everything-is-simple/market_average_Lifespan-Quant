"""除权除息事件入库脚本（来源：通达信本地 gbbq 文件）。

数据流：
  TDX_ROOT/T0002/hq_cache/gbbq（加密二进制）→ 解密解析 → raw_xdxr_event（L1）

gbbq 文件包含 14 种企业行动事件，其中 category=1（除权除息）是
后复权因子计算的核心依据。gbbq 由通达信软件在日常行情更新时自动维护。

注意：
  - 首次使用前请先运行 bootstrap_storage.py
  - TDX_ROOT 环境变量指定通达信安装目录（默认 G:\\new-tdx\\new-tdx）

使用方式：
    python scripts/data/ingest_xdxr.py
    python scripts/data/ingest_xdxr.py --tdx-root "G:\\new-tdx\\new-tdx"
    python scripts/data/ingest_xdxr.py --codes 000001.SZ 600519.SH
"""

from __future__ import annotations

import argparse
import struct
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


# ---------------------------------------------------------------------------
# gbbq 文件解析常量（来自通达信协议逆向工程）
# ---------------------------------------------------------------------------
_GBBQ_RECORD_SIZE = 29
_UINT32_MASK = 0xFFFF_FFFF
_CATEGORY_NAME_MAP = {
    1: "除权除息",
    2: "送配股上市",
    3: "非流通股上市",
    4: "未知股本变动",
    5: "股本变化",
    6: "增发新股",
    7: "股份回购",
    8: "增发新股上市",
    9: "转配股上市",
    10: "可转债上市",
    11: "扩缩股",
    12: "非流通股缩股",
    13: "送认购权证",
    14: "送认沽权证",
}
_MARKET_SUFFIX_MAP = {0: "SZ", 1: "SH", 2: "BJ"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从通达信本地 gbbq 文件读取除权除息事件并写入 raw_xdxr_event"
    )
    parser.add_argument("--tdx-root", type=str, default=None)
    parser.add_argument("--codes", nargs="+", default=None, help="只处理指定代码")
    return parser.parse_args()


def _u32(buf: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(buf[offset: offset + 4], "little")


def _decode_date(raw: int) -> date | None:
    try:
        return datetime.strptime(str(raw), "%Y%m%d").date()
    except ValueError:
        return None


def _decipher(record: bytearray, key: bytes) -> bytes:
    """按 gbbq 本地加密算法解密 29 字节记录。"""
    pos = 0
    for chunk in range(0, 24, 8):
        eax = _u32(key, 0x44)
        ebx = _u32(record, pos)
        num = (eax ^ ebx) & _UINT32_MASK
        numold = _u32(record, pos + 4)
        for ro in range(64, 0, -4):
            ebx = (num & 0xFF0000) >> 16
            eax = (_u32(key, ebx * 4 + 0x448) + _u32(key, (num >> 24) * 4 + 0x48)) & _UINT32_MASK
            eax ^= _u32(key, ((num & 0xFF00) >> 8) * 4 + 0x848)
            eax = (eax + _u32(key, (num & 0xFF) * 4 + 0xC48)) & _UINT32_MASK
            eax ^= _u32(key, ro)
            ebx = num
            num = (numold ^ eax) & _UINT32_MASK
            numold = ebx
        numold ^= _u32(key, 0)
        record[chunk: chunk + 4] = numold.to_bytes(4, "little")
        record[chunk + 4: chunk + 8] = num.to_bytes(4, "little")
        pos += 8
    return bytes(record)


def _decode_payload(category: int, payload: bytes):
    """按类别解码 16 字节 payload，返回 (fenhong, peigujia, songzhuangu, peigu, suogu, ...)。"""
    fenhong = peigujia = songzhuangu = peigu = suogu = None
    panqianliutong = panhouliutong = qianzongguben = houzongguben = None
    fenshu = xingquanjia = None

    if category == 1:
        fenhong, peigujia, songzhuangu, peigu = struct.unpack("<ffff", payload)
    elif category in (11, 12):
        _, _, suogu, _ = struct.unpack("<IIfI", payload)
    elif category in (13, 14):
        xingquanjia, _, fenshu, _ = struct.unpack("<fIfI", payload)
    return (
        fenhong, peigujia, songzhuangu, peigu, suogu,
        panqianliutong, panhouliutong, qianzongguben, houzongguben,
        fenshu, xingquanjia,
    )


def _load_gbbq_key() -> bytes:
    """从 lq.data.raw.gbbq_key 加载解密密钥（若不存在则返回 None）。"""
    try:
        from lq.data.raw.gbbq_key import GBBQ_KEY
        return GBBQ_KEY
    except ImportError:
        return None


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings, tdx_root as resolve_tdx_root
    from lq.data.bootstrap import bootstrap_data_storage

    import duckdb

    settings = default_settings()
    raw_market_path = settings.databases.raw_market
    market_base_path = settings.databases.market_base
    bootstrap_data_storage(raw_market_path, market_base_path)

    resolved_tdx_root = Path(args.tdx_root) if args.tdx_root else resolve_tdx_root()
    gbbq_path = resolved_tdx_root / "T0002" / "hq_cache" / "gbbq"

    if not gbbq_path.exists():
        print(f"gbbq 文件不存在：{gbbq_path}")
        print("请确认通达信已安装并完成一次行情更新。")
        return

    key = _load_gbbq_key()
    if key is None:
        print("警告：未找到 gbbq 解密密钥（lq/data/raw/gbbq_key.py），无法解密。")
        print("请将密钥文件复制至 src/lq/data/raw/gbbq_key.py。")
        return

    allowed_codes: set[str] | None = (
        {c.strip().upper() for c in args.codes} if args.codes else None
    )

    raw_bytes = gbbq_path.read_bytes()
    if len(raw_bytes) < 4:
        print("gbbq 文件为空。")
        return

    count = int.from_bytes(raw_bytes[:4], "little")
    encrypted = bytearray(raw_bytes[4:])
    expected_len = count * _GBBQ_RECORD_SIZE
    if len(encrypted) < expected_len:
        raise ValueError("gbbq 文件长度与头部记录数不一致。")

    run_id = f"tdx-gbbq-{date.today().isoformat()}-{uuid4().hex[:8]}"
    rows: list[list] = []

    for offset in range(0, expected_len, _GBBQ_RECORD_SIZE):
        record = _decipher(encrypted[offset: offset + _GBBQ_RECORD_SIZE], key)
        market_flag = record[0]
        plain_code = record[1:7].decode("ascii", errors="ignore").strip("\x00").strip()
        if not plain_code:
            continue
        exchange = _MARKET_SUFFIX_MAP.get(market_flag)
        if exchange is None:
            continue
        normalized = f"{plain_code}.{exchange}"
        if allowed_codes is not None and normalized not in allowed_codes:
            continue

        event_date = _decode_date(_u32(record, 8))
        if event_date is None:
            continue
        category = record[12]
        payload_fields = _decode_payload(category, record[13:29])
        rows.append([
            "tdx_local_gbbq",
            normalized,
            event_date,
            category,
            _CATEGORY_NAME_MAP.get(category, str(category)),
            *payload_fields,
            run_id,
        ])

    print(f"解析完成：{len(rows)} 条记录。写入 raw_xdxr_event...")

    with duckdb.connect(str(raw_market_path)) as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO raw_xdxr_event
               (provider_name, code, event_date, category, category_name,
                fenhong, peigujia, songzhuangu, peigu, suogu,
                panqianliutong, panhouliutong, qianzongguben, houzongguben,
                fenshu, xingquanjia, ingest_run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.execute(
            """INSERT OR REPLACE INTO raw_ingest_manifest
               (run_id, provider_name, dataset_name, status, rows_written)
               VALUES (?, 'tdx_local_gbbq', 'xdxr', 'completed', ?)""",
            [run_id, len(rows)],
        )

    print(f"完成。run_id={run_id}")


if __name__ == "__main__":
    main()
