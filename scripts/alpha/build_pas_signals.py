"""PAS 信号批量构建脚本 — 分批构建 + 断点续传 + 日增量。

用法：
    # 全量构建（历史回填）
    python scripts/alpha/build_pas_signals.py --start 2015-01-01 --end 2026-04-07

    # 断点续传（中断后继续）
    python scripts/alpha/build_pas_signals.py --start 2015-01-01 --end 2026-04-07 --resume

    # 日增量（每日收盘后）
    python scripts/alpha/build_pas_signals.py --date 2026-04-07

    # 指定股票
    python scripts/alpha/build_pas_signals.py --date 2026-04-07 --codes 600000.SH 600006.SH

    # 参数预览
    python scripts/alpha/build_pas_signals.py --date 2026-04-07 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="PAS 信号批量构建：market_base + malf → research_lab.duckdb"
    )

    # 日期范围（全量构建）
    p.add_argument(
        "--start", type=date.fromisoformat, default=None,
        help="构建起始日（YYYY-MM-DD），全量模式必填",
    )
    p.add_argument(
        "--end", type=date.fromisoformat, default=None,
        help="构建终止日（YYYY-MM-DD），默认到最新",
    )

    # 单日（日增量）
    p.add_argument(
        "--date", type=date.fromisoformat, default=None,
        help="单日增量模式（YYYY-MM-DD）",
    )

    p.add_argument(
        "--codes", nargs="+", default=None,
        help="只处理指定股票代码，不指定则全市场",
    )
    p.add_argument(
        "--patterns", nargs="+", default=None,
        help="指定 trigger 模式（BOF/PB/TST/CPB/BPB），不指定则全部",
    )
    p.add_argument(
        "--lookback", type=int, default=240,
        help="向前读取交易日数，默认 240",
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

    # 参数校验
    if args.date is None and args.start is None:
        print("错误：必须指定 --date（日增量）或 --start（全量构建）", file=sys.stderr)
        sys.exit(1)
    if args.date is not None and args.start is not None:
        print("错误：--date 与 --start 不能同时指定", file=sys.stderr)
        sys.exit(1)

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings
    from lq.malf.pipeline import list_trading_dates
    from lq.alpha.pas.pipeline import run_pas_build

    settings = default_settings()
    dbs = settings.databases

    print("=" * 60)
    print("PAS 信号批量构建")
    print("=" * 60)
    print(f"  market_base:  {dbs.market_base}")
    print(f"  malf:         {dbs.malf}")
    print(f"  research_lab: {dbs.research_lab}")

    # 确定日期列表
    if args.date is not None:
        signal_dates = [args.date]
        print(f"  模式:         日增量（{args.date}）")
    else:
        end = args.end or date.today()
        print(f"  模式:         全量（{args.start} → {end}）")
        print("  正在获取交易日列表...")
        signal_dates = list_trading_dates(dbs.market_base, args.start, end)
        print(f"  交易日数:     {len(signal_dates)}")

    print(f"  股票:         {args.codes or '全市场'}")
    print(f"  触发器:       {args.patterns or '全部五个'}")
    print(f"  lookback:     {args.lookback}")
    print(f"  续跑:         {'是' if args.resume else '否'}")
    print()

    if args.dry_run:
        print("[dry-run] 未执行任何写入。")
        return

    if not signal_dates:
        print("无交易日需要处理，退出。")
        return

    result = run_pas_build(
        market_base_path=dbs.market_base,
        malf_db_path=dbs.malf,
        research_lab_path=dbs.research_lab,
        signal_dates=signal_dates,
        codes=args.codes,
        patterns=args.patterns,
        lookback_days=args.lookback,
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
