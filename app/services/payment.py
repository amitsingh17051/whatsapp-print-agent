"""Payment service for mock payment creation and verification."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.print_job import Payment, PrintJob


class PaymentError(Exception):
    """Raised when a payment operation fails."""


class PaymentService:
    """Deterministic payment service handling MVP mock payments."""

    @staticmethod
    def create_payment(
        db: Session,
        print_job_id: str,
        customer_id: str,
        amount: float,
    ) -> Payment:
        """Create a pending payment record for a print job."""
        job = db.query(PrintJob).filter(PrintJob.id == print_job_id).first()
        if not job:
            raise PaymentError(f"Print job '{print_job_id}' not found.")

        # Check for existing payment
        existing = db.query(Payment).filter(Payment.print_job_id == print_job_id).first()
        if existing:
            return existing

        payment = Payment(
            print_job_id=print_job_id,
            customer_id=customer_id,
            amount=amount,
            status="pending",
            payment_method="mock",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def verify_payment(
        db: Session,
        payment_id: str,
    ) -> Payment:
        """Verify mock payment and transition associated job to 'queued' state."""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentError(f"Payment '{payment_id}' not found.")

        if payment.status == "completed":
            return payment

        # Transition payment state
        payment.status = "completed"
        payment.verified_at = datetime.now(timezone.utc)

        # Update associated print job status to 'queued'
        job = db.query(PrintJob).filter(PrintJob.id == payment.print_job_id).first()
        if job:
            job.status = "queued"

        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def get_payment_by_job_id(db: Session, print_job_id: str) -> Payment | None:
        """Fetch payment record by print job ID."""
        return db.query(Payment).filter(Payment.print_job_id == print_job_id).first()

    @staticmethod
    def record_gateway_link(
        db: Session,
        payment_id: str,
        link_url: str,
        gateway_order_id: str,
    ) -> Payment:
        """Store gateway payment link URL and order ID on payment record."""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise PaymentError(f"Payment '{payment_id}' not found.")
        payment.payment_link_url = link_url
        payment.gateway_order_id = gateway_order_id
        payment.payment_method = "razorpay_upi"
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def get_payment_by_gateway_order_id(db: Session, gateway_order_id: str) -> Payment | None:
        """Find payment by gateway order or payment link ID."""
        return db.query(Payment).filter(Payment.gateway_order_id == gateway_order_id).first()

    @staticmethod
    def complete_gateway_payment(
        db: Session,
        print_job_id: str,
        gateway_order_id: str | None = None,
        gateway_payment_id: str | None = None,
        payment_method: str = "razorpay_upi",
    ) -> Payment:
        """Deterministically complete payment verified by gateway webhook."""
        payment = db.query(Payment).filter(Payment.print_job_id == print_job_id).first()
        if not payment:
            raise PaymentError(f"Payment for job '{print_job_id}' not found.")

        if payment.status == "completed":
            return payment

        payment.status = "completed"
        payment.payment_method = payment_method
        if gateway_order_id:
            payment.gateway_order_id = gateway_order_id
        if gateway_payment_id:
            payment.gateway_payment_id = gateway_payment_id
        payment.verified_at = datetime.now(timezone.utc)

        job = db.query(PrintJob).filter(PrintJob.id == payment.print_job_id).first()
        if job:
            job.status = "queued"

        db.commit()
        db.refresh(payment)
        return payment
