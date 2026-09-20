"""SQLAlchemy models for the WhatsApp Print Agent."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


class Customer(Base):
    """Customer entity identified by WhatsApp phone number."""

    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_number = Column(String(30), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="customer", cascade="all, delete-orphan")
    print_jobs = relationship("PrintJob", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded PDF document metadata."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    page_count = Column(Integer, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), default="application/pdf", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="documents")
    print_jobs = relationship("PrintJob", back_populates="document")


class PrintJob(Base):
    """Print job records with specifications, pricing, and execution status."""

    __tablename__ = "print_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Print options
    copies = Column(Integer, default=1, nullable=False)
    color = Column(String(20), default="bw", nullable=False)  # "bw" or "color"
    duplex = Column(String(20), default="single", nullable=False)  # "single" or "double"
    paper_size = Column(String(20), default="A4", nullable=False)

    # Financials & Status
    total_price = Column(Float, nullable=False)
    status = Column(String(30), default="created", nullable=False)  # created, queued, printing, completed, failed
    pickup_code = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="print_jobs")
    document = relationship("Document", back_populates="print_jobs")
    payment = relationship("Payment", back_populates="print_job", uselist=False)


class Payment(Base):
    """Payment records for print jobs."""

    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    print_job_id = Column(String(36), ForeignKey("print_jobs.id"), nullable=False, unique=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False, index=True)
    
    amount = Column(Float, nullable=False)
    status = Column(String(30), default="pending", nullable=False)  # pending, completed, failed
    payment_method = Column(String(50), default="mock", nullable=False)
    gateway_order_id = Column(String(100), nullable=True)
    gateway_payment_id = Column(String(100), nullable=True)
    payment_link_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)

    print_job = relationship("PrintJob", back_populates="payment")
    customer = relationship("Customer", back_populates="payments")


class ConversationSession(Base):
    """Maintains conversational state per customer phone number."""

    __tablename__ = "conversation_sessions"

    phone_number = Column(String(30), primary_key=True, index=True)
    current_step = Column(String(50), default="idle", nullable=False)
    active_document_id = Column(String(36), nullable=True)
    active_print_job_id = Column(String(36), nullable=True)
    state_json = Column(Text, default="{}", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
