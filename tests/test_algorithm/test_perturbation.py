"""Tests for the Wave 59 PerturbationPolicy split (Paper B BRAI).

Wave 59 §8 — interface-first constraint: the
:class:`adaptive_reflow.algorithm.perturbation.PerturbationPolicy`
must land before any new algorithm (MFPQA / BRAI) is wired into an
adapter. The tests below exercise:

* :class:`UniformFreshPerturbation` byte-stable legacy semantics
  (``x_perturbed = standard_normal(x.shape)`` with a deterministic
  seed).
* :class:`PaperQuantityAttractorInversion` direction = negative
  gradient (the BRAI value-add: the perturbation pushes the state
  AWAY from the paper-quantity attractor, not at random).
* Graceful fallback to uniform-fresh when ``paper_quantities`` is
  ``None`` (or missing ``e_rho`` accessor).
* Config round-trip (P1-1) and ``isinstance`` conformance with
  :class:`PerturbationPolicy`.

The tests do NOT touch any adapter — they live at the algorithm
layer so the contract is independent of the model-specific wiring.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.algorithm.perturbation import (
    BRAI_FALLBACK_FIELDS_MISSING,
    BRAI_GRAD_FALLBACK_TO_FD,
    BRAI_NO_PAPER_QUANTITIES,
    BRAI_NONFINITE_QUANTITY_COERCED,
    DEFAULT_BRAI_EPS_SCALE,
    DEFAULT_BRAI_GRAD_EPS,
    DEFAULT_BRAI_SIGMA,
    PaperQuantitiesPerturbationSnapshotProtocol,
    PaperQuantityAttractorInversion,
    PerturbationConfigError,
    PerturbationPolicy,
    UniformFreshPerturbation,
    build_perturbation_from_config,
    default_brai_perturbation,
    default_uniform_fresh_perturbation,
)


# ---------------------------------------------------------------------------
# Test 1 — UniformFreshPerturbation preserved (byte-stable legacy behaviour)
# ---------------------------------------------------------------------------


def test_uniform_fresh_preserved_default_seed_offset() -> None:
    """UniformFresh must reproduce ``standard_normal(x.shape)`` byte-for-byte.

    This is the **legacy semantics** the framework has shipped
    since Wave 0; per-adapter composite data, regression vectors,
    and pinned metrics across every adapter depend on the exact
    seed -> noise mapping being preserved bit-for-bit. Wave 47 /
    52 / 58 results MUST remain reproducible at default
    ``seed_offset = 0``.
    """
    policy = UniformFreshPerturbation()
    assert policy.seed_offset == 0
    assert policy.family == "uniform_fresh"

    x = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    x_perturbed = policy.propose(x, paper_quantities=None, t=0.0)
    # The fresh-noise path MUST NOT echo ``x``.
    assert x_perturbed.shape == x.shape
    assert x_perturbed.dtype == np.float64
    # With a deterministic seed the noise vector is the same on
    # every call — verify by re-running the proposal and checking
    # equality (the legacy Wave 47 / 52 / 58 byte-stability contract).
    x_perturbed_2 = policy.propose(x, paper_quantities=None, t=0.0)
    np.testing.assert_array_equal(x_perturbed, x_perturbed_2)
    # The policy MUST NOT mutate ``x_saturated``.
    np.testing.assert_array_equal(x, np.array([1.0, 2.0, 3.0], dtype=np.float64))


def test_uniform_fresh_different_t_produces_different_noise() -> None:
    """Different ``t`` MUST produce different noise (per-round variation)."""
    policy = UniformFreshPerturbation()
    x = np.zeros(4, dtype=np.float64)
    n_t0 = policy.propose(x, paper_quantities=None, t=0.0)
    n_t1 = policy.propose(x, paper_quantities=None, t=1.0)
    assert not np.allclose(n_t0, n_t1)


def test_uniform_fresh_isinstance_conformance() -> None:
    """UniformFresh MUST pass ``isinstance(policy, PerturbationPolicy)``."""
    policy = default_uniform_fresh_perturbation()
    assert isinstance(policy, PerturbationPolicy)


def test_uniform_fresh_ignores_paper_quantities() -> None:
    """UniformFresh ignores ``paper_quantities`` (legacy semantics)."""

    class _Snapshot(PaperQuantitiesPerturbationSnapshotProtocol):
        def e_rho(self, t: float) -> float:  # pragma: no cover
            return 999.0

        def log_p_qty(self, x, t: float) -> float:  # pragma: no cover
            return -999.0

    policy = UniformFreshPerturbation()
    x = np.array([1.0], dtype=np.float64)
    x_none = policy.propose(x, paper_quantities=None, t=0.0)
    x_snap = policy.propose(x, paper_quantities=_Snapshot(), t=0.0)
    np.testing.assert_array_equal(x_none, x_snap)


def test_uniform_fresh_validates_seed_offset() -> None:
    """UniformFresh rejects negative or non-integer ``seed_offset``."""
    with pytest.raises(PerturbationConfigError):
        UniformFreshPerturbation(seed_offset=-1)
    with pytest.raises(PerturbationConfigError):
        UniformFreshPerturbation(seed_offset=1.5)  # type: ignore[arg-type]
    with pytest.raises(PerturbationConfigError):
        UniformFreshPerturbation(seed_offset="0")  # type: ignore[arg-type]


def test_uniform_fresh_config_round_trip() -> None:
    """UniformFresh ``from_config(to_config())`` round-trips bit-for-bit."""
    original = UniformFreshPerturbation(seed_offset=7)
    config = original.to_config()
    assert config["family"] == "uniform_fresh"
    assert config["seed_offset"] == 7
    rebuilt = UniformFreshPerturbation.from_config(config)
    assert rebuilt.seed_offset == original.seed_offset
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.to_config() == config


def test_uniform_fresh_config_hash_distinguishes_seed_offset() -> None:
    """Two UniformFresh instances with different offsets MUST hash differently."""
    a = UniformFreshPerturbation(seed_offset=0)
    b = UniformFreshPerturbation(seed_offset=1)
    assert a.config_hash() != b.config_hash()


# ---------------------------------------------------------------------------
# Test 2 — PaperQuantityAttractorInversion inverts the prior (BRAI)
# ---------------------------------------------------------------------------


def test_brai_inverts_prior_direction() -> None:
    """BRAI direction = ``-grad(log P_qty)`` (push AWAY from attractor).

    We use the analytic Gaussian prior
    ``log P_qty(x) = -||x||^2 / (2 * sigma^2)`` so the gradient is
    ``-x / sigma^2`` and the BRAI push direction is
    ``-grad = x / sigma^2`` (i.e. *radially outward* from the
    origin — the canonical "invert the attractor" behaviour).

    Verification: with ``eps_scale > 0``, the perturbed state
    MUST have a strictly larger L2 norm than the saturated state
    (for any non-zero ``x_saturated``).
    """
    sigma = 2.0
    eps_scale = 0.3
    brai = PaperQuantityAttractorInversion(
        eps_scale=eps_scale,
        default_sigma=sigma,
    )

    # Saturated state at radius 1.0 from the origin.
    x_sat = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    pq = {"e_rho": float(sigma)}

    audit: list[str] = []
    x_perturbed = brai.propose(
        x_sat, paper_quantities=pq, t=0.0, audit_codes=audit
    )

    # Expected: x + eps_scale * (-grad) = x + eps_scale * (x / sigma^2)
    #         = x * (1 + eps_scale / sigma^2)
    expected_factor = 1.0 + eps_scale / (sigma ** 2)
    np.testing.assert_allclose(
        x_perturbed, expected_factor * x_sat, atol=1e-12
    )

    # Direction check: the L2 norm MUST grow (push outward).
    assert float(np.linalg.norm(x_perturbed)) > float(np.linalg.norm(x_sat))
    # Direction along the x-axis MUST be positive (push in +x).
    assert x_perturbed[0] > x_sat[0]
    # The y, z components MUST stay zero (radially symmetric push).
    assert abs(x_perturbed[1]) < 1e-12
    assert abs(x_perturbed[2]) < 1e-12


def test_brai_inverts_prior_with_analytic_gradient_callable() -> None:
    """BRAI consumes a user-supplied analytic ``grad_log_p_qty`` when present.

    When the analytic gradient is supplied, BRAI MUST skip the
    finite-difference fallback (audit code
    :data:`BRAI_GRAD_FALLBACK_TO_FD` MUST NOT be emitted).
    """

    def grad_log_p_qty(x, t, e_rho):
        # ``grad log P_qty = -2 x`` (a custom analytic gradient
        # distinct from the default Gaussian prior).
        return -2.0 * np.asarray(x, dtype=np.float64)

    brai = PaperQuantityAttractorInversion(
        eps_scale=0.1,
        grad_log_p_qty=grad_log_p_qty,
        default_sigma=1.0,
    )

    x_sat = np.array([1.0, 1.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    audit: list[str] = []
    x_perturbed = brai.propose(
        x_sat, paper_quantities=pq, t=0.0, audit_codes=audit
    )
    # Expected: x + eps_scale * (-grad) = x + 0.1 * 2x = 1.2 x.
    np.testing.assert_allclose(x_perturbed, 1.2 * x_sat, atol=1e-12)
    # Analytic gradient was supplied -> finite-difference fallback
    # MUST NOT have fired.
    assert BRAI_GRAD_FALLBACK_TO_FD not in audit


def test_brai_finite_difference_when_only_log_p_qty_supplied() -> None:
    """BRAI falls back to finite-difference on ``log_p_qty``.

    When ``grad_log_p_qty`` is ``None`` but ``log_p_qty`` is
    supplied, BRAI MUST emit :data:`BRAI_GRAD_FALLBACK_TO_FD` and
    compute the gradient via central finite differences.
    """

    def log_p_qty(x, t):
        # ``log P_qty = -||x||^2 / 2`` so ``grad log P_qty = -x``.
        arr = np.asarray(x, dtype=np.float64)
        return -0.5 * float(np.sum(arr * arr))

    brai = PaperQuantityAttractorInversion(
        eps_scale=0.1,
        log_p_qty=log_p_qty,
        default_sigma=1.0,
    )

    x_sat = np.array([1.0, 2.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    audit: list[str] = []
    x_perturbed = brai.propose(
        x_sat, paper_quantities=pq, t=0.0, audit_codes=audit
    )
    # Expected: x + 0.1 * (-grad) = x + 0.1 * x = 1.1 x.
    np.testing.assert_allclose(x_perturbed, 1.1 * x_sat, atol=1e-4)
    # Finite-difference fallback MUST have fired.
    assert BRAI_GRAD_FALLBACK_TO_FD in audit


def test_brai_finite_difference_gradient_accuracy() -> None:
    """Finite-difference gradient accuracy matches analytic within ``O(eps^2)``.

    With ``grad_eps = 1e-3`` the central-difference error is
    ``O(eps^2) ~ 1e-6`` — much smaller than the BRAI push
    magnitude ``eps_scale = 0.1``. The test verifies the FD
    gradient is within ``1e-4`` of the analytic.
    """

    def log_p_qty(x, t):
        # ``log P_qty = -||x||^2 / 2`` so ``grad log P_qty = -x``.
        arr = np.asarray(x, dtype=np.float64)
        return -0.5 * float(np.sum(arr * arr))

    brai = PaperQuantityAttractorInversion(
        eps_scale=0.1,
        log_p_qty=log_p_qty,
        grad_eps=DEFAULT_BRAI_GRAD_EPS,
    )

    x_sat = np.array([3.0, -2.0, 4.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    audit: list[str] = []
    x_perturbed = brai.propose(
        x_sat, paper_quantities=pq, t=0.0, audit_codes=audit
    )
    # Analytic: x + 0.1 * (-grad) = x + 0.1 * x = 1.1 x.
    np.testing.assert_allclose(x_perturbed, 1.1 * x_sat, atol=1e-4)


def test_brai_does_not_mutate_x_saturated() -> None:
    """BRAI ``propose`` MUST NOT mutate ``x_saturated`` (fresh allocation)."""
    brai = PaperQuantityAttractorInversion()
    x_sat = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    x_before = x_sat.copy()
    pq = {"e_rho": 1.0}
    brai.propose(x_sat, paper_quantities=pq, t=0.5)
    np.testing.assert_array_equal(x_sat, x_before)


def test_brai_default_coefficients_match_design_doc() -> None:
    """BRAI defaults match ``todo/two-paper-algo-design.md`` §4.1.

    Canonical defaults::

        eps_scale = 0.1, grad_eps = 1e-3, default_sigma = 1.0
    """
    brai = default_brai_perturbation()
    assert brai.eps_scale == pytest.approx(DEFAULT_BRAI_EPS_SCALE)
    assert brai.eps_scale == pytest.approx(0.1)
    assert brai.grad_eps == pytest.approx(DEFAULT_BRAI_GRAD_EPS)
    assert brai.grad_eps == pytest.approx(1e-3)
    assert brai.default_sigma == pytest.approx(DEFAULT_BRAI_SIGMA)
    assert brai.default_sigma == pytest.approx(1.0)
    assert brai.family == "brai"
    assert brai.has_log_p_qty is False
    assert brai.has_grad_log_p_qty is False


def test_brai_isinstance_conformance() -> None:
    """PaperQuantityAttractorInversion passes ``isinstance`` check."""
    brai = default_brai_perturbation()
    assert isinstance(brai, PerturbationPolicy)


# ---------------------------------------------------------------------------
# Test 3 — Graceful fallback when paper_quantities is missing / partial
# ---------------------------------------------------------------------------


def test_brai_fallback_no_paper_quantities() -> None:
    """BRAI falls back to uniform-fresh when ``paper_quantities is None``."""
    brai = PaperQuantityAttractorInversion()
    x = np.array([0.0, 0.0], dtype=np.float64)
    audit: list[str] = []
    x_perturbed = brai.propose(
        x, paper_quantities=None, t=0.0, audit_codes=audit
    )
    # Uniform-fresh path MUST produce standard_normal noise — not
    # the deterministic zeros from a no-op gradient.
    assert x_perturbed.shape == x.shape
    assert x_perturbed.dtype == np.float64
    # The fresh-noise MUST NOT be the deterministic zeros (a
    # no-op perturbation would yield ``x_perturbed == 0`` which is
    # not what uniform-fresh produces).
    assert not np.allclose(x_perturbed, np.zeros_like(x))
    # The audit code MUST be emitted.
    assert BRAI_NO_PAPER_QUANTITIES in audit


def test_brai_fallback_missing_e_rho_field() -> None:
    """BRAI falls back to uniform-fresh when ``e_rho`` is absent from snapshot."""
    brai = PaperQuantityAttractorInversion()
    x = np.zeros(2, dtype=np.float64)
    audit: list[str] = []
    # Snapshot lacks ``e_rho`` accessor (only has ``sheet_A``).
    x_perturbed = brai.propose(
        x, paper_quantities={"sheet_A": 1.0}, t=0.0, audit_codes=audit
    )
    assert x_perturbed.shape == x.shape
    # Uniform-fresh path produces noise; not the deterministic
    # zero perturbation that a missing-``e_rho`` gradient would.
    assert not np.allclose(x_perturbed, np.zeros_like(x))
    assert BRAI_FALLBACK_FIELDS_MISSING in audit


def test_brai_fallback_silent_when_audit_codes_none() -> None:
    """BRAI silently falls back to uniform-fresh when ``audit_codes=None``."""
    brai = PaperQuantityAttractorInversion()
    x = np.zeros(2, dtype=np.float64)
    x_perturbed = brai.propose(x, paper_quantities=None, t=0.0)
    assert x_perturbed.shape == x.shape


def test_brai_coerces_nonfinite_e_rho() -> None:
    """Non-finite ``e_rho`` is coerced to ``default_sigma`` and audited."""
    brai = PaperQuantityAttractorInversion(default_sigma=2.0)
    x = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    pq = {"e_rho": float("nan")}
    audit: list[str] = []
    x_perturbed = brai.propose(
        x, paper_quantities=pq, t=0.0, audit_codes=audit
    )
    # Non-finite e_rho -> default_sigma=2.0; grad = -x/sigma^2;
    # -grad = x/sigma^2 = x/4; x_perturbed = x + 0.1 * x/4
    # = x * 1.025.
    expected_factor = 1.0 + 0.1 / (2.0 ** 2)
    np.testing.assert_allclose(x_perturbed, expected_factor * x, atol=1e-12)
    assert BRAI_NONFINITE_QUANTITY_COERCED in audit


def test_brai_validates_eps_scale() -> None:
    """BRAI rejects non-positive ``eps_scale``."""
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(eps_scale=0.0)
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(eps_scale=-0.01)
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(eps_scale=float("nan"))


def test_brai_validates_grad_eps() -> None:
    """BRAI rejects non-positive ``grad_eps``."""
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(grad_eps=0.0)
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(grad_eps=-1e-3)
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(grad_eps=float("inf"))


def test_brai_validates_default_sigma() -> None:
    """BRAI rejects non-positive ``default_sigma``."""
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(default_sigma=0.0)
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(default_sigma=-1.0)


# ---------------------------------------------------------------------------
# Test 4 — Config round-trip + polymorphic factory
# ---------------------------------------------------------------------------


def test_brai_config_round_trip() -> None:
    """BRAI ``from_config(to_config())`` round-trips bit-for-bit (callables lost)."""
    original = PaperQuantityAttractorInversion(
        eps_scale=0.05, grad_eps=2e-3, default_sigma=1.5
    )
    config = original.to_config()
    assert config["family"] == "brai"
    assert config["eps_scale"] == pytest.approx(0.05)
    assert config["grad_eps"] == pytest.approx(2e-3)
    assert config["default_sigma"] == pytest.approx(1.5)
    rebuilt = PaperQuantityAttractorInversion.from_config(config)
    assert rebuilt.eps_scale == original.eps_scale
    assert rebuilt.grad_eps == original.grad_eps
    assert rebuilt.default_sigma == original.default_sigma
    assert rebuilt.config_hash() == original.config_hash()
    assert rebuilt.to_config() == config


def test_brai_config_hash_distinguishes_coefficients() -> None:
    """Two BRAI instances with different coefficients MUST hash differently."""
    a = PaperQuantityAttractorInversion(eps_scale=0.1)
    b = PaperQuantityAttractorInversion(eps_scale=0.2)
    c = PaperQuantityAttractorInversion(eps_scale=0.1, grad_eps=1e-4)
    assert a.config_hash() != b.config_hash()
    assert a.config_hash() != c.config_hash()
    assert b.config_hash() != c.config_hash()


def test_build_perturbation_from_config_uniform_fresh() -> None:
    """build_perturbation_from_config dispatches ``"uniform_fresh"``."""
    policy = build_perturbation_from_config(
        {"family": "uniform_fresh", "seed_offset": 3}
    )
    assert isinstance(policy, UniformFreshPerturbation)
    assert isinstance(policy, PerturbationPolicy)
    assert policy.seed_offset == 3


def test_build_perturbation_from_config_brai() -> None:
    """build_perturbation_from_config dispatches ``"brai"``."""
    policy = build_perturbation_from_config(
        {
            "family": "brai",
            "eps_scale": 0.07,
            "grad_eps": 5e-3,
            "default_sigma": 2.5,
        }
    )
    assert isinstance(policy, PaperQuantityAttractorInversion)
    assert isinstance(policy, PerturbationPolicy)
    assert policy.eps_scale == pytest.approx(0.07)
    assert policy.grad_eps == pytest.approx(5e-3)
    assert policy.default_sigma == pytest.approx(2.5)


def test_build_perturbation_from_config_rejects_unknown_family() -> None:
    """build_perturbation_from_config rejects unknown family names."""
    with pytest.raises(PerturbationConfigError):
        build_perturbation_from_config({"family": "random_walk"})


def test_build_perturbation_from_config_rejects_non_dict() -> None:
    """build_perturbation_from_config rejects non-dict config."""
    with pytest.raises(PerturbationConfigError):
        build_perturbation_from_config("uniform_fresh")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 5 — Math properties (sanity checks beyond the spec)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "radius", [0.5, 1.0, 2.0, 5.0, 10.0]
)
def test_brai_radial_push_outward_for_gaussian_prior(
    radius: float,
) -> None:
    """For the default Gaussian prior, BRAI pushes radially OUTWARD.

    The push magnitude is ``eps_scale * radius / sigma^2`` along
    each axis, so the L2 norm strictly grows for any non-zero
    ``x_saturated``.
    """
    brai = PaperQuantityAttractorInversion(
        eps_scale=0.1, default_sigma=1.0
    )
    # Saturated state at the given radius along the x-axis.
    x_sat = np.array([radius, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    x_perturbed = brai.propose(x_sat, paper_quantities=pq, t=0.0)
    # Push along the x-axis MUST be positive (radially outward).
    assert x_perturbed[0] > x_sat[0]
    # y-axis MUST stay zero (radially symmetric push).
    assert abs(x_perturbed[1]) < 1e-12
    # L2 norm MUST grow.
    assert float(np.linalg.norm(x_perturbed)) > float(np.linalg.norm(x_sat))


@pytest.mark.parametrize(
    "sat_value", [0.5, -1.0, 2.5, -3.0]
)
def test_brai_preserves_direction_for_scalar_saturation(
    sat_value: float,
) -> None:
    """For scalar ``x_saturated``, the BRAI push direction matches ``x_saturated``.

    With the Gaussian prior, the BRAI push direction
    ``-grad = x / sigma^2`` is always aligned with ``x_saturated``,
    so the perturbation ``x_perturbed = x + eps * (-grad)`` must
    move the state AWAY from the origin in the same direction as
    ``x_saturated``.
    """
    brai = PaperQuantityAttractorInversion(
        eps_scale=0.1, default_sigma=1.0
    )
    x_sat = np.array([sat_value], dtype=np.float64)
    pq = {"e_rho": 1.0}
    x_perturbed = brai.propose(x_sat, paper_quantities=pq, t=0.0)
    # Sign of the perturbation MUST match the sign of x_sat
    # (radially outward push).
    assert (x_perturbed[0] - x_sat[0]) * sat_value > 0.0
    # Magnitude MUST grow.
    assert abs(x_perturbed[0]) > abs(x_sat[0])


def test_uniform_fresh_step_does_not_mutate_x() -> None:
    """UniformFresh ``propose`` MUST NOT mutate ``x_saturated``."""
    policy = UniformFreshPerturbation()
    x = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    x_before = x.copy()
    policy.propose(x, paper_quantities=None, t=0.5)
    np.testing.assert_array_equal(x, x_before)


def test_brai_handles_method_shaped_snapshot() -> None:
    """BRAI reads ``e_rho(t)`` when the snapshot exposes a callable accessor."""

    class _CallableSnapshot(PaperQuantitiesPerturbationSnapshotProtocol):
        def __init__(self, e_rho: float) -> None:
            self._e_rho = e_rho

        def e_rho(self, t: float) -> float:
            return self._e_rho

        def log_p_qty(self, x, t: float) -> float:  # pragma: no cover
            return 0.0

    brai = PaperQuantityAttractorInversion(eps_scale=0.1)
    x = np.array([1.0, 0.0], dtype=np.float64)
    snap = _CallableSnapshot(e_rho=2.0)
    audit: list[str] = []
    x_perturbed = brai.propose(
        x, paper_quantities=snap, t=0.0, audit_codes=audit
    )
    # e_rho=2 -> sigma=2 -> push = 0.1 * x / 4 = 0.025 x.
    expected_factor = 1.0 + 0.025
    np.testing.assert_allclose(x_perturbed, expected_factor * x, atol=1e-12)
    # No fallback codes emitted (snapshot is fully shaped).
    assert BRAI_NO_PAPER_QUANTITIES not in audit
    assert BRAI_FALLBACK_FIELDS_MISSING not in audit


def test_uniform_fresh_output_is_standard_normal_shaped() -> None:
    """UniformFresh output has the same shape as ``x_saturated``.

    Sanity check: the policy MUST NOT reshape the output (a
    bug in the seed-derivation could silently change the shape
    when ``x.shape`` has unusual entries).
    """
    policy = UniformFreshPerturbation()
    for shape in [(2,), (3, 4), (2, 2, 2)]:
        x = np.zeros(shape, dtype=np.float64)
        x_perturbed = policy.propose(x, paper_quantities=None, t=0.0)
        assert x_perturbed.shape == shape
        assert x_perturbed.dtype == np.float64


def test_brai_eps_scale_zero_is_rejected_but_tiny_is_accepted() -> None:
    """``eps_scale`` boundary: 0 is rejected, ``1e-12`` is accepted.

    ``eps_scale = 0`` would freeze the trajectory (no
    perturbation ever). The constructor rejects it; a tiny but
    positive value is accepted.
    """
    with pytest.raises(PerturbationConfigError):
        PaperQuantityAttractorInversion(eps_scale=0.0)
    # Tiny positive eps_scale is accepted.
    brai = PaperQuantityAttractorInversion(eps_scale=1e-12)
    x = np.array([1.0, 0.0], dtype=np.float64)
    pq = {"e_rho": 1.0}
    x_perturbed = brai.propose(x, paper_quantities=pq, t=0.0)
    # The push is tiny but the policy MUST NOT crash.
    assert math.isfinite(x_perturbed[0])
