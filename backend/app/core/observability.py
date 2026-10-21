import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match

REQUESTS = Counter("pult_http_requests_total", "HTTP requests", ["method", "route", "status"])
DURATION = Histogram(
    "pult_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5),
)

access_log = logging.getLogger("pult.access")

REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            entry.update(extra)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def route_template(request: Request) -> str:
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match is Match.FULL:
            return str(getattr(route, "path", request.url.path))
    return "unmatched"


async def observe(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    route = route_template(request)
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        elapsed = time.perf_counter() - started
        if route != "/metrics":
            REQUESTS.labels(request.method, route, str(status)).inc()
            DURATION.labels(request.method, route).observe(elapsed)
        access_log.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "route": route,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 1),
                }
            },
        )


def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def install(app: FastAPI) -> None:
    app.middleware("http")(observe)
    app.add_api_route("/metrics", metrics, include_in_schema=False)
