"""Email polling: check Gmail every 30s for new messages and respond via the chat pipeline."""

import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.routers.chat import run_chat_pipeline_collect
from app.schemas.requests import ChatRequest
from app.services import connections_service, gmail_service
from app.services.agent_service import list_agents_from_db
from app.services.gemini_router import is_gemini_rate_limited

logger = logging.getLogger(__name__)

# Per-user set of already-processed Gmail message IDs (cap size to avoid unbounded growth)
_MAX_PROCESSED_IDS_PER_USER = 1000
_processed_message_ids: dict[str, set[str]] = defaultdict(set)

# Don't send these as email replies (model error/empty)
_ERROR_RESPONSE_PATTERNS = (
    "the model did not return",
    "429",
    "quota",
    "please try again later",
    "api quota was exceeded",
)


def _get_default_agent_id() -> str | None:
    """Return the first available agent ID for use when replying to emails."""
    try:
        agents, total = list_agents_from_db(user_id=None, page=1, limit=1)
        if agents:
            return str(agents[0][0].id)
    except Exception as e:
        logger.warning("Email polling: could not get default agent: %s", e)
    return None


def _trim_processed_set(user_id: str) -> None:
    if len(_processed_message_ids[user_id]) > _MAX_PROCESSED_IDS_PER_USER:
        # Drop oldest half (set has no order; we just shrink)
        excess = len(_processed_message_ids[user_id]) - _MAX_PROCESSED_IDS_PER_USER // 2
        for _ in range(min(excess, len(_processed_message_ids[user_id]))):
            _processed_message_ids[user_id].pop()


def run_email_poll_cycle() -> None:
    """One cycle: for each user with Gmail connected, fetch new messages and reply using the chat pipeline."""
    if is_gemini_rate_limited():
        logger.debug("Email polling: skipping cycle (Gemini 429 backoff)")
        return
    agent_id = _get_default_agent_id()
    if not agent_id:
        return
    user_ids = connections_service.list_user_ids_with_gmail_connected()
    if not user_ids:
        return
    for user_id in user_ids:
        token = connections_service.get_valid_access_token(user_id, "google_gmail")
        if not token:
            continue
        try:
            # Fetch only unread messages (inbox, last 2 minutes to avoid reprocessing)
            since = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y/%m/%d")
            q = f"in:inbox is:unread after:{since}"
            gmail_text = gmail_service.search_gmail(token, q=q, max_results=15)
            if not gmail_text or "No messages match" in gmail_text or "[Gmail:" in gmail_text:
                continue
            # Parse message IDs from the summary (format "Message i (id=XXX): ..."); dedupe
            msg_ids = list(dict.fromkeys(re.findall(r"\(id=([a-zA-Z0-9_-]+)\)", gmail_text)))
            for msg_id in msg_ids:
                if msg_id in _processed_message_ids[user_id]:
                    continue
                try:
                    body = gmail_service.get_gmail_message(token, msg_id)
                    if not body or "[Gmail: could not" in body or "[Gmail: error" in body:
                        continue
                    # Use first ~2000 chars as the "message" for the pipeline
                    message = (body[:2000] + "..." if len(body) > 2000 else body).strip()
                    request = ChatRequest(agent_id=agent_id, message=message)
                    response_text = run_chat_pipeline_collect(request, user_id=user_id)
                    if not response_text:
                        continue
                    # Don't send error/placeholder responses as replies; mark processed to avoid retry loop
                    response_lower = response_text.strip().lower()
                    if any(p in response_lower for p in _ERROR_RESPONSE_PATTERNS):
                        logger.warning(
                            "Email polling: skipping reply for %s (model error/empty response)",
                            msg_id[:8],
                        )
                        gmail_service.mark_as_read(token, msg_id)
                        _processed_message_ids[user_id].add(msg_id)
                        _trim_processed_set(user_id)
                        continue
                    success, err = gmail_service.reply_gmail_message(token, msg_id, response_text[:50_000])
                    if success:
                        gmail_service.mark_as_read(token, msg_id)
                        _processed_message_ids[user_id].add(msg_id)
                        _trim_processed_set(user_id)
                        logger.info("Email polling: replied to message %s for user %s", msg_id[:8], user_id[:8])
                    else:
                        logger.warning("Email polling: reply failed for %s: %s", msg_id[:8], err)
                except Exception as e:
                    logger.warning("Email polling: failed to process message %s: %s", msg_id[:8], e, exc_info=True)
        except Exception as e:
            logger.warning("Email polling: failed for user %s: %s", user_id[:8], e, exc_info=True)


async def email_polling_loop() -> None:
    """Background loop: run poll cycle every 30 seconds."""
    logger.info("Email polling loop started (interval 30s)")
    while True:
        try:
            run_email_poll_cycle()
        except Exception as e:
            logger.warning("Email polling cycle error: %s", e, exc_info=True)
        await asyncio.sleep(30)
