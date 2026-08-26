"""Hypothesis strategies for property-based tests of adaptive_reflow.

The strategies are designed to satisfy the pre-conditions of the
adaptive_reflow contracts so that :func:`hypothesis.given` test bodies
can call public functions directly without additional ``assume()``
filtering. They are deliberately *small* (the cap / floor envelope is
``[0, 1]``) so the test budgets stay bounded.

**Import discipline**: the module deliberately defers every
``adaptive_reflow`` import to the inside of the strategy / helper
functions. The package contains a
``contracts`` ↔ ``molecular`` import cycle that the
:mod:`adaptive_reflow.molecular.__init__` resolver breaks only when
``adaptive_reflow.contracts`` is *fully* loaded. Importing
``adaptive_reflow.contracts`` at the top of this conftest re-enters
that cycle and aborts collection. Strategies are invoked lazily by
hypothesis, so a deferred import inside the function body resolves
the cycle.

Stdlib-only — no torch.
"""
from __future__ import annotations

import math
import string
from collections.abc import Mapping
from typing import Any

from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Floats in the canonical envelopes
# ---------------------------------------------------------------------------

#: Finite ``float`` in the closed interval ``[0, 1]``. No NaN, no inf,
#: no negative; ``allow_nan=False`` is set so Hypothesis never produces
#: non-finite values here.
unit_floats = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)

#: Finite ``float`` in the *strict* interval ``(0, 1)`` (no 0.0, no 1.0).
#: Used for tests that need to perturb a value in a guaranteed
#: non-degenerate way (e.g. monotonicity with "increase" semantics).
unit_floats_strict = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
).filter(lambda x: 0.0 < float(x) < 1.0)

#: Finite ``float`` in ``[0, 1]`` for the prev / dynamic arguments of
#: the bounded merge. Includes 0.0 and 1.0 so we can exercise the
#: envelope boundaries.
prev_dynamic_floats = unit_floats

#: Finite ``float`` in ``[0, 1]`` for delta caps. Includes 0.0 so the
#: empty-interval collapse path is exercised.
delta_cap_floats = unit_floats

#: Finite ``float`` in ``[0, 1]`` for floor values. Includes 0.0.
floor_floats = unit_floats

#: Finite ``float`` in ``[0, 1]`` for cap values. Includes 1.0.
cap_floats = unit_floats

#: ``cap`` value paired with a ``floor <= cap`` to guarantee the
#: bounded-merge envelope is well-formed.
cap_with_floor = st.tuples(floor_floats, cap_floats).map(
    lambda pair: (min(pair[0], pair[1]), max(pair[0], pair[1]))
)

# ---------------------------------------------------------------------------
# Booleans / ints / types for validator tests
# ---------------------------------------------------------------------------

#: ``bool`` strategy (only True / False).
booleans = st.booleans()

#: Small non-negative ints (covers the validator domain for
#: positive / non-negative ints).
nonneg_small_ints = st.integers(min_value=0, max_value=100)

#: Small positive ints (>= 1) for ``validate_positive_int``.
positive_small_ints = st.integers(min_value=1, max_value=100)

#: Negative ints for the rejection paths.
negative_ints = st.integers(max_value=-1)

#: Non-numeric types to feed the validators.
non_numeric_types = st.sampled_from(
    [None, "0.5", "1", "0", [], {}, object(), b"0.5"]
)

# ---------------------------------------------------------------------------
# Bool coercion inputs
# ---------------------------------------------------------------------------

#: Booleans only, used for the bool-coercion property test.
bool_only = st.booleans()

# ---------------------------------------------------------------------------
# Non-finite float inputs (fail-closed path)
# ---------------------------------------------------------------------------

#: ``NaN`` and ``+/- inf`` as Python floats (Hypothesis can generate
#: these directly when ``allow_nan=True``).
non_finite_floats = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=True,
    allow_infinity=True,
).filter(lambda x: not math.isfinite(float(x)))

# ---------------------------------------------------------------------------
# Claim-gate evidence helpers
# ---------------------------------------------------------------------------

#: A short ASCII label used to build stable channel / bundle identifiers.
_label_chars = string.ascii_lowercase
_short_label = st.text(alphabet=_label_chars, min_size=1, max_size=8)

#: A boolean indicating whether a contract passed (the value of
#: ``evidence[contract_id]["passed"]``).
contract_passed = st.booleans()

#: Tuples of contract names used to build a ``required_contracts_passing``
#: config. Each contract name is a short ASCII label.
contract_id_tuples = st.lists(
    elements=_short_label,
    min_size=0,
    max_size=4,
    unique=True,
).map(tuple)

#: A confidence-interval coverage in ``[0, 1]``.
ci_coverage = unit_floats

#: A required paired evidence count (>= 0).
paired_counts = nonneg_small_ints

#: An evaluation-window length (>= 0).
window_lengths = nonneg_small_ints

#: Whether the gate is enabled.
gate_enabled = st.booleans()

#: Evaluated-at-round value (>= 0).
round_values = nonneg_small_ints

# ---------------------------------------------------------------------------
# Generic evidence factors (six-tuple of distinct unit-interval floats)
# ---------------------------------------------------------------------------


@st.composite
def st_factors(draw: Any) -> tuple[float, float, float, float, float, float]:
    """Return a tuple of 6 distinct finite floats in ``[0, 1]``.

    Distinctness is required so the canonical factor index can be
    perturbed in tests that compare factor ordering. ``allow_nan=False``
    is enforced at the strategy layer.
    """
    return draw(
        st.lists(
            elements=unit_floats,
            min_size=6,
            max_size=6,
            unique=True,
        ).map(tuple)
    )


@st.composite
def st_factor_six(draw: Any) -> tuple[float, float, float, float, float, float]:
    """Return a tuple of 6 finite floats in ``[0, 1]`` (no distinctness)."""
    return draw(st.tuples(*([unit_floats] * 6)))


# ---------------------------------------------------------------------------
# Lazy accessors for adaptive_reflow types
# ---------------------------------------------------------------------------
# Importing ``adaptive_reflow.contracts`` at module top-level re-enters
# the ``contracts`` ↔ ``molecular`` cycle and aborts pytest collection.
# The accessor below is invoked only when a strategy needs the actual
# dataclass, so the import happens after ``adaptive_reflow.contracts``
# has fully loaded (e.g. inside a test body or fixture).


def _contracts_types() -> tuple[type, ...]:
    """Return the tuple of dataclasses needed by the heavy strategies.

    Imported lazily on first access.
    """
    from adaptive_reflow.contracts import (  # noqa: PLC0415 - lazy import
        ArtifactHash,
        BundleId,
        ChannelName,
        ChannelRuleInputs,
        ChannelTransferEvidence,
        ProvenanceChain,
        RoundResultBundle,
        RunId,
        SampleId,
        TraceDigest,
    )

    return (
        ArtifactHash,
        BundleId,
        ChannelName,
        ChannelRuleInputs,
        ChannelTransferEvidence,
        ProvenanceChain,
        RoundResultBundle,
        RunId,
        SampleId,
        TraceDigest,
    )


def _hash_helpers() -> tuple[Any, Any]:
    """Return ``(hash_artifact, hash_trace_digest)`` lazily."""
    from adaptive_reflow.contracts import (  # noqa: PLC0415 - lazy import
        hash_artifact,
        hash_trace_digest,
    )

    return hash_artifact, hash_trace_digest


def _phase_state_factory() -> Any:
    """Return ``make_default_phase_state`` lazily."""
    from adaptive_reflow.contracts import (  # noqa: PLC0415 - lazy import
        make_default_phase_state,
    )

    return make_default_phase_state


def _claim_gate_helpers() -> tuple[type, Any]:
    """Return ``(ClaimGateConfig, build_default_claim_gate_config)`` lazily."""
    from adaptive_reflow.eval import (  # noqa: PLC0415 - lazy import
        ClaimGateConfig,
        build_default_claim_gate_config,
    )

    return ClaimGateConfig, build_default_claim_gate_config


# ---------------------------------------------------------------------------
# Internal bundle / evidence builders
# ---------------------------------------------------------------------------


def _make_bundle(source_round: int) -> Any:
    """Build a minimal, valid :class:`RoundResultBundle` for tests."""
    (
        ArtifactHash,
        BundleId,
        _ChannelName_unused,
        _ChannelRuleInputs_unused,
        _ChannelTransferEvidence_unused,
        ProvenanceChain,
        RoundResultBundle,
        RunId,
        SampleId,
        TraceDigest,
    ) = _contracts_types()
    _hash_artifact, hash_trace_digest = _hash_helpers()
    bundle_id = f"bundle-{source_round}"
    trace = TraceDigest(
        hash_trace_digest(
            BundleId(bundle_id),
            int(source_round),
            1,
            RunId("run-prop"),
            SampleId("sample-prop"),
        )
    )
    return RoundResultBundle(
        bundle_id=BundleId(bundle_id),
        source_round=int(source_round),
        round_count=1,
        run_id=RunId("run-prop"),
        sample_id=SampleId("sample-prop"),
        trace_digest=trace,
        condition_digest=TraceDigest(""),
        feedback_mode="inference_external_diagnostic",
        calibration_artifact_hash=ArtifactHash("calibration-prop"),
        state_lock_is_detached=True,
        update_scope="ode_restart_distribution_only",
        coordinate_channel={
            "source_round": int(source_round),
            "channel": "coordinate",
        },
        charge_channel={
            "source_round": int(source_round),
            "channel": "charge",
        },
        raw_pair_channel={
            "source_round": int(source_round),
            "channel": "raw_pair",
        },
        projected_pair_channel={
            "source_round": int(source_round),
            "channel": "projected_pair",
        },
        materialization_evidence=None,
        evaluator_provenance=None,
        feedback_evidence=None,
        shape_spec={},
        frame_spec={},
        provenance=ProvenanceChain(("test_provenance",)),
        created_at_round=int(source_round),
        revoked=False,
    )


def _make_evidence(
    bundle: Any,
    channel: Any,
    *,
    perturbation_stability_lower_bound: float,
    ambiguity: float,
    degeneracy_penalty: float,
    support_coverage: float,
    recency_decay: float,
    calibration_lower_bound: float,
) -> Any:
    """Build a minimal, valid :class:`ChannelTransferEvidence`."""
    (
        _ArtifactHash_unused,
        _BundleId_unused,
        _ChannelName_unused,
        _ChannelRuleInputs_unused,
        ChannelTransferEvidence,
        ProvenanceChain,
        _RoundResultBundle_unused,
        _RunId_unused,
        _SampleId_unused,
        _TraceDigest_unused,
    ) = _contracts_types()
    return ChannelTransferEvidence(
        bundle_id=bundle.bundle_id,
        channel=channel,
        materialization_pass=True,
        geometry_pass=True,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        condition_sensitivity_observable_pass=True,
        external_metric_uncertainty=0.1,
        proxy_only_evidence=False,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        support_coverage=support_coverage,
        recency_decay=recency_decay,
        calibration_lower_bound=calibration_lower_bound,
        raw_score=0.5,
        bounded_score=0.5,
        provenance=ProvenanceChain(("test_evidence",)),
        validation_errors=(),
    )


# ---------------------------------------------------------------------------
# Channel-rule inputs strategy
# ---------------------------------------------------------------------------


@st.composite
def st_channel_inputs(
    draw: Any,
    *,
    min_blockers: int = 0,
    max_blockers: int = 6,
) -> Any:
    """Build a :class:`ChannelRuleInputs` with a controlled blocker budget.

    Parameters
    ----------
    min_blockers, max_blockers:
        Inclusively bound the number of *adversarial* perturbations applied
        to the input. ``0`` means "no perturbations" (gate is open by
        default); ``>= 1`` means the strategy is allowed to break
        individual factors and gate fields so the resulting decision is
        closed with a non-empty ``blocker_codes`` tuple.

    The channel name is sampled from the molecule channel vocabulary so
    downstream code can index the per-channel evidence deterministically.
    """
    (
        ArtifactHash,
        _BundleId_unused,
        ChannelName,
        ChannelRuleInputs,
        _ChannelTransferEvidence_unused,
        _ProvenanceChain_unused,
        _RoundResultBundle_unused,
        _RunId_unused,
        _SampleId_unused,
        _TraceDigest_unused,
    ) = _contracts_types()
    hash_artifact, _hash_trace_digest_unused = _hash_helpers()
    make_phase_state = _phase_state_factory()

    source_round = draw(st.integers(min_value=0, max_value=10))
    bundle = _make_bundle(source_round)
    channel_label = draw(
        st.sampled_from(["coordinate", "charge", "raw_pair", "projected_pair"])
    )
    channel_name = ChannelName(channel_label)

    factor_values = draw(st_factor_six())
    (
        calibration_lower_bound,
        perturbation_stability_lower_bound,
        support_coverage,
        ambiguity,
        degeneracy_penalty,
        recency_decay,
    ) = factor_values

    # Cap / floor / delta-cap fields — drawn from the unit interval so the
    # rule's blocker check stays in the happy path until we perturb.
    cap_kwargs = draw(
        st.fixed_dictionaries(
            mapping={
                "mixing_cap": unit_floats,
                "scheduled_cap": unit_floats,
                "fresh_noise_floor": floor_floats,
                "delta_cap_up": delta_cap_floats,
                "delta_cap_down": delta_cap_floats,
            }
        )
    )

    tail_admissibility = draw(st.booleans())
    complement_excluded = draw(st.booleans())
    horizon_coverage_proven = draw(st.booleans())
    finite_prefix_only = draw(st.booleans())

    # Envelope manifest hash is required when finite_prefix_only=True. We
    # always supply a non-None placeholder so the corresponding blocker
    # is not emitted by accident.
    envelope_hash = ArtifactHash(hash_artifact({"envelope": "prop"}))

    phase = make_phase_state(
        outer_cycle_id=0,
        round_in_cycle=int(source_round),
        horizon_coverage_proven=bool(horizon_coverage_proven),
    )

    evidence = _make_evidence(
        bundle,
        channel_name,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        support_coverage=support_coverage,
        recency_decay=recency_decay,
        calibration_lower_bound=calibration_lower_bound,
    )

    # Apply adversarial perturbations in bounded quantity. We sample a
    # count ``n_perturbs`` in [min_blockers, max_blockers] and then apply
    # that many adversarial mutations. Each perturbation is chosen
    # uniformly from a small catalogue of "break this field" options.
    perturb_pool = [
        # tail admissibility
        "tail_inadmissible",
        # complement exclusion
        "complement_excluded",
        # proxy-only evidence (cannot satisfy calibration_lower_bound)
        "proxy_only_evidence",
        # horizon coverage
        "horizon_unproven",
        # finite-prefix-only
        "not_finite_prefix",
        # envelope manifest hash missing
        "envelope_hash_missing",
    ]
    n_perturbs = draw(
        st.integers(min_value=int(min_blockers), max_value=int(max_blockers))
    )
    perturb_choices = draw(
        st.lists(
            elements=st.sampled_from(perturb_pool),
            min_size=int(n_perturbs),
            max_size=int(n_perturbs),
        )
    )

    if "tail_inadmissible" in perturb_choices:
        tail_admissibility = False
    if "complement_excluded" in perturb_choices:
        complement_excluded = True
    if "proxy_only_evidence" in perturb_choices:
        # Replace the evidence with a proxy-only variant. proxy_only_evidence=True
        # requires calibration_lower_bound == 0.0, so we coerce that too.
        evidence = _make_evidence(
            bundle,
            channel_name,
            perturbation_stability_lower_bound=perturbation_stability_lower_bound,
            ambiguity=ambiguity,
            degeneracy_penalty=degeneracy_penalty,
            support_coverage=support_coverage,
            recency_decay=recency_decay,
            calibration_lower_bound=0.0,
        )
        # Re-stamp proxy_only_evidence=True on the freshly-built evidence
        # (the helper above always sets it False).
        evidence = evidence.__class__(  # type: ignore[call-arg]
            bundle_id=evidence.bundle_id,
            channel=evidence.channel,
            materialization_pass=evidence.materialization_pass,
            geometry_pass=evidence.geometry_pass,
            perturbation_stability_lower_bound=evidence.perturbation_stability_lower_bound,
            condition_sensitivity_observable_pass=evidence.condition_sensitivity_observable_pass,
            external_metric_uncertainty=evidence.external_metric_uncertainty,
            proxy_only_evidence=True,
            ambiguity=evidence.ambiguity,
            degeneracy_penalty=evidence.degeneracy_penalty,
            support_coverage=evidence.support_coverage,
            recency_decay=evidence.recency_decay,
            calibration_lower_bound=0.0,
            raw_score=evidence.raw_score,
            bounded_score=evidence.bounded_score,
            provenance=evidence.provenance,
            validation_errors=(),
        )
    if "horizon_unproven" in perturb_choices:
        horizon_coverage_proven = False
    if "not_finite_prefix" in perturb_choices:
        finite_prefix_only = False
    if "envelope_hash_missing" in perturb_choices:
        # force the finite_prefix_only=True + envelope_hash=None blocker
        finite_prefix_only = True
        envelope_hash = None  # type: ignore[assignment]

    return ChannelRuleInputs(
        bundle=bundle,
        evidence=evidence,
        phase_state=phase,
        scheduled_cap=cap_kwargs["scheduled_cap"],
        mixing_cap=cap_kwargs["mixing_cap"],
        fresh_noise_floor=cap_kwargs["fresh_noise_floor"],
        delta_cap_up=cap_kwargs["delta_cap_up"],
        delta_cap_down=cap_kwargs["delta_cap_down"],
        tail_admissibility=bool(tail_admissibility),
        complement_excluded=bool(complement_excluded),
        frozen_envelope_manifest_hash=envelope_hash,
        finite_prefix_only=bool(finite_prefix_only),
        calibration_lower_bound=calibration_lower_bound,
        perturbation_stability_lower_bound=perturbation_stability_lower_bound,
        support_coverage=support_coverage,
        ambiguity=ambiguity,
        degeneracy_penalty=degeneracy_penalty,
        recency_decay=recency_decay,
        horizon_coverage_proven=bool(horizon_coverage_proven),
        selected_bundle_id=bundle.bundle_id,
    )


# ---------------------------------------------------------------------------
# Claim-gate config + evidence strategies
# ---------------------------------------------------------------------------


@st.composite
def st_claim_config(draw: Any) -> Any:
    """Build a :class:`ClaimGateConfig` whose every field is in-domain."""
    _ClaimGateConfig, build_default_claim_gate_config = _claim_gate_helpers()
    required_contracts = draw(contract_id_tuples)
    required_calibration_artifact_hash = draw(
        st.one_of(
            st.none(),
            st.text(
                alphabet=string.hexdigits.lower(), min_size=8, max_size=64
            ).map(lambda s: __import__("adaptive_reflow.contracts", fromlist=["ArtifactHash"]).ArtifactHash(s)),
        )
    )
    required_paired_evidence_count = draw(paired_counts)
    enabled = draw(gate_enabled)
    evaluation_window_rounds = draw(window_lengths)
    minimum_confidence_interval_coverage = draw(ci_coverage)
    return build_default_claim_gate_config(
        required_contracts_passing=required_contracts,
        required_calibration_artifact_hash=required_calibration_artifact_hash,
        required_paired_evidence_count=required_paired_evidence_count,
        gate_enabled=enabled,
        evaluation_window_rounds=evaluation_window_rounds,
        minimum_confidence_interval_coverage=minimum_confidence_interval_coverage,
    )


@st.composite
def st_claim_evidence(
    draw: Any,
    *,
    min_paired: int = 0,
    max_paired: int = 10,
) -> dict[str, Any]:
    """Build a claim-gate evidence mapping covering every condition key.

    The returned mapping includes entries for
    ``required_contracts_passing``, ``calibration_artifact``,
    ``paired_evidence_count``, ``confidence_interval_coverage``, and
    ``evaluation_window_rounds`` so the evaluator can index them
    regardless of which conditions the config declared.
    """
    required = draw(contract_id_tuples)
    contracts_evidence = {
        cid: {"passed": draw(contract_passed), "summary": "prop"}
        for cid in required
    }
    paired_count = draw(
        st.integers(min_value=int(min_paired), max_value=int(max_paired))
    )
    ci = draw(ci_coverage)
    win = draw(window_lengths)
    calib_hash = draw(
        st.one_of(
            st.none(),
            st.text(alphabet=string.hexdigits.lower(), min_size=8, max_size=64),
        )
    )
    evidence: dict[str, Any] = {
        **contracts_evidence,
        "paired_evidence_count": int(paired_count),
        "confidence_interval_coverage": float(ci),
        "evaluation_window_rounds": int(win),
    }
    if calib_hash is not None:
        evidence["calibration_artifact"] = {"hash": calib_hash}
    return evidence


# ---------------------------------------------------------------------------
# State bundle strategy (universal / molecule-agnostic)
# ---------------------------------------------------------------------------


@st.composite
def st_state_bundle(
    draw: Any,
    *,
    source_round_min: int = 0,
    source_round_max: int = 10,
) -> Mapping[str, Any]:
    """Build a minimal, well-formed state-bundle-shaped mapping.

    The strategy returns a plain ``Mapping`` (rather than the molecule
    :class:`MoleculeRoundResultBundle`) so it can drive fail-closed
    tests against arbitrary downstream code without dragging in the
    molecule-specific channel vocabulary. The mapping carries every
    field the universal ``validate_state_bundle`` checks.
    """
    source_round = draw(
        st.integers(min_value=int(source_round_min), max_value=int(source_round_max))
    )
    batch_id = draw(st.text(alphabet=_label_chars, min_size=1, max_size=8))
    sample_id = draw(st.text(alphabet=_label_chars, min_size=1, max_size=8))
    reference_frame = draw(
        st.sampled_from(["pocket_centered", "world", "lattice"])
    )
    normalization = draw(
        st.sampled_from(["none", "per_atom_std", "per_pocket_std"])
    )
    channel = draw(
        st.sampled_from(["coordinate", "charge", "raw_pair", "projected_pair"])
    )
    return {
        "channels": {channel: f"tensor-{source_round}-{channel}"},
        "masks": {},
        "batch_id": batch_id,
        "sample_id": sample_id,
        "reference_frame": reference_frame,
        "normalization": normalization,
        "source_round": int(source_round),
        "detach_proof": True,
        "native_state_digest": "digest-prop",
        "provenance": ("test_provenance",),
    }


@st.composite
def st_hostile_state(draw: Any) -> Mapping[str, Any]:
    """Build an invalid state-bundle-shaped mapping for fail-closed tests.

    The strategy deliberately produces one or more of:
      * a ``NaN`` or ``inf`` in a numeric field,
      * an empty / missing channel name,
      * a negative ``source_round``,
      * a disallowed ``reference_frame`` / ``normalization`` literal,
      * ``detach_proof=False``.

    The resulting mapping is *not* a valid :class:`StateBundle`; the
    validator must reject it with at least one error code.
    """
    hostile_choice = draw(
        st.sampled_from(
            [
                "nan_source_round",
                "inf_source_round",
                "negative_source_round",
                "empty_batch_id",
                "empty_sample_id",
                "bad_reference_frame",
                "bad_normalization",
                "detach_proof_false",
                "empty_native_state_digest",
                "empty_provenance",
                "empty_channels",
            ]
        )
    )
    base: dict[str, Any] = {
        "channels": {"coordinate": "tensor-x"},
        "masks": {},
        "batch_id": "batch-prop",
        "sample_id": "sample-prop",
        "reference_frame": "pocket_centered",
        "normalization": "none",
        "source_round": 0,
        "detach_proof": True,
        "native_state_digest": "digest-prop",
        "provenance": ("test_provenance",),
    }
    if hostile_choice == "nan_source_round":
        base["source_round"] = float("nan")
    elif hostile_choice == "inf_source_round":
        base["source_round"] = float("inf")
    elif hostile_choice == "negative_source_round":
        base["source_round"] = -1
    elif hostile_choice == "empty_batch_id":
        base["batch_id"] = ""
    elif hostile_choice == "empty_sample_id":
        base["sample_id"] = ""
    elif hostile_choice == "bad_reference_frame":
        base["reference_frame"] = "no_such_frame"
    elif hostile_choice == "bad_normalization":
        base["normalization"] = "per_molecule_quantum"
    elif hostile_choice == "detach_proof_false":
        base["detach_proof"] = False
    elif hostile_choice == "empty_native_state_digest":
        base["native_state_digest"] = ""
    elif hostile_choice == "empty_provenance":
        base["provenance"] = ()
    elif hostile_choice == "empty_channels":
        base["channels"] = {}
    return base


__all__ = [
    "booleans",
    "bool_only",
    "cap_floats",
    "cap_with_floor",
    "ci_coverage",
    "contract_id_tuples",
    "contract_passed",
    "delta_cap_floats",
    "floor_floats",
    "gate_enabled",
    "negative_ints",
    "non_finite_floats",
    "non_numeric_types",
    "nonneg_small_ints",
    "paired_counts",
    "positive_small_ints",
    "prev_dynamic_floats",
    "round_values",
    "st_channel_inputs",
    "st_claim_config",
    "st_claim_evidence",
    "st_factor_six",
    "st_factors",
    "st_hostile_state",
    "st_state_bundle",
    "unit_floats",
    "unit_floats_strict",
    "window_lengths",
]
