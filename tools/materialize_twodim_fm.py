"""Materialize ``data/twodim_fm_*.npz`` weights if missing (DTB-G3 phase 1).

The :class:`TwoDimFMAdapter` runtime loads a small velocity-field
``.npz`` weight file from ``data/twodim_fm_<target>.npz``. Tests in
:mod:`tests.test_adapters.test_twodim_fm` rely on the canonical file
existing at session start. This module exposes:

* :func:`materialize_if_missing` — pure helper, idempotent, returns
  ``True`` when a file was created and ``False`` when the canonical
  file already existed.
* :func:`main` — CLI entry point; ``python -m tools.materialize_twodim_fm``
  materializes both canonical files with a fast training run
  (``--steps 500``).
* :func:`ensure_canonical_files` — convenience for the test-side
  ``conftest.py`` hook.

The materializer trains a fresh velocity-field MLP from scratch using
the canonical trainer (:mod:`adaptive_reflow.adapters.twodim_fm_train`)
with a deliberately small step budget so the helper is fast enough to
run at pytest collection. The weights produced are functional but
unrefined; tests that need a "well-trained" model use the canonical
``data/twodim_fm_two_moons.npz`` that the offline trainer produces
(``python -m adaptive_reflow.adapters.twodim_fm_train --target two_moons
--steps 2000 --out data/twodim_fm_two_moons.npz``).

Stdlib + numpy only (numpy is already an opt-in extra for the adapter
package, gated behind ``[flow_matching]``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from adaptive_reflow.adapters.twodim_fm_train import (
    TARGETS,
    save_weights,
    train,
)

# Canonical files (paths the runtime adapter resolves against).
CANONICAL_TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
DEFAULT_STEPS: int = 500
DEFAULT_BATCH_SIZE: int = 1024
DEFAULT_LR: float = 1e-3
DEFAULT_HIDDEN: int = 64
DEFAULT_SEED: int = 42

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR: Path = REPO_ROOT / "data"


def canonical_path(target: str, *, out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    """Return the canonical ``.npz`` path for ``target`` under ``out_dir``."""
    if target not in CANONICAL_TARGETS:
        raise ValueError(f"unknown_target:{target}")
    return out_dir / f"twodim_fm_{target}.npz"


def materialize_if_missing(
    target: str,
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    steps: int = DEFAULT_STEPS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lr: float = DEFAULT_LR,
    hidden: int = DEFAULT_HIDDEN,
    seed: int = DEFAULT_SEED,
    force: bool = False,
) -> bool:
    """Train and save the canonical ``.npz`` for ``target`` if it is missing.

    Parameters
    ----------
    target:
        ``"two_moons"`` or ``"eight_gaussians"``.
    out_dir:
        Directory into which ``twodim_fm_<target>.npz`` is written.
    steps:
        Number of optimizer steps for the materialization training run.
        Default ``500`` is small enough to materialise during a pytest
        collection without exceeding the 60-second CPU budget the
        engine-stress tests rely on.
    batch_size, lr, hidden, seed:
        Forwarded to :func:`adaptive_reflow.adapters.twodim_fm_train.train`.
    force:
        When ``True``, retrain even if the canonical file already exists.

    Returns
    -------
    bool
        ``True`` if the file was created (or overwritten) by this call;
        ``False`` if it already existed and ``force=False``.
    """
    if target not in CANONICAL_TARGETS:
        raise ValueError(f"unknown_target:{target}")
    out_path = canonical_path(target, out_dir=out_dir)
    if out_path.exists() and not force:
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    weights = train(
        target=target,
        steps=int(steps),
        batch_size=int(batch_size),
        lr=float(lr),
        hidden=int(hidden),
        seed=int(seed),
    )
    save_weights(weights, out_path)
    return True


def ensure_canonical_files(
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    steps: int = DEFAULT_STEPS,
    force: bool = False,
) -> dict[str, bool]:
    """Materialise every canonical ``.npz`` file if missing.

    Returns a mapping ``{target: created}`` so the caller (typically a
    ``conftest.py`` hook) can log which files were created.
    """
    out_dir = Path(out_dir)
    return {
        target: materialize_if_missing(
            target,
            out_dir=out_dir,
            steps=int(steps),
            force=bool(force),
        )
        for target in CANONICAL_TARGETS
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: materialise every canonical ``.npz`` with a fast training run."""
    parser = argparse.ArgumentParser(
        prog="materialize_twodim_fm",
        description=(
            "Materialise data/twodim_fm_<target>.npz for the runtime adapter."
        ),
    )
    parser.add_argument(
        "--target",
        choices=list(CANONICAL_TARGETS) + ["all"],
        default="all",
    )
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Retrain even if the canonical .npz already exists.",
    )
    args = parser.parse_args(argv)

    targets: tuple[str, ...] = (
        CANONICAL_TARGETS if args.target == "all" else (args.target,)
    )

    created_any = False
    for target in targets:
        created = materialize_if_missing(
            target,
            out_dir=args.out_dir,
            steps=args.steps,
            batch_size=args.batch_size,
            lr=args.lr,
            hidden=args.hidden,
            seed=args.seed,
            force=args.force,
        )
        path = canonical_path(target, out_dir=args.out_dir)
        status = "created" if created else "exists"
        # ``np`` is imported but only used here as a sanity check (the
        # trainer uses numpy internally; we assert the file is readable).
        with np.load(path) as data:
            keys = tuple(sorted(data.files))
        print(
            f"[{target}] {status} {path} "
            f"({path.stat().st_size} bytes; keys={keys})",
            flush=True,
        )
        created_any = created_any or created
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())


__all__ = [
    "CANONICAL_TARGETS",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_HIDDEN",
    "DEFAULT_LR",
    "DEFAULT_OUT_DIR",
    "DEFAULT_SEED",
    "DEFAULT_STEPS",
    "canonical_path",
    "ensure_canonical_files",
    "main",
    "materialize_if_missing",
]

# Quiet unused-import linter about TARGETS (kept for symmetry with the
# trainer's public surface so callers can re-export the vocabulary).
_ = TARGETS
