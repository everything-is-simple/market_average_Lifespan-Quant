"""一次性全量灌入脚本：从通达信离线导出 txt 文件填充 L1 + L2。

两步走架构 Step 1：
  1. Non-Adjusted txt → raw_stock_daily（L1）
  2. Backward-Adjusted txt → stock_daily_adjusted（L2，adjust_method='backward'）
  3.（可选）Forward-Adjusted txt → stock_daily_adjusted（L2，adjust_method='forward'）
  4. 聚合周/月线

环境变量：
  TDX_OFFLINE_DATA_ROOT  通达信离线导出数据目录（默认 H:\\tdx_offline_Data）
  LQ_DATA_ROOT           数据存储目录（默认 H:\\Lifespan-Quant-data）

用法：
    python scripts/data/bootstrap_from_txt.py
    python scripts/data/bootstrap_from_txt.py --adjust-types non_adjusted backward
    python scripts/data/bootstrap_from_txt.py --markets SH SZ --limit 100
    python scripts/data/bootstrap_from_txt.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path
from uuid import uuid4


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从通达信离线导出 txt 文件一次性全量灌入 L1 + L2"
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default=None,
        help="TDX 离线导出数据目录（默认读 TDX_OFFLINE_DATA_ROOT 环境变量）",
    )
    parser.add_argument(
        "--adjust-types",
        nargs="+",
        default=["non_adjusted", "backward"],
        choices=["non_adjusted", "forward", "backward"],
        help="要灌入的调整类型（默认 non_adjusted backward）",
    )
    parser.add_argument(
        "--markets",
        nargs="+",
        default=None,
        help="限定市场（如 SH SZ BJ），不指定则全部",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="每种调整类型最多处理的文件数（调试用）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="每批写入的股票数，默认 500",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="gbk",
        help="txt 文件编码（默认 gbk）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印计划，不实际写入",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings, tdx_offline_data_root
    from lq.data.bootstrap import bootstrap_data_storage
    from lq.data.providers.tdx_txt_reader import (
        discover_txt_files,
        parse_txt_file,
    )

    import duckdb
    import pandas as pd

    settings = default_settings()
    raw_market_path = settings.databases.raw_market
    market_base_path = settings.databases.market_base

    offline_root = Path(args.data_root) if args.data_root else tdx_offline_data_root()
    markets = tuple(m.upper() for m in args.markets) if args.markets else None

    print("=" * 60)
    print("TDX 离线 txt 全量灌入")
    print("=" * 60)
    print(f"  离线数据目录: {offline_root}")
    print(f"  raw_market:   {raw_market_path}")
    print(f"  market_base:  {market_base_path}")
    print(f"  调整类型:     {args.adjust_types}")
    print(f"  市场:         {markets or '全部'}")
    print(f"  limit:        {args.limit or '无限制'}")
    print()

    # 扫描文件
    for adj_type in args.adjust_types:
        files = discover_txt_files(
            offline_root,
            security_type="stock",
            adjust_type=adj_type,
            markets=markets,
        )
        if args.limit:
            files = files[:args.limit]
        print(f"  [{adj_type}] 发现 {len(files)} 个文件")

    if args.dry_run:
        print("\n[dry-run] 未执行任何写入操作。")
        return

    # 确保 schema 存在
    settings.ensure_directories()
    bootstrap_data_storage(raw_market_path, market_base_path)

    t0 = time.time()

    # ---------------------------------------------------------------
    # Step 1: Non-Adjusted → raw_stock_daily（L1）
    # ---------------------------------------------------------------
    if "non_adjusted" in args.adjust_types:
        print("\n--- Step 1: Non-Adjusted → raw_stock_daily (L1) ---")
        run_id = f"txt-raw-{date.today().isoformat()}-{uuid4().hex[:8]}"
        files = discover_txt_files(
            offline_root, "stock", "non_adjusted", markets
        )
        if args.limit:
            files = files[:args.limit]

        total_rows = 0
        failed: list[str] = []
        batch_dfs: list[pd.DataFrame] = []

        with duckdb.connect(str(raw_market_path)) as conn:
            for i, fi in enumerate(files, 1):
                try:
                    df = parse_txt_file(fi, encoding=args.encoding)
                    if df.empty:
                        continue

                    # 构造符合 raw_stock_daily schema 的 DataFrame
                    df["provider_name"] = "tdx_offline_txt"
                    df["is_suspended"] = df["volume"] == 0
                    df["ingest_run_id"] = run_id
                    batch_dfs.append(df)

                    # 每 batch_size 只股票批量写入一次
                    if i % args.batch_size == 0:
                        merged = pd.concat(batch_dfs, ignore_index=True)
                        conn.execute(
                            """INSERT OR REPLACE INTO raw_stock_daily
                               (provider_name, code, trade_date, open, high, low, close,
                                volume, amount, is_suspended, ingest_run_id)
                               SELECT provider_name, code, trade_date, open, high, low, close,
                                      volume, amount, is_suspended, ingest_run_id
                               FROM merged"""
                        )
                        total_rows += len(merged)
                        batch_dfs = []
                        print(f"  已处理 {i}/{len(files)} 个文件 ({total_rows} 行)...")

                except Exception as exc:
                    failed.append(f"{fi.normalized_code}: {exc}")

            # 写入剩余
            if batch_dfs:
                merged = pd.concat(batch_dfs, ignore_index=True)
                conn.execute(
                    """INSERT OR REPLACE INTO raw_stock_daily
                       (provider_name, code, trade_date, open, high, low, close,
                        volume, amount, is_suspended, ingest_run_id)
                       SELECT provider_name, code, trade_date, open, high, low, close,
                              volume, amount, is_suspended, ingest_run_id
                       FROM merged"""
                )
                total_rows += len(merged)

            # 写 manifest
            conn.execute(
                """INSERT OR REPLACE INTO raw_ingest_manifest
                   (run_id, provider_name, dataset_name, status, rows_written)
                   VALUES (?, 'tdx_offline_txt', 'raw_stock_daily', 'completed', ?)""",
                [run_id, total_rows],
            )

        print(f"  L1 完成: {total_rows} 行, 失败 {len(failed)} 个, run_id={run_id}")
        if failed:
            for f in failed[:10]:
                print(f"    [FAIL] {f}")
            if len(failed) > 10:
                print(f"    ... 还有 {len(failed) - 10} 个")

    # ---------------------------------------------------------------
    # Step 2: Backward-Adjusted → stock_daily_adjusted（L2）
    # ---------------------------------------------------------------
    for adj_type in ["backward", "forward"]:
        if adj_type not in args.adjust_types:
            continue

        print(f"\n--- Step 2: {adj_type} → stock_daily_adjusted (L2) ---")
        run_id = f"txt-adj-{adj_type[:3]}-{date.today().isoformat()}-{uuid4().hex[:8]}"
        files = discover_txt_files(
            offline_root, "stock", adj_type, markets
        )
        if args.limit:
            files = files[:args.limit]

        total_rows = 0
        failed = []
        batch_dfs: list[pd.DataFrame] = []

        with duckdb.connect(str(market_base_path)) as conn:
            for i, fi in enumerate(files, 1):
                try:
                    df = parse_txt_file(fi, encoding=args.encoding)
                    if df.empty:
                        continue

                    # 过滤停牌日（volume == 0）
                    df = df[df["volume"] > 0].copy()
                    if df.empty:
                        continue

                    # 构造符合 stock_daily_adjusted schema 的 DataFrame
                    df["adjust_method"] = adj_type
                    df["adjustment_factor"] = None
                    df["build_run_id"] = run_id
                    batch_dfs.append(df)

                    if i % args.batch_size == 0:
                        merged = pd.concat(batch_dfs, ignore_index=True)
                        conn.execute(
                            """INSERT OR REPLACE INTO stock_daily_adjusted
                               (code, trade_date, adjust_method, open, high, low, close,
                                volume, amount, adjustment_factor, build_run_id)
                               SELECT code, trade_date, adjust_method, open, high, low, close,
                                      volume, amount, adjustment_factor, build_run_id
                               FROM merged"""
                        )
                        total_rows += len(merged)
                        batch_dfs = []
                        print(f"  已处理 {i}/{len(files)} 个文件 ({total_rows} 行)...")

                except Exception as exc:
                    failed.append(f"{fi.normalized_code}: {exc}")

            if batch_dfs:
                merged = pd.concat(batch_dfs, ignore_index=True)
                conn.execute(
                    """INSERT OR REPLACE INTO stock_daily_adjusted
                       (code, trade_date, adjust_method, open, high, low, close,
                        volume, amount, adjustment_factor, build_run_id)
                       SELECT code, trade_date, adjust_method, open, high, low, close,
                              volume, amount, adjustment_factor, build_run_id
                       FROM merged"""
                )
                total_rows += len(merged)

            # 写 manifest
            conn.execute(
                """INSERT OR REPLACE INTO base_build_manifest
                   (run_id, source_name, dataset_name, status, rows_written)
                   VALUES (?, 'tdx_offline_txt', ?, 'completed', ?)""",
                [run_id, f"stock_daily_adjusted_{adj_type}", total_rows],
            )

        print(f"  L2({adj_type}) 完成: {total_rows} 行, 失败 {len(failed)} 个, run_id={run_id}")
        if failed:
            for f in failed[:10]:
                print(f"    [FAIL] {f}")

    elapsed = time.time() - t0
    print(f"\n全部完成，耗时 {elapsed:.1f} 秒。")


if __name__ == "__main__":
    main()
