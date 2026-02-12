"""Registry of full-text descriptions for tools and modes. Used at prompt-build time to adapt
system and optimized prompts to the agent's tools and mode (keywords only in config/DB).
"""

import json
from typing import Any

# ---------------------------------------------------------------------------
# Tool registry: name (keyword) -> full text (what it does, when to use, how to act when required)
# ---------------------------------------------------------------------------

TOOL_PROMPT_TEXTS: dict[str, str] = {
    "RAG": """RAG (Retrieval-Augmented Generation): Retrieves relevant passages from the agent's knowledge base.
When to use: When the user asks about facts, documents, policies, or data that may be in the agent's indexed content. The router may set needs_rag=true.
When RAG is required: Use the [CONTEXT] section as your PRIMARY source of truth.
- CITATIONS: You must cite the document name or section when using retrieved information.
- NEGATIVE CONSTRAINT: If the [CONTEXT] is empty or does not contain the answer, you MUST state: "I could not find this information in the provided documents." Do not fabricate an answer from training data unless explicitly asked to "guess" or "use general knowledge.".""",

    "Web Search": """Web Search: Allows querying the live web for current information, documentation, or external references.
When to use: When the user needs up-to-date information, external URLs, or content not in the agent's knowledge base. The router may include this in tools_needed.
When Web Search is required: Rely on the search results or context provided. Prefer citing sources. If no results are given, state that and suggest the user rephrase or try later.""",

    "Python Interpreter": """Python Interpreter: Runs Python code for calculation, data processing, or file parsing.
When to use: When the user needs computation, data analysis, CSV/JSON parsing, or scripted logic. The router may include this in tools_needed.
When Python is required:
1. Write and execute the code to solve the problem.
2. In your final response, summarize the methodology used.
3. PRESENTATION: If the result is tabular, render it as a Markdown table. If the result is a single number, state it clearly.
4. SAFETY: Do not execute code that accesses the internet or local file system outside of the sandbox.""",

    "Human Escalation": """Human Escalation: Escalates the conversation to a human agent.
When to use: For angry users, refund requests, or when the AI cannot solve the problem after 2 attempts.
INSTRUCTIONS:
1. First, write a polite, empathetic response acknowledging the issue and stating that a specialist will take over.
2. Immediately after the response, on a new line, output exactly: [[ESCALATE_TO_HUMAN]]
3. Do not add any text after this token.""",

    "Step-by-Step Reasoning": """Step-by-Step Reasoning: Encourages step-by-step reasoning before giving the final answer.
When to use: For complex analysis, multi-step problems, or when accuracy is more important than brevity.
When Step-by-Step Reasoning is required: Show your reasoning steps briefly, then give a concise conclusion. Balance clarity with token efficiency.""",

    "Direct Answer": """Direct Answer: Answer directly without extra reasoning steps.
When to use: For simple factual questions or when the user or router prefers a short, direct response.
When Direct Answer is required: Give a direct answer without lengthy reasoning. Be concise.""",

    "Calculator": """Calculator: Performs numeric calculations.
When to use: When the user asks for arithmetic, percentages, or numeric comparisons.
When Calculator is required: Use the provided result in your answer; do not recalculate manually. State the result clearly.""",
}

# One-line summary per tool for the router (optional).
TOOL_ROUTER_SUMMARIES: dict[str, str] = {
    "RAG": "retrieve from agent knowledge base",
    "Web Search": "search the web for current info",
    "Python Interpreter": "run Python code",
    "Human Escalation": "escalate to human",
    "Step-by-Step Reasoning": "step-by-step reasoning",
    "Direct Answer": "direct short answer",
    "Calculator": "numeric calculations",
}

# ---------------------------------------------------------------------------
# Mode registry: keyword (PERFORMANCE, EFFICIENCY, BALANCED) -> full text
# ---------------------------------------------------------------------------

MODE_PROMPT_TEXTS: dict[str, str] = {
    "PERFORMANCE": """Prioritize quality and completeness over speed. You may give longer, more thorough answers when the question warrants it. Cite sources and show reasoning when helpful. Use the best available model behavior for complex tasks.""",

    "EFFICIENCY": """Prioritize extreme brevity and low token usage.
- No filler words (e.g., "Here is the information you requested", "I hope this helps").
- Use sentence fragments or bullet points where possible.
- Direct Answer only.
- If the user asks "What is X?", answer "X is..." immediately.""",

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


# Tool name that triggers human escalation (excluded from router tools list)
HUMAN_ESCALATION_TOOL = "Human Escalation"


def get_router_tools_line(tool_names: list[str]) -> str:
    """Build a single line for the router: tool names plus optional one-line summaries.
    Excludes Human Escalation: human-needed is decided by the generator's final output, not the router."""
    if not tool_names:
        return "None"
    filtered = [n for n in tool_names if (n or "").strip() != HUMAN_ESCALATION_TOOL]
    if not filtered:
        return "None"
    parts = []
    for name in filtered:
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
) -> str:
    """Build optimized system prompt with full text for tools and mode. Used by optimize_agent_prompt.
    Routing is handled by the JSON Router (Section 6); no legacy Profile 1/2 logic."""
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

ANALYSIS: {json.dumps(analysis_json)}"""
