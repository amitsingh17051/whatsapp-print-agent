"""Integration tests for Razorpay payment webhook endpoint."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.config import settings
from app.models.print_job import Customer, Document, Payment, PrintJob
from app.services.whatsapp import WhatsAppService


def test_payment_webhook_missing_or_invalid_signature(client: TestClient):
    """POST /webhook/payment without valid signature must return 400."""
    response = client.post(
        "/webhook/payment",
        content=b'{"event":"payment_link.paid"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert "Invalid webhook signature" in response.json()["detail"]


def test_payment_webhook_valid_signature_completes_job(client: TestClient, db_session, monkeypatch):
    """POST /webhook/payment with valid HMAC SHA-256 signature completes payment and dispatches print."""
    test_secret = "test_wh_secret_xyz"
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", test_secret)
    WhatsAppService.clear_history()

    # Step 1: Seed customer, doc, print job and payment
    customer = Customer(phone_number="+919876500001")
    db_session.add(customer)
    db_session.commit()

    doc = Document(
        customer_id=customer.id,
        filename="invoice.pdf",
        file_path="/tmp/fake_invoice.pdf",
        page_count=2,
        file_size_bytes=1024,
    )
    db_session.add(doc)
    db_session.commit()

    job = PrintJob(
        customer_id=customer.id,
        document_id=doc.id,
        copies=1,
        color="bw",
        total_price=4.0,
        status="created",
    )
    db_session.add(job)
    db_session.commit()

    payment = Payment(
        print_job_id=job.id,
        customer_id=customer.id,
        amount=4.0,
        status="pending",
        payment_method="razorpay_upi",
        gateway_order_id="plink_test_001",
    )
    db_session.add(payment)
    db_session.commit()

    # Step 2: Construct valid webhook payload
    payload_dict = {
        "entity": "event",
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_test_001",
                    "amount": 400,
                    "status": "paid",
                    "notes": {
                        "print_job_id": job.id,
                        "customer_phone": customer.phone_number,
                    },
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_test_999",
                    "method": "upi",
                    "amount": 400,
                }
            },
        },
    }
    raw_payload = json.dumps(payload_dict).encode("utf-8")
    valid_sig = hmac.new(test_secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()

    # Step 3: POST /webhook/payment
    response = client.post(
        "/webhook/payment",
        content=raw_payload,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": valid_sig,
        },
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["job_id"] == job.id
    assert "pickup_code" in res_data

    # Step 4: Verify payment and print job status updated
    db_session.refresh(payment)
    db_session.refresh(job)
    assert payment.status == "completed"
    assert payment.gateway_payment_id == "pay_test_999"
    assert job.status == "completed"
    assert job.pickup_code is not None

    # Step 5: Verify WhatsApp notification sent with Pickup Code
    assert len(WhatsAppService.outbound_history) == 1
    notification = WhatsAppService.outbound_history[0]
    assert "Payment Received via UPI" in notification["body"]
    assert job.pickup_code in notification["body"]
