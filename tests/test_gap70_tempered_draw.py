"""GAP-70 round 2 — the restart draw's tempering, ``lam``.

Pre-registration: ``docs/audit/gap70-r2-tempered-draw.md``.

The operator is ``fresh = (1 - lam) * state + lam * softmax(randn)``. The two
ends are already-measured arms (no restart, and the shipped D-004b draw), so the
policy is a point on the segment between them, not a new mechanism.

Why the draw and not the placement: round 1 measured the position-selective
blend at ``N_C = 1.5 %`` novelty against the scalar arm's ``0.8 %`` — the mask
is inert against the quantity it was meant to move
(``docs/audit/gap70-lineageflow-position-blend.md`` §4.3).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow import (
    AMINO_ACID_CATEGORICAL,
    LINEAGEFLOW_AA_VOCAB,
    LINEAGEFLOW_STATE_SHAPE,
    LineageFlowAdapter,
    _synthesize_random_simplex,
)
from adaptive_reflow.algorithm.perturbation import (
    PerturbationConfigError,
    TemperedFreshPerturbation,
    build_perturbation_from_config,
)

# ---------------------------------------------------------------------------
# 1. the draw itself
# ---------------------------------------------------------------------------


def _state() -> np.ndarray:
    """A non-uniform ``(L, K)`` simplex: a uniform state hides every blend."""
    rng = np.random.default_rng(7)
    theta = rng.random(LINEAGEFLOW_STATE_SHAPE)
    return theta / theta.sum(axis=-1, keepdims=True)


def test_lam_zero_is_a_no_op() -> None:
    x = _state()
    out = TemperedFreshPerturbation(lam=0.0).propose_with_seed(x, None, 0.0, 11)
    np.testing.assert_array_equal(out, x)
    assert out is not x  # never aliases the caller's array


def test_lam_one_is_the_shipped_draw() -> None:
    """``lam = 1`` must be the adapter's D-004b simplex, not merely similar.

    The adapter's shipped path draws ``_synthesize_random_simplex(rng)`` from a
    ``default_rng(seed)``; pinning the two together is what makes ``lam = 1``
    the "current arm" end of the segment instead of a new arm.
    """
    x = _state()
    out = TemperedFreshPerturbation(lam=1.0).propose_with_seed(x, None, 0.0, 1234)
    expected = _synthesize_random_simplex(np.random.default_rng(1234))
    np.testing.assert_allclose(out, expected, rtol=0.0, atol=0.0)


def test_interior_lam_is_the_midpoint_of_the_two_ends() -> None:
    x = _state()
    lo = TemperedFreshPerturbation(lam=0.0).propose_with_seed(x, None, 0.0, 99)
    hi = TemperedFreshPerturbation(lam=1.0).propose_with_seed(x, None, 0.0, 99)
    mid = TemperedFreshPerturbation(lam=0.5).propose_with_seed(x, None, 0.0, 99)
    np.testing.assert_allclose(mid, 0.5 * lo + 0.5 * hi, atol=1e-15)


def test_distance_from_the_state_grows_with_lam() -> None:
    x = _state()
    dists = []
    for lam in (0.0, 0.25, 0.5, 0.75, 1.0):
        out = TemperedFreshPerturbation(lam=lam).propose_with_seed(
            x, None, 0.0, 4242
        )
        dists.append(float(np.abs(out - x).mean()))
    assert dists == sorted(dists)
    assert dists[0] == 0.0


def test_rows_stay_on_the_simplex() -> None:
    out = TemperedFreshPerturbation(lam=0.37).propose_with_seed(
        _state(), None, 0.0, 5
    )
    assert out.shape == LINEAGEFLOW_STATE_SHAPE
    assert float(out.min()) >= 0.0
    np.testing.assert_allclose(out.sum(axis=-1), 1.0, atol=1e-12)


def test_the_draw_is_seeded_and_per_record() -> None:
    x = _state()
    pol = TemperedFreshPerturbation(lam=1.0)
    a = pol.propose_with_seed(x, None, 0.0, 1)
    b = pol.propose_with_seed(x, None, 0.0, 1)
    c = pol.propose_with_seed(x, None, 0.0, 2)
    np.testing.assert_array_equal(a, b)
    assert not np.allclose(a, c)


def test_only_the_amino_acid_columns_carry_the_draw() -> None:
    """Columns past ``aa_vocab`` keep the canonical uniform share.

    The shipped draw sets the special dims to ``1/K`` and renormalises, so their
    post-normalisation value is ``(1/K) / (1 + (K - aa)/K)``, not ``1/K``. The
    test pins the *convention* (constant across positions and rows) rather than
    the arithmetic, which ``test_lam_one_is_the_shipped_draw`` already pins
    against the adapter's own helper.
    """
    out = TemperedFreshPerturbation(lam=1.0).propose_with_seed(
        _state(), None, 0.0, 8
    )
    tail = out[:, LINEAGEFLOW_AA_VOCAB:]
    assert tail.shape[1] == LINEAGEFLOW_STATE_SHAPE[1] - LINEAGEFLOW_AA_VOCAB
    np.testing.assert_allclose(tail, tail.flat[0], atol=1e-15)


# ---------------------------------------------------------------------------
# 2. validation and config round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", [-0.01, 1.01, float("nan"), float("inf")])
def test_lam_must_lie_in_the_unit_interval(lam: float) -> None:
    with pytest.raises(PerturbationConfigError):
        TemperedFreshPerturbation(lam=lam)


def test_seed_offset_must_be_a_non_negative_int() -> None:
    with pytest.raises(PerturbationConfigError):
        TemperedFreshPerturbation(lam=0.5, seed_offset=-1)
    with pytest.raises(PerturbationConfigError):
        TemperedFreshPerturbation(lam=0.5, seed_offset=1.5)  # type: ignore[arg-type]


def test_aa_vocab_must_be_positive() -> None:
    with pytest.raises(PerturbationConfigError):
        TemperedFreshPerturbation(lam=0.5, aa_vocab=0)


def test_config_round_trip_preserves_the_hash() -> None:
    pol = TemperedFreshPerturbation(lam=0.25, seed_offset=3)
    restored = TemperedFreshPerturbation.from_config(pol.to_config())
    assert restored.config_hash() == pol.config_hash()
    assert restored.lam == pol.lam
    assert restored.seed_offset == pol.seed_offset


def test_different_lam_hashes_differently() -> None:
    assert (
        TemperedFreshPerturbation(lam=0.25).config_hash()
        != TemperedFreshPerturbation(lam=0.5).config_hash()
    )


def test_build_from_config_dispatches_on_family() -> None:
    pol = build_perturbation_from_config(
        TemperedFreshPerturbation(lam=0.75).to_config()
    )
    assert isinstance(pol, TemperedFreshPerturbation)
    assert pol.lam == 0.75


# ---------------------------------------------------------------------------
# 3. end to end through the adapter's restart
# ---------------------------------------------------------------------------


def _adapter(**kwargs: object) -> LineageFlowAdapter:
    return LineageFlowAdapter(
        family_id="PF00005.27",
        force_mode="synthetic",
        seed_offset=1,
        **kwargs,
    )


def _make_restart_policy(*, policy_id: str, beta: float) -> object:
    from adaptive_reflow.contracts import (
        ArtifactHash,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    policy = FinalRestartPolicy(
        policy_id=PolicyId(policy_id),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("run-gap70-r2"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(float(beta))},
        alpha_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(1.0)},
        fresh_noise_floor_by_channel={AMINO_ACID_CATEGORICAL: FactorValue(0.0)},
        schedule_sample=None,
        freeze_admission_by_channel={AMINO_ACID_CATEGORICAL: True},
        ledger_row_id=LedgerRowId(f"ledger-{policy_id}"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )
    return replace(policy, policy_hash=hash_policy_hash(policy))


def _restart(
    adapter: LineageFlowAdapter, *, beta: float, sample_id: str = "s"
) -> tuple[np.ndarray, np.ndarray]:
    bundle = adapter.build_initial_state(batch_id="b", sample_id=sample_id)
    import hashlib

    entry = adapter._native_states.get(bundle.native_state_digest)
    seed = int(hashlib.sha256(str(sample_id).encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    theta = rng.random(np.asarray(entry["theta"]).shape)
    entry["theta"] = theta / theta.sum(axis=-1, keepdims=True)
    prior = np.asarray(
        adapter._native_states.get(bundle.native_state_digest)["theta"],
        dtype=np.float64,
    )
    policy = _make_restart_policy(policy_id=f"p-{beta}", beta=beta)
    out = adapter.apply_restart_distribution(bundle, policy)
    restarted = np.asarray(
        adapter._native_states.get(out.native_state_digest)["theta"],
        dtype=np.float64,
    )
    return prior, restarted


def test_lam_zero_restart_returns_the_prior_unchanged() -> None:
    """The "no restart" end of the segment, through the real blend math."""
    prior, restarted = _restart(
        _adapter(perturbation=TemperedFreshPerturbation(lam=0.0)), beta=0.5
    )
    np.testing.assert_allclose(restarted, prior, atol=1e-12)


def test_lam_one_moves_the_state_away_from_the_prior() -> None:
    prior, restarted = _restart(
        _adapter(perturbation=TemperedFreshPerturbation(lam=1.0)), beta=0.5
    )
    assert not np.allclose(restarted, prior)
    np.testing.assert_allclose(restarted.sum(axis=-1), 1.0, atol=1e-12)


def test_the_restart_moves_further_as_lam_rises() -> None:
    dists = []
    for lam in (0.0, 0.5, 1.0):
        prior, restarted = _restart(
            _adapter(perturbation=TemperedFreshPerturbation(lam=lam)), beta=0.5
        )
        dists.append(float(np.abs(restarted - prior).mean()))
    assert dists[0] == pytest.approx(0.0, abs=1e-12)
    assert dists[0] < dists[1] < dists[2]


def test_the_same_lam_is_record_paired() -> None:
    """Two adapters with the same policy produce the same restart."""
    a = _restart(
        _adapter(perturbation=TemperedFreshPerturbation(lam=0.3)),
        beta=0.5,
        sample_id="x",
    )
    b = _restart(
        _adapter(perturbation=TemperedFreshPerturbation(lam=0.3)),
        beta=0.5,
        sample_id="x",
    )
    np.testing.assert_array_equal(a[1], b[1])


# ---------------------------------------------------------------------------
# 4. the generator's wiring helper
# ---------------------------------------------------------------------------


def test_builder_returns_none_by_default() -> None:
    from tools.gen_lineageflow_n1000_fastas import (
        _build_restart_draw_perturbations,
    )

    assert _build_restart_draw_perturbations(
        ["PF00005.27"], lam=None, aa_vocab=20
    ) is None


def test_builder_makes_one_policy_per_family() -> None:
    from tools.gen_lineageflow_n1000_fastas import (
        _build_restart_draw_perturbations,
    )

    fams = ["PF00005.27", "PF00072.31"]
    out = _build_restart_draw_perturbations(fams, lam=0.5, aa_vocab=20)
    assert out is not None
    assert sorted(out) == sorted(fams)
    hashes = {pol.config_hash() for pol in out.values()}
    assert len(hashes) == 1  # family-independent by construction
    assert all(pol.lam == 0.5 for pol in out.values())


def test_builder_rejects_an_out_of_range_lambda() -> None:
    from tools.gen_lineageflow_n1000_fastas import (
        _build_restart_draw_perturbations,
    )

    with pytest.raises(PerturbationConfigError):
        _build_restart_draw_perturbations(["PF00005.27"], lam=1.5, aa_vocab=20)
