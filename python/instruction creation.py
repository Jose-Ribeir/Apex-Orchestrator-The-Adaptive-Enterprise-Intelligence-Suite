import google.generativeai as genai
import os

# --- CONFIGURATION ---
API_KEY = "AIzaSyDdazQHNvH33BRfB6b_rG898R5uAvukQ60"
genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-pro-latest"


def generate_optimized_prompt(reference_prompt, new_context_or_guidelines):
    """
    Takes a reference prompt (analysis_V5) and a new context.
    Generates a new prompt that follows the structural and reasoning logic of the reference.
    """

    meta_prompt = (
        "You are an expert Prompt Engineer and Logic Architect.\n\n"
        "I have a highly effective prompt (REFERENCE_PROMPT) that uses a specific structure to make binary decisions (Profile 1 vs Profile 2) with strict decision rules.\n"
        "I want you to create a NEW prompt for a different task, based on the NEW_CONTEXT provided below.\n\n"
        "--- REFERENCE_PROMPT (Do not change the logic structure of this, just observe it) ---\n"
        f"{reference_prompt}\n"
        "-----------------------------------------------------------------------------------\n\n"
        "--- NEW_CONTEXT (The topic/guidelines for the new prompt) ---\n"
        f"{new_context_or_guidelines}\n"
        "-----------------------------------------------------------------------------------\n\n"
        "**INSTRUCTIONS:**\n"
        "1. Analyze the REFERENCE_PROMPT. Notice how it defines two distinct profiles, gives specific examples for each, and establishes a 'Decision Rule' that prioritizes safety/accuracy.\n"
        "2. Create a NEW prompt that applies this exact structure to the NEW_CONTEXT.\n"
        "3. The new prompt must have:\n"
        "   - A clear role definition.\n"
        "   - '--- PROFILE 1: [Label] ---' section with bullet points.\n"
        "   - '--- PROFILE 2: [Label] ---' section with bullet points.\n"
        "   - A '**Decision Rule**' section that mimics the logic of the reference (e.g., 'If in doubt, choose X').\n"
        "   - The same '**IMPORTANT**' formatting instruction at the end.\n"
        "4. Output ONLY the new prompt text."
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(meta_prompt)
        return response.text
    except Exception as e:
        return f"Error generating prompt: {e}"


# --- THE REFERENCE PROMPT (Your V5) ---
analysis_V5_template = (
    "Query: {query}\n\n"
    "You are a query classification expert. Your task is to classify the user's query into one of two profiles to determine if document retrieval is necessary for an accurate answer. Choose the profile that is the BEST fit.\n\n"
    "--- PROFILE 1: RETRIEVAL REQUIRED ('1-Yes') ---\n"
    "Choose this profile if the query requires external, specific, or up-to-date knowledge. It MUST be chosen if the query involves:\n"
    "  - **Specific & Non-Famous Entities:** People, organizations, or titles that are not globally famous (e.g., 'Mabel Murphy Smythe-Haith', 'Axle Whitehead').\n"
    "  - **Precise Data:** Specific numbers, dates, statistics, or financial data that is not common knowledge (e.g., 'founding year of Alabama State University', 'box office numbers for a specific film').\n"
    "  - **Comparative Judgments or Opinions:** Questions asking for analysis, comparison, scope, or criticism that require evidence (e.g., 'Who has more scope of profession...', 'What are the main criticisms of X?').\n"
    "  - **Recent Events:** Any topic or event that has occurred very recently, as your internal knowledge may be outdated.\n\n"
    "--- PROFILE 2: DIRECT ANSWER SUFFICIENT ('2-No') ---\n"
    "Choose this profile ONLY if the query is self-contained and relies on stable, common knowledge or creative generation. It is SAFE to choose this profile if the query is clearly one of the following:\n"
    "  - **Common Knowledge:** Asks for a single, static, undisputed fact about a globally famous entity (e.g., 'What is the capital of France?', 'Who wrote Hamlet?', 'What is the chemical formula for water?').\n"
    "  - **General Concepts:** Asks for a broad definition or explanation of a well-established concept (e.g., 'Explain photosynthesis', 'What is a neural network?').\n"
    "  - **Creative & Logic Tasks:** Asks for creative writing (poems, stories), brainstorming, code generation, math problems, or logic puzzles.\n\n"
    "**Decision Rule:** Your primary goal is accuracy. First, check if the query is a perfect, unambiguous match for Profile 2. If there is *any* ambiguity, or if any part of the query touches on a Profile 1 characteristic (like a specific name or date), you MUST choose the safety of '1-Yes'. A slow but correct answer is always better than a fast but wrong one.\n\n"
    "**IMPORTANT** Your response MUST begin with '1-Yes' or '2-No', which will determine the method used. This is followed by the final answer within \\boxed{}.**IMPORTANT**\n"
)

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    print("--- Prompt Optimizer ---")

    # EXAMPLE: Let's say you want to create a prompt that decides if a customer support email
    # should be handled by a Human Agent (Profile 1) or an AI Bot (Profile 2).

    new_scenario = """
    Task: Classify customer support emails.
    Goal: Decide if an email needs a Human Agent ('1-Human') or can be handled by the AI ('2-AI').

    Criteria for Human (1-Human):
    - Angry or emotional customers.
    - Complex billing disputes involving refunds over $50.
    - Technical bugs that aren't in the FAQ.
    - VIP clients.

    Criteria for AI (2-AI):
    - Simple password resets.
    - "Where is my order?" status checks.
    - Basic pricing questions.
    - Feature requests.

    Logic: We want to be careful. If the customer seems even slightly annoyed, send to human.
    """

    print("\nGenerating new prompt based on your scenario...\n")

    new_prompt = generate_optimized_prompt(analysis_V5_template, new_scenario)

    print("--- GENERATED PROMPT ---\n")
    print(new_prompt)
    print("\n------------------------")