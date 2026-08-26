"""Channel-level dynamic shrinkage rule for the adaptive_reflow component (DTB-R2).

Pure, deterministic per-channel rule. Maps :class:`ChannelRuleInputs` (a
typed source bundle, per-channel evidence, phase state, schedule and cap
fields) to a :class:`ChannelTransferDecision` plus a thin
:class:`ChannelRuleOutputs` wrapper.

Hard rules (each one is a fail-closed gate; ``gate=False`` if any fires):

* ``tail_admissibility`` is ``False`` (DTB-NC2)
* ``complement_excluded`` is ``True`` (DTB-NC1)
* ``proxy_only_evidence`` is ``True`` (cannot satisfy calibration_lower_bound)
* ``horizon_coverage_proven`` is ``False`` (artifact does not cover the
  current target horizon H)
* ``finite_prefix_only`` is ``False``
* ``frozen_envelope_manifest_hash`` is ``None`` when
  ``finite_prefix_only`` is ``True``
* any required evidence factor is ``None``, non-finite, or outside
  ``[0, 1]``

Evidence score (``e(b, c)``):

    e = calibration_lower_bound
      * perturbation_stability_lower_bound
      * support_coverage
      * (1 - ambiguity)
      * (1 - degeneracy_penalty)
      * recency_decay

All six factors live in ``[0, 1]``; the product is clamped to ``[0, 1]`` to
defend against float roundoff in the inverted factors.

Memory coefficient:

    raw_target[c] = mixing_cap * scheduled_cap * e
    bounded_target_fraction = clamp(raw_target,
                                    max(0, prev - delta_cap_down),
                                    min(1, prev + delta_cap_up))
    beta  = bounded_target_fraction
    alpha = 1 - beta

``prev`` is the schedule's intended value for this round
(``scheduled_cap``); the fresh-noise floor is exposed as a separate output
field rather than applied to the bounded update.

The rule is a pure function: no I/O, no mutation of ``inputs`` or any
other state, no global state. The same ``ChannelRuleInputs`` always
yields the same ``ChannelRuleOutputs``.
"""

from __future__ import annotations

import math

from adaptive_reflow.contracts import (
    AUDIT_SOURCE_REVOKED,
    ChannelRuleInputs,
    ChannelRuleOutputs,
    ChannelTransferDecision,
    FactorValue,
)

# ---------------------------------------------------------------------------
# Canonical factor order and cap/floor field names
# ---------------------------------------------------------------------------

# Canonical factor order for the evidence score formula. The
# ``raw_factors`` tuple in :class:`ChannelTransferDecision` is built from
# these names, in this order, so tests and validators can index into it
# deterministically. The order matches the order in which factors appear
# in the formula:
#   e = calibration_lower_bound
#     * perturbation_stability_lower_bound
#     * support_coverage
#     * (1 - ambiguity)
#     * (1 - degeneracy_penalty)
#     * recency_decay
CANONICAL_FACTOR_ORDER: tuple[str, ...] = (
    "calibration_lower_bound",
    "perturbation_stability_lower_bound",
    "support_coverage",
    "ambiguity",
    "degeneracy_penalty",
    "recency_decay",
)

# Cap / floor / delta-cap fields that must also be in ``[0, 1]`` for the
# rule to be admissible. They live outside the evidence-score formula but
# are still required to be valid for the rule to produce a non-zero beta.
_CAP_FLOOR_FIELDS: tuple[str, ...] = (
    "mixing_cap",
    "scheduled_cap",
    "fresh_noise_floor",
    "delta_cap_up",
    "delta_cap_down",
)


# ---------------------------------------------------------------------------
# Canonical blocker codes (deterministic, no spaces, ASCII only)
# ---------------------------------------------------------------------------

BLOCKER_TAIL_INADMISSIBLE = "tail_inadmissible"
BLOCKER_COMPLEMENT_EXCLUDED = "complement_excluded"
BLOCKER_PROXY_ONLY = "proxy_only_cannot_satisfy_calibration"
BLOCKER_HORIZON_UNPROVEN = "horizon_coverage_unproven"
BLOCKER_NOT_FINITE_PREFIX = "not_finite_prefix_only"
BLOCKER_ENVELOPE_HASH_MISSING = "frozen_envelope_manifest_hash_required"
BLOCKER_MISSING_FACTOR = "required_factor_missing"
BLOCKER_NON_FINITE = "required_factor_not_real"
BLOCKER_NAN_OR_INF = "required_factor_not_finite"
BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL = "required_factor_out_of_unit_interval"


# ---------------------------------------------------------------------------
# DTB-R0 §3 case 2 — stability-collapse gate closure
# ---------------------------------------------------------------------------
#: Module-level constant (public). ``perturbation_stability_lower_bound``
#: values strictly below this floor close the gate and emit
#: ``AUDIT_STABILITY_COLLAPSE`` in the audit trail. The value is the
#: canonical DTB-R0 §3 floor; ``compute_channel_decision`` does not
#: silently override it.
PERTURBATION_STABILITY_FLOOR: float = 0.5

#: Audit reason emitted when the channel rule closes the gate because
#: ``perturbation_stability_lower_bound < PERTURBATION_STABILITY_FLOOR``
#: (DTB-R0 §3 case 2 — monotonic-uncertainty / cross-seed instability).
#: The string is stable, lowercase snake-case, no spaces, and is used
#: verbatim in :attr:`ChannelTransferDecision.audit_reason`.
AUDIT_STABILITY_COLLAPSE: str = "perturbation_stability_below_threshold"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_factor(x: object) -> float:
    """Coerce a ``FactorValue``-like to a Python ``float``.

    Booleans are treated as integers (``True`` = 1, ``False`` = 0).
    Anything else that is not a real number raises ``TypeError`` so the
    caller can surface a deterministic blocker code.
    """
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise TypeError(f"expected a real number, got {type(x).__name__}")
    return float(x)


def required_factors_in_unit_interval(
    inputs: ChannelRuleInputs,
) -> tuple[str, ...]:
    """Return the tuple of evidence factor names that fail the ``[0, 1]`` check.

    The check covers the six canonical evidence factors (see
    :data:`CANONICAL_FACTOR_ORDER`):

    * non-``None`` (a ``None`` value counts as missing)
    * finite (no ``NaN``, no ``inf``/``-inf``)
    * in the closed interval ``[0, 1]``

    The returned names appear in the canonical factor order so callers can
    compare against a stable reference. The cap / floor / delta-cap fields
    are deliberately not in this set; the rule treats them as a separate
    validation step so the helper can serve as a focused public utility.
    """
    failed: list[str] = []
    for name in CANONICAL_FACTOR_ORDER:
        value = getattr(inputs, name, None)
        if value is None:
            failed.append(name)
            continue
        try:
            f = _coerce_factor(value)
        except (TypeError, ValueError):
            failed.append(name)
            continue
        if not math.isfinite(f):
            failed.append(name)
            continue
        if f < 0.0 or f > 1.0:
            failed.append(name)
    return tuple(failed)


def _classify_failed_factor(name: str, value: object) -> str:
    """Map a single failed factor to its canonical blocker-code suffix."""
    if value is None:
        return f"{BLOCKER_MISSING_FACTOR}:{name}"
    try:
        f = _coerce_factor(value)
    except (TypeError, ValueError):
        return f"{BLOCKER_NON_FINITE}:{name}"
    if not math.isfinite(f):
        return f"{BLOCKER_NAN_OR_INF}:{name}"
    return f"{BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL}:{name}"


def _collect_blockers(inputs: ChannelRuleInputs) -> tuple[str, ...]:
    """Compute the canonical, deterministic blocker tuple for ``inputs``.

    Blockers are appended in a fixed order so the resulting tuple is
    byte-stable across runs. Per-factor failures carry the field name as
    a ``":"`` suffix.
    """
    blockers: list[str] = []

    # 1. tail admissibility (DTB-NC2).
    if not inputs.tail_admissibility:
        blockers.append(BLOCKER_TAIL_INADMISSIBLE)

    # 2. complement exclusion (DTB-NC1).
    if inputs.complement_excluded:
        blockers.append(BLOCKER_COMPLEMENT_EXCLUDED)

    # 3. proxy-only evidence cannot satisfy calibration_lower_bound.
    if inputs.evidence.proxy_only_evidence:
        blockers.append(BLOCKER_PROXY_ONLY)

    # 4. horizon coverage (DTB-L1). ``horizon_coverage_proven`` already
    #    encodes "artifact covers the current H" — if it is ``False`` the
    #    rule must fail closed.
    if not inputs.horizon_coverage_proven:
        blockers.append(BLOCKER_HORIZON_UNPROVEN)

    # 5. finite prefix only.
    if not inputs.finite_prefix_only:
        blockers.append(BLOCKER_NOT_FINITE_PREFIX)

    # 6. envelope manifest hash presence.
    if inputs.finite_prefix_only and inputs.frozen_envelope_manifest_hash is None:
        blockers.append(BLOCKER_ENVELOPE_HASH_MISSING)

    # 7. Required evidence factors (the six in CANONICAL_FACTOR_ORDER).
    for name in required_factors_in_unit_interval(inputs):
        blockers.append(_classify_failed_factor(name, getattr(inputs, name, None)))

    # 8. Cap / floor / delta-cap fields. They are not part of the
    #    evidence score but must be valid real numbers in ``[0, 1]`` for
    #    the rule to run.
    for name in _CAP_FLOOR_FIELDS:
        value = getattr(inputs, name, None)
        if value is None:
            blockers.append(f"{BLOCKER_MISSING_FACTOR}:{name}")
            continue
        try:
            f = _coerce_factor(value)
        except (TypeError, ValueError):
            blockers.append(f"{BLOCKER_NON_FINITE}:{name}")
            continue
        if not math.isfinite(f):
            blockers.append(f"{BLOCKER_NAN_OR_INF}:{name}")
        elif f < 0.0 or f > 1.0:
            blockers.append(f"{BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL}:{name}")

    return tuple(blockers)


def _compute_evidence_score(inputs: ChannelRuleInputs) -> float:
    """Compute the evidence score ``e(b, c)``.

    The product of all six factors, each in ``[0, 1]``. The result is
    clamped to ``[0, 1]`` to defend against float roundoff in the
    inverted factors.
    """
    calib = _coerce_factor(inputs.calibration_lower_bound)
    stability = _coerce_factor(inputs.perturbation_stability_lower_bound)
    support = _coerce_factor(inputs.support_coverage)
    ambiguity = _coerce_factor(inputs.ambiguity)
    degeneracy = _coerce_factor(inputs.degeneracy_penalty)
    recency = _coerce_factor(inputs.recency_decay)

    one_minus_ambiguity = max(0.0, min(1.0, 1.0 - ambiguity))
    one_minus_degeneracy = max(0.0, min(1.0, 1.0 - degeneracy))

    score = (
        calib
        * stability
        * support
        * one_minus_ambiguity
        * one_minus_degeneracy
        * recency
    )
    return max(0.0, min(1.0, score))


def _bounded_target_fraction(
    raw_target: float,
    prev: float,
    delta_cap_up: float,
    delta_cap_down: float,
) -> float:
    """Apply the symmetric bounded update.

    Returns ``raw_target`` clamped to the interval
    ``[max(0, prev - delta_cap_down), min(1, prev + delta_cap_up)]``. If
    the two bounds cross (an adversarial cap configuration) the function
    returns ``0.0`` rather than emit an empty interval; the rule must
    remain pure and finite.
    """
    lo = max(0.0, prev - max(0.0, delta_cap_down))
    hi = min(1.0, prev + max(0.0, delta_cap_up))
    if hi < lo:
        return 0.0
    return max(lo, min(hi, raw_target))


def _raw_factors_tuple(inputs: ChannelRuleInputs) -> tuple[FactorValue, ...]:
    """Build the canonical ``raw_factors`` tuple from the six evidence factors.

    Malformed entries are encoded as ``NaN`` so the audit row keeps a
    six-tuple shape; the gate has already failed in that case and the
    consumer is expected to consult ``blocker_codes`` for the cause.
    """
    values: list[float] = []
    for name in CANONICAL_FACTOR_ORDER:
        value = getattr(inputs, name, None)
        if value is None:
            values.append(float("nan"))
            continue
        try:
            values.append(_coerce_factor(value))
        except (TypeError, ValueError):
            values.append(float("nan"))
    return tuple(FactorValue(float(v)) for v in values)


def _audit_reason_for(blockers: tuple[str, ...]) -> str:
    """Render a deterministic ``audit_reason`` string from ``blockers``."""
    if not blockers:
        return "ok"
    return ";".join(blockers)


def _stability_floor_breached(inputs: ChannelRuleInputs) -> bool:
    """Return True iff ``perturbation_stability_lower_bound`` is below the floor.

    DTB-R0 §3 case 2: a point estimate that looks confident but whose
    ``perturbation_stability_lower_bound`` collapses on seed / condition
    perturbation must close the gate regardless of the raw score. The
    floor is the module-level constant :data:`PERTURBATION_STABILITY_FLOOR`.

    Non-finite values (``NaN``, ``+/-inf``) are treated as "below the
    floor" so the fail-closed branch is also exercised on adversarial
    inputs. ``None`` is treated as missing and also breaches the floor
    (the rule already surfaces the more specific missing-factor blocker
    via :func:`_collect_blockers`; this helper exists to gate the
    collapse decision specifically on the numeric comparison).
    """
    value = inputs.perturbation_stability_lower_bound
    if value is None:
        return True
    try:
        f = _coerce_factor(value)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(f):
        return True
    return float(f) < float(PERTURBATION_STABILITY_FLOOR)


def _build_stability_collapse_outputs(
    inputs: ChannelRuleInputs,
    raw_factors: tuple[FactorValue, ...],
) -> ChannelRuleOutputs | None:
    """Return a fail-closed :class:`ChannelRuleOutputs` on stability collapse.

    Returns ``None`` when ``inputs.perturbation_stability_lower_bound``
    is at or above :data:`PERTURBATION_STABILITY_FLOOR` so the caller
    can fall through to the normal gate-evaluation branch. Otherwise it
    builds the same shape as a normal fail-closed decision (``gate=False``,
    ``beta=0``, ``alpha=1``, ``bounded_target_fraction=0``,
    ``evidence_score=0``) but threads :data:`AUDIT_STABILITY_COLLAPSE`
    through ``audit_reason`` and ``blocker_codes`` so the audit trail
    names the DTB-R0 §3 cause explicitly.
    """
    if not _stability_floor_breached(inputs):
        return None

    # All cap / floor fields have already passed validation in
    # _collect_blockers, so coercion is safe here.
    scheduled_cap = _coerce_factor(inputs.scheduled_cap)
    fresh_noise_floor = _coerce_factor(inputs.fresh_noise_floor)

    decision = ChannelTransferDecision(
        bundle_id=inputs.bundle.bundle_id,
        channel=inputs.evidence.channel,
        gate=False,
        raw_factors=raw_factors,
        evidence_score=FactorValue(0.0),
        scheduled_cap=FactorValue(float(scheduled_cap)),
        bounded_target_fraction=FactorValue(0.0),
        fresh_noise_floor=FactorValue(float(fresh_noise_floor)),
        alpha=FactorValue(1.0),
        beta=FactorValue(0.0),
        audit_reason=AUDIT_STABILITY_COLLAPSE,
        blocker_codes=(AUDIT_STABILITY_COLLAPSE,),
    )
    return ChannelRuleOutputs(
        decision=decision,
        monotonicity_check_passed=False,
        validation_errors=(AUDIT_STABILITY_COLLAPSE,),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_channel_decision(
    inputs: ChannelRuleInputs,
) -> ChannelRuleOutputs:
    """Compute the per-channel decision for ``inputs``.

    Pure function. No I/O, no mutation of ``inputs`` or any other state,
    no global state. The output is built deterministically from the
    inputs and the canonical factor order.

    When the gate is closed (any blocker present) the decision carries
    ``beta=0``, ``alpha=1``, ``bounded_target_fraction=0`` and
    ``evidence_score=0`` per the brief, and ``blocker_codes`` lists the
    precise reason. When the gate is open, ``alpha = 1 - beta`` is a
    label-only invariant for the mixer primitive (no physical variance
    equality is assumed).

    DTB-R0 §3 case 2 — stability-collapse gate closure runs *before*
    the generic blocker collection: a
    ``perturbation_stability_lower_bound`` strictly below
    :data:`PERTURBATION_STABILITY_FLOOR` closes the gate with the
    dedicated ``AUDIT_STABILITY_COLLAPSE`` audit code regardless of
    the rest of the evidence.
    """
    raw_factors = _raw_factors_tuple(inputs)

    # DTB-R0 §3 case 2: stability-collapse short-circuit. A confidence
    # estimate that collapses on seed / condition perturbation must
    # close the gate even when every other factor looks fine. This
    # branch deliberately runs before the generic blocker collection
    # so the audit trail surfaces the dedicated audit code.
    stability_collapse = _build_stability_collapse_outputs(inputs, raw_factors)
    if stability_collapse is not None:
        return stability_collapse

    blockers = _collect_blockers(inputs)
    gate = len(blockers) == 0

    # All cap / floor fields have already passed the validation in
    # _collect_blockers, so coercion is safe here.
    mixing_cap = _coerce_factor(inputs.mixing_cap)
    scheduled_cap = _coerce_factor(inputs.scheduled_cap)
    fresh_noise_floor = _coerce_factor(inputs.fresh_noise_floor)
    delta_cap_up = _coerce_factor(inputs.delta_cap_up)
    delta_cap_down = _coerce_factor(inputs.delta_cap_down)

    if not gate:
        decision = ChannelTransferDecision(
            bundle_id=inputs.bundle.bundle_id,
            channel=inputs.evidence.channel,
            gate=False,
            raw_factors=raw_factors,
            evidence_score=FactorValue(0.0),
            scheduled_cap=FactorValue(float(scheduled_cap)),
            bounded_target_fraction=FactorValue(0.0),
            fresh_noise_floor=FactorValue(float(fresh_noise_floor)),
            alpha=FactorValue(1.0),
            beta=FactorValue(0.0),
            audit_reason=_audit_reason_for(blockers),
            blocker_codes=blockers,
        )
        return ChannelRuleOutputs(
            decision=decision,
            monotonicity_check_passed=False,
            validation_errors=blockers,
        )

    evidence_score = _compute_evidence_score(inputs)
    raw_target = max(0.0, min(1.0, mixing_cap * scheduled_cap * evidence_score))
    bounded = _bounded_target_fraction(
        raw_target=raw_target,
        prev=scheduled_cap,
        delta_cap_up=delta_cap_up,
        delta_cap_down=delta_cap_down,
    )

    beta = bounded
    alpha = 1.0 - beta

    decision = ChannelTransferDecision(
        bundle_id=inputs.bundle.bundle_id,
        channel=inputs.evidence.channel,
        gate=True,
        raw_factors=raw_factors,
        evidence_score=FactorValue(float(evidence_score)),
        scheduled_cap=FactorValue(float(scheduled_cap)),
        bounded_target_fraction=FactorValue(float(bounded)),
        fresh_noise_floor=FactorValue(float(fresh_noise_floor)),
        alpha=FactorValue(float(alpha)),
        beta=FactorValue(float(beta)),
        audit_reason="ok",
        blocker_codes=(),
    )
    return ChannelRuleOutputs(
        decision=decision,
        monotonicity_check_passed=True,
        validation_errors=(),
    )


def evaluate_channel_evidence_with_revocation(
    inputs: ChannelRuleInputs,
) -> ChannelRuleOutputs:
    """Channel-rule wrapper that enforces source-bundle revocation (DTB-R0 §3 case 5).

    This is the canonical entry point for callers that want the channel
    rule's fail-closed behaviour on ``inputs.bundle.revoked == True``.
    When the source bundle has been revoked after registration (e.g.
    evaluator provenance retracted), the gate MUST close with
    ``gate=False``, ``beta=0.0``, ``alpha=1.0`` and the audit reason
    MUST carry :data:`AUDIT_SOURCE_REVOKED`. The check runs before
    :func:`compute_channel_decision` so the revocation audit trail is
    not polluted by downstream blockers.

    When the bundle is not revoked, this function delegates to
    :func:`compute_channel_decision` and returns its output verbatim
    (so the wrapper is transparent for the happy path).

    The function is pure: no I/O, no mutation of ``inputs``, no global
    state. The same ``ChannelRuleInputs`` always yields the same
    ``ChannelRuleOutputs``.
    """
    bundle = inputs.bundle
    revoked = bool(getattr(bundle, "revoked", False))
    raw_factors = _raw_factors_tuple(inputs)

    if revoked:
        # Coerce cap / floor fields if present; fall back to 0.0 when
        # the inputs are partially malformed so the audit surface
        # remains finite. The downstream consumer is expected to consult
        # ``audit_reason`` for the precise cause.
        try:
            scheduled_cap = _coerce_factor(inputs.scheduled_cap)
        except (TypeError, ValueError):
            scheduled_cap = 0.0
        try:
            fresh_noise_floor = _coerce_factor(inputs.fresh_noise_floor)
        except (TypeError, ValueError):
            fresh_noise_floor = 0.0

        decision = ChannelTransferDecision(
            bundle_id=inputs.bundle.bundle_id,
            channel=inputs.evidence.channel,
            gate=False,
            raw_factors=raw_factors,
            evidence_score=FactorValue(0.0),
            scheduled_cap=FactorValue(float(scheduled_cap)),
            bounded_target_fraction=FactorValue(0.0),
            fresh_noise_floor=FactorValue(float(fresh_noise_floor)),
            alpha=FactorValue(1.0),
            beta=FactorValue(0.0),
            audit_reason=AUDIT_SOURCE_REVOKED,
            blocker_codes=(AUDIT_SOURCE_REVOKED,),
        )
        return ChannelRuleOutputs(
            decision=decision,
            monotonicity_check_passed=False,
            validation_errors=(AUDIT_SOURCE_REVOKED,),
        )

    return compute_channel_decision(inputs)


def check_monotonicity_property(
    family: str,
    baseline: ChannelRuleInputs,
    perturbed: ChannelRuleInputs,
) -> bool:
    """Verify the expected monotonicity direction for ``family``.

    Supported families:

    * ``"stability_up"`` — increase ``calibration_lower_bound`` or
      ``perturbation_stability_lower_bound`` (others fixed) ->
      non-decreasing ``beta`` (``perturbed >= baseline``).
    * ``"uncertainty_up"`` — increase ``ambiguity`` or
      ``degeneracy_penalty`` (others fixed) -> non-increasing ``beta``
      (``perturbed <= baseline``).
    * ``"support_down"`` — decrease ``support_coverage`` (others fixed)
      -> non-increasing ``beta`` (``perturbed <= baseline``).
    * ``"age_up"`` — decrease ``recency_decay`` (others fixed) ->
      non-increasing ``beta`` (``perturbed <= baseline``).

    The function is a test utility. It returns ``True`` iff the invariant
    holds for the two resulting decisions, with a tiny float tolerance
    to absorb harmless roundoff. The gate status of either decision is
    not used to short-circuit; monotonicity is over the resulting
    ``beta`` values directly (both may be zero).
    """
    base_out = compute_channel_decision(baseline).decision
    pert_out = compute_channel_decision(perturbed).decision
    base_beta = float(base_out.beta)
    pert_beta = float(pert_out.beta)
    tol = 1e-12

    if family == "stability_up":
        return pert_beta >= base_beta - tol
    if family == "uncertainty_up":
        return pert_beta <= base_beta + tol
    if family == "support_down":
        return pert_beta <= base_beta + tol
    if family == "age_up":
        return pert_beta <= base_beta + tol
    raise ValueError(f"unknown monotonicity family: {family!r}")


__all__ = [
    # DTB-R0 §3 case 2 audit / floor constants (must stay before BLOCKER_*).
    "AUDIT_STABILITY_COLLAPSE",
    "PERTURBATION_STABILITY_FLOOR",
    # DTB-R0 §3 case 5 audit (re-exported from contracts).
    "AUDIT_SOURCE_REVOKED",
    "BLOCKER_COMPLEMENT_EXCLUDED",
    "BLOCKER_ENVELOPE_HASH_MISSING",
    "BLOCKER_FACTOR_OUT_OF_UNIT_INTERVAL",
    "BLOCKER_HORIZON_UNPROVEN",
    "BLOCKER_MISSING_FACTOR",
    "BLOCKER_NAN_OR_INF",
    "BLOCKER_NON_FINITE",
    "BLOCKER_NOT_FINITE_PREFIX",
    "BLOCKER_PROXY_ONLY",
    # Blocker codes
    "BLOCKER_TAIL_INADMISSIBLE",
    # Canonical factor order (used by raw_factors indexing)
    "CANONICAL_FACTOR_ORDER",
    "check_monotonicity_property",
    # Public API
    "compute_channel_decision",
    "evaluate_channel_evidence_with_revocation",
    "required_factors_in_unit_interval",
]
