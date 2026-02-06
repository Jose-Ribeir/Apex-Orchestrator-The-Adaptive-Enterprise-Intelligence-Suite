"""Per-agent LanceDB RAG: document storage and vector search."""

import json
import os
import time
from typing import Any

import lancedb
import pyarrow as pa

from app.config import get_settings
from app.services.embedding import get_embedding_model, init_embedding_model

retriever_cache: dict[str, "LanceRAG"] = {}


def _agent_paths(agent_name: str) -> tuple[str, str]:
    safe_name = "".join(c for c in agent_name if c.isalnum() or c in ("-", "_"))
    settings = get_settings()
    agent_dir = os.path.join(settings.data_folder, safe_name)
    os.makedirs(agent_dir, exist_ok=True)
    db_path = os.path.join(agent_dir, "lancedb")
    return agent_dir, db_path


class LanceRAG:
    """LanceDB-backed RAG with per-agent isolation."""

    EMBEDDING_DIM = 768

    def __init__(self, agent_dir: str, db_path: str) -> None:
        self.agent_dir = agent_dir
        self.db_path = db_path
        self.db = lancedb.connect(self.db_path)
        self.table_name = "documents"
        self._ensure_table()

    def _ensure_table(self) -> None:
        tables = self.db.list_tables().tables
        if self.table_name not in tables:
            schema = pa.schema(
                [
                    pa.field("vector", lancedb.schema.vector(self.EMBEDDING_DIM)),
                    pa.field("id", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("metadata", pa.string()),
                    pa.field("created_at", pa.int64()),
                ]
            )
            self.db.create_table(self.table_name, schema=schema)

    def add_or_update_documents(self, docs: list[dict[str, Any]]) -> None:
        model = get_embedding_model()
        if model is None:
            model = init_embedding_model()
        vectors = [model.encode(doc["content"]).tolist() for doc in docs]
        data = [
            {
                "id": doc["id"],
                "content": doc["content"],
                "metadata": json.dumps(doc.get("metadata", {})),
                "created_at": int(time.time()),
            }
            for doc in docs
        ]
        self.db[self.table_name].add(data, vectors)

    def delete_document(self, doc_id: str) -> bool:
        count = self.db[self.table_name].delete(f"id = '{doc_id}'")
        return count > 0

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        model = get_embedding_model()
        if model is None:
            model = init_embedding_model()
        query_vector = model.encode([query])
        results = (
            self.db[self.table_name].search(query_vector, query_type="vector", n_results=top_k).limit(top_k).to_list()
        )
        return [{"contents": r["content"], "score": r["_distance"]} for r in results]

    def count_documents(self) -> int:
        return self.db[self.table_name].count_rows()


def get_or_create_retriever(agent_name: str) -> LanceRAG:
    if agent_name in retriever_cache:
        return retriever_cache[agent_name]
    init_embedding_model()
    agent_dir, db_path = _agent_paths(agent_name)
    rag = LanceRAG(agent_dir, db_path)
    retriever_cache[agent_name] = rag
    return rag


def list_agent_names_from_disk() -> list[str]:
    """List agent names by scanning DATA_FOLDER for subdirs that contain a LanceDB."""
    settings = get_settings()
    base = settings.data_folder
    if not os.path.isdir(base):
        return []
    names = []
    for entry in os.scandir(base):
        if entry.is_dir() and not entry.name.startswith("."):
            db_path = os.path.join(entry.path, "lancedb")
            if os.path.isdir(db_path):
                names.append(entry.name)
    return sorted(names)


def list_agents_with_doc_counts() -> list[tuple[str, int]]:
    """List all agents (from disk) with their document count. Loads RAG into cache as needed."""
    names = list_agent_names_from_disk()
    result = []
    for name in names:
        rag = get_or_create_retriever(name)
        result.append((name, rag.count_documents()))
    return result
