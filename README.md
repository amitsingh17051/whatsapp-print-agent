# WhatsApp Print Agent

A WhatsApp-based printing service built with Python 3, FastAPI, SQLite, LangGraph, and PyMuPDF. Users can upload documents, select printing preferences (copies, color, duplex), receive deterministic pricing, complete mock payments, and submit print jobs to a printer queue.

---

## Architecture & Principles

- **Deterministic Business Boundaries**: Pricing calculations, payment verification, PDF validation, and printer commands are executed strictly in application services. AI (LangGraph) is limited to natural language understanding and option extraction.
- **FastAPI**: Thin presentation routes delegating to services.
- **PyMuPDF**: Robust PDF page counting and validation.
- **Mock Implementations**: Includes `MockPrinter` and test payment services for fast, hardware-independent development.

---

## Directory Structure

```text
whatsapp-print-agent/
├── AGENTS.md                 # Core principles and boundaries
├── SPEC.md                   # Product specification & 12-step flow
├── ARCHITECTURE.md           # Architecture overview
├── API_CONTRACT.md           # HTTP endpoint definitions
├── CODING_RULES.md           # Python and FastAPI coding standards
├── TESTING.md                # Testing rules and commands
├── EVALS.md                  # Intent and extraction eval cases
├── docs/                     # Detailed domain documentation
├── knowledge/                # Pricing and FAQ knowledge bases
├── app/
│   ├── main.py               # FastAPI entrypoint
│   ├── config.py             # Configuration settings
│   ├── api/                  # WhatsApp webhook endpoints
│   ├── services/             # Core business services
│   ├── agent/                # LangGraph NLU agent
│   ├── models/               # SQLAlchemy SQLite models
│   ├── database/             # Database connection & session
│   └── schemas/              # Pydantic validation schemas
├── tests/
│   ├── conftest.py           # Test fixtures
│   ├── unit/                 # Service unit tests
│   ├── integration/          # Webhook integration tests
│   └── evals/                # Agent intent/extraction evals
└── storage/                  # Upload directory
```

---

## Setup & Installation

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Run Tests & Linter
```bash
pytest -v
ruff check .
```
