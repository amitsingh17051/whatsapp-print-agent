"""Conversation orchestrator coordinating NLU agent and deterministic application services."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.agent.graph import agent_graph
from app.config import settings
from app.models.print_job import (
    ConversationSession,
    Document,
)
from app.schemas.pricing import PrintOptions
from app.services.document import DocumentService, DocumentValidationError
from app.services.payment import PaymentService
from app.services.payment_gateway import RazorpayService
from app.services.pricing import PricingService
from app.services.printing import PrintingService
from app.services.whatsapp import WhatsAppService


class ConversationOrchestrator:
    """Coordinates WhatsApp conversation states with deterministic services and AI NLU."""

    @classmethod
    def get_or_create_session(cls, db: Session, phone_number: str) -> ConversationSession:
        """Retrieve existing conversational session or create a new one."""
        session = db.query(ConversationSession).filter(ConversationSession.phone_number == phone_number).first()
        if not session:
            session = ConversationSession(
                phone_number=phone_number,
                current_step="idle",
                state_json=json.dumps({"options": {"copies": 1, "color": "bw", "duplex": "single", "paper_size": "A4"}}),
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    @classmethod
    def _generate_and_send_quote(
        cls,
        db: Session,
        session: ConversationSession,
        sender_phone: str,
        doc: Document,
        options_dict: dict[str, Any],
        state_data: dict[str, Any],
    ) -> str:
        """Deterministically calculate pricing, create job & payment, and send interactive quote."""
        print_opts = PrintOptions(
            copies=options_dict.get("copies", 1),
            color=options_dict.get("color", "bw"),
            duplex=options_dict.get("duplex", "single"),
            paper_size=options_dict.get("paper_size", "A4"),
        )

        # Deterministic pricing
        pricing_resp = PricingService.calculate_price(doc.page_count, print_opts)

        # Create print job deterministically
        job = PrintingService.create_print_job(
            db=db,
            customer_phone=sender_phone,
            document_id=doc.id,
            options=print_opts,
            total_price=pricing_resp.total_price,
        )

        # Create pending payment record
        payment = PaymentService.create_payment(
            db=db,
            print_job_id=job.id,
            customer_id=job.customer_id,
            amount=pricing_resp.total_price,
        )

        # Generate Razorpay UPI payment link
        link_data = RazorpayService.create_payment_link(
            amount_inr=pricing_resp.total_price,
            print_job_id=job.id,
            customer_phone=sender_phone,
            description=f"Print {doc.filename} ({doc.page_count} pgs)",
        )
        pay_url = link_data.get("short_url", "")
        gateway_order_id = link_data.get("id", "")
        PaymentService.record_gateway_link(
            db=db,
            payment_id=payment.id,
            link_url=pay_url,
            gateway_order_id=gateway_order_id,
        )

        session.active_print_job_id = job.id
        session.current_step = "payment_pending"
        session.state_json = json.dumps(state_data)
        db.commit()

        color_label = "Black & White" if print_opts.color == "bw" else "Full Color"
        reply = (
            f"📋 *Print Summary & Price Quote*:\n"
            f"• Document: *{doc.filename}*\n"
            f"• Total Pages: {doc.page_count}\n"
            f"• Copies: {print_opts.copies}\n"
            f"• Mode: {color_label} (₹{pricing_resp.rate_per_page:.2f}/page)\n"
            f"• Duplex: {print_opts.duplex.capitalize()}\n"
            f"• Total Price: *₹{pricing_resp.total_price:.2f}*\n\n"
            "Tap the button below to open Razorpay and complete payment via Google Pay, PhonePe, or Paytm (or reply *PAY*):"
        )

        if pay_url:
            WhatsAppService.send_cta_url(
                to=sender_phone,
                body_text=reply,
                button_text=f"💳 Pay ₹{pricing_resp.total_price:.2f}",
                url=pay_url,
                header_text="Print Quote & Payment",
                footer_text="Secured by Razorpay UPI",
            )
        else:
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_pay", "title": "💳 Pay Now"},
                    {"id": "btn_reset", "title": "🔄 Start Over"},
                ],
            )
        return reply

    @classmethod
    def handle_message(
        cls,
        db: Session,
        sender_phone: str,
        text: str | None = None,
        button_id: str | None = None,
        file_path: Path | None = None,
        filename: str | None = None,
    ) -> str:
        """Process inbound WhatsApp message, media event, or interactive button tap."""
        session = cls.get_or_create_session(db, sender_phone)
        state_data: dict[str, Any] = json.loads(session.state_json or "{}")
        options_dict = state_data.get("options", {"copies": 1, "color": "bw", "duplex": "single", "paper_size": "A4"})

        # Case 1: PDF Document Uploaded
        if file_path:
            try:
                doc_record = DocumentService.save_and_register_document(
                    db=db,
                    customer_phone=sender_phone,
                    source_path=file_path,
                    original_filename=filename or "document.pdf",
                )
            except DocumentValidationError as err:
                error_msg = f"❌ *Upload Error*: {err!s}"
                WhatsAppService.send_text(sender_phone, error_msg)
                return error_msg

            session.active_document_id = doc_record.id
            session.current_step = "select_color"
            session.state_json = json.dumps(state_data)
            db.commit()

            reply = (
                f"✅ Document received: *{doc_record.filename}* ({doc_record.page_count} pages).\n\n"
                "Please select your print color mode below:"
            )
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_color_bw", "title": "📄 B&W (₹2/page)"},
                    {"id": "btn_color_color", "title": "🌈 Color (₹10/page)"},
                ],
            )
            return reply

        clean_text = (text or "").strip()
        lower_text = clean_text.lower()
        btn_id = (button_id or "").strip()

        # Case 2: Reset Session ("btn_reset" or "reset" / "start over")
        if btn_id == "btn_reset" or lower_text in ["reset", "start over", "cancel"]:
            session.current_step = "idle"
            session.active_document_id = None
            session.active_print_job_id = None
            options_dict = {"copies": 1, "color": "bw", "duplex": "single", "paper_size": "A4"}
            state_data["options"] = options_dict
            session.state_json = json.dumps(state_data)
            db.commit()

            reply = "🔄 Session reset! Send or upload a PDF to print, or tap an option below:"
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_print", "title": "🖨️ Start Print"},
                    {"id": "btn_pricing", "title": "💰 Pricing Rates"},
                    {"id": "btn_faq", "title": "❓ Help & FAQ"},
                ],
            )
            return reply

        # Case 3: Pricing Button / Inquiry
        if btn_id == "btn_pricing" or lower_text in ["rates", "pricing", "price", "rate card", "prices"]:
            reply = (
                "💰 *Printing Price Rates:*\n\n"
                "• *Black & White*: ₹2.00 / page\n"
                "• *Full Color*: ₹10.00 / page\n"
                "• *Duplex*: Double-sided available\n"
                "• Paper Size: Standard A4\n\n"
                "Ready to print? Send your PDF file or tap *Start Print* below!"
            )
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_print", "title": "🖨️ Start Print"},
                    {"id": "btn_faq", "title": "❓ Help & FAQ"},
                ],
            )
            return reply

        # Case 4: FAQ / Help Button
        if btn_id == "btn_faq" or lower_text in ["help", "faq", "support"]:
            reply = (
                "❓ *QuickPrint FAQ:*\n\n"
                "1️⃣ Send any PDF document here.\n"
                "2️⃣ Tap *B&W* or *Color*.\n"
                "3️⃣ Choose number of copies.\n"
                "4️⃣ Tap *Pay Now* & receive your Pickup Code!\n\n"
                "Tap *Start Print* below or upload a PDF to begin:"
            )
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_print", "title": "🖨️ Start Print"},
                    {"id": "btn_pricing", "title": "💰 Pricing Rates"},
                ],
            )
            return reply

        # Case 5: Start Print Button
        if btn_id == "btn_print":
            if session.active_document_id:
                doc = db.query(Document).filter(Document.id == session.active_document_id).first()
                if doc:
                    reply = f"📄 Active document: *{doc.filename}* ({doc.page_count} pages).\nPlease select your color mode:"
                    WhatsAppService.send_buttons(
                        sender_phone,
                        reply,
                        buttons=[
                            {"id": "btn_color_bw", "title": "📄 B&W (₹2/page)"},
                            {"id": "btn_color_color", "title": "🌈 Color (₹10/page)"},
                        ],
                    )
                    return reply

            reply = "📎 Please attach and send your *PDF document* here to begin printing!"
            WhatsAppService.send_text(sender_phone, reply)
            return reply

        # Case 6: Payment Trigger ("btn_pay" or "pay", "mock pay", "confirm payment")
        if (btn_id == "btn_pay" or lower_text in ["pay", "mock pay", "pay now", "confirm payment", "test payment"]) and session.active_print_job_id:
            job = PrintingService.get_job(db, session.active_print_job_id)
            if job and job.status == "created":
                payment = PaymentService.get_payment_by_job_id(db, job.id)
                if payment:
                    # In MOCK_MODE or test payment simulation, verify directly
                    if settings.MOCK_MODE or lower_text in ["mock pay", "test payment"]:
                        PaymentService.verify_payment(db, payment.id)
                        completed_job = PrintingService.dispatch_to_printer(db, job.id)

                        reply = (
                            f"🎉 *Payment Successful!* (₹{job.total_price:.2f})\n\n"
                            f"🖨️ *Print Job Completed*\n"
                            f"• Job ID: `{completed_job.id}`\n"
                            f"• Pickup Code: *{completed_job.pickup_code}*\n"
                            f"• Copies: {completed_job.copies} | Mode: {completed_job.color.upper()}\n\n"
                            "Please show your Pickup Code at the collection counter."
                        )
                        session.current_step = "idle"
                        session.active_document_id = None
                        session.active_print_job_id = None
                        session.state_json = json.dumps({"options": {"copies": 1, "color": "bw", "duplex": "single", "paper_size": "A4"}})
                        db.commit()

                        WhatsAppService.send_buttons(
                            sender_phone,
                            reply,
                            buttons=[
                                {"id": "btn_print", "title": "🖨️ Print Another"},
                                {"id": "btn_faq", "title": "❓ Help & FAQ"},
                            ],
                        )
                        return reply
                    else:
                        # In real live mode with Razorpay, prompt customer to open the Razorpay payment modal
                        pay_url = payment.payment_link_url or "https://rzp.io"
                        reply = (
                            f"⏳ *Payment Pending: ₹{job.total_price:.2f}*\n\n"
                            "Please tap the button below to open Razorpay and complete payment via Google Pay, PhonePe, or Paytm.\n\n"
                            "Your printout will automatically begin as soon as payment is confirmed!"
                        )
                        WhatsAppService.send_cta_url(
                            to=sender_phone,
                            body_text=reply,
                            button_text=f"💳 Pay ₹{job.total_price:.2f}",
                            url=pay_url,
                            header_text="Razorpay Checkout",
                            footer_text="Secured by Razorpay UPI",
                        )
                        return reply

        # Case 7: Color Selection Button or text
        if btn_id in ["btn_color_bw", "btn_color_color"] or (
            session.active_document_id
            and session.current_step in ["select_color", "document_received"]
            and lower_text in ["bw", "b&w", "black and white", "black & white", "black", "color", "colour", "full color", "full colour"]
        ):
            chosen_color = "color" if (btn_id == "btn_color_color" or "color" in lower_text or "colour" in lower_text) else "bw"
            options_dict["color"] = chosen_color
            state_data["options"] = options_dict
            session.current_step = "select_copies"
            session.state_json = json.dumps(state_data)
            db.commit()

            mode_name = "Full Color (₹10/page)" if chosen_color == "color" else "Black & White (₹2/page)"
            reply = (
                f"Selected: *{mode_name}*\n\n"
                "How many copies do you need?\n"
                "Tap a button below or reply with any number (e.g., 5):"
            )
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_copies_1", "title": "1 Copy"},
                    {"id": "btn_copies_2", "title": "2 Copies"},
                    {"id": "btn_copies_3", "title": "3 Copies"},
                ],
            )
            return reply

        # Case 8: Copies Selection Button or numeric reply
        copies_selected = None
        if btn_id.startswith("btn_copies_"):
            try:
                copies_selected = int(btn_id.replace("btn_copies_", ""))
            except ValueError:
                copies_selected = 1
        elif session.active_document_id and session.current_step == "select_copies" and clean_text.isdigit():
            copies_selected = int(clean_text)

        if copies_selected is not None and session.active_document_id:
            options_dict["copies"] = max(1, copies_selected)
            state_data["options"] = options_dict
            doc = db.query(Document).filter(Document.id == session.active_document_id).first()
            if doc:
                return cls._generate_and_send_quote(
                    db=db,
                    session=session,
                    sender_phone=sender_phone,
                    doc=doc,
                    options_dict=options_dict,
                    state_data=state_data,
                )

        # State-Based Unwanted Message Guards (Zero AI Token Cost)
        if session.active_document_id:
            # Guard: If user is in select_color and sent off-topic text without color or copy intent
            has_color_or_copy = any(k in lower_text for k in ["color", "colour", "bw", "black", "cop", "print"])
            if session.current_step in ["select_color", "document_received"] and not has_color_or_copy:
                reply = (
                    "📄 Please select your print color mode below, or tap Start Over:"
                )
                WhatsAppService.send_buttons(
                    sender_phone,
                    reply,
                    buttons=[
                        {"id": "btn_color_bw", "title": "📄 B&W (₹2/page)"},
                        {"id": "btn_color_color", "title": "🌈 Color (₹10/page)"},
                        {"id": "btn_reset", "title": "🔄 Start Over"},
                    ],
                )
                return reply

            # Guard: If user is in select_copies and sent off-topic text without numeric/copy intent
            has_number = any(ch.isdigit() for ch in clean_text) or "cop" in lower_text
            if session.current_step == "select_copies" and not has_number:
                reply = (
                    "🔢 How many copies do you need?\n"
                    "Please tap a button below or reply with any number (e.g., 1, 2, 5):"
                )
                WhatsAppService.send_buttons(
                    sender_phone,
                    reply,
                    buttons=[
                        {"id": "btn_copies_1", "title": "1 Copy"},
                        {"id": "btn_copies_2", "title": "2 Copies"},
                        {"id": "btn_copies_3", "title": "3 Copies"},
                    ],
                )
                return reply

        # Fast Keyword Match in Idle state (Zero AI Token Cost)
        if (
            session.current_step == "idle"
            and not session.active_document_id
            and lower_text in ["hi", "hello", "hey", "start", "menu", "namaste", "halo"]
        ):
                reply = (
                    "👋 Welcome to *WhatsApp Print Agent*! 🖨️\n\n"
                    "Send or upload any PDF document to print immediately, or tap an option below:"
                )
                session.state_json = json.dumps(state_data)
                db.commit()
                WhatsAppService.send_buttons(
                    sender_phone,
                    reply,
                    buttons=[
                        {"id": "btn_print", "title": "🖨️ Start Print"},
                        {"id": "btn_pricing", "title": "💰 Pricing Rates"},
                        {"id": "btn_faq", "title": "❓ Help & FAQ"},
                    ],
                )
                return reply

        # Case 9: NLU Agent Fallback (Only invoked for substantive natural language queries)
        agent_result = agent_graph.invoke({
            "phone_number": sender_phone,
            "user_message": clean_text,
            "options": options_dict,
        })

        extracted_options = agent_result.get("options", options_dict)
        state_data["options"] = extracted_options
        detected_intent = agent_result.get("intent", "unknown")

        # If user has an active document and specifies options in natural language
        if session.active_document_id and (
            session.current_step in ["document_received", "select_color", "select_copies"]
            or detected_intent == "print"
            or "copies" in (agent_result.get("options") or {})
        ):
            doc = db.query(Document).filter(Document.id == session.active_document_id).first()
            if doc:
                return cls._generate_and_send_quote(
                    db=db,
                    session=session,
                    sender_phone=sender_phone,
                    doc=doc,
                    options_dict=extracted_options,
                    state_data=state_data,
                )

        # If greeting intent or "hi", send welcome with buttons
        if detected_intent == "greeting" or lower_text in ["hi", "hello", "hey", "hola", "start"]:
            reply = (
                "👋 Welcome to *WhatsApp Print Agent*! 🖨️\n\n"
                "Send or upload any PDF document to print immediately, or tap an option below:"
            )
            session.state_json = json.dumps(state_data)
            db.commit()
            WhatsAppService.send_buttons(
                sender_phone,
                reply,
                buttons=[
                    {"id": "btn_print", "title": "🖨️ Start Print"},
                    {"id": "btn_pricing", "title": "💰 Pricing Rates"},
                    {"id": "btn_faq", "title": "❓ Help & FAQ"},
                ],
            )
            return reply

        # Otherwise send agent's response message
        reply = agent_result.get("response_message") or "I'm here to help with your printing needs. Send 'Print' or upload a PDF."
        session.state_json = json.dumps(state_data)
        db.commit()

        WhatsAppService.send_text(sender_phone, reply)
        return reply
