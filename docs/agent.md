# Agent Architecture & Workflow

## Overview

The AI Agent is implemented using **LangGraph** and **LangChain**. Its sole responsibility is natural language understanding (NLU) and conversational assistance. It adheres strictly to the deterministic boundaries defined in `AGENTS.md` and `ARCHITECTURE.md`.

---

## Agent Responsibilities & Boundaries

### What the Agent DOES
- **Intent Detection**: Classifies user messages (e.g., greeting, request to print, pricing inquiry, order status, help).
- **Print Option Extraction**: Extracts structured parameters from natural language (e.g., "3 copies in black and white" -> `copies: 3`, `color: "bw"`).
- **General Support & FAQs**: Explains steps, assists users with formatting or requirements using knowledge base documents.
- **Friendly Response Formatting**: Formats service outputs into clear, conversational WhatsApp messages.

### What the Agent DOES NOT DO
- **No Pricing Calculation**: Pricing is calculated deterministically by `PricingService`.
- **No Payment Verification**: Payment status is verified strictly by `PaymentService`.
- **No Direct Database Writes**: Persistence is performed by core application services.
- **No File Validation**: File size, format, and PDF page counts are verified deterministically via `DocumentService` (PyMuPDF).
- **No Printer Control**: Job submission and dispatch to mock or physical printers is handled by `PrintingService`.
- **No Unrestricted Tool / Shell Access**: The agent has no shell, system, or administrative tools.

---

## State Schema (`AgentState`)

```python
from typing import TypedDict, Optional, Dict, Any, List

class AgentState(TypedDict):
    phone_number: str
    session_id: str
    user_message: Optional[str]
    intent: Optional[str]
    document_id: Optional[str]
    page_count: Optional[int]
    options: Dict[str, Any]      # copies, color, duplex, paper_size
    price_total: Optional[float]
    payment_status: Optional[str]
    print_job_id: Optional[str]
    response_message: Optional[str]
    history: List[Dict[str, str]]
```

---

## LangGraph Node Flow

```text
[Incoming WhatsApp Event]
           ↓
   [detect_intent]
           ↓
    ┌──────┴─────────────────────────┐
    ↓                                ↓
[extract_options]             [faq_support]
    ↓                                ↓
[validate_with_service]       [format_reply]
    ↓                                ↓
[format_reply] ──────────────> [WhatsApp API Outbound]
```

### 1. `detect_intent` Node
Analyzes `user_message` and history to detect user intent:
- `greeting`: User sends "Hi", "Hello".
- `print`: User wants to print a document or uploaded a PDF.
- `pricing`: User asks for cost or quotation.
- `order_status`: User asks where their order/job is.
- `faq`: General inquiries about hours, paper size, location.

### 2. `extract_options` Node
Extracts print configuration attributes:
- `copies` (integer >= 1)
- `color` (`"bw"` or `"color"`)
- `duplex` (`"single"` or `"double"`)
- `paper_size` (`"A4"`)

If mandatory options are missing, the state prompts the user for clarification before handing off to services.

### 3. `faq_support` Node
Retrieves answers from the deterministic knowledge base (`knowledge/`) to answer FAQs without hallucinating prices or terms.

---

## Service Integration

When the user flow reaches an action point requiring critical operations:
1. Agent completes extraction of required inputs.
2. The control transitions to the deterministic service layer (e.g. `PricingService.calculate_price()`).
3. The deterministic service result is returned and formatted for WhatsApp delivery.
