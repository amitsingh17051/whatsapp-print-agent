# AGENTS.md

## Project

WhatsApp Print Agent

A WhatsApp-based printing service where users can upload
documents, select printing options, receive pricing,
complete payment, and submit a print job.

## Technology

- Python 3
- FastAPI
- SQLite
- LangGraph
- LangChain
- PyMuPDF
- WhatsApp Cloud API

## Architecture

WhatsApp
    ↓
Meta WhatsApp Cloud API
    ↓
FastAPI
    ↓
Application Services
    ↓
SQLite
    ↓
Print Queue
    ↓
Mock Printer

## Core Principle

The application must remain deterministic for
critical business operations.

AI must NOT control:

- pricing
- payment verification
- database writes
- file validation
- printer commands
- authentication
- security

AI may assist with:

- intent detection
- natural language understanding
- extracting print options
- customer support
- explaining errors

## Coding Rules

- Use Python type hints.
- Keep API routes thin.
- Put business logic in services.
- Keep database operations separate.
- Do not put pricing logic inside LangGraph nodes.
- Do not put payment verification inside prompts.
- Do not give the agent unrestricted shell access.

## Testing

Before considering a feature complete:

1. Add unit tests.
2. Add integration tests when required.
3. Run the test suite.
4. Verify API contracts.
5. Verify agent behavior if the feature involves AI.

## Important

Do not introduce:

- Kubernetes
- microservices
- vector databases
- multiple agents
- production payment systems

until the MVP workflow is working.
