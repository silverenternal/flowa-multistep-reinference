"""Wave 93 Phase 1 — unit tests for ``tools.statistical_power_analysis``.

The :mod:`tools.statistical_power_analysis` module computes per-cell
power + 95 % CI + p-value + Bonferroni-corrected verdict for the
Wave 81-91 Tier 3 paper-metric sweeps. This test suite guards against
silent drift in the statistical methodology:

* Test 1 — known distribution → correct CI bounds (Bernoulli
  proportion with predictable variance).
* Test 2 — Bonferroni correction applied correctly (raw p-value
  multiplied by ``N`` and clipped to ``[0, 1]``).
* Test 3 — underpowered verdict triggered when post-hoc power
  to detect 1 pp is below 0.5.
* Test 4 — SUPPORTED / TIE / REGRESSES verdict thresholds across
  the four precedence levels (noise floor, power floor, sign).

All tests run with numpy + scipy only (no torch, no upstream
packages). The Power-formula fixture uses the closed-form two-sided
normal-approximation power (``Cohen 1988 §2.4``) which is what
:func:`tools.statistical_power_analysis._post_hoc_power` implements.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# pandas is required by tools.statistical_power_analysis (it returns
# pd.DataFrame). Skip the entire module when missing so the rest of
# the suite still collects on pandas-less hosts (Wave 122 venv).
_pandas_spec = pytest.importorskip(
    "pandas",
    reason=(
        "pandas not in venv "
        "(install via `uv pip install pandas`)"
    ),
)

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.statistical_power_analysis import (  # noqa: E402
    Z_CRIT_95,
    _bonferroni,
    _ci_95,
    _p_value_two_sided,
    _per_arm_se,
    _post_hoc_power,
    _verdict,
    compute_power_table,
)

# ---------------------------------------------------------------------------
# Test 1: known distribution → correct CI bounds
# ---------------------------------------------------------------------------


def test_known_distribution_ci_bounds() -> None:
    """A Bernoulli proportion with p=0.5 at N=1000 has SE = 0.0158.

    With ``baseline=0.50, framework=0.55, n=1000`` the per-arm
    Bernoulli variances differ slightly (var_b = 0.25, var_f = 0.2475),
    so the SE of the difference is computed via the tool's
    ``_per_arm_se`` helper to avoid hard-coding the asymmetry.

    The CI half-width must equal ``Z_CRIT_95 * SE`` and the CI must
    bracket the true delta.
    """
    cells = [("m", "metric", 0.50, 0.55, 1000)]
    df = compute_power_table(cells)
    row = df.iloc[0]
    delta = float(row["delta"])
    delta_se = float(row["delta_se"])
    ci_lo = float(row["ci_95_lower"])
    ci_hi = float(row["ci_95_upper"])

    # Delta = 0.05 by construction.
    assert delta == pytest.approx(0.05, abs=1e-12)

    # SE of difference = sqrt(se_b^2 + se_f^2) where each arm uses
    # the Bernoulli variance p*(1-p)/n.
    expected_se_b = math.sqrt(0.50 * 0.50 / 1000.0)
    expected_se_f = math.sqrt(0.55 * 0.45 / 1000.0)
    expected_se = math.sqrt(expected_se_b**2 + expected_se_f**2)
    assert delta_se == pytest.approx(expected_se, rel=1e-9)

    # 95 % CI half-width = z_crit * SE.
    half_width = Z_CRIT_95 * expected_se
    assert ci_lo == pytest.approx(0.05 - half_width, rel=1e-9)
    assert ci_hi == pytest.approx(0.05 + half_width, rel=1e-9)
    # And CI must bracket the delta.
    assert ci_lo < delta < ci_hi

    # p-value for z = 0.05 / SE ≈ 2.241 → two-sided p ≈ 0.0250.
    # Bonferroni with N=1 → p_bonf = p_raw.
    expected_z = 0.05 / expected_se
    from scipy.stats import norm
    expected_p = 2.0 * (1.0 - norm.cdf(expected_z))
    assert float(row["p_value_raw"]) == pytest.approx(expected_p, rel=1e-9)
    assert float(row["p_value_bonferroni"]) == pytest.approx(expected_p, rel=1e-9)


# ---------------------------------------------------------------------------
# Test 2: Bonferroni correction applied correctly (alpha/N)
# ---------------------------------------------------------------------------


def test_bonferroni_correction_applied_correctly() -> None:
    """``p_bonf = min(p_raw * N, 1.0)`` across ``N`` cells.

    Six cells with identical per-arm aggregates (Bernoulli proportion
    setup so each arm has equal variance) must yield identical
    p_raw values and p_bonf = p_raw * 6.

    Uses ``delta=0.01`` (1pp) at N=10000 so ``p_raw ≈ 0.16`` and
    ``p_bonf = 6 * 0.16 ≈ 0.94`` stays well below the clipping
    threshold of 1.0.
    """
    n_cells = 6
    cells = [
        ("m", f"metric_{i}", 0.50, 0.51, 10000)
        for i in range(n_cells)
    ]
    df = compute_power_table(cells, alpha=0.05)
    assert len(df) == n_cells

    p_raw_values = df["p_value_raw"].tolist()
    p_bonf_values = df["p_value_bonferroni"].tolist()

    # p_raw should be identical across the 6 symmetric cells.
    first_p = p_raw_values[0]
    for p in p_raw_values[1:]:
        assert p == pytest.approx(first_p, rel=1e-9)

    # p_bonf = p_raw * N (and is < 1 for our synthetic setup).
    for p_raw, p_bonf in zip(p_raw_values, p_bonf_values):
        assert p_bonf == pytest.approx(p_raw * n_cells, rel=1e-9)
        assert p_bonf < 1.0

    # Direct unit test of the helper: _bonferroni also clips at 1.0.
    assert _bonferroni(0.5, 4) == pytest.approx(1.0)  # 0.5 * 4 = 2 → 1
    assert _bonferroni(0.05, 4) == pytest.approx(0.2)
    assert _bonferroni(0.5, 0) == pytest.approx(0.5)  # n=0 → no scaling


# ---------------------------------------------------------------------------
# Test 3: underpowered verdict triggered when power < 0.5
# ---------------------------------------------------------------------------


def test_underpowered_verdict_when_power_below_threshold() -> None:
    """Small N → SE is large → small non-centrality → low power.

    With ``baseline=0.50, framework=0.511, n=30`` the Bernoulli SE
    of the proportion is ≈ 0.129 (i.e. much larger than the 1pp
    target). The non-centrality parameter ``ncp = 0.01 / 0.129 ≈
    0.078`` is far below the z_alpha = 1.96 threshold needed for
    50 % power, so the verdict must be UNDERPOWERED.
    """
    cells = [("m", "metric", 0.50, 0.511, 30)]
    df = compute_power_table(cells, alpha=0.05, min_effect_size_pp=1.0)
    row = df.iloc[0]
    power = float(row["power_to_detect_1pp"])
    assert math.isfinite(power)
    assert power < 0.5
    assert row["verdict"] == "UNDERPOWERED"

    # Contrast: same delta at very large N → SE shrinks → power > 0.5.
    # At N=100,000 the SE ≈ 0.00224, ncp ≈ 4.47 → power ≈ 1.0.
    df_hi = compute_power_table(
        [("m", "metric", 0.50, 0.511, 100_000)],
        alpha=0.05,
        min_effect_size_pp=1.0,
    )
    power_hi = float(df_hi.iloc[0]["power_to_detect_1pp"])
    assert power_hi > 0.5
    # And the verdict should NOT be UNDERPOWERED (could be TIE, SUPPORTED,
    # or NOT_SIGNIFICANT depending on the p-value — just not underpowered).
    assert df_hi.iloc[0]["verdict"] != "UNDERPOWERED"

    # Direct unit test of the power helper: matches Cohen 1988 §2.4
    # closed-form two-sided normal-approximation power.
    # At SE=0.1, effect=0.01, alpha=0.05 → ncp = 0.1, z_alpha = ppf(0.975).
    # power = sf(z_alpha - ncp) + cdf(-z_alpha - ncp).
    from scipy.stats import norm
    z_alpha = norm.ppf(0.975)
    expected_power = (
        norm.sf(z_alpha - 0.1) + norm.cdf(-z_alpha - 0.1)
    )
    assert _post_hoc_power(0.01, 0.1, 0.05) == pytest.approx(
        expected_power, rel=1e-9,
    )


# ---------------------------------------------------------------------------
# Test 4: SUPPORTED / TIE / REGRESSES verdict thresholds
# ---------------------------------------------------------------------------


def test_verdict_thresholds_supported_tie_regresses() -> None:
    """Cover the three primary verdict branches:

    * **SUPPORTED** — large positive delta, Bonferroni-corrected p < alpha
      after crossing the noise + power floors.
    * **TIE** — ``|delta| < min_effect_size_pp`` (1pp) regardless of power.
    * **REGRESSES** — large negative delta with Bonferroni p < alpha.

    Uses very large N (50,000) so the Bernoulli SE at p≈0.5 is
    ≈ 0.00224, giving ncp = 0.01 / 0.00224 ≈ 4.47 → power ≈ 1.0 at
    1pp, comfortably above the 0.5 threshold.
    """
    n = 50_000
    # 1. SUPPORTED: framework jumps from 0.50 to 0.55 (+5pp), N=50000.
    cells_supported = [("m", "supported", 0.50, 0.55, n)]
    df_s = compute_power_table(cells_supported, alpha=0.05)
    row_s = df_s.iloc[0]
    assert float(row_s["delta"]) > 0.0
    assert float(row_s["p_value_bonferroni"]) < 0.05
    assert float(row_s["power_to_detect_1pp"]) > 0.5
    assert row_s["verdict"] == "SUPPORTED"

    # 2. TIE: tiny delta (+0.3pp) — within the 1pp noise floor.
    cells_tie = [("m", "tie", 0.50, 0.503, n)]
    df_t = compute_power_table(cells_tie, alpha=0.05)
    row_t = df_t.iloc[0]
    assert abs(float(row_t["delta"])) * 100.0 < 1.0
    assert row_t["verdict"] == "TIE"

    # 3. REGRESSES: framework drops from 0.55 to 0.50 (-5pp).
    cells_regress = [("m", "regress", 0.55, 0.50, n)]
    df_r = compute_power_table(cells_regress, alpha=0.05)
    row_r = df_r.iloc[0]
    assert float(row_r["delta"]) < 0.0
    assert float(row_r["p_value_bonferroni"]) < 0.05
    assert float(row_r["power_to_detect_1pp"]) > 0.5
    assert row_r["verdict"] == "REGRESSES"

    # 4. Direct unit test of the verdict helper precedence.
    # TIE wins over SUPPORTED when delta is below the noise floor.
    assert _verdict(
        delta=0.0005,  # 0.05pp — below 1pp threshold
        p_bonferroni=0.001,
        power=1.0,
        alpha=0.05,
        min_effect_size_pp=1.0,
    ) == "TIE"

    # UNDERPOWERED wins over SUPPORTED when power < 0.5.
    assert _verdict(
        delta=0.05,  # 5pp — above noise floor
        p_bonferroni=0.001,
        power=0.3,
        alpha=0.05,
        min_effect_size_pp=1.0,
    ) == "UNDERPOWERED"

    # TIE wins over NOT_SIGNIFICANT when delta is below 1pp.
    assert _verdict(
        delta=0.005,  # 0.5pp — below 1pp threshold
        p_bonferroni=0.5,
        power=0.9,
        alpha=0.05,
        min_effect_size_pp=1.0,
    ) == "TIE"  # noise floor wins

    # Now exercise the actual NOT_SIGNIFICANT branch: delta above 1pp,
    # power above 0.5, p_bonf above alpha.
    assert _verdict(
        delta=0.02,  # 2pp — above 1pp threshold
        p_bonferroni=0.20,  # not significant
        power=0.9,  # high power
        alpha=0.05,
        min_effect_size_pp=1.0,
    ) == "NOT_SIGNIFICANT"


# ---------------------------------------------------------------------------
# Extra: helper smoke tests (not counted as one of the 4 mandated tests)
# ---------------------------------------------------------------------------


def test_per_arm_se_bernoulli_vs_cv_floor() -> None:
    """Bernoulli variance for proportions; CV floor for non-proportions.

    ``_per_arm_se`` must use ``p * (1 - p)`` when ``0 <= mean <= 1``
    and a 5 % coefficient-of-variation floor otherwise.
    """
    # Bernoulli: p=0.5 → var=0.25 → SE = sqrt(0.25/1000) ≈ 0.01581.
    assert _per_arm_se(0.5, 1000) == pytest.approx(math.sqrt(0.25 / 1000.0))
    # Bernoulli edge: p=0 → var=0 → SE=0.
    assert _per_arm_se(0.0, 100) == 0.0
    # Non-Bernoulli: mean=10 → var = (0.05 * 10)^2 = 0.25 → SE = sqrt(0.25/n).
    assert _per_arm_se(10.0, 100) == pytest.approx(math.sqrt(0.25 / 100.0))


def test_ci_95_uses_z_crit_constant() -> None:
    """95 % CI half-width = Z_CRIT_95 * SE."""
    lo, hi = _ci_95(0.0, 1.0)
    assert hi - lo == pytest.approx(2.0 * Z_CRIT_95, rel=1e-12)


def test_p_value_two_sided_degenerate_se() -> None:
    """p_value returns 1.0 when SE is 0 (cannot distinguish from 0)."""
    assert _p_value_two_sided(0.001, 0.0) == 1.0
    assert _p_value_two_sided(0.5, 0.0) == 1.0


def test_compute_power_table_empty_cells_returns_empty_dataframe() -> None:
    """Empty input → empty DataFrame with the documented column order."""
    df = compute_power_table([])
    assert df.empty
    assert list(df.columns) == [
        "model",
        "metric",
        "n",
        "baseline",
        "framework",
        "delta",
        "delta_se",
        "ci_95_lower",
        "ci_95_upper",
        "p_value_raw",
        "p_value_bonferroni",
        "power_to_detect_1pp",
        "verdict",
    ]
