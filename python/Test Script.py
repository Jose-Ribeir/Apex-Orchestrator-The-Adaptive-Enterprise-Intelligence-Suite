#!/usr/bin/env python3
"""
🚀 Complete Gemini Agent Factory Test Suite
Tests: optimize_prompt, generate_stream, upload_and_index, health
"""

import requests
import json
import time
import os
from pathlib import Path
import sys

BASE_URL = f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', 8000)}"


class AgentTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BASE_URL
        print(f"🔗 Testing {self.base_url}")

    def print_header(self, title):
        print(f"\n{'=' * 60}")
        print(f"🧪 {title}")
        print(f"{'=' * 60}")

    def test_health(self):
        """Test 1: Server Health Check"""
        self.print_header("HEALTH CHECK")
        try:
            resp = self.session.get(f"{self.base_url}/health")
            data = resp.json()
            print("✅ Server healthy!")
            print(json.dumps(data, indent=2))
            return data.get("rag_loaded", False)
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_optimize_prompt(self):
        """Test 2: Agent Prompt Optimization"""
        self.print_header("PROMPT OPTIMIZATION")
        configs = [
            {
                "name": "CodeMaster",
                "mode": "PERFORMANCE",
                "instructions": [
                    "Always show working code examples",
                    "Explain security implications",
                    "Use best practices"
                ],
                "tools": ["RAG", "Calculator"]
            },
            {
                "name": "QuickMath",
                "mode": "EFFICIENCY",
                "instructions": ["Show your work briefly"],
                "tools": []
            }
        ]

        prompts = {}
        for i, config in enumerate(configs, 1):
            try:
                resp = self.session.post(
                    f"{self.base_url}/optimize_prompt",
                    json=config
                )
                data = resp.json()
                prompt = data["optimized_prompt"][:150] + "..."
                print(f"✅ Config {i}: {prompt}")
                prompts[f"config_{i}"] = data["optimized_prompt"]
            except Exception as e:
                print(f"❌ Config {i} failed: {e}")

        return prompts

    def test_streaming_chat(self, prompts, rag_available):
        """Test 3: Streaming Chat (Direct + RAG paths)"""
        self.print_header("STREAMING CHAT")

        test_cases = [
            {
                "name": "Direct (Math)",
                "message": "What's 15% of 237? Show work.",
                "prompt_key": "config_2",  # Efficiency mode
                "expected_path": "direct"
            },
            {
                "name": "RAG (if available)" if rag_available else "Fallback",
                "message": "How does FastAPI handle dependency injection?",
                "prompt_key": "config_1",  # Performance + RAG
                "expected_path": "retrieval" if rag_available else "direct"
            }
        ]

        for case in test_cases:
            print(f"\n📨 Testing: {case['name']}")
            try:
                request = {
                    "message": case["message"],
                    "system_prompt": prompts[case["prompt_key"]]
                }

                resp = self.session.post(
                    f"{self.base_url}/generate_stream",
                    json=request,
                    stream=True
                )

                full_text = ""
                metrics = {}
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line.decode())
                        if data.get("text"):
                            full_text += data["text"]
                            print(data["text"], end="", flush=True)
                        if data.get("metrics"):
                            metrics = data["metrics"]

                print(f"\n✅ {case['name']} complete!")
                print(f"   Path: {metrics.get('method', 'unknown')} "
                      f"(expected: {case['expected_path']})")
                print(f"   Tokens: {metrics.get('total_tokens', 0)}")
                print(f"   Docs: {metrics.get('docs', 0)}")

            except Exception as e:
                print(f"❌ {case['name']} failed: {e}")

    def test_file_upload(self):
        """Test 4: Document Upload & Indexing"""
        self.print_header("FILE UPLOAD & INDEXING")

        # Create sample doc
        sample_doc = """FastAPI Dependency Injection:
Dependencies are functions that provide values to route handlers.
Use Depends() to inject them automatically.

Example:
from fastapi import Depends

async def get_user(): return {"id": 1}
@app.get("/users/me")
async def read_me(user=Depends(get_user)): return user
"""

        filename = "fastapi_deps.txt"
        with open(filename, "w") as f:
            f.write(sample_doc)

        try:
            with open(filename, "rb") as f:
                files = {"file": f}
                resp = self.session.post(
                    f"{self.base_url}/upload_and_index",
                    files=files
                )

            data = resp.json()
            print("✅ Upload queued:", data)

            # Wait & check indexing
            print("⏳ Waiting for indexing (10s)...")
            time.sleep(10)

            health = self.session.get(f"{self.base_url}/health").json()
            print("📊 Post-upload health:",
                  f"RAG: {health['rag_loaded']}, "
                  f"Index: {health['index_exists']}")

        except Exception as e:
            print(f"❌ Upload failed: {e}")
        finally:
            if Path(filename).exists():
                os.unlink(filename)

    def run_full_suite(self):
        """Run all tests in sequence"""
        print("🚀 Gemini Agent Factory - FULL TEST SUITE")
        print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        rag_available = self.test_health()
        prompts = self.test_optimize_prompt()

        if prompts:
            self.test_streaming_chat(prompts, rag_available)
            self.test_file_upload()

        print("\n" + "=" * 60)
        print("🎉 TEST SUITE COMPLETE!")
        print("=" * 60)


if __name__ == "__main__":
    tester = AgentTester()

    try:
        tester.run_full_suite()
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)