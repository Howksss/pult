import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import BlockKind, CheckMethod, CheckStatus, MemberRole, ScopeAccess
from app.services.check_config import normalize_config, normalize_target
from app.services.scope import normalize_glob
from app.services.status import BlockStatus

DETAILS_LIMIT = 8000


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
    reason: str | None
    checks_total: int
    checks_problem: int


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
    project_name: str
    generated_at: datetime
    blocks: list[BlockOut]
    links: list[LinkOut]


class ProbeResultIn(StrictModel):
    health_check_id: int
    status: CheckStatus
    checked_at: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    message: str | None = Field(default=None, max_length=2000)
    error_kind: str | None = Field(default=None, pattern=r"^[a-z_]{1,40}$")
    details: dict[str, Any] | None = None

    @field_validator("details")
    @classmethod
    def details_fit(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and len(json.dumps(value, ensure_ascii=False)) > DETAILS_LIMIT:
            raise ValueError(f"details must be at most {DETAILS_LIMIT} characters of JSON")
        return value


class ProbeBatchIn(StrictModel):
    results: list[ProbeResultIn] = Field(min_length=1, max_length=500)


class StatusChange(BaseModel):
    block_id: int
    previous: BlockStatus
    current: BlockStatus


class ProbeAccepted(BaseModel):
    accepted: int
    status_changes: list[StatusChange]


class ResultOut(BaseModel):
    checked_at: datetime
    status: CheckStatus
    latency_ms: int | None
    message: str | None
    error_kind: str | None
    details: dict[str, Any] | None


class HistoryPoint(BaseModel):
    checked_at: datetime
    status: CheckStatus
    latency_ms: int | None


class TimelineBucket(BaseModel):
    start: datetime
    ok: int
    warn: int
    fail: int


class CheckOut(BaseModel):
    id: int
    title: str
    name: str | None
    method: CheckMethod
    target: str
    interval_sec: int
    timeout_sec: int
    enabled: bool
    config: dict[str, Any]
    status: BlockStatus
    reason: str | None
    error_kind: str | None
    last: ResultOut | None
    history: list[HistoryPoint]
    timeline: list[TimelineBucket]
    failing_since: datetime | None


class BlockChecksOut(BaseModel):
    block_id: int
    generated_at: datetime
    checks: list[CheckOut]


def blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class CheckCreate(StrictModel):
    name: str | None = Field(default=None, max_length=120)
    method: CheckMethod
    target: str = Field(min_length=1, max_length=500)
    interval_sec: int = Field(default=60, ge=10, le=604_800)
    timeout_sec: int = Field(default=10, ge=1, le=60)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_for_method(self) -> "CheckCreate":
        if self.timeout_sec > self.interval_sec:
            raise ValueError("таймаут не может быть больше интервала проверки")
        self.name = blank_to_none(self.name)
        self.target = normalize_target(self.method, self.target)
        self.config = normalize_config(self.method, self.config)
        return self


class CheckUpdate(StrictModel):
    name: str | None = Field(default=None, max_length=120)
    target: str | None = Field(default=None, min_length=1, max_length=500)
    interval_sec: int | None = Field(default=None, ge=10, le=604_800)
    timeout_sec: int | None = Field(default=None, ge=1, le=60)
    enabled: bool | None = None
    config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def not_empty(self) -> "CheckUpdate":
        if not self.model_fields_set:
            raise ValueError("нужно передать хотя бы одно поле")
        return self


class ScopeOut(BaseModel):
    id: int
    path_glob: str
    access: ScopeAccess


class ScopeCreate(StrictModel):
    path_glob: str = Field(min_length=1, max_length=300)
    access: ScopeAccess = ScopeAccess.read

    @field_validator("path_glob")
    @classmethod
    def relative_glob(cls, value: str) -> str:
        return normalize_glob(value)


class ScopeUpdate(StrictModel):
    access: ScopeAccess


EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Credentials(StrictModel):
    email: str = Field(max_length=255, pattern=EMAIL)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class RegisterIn(Credentials):
    password: str = Field(min_length=10, max_length=200)
    full_name: str = Field(min_length=1, max_length=150)


class MemberProject(BaseModel):
    id: int
    name: str
    role: MemberRole


class MeOut(BaseModel):
    id: int
    email: str
    full_name: str
    projects: list[MemberProject]


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=150)
    repo_full_name: str = Field(max_length=200, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ProjectCreated(MemberProject):
    probe_token: str


class MemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: MemberRole


class MemberAdd(StrictModel):
    email: str = Field(max_length=255, pattern=EMAIL)
    role: MemberRole

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class MemberUpdate(StrictModel):
    role: MemberRole
