# Architecture

## Monorepo layout

- `mobile/`: Expo React Native TypeScript client
- `backend/`: FastAPI API with versioned routing under `/api/v1`
- `docs/`: product and engineering decisions

## Backend shape

- `app/main.py`: FastAPI application assembly
- `app/core/`: config and shared runtime concerns
- `app/api/v1/endpoints/`: route handlers grouped by resource
- `app/services/`: OCR, parsing, normalization, analytics logic
- `tests/`: API and service-level tests

## Mobile shape

- `App.tsx`: initial shell and vertical-slice UI
- `src/config.ts`: environment-backed runtime configuration

## Conventions

- keep API routes versioned from day one
- keep service logic outside route handlers
- prefer small schemas and explicit DTOs
- add tests as behavior appears, not later
