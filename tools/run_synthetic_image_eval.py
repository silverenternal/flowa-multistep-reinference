"""Theorem-aligned image evaluation under the synthetic image oracle (P-15 phase 3).

Strategic context
-----------------

P-15 sits between the 2D Gaussian-mixture math oracle (P-13) and the
Lumina real-image harness (P-03). This module is the *image-side
evaluation gate*: it runs the framework algorithm against the canonical
synthetic-image ground-truth dataset built by
:mod:`tools.build_synthetic_image_dataset` and emits a
:mod:`adaptive_reflow.eval.fid_theorem_aligned` report that asserts
Theorem 1's BL-distance convergence on the per-round FID trajectory.

The wrapper is a *thin orchestrator*:

1. **Load** the canonical reference statistics from
   ``data/synthetic_image_v1/inception_reference_stats.npz`` (with the
   external fallback path used by ``run_image_eval.py``).
2. **Discover** per-round sub-directories under ``--synthetic-images-dir``
   (the framework arm) and optionally under ``--baseline-images-dir``
   (a no-improvement baseline arm for visual contrast).
3. **Extract** InceptionV3 pool3 features for every round (framework and
   baseline) using the canonical
   :func:`tools.run_image_eval.extract_inception_features_for_image_eval`
   so the feature-space geometry is byte-stable with the production FID
   consumer.
4. **Run** :class:`adaptive_reflow.eval.fid_theorem_aligned
   .PerRoundFIDTracker` on the framework trajectory with the paper
   Proposition-2 default profile ``g(x) = (1 + 0.25 * tanh(x)) * sin(x)``
   and the user-supplied ``--eps-schedule``.
5. **Write** a JSON report under
   ``synthetic_image_theorem_aligned_report.v1`` schema containing
   ``framework_fid_per_round``, ``baseline_fid_per_round`` (when the
   baseline arm is provided), ``paper_quantities``, and the
   ``theorem_aligned_diagnostic``.

Backward compatibility
----------------------

* The legacy :mod:`tools.run_image_eval` is byte-stable when
  ``--synthetic-image`` is omitted (the new flag is additive).
* The wrapper's default ``--reference-stats`` points at the canonical
  synthetic-image InceptionV3 reference; the legacy Lumina/HiDream
  reference stats (``mjhq30k_inception_stats.npz``,
  ``hidream_i1_inception_stats.npz``) are unaffected.

Determinism contract
--------------------

* InceptionV3 runs in ``eval()`` + ``torch.no_grad()`` mode.
* The random-projection inside
  :class:`adaptive_reflow.eval.fid_theorem_aligned.NuGReferenceRegistry`
  is seeded via ``--seed`` so two runs with the same inputs and seed
  return bit-identical ``(ref_mu, ref_sigma)``.
* The Monte-Carlo ``nu_g`` Gaussian fit defaults to the analytic
  fallback (``feature_dim=2048``) so the wrapper does not require a
  large rejection-sampling budget.

Usage::

    python tools/run_synthetic_image_eval.py \\
        --synthetic-images-dir experiments/synth/framework_rounds/ \\
        --baseline-images-dir experiments/synth/baseline_rounds/ \\
        --reference-stats data/synthetic_image_v1/inception_reference_stats.npz \\
        --g-profile "(1 + 0.25 * tanh(x)) * sin(x)" \\
        --eps-schedule "0.5,0.25,0.1,0.05" \\
        --output-json reports/synth_image_theorem_aligned.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Callable

# Make the project importable when running as ``python tools/run_synthetic_image_eval.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


__all__ = [
    "RUN_SYNTHETIC_IMAGE_REPORT_SCHEMA",
    "DEFAULT_SYNTHETIC_IMAGE_REF_STATS_INREPO",
    "DEFAULT_SYNTHETIC_IMAGE_REF_STATS_EXTERNAL",
    "DEFAULT_G_PROFILE_SOURCE",
    "DEFAULT_EPS_SCHEDULE",
    "DEFAULT_FEATURE_DIM",
    "DEFAULT_MC_N",
    "discover_round_subdirs",
    "extract_round_features_for_synthetic_eval",
    "load_synthetic_image_reference_stats",
    "parse_g_profile_source",
    "compute_per_round_fid_against_reference",
    "run_synthetic_image_eval",
    "build_argparser",
    "main",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Output JSON schema identifier (versioned for downstream consumers).
RUN_SYNTHETIC_IMAGE_REPORT_SCHEMA: str = (
    "synthetic_image_theorem_aligned_report.v1"
)

#: Canonical in-repo reference stats path (relative to REPO_ROOT).
DEFAULT_SYNTHETIC_IMAGE_REF_STATS_INREPO: str = (
    "data/synthetic_image_v1/inception_reference_stats.npz"
)

#: Documented external canonical reference stats path produced by
#: :mod:`tools.build_synthetic_image_dataset` on the agent's host. The
#: repo ``.gitignore`` excludes ``data/`` so the in-repo path may be
#: absent on a fresh clone.
DEFAULT_SYNTHETIC_IMAGE_REF_STATS_EXTERNAL: str = (
    "/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz"
)

#: Paper Proposition 2 default profile ``g(x) = (1 + 0.25 * tanh(x)) * sin(x)``.
DEFAULT_G_PROFILE_SOURCE: str = "(1 + 0.25 * math.tanh(x)) * math.sin(x)"

#: Default framework algorithm epsilon schedule (P-15 canonical 5-round run).
DEFAULT_EPS_SCHEDULE: tuple[float, ...] = (0.5, 0.25, 0.1, 0.05)

#: InceptionV3 pool3 feature dimensionality.
DEFAULT_FEATURE_DIM: int = 2048

#: Monte-Carlo sample count for the ``nu_g`` Gaussian fit. ``0`` selects
#: the deterministic analytic fallback (cheap + byte-stable; suitable
#: for the P-15 image oracle gate where the reference statistics come
#: from the canonical 5K synthetic dataset rather than from a Monte-Carlo
#: fit).
DEFAULT_MC_N: int = 0

#: File extensions accepted as image samples.
_SUPPORTED_EXTS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

#: Pattern for parsing the round index out of a subdir name like
#: ``framework_round00`` or ``baseline_round03``.
_ROUND_INDEX_PATTERN = re.compile(r".*_round(\d+)$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def discover_round_subdirs(parent: Path, *, arm: str) -> list[tuple[int, Path]]:
    """Return ``[(round_index, path), ...]`` for every ``{arm}_roundXX`` subdir.

    Sorted ascending by round index so downstream consumers see a stable
    trajectory. Returns an empty list when no ``{arm}_roundXX`` subdirs
    are present (the caller decides whether to raise or fall back).
    """
    if not parent.is_dir():
        return []
    out: list[tuple[int, Path]] = []
    prefix = f"{arm}_round"
    for child in sorted(parent.iterdir()):
        if not child.is_dir() or not child.name.startswith(prefix):
            continue
        suffix = child.name[len(prefix):]
        if not suffix.isdigit():
            continue
        out.append((int(suffix), child))
    out.sort(key=lambda kv: kv[0])
    return out


def load_synthetic_image_reference_stats(path: Path) -> tuple[Any, Any, int]:
    """Load ``(mu, sigma, feature_dim)`` from a synthetic-image reference NPZ.

    Mirrors the legacy
    :func:`tools.run_image_eval.run_fid_metric` schema (``mu`` /
    ``sigma`` keys, both ``float64``) so the same on-disk format is
    used by :mod:`tools.build_synthetic_image_dataset` and consumed
    here.

    Raises
    ------
    FileNotFoundError
        When the reference stats path does not exist.
    ValueError
        When the reference stats NPZ is missing the ``mu`` / ``sigma``
        keys or has an inconsistent shape.
    """
    import numpy as np

    if not path.exists():
        raise FileNotFoundError(
            f"synthetic_image_reference_stats_not_found: {path}"
        )
    ref = np.load(path)
    if "mu" not in ref.files or "sigma" not in ref.files:
        raise ValueError(
            f"synthetic_image_reference_stats_missing_mu_sigma_keys: {path} "
            f"(found keys {list(ref.files)!r})"
        )
    mu = np.asarray(ref["mu"], dtype=np.float64)
    sigma = np.asarray(ref["sigma"], dtype=np.float64)
    if mu.ndim != 1:
        raise ValueError(
            f"synthetic_image_reference_stats_mu_must_be_1d: shape={mu.shape}"
        )
    if sigma.ndim != 2 or sigma.shape[0] != sigma.shape[1]:
        raise ValueError(
            f"synthetic_image_reference_stats_sigma_must_be_square_2d: "
            f"shape={sigma.shape}"
        )
    if sigma.shape[0] != mu.shape[0]:
        raise ValueError(
            f"synthetic_image_reference_stats_mu_sigma_dim_mismatch: "
            f"mu.shape={mu.shape}, sigma.shape={sigma.shape}"
        )
    return mu, sigma, int(mu.shape[0])


def resolve_synthetic_image_reference_stats_path(
    *,
    explicit: Path | None = None,
) -> Path:
    """Return the canonical synthetic-image reference stats path.

    Search order (first match wins):

    1. ``explicit`` (when provided).
    2. ``<REPO_ROOT>/data/synthetic_image_v1/inception_reference_stats.npz``.
    3. ``/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz``.

    Raises
    ------
    FileNotFoundError
        When none of the candidate paths exist.
    """
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(
                f"synthetic_image_reference_stats_not_found (explicit): {explicit}"
            )
        return explicit
    in_repo = REPO_ROOT / DEFAULT_SYNTHETIC_IMAGE_REF_STATS_INREPO
    if in_repo.is_file():
        return in_repo
    external = Path(DEFAULT_SYNTHETIC_IMAGE_REF_STATS_EXTERNAL)
    if external.is_file():
        return external
    raise FileNotFoundError(
        "synthetic_image_reference_stats_not_found: tried "
        f"{in_repo} (in-repo) and {external} (external canonical); "
        "run tools/build_synthetic_image_dataset.py --n-samples 5000 "
        "to materialise the canonical 5K reference."
    )


def parse_g_profile_source(source: str) -> Callable[[float], float]:
    """Compile a textual ``g(x)`` expression into a pure-Python callable.

    The compilation uses Python's :mod:`ast` module so the source is
    *parsed* (rather than blindly ``eval``-ed against the caller
    namespace); the resulting callable only references
    :mod:`math` symbols plus the local name ``x``. This keeps the
    contract strict (no global state mutation, no attribute access on
    arbitrary objects) while still supporting the common paper
    profiles (``sin``, ``cos``, ``tanh``, etc.).

    Parameters
    ----------
    source
        A single-expression string in the variable ``x`` that uses
        :mod:`math` symbols (e.g. ``"(1 + 0.25 * math.tanh(x)) * math.sin(x)"``).

    Returns
    -------
    g
        Callable mapping ``float -> float``.

    Raises
    ------
    ValueError
        When ``source`` is not a parseable expression or references
        unknown names.
    """
    import ast
    import math as _math

    allowed_math_names = set(dir(_math))
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError(
            f"g_profile_source_not_parseable: {source!r} ({exc})"
        ) from exc

    # Walk the AST and confirm every Name is either ``x`` or ``math``
    # (the latter is the prefix of every permitted ``math.<symbol>``
    # attribute access); other top-level names are rejected.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in ("x", "math"):
                continue
            raise ValueError(
                f"g_profile_source_disallowed_name: {node.id!r}; only the "
                "variable 'x' and 'math.<symbol>' references are allowed."
            )
        if isinstance(node, ast.Attribute):
            # Only ``math.<symbol>`` is permitted. Detect by checking the
            # value is a ``Name`` node with id=='math'.
            if not (
                isinstance(node.value, ast.Name)
                and node.value.id == "math"
                and node.attr in allowed_math_names
            ):
                raise ValueError(
                    f"g_profile_source_disallowed_attribute: {ast.dump(node)}; "
                    "only 'math.<symbol>' references are allowed."
                )

    code = compile(tree, "<g_profile_source>", "eval")

    def _g(x: float) -> float:
        return float(eval(code, {"__builtins__": {}}, {"math": _math, "x": float(x)}))  # noqa: S307

    return _g


def extract_round_features_for_synthetic_eval(
    image_paths: list[Path],
    *,
    device: Any,
    target_size: int,
    batch_size: int,
) -> Any:
    """Run the canonical InceptionV3 over a round's images; return ``(n, 2048)``.

    Thin wrapper around
    :func:`tools.run_image_eval.extract_inception_features_for_image_eval`
    so the feature-space geometry is byte-stable with the production
    FID consumer. Local import keeps the module import-time
    stdlib-only.
    """
    import numpy as np

    from tools.run_image_eval import (
        extract_inception_features_for_image_eval,  # P0-1 canonical extractor surface (torchvision IMAGENET1K_V1)
        load_images_as_tensor,
    )

    images = load_images_as_tensor(
        [Path(p) for p in image_paths], target_size=int(target_size),
    )
    if images.shape[0] == 0:
        return np.zeros((0, int(DEFAULT_FEATURE_DIM)), dtype=np.float32)
    return extract_inception_features_for_image_eval(
        images, device=device, batch_size=int(batch_size),
    )


def compute_per_round_fid_against_reference(
    features_per_round: list[Any],
    *,
    ref_mu: Any,
    ref_sigma: Any,
) -> list[dict[str, Any]]:
    """Compute per-round FID against a fixed reference ``(mu, sigma)``.

    Returns a list of dicts (one per round) with the FID value plus the
    round's sample count + feature dimensionality. The FID math is
    delegated to
    :func:`tools.run_image_eval.compute_fid_from_features` (the
    production canonical Fréchet arithmetic); a NaN sentinel is
    returned for any round with fewer than 2 feature rows so the
    downstream convergence diagnostic can skip degenerate rounds.
    """
    from tools.run_image_eval import compute_fid_from_features

    out: list[dict[str, Any]] = []
    for r, feats in enumerate(features_per_round):
        n_samples = int(feats.shape[0])
        feature_dim = int(feats.shape[1]) if feats.ndim == 2 else 0
        if n_samples < 2:
            out.append(
                {
                    "round_index": int(r),
                    "n_samples": n_samples,
                    "feature_dim": feature_dim,
                    "fid": float("nan"),
                    "error": "too_few_samples_for_fid",
                }
            )
            continue
        fid_value = float(
            compute_fid_from_features(feats, ref_mu, ref_sigma)
        )
        out.append(
            {
                "round_index": int(r),
                "n_samples": n_samples,
                "feature_dim": feature_dim,
                "fid": fid_value if math.isfinite(fid_value) else None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def run_synthetic_image_eval(
    *,
    synthetic_images_dir: Path,
    output_json: Path,
    baseline_images_dir: Path | None = None,
    reference_stats_path: Path | None = None,
    g_profile_source: str = DEFAULT_G_PROFILE_SOURCE,
    epsilon_schedule: tuple[float, ...] = DEFAULT_EPS_SCHEDULE,
    feature_dim: int = DEFAULT_FEATURE_DIM,
    monte_carlo_n: int = DEFAULT_MC_N,
    seed: int = 0,
    image_target_size: int = 299,
    fid_batch_size: int = 16,
    device_arg: str = "auto",
    arm_framework: str = "framework",
    arm_baseline: str = "baseline",
) -> dict[str, Any]:
    """Top-level orchestrator: per-round FID + theorem-aligned diagnostic.

    Parameters
    ----------
    synthetic_images_dir
        Parent directory containing ``{arm_framework}_roundXX/``
        sub-directories of PNGs/JPGs (one subdir per round).
    output_json
        Path to write the ``synthetic_image_theorem_aligned_report.v1``
        JSON report.
    baseline_images_dir
        Optional parent directory containing
        ``{arm_baseline}_roundXX/`` sub-directories. When provided, the
        report emits ``baseline_fid_per_round`` alongside
        ``framework_fid_per_round``.
    reference_stats_path
        Path to the canonical InceptionV3 reference statistics NPZ.
        Defaults to the canonical synthetic-image path (in-repo
        first, external fallback second).
    g_profile_source
        Source expression for the profile ``g(x)`` consumed by
        :class:`adaptive_reflow.eval.fid_theorem_aligned.PaperQuantitiesSnapshot
        .for_profile` and
        :meth:`adaptive_reflow.eval.fid_theorem_aligned.NuGReferenceRegistry
        .get_or_compute`.
    epsilon_schedule
        ``(eps_0, eps_1, ..., eps_{R-1})`` from the framework scheduler.
    feature_dim
        InceptionV3 pool3 dimensionality (canonical ``2048``).
    monte_carlo_n
        Monte-Carlo sample count for ``nu_g`` Gaussian fit; ``0``
        selects the analytic fallback.
    seed
        Seed for the ``nu_g`` Monte-Carlo fit (when used).
    image_target_size
        Bilinear resize applied to every image at load time.
    fid_batch_size
        Batch size for the InceptionV3 forward pass.
    device_arg
        Torch device string (``"auto"``, ``"cuda:0"``, ``"cpu"``).
    arm_framework, arm_baseline
        Arm prefixes for the per-round subdir naming convention.

    Returns
    -------
    report
        The dict that was written to ``output_json``.
    """
    import numpy as np

    from adaptive_reflow.eval.fid_theorem_aligned import (
        NuGReferenceRegistry,
        PaperQuantitiesSnapshot,
        PerRoundFIDTracker,
    )
    from tools.run_image_eval import select_device

    t0 = time.perf_counter()

    # Resolve reference stats (canonical by default; explicit override wins).
    resolved_ref_path = resolve_synthetic_image_reference_stats_path(
        explicit=reference_stats_path,
    )
    ref_mu, ref_sigma, ref_feature_dim = load_synthetic_image_reference_stats(
        resolved_ref_path,
    )
    if ref_feature_dim != int(feature_dim):
        raise ValueError(
            f"reference_stats_feature_dim {ref_feature_dim} != configured "
            f"feature_dim {int(feature_dim)}; pass --feature-dim "
            f"{ref_feature_dim} to override."
        )

    # Discover per-round sub-directories.
    framework_rounds = discover_round_subdirs(
        synthetic_images_dir, arm=str(arm_framework),
    )
    if not framework_rounds:
        raise FileNotFoundError(
            f"no_framework_rounds_found: expected "
            f"{synthetic_images_dir}/{arm_framework}_roundXX/ subdirs."
        )

    baseline_rounds: list[tuple[int, Path]] = []
    if baseline_images_dir is not None:
        baseline_rounds = discover_round_subdirs(
            baseline_images_dir, arm=str(arm_baseline),
        )
        if not baseline_rounds:
            print(
                f"[run_synthetic_image_eval] WARNING: --baseline-images-dir "
                f"{baseline_images_dir} has no {arm_baseline}_roundXX/ "
                f"subdirs; baseline_fid_per_round will be omitted.",
                file=sys.stderr,
            )

    # Materialise the profile ``g`` and the paper-quantities snapshot.
    g = parse_g_profile_source(str(g_profile_source))
    paper_quantities = PaperQuantitiesSnapshot.for_profile(g)
    registry = NuGReferenceRegistry(
        feature_dim=int(feature_dim),
        monte_carlo_n=int(monte_carlo_n),
    )
    # We don't actually USE the registry's ``nu_g`` fit here because
    # we already have an explicit reference from the canonical 5K
    # synthetic dataset. We still want to materialise it so the
    # tracker can compute paper quantities uniformly. The tracker's
    # ``.run`` method calls ``registry.get_or_compute(g, seed=seed)``
    # internally; we pre-warm it here so any cache-miss diagnostics
    # are visible in the timing.
    nu_g_mu, nu_g_sigma = registry.get_or_compute(g, seed=int(seed))

    # Extract per-round features for the framework arm.
    device = select_device(str(device_arg))
    framework_features_per_round: list[Any] = []
    framework_n_per_round: list[int] = []
    framework_round_dirs: list[str] = []
    for r_idx, r_dir in framework_rounds:
        paths = sorted(
            p for p in r_dir.iterdir()
            if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTS
        )
        feats = extract_round_features_for_synthetic_eval(
            paths, device=device, target_size=int(image_target_size),
            batch_size=int(fid_batch_size),
        )
        framework_features_per_round.append(feats)
        framework_n_per_round.append(int(feats.shape[0]))
        framework_round_dirs.append(str(r_dir))

    # Per-round FID against the canonical reference for the framework arm.
    framework_fid_per_round = compute_per_round_fid_against_reference(
        framework_features_per_round,
        ref_mu=ref_mu, ref_sigma=ref_sigma,
    )

    # Optional baseline arm.
    baseline_fid_per_round: list[dict[str, Any]] | None = None
    baseline_round_dirs: list[str] | None = None
    baseline_n_per_round: list[int] | None = None
    if baseline_rounds:
        baseline_features_per_round: list[Any] = []
        baseline_round_dirs = []
        baseline_n_per_round = []
        for r_idx, r_dir in baseline_rounds:
            paths = sorted(
                p for p in r_dir.iterdir()
                if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTS
            )
            feats = extract_round_features_for_synthetic_eval(
                paths, device=device, target_size=int(image_target_size),
                batch_size=int(fid_batch_size),
            )
            baseline_features_per_round.append(feats)
            baseline_n_per_round.append(int(feats.shape[0]))
            baseline_round_dirs.append(str(r_dir))
        baseline_fid_per_round = compute_per_round_fid_against_reference(
            baseline_features_per_round,
            ref_mu=ref_mu, ref_sigma=ref_sigma,
        )

    # Sanity-check the eps schedule length vs the number of framework rounds.
    eps_list = [float(e) for e in epsilon_schedule]
    if len(eps_list) != len(framework_rounds):
        raise ValueError(
            f"epsilon_schedule length {len(eps_list)} != "
            f"framework rounds count {len(framework_rounds)}; "
            f"pass --eps-schedule with exactly {len(framework_rounds)} values."
        )

    # Run the theorem-aligned tracker. We pass the per-round features as
    # ``(n_r, d)`` arrays; the tracker wraps them in
    # :class:`adaptive_reflow.eval.fid_theorem_aligned.FIDPerRoundResult`
    # objects with paper-quantity fields. The tracker's reference is the
    # profile-driven ``nu_g`` fit; the per-round FID against the
    # *canonical* reference is emitted separately under
    # ``framework_fid_per_round``.
    tracker = PerRoundFIDTracker(
        evaluator=None,  # default InceptionV3TheoremAlignedFIDEvaluator
        reference_registry=registry,
    )
    theorem_report = tracker.run(
        g,
        framework_features_per_round,
        epsilon_schedule=eps_list,
        seed=int(seed),
    )

    # Build the theorem-aligned diagnostic dict (matches
    # :class:`adaptive_reflow.eval.fid_theorem_aligned.ConvergenceDiagnostic`
    # but JSON-serialisable).
    theorem_diagnostic = {
        "monotone": bool(theorem_report.convergence.monotone),
        "O_eps_holds": bool(theorem_report.convergence.O_eps_holds),
        "per_round_deltas": [
            float(d) if math.isfinite(float(d)) else None
            for d in theorem_report.convergence.per_round_deltas
        ],
        "paper_implied_constant": float(
            theorem_report.convergence.paper_implied_constant
        ),
        "observed_constant": (
            float(theorem_report.convergence.observed_constant)
            if math.isfinite(float(theorem_report.convergence.observed_constant))
            else None
        ),
        "regime_violations": [
            int(r) for r in theorem_report.convergence.regime_violations
        ],
        "paper_quantities_snapshot": {
            "A_g": float(theorem_report.paper_quantities_snapshot.A_g),
            "B_g": float(theorem_report.paper_quantities_snapshot.B_g),
            "C_g": float(theorem_report.paper_quantities_snapshot.C_g),
            "e_rho": float(theorem_report.paper_quantities_snapshot.e_rho),
            "rho": float(theorem_report.paper_quantities_snapshot.rho),
            "c": float(theorem_report.paper_quantities_snapshot.c),
            "eta": float(theorem_report.paper_quantities_snapshot.eta),
            "K": float(theorem_report.paper_quantities_snapshot.K),
            "h": float(theorem_report.paper_quantities_snapshot.h),
        },
        "epsilon_schedule": eps_list,
    }

    # Aggregate status flag. The theorem-aligned report converges
    # (= ``monotone=True`` AND ``O_eps_holds=True``) when the framework
    # produces a valid per-round FID trajectory.
    all_framework_fids_finite = all(
        isinstance(entry.get("fid"), (int, float))
        and math.isfinite(float(entry["fid"]))
        for entry in framework_fid_per_round
    )
    status = "ok"
    if not all_framework_fids_finite:
        status = "framework_fid_not_all_finite"
    if not theorem_diagnostic["monotone"]:
        status = "monotonicity_violated"
    if not theorem_diagnostic["O_eps_holds"]:
        status = "O_eps_bound_violated"

    report: dict[str, Any] = {
        "schema": RUN_SYNTHETIC_IMAGE_REPORT_SCHEMA,
        "synthetic_images_dir": str(synthetic_images_dir),
        "baseline_images_dir": (
            str(baseline_images_dir) if baseline_images_dir else None
        ),
        "reference_stats_path": str(resolved_ref_path),
        "g_profile_source": str(g_profile_source),
        "feature_dim": int(feature_dim),
        "monte_carlo_n": int(monte_carlo_n),
        "seed": int(seed),
        "arm_framework": str(arm_framework),
        "arm_baseline": str(arm_baseline),
        "n_rounds": len(framework_rounds),
        "framework_round_dirs": framework_round_dirs,
        "framework_n_samples_per_round": framework_n_per_round,
        "framework_fid_per_round": framework_fid_per_round,
        "baseline_round_dirs": baseline_round_dirs,
        "baseline_n_samples_per_round": baseline_n_per_round,
        "baseline_fid_per_round": baseline_fid_per_round,
        "paper_quantities": {
            "A_g": float(paper_quantities.A_g),
            "B_g": float(paper_quantities.B_g),
            "C_g": float(paper_quantities.C_g),
            "e_rho": float(paper_quantities.e_rho),
            "rho": float(paper_quantities.rho),
            "c": float(paper_quantities.c),
            "eta": float(paper_quantities.eta),
            "K": float(paper_quantities.K),
            "h": float(paper_quantities.h),
        },
        "theorem_aligned_diagnostic": theorem_diagnostic,
        "wall_clock_seconds": float(time.perf_counter() - t0),
        "status": str(status),
    }

    # Use ``numpy`` types defensively in case ``framework_fid_per_round``
    # or ``theorem_diagnostic`` contain any ndarray-derived scalars.
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return report


def _json_default(obj: Any) -> Any:
    """JSON encoder fallback for ``numpy`` scalars / arrays."""
    try:
        import numpy as np
    except ImportError:  # pragma: no cover — defensive
        return str(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    return str(obj)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    """Return the canonical CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="tools.run_synthetic_image_eval",
        description=(
            "Theorem-aligned image evaluation under the synthetic image "
            "oracle (P-15 phase 3). Runs PerRoundFIDTracker over a "
            "framework algorithm's per-round image samples and emits a "
            "synthetic_image_theorem_aligned_report.v1 JSON report "
            "containing baseline_fid_per_round, framework_fid_per_round, "
            "and the theorem-aligned convergence diagnostic."
        ),
    )
    p.add_argument(
        "--synthetic-images-dir", type=str, required=True,
        help=(
            "Directory containing ``framework_roundXX/`` sub-directories "
            "of PNGs/JPGs (one subdir per framework round)."
        ),
    )
    p.add_argument(
        "--baseline-images-dir", type=str, default=None,
        help=(
            "Optional directory containing ``baseline_roundXX/`` "
            "sub-directories. When provided, the report emits "
            "``baseline_fid_per_round`` alongside "
            "``framework_fid_per_round``."
        ),
    )
    p.add_argument(
        "--reference-stats", type=str, default=None,
        help=(
            "Path to the canonical InceptionV3 reference statistics NPZ "
            "(default: data/synthetic_image_v1/inception_reference_stats.npz "
            "in-repo, falling back to "
            "/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz)."
        ),
    )
    p.add_argument(
        "--g-profile", type=str, default=DEFAULT_G_PROFILE_SOURCE,
        help=(
            "Source expression for the profile g(x) used by the paper "
            "quantities and nu_g fit (default: paper Proposition 2, "
            "(1 + 0.25 * tanh(x)) * sin(x))."
        ),
    )
    p.add_argument(
        "--eps-schedule", type=str,
        default=",".join(str(e) for e in DEFAULT_EPS_SCHEDULE),
        help=(
            "Comma-separated epsilon schedule (default: "
            "0.5,0.25,0.1,0.05 for 4 rounds). Length must match the "
            "number of framework rounds discovered."
        ),
    )
    p.add_argument(
        "--feature-dim", type=int, default=DEFAULT_FEATURE_DIM,
        help="InceptionV3 pool3 feature dimensionality (default: 2048).",
    )
    p.add_argument(
        "--monte-carlo-n", type=int, default=DEFAULT_MC_N,
        help=(
            "Monte-Carlo sample count for nu_g Gaussian fit (default 0 = "
            "analytic fallback, byte-stable and cheap)."
        ),
    )
    p.add_argument(
        "--seed", type=int, default=0,
        help="Seed for the nu_g Monte-Carlo fit (default 0).",
    )
    p.add_argument(
        "--image-target-size", type=int, default=299,
        help="Bilinear resize applied to every image at load time (default: 299).",
    )
    p.add_argument(
        "--fid-batch-size", type=int, default=16,
        help="Batch size for the InceptionV3 forward pass (default: 16).",
    )
    p.add_argument(
        "--device", type=str, default="auto",
        help="Torch device: 'auto' (cuda if available else cpu), or e.g. 'cuda:0'.",
    )
    p.add_argument(
        "--arm-framework", type=str, default="framework",
        help="Arm prefix for the framework per-round subdirs (default: 'framework').",
    )
    p.add_argument(
        "--arm-baseline", type=str, default="baseline",
        help="Arm prefix for the baseline per-round subdirs (default: 'baseline').",
    )
    p.add_argument(
        "--output-json", type=str, required=True,
        help="Path to write the synthetic_image_theorem_aligned_report.v1 JSON.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on error."""
    args = build_argparser().parse_args(argv)
    eps_schedule: tuple[float, ...] = tuple(
        float(s.strip()) for s in str(args.eps_schedule).split(",") if s.strip()
    )
    try:
        report = run_synthetic_image_eval(
            synthetic_images_dir=Path(args.synthetic_images_dir),
            output_json=Path(args.output_json),
            baseline_images_dir=(
                Path(args.baseline_images_dir)
                if args.baseline_images_dir else None
            ),
            reference_stats_path=(
                Path(args.reference_stats) if args.reference_stats else None
            ),
            g_profile_source=str(args.g_profile),
            epsilon_schedule=eps_schedule,
            feature_dim=int(args.feature_dim),
            monte_carlo_n=int(args.monte_carlo_n),
            seed=int(args.seed),
            image_target_size=int(args.image_target_size),
            fid_batch_size=int(args.fid_batch_size),
            device_arg=str(args.device),
            arm_framework=str(args.arm_framework),
            arm_baseline=str(args.arm_baseline),
        )
    except Exception as exc:  # noqa: BLE001 — top-level guard
        print(
            f"[ERROR] synthetic image eval failed: {exc!r}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[DONE] synthetic_image_eval status={report['status']} "
        f"n_rounds={int(report['n_rounds'])} ref={report['reference_stats_path']} "
        f"-> {args.output_json}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover — __main__ guard
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    raise SystemExit(main())
