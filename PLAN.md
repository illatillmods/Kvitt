# KVITT Delivery Plan

## Phase 0: Workspace foundation

- establish clean monorepo structure
- add env handling for backend and mobile
- add backend health checks and test setup
- document setup, conventions, and product direction

## Phase 1: First usable vertical slice

- expose backend health and demo receipt endpoints
- render backend connectivity state in the mobile app
- fetch and display a normalized demo receipt in the mobile UI
- keep the backend stateless and mocked where needed

## Phase 2: Receipt ingestion

- capture or upload receipt images from mobile
- validate file types and request limits in backend
- route images through OCR abstraction
- add API tests around upload and parsing behavior

## Phase 3: Normalization and insights

- expand merchant and line-item normalization rules
- add category confidence and anomaly handling
- compute initial spend summaries and item-level insights

## Phase 4: Persistence and user accounts

- introduce database models and migrations intentionally
- persist receipts, merchants, products, and derived insights
- add auth and per-user access boundaries

## Phase 5: Production hardening

- environment-specific config and secrets management
- structured logging, tracing, and error reporting
- CI for tests and release checks
- mobile release pipeline and backend deployment pipeline
