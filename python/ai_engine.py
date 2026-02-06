#!/usr/bin/env python3
"""
🏆 GEMINI AGENT FACTORY v6.4 - DYNAMIC 2-CALL PIPELINE + GEMINIMESH UPDATE API
✅ Call #1: gemini-2.5-flash-lite (CHEAP ROUTER)
✅ Call #2: DYNAMIC MODEL (router decides: 3-pro/3-flash/2.5-flash)
✅ Tool prediction + V5 routing + token metrics
✅ Per-agent LanceDB isolation
✅ Receives agent_id + generates prompt → POST /agents to GeminiMesh
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import lancedb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# --- LOAD CONFIG ---
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINIMESH_API_URL = os.getenv("GEMINIMESH_API_URL", "https://api.geminimesh.com/api")
GEMINIMESH_API_TOKEN = os.getenv("GEMINIMESH_API_TOKEN")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))
BASE_DATA_FOLDER = os.getenv("DATA_FOLDER", "data")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY missing!")
if GEMINIMESH_API_TOKEN:
    print(f"✅ GeminiMesh POST API configured: {GEMINIMESH_API_URL}/agents")
else:
    print("⚠️  GEMINIMESH_API_TOKEN not configured")

genai.configure(api_key=API_KEY)

# Global embedding
embedding_model = None


def init_embedding_model():
    global embedding_model
    if embedding_model is None:
        print("🔄 Loading BAAI/bge-base-en-v1.5...")
        embedding_model = SentenceTransformer('BAAI/bge-base-en-v1.5')
        print("✅ Embedding ready")


# --- TEMPLATES ---
ANALYSIS_V5_TEMPLATE = """
--- ROUTING LOGIC (V5) ---
Classify into Profile 1 (RETRIEVAL '1-Yes') or Profile 2 (DIRECT '2-No').
Rule: If doubt, choose '1-Yes'. Reply ONLY '1-Yes' or '2-No'.
"""

CHEAP_ROUTER_TEMPLATE = """
CHEAP ROUTER (gemini-2.5-flash-lite) - 50 tokens max:

AGENT: {agent_name}
TOOLS: {tools_list}
QUERY: "{query}"

JSON ONLY:
{{
  "needs_rag": true/false,
  "tools_needed": ["RAG"]|["RAG","Calculator"]|[],
  "model_to_use": "gemini-3-pro-preview"|"gemini-3-flash-preview"|"gemini-2.5-flash",
  "reason": "1-sentence"
}}
"""

# --- FASTAPI ---
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI(title="Gemini Agent Factory v6.4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=[""])

print(f"🚀 v6.4 Dynamic Router + GeminiMesh Update on {HOST}:{PORT}")

# --- LANCEDB ---
retriever_cache: Dict[str, 'LanceRAG'] = {}


def get_agent_paths(agent_name: str):
    safe_name = "".join(c for c in agent_name if c.isalnum() or c in ('-', '_'))
    agent_dir = os.path.join(BASE_DATA_FOLDER, safe_name)
    os.makedirs(agent_dir, exist_ok=True)
    db_path = os.path.join(agent_dir, "lancedb")
    return agent_dir, db_path


class LanceRAG:
    EMBEDDING_DIM = 768

    def __init__(self, agent_dir: str, db_path: str):
        self.agent_dir = agent_dir
        self.db_path = db_path
        self.db = lancedb.connect(self.db_path)
        self.table_name = "documents"
        self._ensure_table()

    def _ensure_table(self):
        if self.table_name not in self.db.table_names():
            self.db.create_table(self.table_name, schema=[
                lancedb.schema.Vector(self.EMBEDDING_DIM),
                lancedb.schema.Col("id").str().primary_key(),
                lancedb.schema.Col("content").str(),
                lancedb.schema.Col("metadata").str(nullable=True),
                lancedb.schema.Col("created_at").int64(),
            ])

    def add_or_update_documents(self, docs: List[Dict[str, Any]]):
        global embedding_model
        init_embedding_model()
        vectors = [embedding_model.encode(doc["content"]).tolist() for doc in docs]
        data = [{
            "id": doc["id"], "content": doc["content"],
            "metadata": json.dumps(doc.get("metadata", {})),
            "created_at": int(time.time())
        } for doc in docs]
        self.db[self.table_name].add(data, vectors)

    def delete_document(self, doc_id: str):
        count = self.db[self.table_name].delete(f"id = '{doc_id}'")
        return count > 0

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        query_vector = embedding_model.encode([query])
        results = self.db[self.table_name].search(
            query_vector, query_type="vector", n_results=top_k
        ).limit(top_k).to_list()
        return [{"contents": r["content"], "score": r["_distance"]} for r in results]

    def count_documents(self) -> int:
        return len(self.db[self.table_name].search(lancedb.filter().match_all()).to_list())


def get_or_create_retriever(agent_name: str):
    if agent_name in retriever_cache:
        return retriever_cache[agent_name]
    init_embedding_model()
    agent_dir, db_path = get_agent_paths(agent_name)
    rag = LanceRAG(agent_dir, db_path)
    retriever_cache[agent_name] = rag
    return rag


# --- MODELS ---
class AgentConfig(BaseModel):
    agent_id: str  # REQUIRED for GeminiMesh updates
    name: str
    mode: str = "PERFORMANCE"
    instructions: List[str]
    tools: List[str] = []


class ChatRequest(BaseModel):
    agent_name: str
    message: str
    system_prompt: str


class UpdateAgentRequest(BaseModel):
    agent_name: str
    doc_id: Optional[str] = None
    action: str
    content: Optional[str] = None
    metadata: Optional[Dict] = None



# --- GEMINIMESH API ENDPOINT ---
@app.post("/update_agent_prompt_geminimesh")
async def update_agent_prompt_geminimesh(config: AgentConfig):
    """Receives agent_id + config → generates prompt → POST /agents to GeminiMesh."""

    if not GEMINIMESH_API_TOKEN:
        raise HTTPException(400, "❌ GEMINIMESH_API_TOKEN not configured in .env")

    # Validate required agent_id
    if not config.agent_id:
        raise HTTPException(400, "❌ agent_id is required to update agent")

    try:
        # Step 1: Generate optimized prompt locally
        model = genai.GenerativeModel("gemini-3-pro-preview")
        analysis_prompt = f"""
        AGENT: {config.name}, MODE: {config.mode}
        INSTRUCTIONS: {json.dumps(config.instructions)}
        TOOLS: {config.tools}

        JSON ONLY:
        {{
          "agent_type": "engineering|sales|research|creative|general",
          "complexity": "low|medium|high",
          "needs_rag": {bool(config.tools)}
        }}
        """

        analysis_raw = model.generate_content(analysis_prompt).text.strip()
        try:
            analysis = json.loads(analysis_raw)
        except:
            analysis = {"agent_type": "general", "complexity": "medium", "needs_rag": bool(config.tools)}

        optimized_prompt = f"""You are **{config.name}** ({config.mode}).

INSTRUCTIONS:
{chr(10).join(f"- {i}" for i in config.instructions)}

TOOLS: {', '.join(config.tools) if config.tools else 'None'}

{ANALYSIS_V5_TEMPLATE}

ANALYSIS: {json.dumps(analysis)}"""

        print(f"🧠 Generated optimized prompt for agent '{config.name}' (ID: {config.agent_id})")

        # Step 2: POST to GeminiMesh /agents with EXACT format
        response = requests.post(
            f"{GEMINIMESH_API_URL}/agents",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "agent_id": config.agent_id,  # For updates
                "name": config.name,
                "mode": config.mode,
                "prompt": optimized_prompt,
                "instructions": config.instructions,
                "tools": config.tools
            },
            timeout=30
        )

        if response.status_code in [200, 201, 202]:
            geminimesh_data = response.json()

            # Step 3: Initialize/update local RAG storage
            rag = get_or_create_retriever(config.name)

            return {
                "status": "success",
                "agent_id": config.agent_id,
                "geminimesh_response": geminimesh_data,
                "optimized_prompt": optimized_prompt,
                "local_rag_docs": rag.count_documents(),
                "message": f"Agent '{config.name}' (ID: {config.agent_id}) updated successfully"
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"GeminiMesh API error: {response.status_code} - {response.text}"
            )

    except requests.exceptions.RequestException as e:
        raise HTTPException(500, f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Error updating agent: {str(e)}")


@app.post("/optimize_prompt")
async def optimize_prompt(config: AgentConfig):
    """Standalone prompt optimization (no GeminiMesh call)."""
    try:
        model = genai.GenerativeModel("gemini-3-pro-preview")
    except Exception as e:
        raise HTTPException(400, f"Model error: {str(e)}")

    analysis_prompt = f"""
    AGENT: {config.name}, MODE: {config.mode}
    INSTRUCTIONS: {json.dumps(config.instructions)}
    TOOLS: {config.tools}

    JSON ONLY:
    {{
      "agent_type": "engineering|sales|research|creative|general",
      "complexity": "low|medium|high",
      "needs_rag": {bool(config.tools)}
    }}
    """

    analysis_raw = model.generate_content(analysis_prompt).text.strip()
    try:
        analysis = json.loads(analysis_raw)
    except:
        analysis = {"agent_type": "general", "complexity": "medium", "needs_rag": bool(config.tools)}

    system_prompt = f"""You are **{config.name}** ({config.mode}).

INSTRUCTIONS:
{chr(10).join(f"- {i}" for i in config.instructions)}

TOOLS: {', '.join(config.tools) if config.tools else 'None'}

{ANALYSIS_V5_TEMPLATE}

ANALYSIS: {json.dumps(analysis)}"""

    return {
        "optimized_prompt": system_prompt,
        "analysis": analysis,
        "model_used": "gemini-3-pro-preview"
    }


@app.post("/generate_stream")
async def generate_stream(request: ChatRequest):
    """v6.4: Cheap router → Dynamic generator."""

    # STEP 1: Extract tools from system_prompt
    tools_line = next((line for line in request.system_prompt.split('\n') if 'TOOLS:' in line), "TOOLS: []")
    tools_list = tools_line.split('TOOLS: ')[1].split('\n')[0] if 'TOOLS:' in tools_line else "[]"

    # STEP 2: CALL #1 - CHEAP ROUTER (gemini-2.5-flash-lite)
    cheap_model = genai.GenerativeModel("gemini-2.5-flash-lite")
    router_prompt = CHEAP_ROUTER_TEMPLATE.format(
        agent_name=request.agent_name,
        tools_list=tools_list,
        query=request.message
    )

    router_response = cheap_model.generate_content(router_prompt)
    try:
        tool_decision = json.loads(router_response.text.strip())
        print(f"🧠 Router: {tool_decision.get('tools_needed', [])} → {tool_decision.get('model_to_use')}")
    except:
        tool_decision = {
            "needs_rag": True, "tools_needed": ["RAG"],
            "model_to_use": "gemini-2.5-flash"
        }

    # STEP 3: Execute predicted tools
    rag = get_or_create_retriever(request.agent_name)
    context_str = ""
    docs_count = 0
    if tool_decision.get("needs_rag", False):
        results = rag.search(request.message)
        docs_count = len(results)
        context_str = "\n\n".join(r["contents"] for r in results)

    # STEP 4: CALL #2 - DYNAMIC GENERATOR MODEL
    generator_model_name = tool_decision.get("model_to_use", "gemini-2.5-flash")
    print(f"🔄 Dynamic switch → {generator_model_name}")

    try:
        generator_model = genai.GenerativeModel(generator_model_name)
    except Exception as e:
        generator_model_name = "gemini-2.5-flash"  # Fallback
        generator_model = genai.GenerativeModel(generator_model_name)

    full_prompt = f"""
[SYSTEM]{request.system_prompt}

[ROUTER]{json.dumps(tool_decision)}

[CONTEXT]{context_str}

[QUERY]{request.message}
"""
    input_chars = len(full_prompt)

    async def two_call_stream():
        # Router decision to client
        yield json.dumps({
            "router_decision": tool_decision,
            "metrics": {
                "call_count": 1,
                "router_model": "gemini-2.5-flash-lite",
                "generator_model": generator_model_name,
                "tools_executed": tool_decision.get("tools_needed", []),
                "docs_retrieved": docs_count
            }
        }) + "\n"

        # CALL #2: Dynamic model generation
        output_chars = 0
        output_tokens = 0

        stream_resp = generator_model.generate_content(full_prompt, stream=True)
        for chunk in stream_resp:
            if chunk.text:
                output_chars += len(chunk.text)
                output_tokens += len(chunk.text) // 4

                yield json.dumps({
                    "text": chunk.text,
                    "metrics": {
                        "call_count": 2,
                        "input_chars": input_chars,
                        "output_chars": output_chars,
                        "input_tokens": input_chars // 4,
                        "output_tokens": output_tokens,
                        "generator_model": generator_model_name
                    }
                }) + "\n"

        # Final metrics
        yield json.dumps({
            "text": "",
            "is_final": True,
            "metrics": {
                "total_calls": 2,
                "router_model": "gemini-2.5-flash-lite",
                "generator_model": generator_model_name,
                "tools_used": tool_decision.get("tools_needed", []),
                "docs_retrieved": docs_count,
                "total_docs": rag.count_documents(),
                "total_tokens": output_tokens
            }
        }) + "\n"

    return StreamingResponse(two_call_stream(), media_type="application/x-ndjson")


@app.post("/update_agent_index")
async def update_agent_index(request: UpdateAgentRequest):
    rag = get_or_create_retriever(request.agent_name)
    action = request.action.lower()

    if action in ["add", "update"]:
        doc_data = json.loads(request.content)
        if not doc_data.get("id"):
            doc_data["id"] = f"doc_{int(time.time())}"
        if request.metadata:
            doc_data["metadata"] = request.metadata
        rag.add_or_update_documents([doc_data])
    elif action == "delete":
        if not rag.delete_document(request.doc_id):
            raise HTTPException(404, f"Doc not found")

    return {"status": "success", "total_docs": rag.count_documents()}


@app.post("/upload_and_index")
async def upload_and_index(agent_name: str = Form(...), file: UploadFile = File(...)):
    rag = get_or_create_retriever(agent_name)
    content = await file.read()
    lines = content.decode('utf-8').splitlines()
    docs = []

    for i, line in enumerate(lines):
        try:
            doc = json.loads(line.strip())
            if not doc.get("id"):
                doc["id"] = f"upload_{agent_name}_{i}"
            docs.append(doc)
        except:
            continue

    if docs:
        rag.add_or_update_documents(docs)

    return {"status": "success", "docs_added": len(docs), "total_docs": rag.count_documents()}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agents": list(retriever_cache.keys()),
        "geminimesh_configured": bool(GEMINIMESH_API_TOKEN),
        "embedding_model": "loaded" if embedding_model else "not_loaded"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, reload=True)