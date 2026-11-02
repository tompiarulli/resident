"""Catalog of known metrics.

Maps every source-specific identifier (HealthKit type names, LOINC codes) onto one canonical
metric key with a canonical unit, so the rest of the system never deals with source quirks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Category(StrEnum):
    VITALS = "vitals"
    ACTIVITY = "activity"
    SLEEP = "sleep"
    BODY = "body"
    LIPIDS = "lipids"
    METABOLIC = "metabolic"
    BLOOD = "blood"


@dataclass(frozen=True)
class Metric:
    key: str
    name: str
    unit: str
    category: Category
    healthkit_types: tuple[str, ...] = ()
    loinc: tuple[str, ...] = ()
    # Conversion factors from other units into the canonical unit.
    conversions: dict[str, float] = field(default_factory=dict)


METRICS: tuple[Metric, ...] = (
    # Wearable metrics
    Metric(
        "heart_rate",
        "Heart rate",
        "count/min",
        Category.VITALS,
        ("HKQuantityTypeIdentifierHeartRate",),
        ("8867-4",),
    ),
    Metric(
        "resting_heart_rate",
        "Resting heart rate",
        "count/min",
        Category.VITALS,
        ("HKQuantityTypeIdentifierRestingHeartRate",),
        ("40443-4",),
    ),
    Metric(
        "hrv_sdnn",
        "Heart rate variability (SDNN)",
        "ms",
        Category.VITALS,
        ("HKQuantityTypeIdentifierHeartRateVariabilitySDNN",),
        ("80404-7",),
    ),
    Metric(
        "respiratory_rate",
        "Respiratory rate",
        "count/min",
        Category.VITALS,
        ("HKQuantityTypeIdentifierRespiratoryRate",),
        ("9279-1",),
    ),
    Metric(
        "oxygen_saturation",
        "Blood oxygen",
        "%",
        Category.VITALS,
        ("HKQuantityTypeIdentifierOxygenSaturation",),
        ("59408-5",),
    ),
    Metric(
        "vo2_max",
        "VO2 max",
        "mL/kg/min",
        Category.ACTIVITY,
        ("HKQuantityTypeIdentifierVO2Max",),
        ("60842-2",),
    ),
    Metric(
        "step_count",
        "Steps",
        "count",
        Category.ACTIVITY,
        ("HKQuantityTypeIdentifierStepCount",),
        ("55423-8",),
    ),
    Metric(
        "active_energy",
        "Active energy",
        "kcal",
        Category.ACTIVITY,
        ("HKQuantityTypeIdentifierActiveEnergyBurned",),
        ("41981-2",),
    ),
    Metric(
        "body_mass",
        "Weight",
        "kg",
        Category.BODY,
        ("HKQuantityTypeIdentifierBodyMass",),
        ("29463-7",),
        {"lb": 0.45359237},
    ),
    Metric(
        "body_fat_percentage",
        "Body fat",
        "%",
        Category.BODY,
        ("HKQuantityTypeIdentifierBodyFatPercentage",),
        ("41982-0",),
    ),
    Metric(
        "sleep_analysis", "Sleep", "min", Category.SLEEP, ("HKCategoryTypeIdentifierSleepAnalysis",)
    ),
    # Lab metrics (canonical units are US conventional; SI factors convert into them)
    Metric(
        "total_cholesterol",
        "Total cholesterol",
        "mg/dL",
        Category.LIPIDS,
        loinc=("2093-3",),
        conversions={"mmol/L": 38.67},
    ),
    Metric(
        "ldl_cholesterol",
        "LDL cholesterol",
        "mg/dL",
        Category.LIPIDS,
        loinc=("13457-7", "18262-6"),
        conversions={"mmol/L": 38.67},
    ),
    Metric(
        "hdl_cholesterol",
        "HDL cholesterol",
        "mg/dL",
        Category.LIPIDS,
        loinc=("2085-9",),
        conversions={"mmol/L": 38.67},
    ),
    Metric(
        "triglycerides",
        "Triglycerides",
        "mg/dL",
        Category.LIPIDS,
        loinc=("2571-8",),
        conversions={"mmol/L": 88.57},
    ),
    Metric(
        "apob",
        "Apolipoprotein B",
        "mg/dL",
        Category.LIPIDS,
        loinc=("1884-6",),
        conversions={"g/L": 100.0},
    ),
    Metric(
        "glucose_fasting",
        "Fasting glucose",
        "mg/dL",
        Category.METABOLIC,
        ("HKQuantityTypeIdentifierBloodGlucose",),
        ("1558-6",),
        {"mmol/L": 18.016},
    ),
    Metric(
        "insulin_fasting",
        "Fasting insulin",
        "uIU/mL",
        Category.METABOLIC,
        loinc=("27873-9",),
        conversions={"pmol/L": 1 / 6.0},
    ),
    Metric("hba1c", "Hemoglobin A1c", "%", Category.METABOLIC, loinc=("4548-4",)),
    Metric(
        "creatinine",
        "Creatinine",
        "mg/dL",
        Category.METABOLIC,
        loinc=("2160-0",),
        conversions={"umol/L": 1 / 88.42},
    ),
    Metric("hs_crp", "hs-CRP", "mg/L", Category.BLOOD, loinc=("30522-7",)),
)

_BY_KEY = {m.key: m for m in METRICS}
_BY_HEALTHKIT = {t: m for m in METRICS for t in m.healthkit_types}
_BY_LOINC = {code: m for m in METRICS for code in m.loinc}


def get(key: str) -> Metric | None:
    return _BY_KEY.get(key)


def from_healthkit(type_identifier: str) -> Metric | None:
    return _BY_HEALTHKIT.get(type_identifier)


def from_loinc(code: str) -> Metric | None:
    return _BY_LOINC.get(code)


def to_canonical(metric: Metric, value: float, unit: str) -> float:
    """Convert ``value`` in ``unit`` to the metric's canonical unit."""
    if unit == metric.unit:
        return value
    try:
        return value * metric.conversions[unit]
    except KeyError:
        raise ValueError(
            f"No conversion from {unit!r} to {metric.unit!r} for {metric.key}"
        ) from None
