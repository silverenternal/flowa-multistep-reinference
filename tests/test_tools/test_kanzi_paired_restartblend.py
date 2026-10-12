"""CPU tests for tools/sweep_kanzi_paired_restartblend.py (GAP-23 F1 driver).

Exercised entirely on the synthetic Kanzi adapter (no torch / no upstream
``kanzi`` package needed) with an injected ``metric_fn``; the real
autoencoder round-trip metric is validated by the bounded GPU run.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

import tools.sweep_kanzi_paired_restartblend as drv
from adaptive_reflow.adapters.kanzi import default_kanzi_adapter
from adaptive_reflow.universal.state import ODEConditionDelta
from tools.eval.baseline import (
    _build_initial_state_and_condition,
    _solve_baseline,
)
from tools.eval.framework import _solve_framework, _stash_endpoint_as_x0


def _metric(endpoint: object, seq_idx: int | None = None) -> float:
    """Deterministic stand-in for the autoencoder round-trip RMSD."""
    arr = np.asarray(endpoint, dtype=np.float64)
    return float(np.mean(np.abs(arr)) + 0.01 * np.std(arr))


def _adapter() -> object:
    return default_kanzi_adapter(force_mode="synthetic", num_steps=6)


# ---------------------------------------------------------------------------
# Eq. 2 fidelity: the restart blend consumes the previous ENDPOINT
# ---------------------------------------------------------------------------


def test_stash_endpoint_as_x0_writes_endpoint_into_bundle_entry() -> None:
    adapter = _adapter()
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=42, nfe=6, batch_id="t", sample_id="r0",
    )
    entry = adapter._native_states[str(bundle.native_state_digest)]
    x0_before = np.asarray(entry["x0"], dtype=np.float64).copy()

    cond = ODEConditionDelta(
        delta_spec={"num_steps": 6, "sampler_id": "euler"},
        source="t", target_round=0, calibration_artifact_hash="t:default",
    )
    trace = adapter.solve_ode(bundle, cond, seed=42)
    endpoint = np.asarray(
        adapter._native_states[str(trace.native_state_digest)]["trajectory"]
    )[-1]

    _stash_endpoint_as_x0(adapter, bundle, trace)

    x0_after = np.asarray(
        adapter._native_states[str(bundle.native_state_digest)]["x0"],
        dtype=np.float64,
    )
    # x0 replaced by the solved endpoint (not left as the initial condition).
    assert not np.allclose(x0_before, x0_after)
    assert np.allclose(x0_after.reshape(endpoint.shape), endpoint)


def test_framework_endpoint_differs_from_baseline_endpoint() -> None:
    adapter = _adapter()
    bundle, _ = _build_initial_state_and_condition(
        adapter, seed=42, nfe=6, batch_id="t", sample_id="r0",
    )
    base_trace, _ = _solve_baseline(adapter, nfe=6, seed=42, bundle=bundle)
    base_ep = drv._endpoint_array(adapter, base_trace)
    fw_trace, _ = _solve_framework(
        adapter, nfe=6, seed=42, n_rounds=3, bundle=bundle,
        restart_from_endpoint=True, reanchor=False,
    )
    fw_ep = drv._endpoint_array(adapter, fw_trace)
    assert base_ep.shape == fw_ep.shape
    assert not np.allclose(base_ep, fw_ep)


# ---------------------------------------------------------------------------
# run_paired_sweep — shared x0, schema, resume, skip handling
# ---------------------------------------------------------------------------


def test_run_paired_sweep_uses_same_bundle_and_eq2_flags(monkeypatch, tmp_path) -> None:
    import tools.eval.baseline as baseline_mod
    import tools.eval.framework as framework_mod

    adapter = _adapter()
    captured: dict[str, object] = {}
    real_base = baseline_mod._solve_baseline
    real_fw = framework_mod._solve_framework

    def rec_base(adapter_, *, nfe, seed, n_molecules=1, bundle=None):  # type: ignore[no-untyped-def]
        captured["base_bundle"] = bundle
        return real_base(
            adapter_, nfe=nfe, seed=seed, n_molecules=n_molecules, bundle=bundle,
        )

    def rec_fw(adapter_, **kwargs):  # type: ignore[no-untyped-def]
        captured["fw_bundle"] = kwargs.get("bundle")
        captured["fw_kwargs"] = kwargs
        return real_fw(adapter_, **kwargs)

    monkeypatch.setattr(baseline_mod, "_solve_baseline", rec_base)
    monkeypatch.setattr(framework_mod, "_solve_framework", rec_fw)

    drv.run_paired_sweep(
        output_dir=tmp_path, seed=42, max_records=1, nfe=6, n_rounds=3,
        adapter=adapter, dae=object(), metric_fn=_metric,
    )

    assert captured["base_bundle"] is captured["fw_bundle"]
    fw_kwargs = captured["fw_kwargs"]
    assert fw_kwargs["restart_from_endpoint"] is True
    assert fw_kwargs["reanchor"] is False
    assert fw_kwargs["n_rounds"] == 3


def test_run_paired_sweep_writes_expected_schema(tmp_path) -> None:
    adapter = _adapter()
    summary = drv.run_paired_sweep(
        output_dir=tmp_path, seed=42, max_records=3, nfe=6, n_rounds=3,
        adapter=adapter, dae=object(), metric_fn=_metric,
    )
    assert summary["n_records_processed"] == 3
    assert summary["n_records_skipped"] == 0
    assert summary["skip_reasons"] == {}
    assert np.isfinite(summary["paired_pearson_r"])

    for arm in ("baseline", "framework"):
        path = tmp_path / f"kanzi_n1000_{arm}_paper_metrics.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert sorted(data["per_seq_rmsd_A"]) == ["seq_0", "seq_1", "seq_2"]
        assert data["n_records_processed"] == 3
        assert data["seed"] == 42
        assert data["nfe_budget"] == 6
        assert "sweep_wallclock_s" in data

    csv_lines = (
        tmp_path / "paired_per_record.csv"
    ).read_text(encoding="utf-8").strip().splitlines()
    assert csv_lines[0] == "seq_idx,baseline_rmsd_A,framework_rmsd_A,paired_diff_A"
    assert len(csv_lines) == 4


def test_run_paired_sweep_resume_extends(tmp_path) -> None:
    adapter = _adapter()
    drv.run_paired_sweep(
        output_dir=tmp_path, seed=42, max_records=2, nfe=6, n_rounds=3,
        adapter=adapter, dae=object(), metric_fn=_metric,
    )
    summary = drv.run_paired_sweep(
        output_dir=tmp_path, seed=42, max_records=4, nfe=6, n_rounds=3,
        adapter=adapter, dae=object(), metric_fn=_metric, resume=True,
    )
    assert summary["n_records_processed"] == 4
    data = json.loads(
        (tmp_path / "kanzi_n1000_framework_paper_metrics.json").read_text(
            encoding="utf-8",
        )
    )
    assert sorted(data["per_seq_rmsd_A"]) == ["seq_0", "seq_1", "seq_2", "seq_3"]
    csv_lines = (
        tmp_path / "paired_per_record.csv"
    ).read_text(encoding="utf-8").strip().splitlines()
    assert len(csv_lines) == 5


def test_run_paired_sweep_skips_on_metric_error(tmp_path) -> None:
    adapter = _adapter()
    calls = {"n": 0}

    def flaky(endpoint: object, seq_idx: int | None = None) -> float:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return _metric(endpoint)

    summary = drv.run_paired_sweep(
        output_dir=tmp_path, seed=42, max_records=2, nfe=6, n_rounds=3,
        adapter=adapter, dae=object(), metric_fn=flaky,
    )
    assert summary["n_records_skipped"] == 1
    assert summary["n_records_processed"] == 1
    assert any("RuntimeError:boom" in k for k in summary["skip_reasons"])


def test_run_paired_sweep_rejects_missing_trajectory(tmp_path) -> None:
    adapter = _adapter()

    class _BadTrace:
        native_state_digest = "does-not-exist"

    with pytest.raises(RuntimeError):
        drv._endpoint_array(adapter, _BadTrace())
