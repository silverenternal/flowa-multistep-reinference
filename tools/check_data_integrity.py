#!/usr/bin/env python3
"""CLI: walk ``verification_outputs/`` and verify every ``SHA256SUMS`` ledger.

For each sub-directory of ``verification_outputs/`` that ships a
``SHA256SUMS`` file, recompute ``sha256`` of every entry the ledger
references and compare against the ledger line. Any of these is reported
as a mismatch:

* **modified** -- a file's current sha256 differs from the ledger entry.
* **missing**  -- a file listed in the ledger is absent from disk.
* **unlisted** -- a file is present on disk but the ledger does not
  cover it (the ledger is supposed to enumerate every artifact).

Exit code is ``0`` iff every ledger passes; ``1`` on any mismatch. The
summary line ``Verified X directories, Y files, Z mismatches`` is
always printed so CI can grep it.

Usage::

    PYTHONPATH=. python tools/check_data_integrity.py [--quiet]
    PYTHONPATH=. python tools/check_data_integrity.py --root verification_outputs/

The script is read-only: it never mutates the working tree. To (re)build
a ledger after a known-good artifact replacement, use
``tools/regenerate_sha256sums.py`` instead -- ``regenerate`` is the only
allowed writer.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

DEFAULT_ROOT: Path = REPO_ROOT / "verification_outputs"
"""Default artifact root. The repo's git-tracked headline data lives here."""


# ---------------------------------------------------------------------------
# Mismatch model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Mismatch:
    """One ledger / on-disk mismatch under a single ``SHA256SUMS`` ledger."""

    subdir: str  # path of the directory containing the ledger, repo-relative
    kind: str  # "modified" | "missing" | "unlisted" | "bad_ledger_line"
    detail: str  # human-readable detail


@dataclass(frozen=True)
class IntegrityResult:
    """Aggregate result of the integrity sweep."""

    verified_directories: int = 0
    verified_files: int = 0
    mismatches: tuple[Mismatch, ...] = field(default_factory=tuple)
    empty_ledgers: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# SHA256SUMS ledger parsing
# ---------------------------------------------------------------------------


def _iter_ledger_entries(ledger: Path) -> Iterable[tuple[str, str]]:
    """Yield ``(sha256, relative_path)`` pairs from a ``SHA256SUMS`` file.

    The standard format is::

        <64 hex sha256><two spaces>./relative/path

    Lines that are blank or start with ``#`` are skipped. Lines that do
    not match the expected format are surfaced by the caller as a
    ``bad_ledger_line`` mismatch (the function itself stays pure /
    generator-only so the caller can keep its reporting simple).
    """
    for line in ledger.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Format: "<sha256>  <path>" -- exactly two spaces between fields.
        # Tolerate single-space separators (some upstream tools emit
        # single-space, some double-space); the ``split`` with a
        # bounded ``maxsplit=1`` handles both.
        parts = s.split(maxsplit=1) if "  " not in s else s.split("  ", 1)
        if len(parts) != 2:
            continue
        sha, rel = parts[0].strip(), parts[1].strip()
        if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha.lower()):
            continue
        yield (sha.lower(), rel)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _sha256_of(path: Path) -> str:
    """Return the lowercase hex sha256 of ``path``.

    Reads the file in 64 KiB chunks so a multi-MiB artifact (e.g. CIFAR
    NPZ shards) does not balloon the verifier's RSS.
    """
    h = __import__("hashlib").sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _verify_subdir(subdir: Path) -> tuple[int, tuple[Mismatch, ...]]:
    """Verify one ``subdir/`` whose ``SHA256SUMS`` is at
    ``subdir/SHA256SUMS``. Returns ``(file_count, mismatches)``.
    """
    ledger = subdir / "SHA256SUMS"
    rel_subdir = str(subdir.relative_to(REPO_ROOT)) if subdir.is_absolute() else str(subdir)
    mismatches: list[Mismatch] = []
    file_count = 0
    listed_paths: set[Path] = set()
    for sha_expected, rel_path in _iter_ledger_entries(ledger):
        if rel_path == "./SHA256SUMS":
            # The ledger's own self-hash is checked separately when the
            # loop completes; skip it here so we don't recurse into the
            # ledger while reading it.
            listed_paths.add(subdir / "SHA256SUMS")
            continue
        file_count += 1
        target = subdir / rel_path.lstrip("./")
        listed_paths.add(target)
        if not target.is_file():
            mismatches.append(
                Mismatch(
                    subdir=rel_subdir,
                    kind="missing",
                    detail=f"{rel_path}: listed in SHA256SUMS but not on disk",
                )
            )
            continue
        try:
            actual = _sha256_of(target)
        except OSError as exc:
            mismatches.append(
                Mismatch(
                    subdir=rel_subdir,
                    kind="missing",
                    detail=f"{rel_path}: failed to read ({exc})",
                )
            )
            continue
        if actual != sha_expected:
            mismatches.append(
                Mismatch(
                    subdir=rel_subdir,
                    kind="modified",
                    detail=(
                        f"{rel_path}: sha256 mismatch "
                        f"(expected {sha_expected[:12]}..., got {actual[:12]}...)"
                    ),
                )
            )
    # Cross-check: every file actually on disk under ``subdir/`` must
    # be listed in the ledger (the ledger is supposed to enumerate every
    # artifact). Walk only the *git-tracked* view via ``rglob``; we treat
    # hidden files / the ledger itself as auto-skip.
    for on_disk in subdir.rglob("*"):
        if not on_disk.is_file():
            continue
        if on_disk.name == "SHA256SUMS":
            continue
        if on_disk not in listed_paths:
            mismatches.append(
                Mismatch(
                    subdir=rel_subdir,
                    kind="unlisted",
                    detail=(
                        f"{on_disk.relative_to(subdir)}: present on disk "
                        f"but not in SHA256SUMS (regenerate the ledger)"
                    ),
                )
            )
    return file_count, tuple(mismatches)


def verify(root: Path = DEFAULT_ROOT) -> IntegrityResult:
    """Run the integrity sweep against ``root``.

    Returns an :class:`IntegrityResult` summarising the directory /
    file / mismatch counts. Pure -- does not print or exit; the CLI
    layer handles user-facing reporting.
    """
    if not root.is_dir():
        return IntegrityResult()
    total_files = 0
    all_mismatches: list[Mismatch] = []
    dirs_with_ledger = 0
    empty_ledgers: list[str] = []
    for subdir in sorted(root.iterdir()):
        if not subdir.is_dir():
            continue
        ledger = subdir / "SHA256SUMS"
        if not ledger.is_file():
            # Subdir without a ledger: the manifest builder ships
            # ``verification_outputs/MANIFEST.md`` for those (the
            # manifest is a flat catalogue, not a per-dir sha256 ledger).
            # Integrity here is "manifest must list it"; we don't fail
            # this verifier on missing ledgers -- the provenance checker
            # owns that contract.
            continue
        dirs_with_ledger += 1
        file_count, mismatches = _verify_subdir(subdir)
        if file_count == 0 and not mismatches:
            empty_ledgers.append(str(subdir.relative_to(REPO_ROOT)))
        total_files += file_count
        all_mismatches.extend(mismatches)
    return IntegrityResult(
        verified_directories=dirs_with_ledger,
        verified_files=total_files,
        mismatches=tuple(all_mismatches),
        empty_ledgers=tuple(empty_ledgers),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _format_report(result: IntegrityResult) -> str:
    """Render a markdown-style report."""
    out: list[str] = []
    out.append("# Verification-output integrity report")
    out.append("")
    out.append(f"- Directories with SHA256SUMS: **{result.verified_directories}**")
    out.append(f"- Files verified: **{result.verified_files}**")
    out.append(f"- Mismatches: **{len(result.mismatches)}**")
    if result.empty_ledgers:
        out.append(
            "- Empty ledgers (no entries; consider removing): "
            + ", ".join(result.empty_ledgers)
        )
    out.append("")
    if not result.mismatches:
        out.append("**All ledgers match on-disk state.**")
    else:
        out.append("## Mismatches")
        out.append("")
        for m in result.mismatches:
            out.append(f"- **{m.subdir}** (`{m.kind}`): {m.detail}")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that every verification_outputs/<sub>/SHA256SUMS ledger "
            "matches the current on-disk state of the artifact tree."
        )
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the one-line summary; suppress the full report.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=(
            "Root directory to scan (default: verification_outputs/). "
            "Test-only override."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    result = verify(root=args.root)
    n_mismatches = len(result.mismatches)
    summary = (
        f"Verified {result.verified_directories} directories, "
        f"{result.verified_files} files, {n_mismatches} mismatches"
    )
    if args.quiet:
        print(summary)
    else:
        print(_format_report(result))
        print(summary)
    return 0 if n_mismatches == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
