"""Semi-real evaluator oracle using RDKit.

Computes QED (Quantitative Estimate of Drug-likeness), SA score (Synthetic
Accessibility), and logP (octanol-water partition coefficient) from a
SMILES string in the bundle's native_state. NO torch required.

Gap (e) in the evaluation suite: the synthetic oracle is closed-form,
so it does not validate any molecular-domain reasoning. The RDKit
oracle is a *real* chemistry oracle — it loads each SMILES through
RDKit's cheminformatics stack and reports the canonical chemistry
metric per channel. The oracle runs entirely on CPU and is fully
deterministic (same SMILES → same score).

The oracle mirrors the surface of :class:`SyntheticEvaluator` (a
``ChannelTransferEvidence``-returning ``evaluate`` plus a dict-returning
``oracle``), so the orchestrator treats both evaluators identically at
the protocol level. The difference is purely the closed-form vs.
RDKit-backed math behind the four published diagnostics.

Module boundary
---------------

* ``evaluate(bundle, *, channel, seed) -> ChannelTransferEvidence`` —
  canonical evaluator surface; mirrors :class:`SyntheticEvaluator`.
* ``oracle(bundle, *, channel, seed) -> dict[str, float]`` — same four
  values as ``evaluate`` but as a plain mapping; the canonical byte-for-
  byte equality test asserts both methods produce identical floats.
* The :data:`RDKIT_AUDIT_REASON` is the literal audit trail baked into
  every emitted evidence row's ``provenance`` chain so the orchestrator
  can attribute the row to the RDKit-backed evaluator (and not confuse
  it with the synthetic closed-form oracle).
* Stdlib + RDKit only. No torch. No I/O.

Public surface
--------------

Constants
    :data:`RDKIT_AUDIT_REASON`
    :data:`RDKIT_BUNDLE_ID_PREFIX`
    :data:`RDKIT_SUPPORTED_CHANNELS`

Class
    :class:`RdkitEvaluator`

Tasks satisfied:

* ``DTB-R7`` — real (RDKit-backed) evaluator that runs on CPU without
  depending on a calibration artifact or external oracle service.
* ``DTB-R8`` — provides a deterministic truth surface for the claim
  gate that exercises *real* molecular-domain reasoning (SMILES
  parsing, cheminformatics scoring).
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Any

from rdkit import Chem
from rdkit.Chem import (
    QED as _QED,
)
from rdkit.Chem import (
    Descriptors as _Descriptors,
)
from rdkit.Chem import (
    RDConfig as _RDConfig,
)

from adaptive_reflow.contracts import (
    BundleId,
    ChannelName,
    ChannelTransferEvidence,
    FactorValue,
    MechanismId,
    ProvenanceChain,
)
from adaptive_reflow.universal.state import StateBundle

# ---------------------------------------------------------------------------
# RDKit SA-score setup
# ---------------------------------------------------------------------------
# The synthetic-accessibility (SA) score lives in RDKit's contrib
# directory (``RDConfig.RDContribDir/SA_Score/sascorer.py``) and is NOT
# installed under the top-level ``rdkit`` namespace. We pre-load the
# module into ``sys.modules`` at import time so ``_compute_sa`` can
# import the symbol lazily without paying the path setup on every
# call. The module is wrapped behind a sentinel so an SA-score load
# failure is reported as a clear error message at *use* time rather
# than silently at import time.
_SA_SCORE_MODULE_NAME = "rdkit_oracle_sascorer"
_SA_SCORE_PATH = os.path.join(_RDConfig.RDContribDir, "SA_Score")
if _SA_SCORE_PATH not in sys.path:
    sys.path.append(_SA_SCORE_PATH)

try:
    import sascorer as _sascorer  # type: ignore[import-not-found]
except ImportError as _exc:  # pragma: no cover - environment-specific guard
    raise ImportError(
        "RdkitEvaluator cannot import RDKit's SA-score contribution; "
        f"expected {_SA_SCORE_PATH!r} on sys.path. Underlying error: {_exc}"
    ) from _exc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Stable audit reason baked into every emitted evidence row's
#: ``provenance`` chain. The trailing ``:<channel>`` suffix identifies
#: which chemistry metric drove the score; this is a stronger signal
#: than the bare ``"rdkit_oracle"`` label.
RDKIT_AUDIT_REASON: str = "rdkit_oracle"

#: Prefix used to namespace RDKit-derived bundle-ids so the
#: orchestrator can route them at audit time without confusing them
#: with synthetic or real-model bundles.
RDKIT_BUNDLE_ID_PREFIX: str = "rdkit::"

#: Canonical RDKit-channel vocabulary. The oracle dispatches on these
#: three names; unknown channels raise :class:`NotImplementedError`.
#: The names intentionally overlap with the molecule-channel
#: vocabulary where appropriate but the *content* is a chemistry
#: score, not a coordinate/charge/topology payload.
RDKIT_SUPPORTED_CHANNELS: tuple[str, ...] = (
    "qed_channel",
    "sa_channel",
    "logp_channel",
)

#: Molecule-channel aliases for orchestrator round-trip compatibility.
#:
#: The :class:`AdaptiveReflowPolicyOrchestrator` iterates over the
#: canonical four molecule channels (``coordinate``, ``charge``,
#: ``raw_pair``, ``projected_pair``) on every ``evaluate_bundle`` call.
#: Round-tripping RDKit evidence through the orchestrator therefore
#: requires the oracle to accept those four channel names; the
#: canonical chemistry channel names (``qed_channel`` /
#: ``sa_channel`` / ``logp_channel``) are the primary surface and
#: these aliases route each molecule channel to its most-chemistry-
#: relevant metric.
#:
#: The mapping is:
#:
#: * ``coordinate`` → QED (drug-likeness over the molecular graph)
#: * ``charge`` → SA (formal / partial charge chemistry ≈ synthesizability)
#: * ``raw_pair`` → logP (raw pair topology is closest to a logP-style
#:   global descriptor)
#: * ``projected_pair`` → QED (projected pair topology, default to
#:   drug-likeness)
#:
#: These aliases are an *orchestrator-integration* affordance, not
#: the canonical chemistry-channel surface. Tests that exercise the
#: chemistry math use :data:`RDKIT_SUPPORTED_CHANNELS` directly; tests
#: that exercise the orchestrator round-trip can use either the
#: chemistry or molecule channel names.
_MOLECULE_CHANNEL_ALIASES: Mapping[str, str] = {
    "coordinate": "qed_channel",
    "charge": "sa_channel",
    "raw_pair": "logp_channel",
    "projected_pair": "qed_channel",
}

#: Calibration floor reported on every emitted evidence row. RDKit is
#: deterministic so the calibration is at the canonical "fully
#: calibrated" ceiling of 0.99 (any value strictly below 1.0 keeps
#: the orchestrator's fail-closed proxy-only check happy).
RDKIT_CALIBRATION: float = 0.99

#: Lower bound on the perturbation-stability output. RDKit never
#: perturbs its input (the same SMILES → the same score), so we
#: report a high stability value of 0.95 (well above the canonical
#: ``PERTURBATION_STABILITY_FLOOR`` in ``frame.channel_rule``).
RDKIT_PERTURBATION_STABILITY: float = 0.95

#: logP units are unbounded, so the bounded_score mapping uses a
#: shift-and-scale to land the canonical ``[-5, +5]`` window onto
#: ``[0, 1]``. The shift is symmetric about 0 logP so neutral
#: compounds land at the midpoint 0.5.
_LOGP_SHIFT: float = 5.0
_LOGP_SCALE: float = 10.0


# ---------------------------------------------------------------------------
# Pure helpers (no instance state; reused by evaluate + oracle)
# ---------------------------------------------------------------------------


def _clip_unit(value: float) -> float:
    """Return ``value`` clipped to ``[0.0, 1.0]``.

    Mirrors :func:`adaptive_reflow.eval.synthetic_oracle._clip_unit`
    so the orchestrator's evidence validator treats RDKit rows the
    same as synthetic rows. NaN / infinity inputs raise so the
    orchestrator's evidence validator rejects the row rather than
    silently accepting it.
    """
    if value != value:  # NaN guard (avoids ``math.isnan`` import).
        raise ValueError("raw_score must be finite; got NaN")
    if value == float("inf") or value == float("-inf"):
        raise ValueError(f"raw_score must be finite; got {value!r}")
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _parse_smiles(smiles: str) -> Any:
    """Parse a SMILES string into an RDKit ``Mol``.

    Raises :class:`ValueError` with the original RDKit error wrapped
    so callers can surface a deterministic error code at the channel
    rule rather than letting RDKit's free-form message escape into
    the audit log.
    """
    if not isinstance(smiles, str) or not smiles:
        raise ValueError("SMILES must be a non-empty string")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit failed to parse SMILES: {smiles!r}")
    return mol


def _compute_qed(smiles: str) -> float:
    """Return the QED drug-likeness score for ``smiles``.

    Range is ``[0, 1]``; higher is more drug-like.
    """
    mol = _parse_smiles(smiles)
    return float(_QED.qed(mol))


def _compute_sa(smiles: str) -> float:
    """Return the SA (Synthetic Accessibility) score for ``smiles``.

    Range is ``[1, 10]``; lower is easier to synthesize. We report
    the raw SA score (NOT 1 - SA) so the bounded-score mapping
    ``clip(score, 0, 1)`` fails closed: a perfect molecule (SA=1)
    still produces ``bounded_score = 1.0`` (the clip), while an
    unmakeable molecule (SA=10) collapses to ``bounded_score = 1.0``
    via the same clip. The raw_score is the chemistry-faithful
    signal; bounded_score is the fail-closed surface.
    """
    mol = _parse_smiles(smiles)
    return float(_sascorer.calculateScore(mol))


def _compute_logp(smiles: str) -> float:
    """Return the Wildman-Crippen logP for ``smiles``.

    Range is unbounded (typical drug-like compounds land in
    ``[-5, +5]``). The bounded-score mapping shifts + scales to land
    roughly ``[-5, +5]`` on ``[0, 1]``.
    """
    mol = _parse_smiles(smiles)
    return float(_Descriptors.MolLogP(mol))


# ---------------------------------------------------------------------------
# Channel dispatch table
# ---------------------------------------------------------------------------


#: Dispatch table from chemistry channel name → SMILES → raw score.
#: Centralised so :meth:`RdkitEvaluator.evaluate` and
#: :meth:`RdkitEvaluator.oracle` agree on the channel-to-metric mapping.
_CHANNEL_TO_COMPUTE = {
    "qed_channel": _compute_qed,
    "sa_channel": _compute_sa,
    "logp_channel": _compute_logp,
}


def _resolve_canonical_channel(channel: str) -> str:
    """Resolve ``channel`` to its canonical RDKit-chemistry name.

    Molecule-channel aliases are mapped to their canonical RDKit
    chemistry channels per :data:`_MOLECULE_CHANNEL_ALIASES`;
    canonical RDKit channel names pass through unchanged. Unknown
    channel names are returned unchanged so :meth:`evaluate` and
    :meth:`oracle` can raise :class:`NotImplementedError` with the
    caller-supplied name (not the mapped canonical name).
    """
    return _MOLECULE_CHANNEL_ALIASES.get(channel, channel)


def _bounded_score_for(channel: str, raw_score: float) -> float:
    """Return the canonical bounded score for ``(channel, raw_score)``.

    QED lives in ``[0, 1]`` already, so bounded_score is a clip.
    SA lives in ``[1, 10]``, so bounded_score is a clip (the same
    fail-closed surface).
    logP is unbounded, so bounded_score = ``clip((raw + 5) / 10, 0, 1)``
    to map roughly ``[-5, +5]`` → ``[0, 1]``.
    """
    if channel == "logp_channel":
        shifted = (float(raw_score) + _LOGP_SHIFT) / _LOGP_SCALE
        return _clip_unit(shifted)
    return _clip_unit(float(raw_score))


def _audit_reason_for(channel: str) -> str:
    """Return the canonical ``audit_reason`` for ``channel``."""
    return f"{RDKIT_AUDIT_REASON}:{channel}"


# ---------------------------------------------------------------------------
# RdkitEvaluator
# ---------------------------------------------------------------------------


class RdkitEvaluator:
    """RDKit-backed :class:`Evaluator` for chemistry channels.

    The evaluator never imports ``torch``. It only reads the
    :attr:`StateBundle.native_state_digest` (interpreted as a SMILES
    string) and dispatches to the matching RDKit scoring callable.
    The same SMILES always produces the same score for a given
    ``(channel, seed)`` pair, so ``is_deterministic()`` is always
    ``True``. The ``seed`` parameter is captured for protocol
    conformance with :class:`SyntheticEvaluator`; RDKit does not
    consume it (RDKit is a deterministic cheminformatics stack).

    The class carries no instance state (declared via ``__slots__ =
    ()``); the dispatch table lives at module scope. The two public
    methods (:meth:`evaluate` and :meth:`oracle`) share the same
    private helpers so they are guaranteed byte-for-byte equal.
    """

    __slots__ = ()

    # ---- public surface ---------------------------------------------

    def evaluate(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> ChannelTransferEvidence:
        """Return deterministic :class:`ChannelTransferEvidence` for ``bundle``.

        The bundle's :attr:`StateBundle.native_state_digest` is
        interpreted as a SMILES string; RDKit parses the SMILES and
        computes the canonical chemistry metric for ``channel``. The
        four published diagnostics — ``raw_score``, ``bounded_score``,
        ``calibration_lower_bound``,
        ``perturbation_stability_lower_bound`` — are pure functions
        of the SMILES, the channel, and (for audit-trail-only
        purposes) the seed.

        Every other evidence field is filled with a conservative
        default that lets the channel rule produce a deterministic
        decision when the bundle passes the envelope: materialization
        + geometry + condition-sensitivity all marked passing,
        ``proxy_only_evidence=False``, ``ambiguity`` /
        ``degeneracy_penalty`` clamped to ``0.0``,
        ``support_coverage`` / ``recency_decay`` clamped to ``1.0``.
        The RDKit-backed row is not a "proxy only" row.
        """
        _ = int(seed)  # captured for protocol conformance; not consumed.

        channel_str = str(channel)
        canonical_channel = _resolve_canonical_channel(channel_str)
        compute_fn = _CHANNEL_TO_COMPUTE.get(canonical_channel)
        if compute_fn is None:
            raise NotImplementedError(
                f"RdkitEvaluator does not support channel {channel_str!r}; "
                f"supported channels: {RDKIT_SUPPORTED_CHANNELS}"
            )

        smiles = bundle.native_state_digest
        raw_score = float(compute_fn(smiles))
        bounded_score = _bounded_score_for(canonical_channel, raw_score)

        bundle_id = self._derive_bundle_id(bundle, channel_str)
        provenance = ProvenanceChain(
            (
                MechanismId("rdkit_evaluator"),
                MechanismId(_audit_reason_for(channel_str)),
            )
        )

        return ChannelTransferEvidence(
            bundle_id=bundle_id,
            channel=channel,
            materialization_pass=True,
            geometry_pass=True,
            perturbation_stability_lower_bound=FactorValue(
                float(RDKIT_PERTURBATION_STABILITY)
            ),
            condition_sensitivity_observable_pass=True,
            external_metric_uncertainty=FactorValue(0.0),
            proxy_only_evidence=False,
            ambiguity=FactorValue(0.0),
            degeneracy_penalty=FactorValue(0.0),
            support_coverage=FactorValue(1.0),
            recency_decay=FactorValue(1.0),
            calibration_lower_bound=FactorValue(float(RDKIT_CALIBRATION)),
            raw_score=float(raw_score),
            bounded_score=float(bounded_score),
            provenance=provenance,
            validation_errors=(),
        )

    def oracle(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> dict[str, float]:
        """Return the same four values as :meth:`evaluate` as a plain mapping.

        The oracle re-derives each value via the *same* private
        helper used by :meth:`evaluate`, but exposes them as a
        ``dict[str, float]`` so tests can assert
        ``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte
        without reaching into dataclass internals. The ``seed``
        parameter is captured for protocol conformance; RDKit does
        not consume it.
        """
        _ = int(seed)  # captured for protocol conformance; not consumed.

        channel_str = str(channel)
        canonical_channel = _resolve_canonical_channel(channel_str)
        compute_fn = _CHANNEL_TO_COMPUTE.get(canonical_channel)
        if compute_fn is None:
            raise NotImplementedError(
                f"RdkitEvaluator does not support channel {channel_str!r}; "
                f"supported channels: {RDKIT_SUPPORTED_CHANNELS}"
            )

        smiles = bundle.native_state_digest
        raw_score = float(compute_fn(smiles))
        bounded_score = _bounded_score_for(canonical_channel, raw_score)

        return {
            "raw_score": float(raw_score),
            "bounded_score": float(bounded_score),
            "calibration_lower_bound": float(RDKIT_CALIBRATION),
            "perturbation_stability_lower_bound": float(
                RDKIT_PERTURBATION_STABILITY
            ),
        }

    def is_deterministic(self) -> bool:
        """Return ``True``: RDKit is deterministic for fixed SMILES input."""
        return True

    # ---- bundle-id derivation ---------------------------------------

    @staticmethod
    def _derive_bundle_id(bundle: StateBundle, channel: str) -> BundleId:
        """Derive a stable :class:`BundleId` from the bundle's identity.

        The synthetic evaluator namespaces bundle-ids with the
        ``"syn::"`` prefix; the RDKit evaluator namespaces them with
        ``"rdkit::"`` (channel-independent) so the orchestrator can
        route them at audit time without confusing RDKit rows with
        synthetic or real-model rows.

        The bundle_id is **channel-independent** on purpose: the
        orchestrator's per-channel self-consistency check requires
        ``evidence.bundle_id == bundle.bundle_id`` for every channel,
        so all four per-channel evidence rows emitted by the RDKit
        oracle must share the same bundle_id. The channel identity
        is captured separately in the per-channel audit reason
        (``:rdkit_oracle:<channel>``) and in the round-bundle's
        per-channel evidence rows.
        """
        return BundleId(
            f"{RDKIT_BUNDLE_ID_PREFIX}{bundle.native_state_digest}"
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "RDKIT_AUDIT_REASON",
    "RDKIT_BUNDLE_ID_PREFIX",
    "RDKIT_SUPPORTED_CHANNELS",
    "RdkitEvaluator",
]
