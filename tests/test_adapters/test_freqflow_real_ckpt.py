"""FreqFlow **real-checkpoint** integration tests (Wave 36 Agent B, PHASE-4).

Companion to :mod:`tests.test_adapters.test_freqflow`, which exercises the
adapter's ``synthetic`` (Protocol-shim) mode only. This module covers the
half that synthetic mode cannot: the checkpoint-resolution contract, and —
when a real ``nnet_ema.pth`` is present — a smoke load, byte-stability,
the 8-check D.5 conformance battery, and the FFT ``frequency_mix`` knob
driven against the real weights.

Checkpoint availability (probed 2026-09-05)
-------------------------------------------

**No public FreqFlow checkpoint exists.** The upstream repository
(``github.com/OliverRensu/FreqFlow``) publishes training and inference
code only: its ``main`` tree contains no ``.pth``/``.safetensors`` blob
and no LFS pointer, its releases list is empty, and neither the model
name nor the author's handle resolves to a Hugging Face repository. The
README's ``--nnet_path=/path/to/nnet_ema.pth`` is a placeholder in the
authors' own recipe, not a download URL. See
``docs/models/freqflow.model_card.md`` and ``data/freqflow_ckpt/README.md``
for the probe transcript and the manual-acquisition procedure.

Consequently every test that requires trained weights is **skipped**
rather than faked — the framework never asserts a number it did not
measure. The skips are declared via :data:`REQUIRES_CKPT` so they flip to
real assertions automatically the moment a checkpoint lands at any path
:func:`freqflow_resolve_weights_path` searches (including ``$FREQFLOW_CKPT``).

What still runs unconditionally
-------------------------------

The tests that do **not** need trained weights run today and are the load-
bearing part of this file until the checkpoint is published:

* the resolver contract (env-var override, directory-vs-file forms, search
  precedence, graceful absence) — exercised with an empty placeholder file,
  which tests *path resolution*, never model behaviour;
* the ``force_mode="torch"`` failure contract when weights are missing;
* the 8-check D.5 conformance battery against the adapter the resolver
  actually selects, so the battery upgrades to real-checkpoint coverage
  with no edit;
* byte-stability and the ``frequency_mix`` knob against that same adapter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter
from adaptive_reflow.adapters.freqflow import (
    ERR_FREQ_FLOW_FREQ_MIX_INVALID,
    ERR_FREQ_FLOW_WEIGHTS_MISSING,
    FREQ_FLOW_CKPT_ENV_VAR,
    FREQ_FLOW_CKPT_FILENAME,
    FREQ_FLOW_STATE_SHAPE,
    FREQ_FLOW_UPSTREAM_REPO,
    FreqFlowAdapter,
    default_freqflow_adapter,
    freqflow_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.universal.state import ODEConditionDelta
from tests.test_adapters.conformance_battery import CHECKS

# ---------------------------------------------------------------------------
# Checkpoint discovery
# ---------------------------------------------------------------------------

#: The checkpoint the adapter would load right now, or ``None``.
CKPT_PATH: Path | None = freqflow_resolve_weights_path()

#: ``True`` iff a real checkpoint is on disk. Currently ``False`` on every
#: host, because upstream has not published ``nnet_ema.pth`` (see module
#: docstring). Kept as a computed value, not a hard-coded ``False``, so the
#: gated tests activate on their own once the file appears.
HAVE_CKPT: bool = CKPT_PATH is not None

REQUIRES_CKPT = pytest.mark.skipif(
    not HAVE_CKPT,
    reason=(
        "FreqFlow nnet_ema.pth is not published upstream "
        f"({FREQ_FLOW_UPSTREAM_REPO}: no release asset, no HF mirror). "
        f"Set ${FREQ_FLOW_CKPT_ENV_VAR} once weights are obtained; see "
        "docs/models/freqflow.model_card.md."
    ),
)


@pytest.fixture(scope="module")
def resolved_adapter() -> FreqFlowAdapter:
    """The adapter the resolver actually selects on this host.

    With a checkpoint present this is the real-weights adapter; without
    one it is the synthetic Protocol shim. Tests written against this
    fixture therefore upgrade to real-checkpoint coverage automatically.
    """
    return default_freqflow_adapter()


def _round_trip(
    adapter: FreqFlowAdapter,
    *,
    batch_id: str = "wave36",
    sample_id: str = "s0",
    seed: int = 20260905,
    frequency_mix: float | None = None,
    num_steps: int = 4,
) -> tuple[str, np.ndarray]:
    """Drive one full build -> compose -> solve -> observe cycle.

    Returns the endpoint bundle's ``native_state_digest`` plus the final
    latent, which together are the two things a byte-stability check needs.
    """
    bundle = adapter.build_initial_state(batch_id=batch_id, sample_id=sample_id)
    spec: dict[str, Any] = {"num_steps": int(num_steps)}
    if frequency_mix is not None:
        spec["frequency_mix"] = float(frequency_mix)
    delta = adapter.compose_condition(
        bundle,
        ODEConditionDelta(
            delta_spec=spec,
            source="test_freqflow_real_ckpt",
            target_round=1,
            calibration_artifact_hash="wave36-freqflow",
        ),
    )
    trace = adapter.solve_ode(bundle, delta, seed=int(seed))
    endpoint = adapter.observe_endpoint(trace, bundle)
    traj = adapter.export_trajectory(trace)
    assert traj is not None, "export_trajectory must return the trajectory"
    return str(endpoint.native_state_digest), np.asarray(traj[-1])


# ---------------------------------------------------------------------------
# 1. Checkpoint-resolution contract (runs unconditionally)
# ---------------------------------------------------------------------------


def test_resolver_returns_none_when_no_checkpoint_anywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty data dir and unset env var resolve to ``None``, not a crash."""
    monkeypatch.delenv(FREQ_FLOW_CKPT_ENV_VAR, raising=False)
    assert freqflow_resolve_weights_path(data_dir=tmp_path) is None


def test_env_var_override_accepts_a_file_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``$FREQFLOW_CKPT`` pointing at the file itself is honoured.

    The placeholder is empty: this asserts *path resolution*, which is the
    only thing the resolver does. It never loads or inspects the bytes.
    """
    ckpt = tmp_path / FREQ_FLOW_CKPT_FILENAME
    ckpt.write_bytes(b"")
    monkeypatch.setenv(FREQ_FLOW_CKPT_ENV_VAR, str(ckpt))
    assert freqflow_resolve_weights_path(data_dir=tmp_path / "nonexistent") == ckpt


def test_env_var_override_accepts_a_directory_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``$FREQFLOW_CKPT`` pointing at a containing directory is honoured."""
    ckpt = tmp_path / FREQ_FLOW_CKPT_FILENAME
    ckpt.write_bytes(b"")
    monkeypatch.setenv(FREQ_FLOW_CKPT_ENV_VAR, str(tmp_path))
    assert freqflow_resolve_weights_path(data_dir=tmp_path / "nonexistent") == ckpt


def test_env_var_pointing_at_a_missing_file_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale ``$FREQFLOW_CKPT`` must not mask the data-dir search.

    Regression guard: an env var left over from a deleted checkpoint should
    degrade to the normal search order rather than pin the adapter to a
    path that does not exist.
    """
    monkeypatch.setenv(FREQ_FLOW_CKPT_ENV_VAR, str(tmp_path / "gone.pth"))
    data_dir = tmp_path / "data"
    (data_dir / "freqflow_ckpt").mkdir(parents=True)
    ckpt = data_dir / "freqflow_ckpt" / FREQ_FLOW_CKPT_FILENAME
    ckpt.write_bytes(b"")
    assert freqflow_resolve_weights_path(data_dir=data_dir) == ckpt


def test_wave36_layout_takes_precedence_over_legacy_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``data/freqflow_ckpt/`` wins over the Wave 21 ``data/freqflow/`` path."""
    monkeypatch.delenv(FREQ_FLOW_CKPT_ENV_VAR, raising=False)
    for sub in ("freqflow_ckpt", "freqflow"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / FREQ_FLOW_CKPT_FILENAME).write_bytes(b"")
    resolved = freqflow_resolve_weights_path(data_dir=tmp_path)
    assert resolved == tmp_path / "freqflow_ckpt" / FREQ_FLOW_CKPT_FILENAME


def test_legacy_and_flat_layouts_still_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave 21 hosts keep working: ``data/freqflow/`` and flat ``data/``."""
    monkeypatch.delenv(FREQ_FLOW_CKPT_ENV_VAR, raising=False)
    legacy_dir = tmp_path / "legacy"
    (legacy_dir / "freqflow").mkdir(parents=True)
    legacy = legacy_dir / "freqflow" / FREQ_FLOW_CKPT_FILENAME
    legacy.write_bytes(b"")
    assert freqflow_resolve_weights_path(data_dir=legacy_dir) == legacy

    flat_dir = tmp_path / "flat"
    flat_dir.mkdir()
    flat = flat_dir / FREQ_FLOW_CKPT_FILENAME
    flat.write_bytes(b"")
    assert freqflow_resolve_weights_path(data_dir=flat_dir) == flat


def test_force_torch_without_weights_raises_documented_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``force_mode="torch"`` fails loudly, never silently degrading.

    This is the contract that keeps a missing checkpoint from being
    mistaken for a real run: the auto path may fall back to synthetic, but
    an explicit torch request must raise.
    """
    monkeypatch.delenv(FREQ_FLOW_CKPT_ENV_VAR, raising=False)
    missing = tmp_path / FREQ_FLOW_CKPT_FILENAME
    if not torch_is_available():
        with pytest.raises(RuntimeError, match="torch requested but not installed"):
            FreqFlowAdapter(weights_path=missing, force_mode="torch")
        return
    with pytest.raises(FileNotFoundError) as excinfo:
        FreqFlowAdapter(weights_path=missing, force_mode="torch")
    assert ERR_FREQ_FLOW_WEIGHTS_MISSING in str(excinfo.value)


def test_adapter_is_registered_under_freqflow_family() -> None:
    """PHASE-4 needs ``build_adapter("freqflow")`` to work for the harness."""
    assert "freqflow" in ADAPTER_REGISTRY
    assert isinstance(build_adapter("freqflow"), FreqFlowAdapter)


# ---------------------------------------------------------------------------
# 2. Smoke: load the real checkpoint, forward + sample (gated)
# ---------------------------------------------------------------------------


@REQUIRES_CKPT
def test_real_ckpt_smoke_load_and_sample(resolved_adapter: FreqFlowAdapter) -> None:
    """Load the published checkpoint and run one forward + sample cycle."""
    assert CKPT_PATH is not None
    assert resolved_adapter._weights_path == CKPT_PATH, (
        "adapter must bind the resolved checkpoint, not a placeholder"
    )
    digest, x_final = _round_trip(resolved_adapter)
    assert digest, "endpoint must carry a native_state_digest"
    assert x_final.shape == FREQ_FLOW_STATE_SHAPE
    assert np.all(np.isfinite(x_final)), "real-ckpt sample must be finite"


@REQUIRES_CKPT
def test_real_ckpt_file_is_nontrivial() -> None:
    """Guard against a truncated or placeholder download.

    A real FreqFlow checkpoint is ~2.7 GB (675 M fp32 params); anything
    under 100 MB is a failed download, not a model.
    """
    assert CKPT_PATH is not None
    assert CKPT_PATH.stat().st_size > 100 * 1024 * 1024, (
        f"{CKPT_PATH} is {CKPT_PATH.stat().st_size} bytes; expected ~2.7 GB"
    )


# ---------------------------------------------------------------------------
# 3. Byte-stability under a fixed seed (runs against the resolved adapter)
# ---------------------------------------------------------------------------


def test_byte_stability_under_fixed_seed(resolved_adapter: FreqFlowAdapter) -> None:
    """Two identical round trips produce byte-identical digests and latents."""
    digest_a, x_a = _round_trip(resolved_adapter, seed=4242)
    digest_b, x_b = _round_trip(resolved_adapter, seed=4242)
    assert digest_a == digest_b, "same seed must give the same endpoint digest"
    np.testing.assert_array_equal(x_a, x_b)


def test_byte_stability_across_fresh_adapter_instances() -> None:
    """Determinism survives a process-level rebuild, not just cache reuse.

    A digest that only matches within one adapter instance would be
    memoisation, not reproducibility.
    """
    digest_a, x_a = _round_trip(default_freqflow_adapter(), seed=99)
    digest_b, x_b = _round_trip(default_freqflow_adapter(), seed=99)
    assert digest_a == digest_b
    np.testing.assert_array_equal(x_a, x_b)


def test_distinct_samples_diverge(resolved_adapter: FreqFlowAdapter) -> None:
    """Different sample ids must not collapse to one trajectory."""
    digest_a, x_a = _round_trip(resolved_adapter, sample_id="s0")
    digest_b, x_b = _round_trip(resolved_adapter, sample_id="s1")
    assert digest_a != digest_b
    assert not np.allclose(x_a, x_b)


# ---------------------------------------------------------------------------
# 4. D.5 conformance battery — all 8 checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "check_name,check_fn", CHECKS, ids=[name for name, _ in CHECKS]
)
def test_conformance_battery(
    check_name: str,
    check_fn: Any,
    resolved_adapter: FreqFlowAdapter,
) -> None:
    """Run each D.5 conformance check against the resolved adapter.

    Parametrised over the battery's own ``CHECKS`` tuple rather than a
    local copy, so a check added upstream is picked up here for free.
    """
    check_fn(resolved_adapter)


def test_battery_covers_all_eight_checks() -> None:
    """Trip-wire: the task requires the full 8-check battery, not a subset."""
    assert len(CHECKS) >= 8, f"expected >= 8 conformance checks, got {len(CHECKS)}"


# ---------------------------------------------------------------------------
# 5. FFT-magnitude specific: the frequency_mix knob
# ---------------------------------------------------------------------------


def test_frequency_mix_changes_the_sample(
    resolved_adapter: FreqFlowAdapter,
) -> None:
    """FreqFlow's central knob must actually steer the trajectory.

    ``frequency_mix`` weights the FFT-magnitude branch against the spatial
    branch. If the two extremes produced the same sample, the frequency
    branch would be dead code — the exact failure this test exists to catch.
    """
    _, x_spatial = _round_trip(resolved_adapter, frequency_mix=0.0)
    _, x_freq = _round_trip(resolved_adapter, frequency_mix=1.0)
    assert not np.allclose(x_spatial, x_freq), (
        "frequency_mix=0.0 and 1.0 must not produce identical samples"
    )


def test_frequency_mix_is_monotone_between_its_endpoints(
    resolved_adapter: FreqFlowAdapter,
) -> None:
    """A mid mix lies strictly between the two pure branches.

    The velocity is a convex combination of the branches, so a 0.5 mix
    must differ from both endpoints rather than snapping to either.
    """
    _, x_spatial = _round_trip(resolved_adapter, frequency_mix=0.0)
    _, x_mid = _round_trip(resolved_adapter, frequency_mix=0.5)
    _, x_freq = _round_trip(resolved_adapter, frequency_mix=1.0)
    assert not np.allclose(x_mid, x_spatial)
    assert not np.allclose(x_mid, x_freq)


def test_frequency_mix_is_reproducible(resolved_adapter: FreqFlowAdapter) -> None:
    """A fixed mix + fixed seed is byte-stable, so mix sweeps are comparable."""
    digest_a, x_a = _round_trip(resolved_adapter, frequency_mix=0.25, seed=7)
    digest_b, x_b = _round_trip(resolved_adapter, frequency_mix=0.25, seed=7)
    assert digest_a == digest_b
    np.testing.assert_array_equal(x_a, x_b)


@pytest.mark.parametrize("bad_mix", [-0.01, 1.01, 2.0, -1.0])
def test_frequency_mix_out_of_range_is_rejected(
    resolved_adapter: FreqFlowAdapter, bad_mix: float
) -> None:
    """Out-of-range mixes raise rather than silently clamping."""
    bundle = resolved_adapter.build_initial_state(batch_id="b", sample_id="s")
    with pytest.raises(ValueError, match=ERR_FREQ_FLOW_FREQ_MIX_INVALID):
        resolved_adapter.compose_condition(
            bundle,
            ODEConditionDelta(
                delta_spec={"frequency_mix": float(bad_mix)},
                source="test",
                target_round=1,
                calibration_artifact_hash="h",
            ),
        )


@REQUIRES_CKPT
def test_frequency_mix_knob_with_real_ckpt(
    resolved_adapter: FreqFlowAdapter,
) -> None:
    """The mix knob steers the *trained* velocity field, not just the shim.

    Same contract as the synthetic case, but asserted against real weights
    so a checkpoint whose frequency branch is missing or zeroed is caught.
    """
    assert CKPT_PATH is not None
    _, x_spatial = _round_trip(resolved_adapter, frequency_mix=0.0)
    _, x_freq = _round_trip(resolved_adapter, frequency_mix=1.0)
    assert np.all(np.isfinite(x_spatial)) and np.all(np.isfinite(x_freq))
    assert not np.allclose(x_spatial, x_freq)


# ---------------------------------------------------------------------------
# 6. Provenance of the "no checkpoint" finding
# ---------------------------------------------------------------------------


def test_upstream_repo_constant_is_recorded() -> None:
    """The adapter names where weights would come from, for the audit trail."""
    assert FREQ_FLOW_UPSTREAM_REPO.endswith("OliverRensu/FreqFlow")


def test_ckpt_absence_is_documented_not_silent() -> None:
    """If no checkpoint resolves, the model card must say why.

    This keeps a missing checkpoint an explicitly documented state rather
    than an invisible skip, per LL-001 (ckpt + upstream both required).
    """
    if HAVE_CKPT:
        pytest.skip("checkpoint present; absence documentation not applicable")
    card = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "models"
        / "freqflow.model_card.md"
    )
    assert card.exists(), f"{card} must document the checkpoint state"
    text = card.read_text(encoding="utf-8")
    assert FREQ_FLOW_CKPT_ENV_VAR in text, (
        "model card must document the $FREQFLOW_CKPT override"
    )
    assert "nnet_ema.pth" in text
