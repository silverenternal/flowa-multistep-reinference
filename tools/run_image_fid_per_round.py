"""Thin wrapper around :class:`PerRoundFIDTracker` for the harness-level per-round FID path.

Phase 4 / Design #1 — bridges the per-round PNGs written by the Lumina
and HiDream harnesses (Phase 4 / Designs #1 + #2) to the
:class:`PerRoundFIDTracker.run` orchestrator that emits a
:class:`TheoremAlignedFIDReport` (Phase 3 surface — preserved unchanged).

Design boundary
---------------

This wrapper is INTENTIONALLY a thin glue layer. It does NOT own the
theorem-aligned FID math (that lives in
:mod:`adaptive_reflow.eval.fid_theorem_aligned`) and it does NOT own
the InceptionV3 feature extraction (that lives in
:func:`tools.run_image_eval.extract_inception_features_for_image_eval`).
The wrapper just glues the two together and writes a JSON report to
``--output``.

CLI
---

::

    python tools/run_image_fid_per_round.py \\
        --per-round-dirs output/framework_round00 output/framework_round01 ... \\
        --reference-stats data/lumina_image_2_0/mjhq30k_inception_stats.npz \\
        --epsilon-schedule '[0.1, 0.05]' \\
        --output output/per_round_fid_report.json

The output JSON is a ``TheoremAlignedFIDReport`` with
``.rounds`` (length = n_rounds), ``.convergence`` (the
:class:`ConvergenceDiagnostic` carrying ``monotone`` / ``O_eps_holds``
/ ``per_round_deltas`` / ``paper_implied_constant`` /
``observed_constant`` / ``regime_violations``) and
``.paper_quantities_snapshot`` (A_g / B_g / C_g / e_rho / rho / eta /
c).

Phase 3 byte-stability
----------------------

This wrapper is purely ADDITIVE — the legacy single-shot
:func:`tools.run_image_eval.run_image_eval` path is untouched, and the
:class:`TheoremAlignedFID` surface in
:mod:`adaptive_reflow.eval.fid_theorem_aligned` is also untouched. The
wrapper reads PNGs from disk and runs InceptionV3 + theorem-aligned
FID math against them; it never mutates scheduler state.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

# Make the repo importable when invoked as ``python tools/run_image_fid_per_round.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.run_image_eval import (  # noqa: E402  — path setup above
    discover_samples,
    extract_inception_features_for_image_eval,
    load_images_as_tensor,
    select_device,
)


# ---------------------------------------------------------------------------
# InceptionV3 feature extraction glue
# ---------------------------------------------------------------------------


def _default_g(x: float) -> float:
    """Canonical paper profile ``g(x) = x^2`` (paper Section 4.1)."""
    return float(x) * float(x)


def _load_features_for_round(
    round_dir: Path,
    *,
    device: Any,
    image_target_size: int = 299,
    batch_size: int = 16,
) -> np.ndarray:
    """Load PNGs from ``round_dir``, run InceptionV3, return ``(N, 2048)`` features.

    Empty / missing directories raise :class:`FileNotFoundError` so the
    caller can surface them as a per-round diagnostic in the report.
    """
    samples = discover_samples(round_dir)
    images = load_images_as_tensor(samples, target_size=int(image_target_size))
    return extract_inception_features_for_image_eval(
        images, device=device, batch_size=int(batch_size)
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_image_fid_per_round(
    *,
    per_round_dirs: Sequence[Path],
    epsilon_schedule: Sequence[float],
    reference_stats_path: Path | None = None,
    profile: Any = _default_g,
    rho: float = 0.1,
    c: float = 1.0,
    eta: float = 0.1,
    device_arg: str = "auto",
    image_target_size: int = 299,
    fid_batch_size: int = 16,
    feature_dim: int = 2048,
    monte_carlo_n: int = 0,
    seed: int = 0,
    tolerance: float = 1e-3,
    output: Path | None = None,
) -> dict[str, Any]:
    """Run per-round theorem-aligned FID across ``per_round_dirs``.

    Parameters
    ----------
    per_round_dirs
        Sequence of directories; each contains PNGs for one round.
        Must align 1:1 with ``epsilon_schedule``.
    epsilon_schedule
        ``len(per_round_dirs)`` ``eps_r`` values from the framework
        scheduler (read-only).
    reference_stats_path
        Optional MJHQ-30K .npz — kept for diagnostic only; the
        theorem-aligned path fits its OWN Gaussian ``nu_g`` reference
        via :class:`NuGReferenceRegistry`. May be ``None``.
    profile
        Callable ``g : R -> R`` for which ``nu_g`` is built. Default
        ``g(x) = x^2`` matches the canonical paper profile.
    rho, c, eta
        Paper-quantity knobs.
    device_arg
        Torch device selection (same vocabulary as
        :func:`tools.run_image_eval.select_device`).
    image_target_size
        Resize applied to every PNG before InceptionV3 forward pass.
    fid_batch_size
        InceptionV3 batch size.
    feature_dim
        Dimensionality of the random-projection target.
    monte_carlo_n
        Monte-Carlo sample count for the ``nu_g`` Gaussian fit; ``0``
        falls back to a deterministic analytic Gaussian.
    seed
        Monte-Carlo seed.
    output
        Optional output path; when provided the JSON report is written.

    Returns
    -------
    dict
        The :class:`TheoremAlignedFIDReport` serialised as a dict.
    """
    if len(per_round_dirs) != len(epsilon_schedule):
        raise ValueError(
            f"per_round_dirs (len={len(per_round_dirs)}) and "
            f"epsilon_schedule (len={len(epsilon_schedule)}) must match"
        )
    if len(per_round_dirs) == 0:
        raise ValueError("per_round_dirs must be non-empty")

    # Import here (not at module scope) so the wrapper can be imported
    # in environments that lack torch without breaking module-level
    # imports of unrelated sub-modules.
    from adaptive_reflow.eval.fid_theorem_aligned import (
        NuGReferenceRegistry,
        PaperQuantitiesSnapshot,
        PerRoundFIDTracker,
    )

    device = select_device(device_arg)

    features_per_round: list[np.ndarray] = []
    for round_idx, round_dir in enumerate(per_round_dirs):
        feats = _load_features_for_round(
            round_dir,
            device=device,
            image_target_size=int(image_target_size),
            batch_size=int(fid_batch_size),
        )
        # The theorem-aligned evaluator expects ``float64`` features; cast
        # so the Frechet's inner arithmetic is bit-stable across runs.
        features_per_round.append(np.asarray(feats, dtype=np.float64))

    evaluator = None
    try:
        from adaptive_reflow.eval.fid_theorem_aligned import (
            InceptionV3TheoremAlignedFIDEvaluator,
        )

        evaluator = InceptionV3TheoremAlignedFIDEvaluator()
    except ImportError:  # pragma: no cover — defensive
        evaluator = None

    registry = NuGReferenceRegistry(
        feature_dim=int(feature_dim),
        monte_carlo_n=int(monte_carlo_n),
    )
    tracker = PerRoundFIDTracker(
        evaluator=evaluator,
        reference_registry=registry,
    )
    report = tracker.run(
        profile,
        sample_features_per_round=features_per_round,
        epsilon_schedule=epsilon_schedule,
        rho=float(rho),
        c=float(c),
        eta=float(eta),
        tolerance=float(tolerance),
        seed=int(seed),
    )

    # Serialise the report to a JSON-friendly dict. ``TheoremAlignedFIDReport``
    # exposes dataclass-style attributes; we round floats to keep the
    # JSON human-readable (no precision loss in math, just display).
    snapshot = report.paper_quantities_snapshot
    serialised: dict[str, Any] = {
        "schema": "theorem_aligned_fid_report.v1",
        "profile_id": "x^2" if profile is _default_g else repr(profile),
        "rounds": [
            {
                "round_index": int(r.round_index),
                "fid_value": (
                    float(r.result.value)
                    if r.result.value is not None
                    and math.isfinite(float(r.result.value))
                    else None
                ),
                "epsilon": float(r.epsilon),
                "regime_check_ok": bool(r.result.regime_check_ok),
            }
            for r in report.rounds
        ],
        "convergence": {
            "monotone": bool(report.convergence.monotone),
            "O_eps_holds": bool(report.convergence.O_eps_holds),
            "per_round_deltas": [
                float(d) for d in report.convergence.per_round_deltas
            ],
            "paper_implied_constant": float(report.convergence.paper_implied_constant),
            "observed_constant": float(report.convergence.observed_constant),
            "regime_violations": list(report.convergence.regime_violations),
        },
        "paper_quantities_snapshot": {
            "A_g": float(snapshot.A_g),
            "B_g": float(snapshot.B_g),
            "C_g": float(snapshot.C_g),
            "e_rho": float(snapshot.e_rho),
            "rho": float(snapshot.rho),
            "c": float(snapshot.c),
            "eta": float(snapshot.eta),
        },
        "n_rounds": int(len(report.rounds)),
        "reference_stats_path": (
            str(reference_stats_path) if reference_stats_path else None
        ),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(serialised, indent=2, sort_keys=True))
    return serialised


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.run_image_fid_per_round",
        description=(
            "Phase 4 / Design #1 — run per-round theorem-aligned FID "
            "(Li 2026 Theorem 1) over a sequence of per-round PNG "
            "directories and emit a TheoremAlignedFIDReport JSON."
        ),
    )
    p.add_argument(
        "--per-round-dir",
        action="append",
        required=True,
        help=(
            "Directory containing PNGs for one round. Repeat the flag "
            "to enumerate rounds (e.g. --per-round-dir output/framework_round00 "
            "--per-round-dir output/framework_round01 ...)."
        ),
    )
    p.add_argument(
        "--epsilon-schedule",
        type=str,
        required=True,
        help=(
            "JSON array of per-round eps values (e.g. '[0.1, 0.05]'). "
            "Length MUST equal the number of --per-round-dir flags."
        ),
    )
    p.add_argument(
        "--reference-stats",
        type=str,
        default=None,
        help=(
            "Optional MJHQ-30K .npz (diagnostic only; the theorem-aligned "
            "path fits its own Gaussian nu_g reference)."
        ),
    )
    p.add_argument("--rho", type=float, default=0.1, help="Paper rho (default 0.1).")
    p.add_argument("--c", type=float, default=1.0, help="Paper c (default 1.0).")
    p.add_argument("--eta", type=float, default=0.1, help="Paper eta (default 0.1).")
    p.add_argument(
        "--device", type=str, default="auto",
        help="Torch device: 'auto' (cuda if available else cpu), or e.g. 'cuda:0', 'cpu'.",
    )
    p.add_argument(
        "--image-target-size", type=int, default=299,
        help="Bilinear resize applied to every PNG before InceptionV3 (default 299).",
    )
    p.add_argument(
        "--fid-batch-size", type=int, default=16,
        help="InceptionV3 batch size (default 16).",
    )
    p.add_argument(
        "--feature-dim", type=int, default=2048,
        help="Random-projection target dim (default 2048 = InceptionV3 pool3).",
    )
    p.add_argument(
        "--monte-carlo-n", type=int, default=0,
        help=(
            "Monte-Carlo sample count for the nu_g Gaussian fit. "
            "0 = deterministic analytic Gaussian (default 0)."
        ),
    )
    p.add_argument("--seed", type=int, default=0, help="Monte-Carlo seed (default 0).")
    p.add_argument(
        "--tolerance", type=float, default=1e-3,
        help="Slack for monotonicity + O(eps) checks (default 1e-3).",
    )
    p.add_argument(
        "--output", type=str, required=True,
        help="Path to write the JSON TheoremAlignedFIDReport.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    try:
        epsilon_schedule = [float(x) for x in json.loads(args.epsilon_schedule)]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            f"[ERROR] --epsilon-schedule could not be parsed: {exc!r}",
            file=sys.stderr,
        )
        return 1
    try:
        report = run_image_fid_per_round(
            per_round_dirs=[Path(p) for p in args.per_round_dir],
            epsilon_schedule=epsilon_schedule,
            reference_stats_path=(
                Path(args.reference_stats) if args.reference_stats else None
            ),
            rho=float(args.rho),
            c=float(args.c),
            eta=float(args.eta),
            device_arg=str(args.device),
            image_target_size=int(args.image_target_size),
            fid_batch_size=int(args.fid_batch_size),
            feature_dim=int(args.feature_dim),
            monte_carlo_n=int(args.monte_carlo_n),
            seed=int(args.seed),
            tolerance=float(args.tolerance),
            output=Path(args.output),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] per_round FID failed: {exc!r}", file=sys.stderr)
        return 1

    n_rounds = int(report["n_rounds"])
    monotone = bool(report["convergence"]["monotone"])
    o_eps_holds = bool(report["convergence"]["O_eps_holds"])
    regime_violations = list(report["convergence"]["regime_violations"])
    print(
        f"[DONE] n_rounds={n_rounds} monotone={monotone} "
        f"O_eps_holds={o_eps_holds} regime_violations={len(regime_violations)} "
        f"-> {args.output}"
    )
    return 0


__all__: list[str] = [
    "run_image_fid_per_round",
    "main",
]


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")  # noqa: F821
    sys.exit(main(sys.argv[1:]))