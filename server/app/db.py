import json
import os
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .state import validate_transition

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://drop:drop@localhost:5432/drop")
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10, open=False)


def open_pool() -> None:
    pool.open(wait=True)
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE tasks
                ADD COLUMN IF NOT EXISTS ebpf_probes JSONB
                NOT NULL DEFAULT '["vfs_read"]'::jsonb
            """
        )
        cur.execute(
            """
            ALTER TABLE profiling_sessions
                ADD COLUMN IF NOT EXISTS ebpf_probes JSONB
                NOT NULL DEFAULT '["vfs_read"]'::jsonb
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS attribution_runs (
                id UUID PRIMARY KEY,
                target_type TEXT NOT NULL CHECK (
                    target_type IN ('TASK', 'SEGMENT')
                ),
                target_id UUID NOT NULL,
                session_id UUID REFERENCES profiling_sessions(id)
                    ON DELETE CASCADE,
                baseline_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                trigger TEXT NOT NULL CHECK (
                    trigger IN ('AUTO', 'MANUAL')
                ),
                status TEXT NOT NULL CHECK (
                    status IN (
                        'RUNNING', 'COMPLETED', 'FAILED',
                        'INSUFFICIENT_DATA'
                    )
                ),
                mode TEXT NOT NULL CHECK (
                    mode IN ('DETERMINISTIC', 'LLM')
                ),
                model TEXT,
                anomaly JSONB NOT NULL DEFAULT '{}'::jsonb,
                comparison JSONB NOT NULL DEFAULT '{}'::jsonb,
                report JSONB,
                tool_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                UNIQUE (target_type, target_id, trigger)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_attribution_runs_session_created
                ON attribution_runs(session_id, created_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_attribution_runs_target
                ON attribution_runs(
                    target_type, target_id, created_at DESC
                )
            """
        )
        conn.commit()


def close_pool() -> None:
    pool.close()


@contextmanager
def connection():
    with pool.connection() as conn:
        conn.row_factory = dict_row
        yield conn


def transition_task(conn, task_id: str, target: str, reason: str, result=None) -> dict:
    with conn.cursor() as cur:
        task = cur.execute(
            "SELECT * FROM tasks WHERE id = %s FOR UPDATE", (task_id,)
        ).fetchone()
        if task is None:
            raise LookupError("task not found")
        validate_transition(task["status"], target, reason)
        cur.execute(
            """
            UPDATE tasks
               SET status = %s, status_reason = %s,
                   result = COALESCE(%s::jsonb, result), updated_at = NOW()
             WHERE id = %s
            """,
            (target, reason.strip(), json.dumps(result) if result is not None else None, task_id),
        )
        cur.execute(
            "INSERT INTO task_events(task_id, from_status, to_status, reason) VALUES (%s, %s, %s, %s)",
            (task_id, task["status"], target, reason.strip()),
        )
        return cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
