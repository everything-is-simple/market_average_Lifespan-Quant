"""data.compute.pipeline — L1 → L2 后复权构建管道。

入口函数 build_l2_adjusted()：
  1. 从 raw_market.duckdb 读取 raw_stock_daily + raw_xdxr_event
  2. 对每只股票计算后复权因子，生成 stock_daily_adjusted
  3. 聚合周线 stock_weekly_adjusted、月线 stock_monthly_adjusted
  4. 写入 market_base.duckdb（幂等：先删后插指定窗口）
  5. 写 base_build_manifest 记录

增量语义：
  - 指定 window_start / window_end 时，只处理该窗口内有数据的股票
  - 对 xdxr 有新事件的股票，全量重算复权因子（非仅增量日期）
  - 幂等：同一股票 + 同一日期范围重复运行，结果相同
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Sequence
from uuid import uuid4

import duckdb
import pandas as pd

from lq.data.compute.adjust import apply_backward_adjustment
from lq.data.compute.aggregate import aggregate_to_weekly, aggregate_to_monthly


def _run_id() -> str:
    return f"l2-build-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


@dataclass
class L2BuildResult:
    """L2 构建结果摘要。"""

    run_id: str
    window_start: date | None
    window_end: date | None
    codes_processed: int = 0
    codes_failed: int = 0
    daily_rows: int = 0
    weekly_rows: int = 0
    monthly_rows: int = 0
    status: str = "completed"


def build_l2_adjusted(
    raw_market_path: Path,
    market_base_path: Path,
    window_start: date | None = None,
    window_end: date | None = None,
    codes: Sequence[str] | None = None,
    batch_size: int = 200,
    verbose: bool = False,
) -> L2BuildResult:
    """从 L1 构建 L2 后复权价格（日线 + 周线 + 月线）。

    参数：
        raw_market_path  — raw_market.duckdb 路径
        market_base_path — market_base.duckdb 路径
        window_start     — 增量窗口起始日（None = 全量）
        window_end       — 增量窗口终止日（None = 全量）
        codes            — 仅处理指定股票代码列表（None = 全市场）
        batch_size       — 每批处理的股票数量（控制内存）
        verbose          — 是否打印进度

    返回：
        L2BuildResult 构建摘要
    """
    run_id = _run_id()
    result = L2BuildResult(
        run_id=run_id,
        window_start=window_start,
        window_end=window_end,
    )

    with duckdb.connect(str(raw_market_path), read_only=True) as raw_conn:
        # 获取待处理股票代码列表
        if codes:
            all_codes = list(codes)
        else:
            all_codes = _get_codes_in_window(raw_conn, window_start, window_end)

    if not all_codes:
        if verbose:
            print("未发现任何待处理股票，跳过。")
        return result

    if verbose:
        print(f"待处理股票数：{len(all_codes)}")

    # 按 batch_size 分批处理，避免一次性加载全市场
    daily_frames: list[pd.DataFrame] = []
    weekly_frames: list[pd.DataFrame] = []
    monthly_frames: list[pd.DataFrame] = []

    with duckdb.connect(str(raw_market_path), read_only=True) as raw_conn:
        for batch_start in range(0, len(all_codes), batch_size):
            batch = all_codes[batch_start: batch_start + batch_size]

            if verbose:
                end_idx = min(batch_start + batch_size, len(all_codes))
                print(f"  处理 {batch_start+1}–{end_idx} / {len(all_codes)}...")

            for code in batch:
                try:
                    daily_df, weekly_df, monthly_df = _build_one_code(
                        raw_conn, code, window_start, window_end
                    )
                    if not daily_df.empty:
                        daily_frames.append(daily_df)
                    if not weekly_df.empty:
                        weekly_frames.append(weekly_df)
                    if not monthly_df.empty:
                        monthly_frames.append(monthly_df)
                    result.codes_processed += 1
                except Exception as exc:
                    result.codes_failed += 1
                    if verbose:
                        print(f"    [ERROR] {code}: {exc}")

    # 汇总写入 market_base.duckdb
    if daily_frames or weekly_frames or monthly_frames:
        daily_out   = pd.concat(daily_frames,   ignore_index=True) if daily_frames   else pd.DataFrame()
        weekly_out  = pd.concat(weekly_frames,  ignore_index=True) if weekly_frames  else pd.DataFrame()
        monthly_out = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()

        _write_to_market_base(
            market_base_path,
            daily_out, weekly_out, monthly_out,
            window_start, window_end, run_id,
        )

        result.daily_rows   = len(daily_out)
        result.weekly_rows  = len(weekly_out)
        result.monthly_rows = len(monthly_out)

    if result.codes_failed > 0 and result.codes_processed == 0:
        result.status = "failed"
    elif result.codes_failed > 0:
        result.status = "partial"

    _write_manifest(market_base_path, result)

    if verbose:
        print(
            f"完成。daily={result.daily_rows} 周={result.weekly_rows} "
            f"月={result.monthly_rows} 失败={result.codes_failed} run_id={run_id}"
        )

    return result


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _get_codes_in_window(
    raw_conn: duckdb.DuckDBPyConnection,
    window_start: date | None,
    window_end: date | None,
) -> list[str]:
    """从 raw_stock_daily 获取在指定窗口内有数据的全部股票代码。"""
    where_clauses = ["is_suspended = FALSE"]
    params: list[date] = []
    if window_start:
        where_clauses.append("trade_date >= ?")
        params.append(window_start)
    if window_end:
        where_clauses.append("trade_date <= ?")
        params.append(window_end)
    where = " AND ".join(where_clauses)
    rows = raw_conn.execute(
        f"SELECT DISTINCT code FROM raw_stock_daily WHERE {where} ORDER BY code",
        params,
    ).fetchall()
    return [r[0] for r in rows]


def _build_one_code(
    raw_conn: duckdb.DuckDBPyConnection,
    code: str,
    window_start: date | None,
    window_end: date | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """为单只股票计算后复权日线 + 周线 + 月线。

    注意：复权因子基于全量 xdxr 事件计算，不受 window 限制；
          最终写入 market_base 的行只包含窗口范围内的日期。
    """
    # 读取全量原始日线（计算复权因子需要全量历史 close）
    raw_bars: pd.DataFrame = raw_conn.execute(
        "SELECT code, trade_date, open, high, low, close, volume, amount, is_suspended "
        "FROM raw_stock_daily WHERE code = ? ORDER BY trade_date",
        [code],
    ).df()

    if raw_bars.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 读取全量 xdxr 事件（复权因子计算必须用全量）
    xdxr: pd.DataFrame = raw_conn.execute(
        "SELECT event_date, category, fenhong, peigujia, songzhuangu, peigu "
        "FROM raw_xdxr_event WHERE code = ? AND category = 1 ORDER BY event_date",
        [code],
    ).df()

    # 计算后复权日线（全量）
    daily_adj = apply_backward_adjustment(raw_bars, xdxr)
    if daily_adj.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 截取窗口范围（只写窗口内的数据，但复权因子基于全量计算）
    daily_window = daily_adj.copy()
    if window_start:
        daily_window = daily_window[daily_window["trade_date"] >= window_start]
    if window_end:
        daily_window = daily_window[daily_window["trade_date"] <= window_end]

    if daily_window.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 聚合（基于窗口内的日线）
    weekly  = aggregate_to_weekly(daily_window)
    monthly = aggregate_to_monthly(daily_window)

    return daily_window, weekly, monthly


def _write_to_market_base(
    market_base_path: Path,
    daily: pd.DataFrame,
    weekly: pd.DataFrame,
    monthly: pd.DataFrame,
    window_start: date | None,
    window_end: date | None,
    run_id: str,
) -> None:
    """将后复权数据写入 market_base.duckdb（幂等：先删后插）。"""
    with duckdb.connect(str(market_base_path)) as conn:
        # --- 日线 ---
        if not daily.empty:
            daily["build_run_id"] = run_id
            _delete_window(conn, "stock_daily_adjusted", "trade_date", window_start, window_end)
            conn.execute(
                "INSERT INTO stock_daily_adjusted "
                "SELECT code, trade_date, adjust_method, open, high, low, close, "
                "       volume, amount, adjustment_factor, build_run_id "
                "FROM daily"
            )

        # --- 周线 ---
        if not weekly.empty:
            weekly["build_run_id"] = run_id
            _delete_window(conn, "stock_weekly_adjusted", "trade_date", window_start, window_end)
            conn.execute(
                "INSERT INTO stock_weekly_adjusted "
                "SELECT code, trade_date, week_start_date, adjust_method, "
                "       open, high, low, close, volume, amount, build_run_id "
                "FROM weekly"
            )

        # --- 月线 ---
        if not monthly.empty:
            monthly["build_run_id"] = run_id
            _delete_window(conn, "stock_monthly_adjusted", "trade_date", window_start, window_end)
            conn.execute(
                "INSERT INTO stock_monthly_adjusted "
                "SELECT code, trade_date, month_start_date, adjust_method, "
                "       open, high, low, close, volume, amount, build_run_id "
                "FROM monthly"
            )


def _delete_window(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    date_col: str,
    window_start: date | None,
    window_end: date | None,
) -> None:
    """删除指定时间窗口内的已有记录（幂等保证）。"""
    clauses: list[str] = []
    params: list[date] = []
    if window_start:
        clauses.append(f"{date_col} >= ?")
        params.append(window_start)
    if window_end:
        clauses.append(f"{date_col} <= ?")
        params.append(window_end)
    if clauses:
        conn.execute(f"DELETE FROM {table} WHERE {' AND '.join(clauses)}", params)
    else:
        # 全量重建：清空全表
        conn.execute(f"DELETE FROM {table}")


def _write_manifest(market_base_path: Path, result: L2BuildResult) -> None:
    """写 base_build_manifest 记录。"""
    with duckdb.connect(str(market_base_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO base_build_manifest "
            "(run_id, source_name, dataset_name, window_start, window_end, status, rows_written) "
            "VALUES (?, 'tdx_local', 'l2_adjusted', ?, ?, ?, ?)",
            [
                result.run_id,
                result.window_start,
                result.window_end,
                result.status,
                result.daily_rows + result.weekly_rows + result.monthly_rows,
            ],
        )
