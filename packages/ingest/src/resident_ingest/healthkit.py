"""Normalize samples pushed by the iOS companion app (live HealthKit sync)."""

from __future__ import annotations

from datetime import datetime

from resident_core import catalog
from resident_ingest.types import NormalizedObservation


def normalize_sample(
    *,
    uuid: str,
    type: str,
    value: float,
    unit: str,
    start: datetime,
    end: datetime,
    source_name: str,
) -> NormalizedObservation | None:
    """Return a normalized observation, or None if the type or unit is not supported."""
    metric = catalog.from_healthkit(type)
    if metric is None:
        return None
    # HealthKit reports percentages as fractions (0.97 for 97%).
    if unit == "%" and value <= 1:
        value *= 100
    try:
        value = catalog.to_canonical(metric, value, unit)
    except ValueError:
        return None
    return NormalizedObservation(
        metric=metric.key,
        value=value,
        unit=metric.unit,
        start_at=start,
        end_at=end,
        source_name=source_name,
        external_id=uuid,
    )
