"""Unit tests for DocumentService and PyMuPDF page extraction."""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.print_job import Document
from app.services.document import DocumentService, DocumentValidationError


def test_pdf_page_count_extraction(sample_pdf_factory):
    """Test extracting exact page counts from valid PDFs."""
    pdf_path = sample_pdf_factory(filename="five_pages.pdf", pages=5)
    page_count = DocumentService.validate_and_extract_page_count(pdf_path)
    assert page_count == 5


def test_corrupted_pdf_rejection(tmp_path: Path):
    """Test that corrupted non-PDF files raise DocumentValidationError."""
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("This is not a real PDF file.", encoding="utf-8")

    with pytest.raises(DocumentValidationError, match="Invalid or corrupted PDF file"):
        DocumentService.validate_and_extract_page_count(fake_pdf)


def test_nonexistent_file_rejection(tmp_path: Path):
    """Test that non-existent paths raise DocumentValidationError."""
    missing_path = tmp_path / "missing.pdf"
    with pytest.raises(DocumentValidationError, match="File does not exist"):
        DocumentService.validate_and_extract_page_count(missing_path)


def test_save_and_register_document(sample_pdf_factory, db_session: Session):
    """Test storing document file and creating database records."""
    pdf_path = sample_pdf_factory(filename="contract.pdf", pages=2)
    phone = "+919876543210"

    doc = DocumentService.save_and_register_document(
        db=db_session,
        customer_phone=phone,
        source_path=pdf_path,
        original_filename="contract.pdf",
    )

    assert doc.id is not None
    assert doc.page_count == 2
    assert doc.filename == "contract.pdf"
    assert Path(doc.file_path).exists()

    # Query DB to ensure persistence
    saved_doc = db_session.query(Document).filter(Document.id == doc.id).first()
    assert saved_doc is not None
    assert saved_doc.page_count == 2
