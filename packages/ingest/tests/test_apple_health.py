import io

import pytest

from resident_ingest.apple_health import parse_export

EXPORT = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min"
   startDate="2024-03-01 00:00:00 -0800" endDate="2024-03-01 23:59:00 -0800" value="52"/>
 <Record type="HKQuantityTypeIdentifierOxygenSaturation" sourceName="Apple Watch" unit="%"
   startDate="2024-03-01 03:10:00 -0800" endDate="2024-03-01 03:10:00 -0800" value="0.97"/>
 <Record type="HKQuantityTypeIdentifierBodyMass" sourceName="Scale" unit="lb"
   startDate="2024-03-01 07:00:00 -0800" endDate="2024-03-01 07:00:00 -0800" value="180"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
   startDate="2024-03-01 01:00:00 -0800" endDate="2024-03-01 02:30:00 -0800"
   value="HKCategoryValueSleepAnalysisAsleepCore"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch"
   startDate="2024-03-01 00:30:00 -0800" endDate="2024-03-01 01:00:00 -0800"
   value="HKCategoryValueSleepAnalysisInBed"/>
 <Record type="HKQuantityTypeIdentifierDietaryWater" sourceName="App" unit="mL"
   startDate="2024-03-01 09:00:00 -0800" endDate="2024-03-01 09:00:00 -0800" value="500"/>
</HealthData>
"""


def test_parse_export_normalizes_known_records():
    obs = {o.metric: o for o in parse_export(io.BytesIO(EXPORT))}

    assert set(obs) == {"resting_heart_rate", "oxygen_saturation", "body_mass", "sleep_analysis"}
    assert obs["resting_heart_rate"].value == 52
    assert obs["oxygen_saturation"].value == pytest.approx(97)
    assert obs["body_mass"].value == pytest.approx(81.65, abs=0.01)
    assert obs["body_mass"].unit == "kg"
    assert obs["sleep_analysis"].value == 90
    assert obs["sleep_analysis"].value_text == "AsleepCore"


def test_external_ids_are_stable():
    first = [o.external_id for o in parse_export(io.BytesIO(EXPORT))]
    second = [o.external_id for o in parse_export(io.BytesIO(EXPORT))]
    assert first == second
    assert len(set(first)) == len(first)
