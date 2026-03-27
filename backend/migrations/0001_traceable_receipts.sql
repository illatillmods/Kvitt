-- 0001_traceable_receipts.sql
-- Schema additions for KVITT traceable receipt pipeline and analytics.
--
-- This migration is written for PostgreSQL. It is intentionally
-- idempotent so it can be applied safely multiple times.

BEGIN;

-- 1) Ingestion root: receipt_ingestions
CREATE TABLE IF NOT EXISTS receipt_ingestions (
    id UUID PRIMARY KEY,
    user_id UUID NULL REFERENCES users(id),
    source VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'processed',
    original_filename TEXT NULL,
    content_type VARCHAR(128) NULL,
    storage_path TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ NULL,
    error_message TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_receipt_ingestions_user_id
    ON receipt_ingestions (user_id);

-- 2) OCR results linked to ingestions
CREATE TABLE IF NOT EXISTS ocr_results (
    id UUID PRIMARY KEY,
    ingestion_id UUID NOT NULL REFERENCES receipt_ingestions(id),
    provider VARCHAR(64) NOT NULL,
    raw_text TEXT NOT NULL,
    blocks JSONB NULL,
    meta JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ocr_results_ingestion_id
    ON ocr_results (ingestion_id);

-- 3) Parsed line items (immutable parser output)
CREATE TABLE IF NOT EXISTS parsed_line_items (
    id SERIAL PRIMARY KEY,
    ocr_result_id UUID NOT NULL REFERENCES ocr_results(id),
    line_index INTEGER NULL,
    raw_description TEXT NOT NULL,
    original_line TEXT NOT NULL,
    quantity NUMERIC(10,3) NULL,
    unit_price NUMERIC(10,2) NULL,
    total_price NUMERIC(10,2) NULL,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    notes JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_parsed_line_items_ocr_result_id
    ON parsed_line_items (ocr_result_id);

-- 4) Link receipts back to ingestions
ALTER TABLE receipts
    ADD COLUMN IF NOT EXISTS ingestion_id UUID NULL REFERENCES receipt_ingestions(id);

CREATE INDEX IF NOT EXISTS ix_receipts_ingestion_id
    ON receipts (ingestion_id);

-- 5) Strengthen product-level search & purchase history
-- Ensure product.category is indexed
CREATE INDEX IF NOT EXISTS ix_products_category
    ON products (category);

-- Ensure line_items.product_id, line_items.parsed_line_item_id are indexed
ALTER TABLE line_items
    ADD COLUMN IF NOT EXISTS parsed_line_item_id INTEGER NULL REFERENCES parsed_line_items(id);

CREATE INDEX IF NOT EXISTS ix_line_items_product_id
    ON line_items (product_id);

CREATE INDEX IF NOT EXISTS ix_line_items_parsed_line_item_id
    ON line_items (parsed_line_item_id);

-- 6) Aggregated per-product statistics
CREATE TABLE IF NOT EXISTS product_stats (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    total_spend NUMERIC(14,2) NOT NULL DEFAULT 0,
    purchase_count INTEGER NOT NULL DEFAULT 0,
    first_purchase_at TIMESTAMPTZ NULL,
    last_purchase_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7) Habit insight snapshots (optional analytics persistence)
CREATE TABLE IF NOT EXISTS habit_insight_snapshots (
    id SERIAL PRIMARY KEY,
    user_id UUID NULL REFERENCES users(id),
    label TEXT NOT NULL,
    monthly_cost_estimate NUMERIC(12,2) NOT NULL,
    frequency_per_month NUMERIC(10,2) NOT NULL,
    period_start TIMESTAMPTZ NULL,
    period_end TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_habit_insight_snapshots_user_id
    ON habit_insight_snapshots (user_id);

COMMIT;
