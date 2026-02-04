import json
from datetime import time
from gc import garbage
from datetime import datetime
import pandas as pd
from prompt_toolkit.application.application import attach_winch_signal_handler
# from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel # Removed
import torch
import os
import unicodedata
from nltk import sent_tokenize
import nltk
import time as time_module  # Renamed to avoid conflict with datetime.time

CRED = '\033[91m'
CGREEN = '\033[92m'
CEND = '\033[0m'
import gc

nltk.download('punkt_tab')
# from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline # Removed
import faiss
from dateutil.parser import parse
import sys
import re
import shutil
from PowerManagement import PowerManagement
import google.generativeai as genai

# Configure Google Gemini API
API_KEY = "AIzaSyDdazQHNvH33BRfB6b_rG898R5uAvukQ60"
genai.configure(api_key=API_KEY)

# Initialize the model
# Using gemini-2.0-flash-thinking-exp as a strong reasoning model alternative to DeepSeek-R1
# You can change this to "gemini-1.5-pro" or "gemini-1.5-flash" if preferred.
GEMINI_MODEL_NAME = "gemini-2.0-flash-thinking-exp-01-21"
gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

pm = PowerManagement()
corpus_file = "datasets/HotPotQa_docs_flashrag.jsonl"
sys.path.append(r'J:\codigo\FlashRAG-main')

from flashrag.config import Config
from flashrag.utils import get_retriever

config_dict = {"retrieval_method": "bge",
               "retrieval_topk": 5,
               "corpus_path": corpus_file,
               "index_path": "./flashrag_index/bge_Flat.index",
               "instruction": "Represent this sentence for searching relevant passages:"}
config = Config(config_dict=config_dict)

retriever = get_retriever(config)

from flashrag.refiner import ExtractiveRefiner

config_dict = {
    "refiner_name": "extractive",
    "refiner_model_path": "BAAI/bge-base-en-v1.5",
    "device": "cuda",
    "refiner_topk": 5,
    "refiner_pooling_method": "mean",
    "refiner_encode_max_length": 512,
    "refiner_mini_batch_size": 256,
    "instruction": "Represent this sentence for searching relevant passages: "  # <-- Add this line
}
config = Config(config_dict=config_dict)

refiner = ExtractiveRefiner(config)

from flashrag.retriever.reranker import CrossReranker

config_dict = {
    "rerank_model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_model_path": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_topk": 5,
    "rerank_max_length": 256,
    "rerank_batch_size": 8,
    "device": "cuda"  # or "cpu"
}
config = Config(config_dict=config_dict)
reranker = CrossReranker(config)


def get_retrieved_docs(query, top_k=5):
    # FlashRAG expects queries to be prefixed with "passage: "
    retriever.topk = 5  # or whatever number you want
    retriever.instruction = "Passage: "
    results = retriever.search(query)
    # Each result is a dict with 'text' and 'score'
    return [doc['contents'] for doc in results]


def delete_contents(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove file or link
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Remove directory and all its contents
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


# --- TOKEN MONITORING UTILS ---
def estimate_tokens(text_chunk):
    # Simple estimation: 1 token approx 4 chars
    return len(text_chunk) / 4


# Helper function to call Gemini with Streaming and Monitoring
def generate_with_gemini(prompt, temperature=0.7, max_output_tokens=1000):
    try:
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        # Enable streaming
        response_stream = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=True
        )

        full_text = ""
        total_estimated_tokens = 0
        start_time = time_module.time()

        # print(f"{CGREEN}--- Generating Response ---{CEND}")

        for chunk in response_stream:
            try:
                new_text = chunk.text
                full_text += new_text

                # Calculate stats
                chunk_tokens = estimate_tokens(new_text)
                total_estimated_tokens += chunk_tokens
                elapsed = time_module.time() - start_time
                speed = total_estimated_tokens / elapsed if elapsed > 0 else 0

                # Print live stats (overwrite line)
                # Using sys.stdout.write to avoid newline spam, or just print normally if you prefer
                # sys.stdout.write(f"\r{CGREEN}[Est. Tokens: {int(total_estimated_tokens)} | Speed: {speed:.1f} t/s]{CEND}")
                # sys.stdout.flush()

            except ValueError:
                # Sometimes chunks are empty or blocked
                pass

        # print(f"\n{CGREEN}--- Generation Complete ---{CEND}")
        return full_text

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return ""


def list_to_string(obj):
    if isinstance(obj, list):
        # If it's a list of lists, flatten it
        if all(isinstance(i, list) for i in obj):
            flat = [item for sublist in obj for item in sublist]
            return " ".join(flat)
        else:
            return " ".join(obj)
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)


def pick_the_path(analysis, query, corpus=None, max_output_first_gen=1000, max_output_second_gen=1000, temp_path=0.7,
                  temp_gen=0.7):
    try:
        # Initialize default values
        method_used = 2
        cost = 0
        final_prompt = ""

        analysis_V1 = (
            f"Query: {query}\n\n"
            "THE ANSWER SHOULD COME WITHIN \\boxed{}, IGNORE THE NEXT INSTRUCTIONS IF YOU CAN ANSWER CORRECTLY.\n"
            "Would this Query benefic from the retrieval of documents?\n"
            "1-Yes\n"
            "2-No\n"
            "**IMPORTANT** The final answer has to come within \\boxed{}.**IMPORTANT**\n\n"
        )

        analysis_V2 = (
            f"Query: {query}\n\n"
            "You are an expert query analyzer. Your primary goal is to eliminate incorrect answers by forcing document retrieval for any non-trivial query. Your default assumption MUST be that retrieval is necessary ('1-Yes').\n\n"
            "You are only permitted to output '2-No' if, and only if, the query meets ALL of the following strict criteria:\n"
            "1. The query involves ONLY globally famous entities (e.g., 'France', 'Shakespeare', 'Google').\n"
            "2. The query asks for a SINGLE, static, and universally known fact (e.g., a capital city, a famous author's most known work).\n\n"
            "For ALL OTHER QUERIES, you MUST output '1-Yes'. This is not optional. Specifically, if the query has any of the following attributes, you MUST output '1-Yes':\n"
            "- Contains specific names of people, places, or things that are not globally famous (e.g., 'Mabel Murphy Smythe-Haith', 'Axle Whitehead').\n"
            "- Asks for a specific number, date, or statistic that is not common knowledge (e.g., the founding year of a specific school).\n"
            "- Requires a comparison or judgment about scope, profession, or other nuanced topics (e.g., comparing two authors).\n\n"
            "Analyze the query against these rules and provide your decision.\n\n"
            "**IMPORTANT** Your response MUST begin with '1-Yes' or '2-No', which will determine the method used. This is followed by the final answer within \\boxed{}.**IMPORTANT**\n"
        )

        analysis_V3 = (
            f"Query: {query}\n\n"
            "Your goal is to balance accuracy with efficiency. You must decide if a query requires document retrieval ('1-Yes') or not ('2-No'). Follow this two-step process:\n\n"
            "**Step 1: First, check if the query is a simple case that does NOT need retrieval.**\n"
            "You can select '2-No' if the query clearly fits one of these categories:\n"
            "  - **Universally Known Facts:** Asks for a single, static fact about a globally famous subject (e.g., 'What is the capital of France?', 'Who is the CEO of Google?').\n"
            "  - **Creative Tasks:** Asks for creative writing, code generation, or brainstorming (e.g., 'Write a poem about the moon', 'Give me ideas for a party theme').\n"
            "  - **General Explanations:** Asks for a general explanation of a broad, well-known concept (e.g., 'Explain how photosynthesis works', 'What is a neural network?').\n\n"
            "**Step 2: If the query is NOT a simple case from Step 1, check for complexity.**\n"
            "You MUST select '1-Yes' if the query has any of the following attributes:\n"
            "  - **Specific, Non-Famous Entities:** Contains names of people, places, or titles that are not globally famous (e.g., 'Mabel Murphy Smythe-Haith', 'Axle Whitehead').\n"
            "  - **Precise, Non-Trivial Data:** Asks for specific numbers, dates, or statistics that are not common knowledge (e.g., 'founding year of a specific school', 'box office numbers for a movie').\n"
            "  - **Comparisons or Analysis:** Requires a nuanced comparison or analysis that would be strengthened by evidence (e.g., 'Who has more scope of profession...', 'What are the main criticisms of...').\n\n"
            "**Decision Heuristic:** If the query does not clearly fit into a 'simple case' from Step 1, your default action should be to retrieve ('1-Yes') to ensure accuracy.\n\n"
            "**IMPORTANT** Your response MUST begin with '1-Yes' or '2-No', which will determine the method used. This is followed by the final answer within \\boxed{}.**IMPORTANT**\n"
        )

        analysis_V4 = (
            f"Query: {query}\n\n"
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
            "**Decision Rule:** Compare the query against both profiles. If it clearly fits Profile 2, select '2-No'. In all other cases, especially if there is any doubt or overlap, you MUST default to the safety of '1-Yes'.\n\n"
            "**IMPORTANT** Your response MUST begin with '1-Yes' or '2-No', which will determine the method used. This is followed by the final answer within \\boxed{}.**IMPORTANT**\n"
        )

        analysis_V5 = (
            f"Query: {query}\n\n"
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

        analysis_V6 = (
            f"Query: {query}\n\n"
            "You are a query classification expert. Your goal is to accurately determine if document retrieval is necessary, with a specific focus on AVOIDING unnecessary retrieval for general knowledge questions.\n\n"
            "--- PROFILE 1: RETRIEVAL REQUIRED ('1-Yes') ---\n"
            "Choose this profile ONLY if the query contains a clear 'retrieval trigger'. A trigger is present if the query involves:\n"
            "  - **Low-Fame Entities:** Specific people, organizations, or products that are not globally famous (e.g., 'Mabel Murphy Smythe-Haith', 'Axle Whitehead'). If you don't have deep, confident knowledge of the entity, retrieve.\n"
            "  - **Hard Data:** Requests for precise numbers, dates, or stats that are not common trivia (e.g., 'box office numbers for a specific film', 'founding year of Alabama State University', 'population of a small city').\n"
            "  - **Recent Information:** Any event, product release, or news from the last two years.\n"
            "  - **Document-Based Analysis:** Questions asking for comparisons, scope, or criticisms that imply needing information from a specific text.\n\n"
            "--- PROFILE 2: DIRECT ANSWER SUFFICIENT ('2-No') ---\n"
            "This is the default profile for most queries. Choose this if the query relies on stable, common, or encyclopedic knowledge. It is the correct choice for:\n"
            "  - **Common Knowledge:** Questions about globally famous entities, major historical events, and well-established scientific facts (e.g., 'What is the capital of France?', 'Who wrote Hamlet?', 'What is H2O?'). This includes famous dates or numbers (e.g., 'When did WWII end?', 'What is the value of Pi?').\n"
            "  - **General Concepts:** Broad definitions or explanations (e.g., 'Explain photosynthesis', 'What is a neural network?').\n"
            "  - **Creative & Logic Tasks:** Requests for code, poems, math problems, or brainstorming.\n\n"
            "**Decision Rule:** Your primary goal is to reduce incorrect '1-Yes' classifications. Start with the assumption that the query is '2-No'. Scrutinize the query for a clear and definite 'retrieval trigger' from Profile 1. If no such trigger is present, you MUST select '2-No'. Do not default to '1-Yes' out of mere caution; an explicit reason is required.\n\n"
            "**IMPORTANT** Your response MUST begin with '1-Yes' or '2-No'.**IMPORTANT**\n"
        )
        print(analysis_V6)
        # Map analysis version to corresponding prompt
        analysis_prompts = {
            1: analysis_V1,
            2: analysis_V2,
            3: analysis_V3,
            4: analysis_V4,
            5: analysis_V5,
            6: analysis_V6
        }

        # Validate and select analysis prompt
        if not isinstance(analysis, int) or analysis < 1 or analysis > 6:
            raise ValueError("Analysis version must be an integer between 1 and 6")

        analysis_prompt = analysis_prompts[analysis]

        # Generate with Gemini
        analysis = generate_with_gemini(analysis_prompt, temperature=temp_path, max_output_tokens=max_output_first_gen)

        cost += 1
        analysis = unicodedata.normalize('NFKC', analysis)
        # print("Analysis:", analysis)
        analysis_unchanged = analysis
        analysis = analysis.split('</think>', 1)[-1]
        if "\\boxed{" in analysis_unchanged:
            match = re.search(r"\\boxed\{(.*?)\}", analysis_unchanged)
            if match:
                extracted_char = match.group(1)
                # Only proceed if it's a single alphabetic character
                if len(extracted_char) == 1 and extracted_char.isalpha():
                    return {
                        "response": extracted_char,
                        "retrieved_docs": "",
                        "refined_context": "",
                        "reranked_docs": "",
                        "method_used": "nothing",
                        "cost": cost,
                        "analysis": analysis_unchanged,
                        "cleaned_analysis": analysis,
                    }

        # Extract all method numbers from the analysis
        method_counts = {2: 0, 1: 0}
        i = 0
        while i < len(analysis):
            # Check for \boxed{n} pattern
            for n in method_counts:
                boxed_pattern = f"\\boxed{{{n}}}"
                if analysis.startswith(boxed_pattern, i):
                    method_counts[n] += 100
                    i += len(boxed_pattern) - 1  # Skip past the boxed pattern
                    break
            i += 1

        if "yes" in analysis.lower():
            method_counts[1] += 100

        print("Method counts:", method_counts)
        # Find the method with the highest count
        suggested_method = max(method_counts, key=method_counts.get)
        # if method_counts[suggested_method] <= 99:
        #     suggested_method = 1  # or any other value to indicate "no valid method"
        print("Suggested method" + str(suggested_method))

        # Generate appropriate prompt based on selected method
        if suggested_method == 1 and corpus:
            try:
                retrieved_results = retrievalOptions(query=query, option="retrieval", k=5)
                reranked_docs, rerank_scores = retrievalOptions(query=query, option="rerank",
                                                                context_list=retrieved_results)
                refined_context = retrievalOptions(query=query, option="refine", ret_docs=reranked_docs)

                retrieved_results = list_to_string(retrieved_results)
                reranked_docs = list_to_string(reranked_docs)
                refined_context = list_to_string(refined_context)

                final_prompt = (
                        f"Question: {query}\n"
                        "Relevant documents:\n" + "\n" + retrieved_results + "\n"
                                                                             "Break down the question into key concepts, "
                                                                             "Analyze their relationships, and provide a detailed answer:\n"
                                                                             "**Important:** Your response must begin with `<think>\\n` and end with `</think>`.\n"

                )

                method_used = "retrieval"
            # Fallback if retrieval fails
            except Exception as e:
                print(f"Document retrieval failed: {e}")

        elif suggested_method == 2:
            final_prompt = (
                f"Question: {query}\n"
                "Break down the question into key concepts, "
                "Analyze their relationships, and provide a detailed answer:\n"
                "**Important:** Your response must begin with `<think>\\n` and end with `</think>`, The final answer should come within \\boxed{}\n\n"

            )

            method_used = "cot"

        # Generate final response with Gemini
        response = generate_with_gemini(final_prompt, temperature=temp_gen, max_output_tokens=max_output_second_gen)

        cost += 1
        return {
            "response": response,
            "retrieved_docs": retrieved_results if suggested_method == 1 else [],
            "refined_context": refined_context if suggested_method == 1 else "",
            "reranked_docs": reranked_docs if suggested_method == 1 else [],
            "method_used": method_used,
            "cost": cost,
            "analysis": analysis_unchanged,
            "cleaned_analysis": analysis,

        }

    except Exception as e:
        print(f"Error in pick_the_path: {e}")
        return {
            "response": f"Error: {str(e)}",
            "method_used": 0,
            "cost": 0,
            "analysis": "",
            "method_counts": {}
        }


def custom_sentence_split(text):
    # Split at a period, followed by a space, followed by a capital letter
    sentences = re.split(r'(?<=[.])\s+(?=[A-Z])', text)
    # Remove any leading/trailing whitespace from each sentence
    return [s.strip() for s in sentences if s.strip()]


# Step 4: Load the Dragon Ball documents from the JSONL file and filter for English documents
def load_corpus(file_path):
    """Load corpus, splitting at periods only when followed by a space and an uppercase letter."""
    corpus = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)
                if doc.get("language") == "en" and "content" in doc:
                    # Clean document text
                    clean_doc = re.sub(r'\s+', ' ', doc["content"]).strip()

                    # Split on period only if followed by a space and uppercase letter
                    phrases = re.split(r'(?<=\.) (?=[A-Z])', clean_doc)

                    for phrase in phrases:
                        phrase = phrase.strip()
                        if phrase:
                            doc_date = parse(doc.get("date", "1970-01-01"))  # Fallback to epoch if missing
                            corpus.append({
                                "text": phrase,
                                "source": doc.get("doc_id", "unknown"),
                                "date": doc_date,  # Store as datetime object
                            })
    except Exception as e:
        print(f"Error loading corpus: {e}")
    return corpus


def load_arc_queries(file_path):
    queries = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue  # Skip blank lines
                try:
                    query_data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Skipping line {i + 1}: {e}")
                    continue

                # Format question with choices if present
                question = query_data.get("question", "")
                choices = query_data.get("choices", {})
                if choices and "text" in choices and "label" in choices:
                    # Combine question and labeled choices
                    labeled_choices = [
                        f"{label}. {text}"
                        for label, text in zip(choices["label"], choices["text"])
                    ]
                    question_with_choices = question + "\n" + "\n".join(labeled_choices)
                else:
                    raise ValueError("No choices provided for the question.")

                # Build the query object in the desired structure
                query_obj = {
                    "domain": query_data.get("domain", ""),
                    "language": query_data.get("language", ""),
                    "query": {
                        "query_id": query_data.get("query_id", i + 1),
                        "query_type": query_data.get("query_type", ""),
                        "content": question_with_choices
                    },
                    "ground_truth": {
                        "doc_ids": query_data.get("ground_truth", {}).get("doc_ids", []),
                        "content": query_data.get("ground_truth", {}).get("content", query_data.get("answer", "")),
                        "references": query_data.get("ground_truth", {}).get("references", []),
                        "keypoints": query_data.get("ground_truth", {}).get("keypoints", [])
                    },
                    "prediction": {
                        "content": "",
                        "references": []
                    }
                }
                queries.append(query_obj)
    except Exception as e:
        print(f"Error loading queries: {e}")
    return queries


# Step 5: Load the queries from the JSONL file
def load_queries(file_path, dataSet):
    queries = []
    if dataSet == "dragonball":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    query_data = json.loads(line)
                    if query_data.get("language") == "en" and "query" in query_data and "content" in query_data[
                        "query"]:
                        queries.append(query_data)
        except Exception as e:
            print(f"Error loading queries: {e}")
        return queries
    elif dataSet == "arc":
        try:
            queries = load_arc_queries(file_path)
        except Exception as e:
            print(f"Error loading queries: {e}")
        return queries
    return "Error: The file path does not contain 'dragonball'."


# Step 6: Define a function for HyDE retrieval


# Step 7: Generate a response based on the query and retrieved documents
def generate_response(query, retrieved_docs, max_output_length=512):
    """
    Generate a response based on the query and the retrieved documents.
    """
    try:
        # Combine the query and retrieved documents into a single input with an answer prompt
        context = (
                f"Query: {query}\nRetrieved Documents:\n"
                + "\n".join(retrieved_docs)
                + "\nAnswer:"
        )

        # Generate output with Gemini
        response = generate_with_gemini(context, temperature=0.6, max_output_tokens=max_output_length)

        return response
    except Exception as e:
        print(f"Error generating response: {e}")
        return ""


# 1. Embed your documents
def embed_documents(docs, embedder):
    return embedder.encode(docs, convert_to_numpy=True)


# 2. Build a FAISS index
def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def retrievalOptions(query=None, option="", ret_docs=None, k=None, context_list=None):
    if option == "retrieval":
        if query == "":
            raise ValueError("Query cannot be empty for retrieval.")
        if k <= 0:
            raise ValueError("Top k must be greater than 0.")
        retrieved_docs = get_retrieved_docs(query, k)
        retrieved_docs = list(retrieved_docs)
        return retrieved_docs

    elif option == "rerank":
        if not context_list:
            raise ValueError("Context list cannot be empty for reranking.")
        if not isinstance(context_list, list):
            raise ValueError("Context list must be a list of documents.")
        if not query:
            raise ValueError("Query cannot be empty for reranking.")

        reranked_docs, rerank_scores = reranker.rerank([query], [context_list])
        if not isinstance(reranked_docs, list):
            reranked_docs = list(reranked_docs)
        if not isinstance(rerank_scores, list):
            rerank_scores = list(rerank_scores)
        return reranked_docs, rerank_scores


    elif option == "refine":

        if not ret_docs: raise ValueError("Retrieved documents cannot be empty for refinement.")
        if not isinstance(ret_docs, list): raise TypeError("ret_docs must be a list of documents.")
        if not query: raise ValueError("Query cannot be empty for refinement.")
        if not isinstance(query, str): raise TypeError("query must be a string.")
        item = type('Item', (object,), {})()
        item.question = query

        if ret_docs and isinstance(ret_docs[0], list):
            retrieved_docs = [item for sublist in ret_docs for item in sublist]
        else:
            retrieved_docs = ret_docs

        # Check for any non-string items and convert them to string if needed
        retrieved_docs = [doc if isinstance(doc, str) else str(doc) for doc in retrieved_docs]
        item.retrieval_result = [{"contents": "DUMMY_HEADER\n" + doc} for doc in retrieved_docs]
        df = pd.DataFrame([{"question": item.question, "retrieval_result": item.retrieval_result}])
        refined_contexts = refiner.batch_run(df)
        refined_context = refined_contexts[0] if refined_contexts else ""

        return refined_context
    raise ValueError("Select a option: retrieval, rerank or refine")


def load_and_process_corpus(corpus_file):
    """Load and process corpus documents."""
    corpus = load_corpus(corpus_file)
    phrases = []
    phrase_meta = []
    docs = []

    with open(corpus_file, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            if doc.get("language") == "en":
                docs.append(doc)

    doc_texts = [doc["content"] for doc in docs]

    for doc in docs:
        sentences = sent_tokenize(doc["content"])
        for sent in sentences:
            phrases.append(sent)
            phrase_meta.append(doc)

    return corpus, phrases, phrase_meta, docs, doc_texts


def initialize_results(checkpoint_file):
    """Initialize results list and start index from checkpoint if exists."""
    results = []
    start_index = 0

    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)
            start_index = checkpoint_data.get("last_processed_index", 0)
            print(f"Resuming from index {start_index}")

    return results, start_index


def process_query(analysis, query_obj, i, corpus, pm, temp_path, temp_gen):
    """Process a single query and return result dictionary."""
    # print(query_obj)
    domain = query_obj.get("domain", [])
    language = query_obj.get("language", [])
    query_content = query_obj["query"]["content"]
    query_id = query_obj["query"].get("query_id", i + 1)
    query_type = query_obj["query"].get("query_type", [])
    ground_truth_doc_ids = query_obj.get("ground_truth", {}).get("doc_ids", [])
    ground_truth_content = query_obj.get("ground_truth", {}).get("content", [])
    ground_truth_references = query_obj.get("ground_truth", {}).get("references", [])
    ground_truth_keypoints = query_obj.get("ground_truth", {}).get("keypoints", [])
    starttime = datetime.now()
    pm.start_measurement()
    # set max_output_first_gen to atleast 1000 forability to think
    response = pick_the_path(analysis, query_content, corpus=corpus, max_output_first_gen=1000,
                             max_output_second_gen=1000, temp_path=temp_path, temp_gen=temp_gen)
    stats = pm.stop_measurement()
    endtime = datetime.now()
    print(response)
    return {
        "domain": domain,
        "language": language,
        "query": {
            "query_id": query_id,
            "query_type": query_type,
            "content": query_content
        },
        "ground_truth": {
            "doc_ids": ground_truth_doc_ids,
            "content": ground_truth_content,
            "references": ground_truth_references,
            "keypoints": ground_truth_keypoints
        },
        "prediction": {
            "path_response": response["analysis"],
            "content": response["response"],
            "references": response["retrieved_docs"],
            "refined_context": response["refined_context"],
            "retrieved_docs_rerank": response["reranked_docs"],
            "method_used": response["method_used"],
            "hops": response["cost"],
            "analysis": response["analysis"],
            "cleaned_analysis": response["cleaned_analysis"],

        },
        "performance_metadata": {
            "start_time": str(starttime),
            "end_time": str(endtime),
            "time_taken_sec": stats['duration_seconds'],
            "energy_consumed_wh": stats['power_wh'],
        }
    }


def save_intermediate_results(results, i, checkpoint_file):
    """Save intermediate results and update checkpoint."""
    output_file = f"./DragonBall_results/hyde_retrieval_results_part_{i // 5 + 1}.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for res in results[-5:]:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
    print(f"Saved intermediate results to {output_file}")

    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump({"last_processed_index": i + 1}, f)
    print(f"Checkpoint updated at index {i + 1}")


def save_final_results(analysis, results, checkpoint_file, dataset_name, path_temp, gen_temp):
    input_folder = os.path.dirname(checkpoint_file)

    # If checkpoint_file is just a filename with no path, dirname returns an empty string.
    # In that case, we default to the current directory ('.').
    if not input_folder:
        input_folder = "."

    print(f"Source folder derived from checkpoint file: '{input_folder}'")

    combined_results = []

    # Check if the derived folder exists.
    if not os.path.isdir(input_folder):
        print(f"Error: The derived folder '{input_folder}' does not exist. Aborting.")
        return

    print(f"Reading all .jsonl files from '{input_folder}'...")
    # Loop through all files in the derived input folder.
    for filename in os.listdir(input_folder):
        if filename.endswith(".jsonl"):
            file_path = os.path.join(input_folder, filename)
            print(f"  - Processing {filename}")
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            combined_results.append(json.loads(line))
                        except json.JSONDecodeError:
                            print(f"    - Warning: Skipping malformed JSON line in {filename}")

    combined_results.sort(key=lambda x: x.get('query', {}).get('query_id'))
    # Define the output directory and create it if it doesn't exist.
    output_dir = "./Results"
    os.makedirs(output_dir, exist_ok=True)

    # Construct the output filename using the path_temp parameter.
    output_file = os.path.join(output_dir, f"system_analysis_V{analysis}_results.jsonl")

    # Write the combined data to the final output file.
    with open(output_file, "w", encoding="utf-8") as f:
        for result in combined_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"\nSuccess! Combined {len(combined_results)} records into '{output_file}'.")

    # Finally, remove the original checkpoint file as requested.
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"Checkpoint file '{checkpoint_file}' removed after successful completion.")
    else:
        print(f"Warning: Checkpoint file '{checkpoint_file}' not found, skipping removal.")


def process_Dataset(analysis, dataset_name, corpus_file, queries_file):
    """Main processing loop for the RAG system."""
    corpus, phrases, phrase_meta, docs, doc_texts = load_and_process_corpus(corpus_file)
    temp_path = 0.7
    temp_gen = 0.7
    # queries_file = "./datasets/ARC-Easy.jsonl"
    queries = load_queries(queries_file, dataset_name)

    checkpoint_file = "./DragonBall_results/checkpoint.json"
    results, start_index = initialize_results(checkpoint_file)

    for i, query_obj in enumerate(queries[start_index:], start=start_index):
        result = process_query(analysis, query_obj, i, corpus, pm, temp_path, temp_gen)
        results.append(result)

        if (i + 1) % 5 == 0:
            save_intermediate_results(results, i, checkpoint_file)

        torch.cuda.empty_cache()
        gc.collect()

    save_final_results(analysis, results, checkpoint_file, dataset_name, temp_path, temp_gen)
    delete_contents("./DragonBall_results")


# Step 8: Test the HyDE retrieval system and save results to a JSON file
if __name__ == "__main__":
    # ... do work ...
    corpus_file = "datasets/HotPotQa_docs.jsonl"

   

    queries_file = "./datasets/finale_queries_arc_fixed.jsonl"
    dataset_name = "dragonball"
    analysis = 6
    process_Dataset(analysis, dataset_name, corpus_file, queries_file)