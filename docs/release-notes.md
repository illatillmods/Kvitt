# Release Notes

## 2026-03-27

- established KVITT monorepo structure
- added root setup docs and phased plan
- documented product, architecture, OCR/parsing, normalization, and analytics direction
- prepared environment configuration examples for backend and mobile
- added free vs premium feature boundaries for safe future monetization
- hardened backend startup with database readiness checks and app lifespan initialization
- made backend models portable across PostgreSQL and SQLite for local test execution
- added Alembic migration infrastructure and a release baseline migration for PostgreSQL deployments
- added a GitHub Actions CI workflow for backend tests and mobile type checks
- added Railway backend deployment config with pre-deploy Alembic migrations and readiness healthchecks
- added mobile production env examples for Railway domains and normalized API base URL handling
