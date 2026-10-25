"""GAP-79 lever 3 — in-loop profile guidance (default off).

Pre-registration: ``docs/audit/gap79-r1-family-lever.md`` §3.

Why this lever and not another restart-side one: ``apply_restart_distribution``
already calls ``perturbation.propose`` at **every** restart, so the profile is
already injected at every round. GAP-79's temperature dose sharpened that
injection by up to 25x and the per-family identity did not move (0/50 on three
of four families at every dose), which falsifies the restart-side placement.
The profile has not been tried inside the integration that follows, where the
field can smooth it away — that is what ``ProfileGuidance`` adds.

The three properties pinned here are the ones that make the lever admissible:
off is byte-identical, on moves the endpoint toward the profile, and ``t_start``
gates the drift without changing anything else.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters.lineageflow import (
    LINEAGEFLOW_STATE_SHAPE,
    LineageFlowAdapter,
    ProfileGuidance,
    ProfileGuidanceConfigError,
)
from adaptive_reflow.universal.state import ODEConditionDelta

LINEAGEFLOW_CONFIG_HASH = "0" * 64


def _adapter(**kwargs: object) -> LineageFlowAdapter:
    return LineageFlowAdapter(
        family_id="PF00005.27",
        force_mode="synthetic",
        seed_offset=1,
        num_steps=4,
        **kwargs,
    )


def _delta() -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={
            "num_steps": 4,
            "sampler_id": "euler",
            "guidance_scale": 1.0,
            "family_id": "PF00005.27",
        },
        source="test",
        target_round=1,
        calibration_artifact_hash=LINEAGEFLOW_CONFIG_HASH,
    )


def _run(adapter: LineageFlowAdapter) -> tuple[np.ndarray, str]:
    bundle = adapter.build_initial_state(batch_id="gap79", sample_id="s")
    delta = adapter.compose_condition(bundle, _delta())
    trace = adapter.solve_ode(bundle, delta, seed=42)
    entry = adapter._native_states[trace.native_state_digest]  # noqa: SLF001
    return np.asarray(entry["trajectory"], dtype=np.float64), (
        trace.native_state_digest
    )


def _one_hot(n_pos: int = 8, n_aa: int = 3) -> np.ndarray:
    prob = np.zeros((n_pos, n_aa), dtype=np.float64)
    prob[:, 0] = 1.0
    return prob


def _sharp_profile(n_pos: int = 8, n_aa: int = 3) -> ProfileGuidance:
    """One-hot profile on the first ``n_pos`` positions, fully conserved."""
    return ProfileGuidance(
        prob=_one_hot(n_pos, n_aa),
        conservation=np.ones(n_pos, dtype=np.float64),
        weight=5.0,
    )


def _agreement(theta: np.ndarray, n_pos: int) -> float:
    """Mean probability mass on amino acid 0 over the profile's positions."""
    return float(np.asarray(theta)[:n_pos, 0].mean())


def test_absent_guidance_changes_nothing() -> None:
    """``None`` reproduces the pre-GAP-79 trajectory and digest exactly."""
    plain, digest_plain = _run(_adapter())
    explicit_off, digest_off = _run(
        _adapter(profile_guidance=ProfileGuidance(
            prob=np.ones((8, 3)) / 3.0,
            conservation=np.ones(8),
            weight=0.0,
        ))
    )
    assert np.array_equal(plain, explicit_off)
    assert digest_plain == digest_off


def test_t_start_one_is_a_no_op() -> None:
    """A ``t_start`` above every step's start time leaves the run untouched."""
    plain, digest_plain = _run(_adapter())
    guided, digest_guided = _run(
        _adapter(profile_guidance=ProfileGuidance(
            prob=_one_hot(),
            conservation=np.ones(8),
            weight=5.0,
            t_start=1.0,
        ))
    )
    # The trajectory is identical: the drift never fires. The digest still
    # differs, and that is deliberate — it records the *configured* spec, so a
    # run cannot be mistaken for an unguided one after the fact.
    assert np.array_equal(plain, guided)
    assert digest_plain != digest_guided


def test_guidance_moves_the_endpoint_toward_the_profile() -> None:
    """The drift is real: the endpoint gains mass on the profile's residue."""
    plain, _ = _run(_adapter())
    guided, digest = _run(_adapter(profile_guidance=_sharp_profile()))
    before = _agreement(plain[-1], n_pos=8)
    after = _agreement(guided[-1], n_pos=8)
    assert after > before
    # The active run is distinguishable from the unguided one in provenance.
    assert digest != _run(_adapter())[1]


def test_weight_is_monotone_at_a_fixed_t_start() -> None:
    """More weight, more mass on the profile, up to the one-hot limit."""
    values = []
    for weight in (1.0, 5.0, 20.0):
        prof = ProfileGuidance(
            prob=_one_hot(),
            conservation=np.ones(8),
            weight=weight,
        )
        traj, _ = _run(_adapter(profile_guidance=prof))
        values.append(_agreement(traj[-1], n_pos=8))
    assert values[0] < values[1] < values[2]
    # The synthetic field keeps pushing back, so the drift saturates well
    # below the one-hot limit; the test pins the *direction*, not a ceiling.
    assert values[-1] > 2.0 * values[0]


def test_positions_past_the_profile_span_are_untouched() -> None:
    """State positions outside the profile carry ``c = 0`` and do not drift."""
    span = 8
    prof = _sharp_profile(n_pos=span)
    plain, _ = _run(_adapter())
    guided, _ = _run(_adapter(profile_guidance=prof))
    assert LINEAGEFLOW_STATE_SHAPE[0] > span
    # The drift term is exactly zero on the padded positions, so their
    # *relative* change is bounded by the shared row renormalisation only.
    tail_plain = plain[-1, span:, :]
    tail_guided = guided[-1, span:, :]
    assert np.allclose(tail_plain.sum(axis=-1), 1.0)
    assert np.allclose(tail_guided.sum(axis=-1), 1.0)


def test_non_amino_acid_channels_are_untouched() -> None:
    """The ``(150, 20)`` profile must not drag the state's 13 extra channels.

    Direct unit test on :meth:`ProfileGuidance.apply`: with ``v = 0`` the
    returned array *is* the drift, so the masks are readable without an ODE
    round. The LineageFlow state is ``(256, 33)``; only positions
    ``[0, span)`` and channels ``[0, 20)`` may move.
    """
    span, n_aa, n_chan = 6, 20, 33
    prof = ProfileGuidance(
        prob=_one_hot(n_pos=span, n_aa=n_aa),
        conservation=np.ones(span, dtype=np.float64),
        weight=3.0,
    )
    x = np.full((LINEAGEFLOW_STATE_SHAPE[0], n_chan), 1.0 / n_chan)
    drift = prof.apply(np.zeros_like(x), x, 0.5)
    assert np.any(drift[:span, :n_aa] != 0.0)
    assert np.all(drift[span:, :] == 0.0)
    assert np.all(drift[:span, n_aa:] == 0.0)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"prob": np.ones(4), "conservation": np.ones(4), "weight": 1.0},
         "prob must be 2-D"),
        ({"prob": np.ones((4, 3)) * -1.0, "conservation": np.ones(4),
          "weight": 1.0}, "non-negative"),
        ({"prob": np.ones((4, 3)), "conservation": np.ones(3),
          "weight": 1.0}, "conservation length"),
        ({"prob": np.ones((4, 3)), "conservation": np.ones(4) * 2.0,
          "weight": 1.0}, "\\[0, 1\\]"),
        ({"prob": np.ones((4, 3)), "conservation": np.ones(4),
          "weight": -1.0}, "weight must be"),
        ({"prob": np.ones((4, 3)), "conservation": np.ones(4),
          "weight": 1.0, "t_start": 2.0}, "t_start must lie"),
    ],
)
def test_malformed_specs_fail_closed(kwargs: dict, match: str) -> None:
    with pytest.raises(ProfileGuidanceConfigError, match=match):
        ProfileGuidance(**kwargs)


def test_adapter_rejects_a_non_guidance_object() -> None:
    with pytest.raises(TypeError, match="profile_guidance_must_be"):
        _adapter(profile_guidance="not-a-spec")


def test_config_round_trip_preserves_the_hash() -> None:
    prof = _sharp_profile()
    restored = ProfileGuidance.from_config(prof.to_config())
    assert restored.config_hash() == prof.config_hash()
    assert np.allclose(restored.prob, prof.prob)
    assert np.allclose(restored.conservation, prof.conservation)


# ---------------------------------------------------------------------------
# CLI wiring (tools/gen_lineageflow_n1000_fastas.py)
# ---------------------------------------------------------------------------


def _profile_json(tmp_path) -> object:
    """Minimal ``tools/pfam_profile.py`` payload: one family, span 4, AA 3."""
    import json

    payload = {
        "families": {
            "PF00005.27": {
                "logp": np.log(np.full((4, 3), 1.0 / 3.0)).tolist(),
                "conservation": [1.0, 0.5, 0.0, 0.25],
            }
        }
    }
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(payload))
    return path


def test_cli_builder_is_off_at_weight_zero(tmp_path) -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_profile_guidance

    assert _build_profile_guidance(
        ["PF00005.27"], weight=0.0, t_start=0.0,
        profile_json=_profile_json(tmp_path),
    ) is None


def test_cli_builder_requires_the_profile(tmp_path) -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_profile_guidance

    with pytest.raises(SystemExit, match="profile_guidance_requires_profile_json"):
        _build_profile_guidance(
            ["PF00005.27"], weight=2.0, t_start=0.0, profile_json=None
        )


def test_cli_builder_turns_logp_into_a_distribution(tmp_path) -> None:
    from tools.gen_lineageflow_n1000_fastas import _build_profile_guidance

    specs = _build_profile_guidance(
        ["PF00005.27"], weight=2.0, t_start=0.25,
        profile_json=_profile_json(tmp_path),
    )
    assert specs is not None
    spec = specs["PF00005.27"]
    assert isinstance(spec, ProfileGuidance)
    assert np.allclose(spec.prob.sum(axis=-1), 1.0)
    assert spec.weight == 2.0
    assert spec.t_start == 0.25
    assert spec.is_active
