from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .flamegraph import generate_flamegraph_svg
from .parser import (
    collapsed_to_tree,
    compare_profile_summaries,
    profile_summary,
    split_ebpf_sources,
    top_functions,
)


class AnalyzeRequest(BaseModel):
    task_id: str = Field(min_length=1)
    collapsed_stacks: str = Field(min_length=1)
    performance_data: dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    target_stacks: str = Field(min_length=1)
    baseline_stacks: str = Field(min_length=1)
    target_metrics: dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=20, ge=1, le=100)


app = FastAPI(title="Mini-Drop Analyzer", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    try:
        flamegraph = collapsed_to_tree(body.collapsed_stacks)
        collector = (
            body.performance_data.get("cpu", {}).get("collector")
            or body.performance_data.get("collector")
        )
        try:
            flamegraph_svg = generate_flamegraph_svg(body.collapsed_stacks)
        except RuntimeError as exc:
            if "not found" not in str(exc):
                raise
            flamegraph_svg = None
        result = {
            "task_id": body.task_id,
            "flamegraph": flamegraph,
            "flamegraph_svg": flamegraph_svg,
            "top_functions": top_functions(body.collapsed_stacks),
            "metrics": body.performance_data,
            "summary": profile_summary(body.collapsed_stacks),
        }
        if collector == "ebpf":
            result["ebpf_sources"] = {
                name: {
                    "source": name,
                    "flamegraph": collapsed_to_tree(source_stacks),
                    "top_functions": top_functions(source_stacks),
                }
                for name, source_stacks in split_ebpf_sources(
                    body.collapsed_stacks
                ).items()
            }
        return result
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/compare")
def compare(body: CompareRequest):
    try:
        target = profile_summary(body.target_stacks, top_k=100)
        baseline = profile_summary(body.baseline_stacks, top_k=100)
        return compare_profile_summaries(
            target,
            baseline,
            body.target_metrics,
            body.baseline_metrics,
            body.top_k,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
