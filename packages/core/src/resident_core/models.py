"""SQLAlchemy models.

Every measurement, whether it came from an Apple Watch, a lab PDF or a FHIR bundle, is stored
as an ``Observation`` (loosely modelled on FHIR's Observation resource). Each one keeps a link
back to where it came from so values can always be traced to their source.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SourceKind(enum.StrEnum):
    HEALTHKIT = "healthkit"
    APPLE_HEALTH_EXPORT = "apple_health_export"
    LAB_DOCUMENT = "lab_document"
    FHIR = "fhir"
    MANUAL = "manual"


class Scope(enum.StrEnum):
    """What a device token is allowed to do."""

    INGEST = "ingest"  # write new data (the iOS app)
    READ = "read"  # read health data (agents, MCP clients)
    ADMIN = "admin"  # manage devices, delete data


class DocumentStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    NEEDS_REVIEW = "needs_review"
    COMPLETE = "complete"
    FAILED = "failed"


class Source(Base):
    """A device, app, lab or import that produced observations."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[SourceKind] = mapped_column(Enum(SourceKind, name="source_kind"))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("kind", "name"),)


class Document(Base):
    """An uploaded file (lab report PDF, scan, FHIR bundle). The original is always kept."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    storage_path: Mapped[str] = mapped_column(Text)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.UPLOADED
    )
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    observations: Mapped[list[Observation]] = relationship(back_populates="document")


class Observation(Base):
    """A single measured value at a point (or span) in time."""

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Catalog key, e.g. "heart_rate" or "ldl_cholesterol". See resident_core.catalog.
    metric: Mapped[str] = mapped_column(String(128))
    loinc: Mapped[str | None] = mapped_column(String(16))
    value: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32))
    # Part of the primary key because observations is a TimescaleDB hypertable partitioned on it,
    # and Timescale requires the partition column in every unique constraint.
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference_low: Mapped[float | None] = mapped_column(Float)
    reference_high: Mapped[float | None] = mapped_column(Float)

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    # Stable id from the origin (HealthKit sample UUID, row hash, ...) used to dedupe re-imports.
    external_id: Mapped[str | None] = mapped_column(String(128))
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))
    extra: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[Source] = relationship()
    document: Mapped[Document | None] = relationship(back_populates="observations")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", "start_at"),
        Index("ix_observations_metric_start", "metric", "start_at"),
    )


class Device(Base):
    """A paired client (phone, agent, MCP client) with its own revocable token.

    Only a SHA-256 hash of the token is stored. Tokens are long random strings, so a fast hash
    is enough; the prefix is kept so a token can be recognized without revealing it.
    """

    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_prefix: Mapped[str] = mapped_column(String(16))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(16)))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """A record of an access to health data. Never stores the values that were returned."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Device name, or "user:<tailscale login>" for people using the dashboard.
    actor: Mapped[str] = mapped_column(String(255))
    # Where the access came from, e.g. "api.get_observations" or "mcp.query_observations".
    action: Mapped[str] = mapped_column(String(64))
    # What was asked for: metric, date range, limit. Never values.
    target: Mapped[dict | None] = mapped_column(JSONB)
    result_count: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_audit_events_at", "at"),)
