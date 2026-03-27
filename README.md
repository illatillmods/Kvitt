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

Production migration flow:

```bash
cd backend
cp .env.production.example .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Railway backend deploy:

```bash
cd backend
railway init
railway up
```

Railway service configuration for this monorepo:

- set the service root directory to `backend`
- set the config-as-code path to `/backend/railway.json`
- attach a Railway PostgreSQL service to the same project
- set `KVITT_DATABASE_URL=${{Postgres.DATABASE_URL}}` in the backend service variables
- optionally set `KVITT_OPENAI_API_KEY` in the backend service variables for OpenAI-backed long-tail categorization
- keep `KVITT_AUTO_CREATE_TABLES=false`
- keep `KVITT_REQUIRE_DB_READY=true`

The Railway deployment config will:

- run `python -m alembic upgrade head` before each deploy
- start the API with the Railway-provided `PORT`
- healthcheck `GET /api/v1/ready` before switching traffic

Local production-like PostgreSQL:

```bash
cd backend
docker compose -f docker-compose.postgres.yml up -d
alembic upgrade head
```

Production-oriented backend flags:

```bash
KVITT_AUTO_CREATE_TABLES=false
KVITT_REQUIRE_DB_READY=true
```

The API exposes both liveness and readiness:

- `GET /api/v1/health` for process health
- `GET /api/v1/ready` for database readiness

For release builds, keep `KVITT_AUTO_CREATE_TABLES=false` and apply schema changes through Alembic only.

## Mobile setup

```bash
cd mobile
npm install
cp .env.example .env
npm run start
```

For iOS simulator and Expo dev-client builds, keep Metro running while the native app starts:

```bash
cd mobile
npm run dev
```

If you want Expo to open the iOS app directly against the dev client, use:

```bash
cd mobile
npm run ios:dev
```

For Expo Go on a real iPhone or Android device, set `EXPO_PUBLIC_API_BASE_URL` in `mobile/.env` to your machine IP, for example `http://192.168.1.10:8000/api/v1`.

For a Railway-backed mobile build, copy `mobile/.env.production.example` to `mobile/.env` and set your Railway public domain:

```bash
cd mobile
cp .env.production.example .env
```

Use either:

- `EXPO_PUBLIC_API_ORIGIN=https://your-backend.up.railway.app`
- or `EXPO_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app/api/v1`

The app normalizes both formats, so a plain Railway origin is enough.

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
- an optional OpenAI-backed long-tail classifier when `KVITT_OPENAI_API_KEY` is configured
- a local semantic classifier fallback when no external AI key is present or the API call fails

On the client side you can expose both generic and specific views, for example:

- Generic: `Chips`, `Energy drink`, `Beer`
- Specific: `Estrella Grillchips`, `Red Bull`, `Red Bull Zero`

## Docs

Start in [docs/README.md](docs/README.md).

## CI

GitHub Actions runs two checks on pushes and pull requests:

- backend `pytest`
- mobile `npm run typecheck`
