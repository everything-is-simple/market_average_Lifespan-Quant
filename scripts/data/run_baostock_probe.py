"""BaoStock 第二校准源审计探针脚本。

对比本地 gbbq 计算的 adjustment_factor 与 BaoStock adj_factor 的差异，
结果保存到 H:\\Lifespan-temp 目录，不写入正式数据库。

用法：
    python scripts/data/run_baostock_probe.py --codes 000001.SZ 600519.SH
    python scripts/data/run_baostock_probe.py --window-start 2024-01-01 --window-end 2024-12-31
    python scripts/data/run_baostock_probe.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BaoStock 复权因子双源差异审计探针"
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="审计指定代码（如 000001.SZ），不指定则抽样 50 只",
    )
    parser.add_argument(
        "--window-start",
        type=date.fromisoformat,
        default=None,
        help="审计窗口起始日（YYYY-MM-DD）",
    )
    parser.add_argument(
        "--window-end",
        type=date.fromisoformat,
        default=None,
        help="审计窗口终止日（YYYY-MM-DD）",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
        help="当 --codes 未指定时，随机抽样的股票数（默认 50）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="结果输出目录（默认 H:\\Lifespan-temp\\baostock_probe）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印参数，不执行审计",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "src"))

    from lq.core.paths import default_settings
    from lq.data.audit.baostock_probe import probe_adjustment_factor_diff, summarize_diff_report
    from lq.data.providers.baostock import BaoStockProvider

    settings = default_settings()
    market_base_path = settings.databases.market_base

    output_dir = Path(args.output_dir) if args.output_dir else (
        settings.temp_root / "baostock_probe"
    )

    print("=" * 60)
    print("BaoStock 复权因子双源差异审计")
    print("=" * 60)
    print(f"  market_base: {market_base_path}")
    print(f"  output_dir:  {output_dir}")
    print(f"  window:      {args.window_start} → {args.window_end}")

    if args.dry_run:
        print("\n[dry-run] 未执行任何操作。")
        return

    # 确定审计股票列表
    if args.codes:
        codes = args.codes
    else:
        import duckdb
        import random
        with duckdb.connect(str(market_base_path), read_only=True) as conn:
            all_codes = [r[0] for r in conn.execute(
                "SELECT DISTINCT code FROM stock_daily_adjusted ORDER BY code"
            ).fetchall()]
        random.seed(42)
        codes = random.sample(all_codes, min(args.sample_size, len(all_codes)))

    print(f"  审计股票数： {len(codes)}")
    print()

    # 初始化 BaoStock provider
    provider = BaoStockProvider()

    # 运行差异探针
    diff_df = probe_adjustment_factor_diff(
        codes=codes,
        market_base_path=market_base_path,
        baostock_provider=provider,
        window_start=args.window_start,
        window_end=args.window_end,
    )

    # 输出汇总报告
    summary = summarize_diff_report(diff_df)
    print("--- 审计汇总 ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # 保存差异明细到 temp 目录（不写正式库）
    output_dir.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    out_path = output_dir / f"adj_factor_diff_{today_str}.csv"

    if not diff_df.empty:
        diff_df.to_csv(out_path, index=False)
        print(f"\n差异明细已保存到：{out_path}")
    else:
        print("\n无差异记录（本地因子与 BaoStock 一致）。")

    # 写汇总文本
    summary_path = output_dir / f"adj_factor_diff_summary_{today_str}.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")
    print(f"汇总报告已保存到：{summary_path}")


if __name__ == "__main__":
    main()
