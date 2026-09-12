"""Tests for the parameter-free DerivationRule framework (DERIV-001).

This test module verifies the minimal proof that the
Hyperparameter-Freeness Principle can be instantiated on a
single component — the canonical restart blend's
``memory_fraction``. The principle states that every framework
hyperparameter SHOULD trace to a paper quantity (A_g / B_g /
C_g / e_rho) or a mathematical theory (Lipschitz,
variance-preserving, OT, BL convergence, Fisher / Polyak /
information geometry); hand-set engineering constants stay as
named provenance.

The test groups follow the design:

(1) **DerivationRule abstract protocol** — verify the protocol
    signature, provenance class-level attributes, and
    runtime-checkable behavior.
(2) **PolyakMemoryFraction closed-form** — verify the derivation
    matches analytical ground truth on synthetic W2 inputs.
(3) **PolyakMemoryFraction fallback** — verify the ADR-0010
    cosine-driven fallback when the derivation context is
    missing the W2 inputs.
(4) **default_memory_fraction dispatcher** — verify the helper
    routes correctly between derivation and fallback.
(5) **derive_default_memory_fraction backward-compat** — verify
    blender_extra.derive_default_memory_fraction preserves the
    existing wiring when called without a context.
(6) **DAG / namespace isolation** — verify the protocol raises
    on cyclic derivation attempts and refuses to share
    namespaces across Fisher-on-posterior vs Fisher-on-model.
(7) **Provenance / docs cross-check** — verify each concrete
    rule carries non-empty derivation_formula + academic
    precedent attributes.

The tests follow ADR-0001 (stdlib-only). NumPy/scipy are
permitted inside ``adaptive_reflow/algorithm/_derivation.py`` if
a future derivation requires them; the tests here stay on
stdlib + math only.
"""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from adaptive_reflow.algorithm._derivation import (
    BLConvergenceEpsilonSchedule,
    BoundaryConditionRule,
    BoundedMergeFloorRule,
    ConvergenceAdaptivePolyRule,
    DEFAULT_EPSILON_SCHEDULE_FALLBACK,
    DEFAULT_LIPSCHITZ_STEP_FALLBACK,
    DEFAULT_MEMORY_FRACTION_FALLBACK,
    DerivationContext,
    DerivationCycleError,
    DerivationRule,
    EMAInverseVarianceRule,
    EpsLogRule,
    ExponentialAlphaRule,
    FisherMemoryFraction,
    LipschitzStepSize,
    LipschitzTemperatureRule,
    MachineEpsilonRule,
    MeanFlowFixedStrengthRule,
    MeanFlowToleranceRule,
    MetricWeightRule,
    MidpointBetaRule,
    MinGumbelTempRule,
    NAMESPACE_ALGORITHM_POSTERIOR,
    OTEpsilonSchedule,
    PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR,
    PolyakMemoryFraction,
    PolynomialPowerRule,
    SigmoidMidpointSteepnessRule,
    VariancePreservingJitterRule,
    default_alpha_grad,
    default_constant_beta,
    default_convergence_adaptive_ema,
    default_convergence_adaptive_kd,
    default_convergence_adaptive_kp,
    default_convergence_adaptive_shift_max,
    default_ema_alpha,
    default_eps_implicit,
    default_eps_log,
    default_exponential_alpha,
    default_handoff_window,
    default_jitter_std,
    default_lipschitz_step,
    default_machine_eps,
    default_memory_fraction,
    default_metric_weights,
    default_min_gumbel_temp,
    default_polynomial_power,
    default_sigmoid_midpoint,
    default_sigmoid_steepness,
    default_tolerance,
    default_distance_decay_temperature,
    make_derivation_context,
)
from adaptive_reflow.algorithm.blender_extra import (
    derive_default_memory_fraction,
)


# ---------------------------------------------------------------------------
# (1) DerivationRule abstract protocol
# ---------------------------------------------------------------------------


def test_derivation_rule_is_runtime_checkable_protocol() -> None:
    """DerivationRule is a ``runtime_checkable`` Protocol.

    The protocol contract requires concrete subclasses to
    expose ``derive``, ``derivation_source``,
    ``derivation_formula``, and ``academic_precedent``. Any
    object satisfying that surface should be accepted by
    ``isinstance(obj, DerivationRule)``.
    """
    rule = PolyakMemoryFraction()
    assert isinstance(rule, DerivationRule)


def test_derivation_rule_class_level_provenance() -> None:
    """Provenance attributes are non-empty strings on the class.

    The docs verifier (see ``tools/check_docs_against_code.py``)
    greps every ``derivation_source`` / ``derivation_formula`` /
    ``academic_precedent`` triple; empty provenance would make
    the rule unauditable.
    """
    rule_cls = PolyakMemoryFraction
    assert isinstance(rule_cls.derivation_source, str)
    assert rule_cls.derivation_source
    assert isinstance(rule_cls.derivation_formula, str)
    assert rule_cls.derivation_formula
    assert isinstance(rule_cls.academic_precedent, tuple)
    assert len(rule_cls.academic_precedent) >= 1
    for entry in rule_cls.academic_precedent:
        assert isinstance(entry, str)
        assert entry  # non-empty


def test_derivation_rule_required_fields_declared() -> None:
    """Required context fields are declared and non-empty.

    The dispatcher (``default_memory_fraction``) uses
    ``required_fields`` to decide whether to attempt the
    derivation or fall back. Empty ``required_fields`` would
    silently accept a partial context and produce nonsense.
    """
    rule_cls = PolyakMemoryFraction
    assert isinstance(rule_cls.required_fields, tuple)
    assert len(rule_cls.required_fields) >= 1
    for entry in rule_cls.required_fields:
        assert isinstance(entry, str)
        assert entry  # non-empty
        # namespace-qualified, e.g. "ot_metrics.W2_round_t"
        assert "." in entry


# ---------------------------------------------------------------------------
# (2) PolyakMemoryFraction closed-form against synthetic ground truth
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("w2_t", "w2_0", "n_cap", "expected"),
    [
        # Round 0 baseline equal to current: m = 0.5 (boundary).
        (1.0, 1.0, 0.5, 0.5),
        # Round t sharper than round 0: m < 0.5 (memory fades).
        (0.25, 1.0, 0.5, 0.25 / 1.25),
        # Round t broader than round 0: m > 0.5 (memory dominates).
        (3.0, 1.0, 0.5, 3.0 / 4.0),
        # Both zero: no measurement, m = 0 (cold start).
        (0.0, 0.0, 0.5, 0.0),
        # Baseline zero, current positive: m = 1 (informative fresh).
        (0.7, 0.0, 0.5, 1.0),
    ],
)
def test_polyak_memory_fraction_closed_form(
    w2_t: float, w2_0: float, n_cap: float, expected: float
) -> None:
    """The derivation matches the analytical closed form.

    For ``W2_round_0 > 0``:
        m_t := W2_round_t / (W2_round_0 + W2_round_t)

    For ``W2_round_0 == 0``:
        m_t = 1 if W2_round_t > 0 else 0
    """
    ctx = make_derivation_context(
        n_cap=n_cap, w2_round_t=w2_t, w2_round_0=w2_0
    )
    rule = PolyakMemoryFraction()
    assert rule(ctx) == pytest.approx(expected, abs=1e-12)


def test_polyak_memory_fraction_is_deterministic() -> None:
    """Repeated calls with the same context return the same value.

    Determinism is the contract for ``memory_fraction``:
    identical inputs must yield identical outputs so the audit
    ledger can replay a run byte-for-byte.
    """
    ctx = make_derivation_context(
        n_cap=0.5, w2_round_t=0.3, w2_round_0=0.7
    )
    rule = PolyakMemoryFraction()
    first = rule(ctx)
    second = rule(ctx)
    third = rule(ctx)
    assert first == second == third


def test_polyak_memory_fraction_is_pure_function_of_context() -> None:
    """The derivation does not mutate the supplied context.

    The framework rule is that ``DerivationRule.derive(ctx)``
    is a pure function of ``ctx``: it reads fields and returns
    a float. Mutating ``ctx`` would break the audit ledger.
    """
    ctx = make_derivation_context(
        n_cap=0.4, w2_round_t=0.6, w2_round_0=0.4
    )
    snapshot = (
        dict(ctx.ot_metrics),
        dict(ctx.scheduler_state),
        dict(ctx.paper_quantities),
        dict(ctx.local_curvature),
    )
    rule = PolyakMemoryFraction()
    _ = rule(ctx)
    assert ctx.ot_metrics == snapshot[0]
    assert ctx.scheduler_state == snapshot[1]
    assert ctx.paper_quantities == snapshot[2]
    assert ctx.local_curvature == snapshot[3]


# ---------------------------------------------------------------------------
# (3) PolyakMemoryFraction fallback (ADR-0010)
# ---------------------------------------------------------------------------


def test_polyak_memory_fraction_falls_back_when_w2_missing() -> None:
    """Missing W2 inputs return ``1 - n_cap`` (ADR-0010).

    The dispatcher's job is to keep existing callers green: when
    the context does not carry W2 measurements, the returned
    value is the documented ADR-0010 cosine-driven fallback.
    """
    ctx = make_derivation_context(n_cap=0.3)  # no W2 fields
    rule = PolyakMemoryFraction()
    assert rule(ctx) == pytest.approx(0.7, abs=1e-12)


def test_polyak_memory_fraction_falls_back_when_only_one_w2_present() -> (
    None
):
    """A partial W2 context also falls back (defensive).

    The closed form requires both ``W2_round_t`` AND
    ``W2_round_0``. If only one is supplied, the dispatcher
    returns the fallback rather than dividing by zero or
    producing a misleading ratio.
    """
    ctx_only_t = make_derivation_context(n_cap=0.4, w2_round_t=0.2)
    ctx_only_0 = make_derivation_context(n_cap=0.4, w2_round_0=0.5)
    rule = PolyakMemoryFraction()
    assert rule(ctx_only_t) == pytest.approx(0.6, abs=1e-12)
    assert rule(ctx_only_0) == pytest.approx(0.6, abs=1e-12)


def test_polyak_memory_fraction_falls_back_when_n_cap_missing() -> None:
    """Missing ``n_cap_t`` and missing W2 falls back to mid-cycle.

    When neither the OT metrics nor ``n_cap_t`` are populated,
    the derivation returns the documented mid-cycle anchor of
    0.5 (the symmetric envelope center per ADR-0010). This is
    the canonical "first round, no measurement yet" case.
    """
    ctx = make_derivation_context()  # everything None
    rule = PolyakMemoryFraction()
    assert rule(ctx) == pytest.approx(0.5, abs=1e-12)


# ---------------------------------------------------------------------------
# (4) default_memory_fraction dispatcher
# ---------------------------------------------------------------------------


def test_default_memory_fraction_with_none_context_uses_fallback() -> None:
    """``None`` context returns ADR-0010 cosine-driven fallback.

    The dispatcher is the canonical entry point used by the
    engine. When the engine does not supply a context (legacy
    callers), the returned value must match ADR-0010 verbatim.
    """
    assert default_memory_fraction(None, n_cap=0.4) == pytest.approx(
        0.6, abs=1e-12
    )
    assert default_memory_fraction(None, n_cap=None) == pytest.approx(
        0.5, abs=1e-12
    )


def test_default_memory_fraction_with_full_context_derives() -> None:
    """A complete context triggers the derivation.

    When both W2 fields and ``n_cap_t`` are populated, the
    dispatcher routes through the :class:`PolyakMemoryFraction`
    rule. The returned value matches the closed-form ratio
    (NOT the ADR-0010 fallback).
    """
    ctx = make_derivation_context(
        n_cap=0.5, w2_round_t=0.25, w2_round_0=1.0
    )
    assert default_memory_fraction(ctx) == pytest.approx(
        0.25 / 1.25, abs=1e-12
    )


def test_default_memory_fraction_promotes_n_cap_into_context() -> None:
    """``n_cap`` kwarg is folded into the context if missing.

    The dispatcher accepts ``n_cap`` as a separate kwarg so
    callers that already know the schedule value do not need
    to build the context from scratch. The promotion is
    additive: the caller's context is not mutated.
    """
    ctx = make_derivation_context(
        w2_round_t=0.25, w2_round_0=1.0
    )  # no n_cap_t
    assert ctx.scheduler_state.get("n_cap_t") is None
    # The dispatcher must still produce a valid value because
    # both W2 inputs are present. n_cap is irrelevant for the
    # closed form (it is only used by the fallback).
    value = default_memory_fraction(ctx, n_cap=0.99)
    assert value == pytest.approx(0.25 / 1.25, abs=1e-12)
    # The caller's context was NOT mutated.
    assert ctx.scheduler_state.get("n_cap_t") is None


def test_default_memory_fraction_handles_invalid_w2_inputs() -> None:
    """Invalid W2 inputs trigger the fallback rather than raising.

    The dispatcher catches :class:`ValueError` from the rule
    (raised on negative or non-finite W2) and returns the
    ADR-0010 fallback. This keeps the engine robust against
    buggy metric estimators without compromising audit.
    """
    ctx = make_derivation_context(
        n_cap=0.3, w2_round_t=-1.0, w2_round_0=1.0
    )
    assert default_memory_fraction(ctx) == pytest.approx(0.7, abs=1e-12)


def test_default_memory_fraction_clips_into_unit_interval() -> None:
    """Derived values are clipped into ``[0, 1]``.

    The closed-form ratio ``W2_t / (W2_0 + W2_t)`` is
    mathematically in ``[0, 1]`` when both W2 values are
    non-negative, but defensive clipping prevents a downstream
    bug in the W2 estimator from corrupting the blend.

    Pathological W2 inputs (negative baseline) make the rule
    raise :class:`ValueError`. The dispatcher catches that and
    falls back to ADR-0010 ``1 - n_cap``. The boundary case
    ``W2_round_0 == 0`` is handled directly by the rule.
    """
    # Negative baseline: rule raises ValueError, dispatcher falls back.
    ctx = make_derivation_context(
        n_cap=0.5, w2_round_t=1.0, w2_round_0=-0.5
    )
    assert default_memory_fraction(ctx) == pytest.approx(0.5, abs=1e-12)
    # When baseline is zero and t > 0, m = 1 (boundary, no fallback).
    ctx_zero = make_derivation_context(
        n_cap=0.5, w2_round_t=2.0, w2_round_0=0.0
    )
    assert default_memory_fraction(ctx_zero) == pytest.approx(
        1.0, abs=1e-12
    )


# ---------------------------------------------------------------------------
# (5) derive_default_memory_fraction (blender_extra entry point)
# ---------------------------------------------------------------------------


def test_blender_extra_derive_default_memory_fraction_fallback() -> None:
    """The blender_extra entry point preserves ADR-0010 on None context."""
    assert derive_default_memory_fraction(n_cap=0.4) == pytest.approx(
        0.6, abs=1e-12
    )
    assert derive_default_memory_fraction(n_cap=None) == pytest.approx(
        0.5, abs=1e-12
    )
    assert derive_default_memory_fraction() == pytest.approx(0.5, abs=1e-12)


def test_blender_extra_derive_default_memory_fraction_uses_rule() -> None:
    """The blender_extra entry point routes through PolyakMemoryFraction."""
    ctx = make_derivation_context(
        n_cap=0.5, w2_round_t=0.4, w2_round_0=0.6
    )
    expected = 0.4 / (0.6 + 0.4)
    assert derive_default_memory_fraction(context=ctx) == pytest.approx(
        expected, abs=1e-12
    )


def test_blender_extra_derive_default_memory_fraction_with_custom_rule() -> (
    None
):
    """A custom rule can be supplied via the ``rule`` kwarg.

    The ``rule`` parameter is the extension point for future
    derivations (FisherMemoryFraction, OTEpsilonSchedule, etc.).
    This test wires a trivial stub rule and verifies the
    dispatcher routes through it.
    """

    class _StubRule:
        derivation_source = "other"
        derivation_formula = "m := 0.42"
        academic_precedent = ("Test fixture 2026",)
        fallback = 0.5
        required_fields: tuple[str, ...] = ()

        def derive(self, context: DerivationContext) -> float:
            return 0.42

        def __call__(self, context: DerivationContext) -> float:
            return self.derive(context)

    rule = _StubRule()
    assert derive_default_memory_fraction(
        context=make_derivation_context(), rule=rule
    ) == pytest.approx(0.42, abs=1e-12)


def test_blender_extra_default_memory_fraction_fallback_constant() -> None:
    """The module exposes ``DEFAULT_MEMORY_FRACTION_FALLBACK`` constant.

    The constant is the documented identifier of the fallback
    strategy ("adr0010_cosine_driven"). Audit consumers can
    grep this constant in the framework's provenance trail.
    """
    assert DEFAULT_MEMORY_FRACTION_FALLBACK == "adr0010_cosine_driven"
    # Re-exported through the canonical blender_extra module (Wave 105 P2-B merge).
    from adaptive_reflow.algorithm.blender.blender_extra import (
        DEFAULT_MEMORY_FRACTION_FALLBACK as _re,
    )
    assert _re == DEFAULT_MEMORY_FRACTION_FALLBACK


# ---------------------------------------------------------------------------
# (6) DAG / namespace isolation
# ---------------------------------------------------------------------------


def test_polyak_memory_fraction_is_frozen() -> None:
    """``PolyakMemoryFraction`` is a frozen dataclass.

    The class-level provenance attributes must NOT be
    overridable per-instance; that would let a caller claim
    a derivation source that the docs verifier cannot
    cross-check.
    """
    rule = PolyakMemoryFraction()
    with pytest.raises(FrozenInstanceError):
        rule.derivation_source = "fisher"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        rule.fallback = 0.99  # type: ignore[misc]


def test_namespace_constant_is_isolated() -> None:
    """The Fisher-on-posterior namespace is distinct from model parameters.

    The framework's information-geometry derivations (future
    FisherMemoryFraction) operate on the algorithm posterior,
    not on model parameters. The namespace constant guards
    against accidentally sharing derivations across the two
    namespaces — a cross-namespace cycle would invalidate the
    audit trail.
    """
    assert NAMESPACE_ALGORITHM_POSTERIOR == "algorithm_posterior"
    assert NAMESPACE_ALGORITHM_POSTERIOR != "model_parameters"


def test_derivation_cycle_error_is_value_error() -> None:
    """DerivationCycleError is a ValueError subclass.

    Callers that catch ValueError (e.g. the dispatcher's
    fallback path) automatically catch DerivationCycleError.
    """
    assert issubclass(DerivationCycleError, ValueError)


# ---------------------------------------------------------------------------
# (7) Provenance / docs cross-check
# ---------------------------------------------------------------------------


def test_polyak_derivation_cites_real_papers() -> None:
    """Academic precedent cites Polyak 1969 and Lipman 2023.

    The two foundational citations are Polyak (residual-derived
    step size / objective-gap weighting) and Lipman et al.
    (flow matching OT path on which the W2 ratio lives).
    Both are real, peer-reviewed, and exist in standard
    literature. The test asserts the citations are present in
    the precedent tuple (substring match, case-insensitive).
    """
    precedent_blob = " ".join(PolyakMemoryFraction.academic_precedent)
    assert "Polyak" in precedent_blob
    assert "1969" in precedent_blob
    assert "Lipman" in precedent_blob
    assert "2210.02747" in precedent_blob


def test_polyak_derivation_source_is_ot() -> None:
    """``derivation_source`` is ``"ot"``.

    The PolyakMemoryFraction reads OT metrics
    (W2_round_t / W2_round_0) so its source is OT. The docs
    verifier greps this string to map derivations to source
    categories.
    """
    assert PolyakMemoryFraction.derivation_source == "ot"


def test_make_derivation_context_promotes_int_to_float() -> None:
    """``make_derivation_context`` accepts ints for the numeric fields.

    The helper coerces int -> float in the scheduler_state
    mapping so callers passing ``cycle_length=20`` do not hit
    a type error on the closed-form division.
    """
    ctx = make_derivation_context(
        n_cap=0.5,
        cycle_length=20,
        n_rounds=10,
        w2_round_t=0.3,
        w2_round_0=0.7,
    )
    assert ctx.scheduler_state["cycle_length"] == 20.0
    assert ctx.scheduler_state["n_rounds"] == 10.0
    assert ctx.scheduler_state["n_cap_t"] == 0.5
    assert ctx.ot_metrics["W2_round_t"] == 0.3
    assert ctx.ot_metrics["W2_round_0"] == 0.7


def test_make_derivation_context_is_immutable() -> None:
    """``DerivationContext`` is frozen.

    Mutating the context after construction would break the
    audit ledger. The dataclass ``frozen=True`` enforces
    this at runtime.
    """
    ctx = make_derivation_context(n_cap=0.5, w2_round_t=0.3, w2_round_0=0.7)
    with pytest.raises(FrozenInstanceError):
        ctx.ot_metrics = {"W2_round_t": 0.0}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# (8) Gaussian-posterior analytical test (synthetic ground truth)
# ---------------------------------------------------------------------------


def test_polyak_memory_fraction_matches_gaussian_ground_truth() -> None:
    """The derivation matches the analytical closed form on a synthetic
    Gaussian posterior — confirming the math rather than the roundoff.

    Setup: a 1-D Gaussian baseline with mean ``mu_0`` and stddev
    ``sigma_0``; a per-round residual profile with the same mean
    and stddev ``sigma_t`` (zero mean shift so the W2 collapses to
    ``|sigma_t - sigma_0|`` in 1-D). For a baseline with
    ``sigma_0 = 1.0`` and a round with ``sigma_t = 0.25``, the
    closed form is::

        m_t = 0.25 / (1.0 + 0.25) = 0.20

    confirming the rule.
    """
    sigma_0 = 1.0
    sigma_t = 0.25
    # 1-D W2 between N(0, sigma_0^2) and N(0, sigma_t^2) is
    # |sigma_t - sigma_0|. Same for both directions; choose the
    # conventional baseline -> current residual.
    w2_0 = abs(sigma_0 - 0.0)  # baseline spread (cold start)
    w2_t = abs(sigma_t - 0.0)  # current spread
    ctx = make_derivation_context(
        n_cap=0.5, w2_round_t=w2_t, w2_round_0=w2_0
    )
    rule = PolyakMemoryFraction()
    expected = sigma_t / (sigma_0 + sigma_t)
    assert rule(ctx) == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------------
# (9) Public surface smoke
# ---------------------------------------------------------------------------


def test_all_exports_are_importable() -> None:
    """Every name in ``__all__`` is importable.

    The module's public surface is small (8 names). This test
    guards against future refactors that drop a name from
    ``__all__`` while leaving a stale import path.
    """
    from adaptive_reflow.algorithm import _derivation

    for name in _derivation.__all__:
        assert hasattr(_derivation, name), (
            f"_derivation.__all__ lists {name!r} but module "
            f"has no such attribute"
        )


def test_blender_extra_re_exports_derivation_helpers() -> None:
    """blender_extra re-exports the derivation helpers for caller convenience.

    The re-exports let engine code do
    ``from adaptive_reflow.algorithm.blender_extra import
    derive_default_memory_fraction`` without a separate import
    from ``_derivation``.
    """
    # Wave 105 P2-B: blender_extra was merged into blender.blender_extra.
    # The legacy top-level blender_extra shim only re-exports a subset; the
    # canonical (post-merge) module carries the full surface.
    from adaptive_reflow.algorithm.blender import blender_extra

    for name in (
        "PolyakMemoryFraction",
        "DerivationRule",
        "DerivationContext",
        "derive_default_memory_fraction",
        "make_derivation_context",
        "DEFAULT_MEMORY_FRACTION_FALLBACK",
    ):
        assert hasattr(blender_extra, name), (
            f"blender_extra is missing re-export {name!r}"
        )


# ---------------------------------------------------------------------------
# (10) OTEpsilonSchedule — paper_quantities (Lipman 2023, Lemma 3)
# ---------------------------------------------------------------------------


def test_ot_epsilon_schedule_is_runtime_checkable_protocol() -> None:
    """OTEpsilonSchedule conforms to the DerivationRule protocol.

    The 4 new concrete derivations added in P-19 all carry the
    same provenance surface (``derivation_source``,
    ``derivation_formula``, ``academic_precedent``,
    ``fallback``, ``required_fields``) so the docs verifier can
    attribute each derivation to its authorized source.
    """
    rule = OTEpsilonSchedule()
    assert isinstance(rule, DerivationRule)


def test_ot_epsilon_schedule_class_level_provenance() -> None:
    """OTEpsilonSchedule exposes non-empty provenance metadata.

    The class-level attributes must be non-empty strings so the
    ``tools/check_docs_against_code.py`` verifier can grep them.
    """
    cls = OTEpsilonSchedule
    assert cls.derivation_source
    assert cls.derivation_formula
    assert isinstance(cls.academic_precedent, tuple)
    assert len(cls.academic_precedent) >= 1
    for entry in cls.academic_precedent:
        assert entry


@pytest.mark.parametrize(
    ("eps", "c_g", "t", "expected"),
    [
        # t == 0: eps_t == eps_implicit (baseline identity).
        (0.05, 0.1, 0.0, 0.05),
        # t == 5 with C_g == 1.0: eps_t = 0.1 * (1 + 1 * 5) = 0.6.
        (0.1, 1.0, 5.0, 0.6),
        # C_g == 0.0: eps_t == eps_implicit regardless of t.
        (0.05, 0.0, 10.0, 0.05),
        # Small t with moderate C_g: linear interpolation.
        (0.1, 0.5, 2.0, 0.1 * (1.0 + 1.0)),
    ],
)
def test_ot_epsilon_schedule_closed_form(
    eps: float, c_g: float, t: float, expected: float
) -> None:
    """OTEpsilonSchedule matches ``eps_implicit * (1 + C_g * t)``.

    Lipman et al. 2023 (arXiv:2210.02747) OT-path epsilon
    schedule; the closed form grows linearly with the round
    index ``t`` and is constant when ``t == 0`` or ``C_g == 0``.
    """
    ctx = make_derivation_context(c_g=c_g, eps_implicit=eps, t=t)
    rule = OTEpsilonSchedule()
    assert rule(ctx) == pytest.approx(expected, abs=1e-12)


def test_ot_epsilon_schedule_fallback_when_inputs_missing() -> None:
    """Missing inputs return ``DEFAULT_EPSILON_SCHEDULE_FALLBACK``.

    When ``eps_implicit`` or ``C_g`` is ``None``, the rule returns
    the canonical ``0.05`` back-compat baseline so legacy callers
    that do not pass a context keep getting the
    :class:`CodimensionSheetScheduler` default.
    """
    ctx_missing_eps = make_derivation_context(c_g=1.0, t=1.0)
    ctx_missing_c_g = make_derivation_context(eps_implicit=0.1, t=1.0)
    rule = OTEpsilonSchedule()
    assert rule(ctx_missing_eps) == pytest.approx(
        DEFAULT_EPSILON_SCHEDULE_FALLBACK, abs=1e-12
    )
    assert rule(ctx_missing_c_g) == pytest.approx(
        DEFAULT_EPSILON_SCHEDULE_FALLBACK, abs=1e-12
    )


def test_ot_epsilon_schedule_raises_on_invalid_inputs() -> None:
    """Non-finite or negative inputs raise ``ValueError``.

    The rule is fail-closed: ``-0.1`` ``eps_implicit`` raises
    (closed form requires ``eps >= 0``) and ``nan`` ``C_g`` raises
    (must be finite).
    """
    rule = OTEpsilonSchedule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(c_g=1.0, eps_implicit=-0.1, t=0.0))
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(
                c_g=float("nan"), eps_implicit=0.1, t=0.0
            )
        )


def test_default_eps_implicit_dispatcher() -> None:
    """``default_eps_implicit`` routes through OTEpsilonSchedule.

    The dispatcher accepts an explicit ``rule`` kwarg so callers
    can opt into the BL-convergence form. The fallback path
    preserves the documented ``0.05`` baseline.
    """
    ctx = make_derivation_context(
        c_g=1.0, eps_implicit=0.1, t=5.0
    )
    assert default_eps_implicit(ctx) == pytest.approx(0.6, abs=1e-12)
    # BL-convergence form: eps_t = sqrt(e_rho * delta_t).
    ctx_bl = make_derivation_context(
        e_rho=0.01, delta_t=0.25, eps_implicit=0.05
    )
    assert default_eps_implicit(
        ctx_bl, rule=BLConvergenceEpsilonSchedule()
    ) == pytest.approx(math.sqrt(0.01 * 0.25), abs=1e-12)
    # Fallback path: no context, returns the canonical 0.05.
    assert default_eps_implicit(None) == pytest.approx(
        DEFAULT_EPSILON_SCHEDULE_FALLBACK, abs=1e-12
    )


# ---------------------------------------------------------------------------
# (11) BLConvergenceEpsilonSchedule — Theorem 1 (Li 2024)
# ---------------------------------------------------------------------------


def test_bl_convergence_epsilon_schedule_is_runtime_checkable() -> None:
    """BLConvergenceEpsilonSchedule conforms to DerivationRule."""
    rule = BLConvergenceEpsilonSchedule()
    assert isinstance(rule, DerivationRule)


def test_bl_convergence_epsilon_schedule_provenance() -> None:
    """BLConvergenceEpsilonSchedule carries non-empty provenance."""
    cls = BLConvergenceEpsilonSchedule
    assert cls.derivation_source
    assert cls.derivation_formula
    assert isinstance(cls.academic_precedent, tuple)
    assert len(cls.academic_precedent) >= 1
    assert cls.fallback == pytest.approx(1e-3, abs=1e-12)


@pytest.mark.parametrize(
    ("e_rho", "delta_t", "expected"),
    [
        # e_rho = 0.04, delta_t = 0.25 -> sqrt(0.01) = 0.1
        (0.04, 0.25, 0.1),
        # e_rho = 0.16, delta_t = 1.0 -> sqrt(0.16) = 0.4
        (0.16, 1.0, 0.4),
        # Zero e_rho: eps_t = 0 (closed form).
        (0.0, 0.5, 0.0),
    ],
)
def test_bl_convergence_epsilon_schedule_closed_form(
    e_rho: float, delta_t: float, expected: float
) -> None:
    """BLConvergenceEpsilonSchedule matches ``sqrt(e_rho * delta_t)``.

    Li 2024 Theorem 1 / Lemma 5 closed form; the per-round eps
    is the geometric mean of the exterior gap and the round
    step.
    """
    ctx = make_derivation_context(e_rho=e_rho, delta_t=delta_t)
    rule = BLConvergenceEpsilonSchedule()
    assert rule(ctx) == pytest.approx(expected, abs=1e-12)


def test_bl_convergence_epsilon_schedule_fallback_when_e_rho_missing() -> None:
    """Missing ``e_rho`` returns the documented ``1e-3`` fallback.

    The fallback matches the asymptotic threshold below which
    the heuristic evidence balance is unsound — see
    :data:`adaptive_reflow.algorithm.evidence_driver.EVIDENCE_HEURISTIC_EPS_THRESHOLD`.
    """
    rule = BLConvergenceEpsilonSchedule()
    assert rule(make_derivation_context(delta_t=0.5)) == pytest.approx(
        1e-3, abs=1e-12
    )


def test_bl_convergence_epsilon_schedule_falls_back_to_cycle_length() -> None:
    """Missing ``delta_t`` derives it from ``cycle_length``.

    When ``delta_t`` is ``None`` but ``cycle_length`` is supplied,
    the rule uses ``1.0 / cycle_length`` as the round step.
    """
    ctx = make_derivation_context(e_rho=0.04, cycle_length=4)
    rule = BLConvergenceEpsilonSchedule()
    # 1.0 / 4 = 0.25; sqrt(0.04 * 0.25) = sqrt(0.01) = 0.1
    assert rule(ctx) == pytest.approx(0.1, abs=1e-12)


def test_bl_convergence_epsilon_schedule_raises_on_invalid_inputs() -> None:
    """Negative ``e_rho`` raises ``ValueError``.

    The rule is fail-closed: a negative ``e_rho`` would produce a
    ``NaN`` ``sqrt`` rather than silently coercing.
    """
    rule = BLConvergenceEpsilonSchedule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(e_rho=-0.01, delta_t=0.25))


# ---------------------------------------------------------------------------
# (12) LipschitzStepSize — Dormand-Prince 1980
# ---------------------------------------------------------------------------


def test_lipschitz_step_size_is_runtime_checkable() -> None:
    """LipschitzStepSize conforms to DerivationRule."""
    rule = LipschitzStepSize()
    assert isinstance(rule, DerivationRule)


def test_lipschitz_step_size_provenance() -> None:
    """LipschitzStepSize carries non-empty provenance."""
    cls = LipschitzStepSize
    assert cls.derivation_source
    assert cls.derivation_formula
    assert isinstance(cls.academic_precedent, tuple)
    assert len(cls.academic_precedent) >= 1
    assert "Dormand" in " ".join(cls.academic_precedent)


@pytest.mark.parametrize(
    ("l_e", "tol", "err", "expected"),
    [
        # tol / err = 1; (1)^{1/5} / L_e = 1 / L_e
        (2.0, 1e-5, 1e-5, 1.0 / 2.0),
        # tol / err = 32; 32^{1/5} = 2; 2 / L_e = 1
        (2.0, 3.2e-4, 1e-5, 1.0),
        # Small L_e (smooth region): step scales up.
        (0.5, 1e-5, 1e-5, 1.0 / 0.5),
        # err < 1e-9 floor: clamped to 1e-9 -> tol / 1e-9 = 1e4;
        # 1e4^{1/5} ~ 6.31; divided by L_e = 2.0.
        (2.0, 1e-5, 0.0, (1e-5 / 1e-9) ** 0.2 / 2.0),
    ],
)
def test_lipschitz_step_size_closed_form(
    l_e: float, tol: float, err: float, expected: float
) -> None:
    """LipschitzStepSize matches ``(tol / err)^{1/5} / L_e``.

    Dormand-Prince 1980 RK45 adaptive-step closed form. The
    ``1/5`` exponent is the embedded-formula order; the ``1e-9``
    floor on ``err`` guards against zero / negative errors.
    """
    ctx = make_derivation_context(l_e=l_e, tol=tol, err=err)
    rule = LipschitzStepSize()
    assert rule(ctx) == pytest.approx(expected, abs=1e-12)


def test_lipschitz_step_size_falls_back_to_uniform_step() -> None:
    """Missing ``L_e`` returns ``1.0 / n_steps``.

    The fallback is the canonical uniform-step Dormand-Prince
    controller used by ``dynamics_solver`` when no Lipschitz
    estimator is wired.
    """
    rule = LipschitzStepSize()
    ctx = make_derivation_context(n_steps=20)
    assert rule(ctx) == pytest.approx(0.05, abs=1e-12)
    # Also via dispatcher.
    assert default_lipschitz_step(ctx) == pytest.approx(0.05, abs=1e-12)


def test_lipschitz_step_size_raises_on_invalid_inputs() -> None:
    """Negative ``L_e`` and ``tol`` raise ``ValueError``.

    The closed form requires all three inputs positive; a
    non-positive input is a contract violation.
    """
    rule = LipschitzStepSize()
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(l_e=-1.0, tol=1e-5, err=1e-5)
        )
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(l_e=1.0, tol=-1e-5, err=1e-5)
        )


def test_default_lipschitz_step_dispatcher() -> None:
    """``default_lipschitz_step`` falls back to ``1.0 / n_steps``.

    The dispatcher catches :class:`ValueError` from the rule
    and returns the uniform-step fallback.
    """
    # Full context: derives the step.
    ctx = make_derivation_context(l_e=2.0, tol=1e-5, err=1e-5)
    assert default_lipschitz_step(ctx) == pytest.approx(0.5, abs=1e-12)
    # Missing context + n_steps kwarg.
    assert default_lipschitz_step(None, n_steps=10) == pytest.approx(
        0.1, abs=1e-12
    )
    # Empty context + no n_steps: returns the documented 0.05
    # mid-cycle anchor.
    assert default_lipschitz_step(None) == pytest.approx(0.05, abs=1e-12)


# ---------------------------------------------------------------------------
# (13) FisherMemoryFraction — Amari 1998
# ---------------------------------------------------------------------------


def test_fisher_memory_fraction_is_runtime_checkable() -> None:
    """FisherMemoryFraction conforms to DerivationRule."""
    rule = FisherMemoryFraction()
    assert isinstance(rule, DerivationRule)


def test_fisher_memory_fraction_provenance() -> None:
    """FisherMemoryFraction cites Amari 1998 and the Lemma 4 gap."""
    cls = FisherMemoryFraction
    assert cls.derivation_source
    assert cls.derivation_formula
    assert isinstance(cls.academic_precedent, tuple)
    assert len(cls.academic_precedent) >= 1
    assert "Amari" in " ".join(cls.academic_precedent)


@pytest.mark.parametrize(
    ("e_rho", "f_trace", "d", "expected"),
    [
        # F_trace == d: m_fisher = 0.5; alpha_grad = exp(-e_rho).
        # e_rho = ln(2); alpha_grad = 0.5; product = 0.25.
        (math.log(2.0), 2.0, 2.0, 0.5 * 0.5),
        # F_trace = 0: m_fisher = 1; alpha_grad = exp(0) = 1;
        # product = 1.0.
        (0.0, 0.0, 4.0, 1.0),
        # Large F_trace: m_fisher ~ 2e-6; alpha_grad = exp(-1) ~ 0.368;
        # product clipped toward 0 but not exactly 0.
        (
            1.0,
            1e6,
            2.0,
            float(math.exp(-1.0)) / (1.0 + 1e6 / 2.0),
        ),
    ],
)
def test_fisher_memory_fraction_closed_form(
    e_rho: float, f_trace: float, d: int, expected: float
) -> None:
    """FisherMemoryFraction matches ``exp(-e_rho) / (1 + F_trace/d)``.

    Amari 1998 natural-gradient step applied to the algorithm
    posterior (NOT model parameters). The canonical return is
    the alpha_grad * m_fisher product clipped into ``[0, 1]``.
    """
    ctx = make_derivation_context(
        e_rho=e_rho, f_trace=f_trace, d=d
    )
    rule = FisherMemoryFraction()
    assert rule(ctx) == pytest.approx(expected, abs=1e-9)


def test_fisher_memory_fraction_falls_back_when_inputs_missing() -> None:
    """Missing inputs return the documented ``0.5`` fallback.

    The rule's fallback matches the documented mid-cycle anchor
    used by :class:`PolyakMemoryFraction`; this keeps the
    framework's parameter-free regime opt-in.
    """
    rule = FisherMemoryFraction()
    assert rule(make_derivation_context()) == pytest.approx(0.5, abs=1e-12)
    assert rule(
        make_derivation_context(e_rho=0.01)
    ) == pytest.approx(0.5, abs=1e-12)
    assert rule(
        make_derivation_context(f_trace=1.0, d=2)
    ) == pytest.approx(0.5, abs=1e-12)


def test_fisher_memory_fraction_raises_on_invalid_inputs() -> None:
    """Negative inputs and zero ``d`` raise ``ValueError``.

    The closed form requires all inputs positive (``d`` is
    strictly positive because it's a dimension); the rule is
    fail-closed.
    """
    rule = FisherMemoryFraction()
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(
                e_rho=-0.01, f_trace=1.0, d=2
            )
        )
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(
                e_rho=0.01, f_trace=1.0, d=0
            )
        )
    with pytest.raises(ValueError):
        rule(
            make_derivation_context(
                e_rho=0.01, f_trace=-1.0, d=2
            )
        )


def test_default_alpha_grad_dispatcher() -> None:
    """``default_alpha_grad`` returns ``exp(-e_rho)`` from context.

    The dispatcher is the canonical entry point for the
    MeanFlow EMA coefficient used by
    :class:`~adaptive_reflow.algorithm.merge_operator_v3.MeanFlowMergeOperator`.
    """
    ctx = make_derivation_context(e_rho=math.log(2.0))
    assert default_alpha_grad(ctx) == pytest.approx(0.5, abs=1e-12)
    # Fallback path: no context, returns the canonical 0.5.
    assert default_alpha_grad(None) == pytest.approx(0.5, abs=1e-12)
    # e_rho kwarg is folded into the context.
    assert default_alpha_grad(None, e_rho=0.0) == pytest.approx(
        1.0, abs=1e-12
    )


# ---------------------------------------------------------------------------
# (14) default_handoff_window — Lipschitz-derived handoff width
# ---------------------------------------------------------------------------


def test_default_handoff_window_with_lipschitz() -> None:
    """``default_handoff_window`` derives ``k`` from ``L_e``.

    The handoff window is ``round(1.0 / L_e)``: a Lipschitz of
    ``0.5`` (smooth region) widens the window to 2 rounds; a
    Lipschitz of ``2.0`` (stiff region) shrinks it to 0 (sharp
    boundary).
    """
    ctx_smooth = make_derivation_context(l_e=0.5)
    ctx_stiff = make_derivation_context(l_e=2.0)
    assert default_handoff_window(ctx_smooth) == 2
    assert default_handoff_window(ctx_stiff) == 0


def test_default_handoff_window_without_context() -> None:
    """``None`` context returns the supplied ``handoff_window``.

    The dispatcher accepts a ``handoff_window`` kwarg that is
    forwarded when the context is missing.
    """
    assert default_handoff_window(None, handoff_window=5) == 5
    assert default_handoff_window(None) == 0
    # Negative handoff_window is clamped to 0.
    assert default_handoff_window(None, handoff_window=-1) == 0


# ---------------------------------------------------------------------------
# (15) Module exports — verify all 4 new rules are importable
# ---------------------------------------------------------------------------


def test_all_4_new_rules_are_exported() -> None:
    """The 4 new concrete derivation rules are in ``__all__``.

    The module's public surface now exposes 4 new rules
    (OTEpsilonSchedule, BLConvergenceEpsilonSchedule,
    LipschitzStepSize, FisherMemoryFraction) plus their
    dispatchers (default_eps_implicit,
    default_lipschitz_step, default_alpha_grad,
    default_handoff_window).
    """
    from adaptive_reflow.algorithm import _derivation

    expected = {
        "OTEpsilonSchedule",
        "BLConvergenceEpsilonSchedule",
        "LipschitzStepSize",
        "FisherMemoryFraction",
        "default_eps_implicit",
        "default_lipschitz_step",
        "default_alpha_grad",
        "default_handoff_window",
        "DEFAULT_EPSILON_SCHEDULE_FALLBACK",
        "DEFAULT_LIPSCHITZ_STEP_FALLBACK",
    }
    for name in expected:
        assert name in _derivation.__all__, (
            f"_derivation.__all__ missing {name!r}"
        )
        assert hasattr(_derivation, name), (
            f"_derivation has no attribute {name!r}"
        )


def test_all_4_new_rules_are_frozen_dataclasses() -> None:
    """The 4 new concrete rules are frozen dataclasses.

    The class-level provenance attributes must NOT be
    overridable per-instance; that would let a caller claim a
    derivation source the docs verifier cannot cross-check.
    """
    for cls in (
        OTEpsilonSchedule,
        BLConvergenceEpsilonSchedule,
        LipschitzStepSize,
        FisherMemoryFraction,
    ):
        rule = cls()
        with pytest.raises(FrozenInstanceError):
            rule.derivation_source = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            rule.fallback = 0.99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# (16) P-19 #7 — MeanFlowToleranceRule (Polyak ratio)
# ---------------------------------------------------------------------------


def test_meanflow_tolerance_closed_form() -> None:
    """MeanFlowToleranceRule matches ``base_tol * n_min / n_cap_t``.

    Polyak 1969 step applied to the cycle anchor ratio. A
    1:2 n_min:n_cap ratio doubles the tolerance; a 2:1 ratio
    halves it.
    """
    # 1e-9 * 0.5 / 1.0 = 5e-10
    ctx = make_derivation_context(n_min=0.5, n_cap=1.0)
    assert MeanFlowToleranceRule()(ctx) == pytest.approx(5e-10, abs=1e-15)
    # 1e-9 * 2.0 / 1.0 = 2e-9
    ctx2 = make_derivation_context(n_min=2.0, n_cap=1.0)
    assert MeanFlowToleranceRule()(ctx2) == pytest.approx(2e-9, abs=1e-15)


def test_meanflow_tolerance_fallback() -> None:
    """Missing inputs return the documented ``1e-9`` fallback."""
    rule = MeanFlowToleranceRule()
    assert rule(make_derivation_context()) == pytest.approx(1e-9, abs=1e-15)
    # None context returns the same fallback via dispatcher.
    assert default_tolerance(None) == pytest.approx(1e-9, abs=1e-15)


def test_meanflow_tolerance_invalid_inputs_raise() -> None:
    """Non-positive ``n_min`` or ``n_cap_t`` raise ``ValueError``."""
    rule = MeanFlowToleranceRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(n_min=0.0, n_cap=1.0))
    with pytest.raises(ValueError):
        rule(make_derivation_context(n_min=0.5, n_cap=0.0))


# ---------------------------------------------------------------------------
# (17) P-19 #8 — MachineEpsilonRule (Lipschitz-driven machine eps)
# ---------------------------------------------------------------------------


def test_machine_epsilon_closed_form() -> None:
    """MachineEpsilonRule matches ``base_eps * |t - s|``."""
    # 1e-12 * |1.0 - 0.0| = 1e-12
    ctx = make_derivation_context(t=1.0, s=0.0)
    assert MachineEpsilonRule()(ctx) == pytest.approx(1e-12, abs=1e-20)
    # 1e-12 * |2.0 - 1.0| = 1e-12
    ctx2 = make_derivation_context(t=2.0, s=1.0)
    assert MachineEpsilonRule()(ctx2) == pytest.approx(1e-12, abs=1e-20)
    # 1e-12 * |0.5 - 0.0| = 5e-13
    ctx3 = make_derivation_context(t=0.5, s=0.0)
    assert MachineEpsilonRule()(ctx3) == pytest.approx(5e-13, abs=1e-20)


def test_machine_epsilon_fallback() -> None:
    """Missing ``t`` or ``s`` returns the documented ``1e-12`` fallback."""
    rule = MachineEpsilonRule()
    assert rule(make_derivation_context()) == pytest.approx(1e-12, abs=1e-20)
    assert default_machine_eps(None) == pytest.approx(1e-12, abs=1e-20)


# ---------------------------------------------------------------------------
# (18) P-19 #9 — EMAInverseVarianceRule (Polyak inverse-variance)
# ---------------------------------------------------------------------------


def test_ema_inverse_variance_closed_form() -> None:
    """EMAInverseVarianceRule matches ``1 / (1 + grad_var / grad_mean^2)``."""
    # grad_var = 1, grad_mean = 1 -> ratio = 1, alpha = 0.5.
    ctx = make_derivation_context(grad_var=1.0, grad_mean=1.0)
    assert EMAInverseVarianceRule()(ctx) == pytest.approx(0.5, abs=1e-12)
    # grad_var = 0, grad_mean = 1 -> ratio = 0, alpha = 1.0.
    ctx2 = make_derivation_context(grad_var=0.0, grad_mean=1.0)
    assert EMAInverseVarianceRule()(ctx2) == pytest.approx(1.0, abs=1e-12)
    # grad_var = 3, grad_mean = 1 -> ratio = 3, alpha = 1/4.
    ctx3 = make_derivation_context(grad_var=3.0, grad_mean=1.0)
    assert EMAInverseVarianceRule()(ctx3) == pytest.approx(0.25, abs=1e-12)


def test_ema_inverse_variance_vanishing_grad_mean() -> None:
    """Vanishing ``grad_mean`` returns the sharp-regime anchor ``1.0``."""
    ctx = make_derivation_context(grad_var=1.0, grad_mean=0.0)
    assert EMAInverseVarianceRule()(ctx) == pytest.approx(1.0, abs=1e-12)


def test_ema_inverse_variance_fallback() -> None:
    """Missing inputs return the documented ``0.1`` fallback."""
    rule = EMAInverseVarianceRule()
    assert rule(make_derivation_context()) == pytest.approx(0.1, abs=1e-12)
    assert default_ema_alpha(None) == pytest.approx(0.1, abs=1e-12)


def test_ema_inverse_variance_invalid_inputs_raise() -> None:
    """Negative ``grad_var`` raises ``ValueError``."""
    rule = EMAInverseVarianceRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(grad_var=-1.0, grad_mean=1.0))


# ---------------------------------------------------------------------------
# (19) P-19 #10 — LipschitzTemperatureRule
# ---------------------------------------------------------------------------


def test_lipschitz_temperature_closed_form() -> None:
    """LipschitzTemperatureRule matches ``1 / sqrt(L_local * n_rounds)``."""
    # L_e = 1, n_rounds = 4 -> tau = 1 / sqrt(4) = 0.5.
    ctx = make_derivation_context(l_e=1.0, n_rounds=4)
    assert LipschitzTemperatureRule()(ctx) == pytest.approx(0.5, abs=1e-12)
    # L_e = 4, n_rounds = 1 -> tau = 1 / sqrt(4) = 0.5.
    ctx2 = make_derivation_context(l_e=4.0, n_rounds=1)
    assert LipschitzTemperatureRule()(ctx2) == pytest.approx(0.5, abs=1e-12)
    # L_e = 0.25, n_rounds = 16 -> tau = 1 / sqrt(4) = 0.5.
    ctx3 = make_derivation_context(l_e=0.25, n_rounds=16)
    assert LipschitzTemperatureRule()(ctx3) == pytest.approx(0.5, abs=1e-12)


def test_lipschitz_temperature_fallback() -> None:
    """Missing inputs return the documented ``1.0`` fallback."""
    rule = LipschitzTemperatureRule()
    assert rule(make_derivation_context()) == pytest.approx(1.0, abs=1e-12)
    assert (
        default_distance_decay_temperature(None)
        == pytest.approx(1.0, abs=1e-12)
    )


def test_lipschitz_temperature_invalid_inputs_raise() -> None:
    """Non-positive ``L_e`` or ``n_rounds`` raise ``ValueError``."""
    rule = LipschitzTemperatureRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(l_e=0.0, n_rounds=10))
    with pytest.raises(ValueError):
        rule(make_derivation_context(l_e=1.0, n_rounds=0))


# ---------------------------------------------------------------------------
# (20) P-19 #11 — MinGumbelTempRule (paper-quantity e_rho / 4)
# ---------------------------------------------------------------------------


def test_min_gumbel_temp_closed_form() -> None:
    """MinGumbelTempRule matches ``e_rho / 4``."""
    # e_rho = 0.004 -> tau = 0.001.
    ctx = make_derivation_context(e_rho=0.004)
    assert MinGumbelTempRule()(ctx) == pytest.approx(1e-3, abs=1e-15)
    # e_rho = 0.0 -> tau = 0.
    ctx2 = make_derivation_context(e_rho=0.0)
    assert MinGumbelTempRule()(ctx2) == pytest.approx(0.0, abs=1e-15)


def test_min_gumbel_temp_fallback() -> None:
    """Missing ``e_rho`` returns the documented ``1e-3`` fallback."""
    rule = MinGumbelTempRule()
    assert rule(make_derivation_context()) == pytest.approx(1e-3, abs=1e-15)
    assert default_min_gumbel_temp(None) == pytest.approx(1e-3, abs=1e-15)


def test_min_gumbel_temp_invalid_inputs_raise() -> None:
    """Negative ``e_rho`` raises ``ValueError``."""
    rule = MinGumbelTempRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(e_rho=-0.01))


# ---------------------------------------------------------------------------
# (21) P-19 #12 — EpsLogRule (paper-quantity e_rho / 8)
# ---------------------------------------------------------------------------


def test_eps_log_closed_form() -> None:
    """EpsLogRule matches ``e_rho / 8`` (or fallback for zero)."""
    # e_rho = 8e-30 -> eps_log = 1e-30.
    ctx = make_derivation_context(e_rho=8e-30)
    assert EpsLogRule()(ctx) == pytest.approx(1e-30, abs=1e-45)
    # e_rho = 0.0 -> eps_log = fallback (1e-30) — never zero.
    ctx2 = make_derivation_context(e_rho=0.0)
    assert EpsLogRule()(ctx2) == pytest.approx(1e-30, abs=1e-45)


def test_eps_log_fallback() -> None:
    """Missing ``e_rho`` returns the documented ``1e-30`` fallback."""
    rule = EpsLogRule()
    assert rule(make_derivation_context()) == pytest.approx(1e-30, abs=1e-45)
    assert default_eps_log(None) == pytest.approx(1e-30, abs=1e-45)


def test_eps_log_invalid_inputs_raise() -> None:
    """Negative ``e_rho`` raises ``ValueError``."""
    rule = EpsLogRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(e_rho=-1.0))


# ---------------------------------------------------------------------------
# (22) P-19 #13 — ExponentialAlphaRule (variance-preserving decay)
# ---------------------------------------------------------------------------


def test_exponential_alpha_closed_form() -> None:
    """ExponentialAlphaRule matches ``ln(n_max / n_min) / (L - 1)``."""
    # n_min = 0.5, n_max = 1.0, L = 11 -> ln(2)/10.
    ctx = make_derivation_context(
        n_min=0.5, n_max=1.0, cycle_length=11
    )
    expected = math.log(2.0) / 10.0
    assert ExponentialAlphaRule()(ctx) == pytest.approx(expected, abs=1e-12)
    # n_min = n_max: alpha = 0 (no decay).
    ctx2 = make_derivation_context(
        n_min=1.0, n_max=1.0, cycle_length=10
    )
    assert ExponentialAlphaRule()(ctx2) == pytest.approx(0.0, abs=1e-12)


def test_exponential_alpha_fallback() -> None:
    """Missing inputs return the documented ``0.1`` fallback."""
    rule = ExponentialAlphaRule()
    assert rule(make_derivation_context()) == pytest.approx(0.1, abs=1e-12)
    assert default_exponential_alpha(None) == pytest.approx(0.1, abs=1e-12)


def test_exponential_alpha_invalid_inputs_raise() -> None:
    """Non-positive ``n_min`` or ``n_max`` raises ``ValueError``."""
    rule = ExponentialAlphaRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(
            n_min=0.0, n_max=1.0, cycle_length=10
        ))
    with pytest.raises(ValueError):
        rule(make_derivation_context(
            n_min=0.5, n_max=0.0, cycle_length=10
        ))


# ---------------------------------------------------------------------------
# (23) P-19 #14 — PolynomialPowerRule (analytic variance-preserving)
# ---------------------------------------------------------------------------


def test_polynomial_power_closed_form() -> None:
    """PolynomialPowerRule matches ``2 * L / (L + 1)``."""
    # L = 3 -> 6/4 = 1.5.
    ctx = make_derivation_context(cycle_length=3)
    assert PolynomialPowerRule()(ctx) == pytest.approx(1.5, abs=1e-12)
    # L = 5 -> 10/6 = 1.667.
    ctx2 = make_derivation_context(cycle_length=5)
    assert PolynomialPowerRule()(ctx2) == pytest.approx(
        10.0 / 6.0, abs=1e-12
    )


def test_polynomial_power_fallback() -> None:
    """Missing ``cycle_length`` returns the documented ``2.0`` fallback."""
    rule = PolynomialPowerRule()
    assert rule(make_derivation_context()) == pytest.approx(2.0, abs=1e-12)
    assert default_polynomial_power(None) == pytest.approx(2.0, abs=1e-12)


# ---------------------------------------------------------------------------
# (24) P-19 #15 — SigmoidMidpointSteepnessRule
# ---------------------------------------------------------------------------


def test_sigmoid_midpoint_closed_form() -> None:
    """SigmoidMidpointSteepnessRule.midpoint matches ``(n_min + n_max) / 2``."""
    rule = SigmoidMidpointSteepnessRule()
    ctx = make_derivation_context(n_min=0.2, n_max=0.8)
    assert rule.derive_midpoint(ctx) == pytest.approx(0.5, abs=1e-12)
    ctx2 = make_derivation_context(n_min=0.0, n_max=1.0)
    assert rule.derive_midpoint(ctx2) == pytest.approx(0.5, abs=1e-12)


def test_sigmoid_steepness_closed_form() -> None:
    """SigmoidMidpointSteepnessRule.steepness matches ``1 / I_F(W2)``."""
    rule = SigmoidMidpointSteepnessRule()
    # I_F = 0.1 -> steepness = 10.0.
    ctx = make_derivation_context(fisher_information=0.1)
    assert rule.derive_steepness(ctx) == pytest.approx(10.0, abs=1e-12)
    # I_F = 0.01 -> steepness = 100.0.
    ctx2 = make_derivation_context(fisher_information=0.01)
    assert rule.derive_steepness(ctx2) == pytest.approx(
        100.0, abs=1e-12
    )


def test_sigmoid_fallback() -> None:
    """Missing inputs return the documented fallbacks ``0.5`` / ``10.0``."""
    rule = SigmoidMidpointSteepnessRule()
    assert rule.derive_midpoint(make_derivation_context()) == pytest.approx(
        0.5, abs=1e-12
    )
    assert rule.derive_steepness(make_derivation_context()) == pytest.approx(
        10.0, abs=1e-12
    )
    assert default_sigmoid_midpoint(None) == pytest.approx(0.5, abs=1e-12)
    assert default_sigmoid_steepness(None) == pytest.approx(10.0, abs=1e-12)


# ---------------------------------------------------------------------------
# (25) P-19 #16 — ConvergenceAdaptivePolyRule (kp/kd/shift_max/ema)
# ---------------------------------------------------------------------------


def test_convergence_adaptive_kp_closed_form() -> None:
    """ConvergenceAdaptivePolyRule.kp scales with the W2 ratio."""
    # W2_history = [1.0, 0.5]: ratio = 0.5 -> kp = 0.10 * 0.5 = 0.05.
    rule = ConvergenceAdaptivePolyRule()
    ctx = make_derivation_context(w2_history=(1.0, 0.5))
    assert rule.derive_kp(ctx) == pytest.approx(0.05, abs=1e-12)


def test_convergence_adaptive_kd_closed_form() -> None:
    """ConvergenceAdaptivePolyRule.kd scales with ``(1 - ratio)``."""
    rule = ConvergenceAdaptivePolyRule()
    ctx = make_derivation_context(w2_history=(1.0, 0.5))
    # kd = 0.05 * (1 - 0.5) = 0.025.
    assert rule.derive_kd(ctx) == pytest.approx(0.025, abs=1e-12)


def test_convergence_adaptive_shift_max_closed_form() -> None:
    """ConvergenceAdaptivePolyRule.shift_max matches ``3 * ratio^2``."""
    rule = ConvergenceAdaptivePolyRule()
    ctx = make_derivation_context(w2_history=(1.0, 0.5))
    # 3 * 0.25 = 0.75.
    assert rule.derive_shift_max(ctx) == pytest.approx(0.75, abs=1e-12)


def test_convergence_adaptive_ema_closed_form() -> None:
    """ConvergenceAdaptivePolyRule.ema matches ``1 / (1 + L / beta1)``."""
    rule = ConvergenceAdaptivePolyRule()
    # L = 9, beta1 = 10 -> ema = 1 / (1 + 0.9) = 10/19.
    ctx = make_derivation_context(cycle_length=9)
    assert rule.derive_ema(ctx) == pytest.approx(
        10.0 / 19.0, abs=1e-12
    )


def test_convergence_adaptive_fallback() -> None:
    """Missing inputs return documented fallbacks ``0.10`` / ``0.05`` / ``0.15`` / ``0.3``."""
    rule = ConvergenceAdaptivePolyRule()
    ctx_empty = make_derivation_context()
    assert rule.derive_kp(ctx_empty) == pytest.approx(0.10, abs=1e-12)
    assert rule.derive_kd(ctx_empty) == pytest.approx(0.05, abs=1e-12)
    assert rule.derive_shift_max(ctx_empty) == pytest.approx(0.15, abs=1e-12)
    assert rule.derive_ema(ctx_empty) == pytest.approx(0.3, abs=1e-12)
    assert default_convergence_adaptive_kp(None) == pytest.approx(
        0.10, abs=1e-12
    )
    assert default_convergence_adaptive_kd(None) == pytest.approx(
        0.05, abs=1e-12
    )
    assert default_convergence_adaptive_shift_max(None) == pytest.approx(
        0.15, abs=1e-12
    )
    assert default_convergence_adaptive_ema(None) == pytest.approx(
        0.3, abs=1e-12
    )


# ---------------------------------------------------------------------------
# (26) P-19 #17 — MetricWeightRule (1 / Var_m)
# ---------------------------------------------------------------------------


def test_metric_weight_closed_form() -> None:
    """MetricWeightRule returns ``1 / Var_m`` per metric."""
    rule = MetricWeightRule()
    # Var(W2) on [1.0, 1.0, 1.0] = 0 -> weight = 1.0 (constant).
    # Var(coverage) on [0.0, 1.0] = 0.25 -> weight = 4.0.
    var_map = {
        "W2": (1.0, 1.0, 1.0),
        "coverage": (0.0, 1.0),
    }
    ctx = make_derivation_context(metric_variances=var_map)
    weights = rule(ctx)
    assert weights["W2"] == pytest.approx(1.0, abs=1e-12)
    assert weights["coverage"] == pytest.approx(4.0, abs=1e-12)


def test_metric_weight_fallback() -> None:
    """Missing ``metric_variances`` returns the documented literal default."""
    rule = MetricWeightRule()
    weights = rule(make_derivation_context())
    assert weights == {
        "W2": 1.0,
        "coverage": 0.3,
        "selection_ratio": 0.5,
    }
    assert default_metric_weights(None) == {
        "W2": 1.0,
        "coverage": 0.3,
        "selection_ratio": 0.5,
    }


# ---------------------------------------------------------------------------
# (27) P-19 #18 — VariancePreservingJitterRule
# ---------------------------------------------------------------------------


def test_variance_preserving_jitter_closed_form() -> None:
    """VariancePreservingJitterRule matches ``sqrt(n_cap * (1 - n_cap) / L)``."""
    rule = VariancePreservingJitterRule()
    # n_cap = 0.5, L = 20 -> sqrt(0.5 * 0.5 / 20) = sqrt(0.0125).
    ctx = make_derivation_context(n_cap=0.5, n_rounds=20)
    assert rule(ctx) == pytest.approx(math.sqrt(0.0125), abs=1e-12)
    # n_cap = 1.0 -> jitter = 0.
    ctx2 = make_derivation_context(n_cap=1.0, n_rounds=20)
    assert rule(ctx2) == pytest.approx(0.0, abs=1e-12)


def test_variance_preserving_jitter_fallback() -> None:
    """Missing inputs return the documented ``0.05`` fallback."""
    rule = VariancePreservingJitterRule()
    assert rule(make_derivation_context()) == pytest.approx(0.05, abs=1e-12)
    assert default_jitter_std(None) == pytest.approx(0.05, abs=1e-12)


def test_variance_preserving_jitter_invalid_inputs_raise() -> None:
    """Out-of-range ``n_cap`` raises ``ValueError``."""
    rule = VariancePreservingJitterRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(n_cap=1.5, n_rounds=20))
    with pytest.raises(ValueError):
        rule(make_derivation_context(n_cap=0.5, n_rounds=0))


# ---------------------------------------------------------------------------
# (28) P-19 #20 — MidpointBetaRule
# ---------------------------------------------------------------------------


def test_midpoint_beta_closed_form() -> None:
    """MidpointBetaRule matches ``(n_min + n_max) / 2``."""
    rule = MidpointBetaRule()
    ctx = make_derivation_context(n_min=0.3, n_max=0.7)
    assert rule(ctx) == pytest.approx(0.5, abs=1e-12)
    ctx2 = make_derivation_context(n_min=0.0, n_max=1.0)
    assert rule(ctx2) == pytest.approx(0.5, abs=1e-12)


def test_midpoint_beta_fallback() -> None:
    """Missing inputs return the documented ``0.5`` fallback."""
    rule = MidpointBetaRule()
    assert rule(make_derivation_context()) == pytest.approx(0.5, abs=1e-12)
    assert default_constant_beta(None) == pytest.approx(0.5, abs=1e-12)


# ---------------------------------------------------------------------------
# (29) P-19 #5 — BoundaryConditionRule (Theorem-fixed)
# ---------------------------------------------------------------------------


def test_boundary_condition_rule_returns_canonical() -> None:
    """BoundaryConditionRule returns ``(t=1.0, s=0.0)`` regardless of context."""
    rule = BoundaryConditionRule()
    assert rule.derive(make_derivation_context()) == 1.0
    assert rule.derive_s(make_derivation_context()) == 0.0
    # Theorem-fixed: no derivation from context.
    assert rule.derivation_source == "other"


def test_boundary_condition_rule_is_frozen() -> None:
    """BoundaryConditionRule is a frozen dataclass."""
    rule = BoundaryConditionRule()
    with pytest.raises(FrozenInstanceError):
        rule.fallback = 0.99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# (30) P-19 #2 — MeanFlowFixedStrengthRule (Theorem 1 fixed drive)
# ---------------------------------------------------------------------------


def test_meanflow_fixed_strength_returns_canonical() -> None:
    """MeanFlowFixedStrengthRule returns ``1.0`` regardless of context."""
    rule = MeanFlowFixedStrengthRule()
    assert rule.derive(make_derivation_context()) == 1.0
    assert rule.fallback == 1.0


def test_meanflow_fixed_strength_is_frozen() -> None:
    """MeanFlowFixedStrengthRule is a frozen dataclass."""
    rule = MeanFlowFixedStrengthRule()
    with pytest.raises(FrozenInstanceError):
        rule.fallback = 0.99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# (31) P-19 #4 — BoundedMergeFloorRule (named provenance for e_rho / 4)
# ---------------------------------------------------------------------------


def test_bounded_merge_floor_closed_form() -> None:
    """BoundedMergeFloorRule returns ``e_rho / 4`` (or divisor fallback)."""
    rule = BoundedMergeFloorRule()
    # e_rho = 0.04 -> floor = 0.01.
    ctx = make_derivation_context(e_rho=0.04)
    assert rule(ctx) == pytest.approx(0.01, abs=1e-15)
    # Missing e_rho -> divisor (4.0) as named provenance.
    assert rule(make_derivation_context()) == pytest.approx(
        PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR, abs=1e-12
    )


def test_bounded_merge_floor_invalid_inputs_raise() -> None:
    """Negative ``e_rho`` raises ``ValueError``."""
    rule = BoundedMergeFloorRule()
    with pytest.raises(ValueError):
        rule(make_derivation_context(e_rho=-0.01))


# ---------------------------------------------------------------------------
# (32) Frozen dataclass + provenance for the 18 new rules
# ---------------------------------------------------------------------------


def test_all_18_new_rules_are_frozen_dataclasses() -> None:
    """All 18 new concrete rules are frozen dataclasses."""
    rule_classes = [
        MeanFlowToleranceRule,
        MachineEpsilonRule,
        EMAInverseVarianceRule,
        LipschitzTemperatureRule,
        MinGumbelTempRule,
        EpsLogRule,
        ExponentialAlphaRule,
        PolynomialPowerRule,
        SigmoidMidpointSteepnessRule,
        ConvergenceAdaptivePolyRule,
        MetricWeightRule,
        VariancePreservingJitterRule,
        MidpointBetaRule,
        BoundaryConditionRule,
        MeanFlowFixedStrengthRule,
        BoundedMergeFloorRule,
    ]
    assert len(rule_classes) == 16, (
        "Expected 16 new concrete rules; got "
        f"{len(rule_classes)}"
    )
    for cls in rule_classes:
        rule = cls()
        assert isinstance(rule, DerivationRule)
        assert isinstance(cls.derivation_source, str)
        assert cls.derivation_source
        assert isinstance(cls.derivation_formula, str)
        assert cls.derivation_formula
        assert isinstance(cls.academic_precedent, tuple)
        assert len(cls.academic_precedent) >= 1
        with pytest.raises(FrozenInstanceError):
            rule.derivation_source = "other"  # type: ignore[misc]


def test_all_18_new_rules_have_required_fields() -> None:
    """All 18 new concrete rules declare non-empty ``required_fields``.

    Theorem-fixed rules (#2, #4, #5) have empty ``required_fields``
    by design — they do not read context. Every other rule declares
    its inputs explicitly so the dispatcher can route correctly.
    """
    rule_classes = [
        MeanFlowToleranceRule,
        MachineEpsilonRule,
        EMAInverseVarianceRule,
        LipschitzTemperatureRule,
        MinGumbelTempRule,
        EpsLogRule,
        ExponentialAlphaRule,
        PolynomialPowerRule,
        SigmoidMidpointSteepnessRule,
        ConvergenceAdaptivePolyRule,
        MetricWeightRule,
        VariancePreservingJitterRule,
        MidpointBetaRule,
        BoundaryConditionRule,
        MeanFlowFixedStrengthRule,
        BoundedMergeFloorRule,
    ]
    for cls in rule_classes:
        assert isinstance(cls.required_fields, tuple)
        # Each non-theorem-fixed rule must declare its required
        # fields; theorem-fixed rules (#2, #5) declare empty tuple.
        if cls in (BoundaryConditionRule, MeanFlowFixedStrengthRule):
            assert cls.required_fields == ()
        else:
            assert len(cls.required_fields) >= 1


def test_all_18_new_rules_are_in_module_all() -> None:
    """The 16 new concrete rules are exposed via ``__all__``.

    Plus the 16 corresponding default_* factory functions.
    """
    from adaptive_reflow.algorithm import _derivation

    expected = {
        "BoundaryConditionRule",
        "BoundedMergeFloorRule",
        "ConvergenceAdaptivePolyRule",
        "EMAInverseVarianceRule",
        "EpsLogRule",
        "ExponentialAlphaRule",
        "LipschitzTemperatureRule",
        "MachineEpsilonRule",
        "MeanFlowFixedStrengthRule",
        "MeanFlowToleranceRule",
        "MetricWeightRule",
        "MidpointBetaRule",
        "MinGumbelTempRule",
        "PolynomialPowerRule",
        "SigmoidMidpointSteepnessRule",
        "VariancePreservingJitterRule",
    }
    for name in expected:
        assert name in _derivation.__all__, (
            f"_derivation.__all__ missing {name!r}"
        )
        assert hasattr(_derivation, name), (
            f"_derivation has no attribute {name!r}"
        )


def test_all_18_new_dispatchers_are_importable() -> None:
    """The new ``default_*`` factory functions are exposed."""
    from adaptive_reflow.algorithm import _derivation

    expected = {
        "default_tolerance",
        "default_machine_eps",
        "default_ema_alpha",
        "default_distance_decay_temperature",
        "default_min_gumbel_temp",
        "default_eps_log",
        "default_exponential_alpha",
        "default_polynomial_power",
        "default_sigmoid_midpoint",
        "default_sigmoid_steepness",
        "default_convergence_adaptive_kp",
        "default_convergence_adaptive_kd",
        "default_convergence_adaptive_shift_max",
        "default_convergence_adaptive_ema",
        "default_metric_weights",
        "default_jitter_std",
        "default_constant_beta",
        "default_adaptive_target_estimate",
    }
    for name in expected:
        assert name in _derivation.__all__, (
            f"_derivation.__all__ missing {name!r}"
        )
        assert hasattr(_derivation, name), (
            f"_derivation has no attribute {name!r}"
        )
