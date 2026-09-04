"""Compute InceptionV3 FID between two .npz sample sets (CIFAR-10 32x32).

Both .npz files are expected to contain key 'samples' with shape
(N, 3, 32, 32) float32/float64 arrays in [-1, 1]. The script:
  1. Loads InceptionV3 (2048-d pool3 features) via the canonical
     :func:`tools.run_image_eval.load_inception_for_fid` surface
     (IMAGENET1K_V1, single source of truth — P0-1).
  2. Maps [-1, 1] -> [0, 1] and ImageNet-normalises (canonical mean/std).
  3. Bilinearly resizes to 299x299.
  4. Returns Fréchet distance on activation Gaussians via the
     canonical :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator`.

Usage:
    python compute_cifar_fid.py <gen.npz> <ref.npz> [<gen.npz> <ref.npz> ...]

Each pair prints "=== FID: <value> ===" on its own line; the orchestrator
in tools/run_sota_cifar_experiment.py greps that line. A JSON companion
line is also emitted (``{"fid": <value>, "extractor_family": "..."}``)
so the orchestrator can prefer JSON in the future without breaking the
existing literal-substring contract.

The Fréchet arithmetic (covariance square root + numerical guards) was
previously a near-duplicate of :func:`tools.eval_rf_cifar.compute_fid`
and :func:`tools.run_image_eval.compute_fid_from_features`. Both
copies have now been folded into
:class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
._compute_frechet_distance_inner`; this script is a thin CLI wrapper
around the shared abstraction.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

# Make the project importable when running as ``python
# tools/compute_cifar_fid.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.fid import InceptionV3FIDEvaluator  # noqa: E402

# P0-1: import the canonical InceptionV3 surface and reuse it. Loaded via
# spec_from_file_location so this script remains self-contained when
# invoked as ``python tools/compute_cifar_fid.py`` (the ``tools/``
# directory is not a package).
_RUN_IMAGE_EVAL_PATH = Path(__file__).resolve().parent / "run_image_eval.py"
_RUN_IMAGE_EVAL_SPEC = importlib.util.spec_from_file_location(
    "tools_run_image_eval_for_compute_cifar_fid", str(_RUN_IMAGE_EVAL_PATH)
)
if _RUN_IMAGE_EVAL_SPEC is None or _RUN_IMAGE_EVAL_SPEC.loader is None:  # pragma: no cover — defensive
    raise ImportError(f"could not load {_RUN_IMAGE_EVAL_PATH}")
tools_run_image_eval = importlib.util.module_from_spec(_RUN_IMAGE_EVAL_SPEC)
sys.modules.setdefault(
    "tools_run_image_eval_for_compute_cifar_fid", tools_run_image_eval
)
_RUN_IMAGE_EVAL_SPEC.loader.exec_module(tools_run_image_eval)


def get_activations(samples: np.ndarray, model: torch.nn.Module, batch_size: int = 32) -> np.ndarray:
    """Run the canonical InceptionV3 on ``(N, 3, 32, 32)`` float arrays in ``[-1, 1]``.

    P0-1: thin pass-through to
    :func:`tools.run_image_eval.extract_inception_features_for_image_eval`.
    The historical ``weights=None`` + ``aux_logits=False`` random-init
    path was removed — see commit ``2fb3dc0`` audit for the regression
    rationale. The forwarded ``model`` arg is now ignored; callers
    should obtain the canonical model via
    :func:`tools.run_image_eval.load_inception_for_fid` (or via this
    helper's defaults). The ``model`` argument is preserved for
    backward compatibility with the previous subprocess shell which
    still imports ``compute_cifar_fid.get_activations``.
    """
    _ = model  # noqa: F841 — intentionally ignored; canonical extractor used
    return tools_run_image_eval.extract_inception_features_for_image_eval(
        samples, device=torch.device("cpu"), batch_size=int(batch_size)
    )


def calculate_frechet_distance(act1: np.ndarray, act2: np.ndarray) -> float:
    """Standard Fréchet distance between two Gaussian fits.

    Thin back-compat wrapper around
    :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
    .compute_from_features`. Returns ``float('nan')`` when either
    operand has fewer than 2 rows (FID is undefined there).
    """
    evaluator = InceptionV3FIDEvaluator(feature_dim=int(act1.shape[1]))
    return float(
        evaluator.compute_from_features(
            act2.astype(np.float64, copy=False),
            act1.astype(np.float64, copy=False),
        ).value
    )


def _load_inception_v3_for_fid() -> torch.nn.Module:
    """Build the canonical InceptionV3 for FID.

    P0-1: thin re-export of
    :func:`tools.run_image_eval.load_inception_for_fid`. The historical
    ``weights=None`` + ``aux_logits=False`` random-init construction
    (commit ``2fb3dc0`` regression) is removed; this helper now
    delegates to the single canonical IMAGENET1K_V1 surface so all
    subprocess callers (``tools/run_sota_cifar_experiment._compute_fid_subprocess``)
    consume the same activations as the MJHQ-30K paper-comparable path.
    """
    return tools_run_image_eval.load_inception_for_fid(torch.device("cpu"))


def compute_fid_for_pair(gen_path: Path, ref_path: Path) -> float:
    gen = np.load(gen_path)["samples"]
    ref = np.load(ref_path)["samples"]
    n = min(int(gen.shape[0]), int(ref.shape[0]))
    gen = np.asarray(gen[:n], dtype=np.float32)
    ref = np.asarray(ref[:n], dtype=np.float32)
    model = _load_inception_v3_for_fid()
    a_gen = get_activations(gen, model)
    a_ref = get_activations(ref, model)
    return calculate_frechet_distance(a_gen, a_ref)


def main() -> None:
    if len(sys.argv) < 3 or (len(sys.argv) - 1) % 2 != 0:
        print("Usage: python compute_cifar_fid.py <gen1.npz> <ref1.npz> [<gen2.npz> <ref2.npz> ...]")
        sys.exit(1)
    args = sys.argv[1:]
    pairs = list(zip(args[0::2], args[1::2], strict=False))
    # Cache the model load across pairs to avoid 95MB download × N
    model = _load_inception_v3_for_fid()
    extractor_family = tools_run_image_eval.CANONICAL_INCEPTION_FAMILY
    results: list[tuple[Path, Path, float]] = []
    for gen_str, ref_str in pairs:
        gen_path, ref_path = Path(gen_str), Path(ref_str)
        gen = np.load(gen_path)["samples"]
        ref = np.load(ref_path)["samples"]
        n = min(int(gen.shape[0]), int(ref.shape[0]))
        a_gen = get_activations(np.asarray(gen[:n], dtype=np.float32), model)
        a_ref = get_activations(np.asarray(ref[:n], dtype=np.float32), model)
        fid = calculate_frechet_distance(a_gen, a_ref)
        results.append((gen_path, ref_path, fid))
        print(f"=== FID ({gen_path.name} vs {ref_path.name}): {fid:.4f} ===", flush=True)
        # P0-1: JSON companion line for forward-compatible parsing. The
        # orchestrator at tools/run_sota_cifar_experiment._compute_fid_subprocess
        # currently parses the literal-substring ``=== FID:`` line; this
        # JSON companion is additive and lets the parser prefer JSON
        # without breaking the existing contract.
        print(
            json.dumps(
                {"fid": fid, "extractor_family": extractor_family, "kind": "pair"}
            ),
            flush=True,
        )
    # Final headline
    if len(results) == 1:
        print(f"=== FID: {results[0][2]:.4f} ===")
        print(
            json.dumps(
                {"fid": results[0][2], "extractor_family": extractor_family, "kind": "headline"}
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()