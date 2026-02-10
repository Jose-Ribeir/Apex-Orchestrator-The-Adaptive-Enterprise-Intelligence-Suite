#!/usr/bin/env python3
"""
Test POST /generate_stream with the Field Service Assistant query and an image.

Usage:
  python scripts/test_generate_stream.py <agent_id> [image_path]
  AGENT_ID=<uuid> python scripts/test_generate_stream.py [image_path]

Defaults:
  BASE_URL=http://localhost:8000
  message="I found this crack on the intake manifold and I can smell fuel leaking near it. Is this safe to drive?"
  image_path=optional; if omitted, request is sent without attachments.

Example with image (from repo root):
  python python/scripts/test_generate_stream.py <agent_uuid> assets/c__Users_josep_AppData_Roaming_Cursor_User_workspaceStorage_..._download__2_-50973c3c-d5ba-4d6f-9cba-7569e19d9a46.png

Get agent_id from GET /api/agents (with auth) or from the DB.
"""

import argparse
import base64
import json
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="POST /generate_stream with optional image attachment"
    )
    parser.add_argument(
        "agent_id",
        nargs="?",
        default=os.environ.get("AGENT_ID"),
        help="Agent UUID (or set AGENT_ID)",
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default=None,
        help="Path to image file (e.g. PNG) to attach",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://localhost:8000"),
        help="API base URL (default: http://localhost:8000 or BASE_URL)",
    )
    parser.add_argument(
        "--message",
        default="I found this crack on the intake manifold and I can smell fuel leaking near it. Is this safe to drive?",
        help="User message to send",
    )
    args = parser.parse_args()

    if not args.agent_id:
        print("error: agent_id required (positional or AGENT_ID env)", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/generate_stream"
    body: dict = {
        "agent_id": args.agent_id,
        "message": args.message,
    }
    if args.image_path:
        path = args.image_path
        if not os.path.isfile(path):
            print(f"error: not a file: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, "rb") as f:
            data_b64 = base64.standard_b64encode(f.read()).decode("ascii")
        mime = "image/png"
        if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
            mime = "image/jpeg"
        elif path.lower().endswith(".webp"):
            mime = "image/webp"
        body["attachments"] = [{"mime_type": mime, "data_base64": data_b64}]
        print(f"attaching image: {path} ({mime}, {len(data_b64)} base64 chars)", file=sys.stderr)
    else:
        print("no image_path; sending request without attachments", file=sys.stderr)

    try:
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            if resp.status != 200:
                print(f"error: HTTP {resp.status} {resp.reason}", file=sys.stderr)
                sys.exit(1)
            buffer = b""
            router_decision = None
            model_text_parts: list[str] = []
            final_metrics = None
            for chunk in resp:
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line.decode("utf-8"))
                        if "error" in obj and obj["error"]:
                            print(json.dumps(obj), file=sys.stderr)
                            sys.exit(1)
                        if "router_decision" in obj:
                            router_decision = obj
                            print("# router_decision + metrics:", json.dumps(obj, ensure_ascii=False))
                        elif obj.get("is_final"):
                            final_metrics = obj.get("metrics") or {}
                            print("# is_final + metrics:", json.dumps(obj, ensure_ascii=False))
                        elif "text" in obj and isinstance(obj.get("text"), str):
                            model_text_parts.append(obj["text"])
                            print(json.dumps(obj, ensure_ascii=False))
                        else:
                            print(json.dumps(obj, ensure_ascii=False))
                    except json.JSONDecodeError:
                        print(line.decode("utf-8", errors="replace"))
            if buffer.strip():
                try:
                    obj = json.loads(buffer.decode("utf-8"))
                    if obj.get("is_final"):
                        final_metrics = obj.get("metrics") or {}
                    if "text" in obj and isinstance(obj.get("text"), str) and obj["text"]:
                        model_text_parts.append(obj["text"])
                    print(json.dumps(obj, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(buffer.decode("utf-8", errors="replace"))

            # Summary: response model output
            model_response = "".join(model_text_parts)
            print("\n--- Model response (full text) ---", file=sys.stderr)
            print(model_response or "(empty)", file=sys.stderr)
            print("--- Final metrics ---", file=sys.stderr)
            print(json.dumps(final_metrics or {}, indent=2), file=sys.stderr)
    except urllib.error.HTTPError as e:
        print(f"error: HTTP {e.code} {e.reason}", file=sys.stderr)
        if e.fp:
            body_err = e.fp.read()
            print(body_err.decode("utf-8", errors="replace")[:2000], file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
