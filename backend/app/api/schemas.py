from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import BlockKind, CheckStatus
from app.services.status import BlockStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BlockOut(BaseModel):
    id: int
    kind: BlockKind
    name: str
    description: str | None
    x: float
    y: float
    status: BlockStatus


class BlockCreate(StrictModel):
    kind: BlockKind
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    x: float = 0
    y: float = 0


class BlockUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    x: float | None = None
    y: float | None = None


class LinkOut(BaseModel):
    id: int
    source_block_id: int
    target_block_id: int
    label: str | None


class LinkCreate(StrictModel):
    source_block_id: int
    target_block_id: int
    label: str | None = Field(default=None, max_length=100)


class GraphOut(BaseModel):
    project_id: int
    generated_at: datetime
    blocks: list[BlockOut]
    links: list[LinkOut]


class ProbeResultIn(StrictModel):
    health_check_id: int
    status: CheckStatus
    checked_at: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    message: str | None = Field(default=None, max_length=2000)


class ProbeBatchIn(StrictModel):
    results: list[ProbeResultIn] = Field(min_length=1, max_length=500)


class StatusChange(BaseModel):
    block_id: int
    previous: BlockStatus
    current: BlockStatus


class ProbeAccepted(BaseModel):
    accepted: int
    status_changes: list[StatusChange]
