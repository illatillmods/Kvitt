# KVITT

KVITT is a monorepo for a receipt intelligence product with an Expo mobile app, a FastAPI backend, and focused product and engineering docs.

## Workspace

- `mobile/`: Expo React Native app for iPhone and Android.
- `backend/`: FastAPI service with versioned API routes and tests.
- `docs/`: product, architecture, OCR/parsing, normalization, analytics, and release notes.

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend test run:

```bash
cd backend
source .venv/bin/activate
pytest
```

## Mobile setup

```bash
cd mobile
npm install
cp .env.example .env
npm run start
```

For Expo Go on a real iPhone or Android device, set `EXPO_PUBLIC_API_BASE_URL` in `mobile/.env` to your machine IP, for example `http://192.168.1.10:8000/api/v1`.

## First vertical slice

The initial usable slice is a demo receipt flow:

- mobile loads backend status on launch
- mobile can request a demo receipt from the backend
- backend returns parsed and normalized receipt data

That gives an end-to-end baseline before introducing real OCR providers, persistence, and analytics.

## Product normalization

KVITT includes a layered product normalization system focused on messy Swedish retail data:

- OCR and text parsing extract probable line items
- A normalization engine (`app/services/product_normalization/`) turns raw labels into:
  - stable categories (e.g. `beer`, `energy_drink`, `snacks`)
  - canonical product names (e.g. `Red Bull`, `Starköl`, `Chips Grill`)
- The engine is hybrid by design:
  - deterministic Sweden-specific rules (percentages, sizes, abbreviations)
  - an extensible mapping repository for brands and variants
  - a placeholder for AI-assisted classification when confidence is low

On the client side you can expose both generic and specific views, for example:

- Generic: `Chips`, `Energy drink`, `Beer`
- Specific: `Estrella Grillchips`, `Red Bull`, `Red Bull Zero`

## Docs

Start in [docs/README.md](docs/README.md).
