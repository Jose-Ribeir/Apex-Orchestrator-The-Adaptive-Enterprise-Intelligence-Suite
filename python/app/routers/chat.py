"""Streaming chat with 2-call router + dynamic generator."""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.requests import ChatRequest
from app.services.gemini_router import run_cheap_router, run_generator_stream
from app.services.rag import get_or_create_retriever

router = APIRouter(tags=["Chat"])


def _run_stream_pipeline(request: ChatRequest):
    """Blocking: router + RAG + generator stream. Yields NDJSON lines."""
    tools_line = next(
        (line for line in request.system_prompt.split("\n") if "TOOLS:" in line),
        "TOOLS: []",
    )
    tools_list = tools_line.split("TOOLS: ")[1].split("\n")[0] if "TOOLS:" in tools_line else "[]"
    tool_decision = run_cheap_router(
        agent_name=request.agent_name,
        tools_list=tools_list,
        query=request.message,
    )
    rag = get_or_create_retriever(request.agent_name)
    context_str = ""
    docs_count = 0
    if tool_decision.get("needs_rag", False):
        results = rag.search(request.message)
        docs_count = len(results)
        context_str = "\n\n".join(r["contents"] for r in results)
    generator_model_name = tool_decision.get("model_to_use", "gemini-2.5-flash")
    full_prompt = f"""
[SYSTEM]{request.system_prompt}

[ROUTER]{json.dumps(tool_decision)}

[CONTEXT]{context_str}

[QUERY]{request.message}
"""
    input_chars = len(full_prompt)
    total_docs = rag.count_documents()

    first_line = (
        json.dumps(
            {
                "router_decision": tool_decision,
                "metrics": {
                    "call_count": 1,
                    "router_model": "gemini-2.5-flash-lite",
                    "generator_model": generator_model_name,
                    "tools_executed": tool_decision.get("tools_needed", []),
                    "docs_retrieved": docs_count,
                },
            }
        )
        + "\n"
    )
    yield first_line
    yield from run_generator_stream(
        full_prompt,
        generator_model_name,
        tool_decision,
        input_chars,
        docs_count,
        total_docs,
    )


@router.post(
    "/generate_stream",
    summary="Stream chat with 2-call pipeline",
    description="Call #1: cheap router (gemini-2.5-flash-lite) decides needs_rag, tools_needed, model_to_use. "
    "Call #2: dynamic generator (e.g. gemini-3-pro-preview or gemini-2.5-flash) streams the response. "
    "Returns NDJSON stream: first line router_decision + metrics, then text chunks with metrics, then final metrics.",
    operation_id="generateStream",
)
async def generate_stream(request: ChatRequest):
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def put(chunk: str | None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, chunk)

    def worker() -> None:
        try:
            for line in _run_stream_pipeline(request):
                put(line)
        finally:
            put(None)

    loop.run_in_executor(None, worker)

    async def ndjson_stream():
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

    return StreamingResponse(
        ndjson_stream(),
        media_type="application/x-ndjson",
    )
