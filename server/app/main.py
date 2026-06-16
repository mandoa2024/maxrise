import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .db import close_pool, connection, open_pool, transition_task
from .models import Heartbeat, TaskCreate, TaskStatusUpdate, TaskUpload

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("minidrop.server")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8090")


def serialize(row):
    if row is None:
        return None
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }


async def offline_monitor() -> None:
    while True:
        try:
            with connection() as conn, conn.cursor() as cur:
                offline = cur.execute(
                    """
                    UPDATE agents SET status = 'OFFLINE', updated_at = NOW()
                     WHERE status = 'ONLINE'
                       AND last_heartbeat_at < NOW() - INTERVAL '30 seconds'
                    RETURNING id
                    """
                ).fetchall()
                for row in offline:
                    cur.execute(
                        "INSERT INTO agent_audit_logs(agent_id, event, reason) VALUES (%s, 'OFFLINE', %s)",
                        (row["id"], "no heartbeat for more than 30 seconds"),
                    )
                conn.commit()
        except Exception:
            log.exception('{"event":"offline_monitor_failed"}')
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    open_pool()
    monitor = asyncio.create_task(offline_monitor())
    yield
    monitor.cancel()
    close_pool()


app = FastAPI(title="Mini-Drop Server", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/v1/agents/heartbeat")
def heartbeat(body: Heartbeat):
    with connection() as conn, conn.cursor() as cur:
        existing = cur.execute("SELECT status FROM agents WHERE id = %s", (body.agent_id,)).fetchone()
        event = "ONLINE" if existing is None else "RECOVERED" if existing["status"] == "OFFLINE" else None
        cur.execute(
            """
            INSERT INTO agents(id, name, hostname, status, last_heartbeat_at)
            VALUES (%s, %s, %s, 'ONLINE', NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, hostname = EXCLUDED.hostname,
                status = 'ONLINE', last_heartbeat_at = NOW(), updated_at = NOW()
            """,
            (body.agent_id, body.name, body.hostname),
        )
        if event:
            reason = "agent registered" if event == "ONLINE" else "heartbeat resumed"
            cur.execute(
                "INSERT INTO agent_audit_logs(agent_id, event, reason) VALUES (%s, %s, %s)",
                (body.agent_id, event, reason),
            )
        conn.commit()
    return {"status": "ONLINE"}


@app.get("/api/v1/agents")
def list_agents():
    with connection() as conn, conn.cursor() as cur:
        rows = cur.execute("SELECT * FROM agents ORDER BY created_at").fetchall()
    return [serialize(row) for row in rows]


@app.get("/api/v1/agents/audit-logs")
def list_agent_audits():
    with connection() as conn, conn.cursor() as cur:
        rows = cur.execute("SELECT * FROM agent_audit_logs ORDER BY created_at DESC LIMIT 100").fetchall()
    return [serialize(row) for row in rows]


@app.post("/api/v1/tasks", status_code=201)
def create_task(body: TaskCreate):
    task_id = str(uuid.uuid4())
    reason = "task accepted by server"
    with connection() as conn, conn.cursor() as cur:
        agent = cur.execute("SELECT id FROM agents WHERE id = %s", (body.agent_id,)).fetchone()
        if agent is None:
            raise HTTPException(404, "agent not found")
        cur.execute(
            """
            INSERT INTO tasks(id, agent_id, pid, duration_seconds, sample_rate, collector, status, status_reason)
            VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s)
            """,
            (task_id, body.agent_id, body.pid, body.duration_seconds, body.sample_rate, body.collector, reason),
        )
        cur.execute(
            "INSERT INTO task_events(task_id, from_status, to_status, reason) VALUES (%s, NULL, 'PENDING', %s)",
            (task_id, reason),
        )
        conn.commit()
        task = cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
    return serialize(task)


@app.get("/api/v1/tasks")
def list_tasks():
    with connection() as conn, conn.cursor() as cur:
        rows = cur.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
    return [serialize(row) for row in rows]


@app.get("/api/v1/tasks/{task_id}")
def get_task(task_id: str):
    with connection() as conn, conn.cursor() as cur:
        task = cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
        if task is None:
            raise HTTPException(404, "task not found")
        events = cur.execute(
            "SELECT * FROM task_events WHERE task_id = %s ORDER BY created_at", (task_id,)
        ).fetchall()
    data = serialize(task)
    data["events"] = [serialize(event) for event in events]
    return data


@app.post("/api/v1/agent/{agent_id}/tasks/next")
def claim_task(agent_id: str, response: Response):
    with connection() as conn, conn.cursor() as cur:
        task = cur.execute(
            """
            SELECT * FROM tasks
             WHERE agent_id = %s AND status = 'PENDING'
             ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
            """,
            (agent_id,),
        ).fetchone()
        if task is None:
            response.status_code = 204
            return None
        task = transition_task(conn, str(task["id"]), "RUNNING", "agent claimed task")
        conn.commit()
    return serialize(task)


@app.post("/api/v1/agent/tasks/{task_id}/status")
def update_task_status(task_id: str, body: TaskStatusUpdate):
    try:
        with connection() as conn:
            task = transition_task(conn, task_id, body.status, body.reason)
            conn.commit()
        return serialize(task)
    except (ValueError, LookupError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/v1/agent/tasks/{task_id}/upload")
async def upload_task(task_id: str, body: TaskUpload):
    try:
        with connection() as conn, conn.cursor() as cur:
            task = cur.execute("SELECT status FROM tasks WHERE id = %s", (task_id,)).fetchone()
            if task is None:
                raise LookupError("task not found")
            if task["status"] == "RUNNING":
                transition_task(conn, task_id, "UPLOADING", body.reason)
            elif task["status"] != "UPLOADING":
                raise ValueError(f"cannot upload task in {task['status']}")
            cur.execute(
                "UPDATE tasks SET raw_data = %s, performance_data = %s::jsonb WHERE id = %s",
                (body.raw_data, json.dumps(body.performance_data), task_id),
            )
            conn.commit()

        async with httpx.AsyncClient(timeout=30) as client:
            analysis = await client.post(
                f"{ANALYZER_URL}/analyze",
                json={
                    "task_id": task_id,
                    "collapsed_stacks": body.raw_data,
                    "performance_data": body.performance_data,
                },
            )
            analysis.raise_for_status()
        with connection() as conn:
            task = transition_task(conn, task_id, "DONE", "analysis completed", analysis.json())
            conn.commit()
        return serialize(task)
    except (ValueError, LookupError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        log.exception('{"event":"analysis_failed","task_id":"%s"}', task_id)
        with connection() as conn:
            try:
                transition_task(conn, task_id, "FAILED", f"analysis failed: {type(exc).__name__}")
                conn.commit()
            except Exception:
                conn.rollback()
        raise HTTPException(502, "analysis failed") from exc
