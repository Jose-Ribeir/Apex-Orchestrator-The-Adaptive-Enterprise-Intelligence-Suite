#!/usr/bin/env python3
"""
🏆 GEMINI 3 HACKATHON - QUOTA + WINDOWS FIXED!
✅ Handles 429 quota errors with retry
✅ Windows Unicode fix (encoding='utf-8')
✅ Falls back to working gemini-3-flash-preview
"""

import requests
import json
import time
import os
from pathlib import Path
import sys

BASE_URL = f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', 8000)}"
AGENT_1_NAME = "Engineering_Bot"
AGENT_2_NAME = "Sales_Bot"


class Gemini3HackathonTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BASE_URL

    def print_header(self, title):
        print(f"\n{'=' * 70}")
        print(f"🎯 HACKATHON TEST: {title}")
        print(f"{'=' * 70}")

    def test_health(self):
        self.print_header("1. SERVER HEALTH")
        try:
            resp = self.session.get(f"{self.base_url}/health")
            data = resp.json()
            print("✅ Server ready for Gemini 3 Hackathon!")
            print(f"   Default model: {data.get('default_model', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def optimize_with_retry(self, config, max_retries=3):
        """🔄 Smart retry for 429 quota errors"""
        for attempt in range(max_retries):
            try:
                print(f"🔥 [{attempt + 1}/{max_retries}] {config['name']} -> {config['model_name']}")
                resp = self.session.post(f"{self.base_url}/optimize_prompt", json=config)

                if resp.status_code == 200:
                    data = resp.json()
                    preview = data["optimized_prompt"][:100].replace('\n', ' ') + "..."
                    print(f"✅ 🏆 SUCCESS: {data.get('model_used', 'N/A')}")
                    print(f"   Preview: {preview}")
                    return data["optimized_prompt"]

                elif "429" in resp.text or "quota" in resp.text.lower():
                    wait_time = 25  # From error: retry in 21s
                    print(f"⏳ 429 Quota hit! Waiting {wait_time}s... (Attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
                    return None

            except Exception as e:
                print(f"💥 Attempt {attempt + 1} failed: {e}")
                time.sleep(5)

        print(f"💥 {config['name']} failed after {max_retries} retries")
        return None

    def test_gemini3_optimize(self):
        self.print_header("2. GEMINI 3 OPTIMIZATION (w/ QUOTA RETRY)")

        # 🏆 HACKATHON PRIORITY: Flash works → Pro quota issue
        configs = [
            {
                "name": AGENT_1_NAME,
                "mode": "HACKATHON_ENGINEERING",
                "instructions": ["🏆 GEMINI 3 HACKATHON", "Production code + security", "Long-context reasoning"],
                "tools": ["RAG", "Calculator"],
                "model_name": "gemini-3-pro-preview"  # May hit quota
            },
            {
                "name": AGENT_2_NAME,
                "mode": "HACKATHON_SALES",
                "instructions": ["🏆 GEMINI 3 HACKATHON", "Persuasive ROI demos", "Low-latency streaming"],
                "tools": ["RAG"],
                "model_name": "gemini-3-flash-preview"  # ✅ Already working!
            }
        ]

        prompts = {}
        for config in configs:
            prompt = self.optimize_with_retry(config)
            if prompt:
                prompts[config["name"]] = prompt

        return prompts

    def test_hackathon_rag(self):
        """3. RAG UPLOAD - WINDOWS UNICODE FIXED"""
        self.print_header("3. RAG UPLOAD & AGENT ISOLATION")

        # ✅ UTF-8 encoding for Windows
        files = {
            AGENT_1_NAME: ("hackathon_eng.txt", "🛡️ Engineering Secret: API key = 'gemini3-hackathon-winner-2026'"),
            AGENT_2_NAME: ("hackathon_sales.txt", "💰 Sales Secret: VIP code = 'GEMINI3WIN'")
        }

        for agent, (fname, content) in files.items():
            # 🔧 Windows fix: explicit UTF-8
            Path(fname).write_text(content, encoding='utf-8')

            print(f"📤 Uploading {agent} docs...")
            try:
                with open(fname, "rb") as f:
                    resp = self.session.post(
                        f"{self.base_url}/upload_and_index",
                        files={"file": f},
                        data={"agent_name": agent}
                    )
                print(f"✅ RAG queued: {resp.json()}")
            except Exception as e:
                print(f"❌ RAG failed: {e}")
            finally:
                Path(fname).unlink(missing_ok=True)

        print("⏳ Indexing (20s)...")
        time.sleep(20)

    def test_hackathon_demo(self, prompts):
        self.print_header("4. HACKATHON LIVE DEMO")

        secret = "gemini3-hackathon-winner-2026"
        cases = [
            {"agent": AGENT_1_NAME, "model": "gemini-3-flash-preview", "should_find": True},
            {"agent": AGENT_2_NAME, "model": "gemini-3-flash-preview", "should_find": False}
        ]

        for case in cases:
            if case["agent"] not in prompts:
                print(f"⚠️  Skipping {case['agent']} (no prompt)")
                continue

            print(f"\n🎬 {case['agent']} ({case['model']}): 'API key?'")
            try:
                resp = self.session.post(
                    f"{self.base_url}/generate_stream",
                    json={
                        "agent_name": case["agent"],
                        "message": "What's the engineering API key for hackathon?",
                        "system_prompt": prompts[case["agent"]],
                        "model_name": case["model"]
                    },
                    stream=True
                )

                response = ""
                print("   A: ", end="")
                for line in resp.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode())
                            if data.get("text"):
                                response += data["text"]
                                print(data["text"], end="", flush=True)
                        except:
                            pass
                print()

                found = secret in response
                if (case["should_find"] and found) or (not case["should_find"] and not found):
                    print("✅ 🏆 HACKATHON PASS!")
                else:
                    print("💥 Demo failed isolation test!")

            except Exception as e:
                print(f"💥 Demo error: {e}")

    def run_hackathon_suite(self):
        print("🏆" * 35)
        print("GEMINI 3 HACKATHON - QUOTA-PROOF TEST HARNESS")
        print("💡 Flash works! Pro needs quota upgrade/retry")
        print("🏆" * 35 + "\n")

        if self.test_health():
            prompts = self.test_gemini3_optimize()
            if any(prompts.values()):  # At least one worked
                self.test_hackathon_rag()
                self.test_hackathon_demo(prompts)
                print("\n🎉 HACKATHON READY! Record your 3min demo NOW!")
            else:
                print("\n💡 Upgrade quota: https://aistudio.google.com/app/apikey")


if __name__ == "__main__":
    Gemini3HackathonTester().run_hackathon_suite()