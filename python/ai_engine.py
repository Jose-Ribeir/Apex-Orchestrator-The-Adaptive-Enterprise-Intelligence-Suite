#!/usr/bin/env python3
"""
🏆 GEMINI AGENT FACTORY v6.7 - AI STUDIO EDITION
✅ ALL MODELS: Mapped to valid AI Studio IDs
✅ SDK: google.generativeai (No Vertex AI)
✅ RAG + Detailed logs
✅ FIX: Retry Logic for 429 Rate Limits
✅ FIX: GeminiMesh Sync uses PATCH /agents/{id}
✅ FIX: Robust Embedding Loading (Local Cache + MiniLM)
✅ FIX: LanceDB Schema (Pydantic) + Lazy Embedding Load
"""

import os
import json
import time
import requests
import traceback
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import lancedb
from lancedb.pydantic import LanceModel, Vector
from sentence_transformers import SentenceTransformer
import logging

# --- LOGGING (FIXED: UTF-8 encoding) ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(), logging.FileHandler('ai_engine.log', encoding='utf-8')])
logger = logging.getLogger(__name__)

# --- CONFIG ---
load_dotenv()

# 🔥 FIX: Unset conflicting Google Cloud variables to force API Key usage
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
if "GOOGLE_CLOUD_PROJECT" in os.environ:
    del os.environ["GOOGLE_CLOUD_PROJECT"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINIMESH_API_URL = os.getenv("GEMINIMESH_API_URL", "https://api.geminimesh.com/api").rstrip('/')
GEMINIMESH_API_TOKEN = os.getenv("GEMINIMESH_API_TOKEN")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
BASE_DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
MODEL_CACHE_FOLDER = os.path.join(BASE_DATA_FOLDER, "model_cache")
os.makedirs(MODEL_CACHE_FOLDER, exist_ok=True)

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY missing! Please add it to your .env file.")

print("🔥 GEMINI FACTORY - AI STUDIO EDITION")
print(f"🔧 TEST MODE: {'🟢 ON' if TEST_MODE else '🔴 OFF'}")

# ✅ AI Studio Setup
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

genai.configure(api_key=GEMINI_API_KEY)
print("✅ Google AI Studio - READY")

embedding_model = None


def init_embedding_model():
    global embedding_model
    if embedding_model is None:
        print(f"🔄 Loading embedding model to {MODEL_CACHE_FOLDER}...")
        try:
            # 🔥 FIX: Use standard MiniLM and local cache
            embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',
                                                  cache_folder=MODEL_CACHE_FOLDER)
            print("✅ Embedding ready")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            logger.error(traceback.format_exc())
            raise e


def get_model_name(model_name: str, is_test_mode: bool = TEST_MODE) -> str:
    mapping = {
        "gemini-3-pro-preview": "gemini-1.5-pro",
        "gemini-3-pro": "gemini-1.5-pro",
        "gemini-3-flash-preview": "gemini-2.0-flash",
        "gemini-3-flash": "gemini-2.0-flash",
        "gemini-3.0-flash-preview": "gemini-2.0-flash",
        "gemini-2.5-flash-lite": "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.5-flash": "gemini-2.0-flash",
        "router": "gemini-2.0-flash",
        "default": "gemini-2.0-flash"
    }
    valid_model = mapping.get(model_name, "gemini-2.0-flash")
    if is_test_mode:
        print(f"🧪 TEST MODE: '{model_name}' → '{valid_model}' ⚡")
        return valid_model
    print(f"🔥 MODEL MAP: '{model_name}' → '{valid_model}'")
    return valid_model


def generate_content(model_name: str, prompt: str, stream: bool = False) -> Any:
    final_model = get_model_name(model_name)
    logger.info(f"AI STUDIO CALL: '{final_model}' (prompt={len(prompt)} chars, stream={stream})")

    model = genai.GenerativeModel(final_model)
    config = genai.types.GenerationConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain"
    )

    max_retries = 5
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, generation_config=config, stream=stream)
            logger.info(f"AI STUDIO SUCCESS: {final_model}")
            return response
        except google_exceptions.ResourceExhausted:
            wait_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                f"⚠️ Rate limit hit (429). Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"AI STUDIO FAILED '{final_model}': {e}")
            logger.error(traceback.format_exc())
            raise

    raise Exception(f"Failed after {max_retries} retries due to Rate Limiting (429).")


# --- TEMPLATES ---
ANALYSIS_V5_TEMPLATE = """
--- ROUTING LOGIC (V5) ---
Classify into Profile 1 (RETRIEVAL '1-Yes') or Profile 2 (DIRECT '2-No').
Rule: If doubt, choose '1-Yes'. Reply ONLY '1-Yes' or '2-No'.
"""

CHEAP_ROUTER_TEMPLATE = """
🔥 ROUTER (gemini-2.0-flash):

AGENT ID: {agent_id}
TOOLS: {tools_list}
QUERY: "{query}"

JSON ONLY: {{"needs_rag":true/false,"tools_needed":["RAG"]|[], "model_to_use":"gemini-3-pro-preview"|"gemini-3-flash-preview","reason":"1-sentence"}}
"""

# --- FASTAPI ---
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI(title="Gemini Agent Factory v6.7 - AI STUDIO EDITION")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

print(f"🚀 v6.7 AI STUDIO EDITION on {HOST}:{PORT}")

# --- LANCEDB ---
retriever_cache: Dict[str, 'LanceRAG'] = {}


def get_agent_paths(agent_id: str):
    safe_id = "".join(c for c in agent_id if c.isalnum() or c in ('-', '_'))
    agent_dir = os.path.join(BASE_DATA_FOLDER, safe_id)
    os.makedirs(agent_dir, exist_ok=True)
    db_path = os.path.join(agent_dir, "lancedb")
    return agent_dir, db_path


# 🔥 FIX: Pydantic Model for LanceDB Schema
class AgentDoc(LanceModel):
    vector: Vector(384)  # Fixed dim for MiniLM
    id: str
    content: str
    metadata: str
    created_at: int


class LanceRAG:
    def __init__(self, agent_dir: str, db_path: str):
        self.agent_dir = agent_dir
        self.db_path = db_path
        self.db = lancedb.connect(self.db_path)
        self.table_name = "documents"
        self._ensure_table()

    def _ensure_table(self):
        if self.table_name not in self.db.table_names():
            # 🔥 FIX: Use Pydantic schema
            self.db.create_table(self.table_name, schema=AgentDoc)

    def add_or_update_documents(self, docs: List[Dict[str, Any]]):
        # 🔥 Lazy Load: Only load model when adding docs
        init_embedding_model()

        vectors = [embedding_model.encode(doc["content"]).tolist() for doc in docs]
        data = [{"id": doc["id"], "content": doc["content"], "metadata": json.dumps(doc.get("metadata", {})),
                 "created_at": int(time.time()), "vector": v} for doc, v in zip(docs, vectors)]

        self.db[self.table_name].add(data)

    def delete_document(self, doc_id: str):
        count = self.db[self.table_name].delete(f"id = '{doc_id}'")
        return count > 0

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        # 🔥 Lazy Load: Only load model when searching
        init_embedding_model()

        query_vector = embedding_model.encode([query])[0]
        results = self.db[self.table_name].search(query_vector).limit(top_k).to_list()
        return [{"contents": r["content"], "score": r["_distance"]} for r in results]

    def count_documents(self) -> int:
        # Does NOT require embedding model
        return len(self.db[self.table_name].search().limit(10000).to_list())


def get_or_create_retriever(agent_id: str):
    if agent_id in retriever_cache: return retriever_cache[agent_id]
    # 🔥 FIX: Removed init_embedding_model() from here!
    agent_dir, db_path = get_agent_paths(agent_id)
    rag = LanceRAG(agent_dir, db_path)
    retriever_cache[agent_id] = rag
    return rag


# --- MODELS ---
class AgentConfig(BaseModel):
    agent_id: str
    name: str
    mode: str = "PERFORMANCE"
    instructions: List[str]
    tools: List[str] = []


class ChatRequest(BaseModel):
    agent_id: str
    message: str
    system_prompt: str


class UpdateAgentRequest(BaseModel):
    agent_id: str
    doc_id: Optional[str] = None
    action: str
    content: Optional[str] = None
    metadata: Optional[Dict] = None


# --- ENDPOINTS ---

@app.post("/set_test_mode")
async def set_test_mode(test_mode: bool):
    global TEST_MODE
    old_mode = TEST_MODE
    TEST_MODE = test_mode
    status = "🟢 ON" if TEST_MODE else "🔴 OFF"
    logger.info(f"Test Mode: {old_mode} → {TEST_MODE}")
    return {"status": "success", "test_mode": TEST_MODE, "description": status}


@app.get("/test_mode")
async def get_test_mode():
    status = "🟢 ON" if TEST_MODE else "🔴 OFF"
    return {"test_mode": TEST_MODE, "description": status}


@app.post("/update_agent_prompt_geminimesh")
async def update_agent_prompt_geminimesh(config: AgentConfig, test_mode: bool = Query(TEST_MODE)):
    print(f"🔥 UPDATING AGENT: '{config.name}' (ID: {config.agent_id})")

    # 🔥 STEP 1: DETERMINE ANALYSIS FROM INPUT (NO MODEL CALL!)
    analysis = {
        "agent_type": "engineering" if "code" in " ".join(config.instructions).lower() else "general",
        "complexity": "high" if len(config.instructions) > 3 or config.tools else "medium",
        "needs_rag": bool(config.tools)
    }
    print(f"📊 ANALYSIS (from data): {analysis}")

    # 🔥 STEP 2: MODEL GENERATES INSTRUCTIONS ONLY (gemini-1.5-pro)
    model_name = get_model_name("gemini-1.5-pro", test_mode)
    instruction_prompt = f"""Create optimized instructions for agent '{config.name}' ({config.mode}).

INPUT DATA:
- Instructions: {json.dumps(config.instructions)}
- Tools: {config.tools}
- Analysis: {json.dumps(analysis)}

OUTPUT ONLY THE INSTRUCTIONS as clean bullet points. No JSON, no explanations.

EXAMPLE:
- You are a helpful assistant
- Always use tools when available
- Keep responses concise"""

    print(f"🔄 Generating instructions: {model_name}")
    response = generate_content(model_name, instruction_prompt)
    optimized_instructions = response.text.strip().split('\n')
    optimized_instructions = [line.strip('- ').strip() for line in optimized_instructions if line.strip()]

    # 🔥 STEP 3: BUILD FINAL PROMPT (NO ANALYSIS NEEDED)
    final_prompt = f"""You are **{config.name}** ({config.mode}).
{chr(10).join(f'- {instr}' for instr in optimized_instructions)}
TOOLS: {', '.join(config.tools) if config.tools else 'None'}"""

    print(f"✅ FINAL PROMPT:\n{final_prompt}")

    # 🔥 STEP 4: GEMINIMESH (MANDATORY)
    if not GEMINIMESH_API_TOKEN:
        raise HTTPException(400, "❌ GEMINIMESH_API_TOKEN required!")

    payload = {
        "name": config.name,
        "mode": config.mode,
        "prompt": final_prompt,
        "instructions": optimized_instructions,  # ← Model-generated!
        "tools": config.tools
    }

    response = requests.patch(f"{GEMINIMESH_API_URL}/agents/{config.agent_id}",
                              headers={"Content-Type": "application/json",
                                       "Authorization": f"Bearer {GEMINIMESH_API_TOKEN}"},
                              json=payload, timeout=30)

    if response.status_code not in [200, 201, 202, 204]:
        raise HTTPException(response.status_code, f"❌ GeminiMesh: {response.text}")

    # Local RAG
    rag = get_or_create_retriever(config.agent_id)

    return {
        "status": "success",
        "model_used": model_name,
        "analysis": analysis,
        "optimized_instructions": optimized_instructions,
        "final_prompt": final_prompt,
        "geminimesh": response.json() if response.content else {"status": "success"},
        "rag_docs": rag.count_documents()
    }


@app.post("/update_agent_prompt_geminimesh")
async def update_agent_prompt_geminimesh(config: AgentConfig, test_mode: bool = Query(TEST_MODE)):
    print(f"🔥 UPDATING AGENT: '{config.name}' (ID: {config.agent_id})")

    # 🔥 STEP 1: DETERMINE ANALYSIS FROM INPUT (NO MODEL CALL!)
    analysis = {
        "agent_type": "engineering" if "code" in " ".join(config.instructions).lower() else "general",
        "complexity": "high" if len(config.instructions) > 3 or config.tools else "medium",
        "needs_rag": bool(config.tools)
    }
    print(f"📊 ANALYSIS (from data): {analysis}")

    # 🔥 STEP 2: MODEL GENERATES INSTRUCTIONS ONLY (gemini-1.5-pro)
    model_name = get_model_name("gemini-1.5-pro", test_mode)
    instruction_prompt = f"""Create optimized instructions for agent '{config.name}' ({config.mode}).

INPUT DATA:
- Instructions: {json.dumps(config.instructions)}
- Tools: {config.tools}
- Analysis: {json.dumps(analysis)}

OUTPUT ONLY THE INSTRUCTIONS as clean bullet points. No JSON, no explanations.

EXAMPLE:
- You are a helpful assistant
- Always use tools when available
- Keep responses concise"""

    print(f"🔄 Generating instructions: {model_name}")
    response = generate_content(model_name, instruction_prompt)
    optimized_instructions = response.text.strip().split('\n')
    optimized_instructions = [line.strip('- ').strip() for line in optimized_instructions if line.strip()]

    # 🔥 STEP 3: BUILD FINAL PROMPT (NO ANALYSIS NEEDED)
    final_prompt = f"""You are **{config.name}** ({config.mode}).
{chr(10).join(f'- {instr}' for instr in optimized_instructions)}
TOOLS: {', '.join(config.tools) if config.tools else 'None'}"""

    print(f"✅ FINAL PROMPT:\n{final_prompt}")

    # 🔥 STEP 4: GEMINIMESH (MANDATORY)
    if not GEMINIMESH_API_TOKEN:
        raise HTTPException(400, "❌ GEMINIMESH_API_TOKEN required!")

    payload = {
        "name": config.name,
        "mode": config.mode,
        "prompt": final_prompt,
        "instructions": optimized_instructions,  # ← Model-generated!
        "tools": config.tools
    }

    response = requests.patch(f"{GEMINIMESH_API_URL}/agents/{config.agent_id}",
                              headers={"Content-Type": "application/json",
                                       "Authorization": f"Bearer {GEMINIMESH_API_TOKEN}"},
                              json=payload, timeout=30)

    if response.status_code not in [200, 201, 202, 204]:
        raise HTTPException(response.status_code, f"❌ GeminiMesh: {response.text}")

    # Local RAG
    rag = get_or_create_retriever(config.agent_id)

    return {
        "status": "success",
        "model_used": model_name,
        "analysis": analysis,
        "optimized_instructions": optimized_instructions,
        "final_prompt": final_prompt,
        "geminimesh": response.json() if response.content else {"status": "success"},
        "rag_docs": rag.count_documents()
    }

@app.post("/optimize_prompt")
async def optimize_prompt(config: AgentConfig, test_mode: bool = Query(TEST_MODE)):
    model_name = get_model_name("gemini-3-pro-preview", test_mode)
    analysis_prompt = f"""
    AGENT: {config.name}, MODE: {config.mode}
    INSTRUCTIONS: {json.dumps(config.instructions)}
    TOOLS: {config.tools}
    JSON ONLY: {{"agent_type": "engineering|sales|research|creative|general", "complexity": "low|medium|high", "needs_rag": {bool(config.tools)}}}
    """

    analysis_response = generate_content(model_name, analysis_prompt)
    analysis_raw = analysis_response.text.strip()

    try:
        analysis = json.loads(analysis_raw)
    except:
        analysis = {"agent_type": "general", "complexity": "medium", "needs_rag": bool(config.tools)}

    system_prompt = f"""You are **{config.name}** ({config.mode}).
INSTRUCTIONS:\n{chr(10).join(f"- {i}" for i in config.instructions)}
TOOLS: {', '.join(config.tools) if config.tools else 'None'}
{ANALYSIS_V5_TEMPLATE}
ANALYSIS: {json.dumps(analysis)}"""

    return {
        "optimized_prompt": system_prompt,
        "analysis": analysis,
        "model_used": model_name,
        "test_mode": test_mode
    }


@app.post("/generate_stream")
async def generate_stream(request: ChatRequest, test_mode: bool = Query(TEST_MODE)):
    """🔥 2-CALL PIPELINE"""

    # Extract tools
    tools_list = next(
        (line.split('TOOLS: ')[1].split('\n')[0] for line in request.system_prompt.split('\n') if 'TOOLS:' in line),
        "[]")

    # 🔥 CALL #1: ROUTER
    router_model = get_model_name("gemini-3-flash-preview", test_mode)
    router_prompt = CHEAP_ROUTER_TEMPLATE.format(agent_id=request.agent_id, tools_list=tools_list,
                                                 query=request.message)
    router_response = generate_content(router_model, router_prompt)

    try:
        tool_decision = json.loads(router_response.text.strip())
    except:
        tool_decision = {"needs_rag": True, "tools_needed": ["RAG"], "model_to_use": "gemini-3-flash-preview"}

    # RAG
    rag = get_or_create_retriever(request.agent_id)
    context_str = ""
    if tool_decision.get("needs_rag"):
        results = rag.search(request.message)
        context_str = "\n\n".join(r["contents"] for r in results)

    # 🔥 CALL #2: GENERATOR
    generator_model = get_model_name(tool_decision.get("model_to_use", "gemini-3-flash-preview"))
    full_prompt = f"[SYSTEM]{request.system_prompt}\n[ROUTER]{json.dumps(tool_decision)}\n[CONTEXT]{context_str}\n[QUERY]{request.message}"

    async def stream():
        yield json.dumps(
            {"router_decision": tool_decision, "models": {"router": router_model, "generator": generator_model},
             "metrics": {"call": 1}}) + "\n"

        stream_resp = generate_content(generator_model, full_prompt, stream=True)
        for chunk in stream_resp:
            if hasattr(chunk, 'text') and chunk.text:
                yield json.dumps(
                    {"text": chunk.text, "models": {"router": router_model, "generator": generator_model}}) + "\n"

        yield json.dumps(
            {"text": "", "is_final": True, "models": {"router": router_model, "generator": generator_model}}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/update_agent_index")
async def update_agent_index(request: UpdateAgentRequest):
    rag = get_or_create_retriever(request.agent_id)
    action = request.action.lower()
    if action in ["add", "update"]:
        doc_data = json.loads(request.content)
        doc_data["id"] = doc_data.get("id", f"doc_{int(time.time())}")
        if request.metadata: doc_data["metadata"] = request.metadata
        rag.add_or_update_documents([doc_data])
    elif action == "delete":
        if not rag.delete_document(request.doc_id):
            raise HTTPException(404, "Doc not found")
    return {"status": "success", "total_docs": rag.count_documents()}


@app.post("/upload_and_index")
async def upload_and_index(agent_id: str = Form(...), file: UploadFile = File(...)):
    rag = get_or_create_retriever(agent_id)
    content = await file.read()
    lines = content.decode('utf-8').splitlines()
    docs = []
    for i, line in enumerate(lines):
        try:
            doc = json.loads(line.strip())
            if not doc.get("id"): doc["id"] = f"upload_{agent_id}_{i}"
            docs.append(doc)
        except:
            continue
    if docs: rag.add_or_update_documents(docs)
    return {"status": "success", "docs_added": len(docs), "total_docs": rag.count_documents()}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "test_mode": TEST_MODE,
        "client_status": "ai_studio_active",
        "log_file": "ai_engine.log",
        "agent_ids": list(retriever_cache.keys()),
        "geminimesh_configured": bool(GEMINIMESH_API_TOKEN)
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ai_engine:app", host=HOST, port=PORT, reload=True, log_level="info")