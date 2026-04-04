"""每日行情数据获取脚本（主线：mootdx 本地通达信数据）。

数据流：
  通达信本地 .day 文件 → mootdx 读取 → raw_stock_daily / raw_index_daily（L1）

注意：
  - 首次使用前请先运行 bootstrap_storage.py
  - 需要在本机安装通达信并保持数据更新（软件自动同步）
  - TDX_ROOT 环境变量指定通达信安装目录（默认 H:\\new_tdx64）
  - LQ_DATA_ROOT 环境变量指定数据存储目录（默认 H:\\Lifespan-Quant-data）

使用方式：
    python scripts/data/fetch_daily.py
    python scripts/data/fetch_daily.py --tdx-root "H:\\new_tdx64"
    python scripts/data/fetch_daily.py --market sh sz --limit 100
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从通达信本地 .day 文件读取日线数据并写入 raw_market.duckdb"
    )
    parser.add_argument(
        "--tdx-root",
        type=str,
        default=None,
        help="通达信安装根目录（默认读 TDX_ROOT 环境变量，再退用 H:\\new_tdx64）",
    )
    parser.add_argument(
        "--market",
        nargs="+",
        default=["sh", "sz", "bj"],
        help="要扫描的市场，默认 sh sz bj",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多处理的股票数（调试用）",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="只处理指定代码（如 000001.SZ），不指定则处理全市场",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings, tdx_root as resolve_tdx_root
    from lq.data.bootstrap import bootstrap_data_storage
    from lq.data.providers.tdx_local import (
        create_tdx_reader,
        discover_tdx_daily_files,
        load_tdx_daily_dataset,
    )

    import duckdb

    settings = default_settings()
    raw_market_path = settings.databases.raw_market
    market_base_path = settings.databases.market_base

    # 确保 schema 存在
    bootstrap_data_storage(raw_market_path, market_base_path)

    resolved_tdx_root = Path(args.tdx_root) if args.tdx_root else resolve_tdx_root()
    print(f"TDX 数据目录：{resolved_tdx_root}")
    print(f"目标数据库：{raw_market_path}")

    # 扫描本地 .day 文件
    daily_files = discover_tdx_daily_files(
        tdx_root=resolved_tdx_root,
        markets=tuple(args.market),
        limit_files=args.limit,
        stock_codes=args.codes,
    )
    print(f"发现 {len(daily_files)} 个文件（stock + index）")

    if not daily_files:
        print("未发现任何文件，请确认 TDX_ROOT 路径正确。")
        return

    # 创建 mootdx reader
    try:
        reader = create_tdx_reader(resolved_tdx_root)
    except ImportError as e:
        print(f"警告：{e}，将使用二进制兜底解析。")
        reader = None

    run_id = f"tdx-daily-{date.today().isoformat()}-{uuid4().hex[:8]}"
    stock_rows: list[list] = []
    index_rows: list[list] = []
    failed: list[str] = []

    for i, daily_file in enumerate(daily_files, 1):
        try:
            df = load_tdx_daily_dataset(reader, daily_file)
            if df is None or df.empty:
                continue

            provider = "tdx_local_day"
            if daily_file.security_type == "stock":
                for idx, row in df.iterrows():
                    trade_date = idx.date() if hasattr(idx, "date") else idx
                    stock_rows.append([
                        provider,
                        daily_file.normalized_code,
                        trade_date,
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("volume"),
                        row.get("amount"),
                        False,  # is_suspended
                        run_id,
                    ])
            elif daily_file.security_type == "index":
                for idx, row in df.iterrows():
                    trade_date = idx.date() if hasattr(idx, "date") else idx
                    index_rows.append([
                        provider,
                        daily_file.normalized_code,
                        trade_date,
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("volume"),
                        row.get("amount"),
                        run_id,
                    ])
        except Exception as exc:
            failed.append(f"{daily_file.normalized_code}: {exc}")
            continue

        if i % 500 == 0:
            print(f"  已处理 {i}/{len(daily_files)} 个文件...")

    # 批量写入
    print(f"写入 {len(stock_rows)} 条股票日线，{len(index_rows)} 条指数日线...")
    with duckdb.connect(str(raw_market_path)) as conn:
        if stock_rows:
            conn.executemany(
                """INSERT OR REPLACE INTO raw_stock_daily
                   (provider_name, code, trade_date, open, high, low, close,
                    volume, amount, is_suspended, ingest_run_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                stock_rows,
            )
        if index_rows:
            conn.executemany(
                """INSERT OR REPLACE INTO raw_index_daily
                   (provider_name, index_code, trade_date, open, high, low, close,
                    volume, amount, ingest_run_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                index_rows,
            )
        conn.execute(
            """INSERT OR REPLACE INTO raw_ingest_manifest
               (run_id, provider_name, dataset_name, status, rows_written)
               VALUES (?, 'tdx_local_day', 'daily', 'completed', ?)""",
            [run_id, len(stock_rows) + len(index_rows)],
        )

    print(f"完成。run_id={run_id}")
    if failed:
        print(f"失败 {len(failed)} 个：{failed[:5]}{'...' if len(failed) > 5 else ''}")


if __name__ == "__main__":
    main()
