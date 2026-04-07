"""alpha/pas 模块 research_lab.duckdb schema 初始化。

research_lab 数据库是 alpha 模块的唯一正式落库目标。
本模块只建表，不写数据。所有写操作由对应 pipeline / runner 负责。

表域分组：
  1. PAS 注册表（run 追踪）: pas_registry_run
  2. PAS 信号表（正式信号）: pas_selected_trace / pas_formal_signal
  3. PAS 矩阵表（四格上下文验证）: pas_condition_matrix_run / pas_condition_matrix_cell
"""

from __future__ import annotations

from pathlib import Path

import duckdb


RESEARCH_LAB_SCHEMA_STATEMENTS = [
    # ---------------------------------------------------------------------------
    # 1. PAS 注册表：每次批量扫描的 run 元数据
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS pas_registry_run (
        run_id          VARCHAR PRIMARY KEY,
        trigger_pattern VARCHAR NOT NULL,          -- BOF / PB / BPB / TST / CPB
        window_start    DATE    NOT NULL,
        window_end      DATE    NOT NULL,
        candidate_count INTEGER NOT NULL DEFAULT 0, -- 本次扫描候选股数量
        signal_count    INTEGER NOT NULL DEFAULT 0, -- 触发信号数量
        status          VARCHAR NOT NULL,           -- running / completed / failed
        created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ---------------------------------------------------------------------------
    # 2. PAS 探测 trace：每次触发的详细检测记录（与 PasDetectTrace 对应）
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS pas_selected_trace (
        trace_id            VARCHAR PRIMARY KEY,
        run_id              VARCHAR NOT NULL,       -- 关联 pas_registry_run.run_id
        signal_id           VARCHAR NOT NULL,       -- 与 pas_formal_signal 对应
        code                VARCHAR NOT NULL,
        signal_date         DATE    NOT NULL,
        pattern             VARCHAR NOT NULL,       -- BOF / PB / BPB / TST / CPB
        triggered           BOOLEAN NOT NULL,
        strength            DOUBLE,
        skip_reason         VARCHAR,
        detect_reason       VARCHAR,
        history_days        INTEGER NOT NULL DEFAULT 0,
        min_history_days    INTEGER NOT NULL DEFAULT 0,
        pb_sequence_number  INTEGER,               -- PB 序号（第几个 PB）
        created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ---------------------------------------------------------------------------
    # 3. PAS 正式信号表：仅记录已触发的正式信号（与 PasSignal 合同对应）
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS pas_formal_signal (
        signal_id           VARCHAR PRIMARY KEY,
        run_id              VARCHAR NOT NULL,       -- 关联 pas_registry_run.run_id
        code                VARCHAR NOT NULL,
        signal_date         DATE    NOT NULL,
        pattern             VARCHAR NOT NULL,       -- BOF / PB / BPB / TST / CPB
        malf_context_4      VARCHAR NOT NULL,       -- BULL_MAINSTREAM / BULL_COUNTERTREND / ...
        strength            DOUBLE  NOT NULL,
        signal_low          DOUBLE  NOT NULL,       -- 信号最低价（止损参考）
        entry_ref_price     DOUBLE  NOT NULL,       -- 参考入场价
        pb_sequence_number  INTEGER,               -- PB 时有效，第几个 PB
        monthly_state       VARCHAR,               -- 触发时的 monthly_state
        weekly_flow         VARCHAR,               -- 触发时的 weekly_flow
        created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ---------------------------------------------------------------------------
    # 4. PAS 四格上下文矩阵验证 run 元数据
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS pas_condition_matrix_run (
        run_id          VARCHAR PRIMARY KEY,
        trigger_pattern VARCHAR NOT NULL,          -- 本次验证的 trigger
        window_start    DATE    NOT NULL,
        window_end      DATE    NOT NULL,
        total_signals   INTEGER NOT NULL DEFAULT 0,
        status          VARCHAR NOT NULL,
        created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ---------------------------------------------------------------------------
    # 5. PAS 四格上下文矩阵验证：每个格子的统计结果
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS pas_condition_matrix_cell (
        cell_id         VARCHAR PRIMARY KEY,
        run_id          VARCHAR NOT NULL,           -- 关联 pas_condition_matrix_run.run_id
        trigger_pattern VARCHAR NOT NULL,
        malf_context_4  VARCHAR NOT NULL,           -- BULL_MAINSTREAM / BULL_COUNTERTREND / BEAR_MAINSTREAM / BEAR_COUNTERTREND
        total_signals   INTEGER NOT NULL DEFAULT 0,
        win_count       INTEGER NOT NULL DEFAULT 0,
        lose_count      INTEGER NOT NULL DEFAULT 0,
        win_rate        DOUBLE,
        avg_return      DOUBLE,
        admission       VARCHAR,                    -- admitted / conditional / rejected / pending
        created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,

    # ---------------------------------------------------------------------------
    # 6. research_lab 构建 manifest 记录
    # ---------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS research_lab_build_manifest (
        run_id       VARCHAR PRIMARY KEY,
        module_name  VARCHAR NOT NULL,              -- alpha / structure / ...
        task_name    VARCHAR NOT NULL,
        window_start DATE,
        window_end   DATE,
        status       VARCHAR NOT NULL,
        rows_written BIGINT  NOT NULL DEFAULT 0,
        created_at   TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]


def bootstrap_research_lab(research_lab_path: Path) -> None:
    """初始化 research_lab.duckdb schema。

    使用 CREATE TABLE IF NOT EXISTS，安全地在已有库上重复调用（幂等）。
    """
    research_lab_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(research_lab_path)) as conn:
        for stmt in RESEARCH_LAB_SCHEMA_STATEMENTS:
            conn.execute(stmt)
