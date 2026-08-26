"""Adaptive reflow — observation-only ledgers (DTB-L4 observe leg).

Frozen dataclasses with ``ledger_only=True``; never influence ``beta`` /
claim / prune. No torch; no I/O.
"""
from .ledger import (
    ERR_CAPACITY_CURVE_NOT_TUPLE,
    ERR_CAPACITY_ENTRY_NOT_PAIR,
    ERR_CYCLE_NEGATIVE,
    ERR_CYCLE_NOT_INT,
    ERR_MASS_NEGATIVE,
    ERR_MASS_NOT_FINITE,
    ERR_N_CAP_NOT_FINITE,
    ERR_N_MAX_NOT_FINITE,
    ERR_N_MIN_NOT_FINITE,
    ERR_RESIDUAL_LOWER_NOT_FINITE,
    ERR_RESIDUAL_ORDER,
    ERR_RESIDUAL_UPPER_NOT_FINITE,
    ERR_ROUND_NEGATIVE,
    ERR_ROUND_NOT_INT,
    ERR_SUMMABLE_STATUS_INVALID,
    FreshNoiseCumulativeMassRecord,
    SpectralResidualBandProxy,
    TailDiagnosticStatus,
    empty_diagnostics,
    validate_fresh_noise_cumulative_mass_record,
    validate_spectral_residual_band_proxy,
    validate_tail_diagnostic_status,
)
