"""WhatsApp Cloud API service for outbound messaging."""

from pathlib import Path
from typing import Any, ClassVar

import httpx

from app.config import settings


class WhatsAppService:
    """Handles communication with Meta WhatsApp Cloud API."""

    # In-memory history for mock mode and testing inspection
    outbound_history: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    def send_text(cls, to: str, text: str) -> dict[str, Any]:
        """Send a standard text message to a WhatsApp user."""
        # Meta API requires digits only (no '+' or whitespace)
        clean_to = "".join(ch for ch in to if ch.isdigit())

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        if settings.MOCK_MODE:
            record = {"to": clean_to, "type": "text", "body": text}
            cls.outbound_history.append(record)
            return {"status": "mock_sent", "payload": payload}

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        url = f"{settings.WHATSAPP_GRAPH_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                print(f"[WhatsAppService] Error sending message to {clean_to}: {response.status_code} - {response.text}")
                return {"status": "error", "code": response.status_code, "detail": response.text}
            return response.json()

    @classmethod
    def send_buttons(
        cls,
        to: str,
        body_text: str,
        buttons: list[dict[str, str]],
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an interactive button message (up to 3 buttons) to a WhatsApp user.
        Each button in `buttons` must be {"id": "...", "title": "..."} (title max 20 chars).
        """
        clean_to = "".join(ch for ch in to if ch.isdigit())

        button_actions = []
        for btn in buttons[:3]:
            btn_title = btn.get("title", "")[:20]
            btn_id = btn.get("id", btn_title)
            button_actions.append({
                "type": "reply",
                "reply": {
                    "id": btn_id,
                    "title": btn_title,
                },
            })

        interactive_payload: dict[str, Any] = {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": button_actions},
        }

        if header_text:
            interactive_payload["header"] = {"type": "text", "text": header_text[:60]}
        if footer_text:
            interactive_payload["footer"] = {"text": footer_text[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": interactive_payload,
        }

        if settings.MOCK_MODE:
            record = {"to": clean_to, "type": "interactive_button", "body": body_text, "buttons": buttons}
            cls.outbound_history.append(record)
            return {"status": "mock_sent", "payload": payload}

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        url = f"{settings.WHATSAPP_GRAPH_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                print(f"[WhatsAppService] Error sending buttons to {clean_to}: {response.status_code} - {response.text}")
                # Fallback to plain text if interactive button is rejected
                return cls.send_text(to, body_text)
            return response.json()

    @classmethod
    def send_cta_url(
        cls,
        to: str,
        body_text: str,
        button_text: str,
        url: str,
        header_text: str | None = None,
        footer_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an interactive CTA URL button message to open an external payment link (e.g. Razorpay).
        """
        clean_to = "".join(ch for ch in to if ch.isdigit())

        interactive_payload: dict[str, Any] = {
            "type": "cta_url",
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": button_text[:20],
                    "url": url,
                },
            },
        }

        if header_text:
            interactive_payload["header"] = {"type": "text", "text": header_text[:60]}
        if footer_text:
            interactive_payload["footer"] = {"text": footer_text[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "interactive",
            "interactive": interactive_payload,
        }

        if settings.MOCK_MODE:
            record = {
                "to": clean_to,
                "type": "cta_url",
                "body": body_text,
                "button_text": button_text,
                "url": url,
            }
            cls.outbound_history.append(record)
            return {"status": "mock_sent", "payload": payload}

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        api_url = f"{settings.WHATSAPP_GRAPH_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

        with httpx.Client(timeout=10.0) as client:
            response = client.post(api_url, json=payload, headers=headers)
            if response.status_code >= 400:
                print(f"[WhatsAppService] Error sending CTA URL to {clean_to}: {response.status_code} - {response.text}")
                return cls.send_text(to, f"{body_text}\n\n👉 {url}")
            return response.json()

    @classmethod
    def download_media(cls, media_id: str) -> Path:
        """Download media file from Meta WhatsApp Cloud API by media_id."""
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "User-Agent": "WhatsAppPrintAgent/1.0",
        }
        meta_url = f"{settings.WHATSAPP_GRAPH_API_URL}/{media_id}"

        with httpx.Client(timeout=30.0) as client:
            # Step 1: Retrieve temporary media download URL
            meta_resp = client.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            download_url = meta_resp.json().get("url")
            if not download_url:
                raise ValueError(f"No download URL found for media ID {media_id}")

            # Step 2: Download binary content
            media_resp = client.get(download_url, headers=headers)
            media_resp.raise_for_status()

            # Step 3: Write to local temporary file
            temp_dir = settings.get_storage_path()
            temp_path = temp_dir / f"inbound_{media_id}.pdf"
            temp_path.write_bytes(media_resp.content)
            return temp_path

    @classmethod
    def clear_history(cls) -> None:
        """Clear recorded messages (useful for unit and integration testing)."""
        cls.outbound_history.clear()
