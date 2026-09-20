# WhatsApp Cloud API Integration

## Overview

The WhatsApp Print Agent communicates with customers via the Meta WhatsApp Cloud API (Graph API).

---

## Webhook Setup

### 1. Verification (`GET /webhook`)

Meta verifies webhook URLs by sending a `GET` request with query parameters:

- `hub.mode`: Expected to be `"subscribe"`.
- `hub.verify_token`: Must match the secret `WHATSAPP_VERIFY_TOKEN` configured in environment.
- `hub.challenge`: An integer string that the server must echo back directly with status `200`.

```python
# Validation logic
if mode == "subscribe" and verify_token == EXPECTED_TOKEN:
    return Response(content=challenge, media_type="text/plain", status_code=200)
return Response(status_code=403)
```

### 2. Event Ingestion (`POST /webhook`)

Meta sends notifications when messages arrive or status updates occur.

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "1555025407",
              "phone_number_id": "PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": { "name": "Customer" },
                "wa_id": "918700525407"
              }
            ],
            "messages": [
              {
                "from": "918700525407",
                "id": "wamid.HBgL...",
                "timestamp": "1726815000",
                "type": "text",
                "text": { "body": "Hi" }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

---

## Supported Message Types

1. **Text Messages (`type: "text"`)**:
   - Extracted from `message["text"]["body"]`.
   - Forwarded to conversational agent.

2. **Document Messages (`type: "document"`)**:
   - Contains `id` (media ID), `mime_type`, and `filename`.
   - Requires downloading through Meta Media API.

3. **Image Messages (`type: "image"`)**:
   - Contains `id` (media ID) and `mime_type`.

---

## Media Download Flow

1. **Retrieve Media URL**:
   ```http
   GET https://graph.facebook.com/v18.0/{media_id}
   Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
   ```
   Response returns JSON containing `"url"`.

2. **Download Binary Content**:
   ```http
   GET {url}
   Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
   ```
   Save the binary stream to `storage/uploads/{filename}`.

---

## Sending Outbound Messages

All outbound messages are sent via HTTP `POST`:

```http
POST https://graph.facebook.com/v18.0/{phone_number_id}/messages
Authorization: Bearer {WHATSAPP_ACCESS_TOKEN}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "{customer_phone_number}",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Your response text here"
  }
}
```
