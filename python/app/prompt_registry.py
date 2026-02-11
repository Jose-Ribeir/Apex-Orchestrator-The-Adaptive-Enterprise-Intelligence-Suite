"""Registry of full-text descriptions for tools and modes. Used at prompt-build time to adapt
system and optimized prompts to the agent's tools and mode (keywords only in config/DB).
"""

import json
from typing import Any

# ---------------------------------------------------------------------------
# Tool registry: name (keyword) -> full text (what it does, when to use, how to act when required)
# ---------------------------------------------------------------------------

TOOL_PROMPT_TEXTS: dict[str, str] = {
    "RAG": """RAG (Retrieval-Augmented Generation): Retrieves relevant passages from the agent's knowledge base (uploaded documents) and injects them into the context.
When to use: When the user asks about facts, documents, policies, or data that may be in the agent's indexed content. The router may set needs_rag=true.
When RAG is required or context is provided: Use the [CONTEXT] section in the prompt as the primary source. Base your answer on the retrieved passages; cite or reference them. Do not invent facts that are not in the context. If the context is empty but RAG was requested, say so and answer from general knowledge only when appropriate.""",

    "Web Search": """Web Search: Allows querying the live web for current information, documentation, or external references.
When to use: When the user needs up-to-date information, external URLs, or content not in the agent's knowledge base. The router may include this in tools_needed.
When Web Search is required: Rely on the search results or context provided. Prefer citing sources. If no results are given, state that and suggest the user rephrase or try later.""",

    "Python Interpreter": """Python Interpreter: Runs Python code (e.g. calculations, data processing, file parsing) in a sandboxed environment.
When to use: When the user needs computation, data analysis, CSV/JSON parsing, or scripted logic. The router may include this in tools_needed.
When Python is required: Use the tool to run code when the task clearly needs it. Summarize the code and results in your response. Do not execute code that could be unsafe or that the user did not ask for.""",

    "human-in-loop": """Human-in-the-loop: Escalates the conversation or decision to a human (e.g. supervisor, support agent) when the situation requires it.
When to use: For complaints, refunds, safety-critical decisions, out-of-scope requests, or when the situation clearly requires human review.
When human-in-loop is required: First write a complete, natural response to the user (acknowledge their concern, set expectations, e.g. "I understand. I'm going to have someone look into this for you and they'll follow up shortly."). Only after your full reply, output the exact phrase: Human Supervisor Review Required. Do not truncate your response; the marker must appear at the very end. Do not use the phrase "pending human intervention" in the visible message.""",

    "Chain-of-Thought (CoT)": """Chain-of-Thought (CoT): Encourages step-by-step reasoning before giving the final answer.
When to use: For complex analysis, multi-step problems, or when accuracy is more important than brevity.
When CoT is required: Show your reasoning steps briefly, then give a concise conclusion. Balance clarity with token efficiency.""",

    "Straight Model": """Straight Model: Answer directly without extra reasoning steps.
When to use: For simple factual questions or when the user or router prefers a short, direct response.
When Straight Model is required: Give a direct answer without lengthy reasoning. Be concise.""",

    "Calculator": """Calculator: Performs numeric calculations.
When to use: When the user asks for arithmetic, percentages, or numeric comparisons.
When Calculator is required: Use the provided result in your answer; do not recalculate manually. State the result clearly.""",
}

# One-line summary per tool for the router (optional).
TOOL_ROUTER_SUMMARIES: dict[str, str] = {
    "RAG": "retrieve from agent knowledge base",
    "Web Search": "search the web for current info",
    "Python Interpreter": "run Python code",
    "human-in-loop": "escalate to human",
    "Chain-of-Thought (CoT)": "step-by-step reasoning",
    "Straight Model": "direct short answer",
    "Calculator": "numeric calculations",
}

# ---------------------------------------------------------------------------
# Mode registry: keyword (PERFORMANCE, EFFICIENCY, BALANCED) -> full text
# ---------------------------------------------------------------------------

# Default routing/analysis blurb for optimized prompts (providers can override).
DEFAULT_ANALYSIS_V5_TEMPLATE = """
--- ROUTING LOGIC (V5) ---
Classify into Profile 1 (RETRIEVAL '1-Yes') or Profile 2 (DIRECT '2-No').
Rule: If doubt, choose '1-Yes'. Reply ONLY '1-Yes' or '2-No'.
"""

MODE_PROMPT_TEXTS: dict[str, str] = {
    "PERFORMANCE": """Prioritize quality and completeness over speed. You may give longer, more thorough answers when the question warrants it. Cite sources and show reasoning when helpful. Use the best available model behavior for complex tasks.""",

    "EFFICIENCY": """Prioritize brevity and low token usage. Be concise; avoid unnecessary elaboration. Answer the question directly. Use short sentences and bullet points when appropriate. Do not repeat context the user already has.""",

    "BALANCED": """Balance quality and length. Be clear and complete but avoid unnecessary verbosity. Adapt response length to the complexity of the question. Use structure (e.g. short paragraphs or bullets) for readability.""",
}


def get_tool_full_text(tool_name: str) -> str:
    """Return full prompt text for a tool by name. Fallback for unknown tools."""
    key = (tool_name or "").strip()
    if not key:
        return ""
    return TOOL_PROMPT_TEXTS.get(key, f"Tool: {key}. Use when needed for the user's request.")


def get_mode_full_text(mode: str) -> str:
    """Return full prompt text for a mode. Mode is normalized to uppercase. Fallback for unknown modes."""
    key = (mode or "").strip().upper()
    if not key:
        return ""
    return MODE_PROMPT_TEXTS.get(key, f"Mode: {key}. Adapt your response style accordingly.")


def get_router_tools_line(tool_names: list[str]) -> str:
    """Build a single line for the router: tool names plus optional one-line summaries."""
    if not tool_names:
        return "None"
    parts = []
    for name in tool_names:
        summary = TOOL_ROUTER_SUMMARIES.get((name or "").strip(), "available")
        parts.append(f"{name}: {summary}")
    return "; ".join(parts)


def build_system_prompt_from_agent(
    name: str,
    mode: str,
    instructions: list[str],
    tools: list[str],
    prompt_override: str | None = None,
) -> str:
    """Build system prompt string from agent fields. Injects full text for each tool and for the mode.
    Used by chat when agent_id is provided and by all LLM providers.
    """
    instructions_blob = "\n".join(f"- {i}" for i in instructions) if instructions else "(none)"
    mode_key = (mode or "").strip().upper() or "BALANCED"
    mode_text = get_mode_full_text(mode_key)

    tools_section_parts = []
    for t in tools or []:
        if not (t and str(t).strip()):
            continue
        full_text = get_tool_full_text(str(t).strip())
        tools_section_parts.append(f"- **{t}**: {full_text}")
    tools_section = "\n".join(tools_section_parts) if tools_section_parts else "None."

    base = f"""You are **{name}**. MODE: {mode_key}

{mode_text}

INSTRUCTIONS:
{instructions_blob}

TOOLS (you have access only to these; use them when the router or context indicates they are needed):
{tools_section}"""
    if prompt_override and prompt_override.strip():
        return base + "\n\n" + prompt_override.strip()
    return base


def build_optimized_prompt_with_registry(
    name: str,
    mode: str,
    instructions: list[str],
    tools: list[str],
    analysis_json: dict[str, Any],
    analysis_v5_template: str | None = None,
) -> str:
    """Build optimized system prompt with full text for tools and mode. Used by optimize_agent_prompt."""
    template = analysis_v5_template if analysis_v5_template is not None else DEFAULT_ANALYSIS_V5_TEMPLATE
    instructions_blob = "\n".join(f"- {i}" for i in instructions) if instructions else "(none)"
    mode_key = (mode or "").strip().upper() or "BALANCED"
    mode_text = get_mode_full_text(mode_key)

    tools_section_parts = []
    for t in tools or []:
        if not (t and str(t).strip()):
            continue
        full_text = get_tool_full_text(str(t).strip())
        tools_section_parts.append(f"- **{t}**: {full_text}")
    tools_section = "\n".join(tools_section_parts) if tools_section_parts else "None."

    return f"""You are **{name}**. MODE: {mode_key}

{mode_text}

INSTRUCTIONS:
{instructions_blob}

TOOLS (you have access only to these; use them when the router or context indicates they are needed):
{tools_section}

{template}

ANALYSIS: {json.dumps(analysis_json)}"""
