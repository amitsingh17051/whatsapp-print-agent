"""Unit tests for Razorpay Payment Gateway Service."""

import hashlib
import hmac

from app.config import settings
from app.services.payment_gateway import RazorpayService


def test_payment_link_generation_mock_mode():
    """Verify payment link generation produces valid structure and paise amount."""
    data = RazorpayService.create_payment_link(
        amount_inr=16.00,
        print_job_id="test-job-12345678",
        customer_phone="+918700525407",
    )
    assert "short_url" in data
    assert data["amount"] == 1600  # 16.00 * 100 paise
    assert data["currency"] == "INR"


def test_webhook_signature_verification_success(monkeypatch):
    """Verify authentic HMAC SHA-256 signature passes verification."""
    test_secret = "test_secret_abc123"
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", test_secret)

    payload = b'{"event":"payment_link.paid","id":"plink_1"}'
    valid_sig = hmac.new(test_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert RazorpayService.verify_webhook_signature(payload, valid_sig) is True


def test_webhook_signature_verification_tampered_payload(monkeypatch):
    """Verify tampered payload fails signature verification."""
    test_secret = "test_secret_abc123"
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", test_secret)

    payload = b'{"event":"payment_link.paid","id":"plink_1"}'
    valid_sig = hmac.new(test_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    tampered_payload = b'{"event":"payment_link.paid","id":"plink_tampered"}'
    assert RazorpayService.verify_webhook_signature(tampered_payload, valid_sig) is False


def test_webhook_signature_verification_invalid_signature(monkeypatch):
    """Verify invalid signature string is rejected."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "secret")
    assert RazorpayService.verify_webhook_signature(b"{}", "invalid_signature_hex") is False


def test_webhook_signature_verification_missing_secret(monkeypatch):
    """Verify missing secret returns False safely."""
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    assert RazorpayService.verify_webhook_signature(b"{}", "some_signature") is False
