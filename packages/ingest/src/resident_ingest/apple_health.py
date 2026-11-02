"""Streaming parser for Apple Health ``export.xml``.

Exports routinely reach several gigabytes, so records are read with ``iterparse`` and cleared
as they go instead of loading the whole tree. Record types not in the catalog are skipped.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from xml.etree.ElementTree import iterparse

from resident_core import catalog
from resident_ingest.types import NormalizedObservation

# Apple writes dates like "2024-03-01 07:12:45 -0800".
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"

# Sleep stages worth counting as time asleep (HKCategoryValueSleepAnalysis*).
_ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}


def parse_export(file: str | Path | BinaryIO) -> Iterator[NormalizedObservation]:
    for _, elem in iterparse(file, events=("end",)):
        if elem.tag == "Record":
            obs = _parse_record(elem.attrib)
            if obs is not None:
                yield obs
        # Records hold child elements (metadata, HRV beats); clear after each top-level element.
        if elem.tag in ("Record", "Workout", "ActivitySummary", "Correlation"):
            elem.clear()


def _parse_record(attrs: dict[str, str]) -> NormalizedObservation | None:
    metric = catalog.from_healthkit(attrs.get("type", ""))
    if metric is None:
        return None

    start = datetime.strptime(attrs["startDate"], _DATE_FORMAT)
    end = datetime.strptime(attrs["endDate"], _DATE_FORMAT)
    raw_value = attrs.get("value", "")

    if metric.key == "sleep_analysis":
        if raw_value not in _ASLEEP_VALUES:
            return None
        value: float | None = (end - start).total_seconds() / 60
        unit = metric.unit
        value_text: str | None = raw_value.removeprefix("HKCategoryValueSleepAnalysis")
    else:
        try:
            value = float(raw_value)
        except ValueError:
            return None
        unit = attrs.get("unit", metric.unit)
        # HealthKit stores percentages as fractions (0.97 for 97%).
        if unit == "%" and value <= 1:
            value *= 100
        try:
            value = catalog.to_canonical(metric, value, unit)
        except ValueError:
            return None
        unit = metric.unit
        value_text = None

    source_name = attrs.get("sourceName", "Apple Health")
    # Exports carry no sample UUID, so derive a stable id to make re-imports idempotent.
    fingerprint = "|".join(
        (attrs["type"], attrs["startDate"], attrs["endDate"], raw_value, source_name)
    )

    return NormalizedObservation(
        metric=metric.key,
        value=value,
        value_text=value_text,
        unit=unit,
        start_at=start,
        end_at=end,
        source_name=source_name,
        external_id=hashlib.sha256(fingerprint.encode()).hexdigest()[:32],
    )
