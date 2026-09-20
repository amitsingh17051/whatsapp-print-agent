"""Integration tests for WhatsApp Webhook endpoints and end-to-end user workflow."""

from fastapi.testclient import TestClient

from app.config import settings
from app.services.whatsapp import WhatsAppService


def test_health_check_contract(client: TestClient):
    """GET /health returns 200 with {'status': 'ok'} as specified in API_CONTRACT.md."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_verification_success(client: TestClient):
    """GET /webhook verifies subscription with valid challenge and token."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "1158201444",
        "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "1158201444"


def test_webhook_verification_failure(client: TestClient):
    """GET /webhook rejects invalid verify token with 403."""
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "1158201444",
        "hub.verify_token": "wrong_token",
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403


def test_full_mvp_workflow_end_to_end(client: TestClient, sample_pdf_factory):
    """
    Test the full 12-step MVP printing flow via inbound webhooks:
    1. Customer sends Hi -> receives bot greeting
    2. Customer uploads PDF -> page count extracted
    3. Customer selects options -> system calculates price
    4. Customer sends PAY -> payment verified, job printed, pickup code returned
    """
    phone = "919876543210"
    pdf_path = sample_pdf_factory(filename="report.pdf", pages=4)

    # Step 1: Customer sends "Hi"
    hi_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-1",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-1",
                        "timestamp": "1700000001",
                        "type": "text",
                        "text": {"body": "Hi"},
                    }]
                }
            }]
        }]
    }
    res1 = client.post("/webhook", json=hi_payload)
    assert res1.status_code == 200
    assert len(WhatsAppService.outbound_history) == 1
    assert "Welcome" in WhatsAppService.outbound_history[-1]["body"]

    # Step 2: Customer uploads PDF
    upload_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-2",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-2",
                        "timestamp": "1700000002",
                        "type": "document",
                        "document": {
                            "id": "doc-1",
                            "filename": "report.pdf",
                            "mime_type": "application/pdf",
                            "local_path": str(pdf_path),
                        },
                    }]
                }
            }]
        }]
    }
    res2 = client.post("/webhook", json=upload_payload)
    assert res2.status_code == 200
    assert len(WhatsAppService.outbound_history) == 2
    assert "4 pages" in WhatsAppService.outbound_history[-1]["body"]

    # Step 3: Customer specifies options: "2 copies in color"
    options_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-3",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-3",
                        "timestamp": "1700000003",
                        "type": "text",
                        "text": {"body": "2 copies in color"},
                    }]
                }
            }]
        }]
    }
    res3 = client.post("/webhook", json=options_payload)
    assert res3.status_code == 200
    assert len(WhatsAppService.outbound_history) == 3
    # 4 pages * 2 copies * ₹10 = ₹80.00
    quote_message = WhatsAppService.outbound_history[-1]["body"]
    assert "₹80.00" in quote_message
    assert "PAY" in quote_message

    # Step 4: Customer sends "PAY"
    pay_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-4",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-4",
                        "timestamp": "1700000004",
                        "type": "text",
                        "text": {"body": "PAY"},
                    }]
                }
            }]
        }]
    }
    res4 = client.post("/webhook", json=pay_payload)
    assert res4.status_code == 200
    assert len(WhatsAppService.outbound_history) == 4
    final_message = WhatsAppService.outbound_history[-1]["body"]
    assert "Payment Successful" in final_message
    assert "Pickup Code" in final_message
    assert "P-" in final_message


def test_interactive_button_workflow_end_to_end(client: TestClient, sample_pdf_factory):
    """Verify zero-typing end-to-end flow using WhatsApp interactive button taps."""
    phone = "+919876543299"
    WhatsAppService.clear_history()

    # Step 1: User sends "Hi"
    res1 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b1",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-1",
                        "timestamp": "1700000100",
                        "type": "text",
                        "text": {"body": "Hi"},
                    }]
                }
            }]
        }]
    })
    assert res1.status_code == 200
    assert len(WhatsAppService.outbound_history) == 1
    last_msg = WhatsAppService.outbound_history[-1]
    assert last_msg["type"] == "interactive_button"
    assert any(b["id"] == "btn_print" for b in last_msg["buttons"])

    # Step 2: User taps "btn_pricing"
    res2 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b2",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-2",
                        "timestamp": "1700000101",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "btn_pricing", "title": "💰 Pricing Rates"},
                        },
                    }]
                }
            }]
        }]
    })
    assert res2.status_code == 200
    assert "Price Rates" in WhatsAppService.outbound_history[-1]["body"]

    # Step 3: User uploads a 4-page PDF
    pdf_path = sample_pdf_factory(filename="interactive_doc.pdf", pages=4)

    res3 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b3",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-3",
                        "timestamp": "1700000102",
                        "type": "document",
                        "document": {
                            "id": "doc-btn-1",
                            "filename": "interactive_doc.pdf",
                            "mime_type": "application/pdf",
                            "local_path": str(pdf_path),
                        },
                    }]
                }
            }]
        }]
    })
    assert res3.status_code == 200
    color_prompt = WhatsAppService.outbound_history[-1]
    assert color_prompt["type"] == "interactive_button"
    assert any(b["id"] == "btn_color_bw" for b in color_prompt["buttons"])
    assert any(b["id"] == "btn_color_color" for b in color_prompt["buttons"])

    # Step 4: User taps "btn_color_bw" (Black & White)
    res4 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b4",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-4",
                        "timestamp": "1700000103",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "btn_color_bw", "title": "📄 B&W (₹2/page)"},
                        },
                    }]
                }
            }]
        }]
    })
    assert res4.status_code == 200
    copies_prompt = WhatsAppService.outbound_history[-1]
    assert "Black & White" in copies_prompt["body"]
    assert any(b["id"] == "btn_copies_1" for b in copies_prompt["buttons"])
    assert any(b["id"] == "btn_copies_2" for b in copies_prompt["buttons"])
    assert any(b["id"] == "btn_copies_3" for b in copies_prompt["buttons"])

    # Step 5: User taps "btn_copies_2" (2 copies)
    # Price: 4 pages * 2 copies * ₹2.00 (B&W) = ₹16.00
    res5 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b5",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-5",
                        "timestamp": "1700000104",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "btn_copies_2", "title": "2 Copies"},
                        },
                    }]
                }
            }]
        }]
    })
    assert res5.status_code == 200
    quote_prompt = WhatsAppService.outbound_history[-1]
    assert "₹16.00" in quote_prompt["body"]
    assert quote_prompt["type"] == "cta_url"
    assert "Pay" in quote_prompt["button_text"]

    # Step 6: User taps "btn_pay"
    res6 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-b6",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-6",
                        "timestamp": "1700000105",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "btn_pay", "title": "💳 Pay Now"},
                        },
                    }]
                }
            }]
        }]
    })
    assert res6.status_code == 200
    final_prompt = WhatsAppService.outbound_history[-1]
    assert "Payment Successful" in final_prompt["body"]
    assert "Pickup Code" in final_prompt["body"]
    assert "P-" in final_prompt["body"]
    assert any(b["id"] == "btn_print" for b in final_prompt["buttons"])


def test_interactive_button_reset_workflow(client):
    """Verify session reset via btn_reset button tap."""
    phone = "+919876543298"
    WhatsAppService.clear_history()

    res = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-reset",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "btn-msg-reset",
                        "timestamp": "1700000110",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": "btn_reset", "title": "🔄 Start Over"},
                        },
                    }]
                }
            }]
        }]
    })
    assert res.status_code == 200
    assert "Session reset" in WhatsAppService.outbound_history[-1]["body"]


def test_webhook_message_deduplication(client: TestClient):
    """Verify that duplicate message IDs (Meta webhook retries) are ignored safely."""
    phone = "+919876543297"
    WhatsAppService.clear_history()

    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-dedup",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "wamid.dedup_test_001",
                        "timestamp": "1700000200",
                        "type": "text",
                        "text": {"body": "Hi"},
                    }]
                }
            }]
        }]
    }

    # First delivery: processed
    res1 = client.post("/webhook", json=webhook_payload)
    assert res1.status_code == 200
    assert len(WhatsAppService.outbound_history) == 1

    # Retry with same wamid: ignored, no duplicate outbound messages sent
    res2 = client.post("/webhook", json=webhook_payload)
    assert res2.status_code == 200
    assert len(WhatsAppService.outbound_history) == 1


def test_state_based_unwanted_message_guard(client: TestClient, sample_pdf_factory):
    """Verify that off-topic / unwanted messages during active states do not call AI and return deterministic prompts."""
    phone = "+919876543296"
    WhatsAppService.clear_history()
    pdf_path = sample_pdf_factory(filename="guard_test.pdf", pages=2)

    # 1. Upload PDF -> transitions to select_color
    client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-g1",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-g1",
                        "type": "document",
                        "document": {"id": "doc-g1", "filename": "guard_test.pdf", "local_path": str(pdf_path)},
                    }]
                }
            }]
        }]
    })

    # 2. User sends off-topic text ("tell me a joke") in select_color state
    res_junk1 = client.post("/webhook", json={
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "entry-g2",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "msg-g2",
                        "type": "text",
                        "text": {"body": "tell me a joke"},
                    }]
                }
            }]
        }]
    })
    assert res_junk1.status_code == 200
    # Guard responds deterministically with color choice buttons
    guard_reply = WhatsAppService.outbound_history[-1]
    assert "Please select your print color mode" in guard_reply["body"]
    assert any(b["id"] == "btn_color_bw" for b in guard_reply["buttons"])


