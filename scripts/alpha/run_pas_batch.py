"""PAS 批量信号扫描脚本。

从 market_base + malf 数据库读取数据，批量运行 PAS 探测器，
将触发信号写入 research_lab.duckdb。

用法：
    python scripts/alpha/run_pas_batch.py --signal-date 2024-06-30
    python scripts/alpha/run_pas_batch.py --signal-date 2024-06-30 --patterns BOF PB
    python scripts/alpha/run_pas_batch.py --signal-date 2024-06-30 --codes 000001.SZ 600519.SH
    python scripts/alpha/run_pas_batch.py --signal-date 2024-06-30 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PAS 批量信号扫描：market_base + malf → research_lab"
    )
    parser.add_argument(
        "--signal-date",
        type=date.fromisoformat,
        required=True,
        help="信号日期（T 日，YYYY-MM-DD）",
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=None,
        choices=["BOF", "PB", "BPB", "TST", "CPB"],
        help="指定 trigger 模式，默认全部（BOF PB TST CPB，BPB 默认拒绝准入）",
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="只扫描指定代码，不指定则扫描全市场在市股票",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=240,
        help="每只股票向前读取的交易日数（默认 240）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印参数，不执行扫描",
    )
    return parser.parse_args()


def _get_active_codes(market_base_path: Path, signal_date: date) -> list[str]:
    """从 market_base.stock_daily_adjusted 获取信号日有数据的全部股票代码。"""
    import duckdb
    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT code FROM stock_daily_adjusted "
            "WHERE trade_date = ? AND adjust_method = 'backward' "
            "ORDER BY code",
            [signal_date],
        ).fetchall()
    return [r[0] for r in rows]


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings
    from lq.alpha.pas.pipeline import run_pas_batch

    settings = default_settings()
    market_base_path  = settings.databases.market_base
    malf_db_path      = settings.databases.malf
    research_lab_path = settings.databases.research_lab

    print("=" * 60)
    print("PAS 批量信号扫描")
    print("=" * 60)
    print(f"  signal_date:   {args.signal_date}")
    print(f"  patterns:      {args.patterns or '全部（BOF PB TST CPB）'}")
    print(f"  market_base:   {market_base_path}")
    print(f"  malf:          {malf_db_path}")
    print(f"  research_lab:  {research_lab_path}")

    if args.dry_run:
        print("\n[dry-run] 未执行任何写入。")
        return

    # 确定候选股列表
    if args.codes:
        codes = args.codes
    else:
        codes = _get_active_codes(market_base_path, args.signal_date)

    if not codes:
        print(f"\n警告：信号日 {args.signal_date} 在 market_base 中无数据，请先运行 build_l2_adjusted.py。")
        return

    print(f"  候选股数：{len(codes)}")
    print()

    result = run_pas_batch(
        signal_date=args.signal_date,
        codes=codes,
        market_base_path=market_base_path,
        malf_db_path=malf_db_path,
        research_lab_path=research_lab_path,
        patterns=args.patterns,
        lookback_days=args.lookback_days,
        verbose=True,
    )

    print()
    print(f"状态:     完成")
    print(f"run_id:   {result.run_id}")
    print(f"扫描股票: {result.codes_scanned}")
    print(f"触发信号: {result.triggered_count}")
    print(f"分模式:   {result.pattern_counts}")


if __name__ == "__main__":
    main()
