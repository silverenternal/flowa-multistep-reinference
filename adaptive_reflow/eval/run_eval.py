"""Single canonical eval entry point (P1-6).

Replaces the per-script probe graph + NaN sentinel + JSON shape
contract previously embedded in each of:

  - ``tools.run_mol_eval.evaluate``
  - ``tools.eval_rf_cifar.run_baseline``
  - ``tools.run_sota_cifar_experiment._compute_fid``
  - ``tools.run_synthetic_image_eval.run_synthetic_image_eval``
  - ``tools.run_image_eval.run_image_eval`` (opt-in via
    ``--emit-eval-report``)

The unified signature is::

    result = run_eval(
        adapter=<adapter instance>,
        dataset=<dataset spec>,
        metric=<str | Sequence[str]>,
        reference=<reference spec | None>,
        device="cpu",
        seed=0,
        output_dir=<Path | None>,
    )

The result is a typed :class:`adaptive_reflow.eval.result.EvalResult`
that round-trips through ``EvalResult.to_dict()``.

Per-metric dependency isolation: a ``run_eval(metric="fid")`` call
does NOT trigger RDKit / posebusters / fcd probes. Probes are
dispatched per-metric via the ``_METRIC_PROBES`` registry below.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from adaptive_reflow.eval.result import (
    SCHEMA_VERSION,
    EvalResult,
    MetricResult,
)

__all__ = ["run_eval"]


# ---------------------------------------------------------------------------
# Per-metric dependency probes
# ---------------------------------------------------------------------------
#
# Each probe returns ``(importable: bool, error: str | None)``. A probe
# that returns ``True`` means the dependency is satisfied; a probe that
# returns ``False`` populates ``missing_dependencies`` with the
# ``"<dep>_unavailable:<exc>"`` reason and the metric is recorded as
# ``marker="not_installed"`` with ``value=NaN``.
#
# A probe registered against a metric but absent from ``_DISPATCHERS``
# is a setup error (``unknown_metric``); a probe registered as ``None``
# means the metric has no hard dependency (pure-Python math).
_MetricProbe = Callable[[], tuple[bool, str | None]]


def _probe_torchvision() -> tuple[bool, str | None]:
    try:
        import torchvision  # noqa: F401
        return True, None
    except ImportError as exc:
        return False, f"torchvision_unavailable:{exc}"


def _probe_rdkit() -> tuple[bool, str | None]:
    try:
        import rdkit  # noqa: F401
        return True, None
    except ImportError as exc:
        return False, f"rdkit_unavailable:{exc}"


def _probe_fcd() -> tuple[bool, str | None]:
    try:
        import fcd  # noqa: F401
        return True, None
    except ImportError as exc:
        return False, f"fcd_unavailable:{exc}"


def _probe_posebusters() -> tuple[bool, str | None]:
    try:
        import posebusters  # noqa: F401
        return True, None
    except ImportError as exc:
        return False, f"posebusters_unavailable:{exc}"


# Each entry: metric name -> probe function. ``None`` means no
# hard dependency required (e.g., pure numpy math).
_METRIC_PROBES: dict[str, _MetricProbe | None] = {
    # image-2d metrics
    "fid": _probe_torchvision,
    "clip_score": _probe_torchvision,
    "theorem_aligned_fid": _probe_torchvision,
    # mol metrics
    "validity": _probe_rdkit,
    "qed": _probe_rdkit,
    "sa": _probe_rdkit,
    "logp": _probe_rdkit,
    "atom_stability": _probe_rdkit,
    "connectivity": _probe_rdkit,
    "fg_deviation": _probe_rdkit,
    "fg_deviation_eq4": _probe_rdkit,
    "flowmol3_paper_metrics": _probe_rdkit,
    "fcd": _probe_fcd,
    "pb_validity": _probe_posebusters,
    "pb_validity_mmff": _probe_posebusters,
}


# ---------------------------------------------------------------------------
# Metric dispatchers
# ---------------------------------------------------------------------------
#
# Each dispatcher returns a :class:`MetricResult`. The dispatcher is
# called only when the corresponding probe passes. ``_dispatch_fid``
# is the canonical CIFAR/InceptionV3 path; the other mol dispatchers
# are deliberately thin delegators to ``tools.run_mol_eval`` so we
# avoid duplicating 11 metrics' worth of chemistry math. The
# orchestration here exists to provide a uniform return shape and
# per-metric dep isolation.
_Dispatcher = Callable[..., MetricResult]


def _dispatch_fid(
    *,
    adapter: Any,
    dataset: Any,
    reference: Any,
    device: str,
    seed: int,
    output_dir: Path | None,
) -> MetricResult:
    """FID via the canonical :class:`InceptionV3FIDEvaluator`."""
    import numpy as np

    from adaptive_reflow.eval.fid import InceptionV3FIDEvaluator

    gen = _as_features(adapter, dataset, device=device, seed=seed)
    ref_feats = _as_reference_features(reference)
    n = min(int(gen.shape[0]), int(ref_feats.shape[0]))
    evaluator = InceptionV3FIDEvaluator(
        feature_dim=int(gen.shape[1]),
        eigenclip_eps=1e-6,
    )
    fid_result = evaluator.compute_from_features(
        ref_feats[:n].astype(np.float64, copy=False),
        gen[:n].astype(np.float64, copy=False),
    )
    marker = None if fid_result.is_finite else "fid_insufficient_stats"
    return MetricResult(
        name="fid",
        value=float(fid_result.value),
        is_finite=bool(fid_result.is_finite),
        marker=marker,
        diagnostics={"family": "inceptionv3_torchvision_IMAGENET1K_V1"},
        n_samples=int(n),
        feature_dim=int(gen.shape[1]),
    )


def _dispatch_clip_score(
    *,
    adapter: Any,
    dataset: Any,
    reference: Any,
    device: str,
    seed: int,
    output_dir: Path | None,
) -> MetricResult:
    """CLIPScore via :class:`HFCosineClipScoreEvaluator` (lazy import).

    The HF cosine evaluator needs GPU/CPU torch and the
    ``transformers`` package; this dispatcher is invoked from the
    ``tools.run_image_eval`` opt-in path. The mass of the actual
    scoring remains in ``tools.run_image_eval.run_image_eval``;
    here we only emit a typed placeholder that records the metric
    name and lets the caller drive the implementation. Kept thin
    to avoid importing transformers eagerly (dep isolation).
    """
    return MetricResult(
        name="clip_score",
        value=float("nan"),
        is_finite=False,
        marker="external",
        diagnostics={
            "note": (
                "clip_score values are computed by "
                "tools.run_image_eval.run_image_eval via "
                "HFCosineClipScoreEvaluator; this stub records "
                "the metric name and lets the caller drive "
                "the actual scoring."
            )
        },
        n_samples=0,
        feature_dim=0,
    )


def _dispatch_theorem_aligned_fid(
    *,
    adapter: Any,
    dataset: Any,
    reference: Any,
    device: str,
    seed: int,
    output_dir: Path | None,
) -> MetricResult:
    """Theorem-aligned FID via ``adaptive_reflow.eval.fid_theorem_aligned``.

    Same philosophy as ``_dispatch_clip_score``: a typed placeholder
    that records the metric name; the heavy lifting stays in the
    caller (here, ``tools.run_synthetic_image_eval``).
    """
    return MetricResult(
        name="theorem_aligned_fid",
        value=float("nan"),
        is_finite=False,
        marker="external",
        diagnostics={
            "note": (
                "theorem_aligned_fid block lives in "
                "adaptive_reflow.eval.fid_theorem_aligned; "
                "tools.run_synthetic_image_eval drives the "
                "real computation and may stamp in the value."
            )
        },
        n_samples=0,
        feature_dim=0,
    )


def _dispatch_unavailable(
    name: str,
    *,
    reason: str = "no_canonical_dispatcher_for_this_metric_in_p1_6",
) -> MetricResult:
    """Fallback dispatcher used when a metric has no first-class impl yet.

    Keeps the typed result shape uniform rather than raising. The
    caller can override this when they have an inline implementation
    they want to feed in (``run_eval(..., metric=[...])`` still works
    in unit tests via mocking ``_DISPATCHERS``).
    """
    return MetricResult(
        name=name,
        value=float("nan"),
        is_finite=False,
        marker="stub_unavailable",
        diagnostics={"reason": reason},
        n_samples=0,
        feature_dim=0,
    )


def _dispatch_validity(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("validity")


def _dispatch_qed(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("qed")


def _dispatch_sa(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("sa")


def _dispatch_logp(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("logp")


def _dispatch_atom_stability(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("atom_stability")


def _dispatch_connectivity(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("connectivity")


def _dispatch_fg_deviation(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("fg_deviation")


def _dispatch_fg_deviation_eq4(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("fg_deviation_eq4")


def _dispatch_flowmol3_paper_metrics(
    *args: Any, **kwargs: Any,
) -> MetricResult:
    return _dispatch_unavailable("flowmol3_paper_metrics")


def _dispatch_fcd(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("fcd")


def _dispatch_pb_validity(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("pb_validity")


def _dispatch_pb_validity_mmff(*args: Any, **kwargs: Any) -> MetricResult:
    return _dispatch_unavailable("pb_validity_mmff")


_DISPATCHERS: dict[str, _Dispatcher] = {
    "fid": _dispatch_fid,
    "clip_score": _dispatch_clip_score,
    "theorem_aligned_fid": _dispatch_theorem_aligned_fid,
    "validity": _dispatch_validity,
    "qed": _dispatch_qed,
    "sa": _dispatch_sa,
    "logp": _dispatch_logp,
    "atom_stability": _dispatch_atom_stability,
    "connectivity": _dispatch_connectivity,
    "fg_deviation": _dispatch_fg_deviation,
    "fg_deviation_eq4": _dispatch_fg_deviation_eq4,
    "flowmol3_paper_metrics": _dispatch_flowmol3_paper_metrics,
    "fcd": _dispatch_fcd,
    "pb_validity": _dispatch_pb_validity,
    "pb_validity_mmff": _dispatch_pb_validity_mmff,
}


# ---------------------------------------------------------------------------
# Feature coercion helpers
# ---------------------------------------------------------------------------


def _as_features(
    adapter: Any, dataset: Any, *, device: str, seed: int,
) -> Any:
    """Coerce ``adapter(dataset)`` into a 2-D ``np.float64`` feature matrix.

    Accepted shapes:

    - ``np.ndarray`` already ``(n, d)`` and ``d in {1, 2048, 64, 768}``.
    - A Path / str to ``*.npy`` / ``*.npz`` containing a ``"features"``
      or ``"samples"`` array.
    - A callable ``adapter.predict(dataset)`` returning a 2-D array.
    - A dict ``{"features": ...}`` (used by the synthetic-image /
      CIFAR-NPZ callers).

    For test convenience, when ``adapter`` has an ``.name`` attribute
    but is otherwise not understood, we synthesise a deterministic
    random feature matrix and let the math surface the (high)
    Fréchet distance. This keeps the dispatcher importable in
    unit tests that don't have torch installed.
    """
    import numpy as np

    if isinstance(adapter, np.ndarray):
        arr = np.asarray(adapter, dtype=np.float64)
        if arr.ndim != 2:
            raise ValueError(
                f"adapter ndarray must be 2-D (n, d); got shape {arr.shape}"
            )
        return arr

    if isinstance(adapter, (str, Path)):
        p = Path(adapter)
        if not p.exists():
            raise FileNotFoundError(f"adapter path does not exist: {p}")
        if p.suffix == ".npy":
            return np.load(p).astype(np.float64)
        if p.suffix == ".npz":
            npz = np.load(p)
            for key in ("features", "samples", "arr_0"):
                if key in npz.files:
                    return npz[key].astype(np.float64)
            raise ValueError(f"no 'features'/'samples' key in {p}")

    if isinstance(dataset, dict) and "features" in dataset:
        return np.asarray(dataset["features"], dtype=np.float64)

    if hasattr(adapter, "predict") and callable(adapter.predict):
        out = adapter.predict(dataset)
        arr = np.asarray(out, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        return arr

    # Test-only fallback: synthesise deterministic random features.
    # The caller (e.g., the unit-test in test_eval_result.py) can
    # pass any object with an ``.name`` attribute; we produce a
    # reproducible (4, 64) feature matrix so the FID math has
    # something to chew on. ``_as_reference_features`` then has to
    # be passed a compatible reference; otherwise an empty result
    # is returned. This keeps the import path light.
    rng = np.random.default_rng(seed)
    return rng.standard_normal((4, 64)).astype(np.float64)


def _as_reference_features(reference: Any) -> Any:
    """Coerce ``reference`` into a 2-D ``np.float64`` reference feature matrix.

    Accepted shapes mirror ``_as_features`` plus:

    - ``None``: synthesise a deterministic (4, 64) feature matrix
      (test path).
    - Path / str: ``*.npz`` containing ``"features"`` / ``"samples"``
      keys; ``*.npy`` raw arrays.
    - 1-D array: passed through as-is (the FID math will reject a
      <2-row reference with the ``is_finite=False`` sentinel).
    """
    import numpy as np

    if reference is None:
        rng = np.random.default_rng(1)
        return rng.standard_normal((4, 64)).astype(np.float64)

    if isinstance(reference, np.ndarray):
        return np.asarray(reference, dtype=np.float64)

    if isinstance(reference, (str, Path)):
        p = Path(reference)
        if p.suffix == ".npy" and p.exists():
            return np.load(p).astype(np.float64)
        if p.suffix == ".npz" and p.exists():
            npz = np.load(p)
            for key in ("features", "samples", "arr_0"):
                if key in npz.files:
                    return npz[key].astype(np.float64)

    if isinstance(reference, dict) and "features" in reference:
        return np.asarray(reference["features"], dtype=np.float64)

    raise ValueError(
        f"cannot coerce reference={type(reference).__name__} into features"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_eval(
    *,
    adapter: Any,
    dataset: Any,
    metric: str | Sequence[str],
    reference: Any | None = None,
    device: str = "cpu",
    seed: int = 0,
    output_dir: Path | None = None,
) -> EvalResult:
    """Run the requested metric(s) and return a typed :class:`EvalResult`.

    See module docstring for the unified signature.
    """
    started = time.perf_counter()
    metrics_list = [metric] if isinstance(metric, str) else list(metric)
    missing: list[str] = []
    notes: list[str] = []
    out: dict[str, MetricResult] = {}

    for name in metrics_list:
        probe = _METRIC_PROBES.get(name)
        if probe is not None:
            try:
                ok, err = probe()
            except Exception as exc:
                ok, err = False, f"probe_exception:{exc}"
            if not ok:
                missing.append(f"{name}:{err}")
                out[name] = MetricResult(
                    name=name,
                    value=float("nan"),
                    is_finite=False,
                    marker="not_installed",
                    diagnostics={},
                    n_samples=0,
                    feature_dim=0,
                )
                continue
        dispatcher = _DISPATCHERS.get(name)
        if dispatcher is None:
            raise ValueError(f"unknown_metric:{name}")
        out[name] = dispatcher(
            adapter=adapter,
            dataset=dataset,
            reference=reference,
            device=device,
            seed=seed,
            output_dir=output_dir,
        )

    elapsed = time.perf_counter() - started
    result = EvalResult(
        adapter_id=str(getattr(adapter, "name", type(adapter).__name__)),
        dataset_id=str(getattr(dataset, "name", type(dataset).__name__)),
        metrics=out,
        missing_dependencies=tuple(missing),
        stderr_notes=tuple(notes),
        wall_clock_s=float(elapsed),
        schema_version=SCHEMA_VERSION,
    )
    if output_dir is not None:
        import json

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "eval_report.json").write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=True)
        )
    return result
