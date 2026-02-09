"""
Gemini Agent Factory – FastAPI application entrypoint.

Dynamic 2-call pipeline: cheap router (gemini-2.5-flash-lite) + dynamic generator
(gemini-3-pro-preview / gemini-3-flash-preview / gemini-2.5-flash). Per-agent LanceDB RAG.
Optional GeminiMesh integration to update agent prompts via POST /agents.

Run locally:
  uvicorn main:app --host 127.0.0.1 --port 8000 --reload

Environment: see .env.example and app.config.Settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the python app root (directory containing main.py) so credentials are found
# regardless of current working directory when uvicorn is started.
_APP_DIR = Path(__file__).resolve().parent
load_dotenv(_APP_DIR / ".env")

# If GOOGLE_APPLICATION_CREDENTIALS is a relative path, resolve it relative to this app dir
# so GCS/Vertex clients find the key file no matter where the process was started.
_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if _creds:
    _creds_path = Path(_creds)
    if not _creds_path.is_absolute():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str((_APP_DIR / _creds_path).resolve())

import logging
import sys
from contextlib import asynccontextmanager

from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("app")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import __version__
from app.auth.routes import router as auth_router
from app.routers import chat, connections, health, index
from app.routers.api_router import api_router
from app.seed import seed_connection_types, seed_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    try:
        seed_tools()
        seed_connection_types()
    except Exception as e:
        logger.warning("Startup seed skipped: %s", e)
    yield


OPENAPI_TAGS = [
    {"name": "Health", "description": "Service health and configuration status."},
    {"name": "Auth", "description": "Login, register, logout, and current user (cookie-based)."},
    {"name": "Agents", "description": "Agent CRUD."},
    {"name": "Agents -> Documents", "description": "List, add, get, and delete agent documents (RAG)."},
    {"name": "Agents -> Instructions", "description": "Per-agent instructions (order and content)."},
    {"name": "Agents -> Tools", "description": "Link or unlink tools to/from an agent."},
    {"name": "Agents -> Queries", "description": "Model queries: user query, response, and method used."},
    {"name": "Tools", "description": "Global tool registry (list, create, update, delete)."},
    {"name": "API Tokens", "description": "Create, list, and revoke API tokens."},
    {"name": "Human Tasks", "description": "Human-in-the-loop tasks for model queries."},
    {"name": "Chat", "description": "Streaming chat with router + generator pipeline."},
    {"name": "Index", "description": "RAG index: add, update, delete, and ingest documents."},
    {"name": "Connections", "description": "OAuth connections (e.g. Google Gmail); list, connect, disconnect."},
]

app = FastAPI(
    title="Gemini Agent Factory",
    description="Dynamic 2-call pipeline: cheap router + dynamic generator. "
    "Per-agent LanceDB RAG. Optional GeminiMesh agent prompt updates.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def _root():
    """Redirect browser visitors to API docs."""
    return RedirectResponse(url="/docs", status_code=302)


# Auth (cookie + Bearer API token; /auth/me for current user)
app.include_router(auth_router)

# Protected API (cookie or Bearer required)
app.include_router(api_router)

# Connections (auth on list/start/disconnect; callback is public)
app.include_router(connections.router, prefix="/api")

# Other routers at root (e.g. /health, /generate_stream)
app.include_router(chat.router)
app.include_router(index.router)
app.include_router(health.router)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
