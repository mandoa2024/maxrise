from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
        return {
            "task_id": body.task_id,
            "flamegraph": collapsed_to_tree(body.collapsed_stacks),
            "top_functions": top_functions(body.collapsed_stacks),
            "metrics": body.performance_data,
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
