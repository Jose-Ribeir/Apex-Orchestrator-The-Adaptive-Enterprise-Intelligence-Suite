"""Vertex AI RAG: Embeddings + Vector Search. Single shared index with agent_name in restricts."""

import json
from typing import Any

from google import genai
from google.cloud import aiplatform, storage
from google.cloud.aiplatform import matching_engine
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (
    Namespace as RestrictNamespace,
)
from google.cloud.aiplatform_v1 import IndexDatapoint
from google.genai import types

from app.config import get_settings

# Embedding dimension for text-embedding-005 (up to 768)
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "text-embedding-005"
REGISTRY_BLOB = "_registry.json"

_embed_client: genai.Client | None = None
_index: matching_engine.MatchingEngineIndex | None = None
_endpoint: matching_engine.MatchingEngineIndexEndpoint | None = None


def _safe_agent(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")) or "default"


def _get_embed_client() -> genai.Client:
    global _embed_client
    if _embed_client is None:
        settings = get_settings()
        _embed_client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_region,
        )
    return _embed_client


def _embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _get_embed_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    out: list[list[float]] = []
    for emb in response.embeddings or []:
        vals = emb.values if emb else None
        out.append(list(vals) if vals else [])
    return out


def _embed_single(text: str) -> list[float]:
    return _embed([text])[0]


def _get_index() -> matching_engine.MatchingEngineIndex:
    global _index
    if _index is None:
        settings = get_settings()
        aiplatform.init(project=settings.gcp_project_id, location=settings.vertex_region)
        _index = matching_engine.MatchingEngineIndex(
            index_name=settings.vertex_rag_index_id,
            project=settings.gcp_project_id,
            location=settings.vertex_region,
        )
    return _index


def _get_endpoint() -> matching_engine.MatchingEngineIndexEndpoint:
    global _endpoint
    if _endpoint is None:
        settings = get_settings()
        aiplatform.init(project=settings.gcp_project_id, location=settings.vertex_region)
        _endpoint = matching_engine.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.vertex_rag_index_endpoint_id,
            project=settings.gcp_project_id,
            location=settings.vertex_region,
        )
    return _endpoint


def _registry_path() -> str:
    settings = get_settings()
    prefix = (settings.gcs_documents_prefix or "agents").strip("/")
    return f"{prefix}/{REGISTRY_BLOB}"


def _read_registry() -> dict[str, int]:
    settings = get_settings()
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(_registry_path())
    try:
        data = blob.download_as_bytes()
        return json.loads(data.decode("utf-8")).get("agents", {})
    except Exception:
        return {}


def _write_registry(agents: dict[str, int]) -> None:
    settings = get_settings()
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(_registry_path())
    blob.upload_from_string(
        json.dumps({"agents": agents}, indent=2),
        content_type="application/json",
    )


def _update_agent_count(agent_name: str, delta: int) -> None:
    reg = _read_registry()
    key = _safe_agent(agent_name)
    reg[key] = max(0, reg.get(key, 0) + delta)
    if reg[key] == 0:
        del reg[key]
    _write_registry(reg)


class VertexRAG:
    """Vertex AI Vector Search RAG with per-agent isolation via restricts."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self._restrict_namespace = "agent"
        self._agent_restrict = _safe_agent(agent_name)

    def add_or_update_documents(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            return
        vectors = _embed([d["content"] for d in docs])
        datapoints = []
        for i, doc in enumerate(docs):
            meta = doc.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}
            # embedding_metadata: Struct (dict); 2KB limit - store content truncated
            content_preview = (doc["content"] or "")[:1500]
            embedding_metadata = {
                "content": content_preview,
                "id": doc["id"],
            }
            restriction = IndexDatapoint.Restriction(
                namespace=self._restrict_namespace,
                allow_list=[self._agent_restrict],
            )
            dp = IndexDatapoint(
                datapoint_id=doc["id"],
                feature_vector=vectors[i],
                restricts=[restriction],
                embedding_metadata=embedding_metadata,
            )
            datapoints.append(dp)
        _get_index().upsert_datapoints(datapoints=datapoints)
        _update_agent_count(self.agent_name, len(docs))

    def delete_document(self, doc_id: str) -> bool:
        try:
            _get_index().remove_datapoints(datapoint_ids=[doc_id])
            _update_agent_count(self.agent_name, -1)
            return True
        except Exception:
            return False

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        settings = get_settings()
        qvec = _embed_single(query)
        response = _get_endpoint().find_neighbors(
            deployed_index_id=settings.vertex_rag_deployed_index_id,
            queries=[qvec],
            num_neighbors=top_k,
            filter=[RestrictNamespace(name=self._restrict_namespace, allow_tokens=[self._agent_restrict])],
            return_full_datapoint=True,
        )
        # API returns List[List[MatchNeighbor]]: one list per query; MatchNeighbor has embedding_metadata, distance
        results = []
        if response and len(response) > 0:
            neighbors = response[0]
            for nn in neighbors:
                content = ""
                emb_meta = getattr(nn, "embedding_metadata", None)
                if emb_meta is not None:
                    try:
                        meta = dict(emb_meta) if hasattr(emb_meta, "items") else {}
                    except Exception:
                        meta = {}
                    content = (meta.get("content") or "").strip()
                results.append(
                    {
                        "contents": content,
                        "score": getattr(nn, "distance", 0.0),
                    }
                )
        return results[:top_k]

    def count_documents(self) -> int:
        reg = _read_registry()
        return reg.get(self._agent_restrict, 0)


retriever_cache: dict[str, VertexRAG] = {}


def get_or_create_retriever(agent_name: str) -> VertexRAG:
    if agent_name not in retriever_cache:
        retriever_cache[agent_name] = VertexRAG(agent_name)
    return retriever_cache[agent_name]


def list_agent_names_from_disk() -> list[str]:
    """List agent names from GCS registry (no filesystem)."""
    reg = _read_registry()
    return sorted(reg.keys())


def list_agents_with_doc_counts() -> list[tuple[str, int]]:
    """List agents with document counts from registry."""
    reg = _read_registry()
    return sorted(reg.items(), key=lambda x: x[0])
