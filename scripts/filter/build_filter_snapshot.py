"""Filter 不利条件过滤快照构建脚本 — 分批构建 + 断点续传 + 日增量。

依赖链：filter 依赖 malf + structure 已完成构建。
    market_base → malf → structure → filter

用法：
    # 全量构建（历史回填）
    python scripts/filter/build_filter_snapshot.py --start 2015-01-01 --end 2026-04-07

    # 断点续传（中断后继续）
    python scripts/filter/build_filter_snapshot.py --start 2015-01-01 --end 2026-04-07 --resume

    # 日增量（每日收盘后）
    python scripts/filter/build_filter_snapshot.py --date 2026-04-07

    # 指定股票
    python scripts/filter/build_filter_snapshot.py --date 2026-04-07 --codes 000001.SZ 600519.SH

    # 参数预览
    python scripts/filter/build_filter_snapshot.py --date 2026-04-07 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Filter 不利条件过滤构建：market_base + malf + structure → filter.duckdb"
    )

    p.add_argument(
        "--start", type=date.fromisoformat, default=None,
        help="构建起始日（YYYY-MM-DD），全量模式必填",
    )
    p.add_argument(
        "--end", type=date.fromisoformat, default=None,
        help="构建终止日（YYYY-MM-DD），默认到最新",
    )
    p.add_argument(
        "--date", type=date.fromisoformat, default=None,
        help="单日增量模式（YYYY-MM-DD）",
    )
    p.add_argument(
        "--codes", nargs="+", default=None,
        help="只处理指定股票代码，不指定则全市场",
    )
    p.add_argument(
        "--batch-size", type=int, default=200,
        help="每批股票数，默认 200",
    )
    p.add_argument(
        "--resume", action="store_true",
        help="从 checkpoint 续跑",
    )
    p.add_argument(
        "--reset", action="store_true",
        help="清空旧 checkpoint 重跑",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="仅打印参数，不执行",
    )

    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.date is None and args.start is None:
        print("错误：必须指定 --date（日增量）或 --start（全量构建）", file=sys.stderr)
        sys.exit(1)
    if args.date is not None and args.start is not None:
        print("错误：--date 与 --start 不能同时指定", file=sys.stderr)
        sys.exit(1)

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings
    from lq.filter.pipeline import (
        bootstrap_filter_storage,
        list_trading_dates,
        run_filter_build,
    )

    settings = default_settings()
    dbs = settings.databases

    print("=" * 60)
    print("Filter 不利条件过滤构建")
    print("=" * 60)
    print(f"  market_base: {dbs.market_base}")
    print(f"  malf:        {dbs.malf}")
    print(f"  structure:   {dbs.structure}")
    print(f"  filter:      {dbs.filter}")

    if args.date is not None:
        signal_dates = [args.date]
        print(f"  模式:        日增量（{args.date}）")
    else:
        end = args.end or date.today()
        print(f"  模式:        全量（{args.start} → {end}）")
        print("  正在获取交易日列表...")
        signal_dates = list_trading_dates(dbs.market_base, args.start, end)
        print(f"  交易日数:    {len(signal_dates)}")

    print(f"  股票:        {args.codes or '全市场'}")
    print(f"  批大小:      {args.batch_size}")
    print(f"  续跑:        {'是' if args.resume else '否'}")
    print()

    if args.dry_run:
        print("[dry-run] 未执行任何写入。")
        return

    if not signal_dates:
        print("无交易日需要处理，退出。")
        return

    bootstrap_filter_storage(dbs.filter)

    result = run_filter_build(
        market_base_path=dbs.market_base,
        malf_db_path=dbs.malf,
        structure_db_path=dbs.structure,
        filter_db_path=dbs.filter,
        signal_dates=signal_dates,
        codes=args.codes,
        batch_size=args.batch_size,
        resume=args.resume,
        reset_checkpoint=args.reset,
        settings=settings,
        verbose=True,
    )

    print()
    print(f"状态:   {result.status}")
    print(f"run_id: {result.run_id}")


if __name__ == "__main__":
    main()
