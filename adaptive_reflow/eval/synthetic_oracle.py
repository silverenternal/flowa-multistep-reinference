"""Deterministic, stdlib-only evaluator with self-describing truth.

This module satisfies the CPU-only DTB-R7 / DTB-R8 evaluation leg by
providing :class:`SyntheticEvaluator`, whose four primary diagnostics
are pure closed-form functions of three inputs only:

* ``bundle.native_state_digest`` — the universal :class:`StateBundle`
  opaque identity string. Only the first 8 bytes are read.
* ``channel`` — the adapter-supplied :data:`ChannelName`. Captured by
  the signature for protocol conformance; not folded into the math
  (channels are already encoded in the bundle's per-channel round
  trace, which is not part of the oracle).
* ``seed`` — the round-level integer seed used for deterministic
  replay.

The four published diagnostics are:

* ``raw_score`` — first 8 bytes of ``native_state_digest`` unpacked
  as a little-endian ``uint64`` (``struct.unpack("<Q", ...)``), XOR'd
  with ``seed``, masked to its low 32 bits and normalised to ``[0, 1]``
  by dividing by ``2**32``.
* ``bounded_score`` — ``clip(raw_score, 0, 1)`` (the normalisation
  step already puts ``raw_score`` in ``[0, 1]``; the clip is the
  fail-closed surface against hostile inputs).
* ``calibration_lower_bound`` — same construction with
  ``seed ^ 0xDEADBEEF`` as the XOR operand (always in ``[0, 1]``).
* ``perturbation_stability_lower_bound`` — same construction with
  ``seed ^ 0xCAFEBABE`` as the XOR operand, then linearly rescaled
  from ``[0, 1]`` to ``[0.3, 0.95]`` so the output is in the
  stability interval documented by the orchestrator.

The companion :meth:`SyntheticEvaluator.oracle` method re-derives the
same four values via the *same* closed-form code path, but exposes
them as a plain mapping so any test can assert
``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte without
reaching into dataclass internals. The match is exact because both
methods share the same private helpers — the oracle is the self-
describing truth surface for the evaluator.

The evaluator never imports ``torch``, never touches I/O, and is
fully deterministic. It exists so DTB-R7 / R8 properties can be
exercised on CPU without depending on a model family, a calibration
artifact, or an external oracle (GNINA / QED / ADMET / PoseBusters).

Public surface
--------------

* :data:`SYNTHETIC_AUDIT_REASON` — the literal string baked into every
  emitted evidence row's ``provenance`` chain.
* :class:`SyntheticEvaluator` — the deterministic closed-form
  evaluator + self-describing oracle.

Tasks satisfied:

* ``DTB-R7`` — closed-form evaluator that does not require any
  external model to run on CPU.
* ``DTB-R8`` — the oracle lets the claim-gate be exercised against
  a deterministic truth surface without a calibration dataset.
"""
from __future__ import annotations

import struct
from typing import Any

from adaptive_reflow.contracts import (  # type: ignore[attr-defined]
    BundleId,
    ChannelName,
    ChannelTransferEvidence,
    FactorValue,
    MechanismId,
    ProvenanceChain,
)
from adaptive_reflow.universal.state import StateBundle

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Stable audit reason baked into every emitted evidence row.
#:
#: Stored as the trailing entry of the row's ``provenance`` tuple
#: (ChannelTransferEvidence does not carry a free-form ``audit_reason``
#: field; the channel rule reads the provenance chain instead). The
#: literal value is asserted in tests as the proof that the row was
#: emitted by this evaluator rather than by a real model adapter.
SYNTHETIC_AUDIT_REASON: str = "synthetic_evaluator:closed_form"

#: Lower bound on the perturbation-stability output range. Picked so
#: the value is always strictly above the fresh-noise collapse
#: threshold used by the round-to-round oscillation detector
#: (5e-2) and well below the canonical "open-gate" cap (1.0).
_PERTURBATION_LOWER: float = 0.3

#: Upper bound on the perturbation-stability output range. Picked so
#: the value is strictly below 1.0 (admissible band) but above 0.5
#: (the symmetric delta cap) so the channel rule's stability floor
#: check always passes for synthetic bundles.
_PERTURBATION_UPPER: float = 0.95

#: Number of bytes consumed from ``native_state_digest`` for the
#: uint64 unpack. Eight bytes is the smallest power-of-two that
#: gives the XOR-32 fold a stable 32-bit normalised output.
_DIGEST_PREFIX_BYTES: int = 8

#: 32-bit modulus applied before normalisation. ``raw_score`` lives
#: in ``[0, 1]`` because the upper 32 bits of the XOR'd uint64 are
#: masked away.
_SCORE_MOD: int = 1 << 32

#: 32-bit mask isolating the low half of the XOR'd uint64.
_SCORE_MASK: int = (1 << 32) - 1

#: XOR operand folded into the calibration diagnostic. A 32-bit
#: constant so the same seed produces the same calibration regardless
#: of which 8-byte window of the digest is consumed.
_CALIBRATION_XOR: int = 0xDEADBEEF

#: XOR operand folded into the perturbation diagnostic. A 32-bit
#: constant, disjoint from :data:`_CALIBRATION_XOR`, so calibration
#: and perturbation are guaranteed to differ.
_PERTURBATION_XOR: int = 0xCAFEBABE


# ---------------------------------------------------------------------------
# Pure helpers (no instance state; reused by evaluate + oracle)
# ---------------------------------------------------------------------------


def _digest_uint64(native_state_digest: str) -> int:
    """Return the first 8 bytes of ``native_state_digest`` as a uint64.

    The digest is encoded as UTF-8 (the canonical hash representation
    for this codebase) and padded with zero bytes if it is shorter
    than 8 bytes. The value is interpreted as a little-endian uint64
    via :func:`struct.unpack`. Padding is the documented behaviour for
    short digests so the oracle is a total function on any string.
    """
    raw = native_state_digest.encode("utf-8")[:_DIGEST_PREFIX_BYTES]
    if len(raw) < _DIGEST_PREFIX_BYTES:
        raw = raw + b"\x00" * (_DIGEST_PREFIX_BYTES - len(raw))
    return int(struct.unpack("<Q", raw)[0])


def _normalise_uint32(value: int) -> float:
    """Return ``(value & _SCORE_MASK) / 2**32`` in ``[0, 1]``.

    The 32-bit mask guarantees the result is in ``[0, 1)``; the
    divide produces a Python float with the exact same bits the
    bytecode yields for the same operand on the same interpreter.
    """
    return float(value & _SCORE_MASK) / float(_SCORE_MOD)


def _rescale_to_range(value: float, *, lo: float, hi: float) -> float:
    """Linearly rescale ``value`` from ``[0, 1]`` to ``[lo, hi]``.

    Assumes ``0.0 <= value <= 1.0``. The bounds are not re-clamped
    here because the upstream normalisation already pins ``value``
    inside ``[0, 1]``; if a caller passes an out-of-range value the
    linear map will return a value outside ``[lo, hi]`` and the
    channel rule will reject it through its standard unit-factor
    validation path.
    """
    return float(lo) + float(value) * float(hi - lo)


# ---------------------------------------------------------------------------
# SyntheticEvaluator
# ---------------------------------------------------------------------------


class SyntheticEvaluator:
    """Closed-form :class:`Evaluator` with self-describing oracle.

    The evaluator never inspects any tensor content; it only reads
    :attr:`StateBundle.native_state_digest`. The same digest always
    produces the same score for a given ``(channel, seed)`` pair, so
    ``is_deterministic()`` is always ``True``.

    The class carries no instance state (declared via ``__slots__ =
    ()``) and the closed-form math is exposed only as private
    helpers. Tests and the golden generator consume the public
    :meth:`evaluate` / :meth:`oracle` / :meth:`is_deterministic`
    surface; the private helpers are an implementation detail and may
    evolve as long as the byte-for-byte equality contract between
    :meth:`evaluate` and :meth:`oracle` is preserved.
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

        The four published diagnostics — ``raw_score``, ``bounded_score``,
        ``calibration_lower_bound``, ``perturbation_stability_lower_bound``
        — are pure closed-form functions of
        ``bundle.native_state_digest``, ``channel`` and ``seed``. Every
        other evidence field is filled with a conservative default
        that lets the channel rule produce a deterministic decision
        when the bundle passes the envelope: materialisation +
        geometry + condition-sensitivity all marked passing,
        ``proxy_only_evidence=False``, ``ambiguity`` /
        ``degeneracy_penalty`` clamped to ``0.0``,
        ``support_coverage`` / ``recency_decay`` clamped to ``1.0``.
        The synthetic bundle is not a "proxy only" row.
        """
        raw_score = self._closed_form_score(
            bundle, channel=channel, seed=seed
        )
        bounded_score = _clip_unit(raw_score)
        calibration = self._closed_form_calibration(
            bundle, channel=channel, seed=seed
        )
        perturbation = self._closed_form_perturbation_bound(
            bundle, channel=channel, seed=seed
        )

        bundle_id = self._derive_bundle_id(bundle)
        provenance = ProvenanceChain(
            (
                MechanismId("synthetic_evaluator"),
                MechanismId(SYNTHETIC_AUDIT_REASON),
            )
        )

        return ChannelTransferEvidence(
            bundle_id=bundle_id,
            channel=channel,
            materialization_pass=True,
            geometry_pass=True,
            perturbation_stability_lower_bound=FactorValue(float(perturbation)),
            condition_sensitivity_observable_pass=True,
            external_metric_uncertainty=FactorValue(0.0),
            proxy_only_evidence=False,
            ambiguity=FactorValue(0.0),
            degeneracy_penalty=FactorValue(0.0),
            support_coverage=FactorValue(1.0),
            recency_decay=FactorValue(1.0),
            calibration_lower_bound=FactorValue(float(calibration)),
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

        The oracle re-derives each value via the *same* closed-form
        construction used by :meth:`evaluate`, but exposes them as a
        plain ``dict[str, float]`` so tests can assert
        ``evaluate(b, c, s) == oracle(b, c, s)`` byte-for-byte without
        reaching into dataclass internals. The ``bounded_score`` key
        is always equal to the clipped raw_score; the oracle does not
        surface any other evidence field.
        """
        raw_score = self._closed_form_score(
            bundle, channel=channel, seed=seed
        )
        bounded_score = _clip_unit(raw_score)
        calibration = self._closed_form_calibration(
            bundle, channel=channel, seed=seed
        )
        perturbation = self._closed_form_perturbation_bound(
            bundle, channel=channel, seed=seed
        )
        return {
            "raw_score": float(raw_score),
            "bounded_score": float(bounded_score),
            "calibration_lower_bound": float(calibration),
            "perturbation_stability_lower_bound": float(perturbation),
        }

    def is_deterministic(self) -> bool:
        """Return ``True``: this evaluator is always deterministic."""
        return True

    # ---- closed-form math (also used by oracle) ---------------------

    def _closed_form_score(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> float:
        """First 8 bytes of digest as uint64, XOR with seed, normalise to [0,1]."""
        digest_int = _digest_uint64(bundle.native_state_digest)
        xored = digest_int ^ int(seed)
        return _normalise_uint32(xored)

    def _closed_form_calibration(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> float:
        """XOR with ``seed ^ _CALIBRATION_XOR``, normalise to ``[0, 1]``."""
        digest_int = _digest_uint64(bundle.native_state_digest)
        xored = digest_int ^ (int(seed) ^ _CALIBRATION_XOR)
        return _normalise_uint32(xored)

    def _closed_form_perturbation_bound(
        self,
        bundle: StateBundle,
        *,
        channel: ChannelName,
        seed: int,
    ) -> float:
        """XOR with ``seed ^ _PERTURBATION_XOR``, rescaled to ``[_PERTURBATION_LOWER, _PERTURBATION_UPPER]``."""
        digest_int = _digest_uint64(bundle.native_state_digest)
        xored = digest_int ^ (int(seed) ^ _PERTURBATION_XOR)
        base = _normalise_uint32(xored)
        return _rescale_to_range(
            base, lo=_PERTURBATION_LOWER, hi=_PERTURBATION_UPPER
        )

    # ---- bundle-id derivation ---------------------------------------

    @staticmethod
    def _derive_bundle_id(bundle: StateBundle) -> BundleId:
        """Derive a stable :class:`BundleId` from the bundle's identity.

        The synthetic evaluator does not carry an explicit ``bundle_id``
        on the universal :class:`StateBundle` carrier; the canonical
        unique key is the bundle's opaque ``native_state_digest``. We
        namespace the synthetic bundle-id with the ``"syn::"`` prefix
        so the orchestrator can detect a synthetic row at audit time
        without confusing it with any real producer.
        """
        return BundleId(f"syn::{bundle.native_state_digest}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clip_unit(value: float) -> float:
    """Return ``value`` clipped to ``[0.0, 1.0]``.

    Fail-closed against hostile inputs (NaN, infinities, out-of-range
    reals). NaN propagates through ``min`` / ``max``; the function
    therefore raises :class:`ValueError` for non-finite inputs so the
    orchestrator's evidence validator rejects the row instead of
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


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "SYNTHETIC_AUDIT_REASON",
    "SyntheticEvaluator",
]
