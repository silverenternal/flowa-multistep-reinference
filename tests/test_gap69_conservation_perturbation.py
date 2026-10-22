"""GAP-69 — profile-aware perturbation is opt-in, pure, and correctly wired.

Six properties, matching the gap's acceptance criteria:

1. ``c = 0`` reproduces the D-004b ``softmax(randn)`` draw **bit for bit** for
   the same seed — the conservation weighting is the only change;
2. ``c = 1`` reproduces the Pfam match emission itself, so the argmax recovers
   the HMM consensus at every column;
3. the draw is per-record: same seed ⇒ identical, different seed ⇒ different;
4. every row is a valid simplex of ``(L, K)`` shape and ``x_saturated`` is not
   mutated;
5. the LineageFlow adapter routes through ``propose_with_seed`` when the policy
   exposes it (the per-record, per-round ``restart_seed``), and the default
   ``UniformFreshPerturbation`` path stays untouched;
6. the generator's ``--init-profile off`` path returns ``None`` — i.e. no
   perturbation object, so every pre-GAP-69 call is byte-identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.lineageflow import (  # noqa: E402
    LINEAGEFLOW_AA_VOCAB,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_VOCAB_SIZE,
    LineageFlowAdapter,
    _synthesize_random_simplex,
)
from adaptive_reflow.algorithm.perturbation import (  # noqa: E402
    ConservationWeightedPerturbation,
    PerturbationConfigError,
    UniformFreshPerturbation,
    build_perturbation_from_config,
)

SPAN = 12
AA = LINEAGEFLOW_AA_VOCAB
L = int(LINEAGEFLOW_STATE_SHAPE[0])
K = int(LINEAGEFLOW_VOCAB_SIZE)


def _profile(*, conservation: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """A deterministic ``(SPAN, AA)`` log-prob profile with a known consensus."""
    rng = np.random.default_rng(7)
    logits = rng.standard_normal((SPAN, AA)) * 2.0
    logits = logits - logits.max(axis=-1, keepdims=True)
    p = np.exp(logits)
    p = p / p.sum(axis=-1, keepdims=True)
    logp = np.log(p)
    cons = np.full(SPAN, float(conservation))
    return logp, cons


def _policy(conservation: float = 0.0) -> ConservationWeightedPerturbation:
    logp, cons = _profile(conservation=conservation)
    return ConservationWeightedPerturbation(logp=logp, conservation=cons)


def test_zero_conservation_is_the_d004b_draw() -> None:
    """``c = 0`` must equal ``_synthesize_random_simplex`` for the same seed."""
    policy = _policy(conservation=0.0)
    x = np.full((L, K), 1.0 / K, dtype=np.float64)
    got = policy.propose_with_seed(x, None, 0.0, 4242)
    want = _synthesize_random_simplex(np.random.default_rng(4242))
    assert got.shape == (L, K)
    np.testing.assert_allclose(got, want, rtol=0.0, atol=0.0)


def test_full_conservation_recovers_the_profile_consensus() -> None:
    """``c = 1`` must reproduce the emission, so argmax = profile consensus."""
    logp, cons = _profile(conservation=1.0)
    policy = ConservationWeightedPerturbation(logp=logp, conservation=cons)
    x = np.full((L, K), 1.0 / K, dtype=np.float64)
    got = policy.propose_with_seed(x, None, 0.0, 1)
    consensus = logp.argmax(axis=-1)
    np.testing.assert_array_equal(got[:SPAN, :AA].argmax(axis=-1), consensus)


def test_draw_is_per_record_and_deterministic() -> None:
    policy = _policy(conservation=0.3)
    x = np.full((L, K), 1.0 / K, dtype=np.float64)
    a = policy.propose_with_seed(x, None, 0.0, 1234)
    b = policy.propose_with_seed(x, None, 0.0, 1234)
    c = policy.propose_with_seed(x, None, 0.0, 9999)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)


def test_rows_stay_on_the_simplex_and_input_is_not_mutated() -> None:
    policy = _policy(conservation=0.5)
    x = np.full((L, K), 1.0 / K, dtype=np.float64)
    before = x.copy()
    got = policy.propose_with_seed(x, None, 0.0, 7)
    np.testing.assert_array_equal(x, before)
    assert float(got.min()) >= 0.0
    np.testing.assert_allclose(got.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)


def test_config_round_trip() -> None:
    policy = _policy(conservation=0.4)
    rebuilt = build_perturbation_from_config(policy.to_config())
    assert isinstance(rebuilt, ConservationWeightedPerturbation)
    assert rebuilt.config_hash() == policy.config_hash()


def test_invalid_construction_is_rejected() -> None:
    logp, cons = _profile(conservation=0.2)
    with pytest.raises(PerturbationConfigError):
        ConservationWeightedPerturbation(logp=logp, conservation=cons[:-1])
    with pytest.raises(PerturbationConfigError):
        ConservationWeightedPerturbation(
            logp=logp, conservation=np.full(SPAN, 1.5)
        )


def test_adapter_prefers_propose_with_seed() -> None:
    """The adapter must hand the per-record ``restart_seed`` to the policy."""
    calls: list[int] = []

    class _RecordingPolicy:
        FAMILY = "recording"

        def propose(self, x_saturated, paper_quantities, t):  # noqa: ANN001
            raise AssertionError("propose() must not be used when the hook exists")

        def propose_with_seed(self, x_saturated, paper_quantities, t, seed):  # noqa: ANN001
            calls.append(int(seed))
            return np.asarray(x_saturated, dtype=np.float64).copy()

    adapter = LineageFlowAdapter(
        family_id="PF00005.27",
        force_mode="synthetic",
        seed_offset=42,
        perturbation=_RecordingPolicy(),
    )
    bundle, _ = _initial_bundle(adapter)
    policy = _restart_policy()
    adapter.apply_restart_distribution(bundle, policy)
    assert len(calls) == 1


def test_default_uniform_policy_path_is_unchanged() -> None:
    """``UniformFreshPerturbation`` still takes the preserved inline branch."""
    adapter = LineageFlowAdapter(
        family_id="PF00005.27",
        force_mode="synthetic",
        seed_offset=42,
        perturbation=UniformFreshPerturbation(),
    )
    bundle, _ = _initial_bundle(adapter)
    out = adapter.apply_restart_distribution(bundle, _restart_policy())
    assert out is not None


def test_generator_off_path_returns_none() -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_init_perturbations

    assert _build_init_perturbations(
        ["PF00005.27"], init_profile="off", profile_json=None
    ) is None


def test_generator_conservation_path_builds_one_policy_per_family() -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_init_perturbations

    profile_json = REPO_ROOT / "verification_outputs" / "gap69-lineageflow-profile" / "profiles.json"
    if not profile_json.exists():
        pytest.skip("profile_json_not_generated")
    fams = ["PF00005.27", "PF00072.24"]
    got = _build_init_perturbations(
        fams, init_profile="conservation", profile_json=profile_json
    )
    assert got is not None
    assert set(got) == set(fams)
    assert all(isinstance(v, ConservationWeightedPerturbation) for v in got.values())


# -- helpers ---------------------------------------------------------------


def _initial_bundle(adapter: LineageFlowAdapter):
    from adaptive_reflow.universal.state import ODEConditionDelta

    condition = ODEConditionDelta(
        delta_spec={"num_steps": 2, "sampler_id": "euler"},
        source="test_gap69",
        target_round=0,
        calibration_artifact_hash="test_gap69:default",
    )
    bundle = adapter.build_initial_state(
        batch_id="test", sample_id="0"
    )
    return bundle, condition


def _restart_policy():
    from adaptive_reflow.contracts.authority import FinalRestartPolicy

    return FinalRestartPolicy(
        policy_id="test",
        writer_id="inference.adaptive_reflow",
        run_id="test-gap69",
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={"amino_acid_categorical": 1.0},
        alpha_by_channel={"amino_acid_categorical": 1.0},
        fresh_noise_floor_by_channel={"amino_acid_categorical": 0.0},
        schedule_sample=None,
        freeze_admission_by_channel={},
        ledger_row_id="test",
        policy_hash="test-hash",
        created_at_round=0,
    )


def test_profile_arm_refuses_to_silently_degrade() -> None:
    """GAP-69 — a bare-RNG fallback inside a profile arm must fail closed.

    Observed on 2026-10-22: a CUDA OOM made ``_write_framework_arm`` substitute
    the bare-RNG draw for 1000/1000 records, and the run still wrote a manifest
    that looked valid (181 hits vs the baseline's 158). That is not the profile
    arm and must never reach scoring.
    """
    from tools.gen_lineageflow_n1000_fastas import _assert_no_profile_fallback

    # Default path: fallbacks are tolerated (pre-GAP-69 behaviour).
    _assert_no_profile_fallback(None, {"PF00005.27": 3}, n=10)
    # Profile arm with a clean run: fine.
    _assert_no_profile_fallback({"PF00005.27": object()}, {}, n=10)
    # Profile arm with any fallback: hard stop.
    with pytest.raises(SystemExit) as exc:
        _assert_no_profile_fallback(
            {"PF00005.27": object()}, {"PF00005.27": 10}, n=10
        )
    assert "gap69_profile_arm_fell_back_to_bare_rng" in str(exc.value)
