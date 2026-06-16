from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    agent_id: str = Field(min_length=1)
    pid: int = Field(gt=0)
    duration_seconds: int = Field(default=10, ge=1, le=300)
    sample_rate: int = Field(default=99, ge=1, le=999)
    collector: Literal["perf"] = "perf"


class Heartbeat(BaseModel):
    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    hostname: str = Field(min_length=1)


class TaskStatusUpdate(BaseModel):
    status: Literal["RUNNING", "UPLOADING", "FAILED"]
    reason: str = Field(min_length=1)


class TaskUpload(BaseModel):
    raw_data: str = Field(min_length=1)
    performance_data: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="agent uploaded profiling data", min_length=1)
