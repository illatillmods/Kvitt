# OCR And Parsing

## Current stance

OCR is behind a small interface so the app can start with a dummy provider and swap in a real one later.

## Near-term plan

- keep a deterministic demo OCR response for fast iteration
- parse Swedish-style receipts first
- validate line-item extraction with focused tests

## Risks

- merchant-specific formats vary heavily
- OCR noise will create brittle parsing if rules stay too naive
- totals and item rows need explicit reconciliation logic later
