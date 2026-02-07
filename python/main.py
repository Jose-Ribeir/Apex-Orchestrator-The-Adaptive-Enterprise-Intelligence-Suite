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

from app import __version__
from app.routers import agents, chat, health, index


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: validate config and log GeminiMesh status."""
    settings = get_settings()
    if settings.geminimesh_configured:
        logger.info(
            "GeminiMesh POST API configured: %s/agents",
            settings.geminimesh_api_url,
        )
    else:
        logger.warning("GEMINIMESH_API_TOKEN not configured")
    yield
    # Shutdown if needed (e.g. close DB connections)
    pass


app = FastAPI(
    title="Gemini Agent Factory",
    description="Dynamic 2-call pipeline: cheap router + dynamic generator. "
    "Per-agent LanceDB RAG. Optional GeminiMesh agent prompt updates.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers at root to keep same paths as original (e.g. /health, /generate_stream)
app.include_router(agents.router)
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
