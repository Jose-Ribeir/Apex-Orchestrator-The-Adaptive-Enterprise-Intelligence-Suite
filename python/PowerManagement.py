import json
import os
import sys
import shutil
import re
import unicodedata
from datetime import datetime
from dateutil.parser import parse
import google.generativeai as genai
from PowerManagement import PowerManagement

# --- CONFIGURATION ---
API_KEY = "AIzaSyDdazQHNvH33BRfB6b_rG898R5uAvukQ60"
genai.configure(api_key=API_KEY)

# Using Gemini 1.5 Pro for its large context window (up to 1M-2M tokens)
# This allows us to dump many retrieved documents directly into the prompt.
GEMINI_MODEL_NAME = "gemini-1.5-pro-latest"

# --- FLASHRAG SETUP (LOCAL) ---
# Ensure this path points to your FlashRAG installation
sys.path.append(r'J:\codigo\FlashRAG-main')

from flashrag.config import Config
from flashrag.utils import get_retriever

# Define corpus and index paths
corpus_file = "datasets/HotPotQa_docs_flashrag.jsonl"
index_path = "flashrag_index/bge_Flat.index"

# Initialize Retriever
# We increase retrieval_topk (e.g., to 20 or 50) because we are skipping the
# reranker/refiner and relying on Gemini's long context to sift through the data.
config_dict = {
    "retrieval_method": "bge",
    "retrieval_topk": 20,
    "corpus_path": corpus_file,
    "index_path": index_path,
    "instruction": "Represent this sentence for searching relevant passages:",
    "device": "cuda"
}
config = Config(config_dict=config_dict)
retriever = get_retriever(config)

# Initialize PowerManagement
pm = PowerManagement()


def delete_contents(folder_path):
    if not os.path.exists(folder_path):
        return
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def get_retrieved_docs(query, top_k=20):
    """
    Retrieves documents using the local FlashRAG retriever.
    """
    # Update topk dynamically if needed
    retriever.topk = top_k
    # FlashRAG BGE instruction format
    retriever.instruction = "Passage: "
    results = retriever.search(query)
    # Each result is a dict with 'contents' (text) and 'score'
    return [doc['contents'] for doc in results]


def generate_with_gemini(prompt, temperature=0.7):
    """
    Sends the prompt to Google Gemini API.
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return ""


def pick_the_path(analysis, query, temp_path=0.7, temp_gen=0.7):
    try:
        cost = 0

        # 1. ANALYSIS PHASE (Using Gemini)
        # We ask Gemini to decide if retrieval is needed.
        analysis_prompt = (
            f"Query: {query}\n"
            "Determine if this query requires retrieving external documents.\n"
            "Output '1-Yes' or '2-No' followed by your reasoning.\n"
            "Wrap the final decision number in \\boxed{}."
        )

        analysis_response = generate_with_gemini(analysis_prompt, temperature=temp_path)
        cost += 1

        # Parse decision
        method_used = "cot"  # Default to Chain of Thought (No Retrieval)
        if "1-Yes" in analysis_response or "\\boxed{1}" in analysis_response:
            method_used = "retrieval"

        retrieved_docs = []
        final_response = ""

        # 2. EXECUTION PHASE
        if method_used == "retrieval":
            # A. Local Retrieval
            # We fetch a larger number of docs (20) since we aren't filtering them further.
            retrieved_docs = get_retrieved_docs(query, top_k=20)

            # B. Long Context Generation
            # We dump all retrieved text into the prompt.
            context_str = "\n\n".join(retrieved_docs)

            final_prompt = (
                f"Query: {query}\n\n"
                "Below are several retrieved documents that may contain relevant information. "
                "Read through them and answer the query. If the documents do not contain the answer, "
                "you may use your internal knowledge but please mention that the documents were insufficient.\n\n"
                f"--- RETRIEVED DOCUMENTS ---\n{context_str}\n"
                "---------------------------\n\n"
                "Answer:"
            )

            final_response = generate_with_gemini(final_prompt, temperature=temp_gen)

        else:
            # Direct Generation (No Context)
            final_response = generate_with_gemini(query, temperature=temp_gen)

        cost += 1

        return {
            "response": final_response,
            "retrieved_docs": retrieved_docs,
            "method_used": method_used,
            "cost": cost,
            "analysis": analysis_response,
            "cleaned_analysis": analysis_response
        }

    except Exception as e:
        print(f"Error in pick_the_path: {e}")
        return {
            "response": f"Error: {e}",
            "retrieved_docs": [],
            "method_used": "error",
            "cost": 0,
            "analysis": "",
            "cleaned_analysis": ""
        }


# --- DATA LOADING UTILS ---

def load_queries(file_path, dataset_name):
    queries = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    q_content = ""
                    if dataset_name == "dragonball":
                        q_content = data.get("query", {}).get("content", "")
                    elif dataset_name == "arc":
                        q_content = data.get("question", "")

                    if q_content:
                        queries.append({
                            "query": {"query_id": i, "content": q_content},
                            "ground_truth": {}
                        })
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error loading queries: {e}")
    return queries


def process_Dataset(analysis, dataset_name, corpus_file, queries_file):
    queries = load_queries(queries_file, dataset_name)
    results = []

    checkpoint_file = "./DragonBall_results/checkpoint.json"
    os.makedirs("./DragonBall_results", exist_ok=True)

    for i, query_obj in enumerate(queries):
        print(f"Processing Query {i}: {query_obj['query']['content'][:50]}...")
        pm.start_measurement()

        res = pick_the_path(
            analysis,
            query_obj["query"]["content"]
        )

        stats = pm.stop_measurement()

        result_entry = {
            "query_id": query_obj["query"]["query_id"],
            "content": query_obj["query"]["content"],
            "response": res["response"],
            "retrieved_docs": res["retrieved_docs"],
            "method": res["method_used"],
            "stats": stats
        }
        results.append(result_entry)

        # Save intermediate
        if i % 5 == 0:
            with open(f"./DragonBall_results/results_{i}.jsonl", "w") as f:
                json.dump(result_entry, f)

    # Final Save
    os.makedirs("./Results", exist_ok=True)
    with open(f"./Results/final_results_V{analysis}.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    # Ensure these paths match your local setup
    corpus_file = "datasets/HotPotQa_docs_flashrag.jsonl"
    queries_file = "datasets/finale_queries_arc_fixed.jsonl"

    # Run processing
    process_Dataset(6, "dragonball", corpus_file, queries_file)