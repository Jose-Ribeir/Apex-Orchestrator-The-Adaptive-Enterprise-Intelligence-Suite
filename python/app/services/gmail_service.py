"""Gmail API actions: search (with q filter), read, send, reply, and natural-language query generator.

Uses Gmail API search/filtering: https://developers.google.com/workspace/gmail/api/guides/filtering
"""

import base64
import email.utils
import logging
import urllib.parse
from email.mime.text import MIMEText

import requests

from app.config import get_settings

logger = logging.getLogger("app.gmail_service")

GMAIL_API_BASE = "https://www.googleapis.com/gmail/v1"


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _decode_body(part: dict) -> str:
    """Decode body.data (base64url) from a message part to UTF-8 text."""
    data = part.get("body", {}).get("data")
    if not data:
        return ""
    try:
        pad = 4 - len(data) % 4
        if pad != 4:
            data += "=" * pad
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_text_from_payload(payload: dict) -> str:
    """Extract plain text from payload (format=full). Prefer text/plain parts."""
    parts = payload.get("parts") or []
    if not parts:
        return _decode_body(payload)
    text_parts = []
    for p in parts:
        mime = (p.get("mimeType") or "").lower()
        if mime == "text/plain":
            text_parts.append(_decode_body(p))
        elif mime == "text/html" and not text_parts:
            text_parts.append(_decode_body(p))
    if text_parts:
        return "\n".join(text_parts)
    for p in parts:
        if p.get("parts"):
            return _extract_text_from_payload(p)
    return ""


def search_gmail(
    access_token: str,
    q: str,
    max_results: int = 20,
) -> str:
    """Search Gmail with query string q (Gmail search syntax). Returns formatted summary text.

    See https://developers.google.com/workspace/gmail/api/guides/filtering for q syntax
    (from:, to:, subject:, after:, before:, in:, is:, label:, etc.).
    """
    headers = _headers(access_token)
    list_url = f"{GMAIL_API_BASE}/users/me/messages?maxResults={max_results}&q={urllib.parse.quote(q)}"
    try:
        r = requests.get(list_url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning("Gmail list (search) failed: %s %s", r.status_code, r.text[:200])
            return "[Gmail: search failed.]"
        data = r.json()
        messages = data.get("messages") or []
        if not messages:
            return "No messages match the search."
        lines = []
        for i, m in enumerate(messages[:max_results], 1):
            msg_id = m.get("id")
            if not msg_id:
                continue
            get_url = (
                f"{GMAIL_API_BASE}/users/me/messages/{msg_id}"
                "?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
            )
            mr = requests.get(get_url, headers=headers, timeout=10)
            if mr.status_code != 200:
                lines.append(f"Message {i}: [could not load]")
                continue
            md = mr.json()
            from_h = subj_h = date_h = ""
            for h in md.get("payload", {}).get("headers") or []:
                n = (h.get("name") or "").lower()
                v = h.get("value") or ""
                if n == "from":
                    from_h = v
                elif n == "subject":
                    subj_h = v
                elif n == "date":
                    date_h = v
            snippet = (md.get("snippet") or "").strip()[:200]
            if snippet:
                snippet = " " + snippet
            lines.append(f"Message {i} (id={msg_id}): From: {from_h} | Subject: {subj_h} | Date: {date_h}{snippet}")
        return "\n".join(lines) if lines else "No messages match the search."
    except Exception as e:
        logger.warning("Gmail search failed: %s", e, exc_info=True)
        return "[Gmail: error searching messages.]"


def get_gmail_message(access_token: str, message_id: str) -> str:
    """Read a single Gmail message by id. Returns From, Subject, Date, and body text."""
    headers = _headers(access_token)
    get_url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}?format=full"
    try:
        r = requests.get(get_url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning("Gmail get message failed: %s %s", r.status_code, r.text[:200])
            return "[Gmail: could not load message.]"
        md = r.json()
        from_h = subj_h = date_h = ""
        payload = md.get("payload") or {}
        for h in payload.get("headers") or []:
            n = (h.get("name") or "").lower()
            v = h.get("value") or ""
            if n == "from":
                from_h = v
            elif n == "subject":
                subj_h = v
            elif n == "date":
                date_h = v
        body_text = _extract_text_from_payload(payload)
        if len(body_text) > 3000:
            body_text = body_text[:3000] + "\n...[truncated]"
        return f"From: {from_h}\nSubject: {subj_h}\nDate: {date_h}\n\n{body_text}"
    except Exception as e:
        logger.warning("Gmail get message failed: %s", e, exc_info=True)
        return "[Gmail: error loading message.]"


def _get_message_metadata(access_token: str, message_id: str) -> dict | None:
    """Get threadId, Message-ID, From, Subject for a message. Returns None on failure."""
    headers = _headers(access_token)
    get_url = (
        f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
        "?format=metadata&metadataHeaders=Message-ID&metadataHeaders=From&metadataHeaders=Subject"
    )
    try:
        r = requests.get(get_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        md = r.json()
        thread_id = md.get("threadId")
        message_id_h = from_h = subject_h = ""
        for h in md.get("payload", {}).get("headers") or []:
            n = (h.get("name") or "").lower()
            v = h.get("value") or ""
            if n == "message-id":
                message_id_h = v.strip()
            elif n == "from":
                from_h = v
            elif n == "subject":
                subject_h = v
        return {
            "thread_id": thread_id,
            "message_id_header": message_id_h,
            "from": from_h,
            "subject": subject_h,
        }
    except Exception:
        return None


def _encode_raw_message(msg: MIMEText) -> str:
    """Encode MIME message as base64url for Gmail API."""
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw.rstrip("=")


def send_gmail_message(
    access_token: str,
    to: str,
    subject: str,
    body_plain: str,
) -> tuple[bool, str]:
    """Send a new email. Returns (success, error_message)."""
    if not to or not (to.strip()):
        return False, "Missing recipient (to)."
    try:
        msg = MIMEText(body_plain or "", "plain", "utf-8")
        msg["To"] = to.strip()
        msg["Subject"] = (subject or "").strip() or "(No subject)"
        msg["Date"] = email.utils.formatdate(localtime=True)
        raw = _encode_raw_message(msg)
        send_url = f"{GMAIL_API_BASE}/users/me/messages/send"
        r = requests.post(
            send_url,
            headers={**_headers(access_token), "Content-Type": "application/json"},
            json={"raw": raw},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            err = (r.json() or {}).get("error", {}).get("message", r.text[:200])
            logger.warning("Gmail send failed: %s %s", r.status_code, err)
            return False, err or "Send failed."
        return True, ""
    except Exception as e:
        logger.warning("Gmail send failed: %s", e, exc_info=True)
        return False, str(e)


def reply_gmail_message(
    access_token: str,
    message_id: str,
    body_plain: str,
) -> tuple[bool, str]:
    """Reply to an existing email. Uses threadId and In-Reply-To. Returns (success, error_message)."""
    meta = _get_message_metadata(access_token, message_id)
    if not meta or not meta.get("thread_id"):
        return False, "Could not load original message or thread."
    thread_id = meta["thread_id"]
    reply_to = meta.get("from") or ""
    # Extract email from "Name <email>" or use as-is
    if "<" in reply_to and ">" in reply_to:
        reply_to = reply_to.split("<")[-1].split(">")[0].strip()
    if not reply_to:
        return False, "Could not determine reply recipient."
    try:
        msg = MIMEText(body_plain or "", "plain", "utf-8")
        msg["To"] = reply_to
        subj = (meta.get("subject") or "").strip()
        msg["Subject"] = f"Re: {subj}" if subj else "Re: (reply)"
        msg["Date"] = email.utils.formatdate(localtime=True)
        if meta.get("message_id_header"):
            msg["In-Reply-To"] = meta["message_id_header"]
            msg["References"] = meta["message_id_header"]
        raw = _encode_raw_message(msg)
        send_url = f"{GMAIL_API_BASE}/users/me/messages/send"
        r = requests.post(
            send_url,
            headers={**_headers(access_token), "Content-Type": "application/json"},
            json={"raw": raw, "threadId": thread_id},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            err = (r.json() or {}).get("error", {}).get("message", r.text[:200])
            logger.warning("Gmail reply failed: %s %s", r.status_code, err)
            return False, err or "Reply failed."
        return True, ""
    except Exception as e:
        logger.warning("Gmail reply failed: %s", e, exc_info=True)
        return False, str(e)


def mark_as_read(access_token: str, message_id: str) -> bool:
    """Remove UNREAD label so the message won't be returned by is:unread search. Returns True on success."""
    headers = {**_headers(access_token), "Content-Type": "application/json"}
    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/modify"
    try:
        r = requests.post(url, headers=headers, json={"removeLabelIds": ["UNREAD"]}, timeout=10)
        if r.status_code != 200:
            logger.warning("Gmail mark as read failed: %s %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:
        logger.warning("Gmail mark as read failed: %s", e, exc_info=True)
        return False


def generate_gmail_query(user_message: str) -> str:
    """Convert natural language to a Gmail search query (q parameter).

    Uses Gmail search operators: from:, to:, subject:, after:, before:,
    older_than:, newer_than:, in: (inbox, sent, trash), is: (read, unread),
    label:, has:attachment. Returns empty string if no Gmail intent or on error.
    """
    if not (user_message or "").strip():
        return ""
    settings = get_settings()
    if not getattr(settings, "gemini_api_key", None) or not settings.gemini_api_key.strip():
        return ""
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        prompt = (
            "You are a Gmail search query generator. From the user message, output one Gmail search query.\n\n"
            "Operators: from:, to:, subject:, after:, before:, newer_than:Nd, older_than:Nd, "
            "in:inbox|sent|trash, is:read|unread, label:, has:attachment.\n"
            "If user wants recent/inbox with no filter, reply: in:inbox\n"
            "If not about email, reply exactly: NONE\n"
            "Reply with ONLY the query (or NONE), one line, no quotes."
        )

        resp = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=f"{prompt}\n\nUser message: {user_message.strip()!r}",
        )
        text = (resp.text or "").strip().strip('"').strip()
        if not text or text.upper() == "NONE":
            return ""
        return text
    except Exception as e:
        logger.warning("Gmail query generation failed: %s", e, exc_info=True)
        return ""


def extract_email_action_only(
    user_message: str,
    assistant_response: str,
    gmail_context_with_ids: str,
) -> dict | None:
    """Extract email action (send/reply) from user and assistant text. Does not execute.
    Returns parsed dict with action, to, subject, body, message_id (for reply) or None."""
    import json as _json

    if not (gmail_context_with_ids or "").strip() or not (assistant_response or "").strip():
        return None
    settings = get_settings()
    if not getattr(settings, "gemini_api_key", None) or not settings.gemini_api_key.strip():
        return None
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        prompt = (
            "Extract an email action from the user request and assistant reply.\n\n"
            "If the user asked to SEND a new email and the assistant wrote the content, output JSON only:\n"
            '{"action": "send_email", "to": "recipient@example.com", "subject": "...", "body": "..."}\n'
            "If the user asked to REPLY to an email and the assistant wrote the reply body, output JSON only:\n"
            '{"action": "reply_email", "message_id": "<id from Gmail context>", "body": "..."}\n'
            "message_id must be exactly one of the (id=...) values from the Gmail context below.\n"
            'If there is no send or reply intent, or body is empty, output: {"action": null}\n\n'
            "Gmail context (message ids for reply_email):\n"
            f"{gmail_context_with_ids[:2000]}\n\n"
            "User message:\n"
            f"{user_message[:500]}\n\n"
            "Assistant reply:\n"
            f"{assistant_response[:3000]}"
        )
        resp = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        text = (resp.text or "").strip()
        start_idx = text.find("{")
        if start_idx >= 0:
            end_idx = text.rfind("}")
            if end_idx > start_idx:
                text = text[start_idx : end_idx + 1]
        data = _json.loads(text)
        if not data or data.get("action") is None:
            return None
        return data
    except _json.JSONDecodeError:
        return None
    except Exception as e:
        logger.warning("Email action extraction failed: %s", e, exc_info=True)
        return None


def execute_email_action(user_id: str, action_data: dict, get_token: "object") -> dict:
    """Execute a previously extracted email action (send_email or reply_email).
    get_token: callable(user_id) -> access_token or None.
    Returns {type, success, error}."""
    action = action_data.get("action")
    if not action:
        return {"type": "unknown", "success": False, "error": "No action in payload."}
    token = get_token(user_id) if callable(get_token) else None
    if not token:
        return {"type": action, "success": False, "error": "Gmail not connected."}
    if action == "send_email":
        to = (action_data.get("to") or "").strip()
        body = (action_data.get("body") or "").strip()
        success, err = send_gmail_message(
            token,
            to=to,
            subject=(action_data.get("subject") or "").strip() or "(No subject)",
            body_plain=body,
        )
        return {"type": "send_email", "success": success, "error": err or None}
    if action == "reply_email":
        msg_id = (action_data.get("message_id") or "").strip()
        body = (action_data.get("body") or "").strip()
        if not msg_id:
            return {"type": "reply_email", "success": False, "error": "Missing message_id."}
        success, err = reply_gmail_message(token, msg_id, body)
        return {"type": "reply_email", "success": success, "error": err or None}
    return {"type": action, "success": False, "error": "Unknown action."}


def extract_and_execute_email_actions(
    user_id: str,
    user_message: str,
    assistant_response: str,
    gmail_context_with_ids: str,
    get_token: "object",
) -> dict | None:
    """If the user asked to send/reply and the assistant wrote content, extract params and execute.

    get_token: callable(user_id) -> access_token or None.
    Returns None if no action or extraction failed; else {type, success, error}.
    """
    action_data = extract_email_action_only(user_message, assistant_response, gmail_context_with_ids)
    if not action_data:
        return None
    return execute_email_action(user_id, action_data, get_token)
