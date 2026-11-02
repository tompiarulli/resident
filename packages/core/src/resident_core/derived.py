"""Derived markers computed from other observations.

Each function documents its formula source so ranges and results stay traceable.
Inputs are in the catalog's canonical units.
"""

from __future__ import annotations


def homa_ir(glucose_mg_dl: float, insulin_uiu_ml: float) -> float:
    """HOMA-IR insulin resistance estimate (Matthews et al., Diabetologia 1985)."""
    return glucose_mg_dl * insulin_uiu_ml / 405


def tg_hdl_ratio(triglycerides_mg_dl: float, hdl_mg_dl: float) -> float:
    """Triglyceride to HDL ratio, a common proxy for insulin resistance."""
    if hdl_mg_dl <= 0:
        raise ValueError("HDL must be positive")
    return triglycerides_mg_dl / hdl_mg_dl


def non_hdl_cholesterol(total_mg_dl: float, hdl_mg_dl: float) -> float:
    """Total cholesterol minus HDL."""
    return total_mg_dl - hdl_mg_dl


def egfr_ckd_epi_2021(creatinine_mg_dl: float, age_years: float, female: bool) -> float:
    """eGFR in mL/min/1.73m² using the race-free CKD-EPI 2021 equation (Inker et al., NEJM 2021)."""
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    ratio = creatinine_mg_dl / kappa
    egfr = 142 * min(ratio, 1) ** alpha * max(ratio, 1) ** -1.200 * 0.9938**age_years
    return egfr * 1.012 if female else egfr
