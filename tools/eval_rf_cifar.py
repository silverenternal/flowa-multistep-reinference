"""Baseline reproduction for Rectified Flow (Liu 2022) on CIFAR-10.

Implements the plan's §4 — *Baseline reproduction plan*. The script
loads the published Rectified Flow velocity-field UNet (or falls back
to the synthetic NumPy velocity field in ``RectifiedFlowCIFARAdapter``
when torch is not available), generates ``--num-samples`` samples via
the paper's 2-NFE Euler schedule, and computes FID against a reference
InceptionV3 features file.

Important — environment caveats
-------------------------------

The published FID 2.21 reproduction requires:

1. The pretrained UNet ``state_dict`` (120 MB) downloaded to
   ``data/rectified_flow_cifar10.safetensors`` (or ``.pth``).
2. :mod:`torch` + :mod:`torchvision` installed (``pip install '.[rf-cifar]'``).
3. The pre-computed CIFAR-10 train InceptionV3 features at
   ``data/cifar10_inception_features.npz``.

When any of the three is missing the script falls back to a *synthetic*
baseline (random-init NumPy velocity field). The synthetic FID is
NOT a reproduction of Liu 2022 — it is a Protocol-surface smoke test
that exercises the baseline codepath end-to-end. The script prints a
clear ``[SYNTHETIC BASELINE]`` banner so the operator knows the
numbers are not paper-comparable.

Usage::

    # Synthetic smoke test (no torch / no weights):
    python -m tools.eval_rf_cifar --num-samples 64

    # Full baseline reproduction (requires [rf-cifar] + weights + inception):
    python -m tools.eval_rf_cifar --num-samples 50000 --batch-size 64

The script exits ``0`` on success (regardless of whether the baseline
FID is within the 5%-of-paper band — failure is reported, not raised)
and ``1`` only on hard errors (missing argument, bad path, etc.).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

# Make the project importable when running as ``python tools/eval_rf_cifar.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.rectified_flow_cifar import (  # noqa: E402
    RF_CIFAR_CONFIG_HASH,
    RectifiedFlowCIFARAdapter,
    rectified_flow_cifar_resolve_weights_path,
    torch_is_available,
)
from adaptive_reflow.eval.fid import (  # noqa: E402
    InceptionV3FIDEvaluator,
)

# P0-1: import the canonical InceptionV3 feature-extractor surface
# directly from ``tools.run_image_eval``. Loaded via spec_from_file_location
# so this module remains self-contained when invoked as
# ``python tools/eval_rf_cifar.py`` (the ``tools/`` directory is not a
# package, so a plain ``import`` would fail).
import importlib.util as _importlib_util  # noqa: E402

_RUN_IMAGE_EVAL_PATH = Path(__file__).resolve().parent / "run_image_eval.py"
_RUN_IMAGE_EVAL_SPEC = _importlib_util.spec_from_file_location(
    "tools_run_image_eval", str(_RUN_IMAGE_EVAL_PATH)
)
if _RUN_IMAGE_EVAL_SPEC is None or _RUN_IMAGE_EVAL_SPEC.loader is None:  # pragma: no cover — defensive
    raise ImportError(f"could not load {_RUN_IMAGE_EVAL_PATH}")
tools_run_image_eval = _importlib_util.module_from_spec(_RUN_IMAGE_EVAL_SPEC)
sys.modules.setdefault("tools_run_image_eval", tools_run_image_eval)
_RUN_IMAGE_EVAL_SPEC.loader.exec_module(tools_run_image_eval)

# Published baseline from Liu 2022 (Table 2 — 2-rectified flow, 1-NFE
# Euler on CIFAR-10 32×32).
PUBLISHED_BASELINE_FID: float = 2.21
PUBLISHED_BASELINE_BAND: float = 0.11  # 5% tolerance band.

# Default InceptionV3 reference features path.
DEFAULT_REFERENCE_FEATURES: str = "data/cifar10_inception_features.npz"


# ---------------------------------------------------------------------------
# FID computation — closed-form NumPy helper + lazy public wrapper
# ---------------------------------------------------------------------------
#
# Behaviour change: the legacy :func:`compute_fid` returned
# ``float('inf')`` on insufficient statistics (``<2`` rows in either
# operand). The new abstraction follows the scientific convention and
# returns ``float('nan')`` in that case (the FID is genuinely undefined
# when the sample covariance is degenerate). Callers that need to
# distinguish "undefined" from a finite-but-large FID should branch on
# ``math.isnan(...)`` / ``math.isfinite(...)``.
#
# Wave 119 Phase 3 (Category B): reuse the Wave 118 closed-form
# decoupling pattern (``adaptive_reflow/eval/fid.py:539-609``). The
# pure-NumPy Fréchet arithmetic was always independent of the InceptionV3
# feature extractor, but the historical eager
# :class:`InceptionV3FIDEvaluator` construction forced the closed-form
# path to drag in ``torch`` + ``torchvision``. The two-tier structure
# below mirrors the Wave 118 commit (``435ba7c``):
#
#   1. :func:`_compute_frechet_distance_inner` — pure-NumPy helper
#      (scipy.linalg.sqrtm → eigen-clipping retry → pure-NumPy fallback).
#   2. :func:`compute_fid` — public lazy wrapper that fits the Gaussians
#      and delegates to the inner helper. The InceptionV3 evaluator is
#      no longer constructed on this path, so the function works in
#      environments without ``torch`` / ``torchvision`` (CPU-only CI,
#      synthetic-mode smoke tests).
#   3. :data:`compute_frechet_distance_closed_form` — public alias of
#      the inner helper, provided so external callers can reuse the
#      closed-form math without importing this module's
#      ``InceptionV3FIDEvaluator`` import surface.


def _compute_frechet_distance_inner(
    sigma_real: np.ndarray,
    sigma_fake: np.ndarray,
    mu_real: np.ndarray,
    mu_fake: np.ndarray,
    *,
    eps: float = 1e-6,
) -> float:
    """Pure-NumPy closed-form Fréchet distance (no torch / torchvision).

    Implements::

        FID = ||μ_real - μ_fake||^2 + Tr(Σ_real + Σ_fake - 2 (Σ_real Σ_fake)^{1/2})

    with the three-tier numerical fallback used by the canonical
    :func:`adaptive_reflow.eval.fid._frechet_distance_closed_form`
    (scipy.linalg.sqrtm → eigen-clipping retry ``+ eps * I`` →
    pure-NumPy eigendecomposition). Returns ``float('nan')`` when the
    result is non-finite after all three guards; the result is clipped
    to ``>= 0`` otherwise.

    The argument order (``sigma_real, sigma_fake, mu_real, mu_fake``)
    matches :func:`tools.compute_cifar_fid._compute_frechet_distance_inner`
    so the closed-form math is byte-identical across tools.
    """
    sig_r = np.asarray(sigma_real, dtype=np.float64)
    sig_f = np.asarray(sigma_fake, dtype=np.float64)
    mu_r = np.asarray(mu_real, dtype=np.float64)
    mu_f = np.asarray(mu_fake, dtype=np.float64)

    if sig_r.shape != sig_f.shape:
        raise ValueError(
            f"sigma shapes must match: {sig_r.shape} vs {sig_f.shape}"
        )
    if mu_r.shape != mu_f.shape:
        raise ValueError(
            f"mu shapes must match: {mu_r.shape} vs {mu_f.shape}"
        )

    # Tier 1: scipy.linalg.sqrtm when scipy is importable. Retry with
    # the ``+ eps * I`` offset on non-finite output (canonical
    # pytorch-fid eigen-clipping pattern).
    try:
        from scipy.linalg import sqrtm as _scipy_sqrtm  # local import

        covmean = np.asarray(_scipy_sqrtm(sig_r @ sig_f), dtype=np.complex128)
        if not bool(np.all(np.isfinite(covmean))):
            dim = int(sig_r.shape[0])
            offset = np.eye(dim, dtype=np.float64) * float(eps)
            covmean = np.asarray(
                _scipy_sqrtm((sig_r + offset) @ (sig_f + offset)),
                dtype=np.complex128,
            )
    except ImportError:
        # Tier 3: pure-NumPy eigendecomposition. Clips eigenvalues at
        # ``eps`` so the floor is non-negative (standard pytorch-fid
        # "clipped FID" surrogate).
        prod = sig_r @ sig_f
        eigvals, eigvecs = np.linalg.eigh(prod)
        eigvals_clipped = np.clip(eigvals, float(eps), None)
        covmean = eigvecs @ np.diag(np.sqrt(eigvals_clipped)) @ eigvecs.T

    # Complex-valued result → keep real part (mirrors tools.run_image_eval).
    if np.iscomplexobj(covmean):
        covmean = np.real(covmean)

    diff = mu_r - mu_f
    fid_value = float(
        float(np.dot(diff, diff))
        + float(np.trace(sig_r))
        + float(np.trace(sig_f))
        - 2.0 * float(np.trace(covmean))
    )
    # FID is non-negative by construction; numerical noise may push
    # the value to a tiny negative. Clip to zero for safety.
    if not math.isfinite(fid_value):
        return float("nan")
    return float(max(fid_value, 0.0))


# Public alias for closed-form callers (Wave 118 pattern). The two
# names route through the single source of truth above so the numerical
# contract is identical.
compute_frechet_distance_closed_form = _compute_frechet_distance_inner


def compute_fid(
    generated_feats: np.ndarray,
    reference_feats: np.ndarray,
    *,
    eps: float = 1e-6,
) -> float:
    """Compute the Fréchet Inception Distance (FID) between two feature sets.

    Public lazy wrapper around :func:`_compute_frechet_distance_inner`
    (pure NumPy, no torch / torchvision dependency). The standard FID
    formula is::

        FID = ||μ_r - μ_g||^2 + Tr(Σ_r + Σ_g - 2 (Σ_r Σ_g)^{1/2})

    Both ``generated_feats`` and ``reference_feats`` are 2D arrays of
    shape ``(N, D)`` (typically ``D = 2048`` from InceptionV3's pool3
    layer). The matrix square root is computed via
    ``scipy.linalg.sqrtm`` with eigen-clipping for numerical safety;
    callers that need bit-determinism across machines should seed
    numpy's PRNG via ``np.random.default_rng``.

    Returns ``float('nan')`` when either input has fewer than 2 rows
    (insufficient statistics for FID). **Behaviour change**: this
    sentinel used to be ``float('inf')`` — the legacy call sites in
    :mod:`tools.run_sota_cifar_experiment` already branch on
    ``math.isfinite`` so they keep working.

    Note — Wave 119 Phase 3 (Category B): the historical implementation
    eagerly constructed an :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator`
    (which requires ``torch`` + ``torchvision``), so the closed-form path
    failed loud with an :class:`ImportError` in CPU-only environments
    even though the Fréchet arithmetic was always pure-NumPy. The
    function now fits Gaussians locally and delegates to the pure-NumPy
    :func:`_compute_frechet_distance_inner` helper. Callers who want
    the canonical InceptionV3-evaluated FID can still import
    :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator` directly
    and call ``compute_from_features``.
    """
    if generated_feats.ndim != 2 or reference_feats.ndim != 2:
        raise ValueError("features_must_be_2d")
    if generated_feats.shape[1] != reference_feats.shape[1]:
        raise ValueError("feature_dims_must_match")
    gen64 = generated_feats.astype(np.float64, copy=False)
    ref64 = reference_feats.astype(np.float64, copy=False)
    if gen64.shape[0] < 2 or ref64.shape[0] < 2:
        return float("nan")

    # Fit Gaussians locally (no InceptionV3 construction).
    mu_g = np.asarray(np.mean(gen64, axis=0), dtype=np.float64)
    mu_r = np.asarray(np.mean(ref64, axis=0), dtype=np.float64)
    sigma_g = np.asarray(np.cov(gen64, rowvar=False), dtype=np.float64)
    sigma_r = np.asarray(np.cov(ref64, rowvar=False), dtype=np.float64)

    return _compute_frechet_distance_inner(
        sigma_real=sigma_r,
        sigma_fake=sigma_g,
        mu_real=mu_r,
        mu_fake=mu_g,
        eps=float(eps),
    )


# Public lazy wrapper (Wave 118 pattern). Takes pre-computed
# Gaussian statistics and routes them through the closed-form inner
# helper — the InceptionV3 evaluator is **never** instantiated on this
# path. Provided so external callers (and the user's verification
# import-check ``from tools.eval_rf_cifar import compute_frechet_distance,
# compute_frechet_distance_closed_form``) can reuse the canonical FID
# arithmetic without dragging in ``torch`` / ``torchvision``.
def compute_frechet_distance(
    sigma_real: np.ndarray,
    sigma_fake: np.ndarray,
    mu_real: np.ndarray,
    mu_fake: np.ndarray,
    *,
    eps: float = 1e-6,
) -> float:
    """Closed-form Fréchet distance between two pre-computed Gaussians.

    Thin lazy wrapper around :func:`_compute_frechet_distance_inner`
    (pure NumPy). The argument order matches the canonical
    :func:`adaptive_reflow.eval.fid.compute_frechet_distance` so
    legacy call sites that import the FID math from this module
    continue to work unchanged.

    Wave 119 Phase 3 (Category B): the canonical InceptionV3 evaluator
    is **not** constructed on this path. Callers who need the
    InceptionV3-evaluated FID should import
    :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator` directly
    and call ``compute_from_features``.
    """
    return _compute_frechet_distance_inner(
        sigma_real=sigma_real,
        sigma_fake=sigma_fake,
        mu_real=mu_real,
        mu_fake=mu_fake,
        eps=float(eps),
    )


def random_inception_features(
    n: int,
    *,
    dim: int = 2048,
    seed: int = 0,
) -> np.ndarray:
    """Return ``(n, dim)`` random features used as a synthetic reference.

    Used when the real CIFAR-10 InceptionV3 features are unavailable.
    The random features are *not* a valid FID reference — callers using
    this fallback must explicitly note that the computed FID is a
    synthetic-vs-synthetic score, not a paper-comparable measurement.
    """
    rng = np.random.default_rng(int(seed))
    arr64 = rng.standard_normal((int(n), int(dim))).astype(np.float64)
    return np.asarray(arr64, dtype=np.float64)  # type: ignore[no-any-return]


def extract_inception_features(
    images: np.ndarray,
    *,
    batch_size: int = 64,
) -> np.ndarray:
    """Extract InceptionV3 ``pool3`` features for ``(N, 3, 32, 32)`` images.

    Returns ``(N, 2048)`` float32 features. Resizes the 32×32 inputs to
    299×299 (InceptionV3's expected input) and runs the network in
    ``eval()`` / ``no_grad()`` mode. Falls back to a deterministic
    random-projection when :mod:`torchvision` is not installed.

    P0-1 redirect: the InceptionV3 construction is now a thin
    delegation to :func:`tools.run_image_eval.extract_inception_features_for_image_eval`
    (the *single canonical* IMAGENET1K_V1 extractor surface). The
    historical ``weights=None, aux_logits=False`` body — which produced
    a randomly-initialized network and ~1e25-magnitude FID values (see
    commit ``2fb3dc0`` audit) — is removed; the canonical surface is
    the only path that produces paper-comparable pool3 features. The
    random-projection fallback (environment-driven, not feature-
    extractor-driven) is preserved.
    """
    if images.ndim != 4 or images.shape[1:] != (3, 32, 32):
        raise ValueError("images_must_have_shape_n_3_32_32")
    if not torch_is_available():
        # Random-projection fallback: deterministic, NOT a real Inception.
        rng = np.random.default_rng(0)
        proj: np.ndarray = rng.standard_normal((3 * 32 * 32, 2048)).astype(np.float64) / np.sqrt(
            3 * 32 * 32
        )
        flat: np.ndarray = images.reshape(images.shape[0], -1).astype(np.float64)
        feats = flat @ proj
        return np.asarray(feats, dtype=np.float32)  # type: ignore[no-any-return]

    # Delegate to the canonical IMAGENET1K_V1 surface. The CIFAR
    # ``batch_size`` is forwarded through. The function moves tensors
    # to CPU; for GPU callers, wrap with a host-side ``device`` argument
    # in the future (out of scope here).
    import torch

    feats = tools_run_image_eval.extract_inception_features_for_image_eval(
        images,
        device=torch.device("cpu"),
        batch_size=int(batch_size),
    )
    return feats  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Baseline reproduction driver
# ---------------------------------------------------------------------------


def run_baseline(
    *,
    num_samples: int,
    nfe: int,
    batch_size: int,
    seed: int,
    weights_path: Path | None,
    reference_features: Path | None,
    output_dir: Path,
) -> dict[str, object]:
    """Run the baseline reproduction. Returns a JSON-serialisable summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    # Wave 56 Agent C fix: when the caller does NOT pass an explicit
    # ``weights_path`` (e.g. the in-process smoke test
    # ``test_eval_rf_cifar_synthetic_smoke`` or a CLI invocation
    # without ``--weights-path``) honour the documented "any of the
    # three preconditions missing ⇒ synthetic" fallback by forcing
    # ``synthetic`` mode. Otherwise ``force_mode="auto"`` would silently
    # pick up the vendored ``data/cifar10_rf.pth`` checkpoint and switch
    # the adapter to torch mode, breaking the smoke test's
    # ``summary["mode"] == "synthetic"`` assertion and also producing a
    # paper-comparable FID number without the operator's explicit
    # consent.
    adapter = RectifiedFlowCIFARAdapter(
        weights_path=weights_path,
        force_mode=("auto" if weights_path is not None else "synthetic"),
        num_steps=int(nfe),
    )

    summary: dict[str, object] = {
        "mode": str(adapter._mode),  # noqa: SLF001 — internal logging.
        "weights_path": str(adapter._weights_path),  # noqa: SLF001
        "num_samples": int(num_samples),
        "nfe": int(nfe),
        "seed": int(seed),
        "torch_available": bool(torch_is_available()),
        "published_baseline_fid": float(PUBLISHED_BASELINE_FID),
        "within_5pct_band": None,
        "wall_clock_per_round_seconds": None,
        "fid": None,
    }

    print(
        f"[{'SYNTHETIC' if adapter._mode == 'synthetic' else 'TORCH'} BASELINE] "
        f"mode={adapter._mode} weights={adapter._weights_path} "
        f"num_samples={num_samples} nfe={nfe}"
    )

    # 1. Generate samples.
    t0 = time.perf_counter()
    samples = adapter.batched_inference(
        n_samples=int(num_samples),
        num_steps=int(nfe),
        seed=int(seed),
    )
    gen_seconds = time.perf_counter() - t0
    summary["generation_seconds"] = float(gen_seconds)
    summary["samples_per_second"] = float(num_samples) / float(max(gen_seconds, 1e-12))
    samples_path = output_dir / "samples.npy"
    np.save(samples_path, samples)
    summary["samples_path"] = str(samples_path)

    # 2. Extract InceptionV3 features.
    t1 = time.perf_counter()
    feats = extract_inception_features(samples, batch_size=int(batch_size))
    feat_seconds = time.perf_counter() - t1
    summary["inception_seconds"] = float(feat_seconds)

    # 3. Compute FID.
    if reference_features is not None and reference_features.exists():
        ref = np.load(reference_features)["features"].astype(np.float32)
        fid = compute_fid(feats.astype(np.float64), ref.astype(np.float64))
    else:
        # Honest fallback: compute FID against a synthetic reference of
        # the same size so the codepath still runs. The printed FID is
        # meaningless (synthetic-vs-synthetic) but the script doesn't
        # silently skip the FID step.
        print("[FALLBACK REFERENCE] No real Inception features; using random reference.")
        ref = random_inception_features(num_samples, dim=2048, seed=1).astype(np.float32)
        fid = compute_fid(feats.astype(np.float64), ref.astype(np.float64))
        summary["fallback_reference"] = True

    summary["fid"] = float(fid)
    summary["within_5pct_band"] = bool(fid <= PUBLISHED_BASELINE_FID * 1.05)

    # P1-6: additive eval_report block (typed shape). The legacy
    # baseline_summary.json shape is preserved verbatim; consumers
    # that ignore unknown keys see no change.
    #
    # Wave 51 Agent B fix: previously the caller constructed
    # ``output_dir / "cifar10_reference.npz"`` — a PosixPath that did
    # not exist on disk — which crashed run_eval.py:436 with
    # ``cannot coerce reference=PosixPath into features``. The eval
    # layer is out of scope for this fix (DO NOT touch
    # adaptive_reflow/eval/), so we fix the caller to (a) only pass
    # ``reference=`` when the reference path actually exists on disk,
    # and (b) feed ``run_eval`` the already-computed 2-D Inception
    # features (``feats``) as the ``adapter`` argument rather than the
    # raw-samples path. When the reference is missing we synthesise a
    # same-dim fallback via :func:`random_inception_features` instead
    # of relying on ``_as_reference_features``'s (4, 64) hard-coded
    # fallback — which mismatches the 2048-dim InceptionV3 dim that
    # ``_dispatch_fid`` configures the evaluator with.
    from adaptive_reflow.eval.run_eval import run_eval

    if reference_features is not None and reference_features.exists():
        eval_reference: Any = reference_features
    else:
        # Match the actual Inception feature dim so the eval layer's
        # FID math doesn't blow up on a (4, 64) vs (n, 2048) mismatch.
        eval_reference = random_inception_features(
            int(num_samples), dim=int(feats.shape[1]), seed=int(seed) + 1
        ).astype(np.float64)

    _eval_result = run_eval(
        adapter=feats,
        dataset={"name": "cifar10"},
        metric="fid",
        reference=eval_reference,
        device="cpu",
        seed=int(seed),
        output_dir=None,
    )
    summary["eval_report"] = _eval_result.to_dict()

    out_json = output_dir / "baseline_summary.json"
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    summary["summary_path"] = str(out_json)
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.eval_rf_cifar",
        description="Rectified Flow CIFAR-10 baseline reproduction (Liu 2022).",
    )
    p.add_argument("--num-samples", type=int, default=64,
                   help="Number of samples to generate (paper uses 50000).")
    p.add_argument("--nfe", type=int, default=2,
                   help="Number of Euler integration steps (paper uses 2).")
    p.add_argument("--batch-size", type=int, default=64,
                   help="Batch size for InceptionV3 forward pass.")
    p.add_argument("--seed", type=int, default=42,
                   help="PRNG seed (NumPy; numpy.random.default_rng).")
    p.add_argument("--weights-path", type=str, default=None,
                   help="Explicit path to UNet state_dict (.safetensors / .pth / .pt).")
    p.add_argument("--reference-features", type=str, default=DEFAULT_REFERENCE_FEATURES,
                   help="Path to .npz with real CIFAR-10 InceptionV3 features.")
    p.add_argument("--output-dir", type=str, default="data/rf_baseline",
                   help="Where to save the samples + summary JSON.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    weights = Path(args.weights_path) if args.weights_path else None
    ref = Path(args.reference_features) if args.reference_features else None
    output = Path(args.output_dir)

    try:
        summary = run_baseline(
            num_samples=args.num_samples,
            nfe=args.nfe,
            batch_size=args.batch_size,
            seed=args.seed,
            weights_path=weights,
            reference_features=ref,
            output_dir=output,
        )
    except Exception as exc:  # noqa: BLE001 — final guard, report & exit 1
        print(f"[ERROR] baseline run failed: {exc!r}", file=sys.stderr)
        return 1

    print(
        f"[DONE] mode={summary['mode']} samples={summary['num_samples']} "
        f"fid={summary['fid']!s} (published baseline {PUBLISHED_BASELINE_FID}) "
        f"within_5pct={summary['within_5pct_band']} "
        f"gen_sec={summary['generation_seconds']:.1f}"
    )
    print(f"[DONE] summary -> {summary['summary_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
