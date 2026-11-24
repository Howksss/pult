from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_keys, auth, checks, graph, health, probe, problems, projects, scopes
from app.core import observability
from app.core.config import get_settings

settings = get_settings()
observability.configure_logging()

app = FastAPI(title="Pult", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
problems.install(app)
observability.install(app)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(projects.router)
app.include_router(graph.router)
app.include_router(checks.router)
app.include_router(scopes.router)
app.include_router(probe.router)
