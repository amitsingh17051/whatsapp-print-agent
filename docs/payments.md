# Payments Specification & Mock Payment Flow

## Core Principle

> [!IMPORTANT]
> **AI must NEVER control payment verification or pricing.**  
> Payment status changes must be strictly deterministic and driven by cryptographically verifiable webhooks or explicit service calls.

---

## Payment Lifecycle

```text
[Pending] ──▶ [Paid] ──▶ [Job Created]
   │
   └──▶ [Expired / Failed]
```

1. **Pending**: Order is generated with deterministic total amount; awaiting payment.
2. **Paid**: Payment confirmation received and validated by `PaymentService`.
3. **Failed / Expired**: Payment rejected or timed out.

---

## MVP Mock Payment Flow

For MVP validation without third-party financial gateways:

1. **Payment Creation (`PaymentService.create_payment`)**:
   - Generates a payment intent with:
     - `payment_id`: e.g. `PAY-MOCK-9281`
     - `order_id`: e.g. `ORD-1044`
     - `amount`: Calculated price from `PricingService`
     - `currency`: `"INR"`
     - `status`: `"pending"`
   - Constructs user prompt:
     ```text
     🧾 Total: ₹10.00
     💳 Test Payment Reference: PAY-MOCK-9281
     Reply "PAY" to simulate test payment confirmation.
     ```

2. **Payment Verification (`PaymentService.verify_mock_payment`)**:
   - Triggered when customer sends the designated test confirmation or calls the test verification API.
   - Updates payment record to `"paid"`.
   - Records timestamp and reference.
   - Emits event triggering `PrintingService.create_job()`.

---

## Production Extension Point

To integrate real payment systems (Razorpay / Cashfree / UPI Intent):
- Replace mock verification with HMAC SHA-256 webhook signature validation.
- Store gateway transaction IDs and ledger records in SQLite.
