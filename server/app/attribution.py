import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from .db import connection


log = logging.getLogger("minidrop.attribution")

ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8090")
ATTRIBUTION_ENABLED = (
    os.getenv("ATTRIBUTION_ENABLED", "true").lower() == "true"
)
MIN_BASELINE_SEGMENTS = int(
    os.getenv("ATTRIBUTION_MIN_BASELINE_SEGMENTS", "3")
)
BASELINE_SEGMENTS = int(os.getenv("ATTRIBUTION_BASELINE_SEGMENTS", "5"))
CPU_DELTA_THRESHOLD_PP = float(
    os.getenv("ATTRIBUTION_CPU_DELTA_PP", "12")
)
MEMORY_RATIO_THRESHOLD = float(
    os.getenv("ATTRIBUTION_MEMORY_RATIO", "1.3")
)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://api.openai.com/v1"
).rstrip("/")
OPENAI_REASONING_EFFORT = os.getenv(
    "OPENAI_REASONING_EFFORT", "medium"
)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
).rstrip("/")
DEEPSEEK_REASONING_EFFORT = os.getenv(
    "DEEPSEEK_REASONING_EFFORT", "medium"
)
DEEPSEEK_THINKING = (
    os.getenv("DEEPSEEK_THINKING", "true").lower() == "true"
)
MAX_TOOL_CALLS = int(os.getenv("ATTRIBUTION_MAX_TOOL_CALLS", "8"))

_background_tasks: set[asyncio.Task] = set()


class AttributionFinding(BaseModel):
    category: Literal[
        "CPU_HOTSPOT_REGRESSION",
        "CALL_PATH_REGRESSION",
        "MEMORY_REGRESSION",
        "DATA_QUALITY",
    ]
    subject: str = Field(min_length=1, max_length=200)
    claim: str = Field(min_length=1, max_length=600)
    impact: Literal["HIGH", "MEDIUM", "LOW"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    evidence_ids: list[str] = Field(min_length=1, max_length=6)
    recommendation: str = Field(min_length=1, max_length=600)


class AttributionReport(BaseModel):
    status: Literal["SUPPORTED", "INSUFFICIENT_DATA"]
    summary: str = Field(min_length=1, max_length=1000)
    findings: list[AttributionFinding] = Field(max_length=5)
    limitations: list[str] = Field(max_length=8)


REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["SUPPORTED", "INSUFFICIENT_DATA"],
        },
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "CPU_HOTSPOT_REGRESSION",
                            "CALL_PATH_REGRESSION",
                            "MEMORY_REGRESSION",
                            "DATA_QUALITY",
                        ],
                    },
                    "subject": {"type": "string"},
                    "claim": {"type": "string"},
                    "impact": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW"],
                    },
                    "evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 6,
                        "items": {"type": "string"},
                    },
                    "recommendation": {"type": "string"},
                },
                "required": [
                    "category",
                    "subject",
                    "claim",
                    "impact",
                    "confidence",
                    "evidence_ids",
                    "recommendation",
                ],
                "additionalProperties": False,
            },
        },
        "limitations": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string"},
        },
    },
    "required": ["status", "summary", "findings", "limitations"],
    "additionalProperties": False,
}


TOOLS = [
    {
        "type": "function",
        "name": "get_profile_metadata",
        "description": (
            "Return immutable collection metadata and sample counts for the "
            "target and automatically selected baseline. Call this before "
            "making data-quality claims."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_profile_summary",
        "description": (
            "Return deterministic self-CPU function deltas between target "
            "and baseline. Positive delta_pp means the function consumes a "
            "larger share in the target."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                }
            },
            "required": ["limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_stack_evidence",
        "description": (
            "Inspect one stack evidence item returned by the comparison. "
            "Use it to verify which complete call path grew."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "evidence_id": {"type": "string"},
            },
            "required": ["evidence_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_metrics",
        "description": (
            "Return deterministic memory metric deltas. Do not infer metric "
            "changes without calling this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def attribution_config() -> dict:
    api_key, model = selected_llm_credentials()
    return {
        "enabled": ATTRIBUTION_ENABLED,
        "provider": LLM_PROVIDER,
        "llm_configured": bool(api_key),
        "model": model if api_key else None,
        "min_baseline_segments": MIN_BASELINE_SEGMENTS,
        "baseline_segments": BASELINE_SEGMENTS,
        "cpu_delta_threshold_pp": CPU_DELTA_THRESHOLD_PP,
        "memory_ratio_threshold": MEMORY_RATIO_THRESHOLD,
    }


def selected_llm_credentials() -> tuple[str, str]:
    if LLM_PROVIDER == "deepseek":
        return DEEPSEEK_API_KEY, DEEPSEEK_MODEL
    if LLM_PROVIDER == "openai":
        return OPENAI_API_KEY, OPENAI_MODEL
    return "", ""


def schedule_attribution(coroutine) -> None:
    if not ATTRIBUTION_ENABLED:
        return
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_finish_background_task)


def _finish_background_task(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    try:
        task.result()
    except Exception:
        log.exception('{"event":"automatic_attribution_failed"}')


def aggregate_metrics(rows: list[dict]) -> dict:
    memory_items = [
        (row.get("performance_data") or {}).get("memory") or {}
        for row in rows
    ]

    def average(key):
        values = [
            item[key]
            for item in memory_items
            if isinstance(item.get(key), (int, float))
        ]
        return round(sum(values) / len(values), 3) if values else None

    return {
        "memory": {
            "rss_kb": average("rss_kb"),
            "peak_rss_kb": average("peak_rss_kb"),
            "vms_kb": average("vms_kb"),
        }
    }


async def evaluate_segment(
    segment_id: str, trigger: str = "AUTO", force: bool = False
) -> dict | None:
    with connection() as conn, conn.cursor() as cur:
        target = cur.execute(
            """
            SELECT ps.*, s.sample_rate, s.segment_seconds, s.ebpf_probes
              FROM profile_segments ps
              JOIN profiling_sessions s ON s.id = ps.session_id
             WHERE ps.id = %s
            """,
            (segment_id,),
        ).fetchone()
        if target is None:
            raise LookupError("profile segment not found")
        baselines = cur.execute(
            """
            SELECT id, raw_data, performance_data, start_at, end_at
              FROM profile_segments
             WHERE session_id = %s AND start_at < %s
             ORDER BY start_at DESC
             LIMIT %s
            """,
            (
                target["session_id"],
                target["start_at"],
                BASELINE_SEGMENTS,
            ),
        ).fetchall()

    if len(baselines) < MIN_BASELINE_SEGMENTS:
        if trigger == "MANUAL":
            return create_insufficient_run(
                "SEGMENT",
                segment_id,
                str(target["session_id"]),
                [str(row["id"]) for row in baselines],
                trigger,
                (
                    f"baseline requires {MIN_BASELINE_SEGMENTS} segments; "
                    f"found {len(baselines)}"
                ),
            )
        return None

    metadata = {
        "target_type": "SEGMENT",
        "collector": target["collector"],
        "pid": target["pid"],
        "sample_rate_hz": target["sample_rate"],
        "segment_seconds": target["segment_seconds"],
        "target_window": {
            "start_at": target["start_at"].isoformat(),
            "end_at": target["end_at"].isoformat(),
        },
        "baseline_windows": [
            {
                "start_at": row["start_at"].isoformat(),
                "end_at": row["end_at"].isoformat(),
            }
            for row in reversed(baselines)
        ],
        "baseline_count": len(baselines),
    }
    return await compare_and_attribute(
        target_type="SEGMENT",
        target_id=segment_id,
        session_id=str(target["session_id"]),
        baseline_ids=[str(row["id"]) for row in baselines],
        target_stacks=target["raw_data"],
        baseline_stacks="\n".join(
            row["raw_data"] for row in baselines
        ),
        target_metrics=target["performance_data"] or {},
        baseline_metrics=aggregate_metrics(baselines),
        metadata=metadata,
        trigger=trigger,
        force=force,
    )


async def evaluate_task(
    task_id: str, trigger: str = "AUTO", force: bool = False
) -> dict | None:
    with connection() as conn, conn.cursor() as cur:
        target = cur.execute(
            "SELECT * FROM tasks WHERE id = %s", (task_id,)
        ).fetchone()
        if target is None:
            raise LookupError("task not found")
        baseline = cur.execute(
            """
            SELECT * FROM tasks
             WHERE id <> %s
               AND agent_id = %s
               AND pid = %s
               AND collector = %s
               AND status = 'DONE'
               AND raw_data IS NOT NULL
               AND created_at < %s
             ORDER BY created_at DESC
             LIMIT 1
            """,
            (
                task_id,
                target["agent_id"],
                target["pid"],
                target["collector"],
                target["created_at"],
            ),
        ).fetchone()
    if baseline is None:
        if trigger == "MANUAL":
            return create_insufficient_run(
                "TASK",
                task_id,
                None,
                [],
                trigger,
                "no comparable completed task exists",
            )
        return None
    if target["status"] != "DONE" or not target.get("raw_data"):
        if trigger == "MANUAL":
            return create_insufficient_run(
                "TASK",
                task_id,
                None,
                [str(baseline["id"])],
                trigger,
                "target task has not completed profiling analysis",
            )
        return None

    metadata = {
        "target_type": "TASK",
        "collector": target["collector"],
        "pid": target["pid"],
        "sample_rate_hz": target["sample_rate"],
        "duration_seconds": target["duration_seconds"],
        "target_created_at": target["created_at"].isoformat(),
        "baseline_created_at": baseline["created_at"].isoformat(),
        "baseline_count": 1,
    }
    return await compare_and_attribute(
        target_type="TASK",
        target_id=task_id,
        session_id=None,
        baseline_ids=[str(baseline["id"])],
        target_stacks=target["raw_data"],
        baseline_stacks=baseline["raw_data"],
        target_metrics=target["performance_data"] or {},
        baseline_metrics=baseline["performance_data"] or {},
        metadata=metadata,
        trigger=trigger,
        force=force,
    )


async def compare_and_attribute(
    *,
    target_type: str,
    target_id: str,
    session_id: str | None,
    baseline_ids: list[str],
    target_stacks: str,
    baseline_stacks: str,
    target_metrics: dict,
    baseline_metrics: dict,
    metadata: dict,
    trigger: str,
    force: bool,
) -> dict | None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{ANALYZER_URL}/compare",
            json={
                "target_stacks": target_stacks,
                "baseline_stacks": baseline_stacks,
                "target_metrics": target_metrics,
                "baseline_metrics": baseline_metrics,
                "top_k": 20,
            },
        )
        response.raise_for_status()
    comparison = response.json()
    anomaly = detect_anomaly(comparison)
    if not anomaly["detected"] and not force:
        return None

    run = reserve_run(
        target_type,
        target_id,
        session_id,
        baseline_ids,
        trigger,
        anomaly,
        comparison,
    )
    if run is None:
        return latest_run(target_type, target_id, trigger)

    try:
        api_key, configured_model = selected_llm_credentials()
        if api_key:
            try:
                report, trace, request_id = await generate_llm_report(
                    str(run["id"]), metadata, comparison
                )
                mode = "LLM"
                model = configured_model
                if request_id:
                    trace.append(
                        {
                            "type": "llm_request",
                            "provider": LLM_PROVIDER,
                            "request_id": request_id,
                        }
                    )
            except Exception as exc:
                log.exception(
                    '{"event":"llm_attribution_fallback","run_id":"%s"}',
                    run["id"],
                )
                report = deterministic_report(comparison, anomaly)
                report["limitations"].append(
                    f"{LLM_PROVIDER} 调用失败，已降级为确定性差分报告。"
                )
                trace = [
                    {
                        "type": "llm_error",
                        "error": type(exc).__name__,
                    }
                ]
                mode = "DETERMINISTIC"
                model = None
        else:
            report = deterministic_report(comparison, anomaly)
            trace = []
            mode = "DETERMINISTIC"
            model = None
        report = verify_and_enrich_report(
            report,
            comparison,
            metadata,
            trace if mode == "LLM" else None,
        )
        return complete_run(
            str(run["id"]), report, trace, mode, model
        )
    except Exception as exc:
        log.exception(
            '{"event":"attribution_failed","run_id":"%s"}', run["id"]
        )
        return fail_run(str(run["id"]), str(exc))


def detect_anomaly(comparison: dict) -> dict:
    top_function = next(
        iter(comparison.get("function_deltas") or []), None
    )
    top_stack = next(iter(comparison.get("stack_deltas") or []), None)
    memory = max(
        (
            item
            for item in comparison.get("metric_deltas", [])
            if item["metric"] in {"rss_kb", "peak_rss_kb"}
            and item.get("ratio") is not None
        ),
        key=lambda item: item["ratio"],
        default=None,
    )
    cpu_detected = bool(
        top_function
        and top_function["delta_pp"] >= CPU_DELTA_THRESHOLD_PP
    )
    stack_detected = bool(
        top_stack and top_stack["delta_pp"] >= CPU_DELTA_THRESHOLD_PP
    )
    memory_detected = bool(
        memory and memory["ratio"] >= MEMORY_RATIO_THRESHOLD
    )
    return {
        "detected": cpu_detected or stack_detected or memory_detected,
        "cpu_detected": cpu_detected,
        "stack_detected": stack_detected,
        "memory_detected": memory_detected,
        "cpu_threshold_pp": CPU_DELTA_THRESHOLD_PP,
        "memory_ratio_threshold": MEMORY_RATIO_THRESHOLD,
        "top_function": top_function,
        "top_stack": top_stack,
        "top_memory_metric": memory,
    }


def reserve_run(
    target_type,
    target_id,
    session_id,
    baseline_ids,
    trigger,
    anomaly,
    comparison,
):
    run_id = str(uuid.uuid4())
    api_key, configured_model = selected_llm_credentials()
    mode = "LLM" if api_key else "DETERMINISTIC"
    with connection() as conn, conn.cursor() as cur:
        row = cur.execute(
            """
            INSERT INTO attribution_runs(
                id, target_type, target_id, session_id, baseline_ids,
                trigger, status, mode, model, anomaly, comparison
            )
            VALUES (
                %s, %s, %s, %s, %s::jsonb, %s, 'RUNNING', %s, %s,
                %s::jsonb, %s::jsonb
            )
            ON CONFLICT (target_type, target_id, trigger) DO NOTHING
            RETURNING *
            """,
            (
                run_id,
                target_type,
                target_id,
                session_id,
                json.dumps(baseline_ids),
                trigger,
                mode,
                configured_model if api_key else None,
                json.dumps(anomaly),
                json.dumps(comparison),
            ),
        ).fetchone()
        conn.commit()
    return row


def create_insufficient_run(
    target_type,
    target_id,
    session_id,
    baseline_ids,
    trigger,
    reason,
):
    report = {
        "status": "INSUFFICIENT_DATA",
        "summary": "当前数据不足以生成可验证的归因结论。",
        "findings": [],
        "limitations": [reason],
    }
    run_id = str(uuid.uuid4())
    with connection() as conn, conn.cursor() as cur:
        row = cur.execute(
            """
            INSERT INTO attribution_runs(
                id, target_type, target_id, session_id, baseline_ids,
                trigger, status, mode, report, completed_at
            )
            VALUES (
                %s, %s, %s, %s, %s::jsonb, %s,
                'INSUFFICIENT_DATA', 'DETERMINISTIC', %s::jsonb, NOW()
            )
            ON CONFLICT (target_type, target_id, trigger)
            DO UPDATE SET report = EXCLUDED.report,
                          status = EXCLUDED.status,
                          completed_at = NOW()
            RETURNING *
            """,
            (
                run_id,
                target_type,
                target_id,
                session_id,
                json.dumps(baseline_ids),
                trigger,
                json.dumps(report),
            ),
        ).fetchone()
        conn.commit()
    return serialize_row(row)


def deterministic_report(comparison: dict, anomaly: dict) -> dict:
    findings = []
    top_function = anomaly.get("top_function")
    if anomaly.get("cpu_detected") and top_function:
        stack = next(
            (
                item
                for item in comparison.get("stack_deltas", [])
                if top_function["function"] in item["frames"]
            ),
            None,
        )
        evidence_ids = [top_function["evidence_id"]]
        if stack:
            evidence_ids.append(stack["evidence_id"])
        findings.append(
            {
                "category": "CPU_HOTSPOT_REGRESSION",
                "subject": top_function["function"],
                "claim": (
                    f"{top_function['function']} 的 self CPU 样本占比"
                    "相对 baseline 显著上升。"
                ),
                "impact": (
                    "HIGH"
                    if top_function["delta_pp"] >= 25
                    else "MEDIUM"
                ),
                "confidence": "HIGH",
                "evidence_ids": evidence_ids,
                "recommendation": (
                    "检查该函数及其增长调用路径上的近期代码、输入规模"
                    "和执行次数变化。"
                ),
            }
        )
    top_stack = anomaly.get("top_stack")
    if (
        anomaly.get("stack_detected")
        and top_stack
        and not anomaly.get("cpu_detected")
    ):
        subject = top_stack["frames"][-1]
        findings.append(
            {
                "category": "CALL_PATH_REGRESSION",
                "subject": subject,
                "claim": (
                    f"以 {subject} 结尾的完整调用路径在目标 profile "
                    "中的样本占比显著上升。"
                ),
                "impact": (
                    "HIGH"
                    if top_stack["delta_pp"] >= 25
                    else "MEDIUM"
                ),
                "confidence": "HIGH",
                "evidence_ids": [top_stack["evidence_id"]],
                "recommendation": (
                    "检查该调用路径的触发频率、上游调用方和对应系统事件。"
                ),
            }
        )
    memory = anomaly.get("top_memory_metric")
    if anomaly.get("memory_detected") and memory:
        findings.append(
            {
                "category": "MEMORY_REGRESSION",
                "subject": memory["metric"],
                "claim": "目标窗口的内存指标显著高于 baseline。",
                "impact": "HIGH" if memory["ratio"] >= 2 else "MEDIUM",
                "confidence": "MEDIUM",
                "evidence_ids": [memory["evidence_id"]],
                "recommendation": (
                    "结合对象分配、缓存大小或请求并发进一步检查内存增长。"
                ),
            }
        )
    return {
        "status": "SUPPORTED" if findings else "INSUFFICIENT_DATA",
        "summary": (
            "检测到相对历史 baseline 的性能结构变化，结论基于"
            "确定性采样差分。"
            if findings
            else "未获得足够证据支持具体归因。"
        ),
        "findings": findings,
        "limitations": (
            [
                f"未配置 {LLM_PROVIDER} API Key，"
                "当前报告为确定性差分摘要。"
            ]
            if not selected_llm_credentials()[0]
            else []
        ),
    }


async def generate_llm_report(
    run_id: str, metadata: dict, comparison: dict
) -> tuple[dict, list[dict], str | None]:
    if LLM_PROVIDER == "deepseek":
        return await generate_deepseek_report(
            run_id, metadata, comparison
        )
    if LLM_PROVIDER == "openai":
        return await generate_openai_report(run_id, metadata, comparison)
    raise ValueError(f"unsupported LLM provider: {LLM_PROVIDER}")


def attribution_instructions() -> str:
    return (
        "你是性能回归归因代理。只能依据本次运行提供的函数工具取证，"
        "禁止使用外部知识补全事实。先调用 compare_profile_summary；"
        "需要路径证据时调用 inspect_stack_evidence；涉及内存时调用"
        " compare_metrics；涉及可比性时调用 get_profile_metadata。"
        "每条 finding 必须引用工具实际返回的 evidence_id。"
        "subject 必须原样使用证据中的 function、完整调用路径末帧或"
        " metric 字段，不能改写。"
        "claim 只描述证据直接支持的现象，不得声称已定位代码 bug、"
        "提交或业务原因。证据不足时返回 INSUFFICIENT_DATA。"
    )


async def generate_openai_report(
    run_id: str, metadata: dict, comparison: dict
) -> tuple[dict, list[dict], str | None]:
    payload = {
        "model": OPENAI_MODEL,
        "instructions": attribution_instructions(),
        "input": (
            "自动异常检测已触发。请调查本次 profile 相对自动 baseline "
            "的变化并生成可验证归因报告。除这句话外没有提供任何"
            "性能事实；所有事实必须通过工具取得。"
        ),
        "tools": TOOLS,
        "tool_choice": "required",
        "parallel_tool_calls": False,
        "reasoning": {"effort": OPENAI_REASONING_EFFORT},
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "attribution_report",
                "strict": True,
                "schema": REPORT_SCHEMA,
            },
        },
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "X-Client-Request-Id": run_id,
    }
    trace = []
    request_id = None
    call_count = 0
    async with httpx.AsyncClient(timeout=90) as client:
        while True:
            response = await client.post(
                f"{OPENAI_BASE_URL}/responses",
                headers=headers,
                json=payload,
            )
            request_id = response.headers.get("x-request-id") or request_id
            response.raise_for_status()
            body = response.json()
            calls = [
                item
                for item in body.get("output", [])
                if item.get("type") == "function_call"
            ]
            if not calls:
                return (
                    AttributionReport.model_validate_json(
                        extract_output_text(body)
                    ).model_dump(),
                    trace,
                    request_id,
                )

            outputs = []
            for call in calls:
                call_count += 1
                if call_count > MAX_TOOL_CALLS:
                    raise RuntimeError("LLM exceeded tool call budget")
                arguments = json.loads(call.get("arguments") or "{}")
                result = execute_tool(
                    call["name"], arguments, metadata, comparison
                )
                trace.append(
                    {
                        "tool": call["name"],
                        "arguments": arguments,
                        "result": result,
                    }
                )
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(
                            result, ensure_ascii=False
                        ),
                    }
                )
            payload = {
                "model": OPENAI_MODEL,
                "previous_response_id": body["id"],
                "input": outputs,
                "tools": TOOLS,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "reasoning": {"effort": OPENAI_REASONING_EFFORT},
                "text": {
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "attribution_report",
                        "strict": True,
                        "schema": REPORT_SCHEMA,
                    },
                },
            }


def deepseek_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        for tool in TOOLS
    ]


def deepseek_tool_choice(first_turn: bool) -> str:
    if DEEPSEEK_THINKING:
        return "auto"
    return "required" if first_turn else "auto"


async def generate_deepseek_report(
    run_id: str, metadata: dict, comparison: dict
) -> tuple[dict, list[dict], str | None]:
    schema_text = json.dumps(REPORT_SCHEMA, ensure_ascii=False)
    messages = [
        {
            "role": "system",
            "content": (
                attribution_instructions()
                + " 最终必须只输出 JSON，不要使用 Markdown。JSON 必须符合"
                + f"以下 schema：{schema_text}"
            ),
        },
        {
            "role": "user",
            "content": (
                "自动异常检测已触发。请调查本次 profile 相对自动 "
                "baseline 的变化并生成可验证归因报告。所有性能事实"
                "必须通过工具取得。"
            ),
        },
    ]
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "X-Client-Request-Id": run_id,
    }
    trace = []
    request_id = None
    call_count = 0
    first_turn = True
    async with httpx.AsyncClient(timeout=90) as client:
        while True:
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "tools": deepseek_tools(),
                "tool_choice": deepseek_tool_choice(first_turn),
                "response_format": {"type": "json_object"},
                "max_tokens": 3000,
                "stream": False,
            }
            if DEEPSEEK_THINKING:
                payload["thinking"] = {"type": "enabled"}
                payload["reasoning_effort"] = DEEPSEEK_REASONING_EFFORT
            response = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            request_id = response.headers.get("x-request-id") or request_id
            response.raise_for_status()
            body = response.json()
            message = body["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            if not calls:
                content = message.get("content") or ""
                if not content.strip():
                    raise RuntimeError(
                        "DeepSeek returned an empty attribution report"
                    )
                return (
                    AttributionReport.model_validate_json(
                        content
                    ).model_dump(),
                    trace,
                    request_id,
                )

            messages.append(
                {
                    key: value
                    for key, value in message.items()
                    if key in {
                        "role",
                        "content",
                        "tool_calls",
                        "reasoning_content",
                    }
                }
            )
            for call in calls:
                call_count += 1
                if call_count > MAX_TOOL_CALLS:
                    raise RuntimeError("LLM exceeded tool call budget")
                function = call.get("function") or {}
                arguments = json.loads(function.get("arguments") or "{}")
                result = execute_tool(
                    function["name"], arguments, metadata, comparison
                )
                trace.append(
                    {
                        "tool": function["name"],
                        "arguments": arguments,
                        "result": result,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(
                            result, ensure_ascii=False
                        ),
                    }
                )
            first_turn = False


def execute_tool(
    name: str, arguments: dict, metadata: dict, comparison: dict
) -> dict:
    if name == "get_profile_metadata":
        if arguments:
            raise ValueError("get_profile_metadata takes no arguments")
        return {
            **metadata,
            "target_total_samples": comparison["target_total_samples"],
            "baseline_total_samples": comparison[
                "baseline_total_samples"
            ],
            "evidence_id": "ev-metadata-profile",
        }
    if name == "compare_profile_summary":
        limit = arguments.get("limit")
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be an integer between 1 and 20")
        return {
            "function_deltas": comparison.get("function_deltas", [])[
                :limit
            ],
            "stack_evidence_candidates": [
                {
                    "evidence_id": item["evidence_id"],
                    "source": item["source"],
                    "leaf": item["frames"][-1],
                    "delta_pp": item["delta_pp"],
                }
                for item in comparison.get("stack_deltas", [])[:10]
            ],
        }
    if name == "inspect_stack_evidence":
        evidence_id = arguments.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.startswith(
            "ev-stack-"
        ):
            raise ValueError("invalid stack evidence_id")
        item = next(
            (
                value
                for value in comparison.get("stack_deltas", [])
                if value["evidence_id"] == evidence_id
            ),
            None,
        )
        return item or {"error": "stack evidence not found"}
    if name == "compare_metrics":
        if arguments:
            raise ValueError("compare_metrics takes no arguments")
        return {"metric_deltas": comparison.get("metric_deltas", [])}
    raise ValueError(f"unsupported attribution tool: {name}")


def extract_output_text(response: dict) -> str:
    if response.get("output_text"):
        return response["output_text"]
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content["text"]
            if content.get("type") == "refusal":
                raise RuntimeError(content.get("refusal", "model refused"))
    raise RuntimeError("OpenAI response did not contain a final report")


def evidence_map(comparison: dict, metadata: dict) -> dict:
    items = {
        item["evidence_id"]: item
        for group in (
            comparison.get("function_deltas", []),
            comparison.get("stack_deltas", []),
            comparison.get("metric_deltas", []),
        )
        for item in group
    }
    items["ev-metadata-profile"] = {
        "evidence_id": "ev-metadata-profile",
        "type": "metadata",
        **metadata,
    }
    return items


def verify_and_enrich_report(
    report: dict,
    comparison: dict,
    metadata: dict,
    tool_trace: list[dict] | None = None,
) -> dict:
    parsed = AttributionReport.model_validate(report)
    evidence = evidence_map(comparison, metadata)
    allowed_evidence = (
        evidence_ids_from_trace(tool_trace)
        if tool_trace is not None
        else set(evidence)
    )
    inspected_stack_ids = {
        item.get("result", {}).get("evidence_id")
        for item in tool_trace or []
        if item.get("tool") == "inspect_stack_evidence"
    }
    enriched = parsed.model_dump()
    for finding in enriched["findings"]:
        unknown = [
            item
            for item in finding["evidence_ids"]
            if item not in evidence or item not in allowed_evidence
        ]
        if unknown:
            raise ValueError(
                f"finding references unknown evidence: {unknown}"
            )
        if finding["category"] in {
            "CPU_HOTSPOT_REGRESSION",
            "CALL_PATH_REGRESSION",
        } and not any(
            item.startswith(("ev-function-", "ev-stack-"))
            for item in finding["evidence_ids"]
        ):
            raise ValueError("CPU finding lacks profile evidence")
        if (
            tool_trace is not None
            and finding["category"] == "CALL_PATH_REGRESSION"
            and not any(
                item in inspected_stack_ids
                for item in finding["evidence_ids"]
            )
        ):
            raise ValueError(
                "call-path finding lacks inspected stack evidence"
            )
        if (
            finding["category"] == "MEMORY_REGRESSION"
            and not any(
                item.startswith("ev-metric-")
                for item in finding["evidence_ids"]
            )
        ):
            raise ValueError("memory finding lacks metric evidence")
        subjects = []
        for evidence_id_value in finding["evidence_ids"]:
            item = evidence[evidence_id_value]
            if item.get("function"):
                subjects.append(item["function"])
            subjects.extend(item.get("frames", []))
            if item.get("metric"):
                subjects.append(item["metric"])
        if finding["subject"] not in subjects and (
            finding["category"] != "DATA_QUALITY"
        ):
            raise ValueError(
                "finding subject is not supported by cited evidence"
            )
        finding["evidence"] = [
            evidence[item] for item in finding["evidence_ids"]
        ]
    enriched["verification"] = {
        "verified": True,
        "evidence_count": sum(
            len(item["evidence_ids"]) for item in enriched["findings"]
        ),
        "verified_at": datetime.now().astimezone().isoformat(),
    }
    return enriched


def evidence_ids_from_trace(trace: list[dict]) -> set[str]:
    output: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            evidence_id_value = value.get("evidence_id")
            if isinstance(evidence_id_value, str):
                output.add(evidence_id_value)
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    for item in trace:
        walk(item.get("result"))
    return output


def complete_run(run_id, report, trace, mode, model):
    with connection() as conn, conn.cursor() as cur:
        row = cur.execute(
            """
            UPDATE attribution_runs
               SET status = 'COMPLETED', report = %s::jsonb,
                   tool_trace = %s::jsonb, mode = %s, model = %s,
                   completed_at = NOW()
             WHERE id = %s
            RETURNING *
            """,
            (
                json.dumps(report),
                json.dumps(trace),
                mode,
                model,
                run_id,
            ),
        ).fetchone()
        conn.commit()
    return serialize_row(row)


def fail_run(run_id, error):
    with connection() as conn, conn.cursor() as cur:
        row = cur.execute(
            """
            UPDATE attribution_runs
               SET status = 'FAILED', error = %s, completed_at = NOW()
             WHERE id = %s
            RETURNING *
            """,
            (error[:2000], run_id),
        ).fetchone()
        conn.commit()
    return serialize_row(row)


def latest_run(target_type, target_id, trigger=None):
    clauses = ["target_type = %s", "target_id = %s"]
    values: list[Any] = [target_type, target_id]
    if trigger:
        clauses.append("trigger = %s")
        values.append(trigger)
    with connection() as conn, conn.cursor() as cur:
        row = cur.execute(
            f"""
            SELECT * FROM attribution_runs
             WHERE {' AND '.join(clauses)}
             ORDER BY created_at DESC LIMIT 1
            """,
            values,
        ).fetchone()
    return serialize_row(row)


def list_runs_for_session(session_id: str) -> list[dict]:
    with connection() as conn, conn.cursor() as cur:
        rows = cur.execute(
            """
            SELECT * FROM attribution_runs
             WHERE session_id = %s
             ORDER BY created_at DESC
             LIMIT 50
            """,
            (session_id,),
        ).fetchall()
    return [serialize_row(row) for row in rows]


def serialize_row(row):
    if row is None:
        return None
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }
