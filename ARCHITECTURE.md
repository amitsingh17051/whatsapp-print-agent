# Architecture

## High-Level

Customer
   ↓
WhatsApp
   ↓
Meta WhatsApp Cloud API
   ↓
FastAPI
   ↓
Conversation State
   ↓
Application Services
   ↓
Print Job
   ↓
Mock Printer

## Services

### DocumentService

Responsible for:

- receiving documents
- validating documents
- storing documents
- extracting PDF information

### PricingService

Responsible for:

- calculating print price

### PaymentService

Responsible for:

- creating test payment
- verifying test payment

### PrintingService

Responsible for:

- creating print jobs
- sending jobs to printer implementation

## Agent

LangGraph is responsible for:

- understanding natural language
- identifying intent
- extracting structured options
- selecting approved tools

The agent must not directly perform critical business operations.
