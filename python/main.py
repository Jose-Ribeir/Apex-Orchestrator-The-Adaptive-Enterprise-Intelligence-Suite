"""
Gemini Agent Factory – FastAPI application entrypoint.

Dynamic 2-call pipeline: router (gemini-3-flash-preview) + dynamic generator
(gemini-3-flash-preview / gemini-2.5-flash; pro not on free tier). Per-agent LanceDB RAG.
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

# Ensure request/stream logs from app.routers.chat and app.services.gemini_router are visible.
# Uvicorn can override root logging; we explicitly configure the "app" logger so it always outputs.
# Also log to a file so logs can be read without terminal access.
_CHAT_LOG_FILE = _APP_DIR / "chat_stream.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
_log_fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
if not _app_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(_log_fmt)
    _app_logger.addHandler(_handler)
try:
    _file_handler = logging.FileHandler(_CHAT_LOG_FILE, encoding="utf-8")
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(_log_fmt)
    _app_logger.addHandler(_file_handler)
except Exception:  # e.g. read-only filesystem
    pass
# Do not propagate so each log is only handled once (app's stream + file handlers).
_app_logger.propagate = False
logger = _app_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app import __version__
from app.auth.routes import router as auth_router
from app.routers import chat, connections, health, index
from app.routers.api_router import api_router
from app.seed import seed_agents, seed_connection_types, seed_tools, seed_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    import asyncio

    try:
        with open(_CHAT_LOG_FILE, "a", encoding="utf-8") as f:
            import datetime

            f.write(f"\n===== App started {datetime.datetime.now().isoformat()} =====\n")
            f.flush()
    except Exception:
        pass
    try:
        seed_tools()
        seed_connection_types()
        seed_users()
        await seed_agents()
    except Exception as e:
        logger.warning("Startup seed skipped: %s", e)
    # Background: email polling every 30s
    from app.services.email_polling import email_polling_loop

    _email_poll_task = asyncio.create_task(email_polling_loop())
    yield
    _email_poll_task.cancel()
    try:
        await _email_poll_task
    except asyncio.CancelledError:
        pass


OPENAPI_TAGS = [
    {"name": "Health", "description": "Service health and configuration status."},
    {"name": "Auth", "description": "Login, register, logout, and current user (cookie-based)."},
    {"name": "Agents", "description": "Agent CRUD."},
    {"name": "Agents -> Knowledge Base", "description": "List, add, get, and delete agent knowledge base items (RAG)."},
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
    description="Dynamic 2-call pipeline: router + dynamic generator. "
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
