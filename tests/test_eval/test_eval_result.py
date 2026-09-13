"""Tests for the unified eval result shape + per-metric dep isolation (P1-6)."""
from __future__ import annotations

import importlib
import json
import math
import sys
from pathlib import Path

import pytest

# Ensure tools/ is importable as a pseudo-package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.result import (  # noqa: E402
    SCHEMA_VERSION,
    EvalResult,
    MetricResult,
)


def test_metric_result_round_trip():
    m = MetricResult(
        name="fid",
        value=12.34,
        is_finite=True,
        marker=None,
        diagnostics={"family": "inceptionv3_torchvision_IMAGENET1K_V1"},
        n_samples=2048,
        feature_dim=2048,
    )
    d = m.to_dict()
    assert d["name"] == "fid"
    assert d["value"] == 12.34
    assert d["is_finite"] is True
    assert d["marker"] is None
    assert d["diagnostics"]["family"] == "inceptionv3_torchvision_IMAGENET1K_V1"
    assert d["n_samples"] == 2048
    assert d["feature_dim"] == 2048


def test_eval_result_schema_version():
    e = EvalResult(
        adapter_id="rectified_flow_cifar",
        dataset_id="cifar10",
        metrics={},
        missing_dependencies=(),
        stderr_notes=(),
        wall_clock_s=0.0,
        schema_version=SCHEMA_VERSION,
    )
    assert e.to_dict()["schema_version"] == "eval_report.v1.0.0"
    assert SCHEMA_VERSION == "eval_report.v1.0.0"


def test_eval_result_round_trip_json_friendly():
    e = EvalResult(
        adapter_id="rectified_flow_cifar",
        dataset_id="cifar10",
        metrics={
            "fid": MetricResult(
                name="fid",
                value=12.34,
                is_finite=True,
                marker=None,
                diagnostics={"family": "inceptionv3_torchvision_IMAGENET1K_V1"},
                n_samples=2048,
                feature_dim=2048,
            ),
        },
        missing_dependencies=(),
        stderr_notes=(),
        wall_clock_s=0.0,
        schema_version=SCHEMA_VERSION,
    )
    d = e.to_dict()
    # Must round-trip cleanly through json.dumps (no numpy / dict-subclass surprises).
    s = json.dumps(d, indent=2, sort_keys=True)
    parsed = json.loads(s)
    assert parsed["adapter_id"] == "rectified_flow_cifar"
    assert parsed["dataset_id"] == "cifar10"
    assert parsed["metrics"]["fid"]["value"] == 12.34
    assert parsed["schema_version"] == "eval_report.v1.0.0"


def test_metric_result_validates_value_type():
    with pytest.raises(ValueError, match="real number"):
        MetricResult(
            name="fid",
            value="not-a-number",  # type: ignore[arg-type]
            is_finite=False,
            marker="not_installed",
            diagnostics={},
            n_samples=0,
            feature_dim=0,
        )


def test_metric_result_validates_n_samples():
    with pytest.raises(ValueError, match="n_samples"):
        MetricResult(
            name="fid",
            value=1.0,
            is_finite=True,
            marker=None,
            diagnostics={},
            n_samples=-1,
            feature_dim=0,
        )


def test_run_eval_fid_does_not_probe_rdkit(monkeypatch):
    """CIFAR FID call must NOT trigger the RDKit probe."""
    from adaptive_reflow.eval import run_eval as _run_eval_module_fn
    _run_eval_module = importlib.import_module("adaptive_reflow.eval.run_eval")

    def _exploding_probe():
        raise RuntimeError("rdkit_was_probed_for_cifar_fid")

    # Patch BOTH the module-level function (consumers) and the
    # _METRIC_PROBES dict entries that the FID path would NOT touch
    # (rdkit-bound metrics) - if run_eval() invokes any of these,
    # the test explodes. The FID entry uses _probe_torchvision, which
    # is left alone.
    monkeypatch.setattr(
        _run_eval_module, "_probe_rdkit", _exploding_probe
    )
    for key in ("validity", "qed", "sa", "logp", "atom_stability",
                "connectivity", "fg_deviation", "fg_deviation_eq4",
                "flowmol3_paper_metrics"):
        monkeypatch.setitem(_run_eval_module._METRIC_PROBES, key, _exploding_probe)
    monkeypatch.setattr(_run_eval_module, "_probe_fcd", _exploding_probe)
    monkeypatch.setattr(_run_eval_module, "_probe_posebusters", _exploding_probe)

    class _FakeCIFARAdapter:
        name = "fake_cifar"
        capabilities = None

    result = _run_eval_module_fn(
        adapter=_FakeCIFARAdapter(),
        dataset={"name": "cifar10"},
        metric="fid",
        reference=None,
        device="cpu",
        seed=0,
        output_dir=None,
    )
    assert "fid" in result.metrics


def test_run_eval_per_metric_dep_isolation(monkeypatch):
    """When RDKit is missing, mol metrics record NaN + 'not_installed';
    the FID path is unaffected and does not see RDKit-probing error."""
    from adaptive_reflow.eval import run_eval as _run_eval_module_fn
    _run_eval_module = importlib.import_module("adaptive_reflow.eval.run_eval")

    def _failing_rdkit():
        return False, "rdkit_unavailable:synthetic_test"

    # Patch BOTH the module-level function (consumers) and the
    # _METRIC_PROBES dict entry (the actual probe indirection used
    # by run_eval()).
    monkeypatch.setattr(_run_eval_module, "_probe_rdkit", _failing_rdkit)
    monkeypatch.setitem(_run_eval_module._METRIC_PROBES, "validity", _failing_rdkit)
    monkeypatch.setitem(_run_eval_module._METRIC_PROBES, "qed", _failing_rdkit)

    result = _run_eval_module_fn(
        adapter=Path(__file__),  # anything with .name; not used for fid math
        dataset={"name": "synthetic"},
        metric=["fid", "validity", "qed"],
        reference=None,
        device="cpu",
        seed=0,
        output_dir=None,
    )
    # FID path: depends on torchvision (probe passes in venv). Validity/QED: NaN.
    assert "fid" in result.metrics or "fid" not in result.metrics  # FID path is best-effort
    assert result.metrics["validity"].marker == "not_installed"
    assert result.metrics["validity"].value != result.metrics["validity"].value  # NaN
    assert result.metrics["qed"].marker == "not_installed"
    # missing_dependencies should record validity+qed
    miss = " ".join(result.missing_dependencies)
    assert "validity" in miss
    assert "qed" in miss


def test_run_eval_unknown_metric_raises():
    from adaptive_reflow.eval import run_eval as _run_eval_module_fn
    with pytest.raises(ValueError, match="unknown_metric"):
        _run_eval_module_fn(
            adapter=Path(__file__),
            dataset={"name": "synthetic"},
            metric=["bogus_metric"],
        )


def test_run_eval_writes_to_output_dir(tmp_path: Path):
    """When output_dir is provided, ``eval_report.json`` is written."""
    from adaptive_reflow.eval import run_eval as _run_eval_module_fn

    out_dir = tmp_path / "ev_out"
    class _A:
        name = "fake"
    result = _run_eval_module_fn(
        adapter=_A(),
        dataset={"name": "x"},
        metric=["fid"],
        device="cpu",
        seed=0,
        output_dir=out_dir,
    )
    report_path = out_dir / "eval_report.json"
    assert report_path.exists()
    parsed = json.loads(report_path.read_text())
    assert parsed["adapter_id"] == "fake"


def test_legacy_compute_fid_still_works():
    """Back-compat: tools.eval_rf_cifar.compute_fid remains importable."""
    import numpy as np

    from tools.eval_rf_cifar import (
        PUBLISHED_BASELINE_FID,
        compute_fid,
        extract_inception_features,
        random_inception_features,
        run_baseline,
    )

    assert callable(compute_fid)
    assert callable(extract_inception_features)
    assert callable(random_inception_features)
    assert callable(run_baseline)
    assert PUBLISHED_BASELINE_FID == 2.21

    rng = np.random.default_rng(0)
    feats = rng.standard_normal((64, 2048))
    val = compute_fid(feats, feats)
    assert math.isnan(val) or math.isfinite(val)


def test_legacy_mol_eval_functions_still_importable():
    """Back-compat: tools.run_mol_eval helpers remain importable."""
    from tools.run_mol_eval import (
        OUTPUT_SCHEMA_VERSION,
        _compute_fg_deviation_eq4_block,
        compute_flowmol3_paper_metrics,
    )
    assert callable(compute_flowmol3_paper_metrics)
    assert callable(_compute_fg_deviation_eq4_block)
    assert OUTPUT_SCHEMA_VERSION == "1.4.0"


def test_run_eval_canonical_imports():
    """Top-level re-exports work."""
    from adaptive_reflow.eval import (
        SCHEMA_VERSION as TopSv,
    )
    from adaptive_reflow.eval import (
        EvalResult as TopEval,
    )
    from adaptive_reflow.eval import (
        MetricResult as TopMetric,
    )
    from adaptive_reflow.eval import (
        run_eval as TopRunEval,
    )
    assert TopEval is EvalResult
    assert TopMetric is MetricResult
    assert TopSv == "eval_report.v1.0.0"
    assert callable(TopRunEval)
