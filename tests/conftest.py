"""Pytest test configuration and shared fixtures."""

from pathlib import Path

import pymupdf as fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.services.whatsapp import WhatsAppService


@pytest.fixture(autouse=True)
def clean_whatsapp_history():
    """Clear simulated WhatsApp messages and ensure MOCK_MODE is enabled for tests."""
    original_mock = settings.MOCK_MODE
    settings.MOCK_MODE = True
    WhatsAppService.clear_history()
    yield
    WhatsAppService.clear_history()
    settings.MOCK_MODE = original_mock


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine with StaticPool for multi-threaded testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine) -> Session:
    """Create an isolated session for unit tests."""
    testing_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = testing_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine) -> TestClient:
    """FastAPI TestClient with overridden database session pointing to test_engine."""
    testing_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = testing_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_factory(tmp_path: Path):
    """Factory fixture to create sample PDF files with custom page counts."""
    def _create_pdf(filename: str = "sample.pdf", pages: int = 3) -> Path:
        file_path = tmp_path / filename
        doc = fitz.open()
        for i in range(pages):
            page = doc.new_page(width=595, height=842)  # A4 size in points
            page.insert_text((50, 50), f"Test Document Page {i + 1}")
        doc.save(str(file_path))
        doc.close()
        return file_path

    return _create_pdf
