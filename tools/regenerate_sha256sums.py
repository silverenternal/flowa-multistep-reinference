#!/usr/bin/env python3
"""CLI: (re)build ``SHA256SUMS`` ledgers under ``verification_outputs/``.

This script is the **only allowed writer** of the per-subdir SHA256SUMS
files. It enforces two safety policies:

1. **Subdirs without a ledger**: a fresh ledger is generated.
2. **Subdirs with a stale ledger**: the script DOES NOT auto-overwrite
   the existing ledger. It logs a warning listing every file whose
   on-disk sha256 differs from the ledger, and exits with a non-zero
   code so a human operator must explicitly delete the stale ledger
   and re-run with ``--force`` to regenerate.

This split is deliberate: a ``verification_outputs/<sub>/`` whose
artifacts were silently swapped (e.g. a partial rerun that overwrote
``seed42/summary.json`` but left the ledger untouched) is a *data
integrity incident* and must not be auto-fixed. The script treats any
drift between an existing ledger and disk as a stop-the-line event;
``--force`` is the only escape hatch.

Usage::

    # Print a summary of which subdirs are missing / stale / clean.
    PYTHONPATH=. python tools/regenerate_sha256sums.py --dry-run

    # Generate SHA256SUMS for every subdir that does not yet have one.
    PYTHONPATH=. python tools/regenerate_sha256sums.py

    # Force-regenerate a specific subdir's ledger after a known-good
    # artifact replacement (e.g. after rerunning an experiment).
    PYTHONPATH=. python tools/regenerate_sha256sums.py \
        --subdir verification_outputs/wave280-p-r1 --force
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

VERIF_ROOT: Path = REPO_ROOT / "verification_outputs"
"""Artifact root. The script walks this tree one level deep."""


# ---------------------------------------------------------------------------
# Subdir state model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubdirState:
    """Per-subdir state observed by the walker."""

    rel_path: str
    has_ledger: bool
    is_clean: bool  # True if ledger is present and matches disk
    n_files: int  # number of files tracked by the ledger (excluding self)
    n_drifts: int  # number of mismatches ledger-vs-disk


@dataclass(frozen=True)
class RegenerationReport:
    """Aggregate report across all subdirs."""

    states: tuple[SubdirState, ...] = field(default_factory=tuple)
    generated: tuple[str, ...] = field(default_factory=tuple)
    stale: tuple[str, ...] = field(default_factory=tuple)
    forced: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_of(path: Path) -> str:
    """Lowercase hex sha256 of ``path``, streaming in 64 KiB chunks."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _parse_ledger(ledger: Path) -> dict[str, str]:
    """Return ``{relative_path: sha256}`` from ``ledger``. Self-references
    to ``./SHA256SUMS`` are skipped (the ledger's own hash is appended
    in :func:`_emit_ledger` so we don't try to hash the ledger while
    we're writing it).
    """
    if not ledger.is_file():
        return {}
    out: dict[str, str] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(maxsplit=1) if "  " not in s else s.split("  ", 1)
        if len(parts) != 2:
            continue
        sha, rel = parts[0].strip().lower(), parts[1].strip()
        if rel == "./SHA256SUMS":
            continue
        if len(sha) != 64:
            continue
        out[rel] = sha
    return out


def _observe_subdir(subdir: Path) -> SubdirState:
    """Compute the (has_ledger, is_clean, n_files, n_drifts) tuple for
    ``subdir`` without mutating anything on disk.
    """
    ledger = subdir / "SHA256SUMS"
    rel = str(subdir.relative_to(REPO_ROOT))
    if not ledger.is_file():
        # No ledger: count the on-disk files for transparency.
        n_files = sum(1 for p in subdir.rglob("*") if p.is_file())
        return SubdirState(
            rel_path=rel,
            has_ledger=False,
            is_clean=False,
            n_files=n_files,
            n_drifts=0,
        )
    entries = _parse_ledger(ledger)
    drifts = 0
    for rel_path, sha_expected in entries.items():
        target = subdir / rel_path.lstrip("./")
        if not target.is_file():
            drifts += 1
            continue
        if _sha256_of(target) != sha_expected:
            drifts += 1
    return SubdirState(
        rel_path=rel,
        has_ledger=True,
        is_clean=(drifts == 0),
        n_files=len(entries),
        n_drifts=drifts,
    )


def _emit_ledger(subdir: Path) -> Path:
    """Write a fresh ``SHA256SUMS`` for ``subdir``.

    The format matches the convention used by ``wave280-p-r1`` etc.:
    one entry per line ``<sha256>  ./<relative_path>``, sorted by
    relative path for determinism. The ledger's own self-hash is
    appended at the end (matching the existing wave280 ledgers).
    Returns the path of the written ledger.
    """
    entries: list[tuple[str, str]] = []
    for p in sorted(subdir.rglob("*")):
        if not p.is_file():
            continue
        if p.name == "SHA256SUMS":
            continue
        rel = p.relative_to(subdir).as_posix()
        entries.append((_sha256_of(p), f"./{rel}"))
    # Placeholder self-hash -- filled in after the ledger is written.
    entries.append(("0" * 64, "./SHA256SUMS"))
    lines = [f"{sha}  {rel}" for sha, rel in entries]
    ledger = subdir / "SHA256SUMS"
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Patch in the real self-hash (overwrite the placeholder line).
    self_sha = _sha256_of(ledger)
    text = ledger.read_text(encoding="utf-8")
    text = text.replace("0" * 64 + "  ./SHA256SUMS", f"{self_sha}  ./SHA256SUMS")
    ledger.write_text(text, encoding="utf-8")
    return ledger


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "(Re)generate SHA256SUMS ledgers under "
            "verification_outputs/. Stale ledgers are NOT auto-overwritten."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report per-subdir state without writing anything.",
    )
    parser.add_argument(
        "--subdir",
        type=Path,
        default=None,
        help=(
            "Restrict the operation to a single subdir "
            "(default: every subdir of verification_outputs/)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Regenerate even subdirs whose existing ledger disagrees "
            "with the on-disk state. Use only after a known-good "
            "artifact replacement."
        ),
    )
    parser.add_argument(
        "--verif-root",
        type=Path,
        default=VERIF_ROOT,
        help=(
            "verification_outputs/ root (default: <repo>/verification_outputs). "
            "Test-only override."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    root: Path = args.verif_root
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    targets: list[Path]
    if args.subdir is not None:
        targets = [args.subdir]
    else:
        targets = sorted(p for p in root.iterdir() if p.is_dir())

    states: list[SubdirState] = []
    generated: list[str] = []
    stale: list[str] = []
    forced: list[str] = []

    for subdir in targets:
        state = _observe_subdir(subdir)
        states.append(state)
        if args.dry_run:
            continue
        if not state.has_ledger:
            _emit_ledger(subdir)
            generated.append(state.rel_path)
        elif not state.is_clean:
            stale.append(state.rel_path)
            if args.force:
                _emit_ledger(subdir)
                forced.append(state.rel_path)

    # Report.
    print(f"# SHA256SUMS regeneration report (root={root})")
    print()
    print(f"- Subdirs observed: {len(states)}")
    print(f"- Ledgers already clean: "
          f"{sum(1 for s in states if s.has_ledger and s.is_clean)}")
    if not args.dry_run:
        print(f"- Ledgers generated: {len(generated)}")
        print(f"- Stale ledgers (NOT auto-overwritten): {len(stale)}")
        if args.force:
            print(f"- Ledgers force-regenerated: {len(forced)}")
    print()
    for state in states:
        flag = (
            "CLEAN"
            if state.has_ledger and state.is_clean
            else "MISSING" if not state.has_ledger else "STALE"
        )
        print(
            f"  [{flag:>7}] {state.rel_path:<60s} "
            f"files={state.n_files:<5d} drifts={state.n_drifts}"
        )

    if stale and not args.force:
        print()
        print(
            "Stale ledgers require operator confirmation. Re-run with "
            "--subdir <path> --force after a known-good artifact "
            "replacement.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())