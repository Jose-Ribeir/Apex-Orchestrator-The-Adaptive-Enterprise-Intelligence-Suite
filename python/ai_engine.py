import os
import json
import time
import torch
import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from dotenv import load_dotenv

# --- LOAD ENVIRONMENT VARIABLES FIRST ---
load_dotenv()

# --- CONFIGURATION FROM .env ---
API_KEY = os.getenv("GEMINI_API_KEY")
# This is now just a DEFAULT fallback, not the only option
DEFAULT_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
FLASH_RAG_PATH = os.getenv("FLASH_RAG_PATH")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8000))
BASE_DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
CORPUS_FILENAME = "uploaded_docs.jsonl"
INDEX_DIR_NAME = "flashrag_index"

# Validate critical config
if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY missing from .env!")
if not FLASH_RAG_PATH or not Path(FLASH_RAG_PATH).exists():
    print("⚠️ FLASH_RAG_PATH not found or invalid")
else:
    if FLASH_RAG_PATH not in sys.path:
        sys.path.append(FLASH_RAG_PATH)

# Gemini Setup
import google.generativeai as genai

genai.configure(api_key=API_KEY)
# Note: We do NOT initialize a global 'model' here anymore.
# We do it per-request to support multiple models.

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI(title="Gemini Agent Factory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"🚀 Server starting on {HOST}:{PORT}")
print(f"📁 Base Data Folder: {BASE_DATA_FOLDER}")
print(f"🤖 Default Model: {DEFAULT_MODEL_NAME}")

# --- RAG SYSTEM (Multi-Agent) ---
retriever_cache = {}


def get_agent_paths(agent_name: str):
    """Helper to get paths for a specific agent and ensure directory exists."""
    safe_name = "".join([c for c in agent_name if c.isalnum() or c in ('-', '_')])
    agent_dir = os.path.join(BASE_DATA_FOLDER, safe_name)

    if not os.path.exists(agent_dir):
        os.makedirs(agent_dir, exist_ok=True)

    corpus_path = os.path.join(agent_dir, CORPUS_FILENAME)
    index_path = os.path.join(agent_dir, INDEX_DIR_NAME, "bge_Flat.index")
    index_dir = os.path.join(agent_dir, INDEX_DIR_NAME)
    return agent_dir, corpus_path, index_path, index_dir


def get_or_load_retriever(agent_name: str):
    if agent_name in retriever_cache:
        return retriever_cache[agent_name]

    _, corpus_path, index_path, _ = get_agent_paths(agent_name)

    if not os.path.exists(index_path):
        return None

    try:
        from flashrag.config import Config
        from flashrag.utils import get_retriever

        print(f"🔄 Loading RAG index for agent: {agent_name}...")
        config_dict = {
            "retrieval_method": "bge",
            "retrieval_topk": int(os.getenv("RAG_TOPK", 5)),
            "corpus_path": corpus_path,
            "index_path": index_path,
            "instruction": os.getenv("RAG_INSTRUCTION", "Represent this sentence for searching relevant passages:"),
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
        config = Config(config_dict=config_dict)
        retriever = get_retriever(config)
        retriever_cache[agent_name] = retriever
        print(f"✅ RAG Loaded for {agent_name}")
        return retriever
    except Exception as e:
        print(f"❌ RAG Load Error for {agent_name}: {e}")
        return None


# --- DATA MODELS ---
class AgentConfig(BaseModel):
    name: str
    mode: str
    instructions: List[str]
    tools: List[str]
    # Allow user to specify model for optimization, default to env var
    model_name: str = DEFAULT_MODEL_NAME


class ChatRequest(BaseModel):
    agent_name: str
    message: str
    system_prompt: str
    # Allow user to specify model for chat, default to env var
    model_name: str = DEFAULT_MODEL_NAME


# --- ANALYSIS TEMPLATE ---
ANALYSIS_V5_TEMPLATE = (
    "--- ROUTING LOGIC (V5) ---\n"
    "You are a query classification expert. Classify the query into Profile 1 or Profile 2.\n"
    "--- PROFILE 1: RETRIEVAL REQUIRED ('1-Yes') ---\n"
    "Choose this if the query requires external, specific, or up-to-date knowledge.\n"
    "--- PROFILE 2: DIRECT ANSWER SUFFICIENT ('2-No') ---\n"
    "Choose this if the query is self-contained, common knowledge, or creative.\n"
    "**Decision Rule:** If in doubt, choose '1-Yes'.\n"
    "**IMPORTANT** Reply ONLY with '1-Yes' or '2-No'."
)


# --- ENDPOINTS ---

@app.post("/optimize_prompt")
async def optimize_prompt(config: AgentConfig):
    # Initialize the specific model requested
    try:
        current_model = genai.GenerativeModel(config.model_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid model name '{config.model_name}': {str(e)}")

    mode_instruction = {
        "PERFORMANCE": "Prioritize accuracy, detail, thoroughness. Double-check reasoning.",
        "EFFICIENCY": "Prioritize concise, direct answers. Skip unnecessary retrieval."
    }.get(config.mode, "")

    tools_list = ", ".join(config.tools) if config.tools else "No tools."
    raw_instructions = "\n".join(f"- {instr}" for instr in config.instructions)

    meta_prompt = f"""You are an expert AI Architect. Compile SYSTEM PROMPT from:

Name: {config.name}
Mode: {config.mode} ({mode_instruction})
Tools: {tools_list}
Guidelines:
{raw_instructions}

{ANALYSIS_V5_TEMPLATE}

Output ONLY the final System Prompt."""

    try:
        response = current_model.generate_content(meta_prompt)
        return {"optimized_prompt": response.text, "model_used": config.model_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini Error: {str(e)}")


async def decide_path(query, system_prompt, model_instance):
    """Uses the provided model instance to decide routing."""
    routing_check = f"{system_prompt}\n\n[TASK] Analyze: {query}\nReply ONLY '1-Yes' or '2-No'."
    try:
        response = model_instance.generate_content(routing_check)
        return "retrieval" if "1-Yes" in response.text else "direct"
    except:
        return "direct"


@app.post("/generate_stream")
async def generate_stream(request: ChatRequest):
    # 1. Initialize the specific model requested by the user
    try:
        current_model = genai.GenerativeModel(request.model_name)
    except Exception as e:
        # Fallback or error if model name is invalid
        yield json.dumps({"error": f"Invalid model name: {str(e)}"}) + "\n"
        return

    # 2. Decide path using the selected model
    method = await decide_path(request.message, request.system_prompt, current_model)

    agent_retriever = get_or_load_retriever(request.agent_name)

    context_str = ""
    retrieved_docs = []

    if method == "retrieval" and agent_retriever:
        try:
            results = agent_retriever.search(request.message)
            retrieved_docs = [doc['contents'] for doc in results]
            context_str = "\n".join(retrieved_docs)
        except Exception as e:
            context_str = f"RAG Error: {e}"
    elif method == "retrieval" and not agent_retriever:
        context_str = "No knowledge base found for this agent."

    full_prompt = f"""[SYSTEM] {request.system_prompt}

[CONTEXT] Method: {method}
{context_str or 'No context.'}

[USER] {request.message}"""

    async def stream():
        yield json.dumps(
            {"text": "", "is_final": False, "metrics": {"method": method, "model": request.model_name}}) + "\n"

        try:
            # 3. Generate content using the selected model
            stream_response = current_model.generate_content(full_prompt, stream=True)
            total_tokens = 0
            start = time.time()

            for chunk in stream_response:
                if chunk.text:
                    total_tokens += len(chunk.text) // 4
                    yield json.dumps({
                        "text": chunk.text,
                        "is_final": False,
                        "metrics": {"tokens": total_tokens}
                    }) + "\n"

            yield json.dumps({
                "text": "",
                "is_final": True,
                "metrics": {
                    "total_tokens": total_tokens,
                    "duration": round(time.time() - start, 2),
                    "docs": len(retrieved_docs),
                    "rag_active": agent_retriever is not None,
                    "model_used": request.model_name
                }
            }) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/upload_and_index")
async def upload_and_index(
        background_tasks: BackgroundTasks,
        agent_name: str = Form(...),
        file: UploadFile = File(...)
):
    agent_dir, corpus_path, _, index_dir = get_agent_paths(agent_name)

    with open(corpus_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    def index_docs_task(a_name, c_path, i_dir):
        print(f"🔨 Starting indexing for agent: {a_name}")
        subprocess.run([
            "python", "-m", "flashrag.retriever.index_builder",
            "--retrieval_method", "bge",
            "--model_path", "BAAI/bge-base-en-v1.5",
            "--corpus_path", c_path,
            "--save_dir", i_dir,
            "--faiss_type", "Flat"
        ], cwd=FLASH_RAG_PATH, capture_output=True)

        if a_name in retriever_cache:
            del retriever_cache[a_name]
        get_or_load_retriever(a_name)
        print(f"✅ Indexing complete for agent: {a_name}")

    background_tasks.add_task(index_docs_task, agent_name, corpus_path, index_dir)
    return {"status": "queued", "agent": agent_name, "path": corpus_path}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "loaded_agents": list(retriever_cache.keys()),
        "default_model": DEFAULT_MODEL_NAME,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, reload=True)