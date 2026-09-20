"""WhatsApp webhook API routes adhering strictly to API_CONTRACT.md and CODING_RULES.md."""

import json
from collections import deque
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.services.conversation import ConversationOrchestrator
from app.services.whatsapp import WhatsAppService

router = APIRouter(tags=["WhatsApp"])

# Message Deduplication Cache (LRU FIFO)
_PROCESSED_MESSAGE_IDS: set[str] = set()
_PROCESSED_ORDER: deque[str] = deque(maxlen=2000)


def is_duplicate_message(msg_id: str | None) -> bool:
    """Return True if message has already been processed recently."""
    if not msg_id:
        return False
    if msg_id in _PROCESSED_MESSAGE_IDS:
        return True
    if len(_PROCESSED_ORDER) >= 2000:
        oldest = _PROCESSED_ORDER.popleft()
        _PROCESSED_MESSAGE_IDS.discard(oldest)
    _PROCESSED_ORDER.append(msg_id)
    _PROCESSED_MESSAGE_IDS.add(msg_id)
    return False


@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
) -> Response:
    """
    Handle Meta WhatsApp Webhook verification challenge.
    Conforms to GET /webhook in API_CONTRACT.md.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge or "", media_type="text/plain", status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Receive incoming WhatsApp Cloud API events.
    Conforms to POST /webhook in API_CONTRACT.md.
    """
    try:
        payload = await request.json()
    except (ValueError, json.JSONDecodeError):
        return {"status": "ok"}

    if not isinstance(payload, dict):
        return {"status": "ok"}

    print(f"[Webhook Received]: {json.dumps(payload)}")

    # Process entries safely
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                sender_phone = msg.get("from")
                msg_type = msg.get("type")
                msg_id = msg.get("id")

                if not sender_phone:
                    continue

                if is_duplicate_message(msg_id):
                    print(f"[Webhook] Ignoring duplicate message ID: {msg_id}")
                    continue

                if msg_type == "text":
                    body = msg.get("text", {}).get("body", "")
                    ConversationOrchestrator.handle_message(
                        db=db,
                        sender_phone=sender_phone,
                        text=body,
                    )
                elif msg_type == "document":
                    doc_meta = msg.get("document", {})
                    filename = doc_meta.get("filename", "upload.pdf")
                    mock_local_path = doc_meta.get("local_path")
                    file_path = None

                    if mock_local_path:
                        file_path = Path(mock_local_path)
                    elif doc_meta.get("id"):
                        try:
                            file_path = WhatsAppService.download_media(doc_meta["id"])
                        except (httpx.HTTPError, ValueError, OSError) as e:
                            WhatsAppService.send_text(sender_phone, f"❌ Failed to download attachment: {e}")
                            continue

                    if file_path:
                        ConversationOrchestrator.handle_message(
                            db=db,
                            sender_phone=sender_phone,
                            file_path=file_path,
                            filename=filename,
                        )
                elif msg_type == "interactive":
                    interactive_obj = msg.get("interactive", {})
                    reply_data = interactive_obj.get("button_reply") or interactive_obj.get("list_reply") or {}
                    button_title = reply_data.get("title", "")
                    button_id = reply_data.get("id", "")
                    ConversationOrchestrator.handle_message(
                        db=db,
                        sender_phone=sender_phone,
                        text=button_title,
                        button_id=button_id,
                    )

    return {"status": "ok"}
