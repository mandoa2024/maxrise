from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .flamegraph import generate_flamegraph_svg
from .parser import collapsed_to_tree, top_functions


class AnalyzeRequest(BaseModel):
    task_id: str = Field(min_length=1)
    collapsed_stacks: str = Field(min_length=1)
    performance_data: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Mini-Drop Analyzer", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    try:
        flamegraph = collapsed_to_tree(body.collapsed_stacks)
        try:
            flamegraph_svg = generate_flamegraph_svg(body.collapsed_stacks)
        except RuntimeError as exc:
            if "not found" not in str(exc):
                raise
            flamegraph_svg = None
        return {
            "task_id": body.task_id,
            "flamegraph": flamegraph,
            "flamegraph_svg": flamegraph_svg,
            "top_functions": top_functions(body.collapsed_stacks),
            "metrics": body.performance_data,
        }
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
