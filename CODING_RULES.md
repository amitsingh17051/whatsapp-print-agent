# Coding Rules

## Python

- Use Python type hints.
- Prefer small functions.
- Avoid global mutable state.
- Use descriptive names.

## FastAPI

Routes should:

- validate input
- call services
- return responses

Routes should NOT:

- contain business logic
- calculate prices
- directly manipulate printer implementation

## Services

Business logic belongs in services.

Example:

GOOD:

route
  ↓
PricingService
  ↓
calculate_price()

BAD:

route
  ↓
price = pages * copies * 2
