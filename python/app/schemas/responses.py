"""Response schemas for API endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    """Agent mode: PERFORMANCE | EFFICIENCY | BALANCED."""

    PERFORMANCE = "PERFORMANCE"
    EFFICIENCY = "EFFICIENCY"
    BALANCED = "BALANCED"


class AgentToolRef(BaseModel):
    """Tool reference in agent response (id and name)."""

    id: str = Field(..., description="Tool ID (UUID)")
    name: str = Field(..., description="Tool display name")


class UserRef(BaseModel):
    """Minimal user reference (id and name)."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="Display name")


class AgentStatusIndexing(BaseModel):
    """Indexing and enrich status: pending | error | completed."""

    indexing: str = Field(..., description="One of: pending, error, completed")
    enrich: str = Field(default="pending", description="One of: pending, error, completed")


class AgentMetadata(BaseModel):
    """Agent metadata; status.indexing (document) and status.enrich (prompt) state."""

    status: AgentStatusIndexing = Field(
        default_factory=lambda: AgentStatusIndexing(indexing="completed", enrich="pending"),
        description="Status including indexing and enrich state",
    )


class AgentInfo(BaseModel):
    """Single agent in list: agent_id, name, user ref; optional doc_count, metadata, timestamps, tools, instructions when from DB."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    name: str = Field(..., description="Display name")
    mode: AgentMode | None = Field(None, description="PERFORMANCE | EFFICIENCY | BALANCED")
    prompt: str | None = Field(None, description="System prompt")
    instructions: list[str] = Field(default_factory=list, description="Instruction lines in order")
    user: UserRef | None = Field(None, description="Owner (when from DB)")
    doc_count: int = Field(0, description="Number of documents in this agent's RAG index (when from DB)")
    tools: list[AgentToolRef] = Field(default_factory=list, description="Tools linked to this agent (id, name)")
    created_at: datetime | None = Field(None, description="Creation time (when from DB)")
    updated_at: datetime | None = Field(None, description="Last update time (when from DB)")
    metadata: AgentMetadata = Field(
        default_factory=lambda: AgentMetadata(status=AgentStatusIndexing(indexing="completed", enrich="pending")),
        description="Metadata including status.indexing and status.enrich",
    )


class AgentDetailResponse(BaseModel):
    """Single agent full detail (GET /agents/{id})."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    user_id: str = Field(..., description="Owner user id")
    name: str = Field(..., description="Display name")
    mode: AgentMode = Field(..., description="PERFORMANCE | EFFICIENCY | BALANCED")
    prompt: str | None = Field(None, description="System prompt")
    instructions: list[str] = Field(..., description="Instruction lines in order")
    tools: list[AgentToolRef] = Field(default_factory=list, description="Tools linked to this agent (id, name)")
    doc_count: int = Field(..., description="RAG document count for this agent")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    metadata: AgentMetadata = Field(
        default_factory=lambda: AgentMetadata(status=AgentStatusIndexing(indexing="completed", enrich="pending")),
        description="Metadata including status.indexing and status.enrich",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int = Field(..., description="Current page (1-based)")
    limit: int = Field(..., description="Page size")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    more: bool = Field(..., description="Whether there are more pages")


class ListAgentsResponse(BaseModel):
    """Response for GET /agents: paginated agents with doc counts."""

    agents: list[AgentInfo] = Field(..., description="Agents that have RAG data (from DATA_FOLDER)")
    meta: PaginationMeta | None = Field(None, description="Pagination metadata (when DB configured)")


class CreateAgentResponse(BaseModel):
    """Response after creating an agent."""

    agent_id: str = Field(..., description="Agent ID (UUID)")
    message: str = Field(default="created", description="Human-readable status")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Always 'healthy' when endpoint succeeds")
    agents: list[str] = Field(..., description="List of agent names with loaded RAG")
    geminimesh_configured: bool = Field(..., description="Whether GeminiMesh API token is set")
    embedding_model: str = Field(..., description="'loaded' or 'not_loaded'")
    database_configured: bool = Field(..., description="Whether DATABASE_URL is set")
    database_connected: bool = Field(..., description="Whether DB connection succeeds")


class OptimizePromptResponse(BaseModel):
    """Response from standalone prompt optimization (no GeminiMesh call)."""

    optimized_prompt: str = Field(..., description="Generated system prompt")
    analysis: dict[str, Any] = Field(..., description="Agent type, complexity, needs_rag")
    model_used: str = Field(..., description="Model used for optimization")


class UpdateAgentGeminimeshResponse(BaseModel):
    """Response after updating agent prompt in GeminiMesh."""

    status: str = Field(..., description="'success' on success")
    agent_id: str = Field(..., description="Agent ID that was updated")
    geminimesh_response: dict[str, Any] = Field(..., description="Raw response from GeminiMesh API")
    optimized_prompt: str = Field(..., description="Generated prompt that was sent")
    local_rag_docs: int = Field(..., description="Document count in local RAG for this agent")
    message: str = Field(..., description="Human-readable success message")


class UpdateAgentIndexResponse(BaseModel):
    """Response after updating agent RAG index (add/update/delete)."""

    status: str = Field(..., description="'success' on success")
    total_docs: int = Field(..., description="Total documents in agent index after update")


class UploadAndIndexResponse(BaseModel):
    """Response after uploading a JSONL file and indexing documents."""

    status: str = Field(..., description="'success' on success")
    docs_added: int = Field(..., description="Number of documents parsed and added")
    total_docs: int = Field(..., description="Total documents in agent index after upload")


class HumanTaskModelQueryRef(BaseModel):
    """Model query reference embedded in a human task response."""

    id: str = Field(..., description="Model query ID")
    userQuery: str | None = Field(None, description="User query text")
    modelResponse: str | None = Field(None, description="Model response text")


class HumanTaskResponse(BaseModel):
    """Single human task (list item or get-by-id)."""

    id: str = Field(..., description="Human task ID (UUID)")
    modelQueryId: str = Field(..., description="Linked model query ID")
    reason: str | None = Field(None, description="Reason for human review")
    retrievedData: str | None = Field(None, description="Retrieved data snapshot")
    modelMessage: str | None = Field(None, description="Model message for context")
    status: str = Field(..., description="PENDING | RESOLVED")
    createdAt: str = Field(..., description="Creation time (ISO)")
    updatedAt: str = Field(..., description="Last update time (ISO)")
    modelQuery: HumanTaskModelQueryRef | None = Field(None, description="Linked model query when loaded")


class ListHumanTasksResponse(BaseModel):
    """Response for GET /human-tasks: paginated list of human tasks."""

    data: list[HumanTaskResponse] = Field(..., description="Human tasks")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
