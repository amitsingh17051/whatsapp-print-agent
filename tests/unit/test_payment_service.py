"""Unit tests for PaymentService."""

import pytest
from sqlalchemy.orm import Session

from app.models.print_job import Customer, Document, PrintJob
from app.services.payment import PaymentError, PaymentService


@pytest.fixture
def sample_job(db_session: Session) -> PrintJob:
    """Fixture creating a test customer, document, and print job."""
    customer = Customer(phone_number="+919876543210")
    db_session.add(customer)
    db_session.commit()

    doc = Document(
        customer_id=customer.id,
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        page_count=4,
        file_size_bytes=1024,
    )
    db_session.add(doc)
    db_session.commit()

    job = PrintJob(
        customer_id=customer.id,
        document_id=doc.id,
        copies=1,
        color="bw",
        duplex="single",
        paper_size="A4",
        total_price=8.0,
        status="created",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_create_and_verify_payment(db_session: Session, sample_job: PrintJob):
    """Test full payment lifecycle from creation to verification."""
    # Create payment
    payment = PaymentService.create_payment(
        db=db_session,
        print_job_id=sample_job.id,
        customer_id=sample_job.customer_id,
        amount=8.0,
    )

    assert payment.id is not None
    assert payment.status == "pending"
    assert payment.amount == 8.0
    assert payment.verified_at is None

    # Verify payment
    verified = PaymentService.verify_payment(db=db_session, payment_id=payment.id)
    assert verified.status == "completed"
    assert verified.verified_at is not None

    # Check that job status updated to 'queued'
    db_session.refresh(sample_job)
    assert sample_job.status == "queued"


def test_payment_for_missing_job_raises_error(db_session: Session):
    """Test error raised when job does not exist."""
    with pytest.raises(PaymentError, match="not found"):
        PaymentService.create_payment(
            db=db_session,
            print_job_id="nonexistent-job-id",
            customer_id="cust-123",
            amount=20.0,
        )


def test_verify_nonexistent_payment_raises_error(db_session: Session):
    """Test error raised when payment id does not exist."""
    with pytest.raises(PaymentError, match="not found"):
        PaymentService.verify_payment(db=db_session, payment_id="nonexistent-pay-id")
