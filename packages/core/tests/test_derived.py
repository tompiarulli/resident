import pytest

from resident_core import catalog, derived


def test_homa_ir():
    assert derived.homa_ir(90, 5) == pytest.approx(1.111, abs=1e-3)


def test_tg_hdl_ratio():
    assert derived.tg_hdl_ratio(100, 50) == 2


def test_egfr_ckd_epi_2021_reference_values():
    # Expected values worked by hand from the published equation.
    assert derived.egfr_ckd_epi_2021(1.0, 50, female=False) == pytest.approx(92, abs=1)
    assert derived.egfr_ckd_epi_2021(0.8, 40, female=True) == pytest.approx(95, abs=1)


def test_catalog_lookup_and_conversion():
    ldl = catalog.from_loinc("13457-7")
    assert ldl is not None and ldl.key == "ldl_cholesterol"
    assert catalog.to_canonical(ldl, 2.5, "mmol/L") == pytest.approx(96.7, abs=0.1)
    assert catalog.from_healthkit("HKQuantityTypeIdentifierRestingHeartRate").key == (
        "resting_heart_rate"
    )


def test_unknown_conversion_raises():
    with pytest.raises(ValueError):
        catalog.to_canonical(catalog.get("hba1c"), 48, "mmol/mol")
