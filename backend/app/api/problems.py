from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ExceptionHandler

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_BASE = "https://pult.dev/problems/"


class ProblemError(Exception):
    def __init__(
        self, status: int, slug: str, title: str, detail: str, errors: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.slug = slug
        self.title = title
        self.detail = detail
        self.errors = errors


def problem_response(
    status: int, slug: str, title: str, detail: str, errors: list[dict[str, Any]] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {"type": PROBLEM_BASE + slug, "title": title, "status": status, "detail": detail}
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE)


def not_found(entity: str, entity_id: int) -> ProblemError:
    return ProblemError(404, "not-found", "Not Found", f"{entity} {entity_id} not found")


async def handle_problem(_: Request, exc: ProblemError) -> JSONResponse:
    return problem_response(exc.status, exc.slug, exc.title, exc.detail, exc.errors)


async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"location": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    return problem_response(422, "validation", "Unprocessable Entity", "request validation failed", errors)


async def handle_http(_: Request, exc: HTTPException) -> JSONResponse:
    slug = "not-found" if exc.status_code == 404 else "http-error"
    return problem_response(exc.status_code, slug, str(exc.detail), str(exc.detail))


def install(app: FastAPI) -> None:
    app.add_exception_handler(ProblemError, cast(ExceptionHandler, handle_problem))
    app.add_exception_handler(RequestValidationError, cast(ExceptionHandler, handle_validation))
    app.add_exception_handler(HTTPException, cast(ExceptionHandler, handle_http))
