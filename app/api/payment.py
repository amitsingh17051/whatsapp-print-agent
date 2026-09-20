"""Razorpay payment webhook handler."""

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.print_job import ConversationSession, PrintJob
from app.services.payment import PaymentError, PaymentService
from app.services.payment_gateway import RazorpayService
from app.services.printing import PrintingError, PrintingService
from app.services.whatsapp import WhatsAppService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Payment Webhooks"])


@router.post("/payment")
async def handle_payment_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_razorpay_signature: Annotated[str | None, Header(alias="X-Razorpay-Signature")] = None,
) -> dict[str, Any]:
    """
    Handle incoming Razorpay payment webhooks with cryptographic signature verification.
    Processes 'payment_link.paid' and 'payment.captured' events.
    """
    body_bytes = await request.body()

    # Step 1: Verify cryptographic HMAC SHA-256 signature
    if not x_razorpay_signature or not RazorpayService.verify_webhook_signature(body_bytes, x_razorpay_signature):
        logger.warning("Rejected payment webhook: invalid or missing X-Razorpay-Signature.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        logger.error("Failed to parse payment webhook payload: %s", err)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload.") from err

    event_name = payload.get("event", "")
    logger.info("Received verified Razorpay webhook event: %s", event_name)

    if event_name not in ["payment_link.paid", "payment.captured"]:
        return {"status": "ignored", "event": event_name}

    # Step 2: Extract payment link and job references
    payload_data = payload.get("payload", {})
    payment_link_entity = payload_data.get("payment_link", {}).get("entity", {})
    payment_entity = payload_data.get("payment", {}).get("entity", {})

    notes = payment_link_entity.get("notes") or payment_entity.get("notes") or {}
    print_job_id = notes.get("print_job_id")

    gateway_order_id = payment_link_entity.get("id") or payment_entity.get("order_id")
    gateway_payment_id = payment_entity.get("id")

    # If print_job_id was not in notes, attempt lookup by gateway order ID
    if not print_job_id and gateway_order_id:
        payment_record = PaymentService.get_payment_by_gateway_order_id(db, gateway_order_id)
        if payment_record:
            print_job_id = payment_record.print_job_id

    if not print_job_id:
        logger.warning("Payment webhook without identifiable print_job_id. Order: %s", gateway_order_id)
        return {"status": "unmatched_order", "order_id": gateway_order_id}

    # Step 3: Complete payment deterministically
    try:
        PaymentService.complete_gateway_payment(
            db=db,
            print_job_id=print_job_id,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
            payment_method="razorpay_upi",
        )
    except PaymentError as err:
        logger.error("Payment completion error for job %s: %s", print_job_id, err)
        return {"status": "payment_error", "detail": str(err)}

    # Step 4: Dispatch job to MockPrinter deterministically
    try:
        completed_job = PrintingService.dispatch_to_printer(db, print_job_id)
    except PrintingError as err:
        logger.error("Printing dispatch error for job %s: %s", print_job_id, err)
        return {"status": "print_dispatch_error", "detail": str(err)}

    # Step 5: Notify customer on WhatsApp & reset conversation session
    job = db.query(PrintJob).filter(PrintJob.id == print_job_id).first()
    if job and job.customer:
        customer_phone = job.customer.phone_number

        # Reset active session
        session = db.query(ConversationSession).filter(ConversationSession.phone_number == customer_phone).first()
        if session and session.active_print_job_id == print_job_id:
            session.current_step = "idle"
            session.active_document_id = None
            session.active_print_job_id = None
            session.state_json = json.dumps({"options": {"copies": 1, "color": "bw", "duplex": "single", "paper_size": "A4"}})
            db.commit()

        reply = (
            f"🎉 *Payment Received via UPI!* (₹{completed_job.total_price:.2f})\n\n"
            f"🖨️ *Print Job Completed*\n"
            f"• Job ID: `{completed_job.id}`\n"
            f"• Pickup Code: *{completed_job.pickup_code}*\n"
            f"• Copies: {completed_job.copies} | Mode: {completed_job.color.upper()}\n\n"
            "Please show your Pickup Code at the collection counter."
        )
        WhatsAppService.send_buttons(
            customer_phone,
            reply,
            buttons=[
                {"id": "btn_print", "title": "🖨️ Print Another"},
                {"id": "btn_faq", "title": "❓ Help & FAQ"},
            ],
        )

    return {
        "status": "ok",
        "job_id": print_job_id,
        "pickup_code": completed_job.pickup_code,
    }
