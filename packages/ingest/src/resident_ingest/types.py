from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NormalizedObservation(BaseModel):
    """Source-independent observation ready to be written to the database."""

    metric: str
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    source_name: str
    external_id: str | None = None
