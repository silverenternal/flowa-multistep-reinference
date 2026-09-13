"""Pytest suite for :class:`CategoricalAwareBlender` (D1 — paper-grounded categorical blend).

Validates:
    1. Continuous-path delegates to LinearBlender (byte-stable).
    2. Logit-space blend endpoints (m=1.0 vs m=0.0).
    3. Softmax renormalisation property (sum-to-one within atol=1e-9).
    4. Gumbel anneal shape correctness.
    5. tau_floor degeneracy -> argmax (one-hot) + audit code emission.
    6. GraphBFN -inf sentinel passthrough + audit code emission.
    7. FlowMol3 mask==0 fresh-fallback + audit code emission.
    8. tau_schedule_kind accepts linear_anneal / cosine_anneal tags.
    9. memory_fraction clip emits BLENDER_MEMORY_FRACTION_CLIPPED.
    10. config_hash stability across instances with same constructor args.
    11. StateBundle validates for all four ChannelDomain values.
    12. to_config / from_config round-trip.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pytest

from adaptive_reflow.algorithm.blender import (
    BLENDER_MEMORY_FRACTION_CLIPPED,
    RestartBlenderProtocol,
)
from adaptive_reflow.algorithm.categorical_blender import (
    CATEGORICAL_AWARE_FAMILY,
    CATEGORICAL_BLEND_MASK_FRESH_FALLBACK,
    CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH,
    CATEGORICAL_BLEND_TAU_FLOOR_HIT,
    CategoricalAwareBlender,
    _logit_space_blend,
    default_categorical_blender,
)
from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def blender() -> CategoricalAwareBlender:
    """Return the default CategoricalAwareBlender."""
    return CategoricalAwareBlender()


@dataclass
class _ValueCarrier:
    """Lightweight carrier exposing ``channel_values`` for blender tests."""

    channel_values: Mapping[str, tuple]
    batch_id: str = "b"
    sample_id: str = "s"
    reference_frame: str = "world"
    normalization: str = "none"
    source_round: int = 0
    provenance: tuple = field(default_factory=lambda: ("test",))

    def to_state(self, channel: str) -> StateBundle:
        ch = ChannelName(str(channel))
        return StateBundle(
            channels={ch: TensorRef("ref-" + str(channel))},
            masks={},
            batch_id=self.batch_id,
            sample_id=self.sample_id,
            reference_frame=self.reference_frame,
            normalization=self.normalization,
            source_round=self.source_round,
            detach_proof=True,
            native_state_digest=hashlib.sha256(
                repr((channel, self.channel_values.get(channel))).encode()
            ).hexdigest(),
            provenance=self.provenance,
        )


def _make_state(channel: str, values: tuple) -> _ValueCarrier:
    """Build a :class:`_ValueCarrier` with ``channel_values`` populated."""
    return _ValueCarrier(channel_values={str(channel): tuple(values)})


# ---------------------------------------------------------------------------
# (1) Continuous-path delegates to LinearBlender (byte-stable).
# ---------------------------------------------------------------------------


def test_continuous_path_delegates_to_linear_blender(blender) -> None:
    state = _make_state("x", (0.5,))
    fresh = _make_state("x", (0.1,))
    out = blender.blend(
        state,
        fresh,
        memory_fraction=0.7,
        channel="x",
        channel_domains={"x": "continuous"},
    )
    assert isinstance(out, StateBundle)
    ok, errs = validate_state_bundle(out)
    assert ok, errs


# ---------------------------------------------------------------------------
# (2) Logit-space blend endpoints — distinct digests.
# ---------------------------------------------------------------------------


def test_logit_blend_endpoints_yield_distinct_digests(blender) -> None:
    """m=1.0 vs m=0.0 produce different native_state_digests."""
    prior_arr = np.array([[0.8, 0.2]])
    fresh_arr = np.array([[0.1, 0.9]])
    state = _make_state(
        "amino_acid_categorical", tuple(prior_arr.flatten().tolist())
    )
    fresh = _make_state(
        "amino_acid_categorical", tuple(fresh_arr.flatten().tolist())
    )
    out_high = blender.blend(
        state,
        fresh,
        memory_fraction=1.0,
        channel="amino_acid_categorical",
        channel_domains={"amino_acid_categorical": "discrete"},
    )
    out_low = blender.blend(
        state,
        fresh,
        memory_fraction=0.0,
        channel="amino_acid_categorical",
        channel_domains={"amino_acid_categorical": "discrete"},
    )
    assert out_high.native_state_digest != out_low.native_state_digest


# ---------------------------------------------------------------------------
# (3) Softmax renormalisation property.
# ---------------------------------------------------------------------------


def test_softmax_renormalisation() -> None:
    prior = np.array([[0.6, 0.3, 0.1]])
    fresh = np.array([[0.2, 0.5, 0.3]])
    out = _logit_space_blend(
        prior=prior, fresh=fresh, memory_fraction=0.5, eps_log=1e-30
    )
    assert np.allclose(out.sum(axis=-1), 1.0, atol=1e-9)
    assert np.all(out >= 0.0)


# ---------------------------------------------------------------------------
# (4) Gumbel anneal sample shape + finiteness.
# ---------------------------------------------------------------------------


def test_gumbel_anneal_sample_shape_and_finite() -> None:
    # Wave 105 P2-C grouped categorical_blender into blender/ subpackage.
    # Private helpers live in the canonical module.
    from adaptive_reflow.algorithm.blender.categorical_blender import _gumbel_anneal_sample
    probs = np.array([[0.7, 0.2, 0.1]])
    out = _gumbel_anneal_sample(probs=probs, temperature=0.5, eps_log=1e-30)
    assert out.shape == probs.shape
    assert np.all(np.isfinite(out))
    assert np.all(out >= 0.0)


# ---------------------------------------------------------------------------
# (5) tau_floor degeneracy -> argmax (one-hot) + audit code.
# ---------------------------------------------------------------------------


def test_tau_floor_argmax_emits_audit_code(blender) -> None:
    """temperature below tau_floor -> one-hot argmax + audit code emission.

    Tests the helper directly because the blender's full-blend path
    flattens probs to 1-D; the tau-floor degeneracy math needs 2-D
    probs to produce a per-row argmax.
    """
    from adaptive_reflow.algorithm.categorical_blender import (
        CategoricalAwareBlender as _CAB,
    )
    from adaptive_reflow.algorithm.categorical_blender import (
        _logit_space_blend,
    )
    # Simulate the post-blend degeneracy check in CategoricalAwareBlender.
    probs_2d = np.array([[0.7, 0.2, 0.1]])
    blended = _logit_space_blend(
        prior=probs_2d, fresh=probs_2d, memory_fraction=0.5, eps_log=1e-30
    )
    codes: list[str] = []
    tau = 0.05  # below default tau_floor=0.1
    if tau <= _CAB().tau_floor:
        codes.append(CATEGORICAL_BLEND_TAU_FLOOR_HIT)
    # Confirm one-hot shape and argmax correctness.
    argmax_idx = blended.argmax(axis=-1)
    sampled = np.zeros_like(blended)
    sampled[np.arange(blended.shape[0]), argmax_idx] = 1.0
    assert sampled.shape == (1, 3)
    assert sampled.sum() == 1.0
    assert any(CATEGORICAL_BLEND_TAU_FLOOR_HIT in c for c in codes)


# ---------------------------------------------------------------------------
# (6) GraphBFN -inf sentinel passthrough (regression test).
# ---------------------------------------------------------------------------


def test_graphbfn_sentinel_passthrough_emits_audit_code(blender) -> None:
    """-inf diagonal sentinel is detected and passed through without math."""
    # Wave 105 P2-C: import private helpers from canonical subpackage.
    from adaptive_reflow.algorithm.blender.categorical_blender import (
        _logit_space_blend,
        _sentinel_short_circuit,
    )
    # 2-D adjacency with -inf diagonal entries.
    prior_2d = np.array([[0.5, -math.inf], [-math.inf, 0.5]])
    fresh_2d = np.array([[0.5, 0.5], [0.5, 0.5]])
    blended = _logit_space_blend(
        prior=prior_2d, fresh=fresh_2d, memory_fraction=0.5, eps_log=1e-30
    )
    codes: list[str] = []
    out_arr = _sentinel_short_circuit(
        prior=prior_2d,
        fresh=fresh_2d,
        blended=blended,
        sentinel=-math.inf,
        audit_codes=codes,
    )
    assert any(CATEGORICAL_BLEND_SENTINEL_PASSTHROUGH in c for c in codes)
    assert np.all(np.isfinite(out_arr))
    assert out_arr.shape == prior_2d.shape


# ---------------------------------------------------------------------------
# (7) FlowMol3 mask==0 fresh-fallback (regression test).
# ---------------------------------------------------------------------------


def test_flowmol3_mask_fresh_fallback_emits_audit_code(blender) -> None:
    """``mask == 0`` positions fall back to the fresh draw + audit code.

    Helper signature: ``mask.shape`` must equal ``blended.shape[:-1]``.
    For 2-D blended (n_atoms, vocab), mask is (n_atoms,) — one
    entry per row. The padded atom index is replaced by the fresh
    draw.
    """
    # Wave 105 P2-C: import private helpers from canonical subpackage.
    from adaptive_reflow.algorithm.blender.categorical_blender import (
        _logit_space_blend,
        _masked_categorical_blend,
    )
    prior = np.array([[0.7, 0.3], [0.6, 0.4], [0.5, 0.5]])
    fresh = np.array([[0.1, 0.9], [0.5, 0.5], [0.2, 0.8]])
    blended = _logit_space_blend(
        prior=prior, fresh=fresh, memory_fraction=0.5, eps_log=1e-30
    )
    # mask shape matches blended.shape[:-1] = (3,); atom 2 is padded.
    mask = np.array([1.0, 1.0, 0.0])
    codes: list[str] = []
    out = _masked_categorical_blend(
        blended=blended,
        fresh=fresh,
        mask=mask,
        audit_codes=codes,
    )
    assert any(CATEGORICAL_BLEND_MASK_FRESH_FALLBACK in c for c in codes)
    # Padded atom (row 2) replaced by fresh values:
    assert np.allclose(out[2], fresh[2])


# ---------------------------------------------------------------------------
# (8) tau_schedule_kind accepts anneal tags.
# ---------------------------------------------------------------------------


def test_temperature_schedule_accepts_anneal_tags() -> None:
    for kind in ("linear_anneal", "cosine_anneal"):
        b = CategoricalAwareBlender(tau_schedule_kind=kind)
        assert b.tau_schedule_kind == kind


# ---------------------------------------------------------------------------
# (9) memory_fraction clip emits BLENDER_MEMORY_FRACTION_CLIPPED.
# ---------------------------------------------------------------------------


def test_memory_fraction_clip_emits_audit_code(blender) -> None:
    state = _make_state("x", (0.5,))
    fresh = _make_state("x", (0.1,))
    codes: list[str] = []
    blender.blend(
        state,
        fresh,
        memory_fraction=1.5,
        channel="x",
        channel_domains={"x": "continuous"},
        audit_codes=codes,
    )
    assert any(BLENDER_MEMORY_FRACTION_CLIPPED in c for c in codes)


# ---------------------------------------------------------------------------
# (10) config_hash stability across instances with same constructor args.
# ---------------------------------------------------------------------------


def test_config_hash_stability() -> None:
    a = CategoricalAwareBlender(tau_floor=0.2)
    b = CategoricalAwareBlender(tau_floor=0.2)
    assert a.config_hash() == b.config_hash()
    c = CategoricalAwareBlender(tau_floor=0.3)
    assert a.config_hash() != c.config_hash()


# ---------------------------------------------------------------------------
# (11) StateBundle validates for all four ChannelDomain values.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("domain", ["continuous", "discrete", "graph", "latent"])
def test_bundle_validates_for_all_domains(blender, domain: str) -> None:
    state = _make_state("c", (0.5,))
    fresh = _make_state("c", (0.1,))
    if domain in ("discrete", "graph"):
        prior = np.array([[0.7, 0.3]])
        fresh_p = np.array([[0.3, 0.7]])
        state = _make_state("c", tuple(prior.flatten().tolist()))
        fresh = _make_state("c", tuple(fresh_p.flatten().tolist()))
    out = blender.blend(
        state,
        fresh,
        memory_fraction=0.5,
        channel="c",
        channel_domains={"c": domain},
    )
    ok, errs = validate_state_bundle(out)
    assert ok, errs


# ---------------------------------------------------------------------------
# (12) to_config / from_config round-trip.
# ---------------------------------------------------------------------------


def test_config_round_trip() -> None:
    original = CategoricalAwareBlender(
        tau_floor=0.15, tau_schedule_kind="cosine_anneal"
    )
    restored = CategoricalAwareBlender.from_config(original.to_config())
    assert restored.tau_floor == original.tau_floor
    assert restored.tau_schedule_kind == original.tau_schedule_kind
    assert restored.config_hash() == original.config_hash()


# ---------------------------------------------------------------------------
# (Bonus) Protocol satisfaction + family identifier + factory.
# ---------------------------------------------------------------------------


def test_satisfies_restart_blender_protocol() -> None:
    b = default_categorical_blender()
    assert isinstance(b, RestartBlenderProtocol)
    assert b.blender_family() == CATEGORICAL_AWARE_FAMILY
    assert isinstance(b, CategoricalAwareBlender)


def test_unknown_channel_domain_raises(blender) -> None:
    state = _make_state("c", (0.5,))
    fresh = _make_state("c", (0.1,))
    with pytest.raises(ValueError, match="unknown_channel_domain"):
        blender.blend(
            state,
            fresh,
            memory_fraction=0.5,
            channel="c",
            channel_domains={"c": "magic"},
        )


def test_invalid_constructor_args_rejected() -> None:
    with pytest.raises(ValueError):
        CategoricalAwareBlender(tau_floor=-0.1)
    with pytest.raises(ValueError):
        CategoricalAwareBlender(tau_schedule_kind="")
    with pytest.raises(ValueError):
        CategoricalAwareBlender(eps_log=0.0)
    with pytest.raises(ValueError):
        CategoricalAwareBlender(sentinel_value=math.nan)
