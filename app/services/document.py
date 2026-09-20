"""Document service for handling file validation, storage, and PyMuPDF page extraction."""

import shutil
import uuid
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from sqlalchemy.orm import Session

from app.config import settings
from app.models.print_job import Customer, Document

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class DocumentValidationError(Exception):
    """Raised when an uploaded document fails validation."""


class DocumentService:
    """Service for validating, processing, and storing PDF documents."""

    @staticmethod
    def validate_and_extract_page_count(file_path: Path) -> int:
        """Validate PDF format and extract page count using PyMuPDF."""
        if not file_path.exists():
            raise DocumentValidationError("File does not exist.")

        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise DocumentValidationError(f"File size ({file_size} bytes) exceeds the 25 MB limit.")

        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:
            raise DocumentValidationError("Invalid or corrupted PDF file.") from exc

        try:
            if doc.is_encrypted:
                raise DocumentValidationError("Password-protected or encrypted PDFs are not supported.")

            page_count = doc.page_count
            if page_count < 1:
                raise DocumentValidationError("The document contains no readable pages.")
            if page_count > 500:
                raise DocumentValidationError("Documents with more than 500 pages are not supported in MVP.")

            return page_count
        finally:
            doc.close()

    @classmethod
    def save_and_register_document(
        cls,
        db: Session,
        customer_phone: str,
        source_path: Path,
        original_filename: str,
    ) -> Document:
        """Validate, store, and register a PDF in the database."""
        # Find or create customer
        customer = db.query(Customer).filter(Customer.phone_number == customer_phone).first()
        if not customer:
            customer = Customer(phone_number=customer_phone)
            db.add(customer)
            db.commit()
            db.refresh(customer)

        # Validate PDF
        page_count = cls.validate_and_extract_page_count(source_path)
        file_size = source_path.stat().st_size

        # Determine target file destination
        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}_{Path(original_filename).name}"
        storage_dir = settings.get_storage_path()
        dest_path = storage_dir / safe_filename

        # Move or copy file
        shutil.copy2(source_path, dest_path)

        # Create database record
        doc_record = Document(
            id=doc_id,
            customer_id=customer.id,
            filename=original_filename,
            file_path=str(dest_path),
            page_count=page_count,
            file_size_bytes=file_size,
            mime_type="application/pdf",
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        return doc_record
