"""Mount all /api routes with auth dependency."""

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.routers import agents, agents_nested, api_tokens, human_tasks_api, tools_api

# All routes under /api require cookie or Bearer API token
api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
# Nested routes first so /api/agents/{id}/instructions etc. match before /api/agents/{id}
api_router.include_router(agents_nested.router)
api_router.include_router(agents.documents_router)
api_router.include_router(agents.router)
api_router.include_router(api_tokens.router)
api_router.include_router(tools_api.router)
api_router.include_router(human_tasks_api.router)
