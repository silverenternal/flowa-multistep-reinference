"""GAP-53 — batched endpoints and per-molecule restart blends.

The upstream ``n_molecules > 1`` path caches ``traj_*_batch`` and does
NOT populate the legacy ``traj_*`` keys. ``observe_endpoint`` used to
read ``traj_x`` unconditionally, so a multi-round restart at batch size
> 1 either raised ``KeyError`` or silently observed the wrong state
(the R=2 smoke produced byte-identical ``fg_dev`` for both arms).

These CPU tests pin the contract:

* ``observe_endpoint`` returns a per-molecule endpoint with a leading
  molecule axis and ``n_molecules`` on the cached entry;
* ``apply_restart_distribution`` blends each molecule with its own
  fresh draw (molecules do not collapse onto one another);
* a re-solve consumes the blended bundle and produces a batch;
* the single-molecule path keeps its 2-D endpoint (D.4 stability).
"""
from __future__ import annotations

import numpy as np

from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
from adaptive_reflow.universal.state import ODEConditionDelta


def _adapter() -> FlowMol3V2Adapter:
    return FlowMol3V2Adapter(backend="numpy", num_steps=4)


def _condition(num_steps: int = 4, target_round: int = 0) -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={"num_steps": int(num_steps)},
        source="gap53_test",
        target_round=int(target_round),
        calibration_artifact_hash="gap53-test",
    )


def _policy(beta: float = 0.5) -> object:
    from adaptive_reflow.contracts import (
        ArtifactHash,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        PolicyId,
        RunId,
    )
    from adaptive_reflow.universal.state import ChannelName

    coord = ChannelName("coordinate")
    charge = ChannelName("charge")
    pair = ChannelName("raw_pair")
    return FinalRestartPolicy(
        policy_id=PolicyId("gap53-batch-policy"),
        writer_id="inference.adaptive_reflow",
        run_id=RunId("gap53-batch-run"),
        target_round=0,
        outer_cycle_id=0,
        beta_by_channel={
            coord: FactorValue(float(beta)),
            charge: FactorValue(float(beta)),
            pair: FactorValue(float(beta)),
        },
        alpha_by_channel={
            coord: FactorValue(1.0),
            charge: FactorValue(1.0),
            pair: FactorValue(1.0),
        },
        fresh_noise_floor_by_channel={
            coord: FactorValue(0.0),
            charge: FactorValue(0.0),
            pair: FactorValue(0.0),
        },
        schedule_sample=None,
        freeze_admission_by_channel={coord: True, charge: True, pair: True},
        ledger_row_id=LedgerRowId("gap53-batch-ledger"),
        policy_hash=ArtifactHash(""),
        created_at_round=0,
        beta_from_schedule=False,
    )


def test_observe_endpoint_reads_the_batched_lineage() -> None:
    adapter = _adapter()
    bundle = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    trace = adapter.solve_ode(bundle, _condition(), seed=11, n_molecules=4)
    endpoint = adapter.observe_endpoint(trace, bundle)
    entry = adapter._native_states[endpoint.native_state_digest]
    n = int(entry["n_atoms"])
    assert entry["n_molecules"] == 4
    assert np.asarray(entry["x"]).shape == (4, n, 3)
    assert np.asarray(entry["c"]).shape == (4, n)
    assert np.asarray(entry["a"]).shape == (4, n)
    assert np.asarray(entry["e"]).shape == (4, n, n)


def test_batch_restart_blends_each_molecule_independently() -> None:
    adapter = _adapter()
    bundle = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    trace = adapter.solve_ode(bundle, _condition(), seed=11, n_molecules=4)
    endpoint = adapter.observe_endpoint(trace, bundle)
    ep_entry = adapter._native_states[endpoint.native_state_digest]

    restarted = adapter.apply_restart_distribution(endpoint, _policy())
    out = adapter._native_states[restarted.native_state_digest]

    x0 = np.asarray(ep_entry["x"])
    x1 = np.asarray(out["x"])
    assert out["n_molecules"] == 4
    assert x1.shape == x0.shape
    # Every molecule moved (the blend is active on all batch slots).
    # Padded rows can stay zero when the fresh draw is shorter, so check
    # per molecule rather than elementwise.
    for mol_idx in range(4):
        assert np.any(np.abs(x1[mol_idx] - x0[mol_idx]) > 0.0)
    # ... and the per-molecule fresh draws differ, so the batch does not
    # collapse onto a single molecule.
    assert not np.allclose(x1[0], x1[1])
    assert not np.allclose(x1[1], x1[2])


def test_batch_restart_re_solves_the_blended_bundle() -> None:
    adapter = _adapter()
    bundle = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    trace = adapter.solve_ode(bundle, _condition(2), seed=11, n_molecules=4)
    endpoint = adapter.observe_endpoint(trace, bundle)
    restarted = adapter.apply_restart_distribution(endpoint, _policy())
    trace2 = adapter.solve_ode(
        restarted, _condition(2, target_round=1), seed=11, n_molecules=4,
    )
    lineage = adapter.export_trajectory(trace2)
    assert lineage is not None
    assert np.asarray(lineage["traj_x_batch"]).shape[0] == 4


def test_single_molecule_endpoint_keeps_the_legacy_shape() -> None:
    adapter = _adapter()
    bundle = adapter.build_initial_state(batch_id="b0", sample_id="s0")
    trace = adapter.solve_ode(bundle, _condition(), seed=11, n_molecules=1)
    endpoint = adapter.observe_endpoint(trace, bundle)
    entry = adapter._native_states[endpoint.native_state_digest]
    assert entry["n_molecules"] == 1
    assert np.asarray(entry["x"]).ndim == 2
    assert np.asarray(entry["e"]).ndim == 2
