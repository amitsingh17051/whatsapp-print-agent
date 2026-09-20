# API Contract

## GET /health

### Response

200

{
    "status": "ok"
}

---

## GET /webhook

Purpose:

Meta webhook verification.

---

## POST /webhook

Purpose:

Receive WhatsApp events.

Input:

WhatsApp webhook payload.

Output:

200 OK
