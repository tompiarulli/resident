"""Initial schema: sources, documents and the observations hypertable.

Revision ID: 0001
Revises:
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    source_kind = postgresql.ENUM(
        "HEALTHKIT", "APPLE_HEALTH_EXPORT", "LAB_DOCUMENT", "FHIR", "MANUAL", name="source_kind"
    )
    document_status = postgresql.ENUM(
        "UPLOADED", "EXTRACTING", "NEEDS_REVIEW", "COMPLETE", "FAILED", name="document_status"
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", source_kind, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("kind", "name"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("extracted_text", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(128), nullable=False),
        sa.Column("loinc", sa.String(16)),
        sa.Column("value", sa.Float()),
        sa.Column("value_text", sa.Text()),
        sa.Column("unit", sa.String(32)),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("reference_low", sa.Float()),
        sa.Column("reference_high", sa.Float()),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(128)),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id")),
        sa.Column("extra", postgresql.JSONB()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", "start_at"),
        sa.UniqueConstraint("source_id", "external_id", "start_at"),
    )
    op.create_index("ix_observations_metric_start", "observations", ["metric", "start_at"])
    op.execute("SELECT create_hypertable('observations', by_range('start_at'))")


def downgrade() -> None:
    op.drop_table("observations")
    op.drop_table("documents")
    op.drop_table("sources")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS source_kind")
