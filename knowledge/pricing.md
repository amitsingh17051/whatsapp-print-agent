# Pricing Knowledge Base

## Pricing Rules & Standard Rates

All prices are calculated deterministically by `PricingService`.

### Standard Rates (A4)

| Color Mode | Rate per Page (INR) | Description |
|---|---|---|
| Black & White (`bw`) | ₹2.00 | Standard monochrome printing on 75 GSM A4 paper |
| Color (`color`) | ₹10.00 | Full color printing on 75 GSM A4 paper |

---

## Calculation Formula

$$\text{Total Price} = \text{Page Count} \times \text{Number of Copies} \times \text{Rate per Page}$$

### Examples:
1. **Document with 5 pages, Black & White, 1 copy:**
   - 5 pages $\times$ 1 copy $\times$ ₹2.00 = **₹10.00**
2. **Document with 10 pages, Color, 2 copies:**
   - 10 pages $\times$ 2 copies $\times$ ₹10.00 = **₹200.00**
3. **Document with 3 pages, Black & White, 3 copies:**
   - 3 pages $\times$ 3 copies $\times$ ₹2.00 = **₹18.00**

---

## Duplex (Double-Sided) Policy

- In the MVP, rate is charged per printed side (page face).
- A 10-page document printed double-sided consumes 5 sheets of paper, but contains 10 printed page faces. Pricing is based on total page faces (10 $\times$ rate).

---

## Safety & Accuracy

- AI models must never invent custom discounts, promotional codes, or rates outside this table.
- All final checkout totals presented to the user must originate from `PricingService.calculate_price()`.
