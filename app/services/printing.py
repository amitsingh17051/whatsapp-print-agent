"""Printing service and MockPrinter implementation."""

import random

from sqlalchemy.orm import Session

from app.config import settings
from app.models.print_job import Customer, Document, PrintJob
from app.schemas.pricing import PrintOptions


class PrintingError(Exception):
    """Raised when print operations fail."""


class MockPrinter:
    """Simulates physical printer execution without requiring physical hardware."""

    @staticmethod
    def execute(job_id: str, document_path: str, options: dict) -> str:
        """Simulate printing job and produce completion artifact."""
        output_dir = settings.get_output_path()
        output_file = output_dir / f"{job_id}_printed.txt"
        
        pickup_code = f"P-{random.randint(1000, 9999)}"

        receipt_content = (
            f"=== MOCK PRINTER RECEIPT ===\n"
            f"Job ID: {job_id}\n"
            f"Source Document: {document_path}\n"
            f"Options: {options}\n"
            f"Pickup Code: {pickup_code}\n"
            f"Status: COMPLETED\n"
            f"============================\n"
        )
        output_file.write_text(receipt_content, encoding="utf-8")
        return pickup_code


class PrintingService:
    """Coordinates print job lifecycle from creation to mock printer dispatch."""

    @staticmethod
    def create_print_job(
        db: Session,
        customer_phone: str,
        document_id: str,
        options: PrintOptions,
        total_price: float,
    ) -> PrintJob:
        """Create an initial print job in 'created' state."""
        customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
        if not customer:
            customer = Customer(phone_number=customer_phone)
            db.add(customer)
            db.commit()
            db.refresh(customer)

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise PrintingError(f"Document '{document_id}' not found.")

        job = PrintJob(
            customer_id=customer.id,
            document_id=document_id,
            copies=options.copies,
            color=options.color,
            duplex=options.duplex,
            paper_size=options.paper_size,
            total_price=total_price,
            status="created",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def dispatch_to_printer(
        db: Session,
        job_id: str,
    ) -> PrintJob:
        """Submit a queued job to MockPrinter and mark as completed."""
        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise PrintingError(f"Print job '{job_id}' not found.")

        if job.status != "queued":
            raise PrintingError(f"Cannot print job '{job_id}' in '{job.status}' status (must be 'queued').")

        # Set to printing
        job.status = "printing"
        db.commit()

        # Run mock printer
        opts = {
            "copies": job.copies,
            "color": job.color,
            "duplex": job.duplex,
            "paper_size": job.paper_size,
        }
        pickup_code = MockPrinter.execute(
            job_id=job.id,
            document_path=job.document.file_path,
            options=opts,
        )

        # Mark completed
        job.status = "completed"
        job.pickup_code = pickup_code
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> PrintJob | None:
        """Fetch print job by ID."""
        return db.query(PrintJob).filter(PrintJob.id == job_id).first()
