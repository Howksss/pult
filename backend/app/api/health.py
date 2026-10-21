from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.api.problems import ProblemError
from app.db import get_session

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


class ReadyResponse(BaseModel):
    status: str
    database: str


@router.get("/ready", response_model=ReadyResponse)
def ready(session: Annotated[Session, Depends(get_session)]) -> ReadyResponse:
    try:
        session.execute(text("select 1"))
    except SQLAlchemyError as error:
        raise ProblemError(503, "not-ready", "Service Unavailable", "database is not reachable") from error
    return ReadyResponse(status="ready", database="ok")
