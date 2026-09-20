"""Unit tests for PrintingService and MockPrinter."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.print_job import Customer, Document, PrintJob
from app.schemas.pricing import PrintOptions
from app.services.printing import MockPrinter, PrintingError, PrintingService


@pytest.fixture
def ready_job(db_session: Session, tmp_path: Path) -> PrintJob:
    """Fixture creating a print job ready for printing."""
    customer = Customer(phone_number="+919876543210")
    db_session.add(customer)
    db_session.commit()

    test_file = tmp_path / "print_test.pdf"
    test_file.write_text("Mock PDF content")

    doc = Document(
        customer_id=customer.id,
        filename="print_test.pdf",
        file_path=str(test_file),
        page_count=3,
        file_size_bytes=100,
    )
    db_session.add(doc)
    db_session.commit()

    options = PrintOptions(copies=2, color="color", duplex="single", paper_size="A4")
    job = PrintingService.create_print_job(
        db=db_session,
        customer_phone=customer.phone_number,
        document_id=doc.id,
        options=options,
        total_price=60.0,
    )
    return job


def test_mock_printer_execution(tmp_path: Path):
    """Test that MockPrinter produces a receipt artifact and pickup code."""
    pickup_code = MockPrinter.execute(
        job_id="test-job-99",
        document_path=str(tmp_path / "doc.pdf"),
        options={"copies": 1, "color": "bw"},
    )

    assert pickup_code.startswith("P-")


def test_dispatch_unpaid_job_raises_error(db_session: Session, ready_job: PrintJob):
    """Test that dispatching a job in 'created' status fails with PrintingError."""
    assert ready_job.status == "created"
    with pytest.raises(PrintingError, match="must be 'queued'"):
        PrintingService.dispatch_to_printer(db=db_session, job_id=ready_job.id)


def test_dispatch_queued_job_succeeds(db_session: Session, ready_job: PrintJob):
    """Test that a queued job transitions to 'completed' with a valid pickup code."""
    # Simulate payment verified -> queued
    ready_job.status = "queued"
    db_session.commit()

    completed = PrintingService.dispatch_to_printer(db=db_session, job_id=ready_job.id)

    assert completed.status == "completed"
    assert completed.pickup_code is not None
    assert completed.pickup_code.startswith("P-")
