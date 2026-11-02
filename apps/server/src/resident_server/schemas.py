from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthKitSample(BaseModel):
    """One HealthKit sample as sent by the iOS companion app."""

    uuid: str
    type: str = Field(
        description="HealthKit type identifier, e.g. HKQuantityTypeIdentifierHeartRate"
    )
    value: float
    unit: str
    start: datetime
    end: datetime
    source_name: str


class HealthKitBatch(BaseModel):
    samples: list[HealthKitSample]


class IngestResult(BaseModel):
    received: int
    stored: int
    skipped_unknown: int


class MetricSummary(BaseModel):
    metric: str
    name: str | None
    unit: str | None
    count: int
    latest_at: datetime


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: str
    value: float | None
    value_text: str | None
    unit: str | None
    start_at: datetime
    end_at: datetime | None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    at: datetime
    actor: str
    action: str
    target: dict | None
    result_count: int | None
