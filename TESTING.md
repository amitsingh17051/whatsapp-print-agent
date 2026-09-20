# Testing

## Unit Tests

Test:

- PDF page extraction
- pricing
- payment
- print job creation
- mock printer

## Integration Tests

Test:

WhatsApp webhook
    ↓
application
    ↓
database

## Required Before Completion

- All tests pass.
- No existing tests are broken.
- API contract remains valid.
- No security secrets are committed.

## Commands

pytest

ruff check .
