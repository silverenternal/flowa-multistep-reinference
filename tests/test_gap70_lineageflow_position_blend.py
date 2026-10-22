"""GAP-70 (re-scoped to LineageFlow) — per-position restart blend.

Pre-registration: ``docs/audit/gap70-lineageflow-position-blend.md`` §0. The
operator is ``m_vec = m * w`` with ``w`` a per-family constant vector supplied at
construction; ``w = 1`` reproduces the scalar blend exactly and ``w = 0`` makes
the restart independent of the prior.

Why LineageFlow and not Kanzi: K7 is a LineageFlow cell
(``docs/audit/gap70-kanzi-latent.md`` §0.2 P1), so a Kanzi blend cannot move it.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow import (
    AMINO_ACID_CATEGORICAL,
    LINEAGEFLOW_STATE_SHAPE,
    LineageFlowAdapter,
)


def _adapter(**kwargs: object) -> LineageFlowAdapter:
    return LineageFlowAdapter(
        family_id="PF00005.27",
        force_mode="synthetic",
        seed_offset=1,
        **kwargs,
    )


def _make_final_policy(*, policy_id: str, beta: float) -> object:
    from adaptive_reflow.contracts import (
        ArtifactHash,
        ChannelName,
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
        run_id=RunId("run-gap70-lf"),
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
    adapter: LineageFlowAdapter,
    *,
    beta: float,
    sample_id: str = "s",
    nonuniform: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """One restart. ``nonuniform`` replaces the synthetic near-uniform state.

    The synthetic adapter's ``theta`` is uniform to ~1e-7, so *every* blend of it
    with the near-uniform fresh draw is numerically a no-op — the same "wired but
    inert" trap GAP-44 documented. Tests that need to see the operator must give
    it a state where the prior and the fresh draw actually differ.
    """
    bundle = adapter.build_initial_state(batch_id="b", sample_id=sample_id)
    if nonuniform:
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
    policy = _make_final_policy(policy_id=f"p-{beta}", beta=beta)
    out = adapter.apply_restart_distribution(bundle, policy)
    restarted = np.asarray(
        adapter._native_states.get(out.native_state_digest)["theta"],
        dtype=np.float64,
    )
    return prior, restarted


# ---------------------------------------------------------------------------
# 1. default off
# ---------------------------------------------------------------------------


def test_default_keeps_the_scalar_blend() -> None:
    plain = _adapter()
    assert plain._token_keep_weights is None
    _, a = _restart(plain, beta=0.5)
    _, b = _restart(_adapter(), beta=0.5)
    np.testing.assert_array_equal(a, b)
    # Still a valid per-position distribution.
    np.testing.assert_allclose(a.sum(axis=-1), 1.0, atol=1e-12)


# ---------------------------------------------------------------------------
# 2. the operator
# ---------------------------------------------------------------------------


def test_uniform_weights_reproduce_the_scalar_blend() -> None:
    ones = np.ones(LINEAGEFLOW_STATE_SHAPE[0])
    _, plain = _restart(_adapter(), beta=0.5, nonuniform=True)
    _, selective = _restart(
        _adapter(token_keep_weights=ones), beta=0.5, nonuniform=True
    )
    np.testing.assert_array_equal(plain, selective)


def test_zero_weights_make_the_restart_prior_independent() -> None:
    zeros = np.zeros(LINEAGEFLOW_STATE_SHAPE[0])
    adapter = _adapter(token_keep_weights=zeros)
    prior_a, x_a = _restart(adapter, beta=0.5, sample_id="a", nonuniform=True)
    prior_b, x_b = _restart(adapter, beta=0.5, sample_id="b", nonuniform=True)
    assert not np.allclose(prior_a, prior_b)
    np.testing.assert_array_equal(x_a, x_b)


def test_partial_weights_land_between_the_two_ends() -> None:
    n = LINEAGEFLOW_STATE_SHAPE[0]
    half = np.zeros(n)
    half[: n // 2] = 1.0
    _, x_half = _restart(
        _adapter(token_keep_weights=half), beta=0.5, nonuniform=True
    )
    _, x_full = _restart(
        _adapter(token_keep_weights=np.ones(n)), beta=0.5, nonuniform=True
    )
    _, x_zero = _restart(
        _adapter(token_keep_weights=np.zeros(n)), beta=0.5, nonuniform=True
    )
    assert not np.allclose(x_half, x_full)
    assert not np.allclose(x_half, x_zero)
    np.testing.assert_allclose(x_half.sum(axis=-1), 1.0, atol=1e-12)


def test_memory_is_redistributed_per_position_not_averaged() -> None:
    """The operator is ``m_vec = m * w``, *not* ``mean(m * w)``.

    Endpoint tests cannot see the difference: ``w ≡ 1`` and ``w ≡ 0`` agree
    under both readings. This one reconstructs the fresh draw from the scalar
    run and pins the per-position blend, then asserts the scalar-collapsed
    hypothesis is rejected — the regression that the first wiring of this
    operator actually shipped (the token branch fell through into the scalar
    ``else``).
    """
    n = LINEAGEFLOW_STATE_SHAPE[0]
    beta = 0.5
    m = 1.0 - beta  # memory_fraction_for: max(1 - beta, floor)
    w = np.zeros(n)
    w[::2] = 1.0

    prior, y_scalar = _restart(_adapter(), beta=beta, nonuniform=True)
    _, y_vec = _restart(
        _adapter(token_keep_weights=w), beta=beta, nonuniform=True
    )
    fresh = (y_scalar - m * prior) / (1.0 - m)
    m_vec = (m * w).reshape(-1, 1)
    expected = m_vec * prior + (1.0 - m_vec) * fresh
    np.testing.assert_allclose(y_vec, expected, atol=1e-10)

    collapsed = (m * w).mean()
    scalar_hypothesis = collapsed * prior + (1.0 - collapsed) * fresh
    assert not np.allclose(y_vec, scalar_hypothesis, atol=1e-6)


# ---------------------------------------------------------------------------
# 3. validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("weights", "code"),
    [
        (np.ones(LINEAGEFLOW_STATE_SHAPE[0] - 1), "wrong_length"),
        (np.full(LINEAGEFLOW_STATE_SHAPE[0], 1.5), "out_of_unit_interval"),
        (np.full(LINEAGEFLOW_STATE_SHAPE[0], -0.5), "out_of_unit_interval"),
        (np.full(LINEAGEFLOW_STATE_SHAPE[0], np.nan), "nonfinite"),
    ],
)
def test_malformed_weights_are_rejected(weights: np.ndarray, code: str) -> None:
    with pytest.raises(ValueError, match=code):
        _adapter(token_keep_weights=weights)


def test_mutually_exclusive_with_the_classifier_aware_path() -> None:
    with pytest.raises(ValueError, match="mutually_exclusive"):
        _adapter(
            token_keep_weights=np.ones(LINEAGEFLOW_STATE_SHAPE[0]),
            classifier_aware_restart=True,
        )


# ---------------------------------------------------------------------------
# 4. the generator-side weight builder
# ---------------------------------------------------------------------------


def _profile_json(tmp_path: object) -> object:
    import json
    from pathlib import Path

    payload = {
        "families": {
            "PF00005.27": {"conservation": [0.0, 0.5, 1.0]},
            "PF00072.24": {"conservation": [1.0, 0.0, 0.25]},
        }
    }
    path = Path(str(tmp_path)) / "profiles.json"
    path.write_text(json.dumps(payload))
    return path


def test_weight_builder_off_returns_none() -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_token_keep_weights

    assert (
        _build_token_keep_weights(
            ["PF00005.27"], mode="off", profile_json=None
        )
        is None
    )


def test_weight_builder_is_the_complement_of_conservation(tmp_path: object) -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_token_keep_weights

    out = _build_token_keep_weights(
        ["PF00005.27", "PF00072.24"],
        mode="conservation",
        profile_json=_profile_json(tmp_path),
    )
    assert set(out) == {"PF00005.27", "PF00072.24"}
    for w in out.values():
        assert w.shape == (LINEAGEFLOW_STATE_SHAPE[0],)
        assert float(w.min()) >= 0.0 and float(w.max()) <= 1.0
    # Endpoints map exactly: conservation 0 -> keep 1, conservation 1 -> keep 0.
    assert out["PF00005.27"][0] == pytest.approx(1.0)
    assert out["PF00005.27"][-1] == pytest.approx(0.0)
    assert out["PF00072.24"][0] == pytest.approx(0.0)
    assert out["PF00072.24"][-1] == pytest.approx(0.75)


def test_weight_builder_rejects_missing_family(tmp_path: object) -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_token_keep_weights

    with pytest.raises(SystemExit, match="profile_missing_family"):
        _build_token_keep_weights(
            ["PF00183.19"],
            mode="conservation",
            profile_json=_profile_json(tmp_path),
        )


def test_weight_builder_requires_the_profile() -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_token_keep_weights

    with pytest.raises(SystemExit, match="requires_profile_json"):
        _build_token_keep_weights(
            ["PF00005.27"], mode="conservation", profile_json=None
        )
