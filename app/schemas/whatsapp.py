"""Schemas for WhatsApp Cloud API webhooks and outbound messages."""

from pydantic import BaseModel, Field


class WhatsAppProfile(BaseModel):
    name: str | None = None


class WhatsAppContact(BaseModel):
    profile: WhatsAppProfile | None = None
    wa_id: str


class WhatsAppTextMessage(BaseModel):
    body: str


class WhatsAppDocumentMessage(BaseModel):
    id: str
    filename: str | None = None
    mime_type: str | None = None
    sha256: str | None = None


class WhatsAppButtonReply(BaseModel):
    id: str
    title: str


class WhatsAppInteractiveMessage(BaseModel):
    type: str
    button_reply: WhatsAppButtonReply | None = None


class WhatsAppInboundMessage(BaseModel):
    from_: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str
    text: WhatsAppTextMessage | None = None
    document: WhatsAppDocumentMessage | None = None
    interactive: WhatsAppInteractiveMessage | None = None


class WhatsAppMetadata(BaseModel):
    display_phone_number: str | None = None
    phone_number_id: str | None = None


class WhatsAppValue(BaseModel):
    messaging_product: str = "whatsapp"
    metadata: WhatsAppMetadata | None = None
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppInboundMessage] | None = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str | None = None
    entry: list[WhatsAppEntry] | None = None


# Outbound message schemas
class OutboundTextBody(BaseModel):
    preview_url: bool = False
    body: str


class OutboundTextMessage(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "text"
    text: OutboundTextBody
