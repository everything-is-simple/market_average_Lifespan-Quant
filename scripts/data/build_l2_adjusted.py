"""L2 后复权价格构建脚本。

从 L1 raw_market.duckdb 计算后复权日线 + 周线 + 月线，写入 market_base.duckdb。

用法：
    python scripts/data/build_l2_adjusted.py
    python scripts/data/build_l2_adjusted.py --window-start 2024-01-01 --window-end 2024-12-31
    python scripts/data/build_l2_adjusted.py --codes 000001.SZ 600519.SH
    python scripts/data/build_l2_adjusted.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="L2 后复权价格构建：raw_market → market_base"
    )
    parser.add_argument(
        "--window-start",
        type=date.fromisoformat,
        default=None,
        help="增量窗口起始日（YYYY-MM-DD），不指定则全量重建",
    )
    parser.add_argument(
        "--window-end",
        type=date.fromisoformat,
        default=None,
        help="增量窗口终止日（YYYY-MM-DD），不指定则到最新",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="只处理指定代码（如 000001.SZ 600519.SH），不指定则处理全市场",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="每批处理的股票数，默认 200",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印参数，不执行构建",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings
    from lq.data.bootstrap import bootstrap_data_storage
    from lq.data.compute.pipeline import build_l2_adjusted

    settings = default_settings()
    raw_market_path  = settings.databases.raw_market
    market_base_path = settings.databases.market_base

    print("=" * 60)
    print("L2 后复权构建")
    print("=" * 60)
    print(f"  raw_market:  {raw_market_path}")
    print(f"  market_base: {market_base_path}")
    print(f"  window:      {args.window_start} → {args.window_end}")
    print(f"  codes:       {args.codes or '全市场'}")
    print()

    if args.dry_run:
        print("[dry-run] 未执行任何写入。")
        return

    # 确保 schema 存在
    bootstrap_data_storage(raw_market_path, market_base_path)

    result = build_l2_adjusted(
        raw_market_path=raw_market_path,
        market_base_path=market_base_path,
        window_start=args.window_start,
        window_end=args.window_end,
        codes=args.codes,
        batch_size=args.batch_size,
        verbose=True,
    )

    print()
    print(f"状态:   {result.status}")
    print(f"run_id: {result.run_id}")
    print(f"股票数: {result.codes_processed} 成功 / {result.codes_failed} 失败")
    print(f"写入:   日线 {result.daily_rows} 行  周线 {result.weekly_rows} 行  月线 {result.monthly_rows} 行")


if __name__ == "__main__":
    main()
