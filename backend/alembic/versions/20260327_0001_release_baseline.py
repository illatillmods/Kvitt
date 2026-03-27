"""release baseline schema

Revision ID: 20260327_0001
Revises:
Create Date: 2026-03-27 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchants_id", "merchants", ["id"], unique=False)
    op.create_index("ix_merchants_name", "merchants", ["name"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("subcategory", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_category", "products", ["category"], unique=False)
    op.create_index("ix_products_id", "products", ["id"], unique=False)
    op.create_index("ix_products_normalized_name", "products", ["normalized_name"], unique=False)

    op.create_table(
        "receipt_ingestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("storage_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_receipt_ingestions_user_id", "receipt_ingestions", ["user_id"], unique=False)

    op.create_table(
        "ocr_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("blocks", sa.JSON(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_id"], ["receipt_ingestions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocr_results_ingestion_id", "ocr_results", ["ingestion_id"], unique=False)

    op.create_table(
        "parsed_line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ocr_result_id", sa.Uuid(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=True),
        sa.Column("raw_description", sa.String(), nullable=False),
        sa.Column("original_line", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ocr_result_id"], ["ocr_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parsed_line_items_id", "parsed_line_items", ["id"], unique=False)
    op.create_index("ix_parsed_line_items_ocr_result_id", "parsed_line_items", ["ocr_result_id"], unique=False)

    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("merchant_id", sa.Integer(), nullable=True),
        sa.Column("ingestion_id", sa.Uuid(), nullable=True),
        sa.Column("purchase_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_id"], ["receipt_ingestions.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_receipts_ingestion_id", "receipts", ["ingestion_id"], unique=False)
    op.create_index("ix_receipts_purchase_datetime", "receipts", ["purchase_datetime"], unique=False)

    op.create_table(
        "line_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("parsed_line_item_id", sa.Integer(), nullable=True),
        sa.Column("raw_description", sa.String(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parsed_line_item_id"], ["parsed_line_items.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_line_items_id", "line_items", ["id"], unique=False)
    op.create_index("ix_line_items_parsed_line_item_id", "line_items", ["parsed_line_item_id"], unique=False)
    op.create_index("ix_line_items_product_id", "line_items", ["product_id"], unique=False)
    op.create_index("ix_line_items_receipt_id", "line_items", ["receipt_id"], unique=False)

    op.create_table(
        "product_stats",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("total_spend", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("purchase_count", sa.Integer(), nullable=False),
        sa.Column("first_purchase_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_purchase_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("product_id"),
    )

    op.create_table(
        "habit_insight_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("monthly_cost_estimate", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("frequency_per_month", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_habit_insight_snapshots_user_id",
        "habit_insight_snapshots",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_habit_insight_snapshots_user_id", table_name="habit_insight_snapshots")
    op.drop_table("habit_insight_snapshots")
    op.drop_table("product_stats")
    op.drop_index("ix_line_items_receipt_id", table_name="line_items")
    op.drop_index("ix_line_items_product_id", table_name="line_items")
    op.drop_index("ix_line_items_parsed_line_item_id", table_name="line_items")
    op.drop_index("ix_line_items_id", table_name="line_items")
    op.drop_table("line_items")
    op.drop_index("ix_receipts_purchase_datetime", table_name="receipts")
    op.drop_index("ix_receipts_ingestion_id", table_name="receipts")
    op.drop_table("receipts")
    op.drop_index("ix_parsed_line_items_ocr_result_id", table_name="parsed_line_items")
    op.drop_index("ix_parsed_line_items_id", table_name="parsed_line_items")
    op.drop_table("parsed_line_items")
    op.drop_index("ix_ocr_results_ingestion_id", table_name="ocr_results")
    op.drop_table("ocr_results")
    op.drop_index("ix_receipt_ingestions_user_id", table_name="receipt_ingestions")
    op.drop_table("receipt_ingestions")
    op.drop_index("ix_products_normalized_name", table_name="products")
    op.drop_index("ix_products_id", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_merchants_name", table_name="merchants")
    op.drop_index("ix_merchants_id", table_name="merchants")
    op.drop_table("merchants")
    op.drop_table("users")