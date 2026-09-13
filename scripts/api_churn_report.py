"""Per-wave public-symbol churn report (framework-internal-metrics rev 3 J.1).

Computes the per-wave API stability rate
``1 - (added + removed public symbols in adaptive_reflow/) /
total public symbols`` over a configurable rolling window of git
commits, and emits both a human-readable summary and a
machine-checkable JSON artifact.

Why this exists (rev 3 §2 Group J rationale)
--------------------------------------------
Per ``framework-internal-metrics-rev3-plan.md`` §2 (J.1): saturated
audit metrics incentivise frozen APIs. Surfacing churn makes the
cost of refactors explicit, so a wave that quietly renames a dozen
public functions shows up in a per-wave report instead of as a
surprise downstream breakage. The companion metric J.2
(``docs/DEPRECATION.md``) is enforced by a separate static check on
deprecation-table entries carrying ``sunset_date:``.

Public-surface definition
-------------------------
A symbol is "public" iff it appears in one of:

1. ``adaptive_reflow/<pkg>/__init__.py`` ``__all__`` (re-exports).
2. A non-underscore-prefixed top-level ``def`` or ``class`` in any
   ``adaptive_reflow/`` ``.py`` file that is NOT under
   ``adaptive_reflow/legacy/`` (the quarantine directory; per
   ``pyproject.toml`` it is excluded from the wheel and is therefore
   not a public surface).
3. A ``Protocol`` declaration under ``adaptive_reflow/framework/``
   (the typed-contracts surface; explicitly part of J.1 even when
   the class name is CamelCase-suffixed with ``Protocol``).

Two symbols are "the same" iff they share an identical ``qualified
name`` (``module.name``) across two snapshots. A symbol that
changes ONLY its signature (same name, same module, different
parameters) is NOT counted as churn -- the metric rewards adding
or removing names, not internal evolution. This matches the
semver-style definition rev 3 adopts.

Usage
-----
::

    # Default: scan the last 4 waves (configurable) from current HEAD
    python scripts/api_churn_report.py report

    # Pin a window explicitly (start_commit end_commit)
    python scripts/api_churn_report.py report --since <sha> --until <sha>

    # JSON output (machine-checkable)
    python scripts/api_churn_report.py report --json \
        --output verification_outputs/api_churn_w24.json

    # Single-shot (one wave's delta vs the previous wave's HEAD)
    python scripts/api_churn_report.py report --window-size 1

Args
----
report                 sub-command (required for now; future: ``verify``
                       will compare against the committed JSON).
--since <sha>          start commit (inclusive). Default: derived from
                       ``--window-size``.
--until <sha>          end commit (inclusive). Default: HEAD.
--window-size <N>      number of commits back to span when --since is
                       not given. Default: 4 (per rev 3 §2 J.1 "last 4
                       waves"; a wave is taken to be one commit for the
                       purposes of this report).
--root <path>          repository root. Default: ``<script>/..``.
--json                 emit JSON to stdout (or to ``--output`` if given).
--output <path>        write the JSON artifact to <path>. Required if
                       ``--json`` is passed and the caller wants the
                       artifact captured for ``tools/check_api_churn.py``
                       downstream.

Output schema (JSON)
--------------------
::

    {
      "schema_version": "1.0",
      "since": "<sha>",
      "until": "<sha>",
      "window_size_commits": 4,
      "added":     ["adaptive_reflow.foo.bar", ...],
      "removed":   ["adaptive_reflow.baz.qux", ...],
      "unchanged_count": 42,
      "added_count": 3,
      "removed_count": 2,
      "total_at_until": 44,
      "total_at_since": 43,
      "churn_rate": 0.045,        # (added + removed) / max(total_at_since, total_at_until)
      "stability_rate": 0.955,    # 1 - churn_rate
      "passes_j1_gate": true      # stability_rate >= 0.95 (rev 3 §2 J.1 target)
    }

Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# Allow direct execution from a source checkout without requiring
# ``pip install -e .`` first; this script imports the local host fingerprint
# helper for reproducibility metadata.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.util.host_fingerprint import with_host_fingerprint

SCHEMA_VERSION = "1.0"
# rev 3 §2 J.1 target: stability_rate >= 0.95 (≤ 5% churn).
J1_GATE_THRESHOLD = 0.95
# rev 3 §2 J.1: "computed per wave over the last 4 waves"
DEFAULT_WINDOW_SIZE = 4
# Quarantine dir excluded from public surface (pyproject.toml wheel).
LEGACY_DIR = "adaptive_reflow/legacy/"


# ---------------------------------------------------------------------------
# Public-symbol extraction (source-side; runs against a checked-out tree).
# ---------------------------------------------------------------------------


def _list_py_files(root: Path, at_sha: str) -> list[Path]:
    """List all ``adaptive_reflow/**/*.py`` files at the given git SHA.

    Excludes the quarantine ``adaptive_reflow/legacy/`` directory and
    any ``__pycache__/`` entries.
    """
    out = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", at_sha,
         "--", "adaptive_reflow/"],
        text=True,
    )
    paths: list[Path] = []
    for line in out.splitlines():
        if not line.endswith(".py"):
            continue
        if line.startswith(LEGACY_DIR):
            continue
        if "__pycache__/" in line:
            continue
        paths.append(Path(line))
    return paths


# Heuristic regexes for symbol extraction; deliberately simple to
# avoid an AST dependency (this script is stdlib-only). False positives
# are bounded: a name must appear at column-0 (top-level) and not be
# indented, AND must not be prefixed with underscore.
_DEF_RE = re.compile(r"^def ([a-zA-Z][a-zA-Z0-9_]*)\(")
_CLASS_RE = re.compile(r"^class ([a-zA-Z][a-zA-Z0-9_]*)")
_ALL_RE = re.compile(r"^__all__\s*=\s*\[(.*?)\]", re.DOTALL)
_STR_RE = re.compile(r"'([^']+)'|\"([^\"]+)\"")


def _extract_symbols(root: Path, at_sha: str) -> dict[str, str]:
    """Return ``{qualified_name: kind}`` for the public surface at ``at_sha``.

    Qualified name format: ``adaptive_reflow.<module path>.<symbol>``
    where the module path omits the leading ``adaptive_reflow/`` and
    the trailing ``.py``. Re-exports via ``__all__`` are recorded with
    their canonical import path; class / def symbols are recorded
    under their defining module.

    Examples:
      ``adaptive_reflow/theory/__init__.py`` with ``__all__ = ["Foo"]``
      yields ``{"adaptive_reflow.theory.Foo": "reexport"}``.

      ``adaptive_reflow/theory/checkers.py`` with ``def bar(...)`` yields
      ``{"adaptive_reflow.theory.checkers.bar": "def"}``.
    """
    out: dict[str, str] = {}
    for rel in _list_py_files(root, at_sha):
        blob = subprocess.check_output(
            ["git", "-C", str(root), "show", f"{at_sha}:{rel.as_posix()}"],
            text=True,
        )
        module_path = rel.with_suffix("").as_posix().replace("/", ".")
        # __all__ re-exports (highest priority; declared at the column-0
        # of __init__.py files in this codebase).
        if rel.name == "__init__.py":
            m = _ALL_RE.search(blob)
            if m is not None:
                inner = m.group(1)
                for sym in _STR_RE.findall(inner):
                    name = sym[0] or sym[1]
                    if name and not name.startswith("_"):
                        out[f"{module_path}.{name}"] = "reexport"
        # Top-level def / class (skip private names).
        for line in blob.splitlines():
            stripped = line.lstrip()
            if stripped != line:
                # Indented -> not top-level.
                continue
            md = _DEF_RE.match(line)
            if md is not None:
                name = md.group(1)
                if not name.startswith("_"):
                    out[f"{module_path}.{name}"] = "def"
                continue
            mc = _CLASS_RE.match(line)
            if mc is not None:
                name = mc.group(1)
                if not name.startswith("_"):
                    out[f"{module_path}.{name}"] = "class"
    return out


# ---------------------------------------------------------------------------
# Git window selection.
# ---------------------------------------------------------------------------


def _resolve_sha(root: Path, ref: str) -> str:
    """Resolve ``ref`` (HEAD, branch name, SHA prefix) to a full SHA."""
    out = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--verify", ref],
        text=True,
    ).strip()
    return out


def _nth_commit_back(root: Path, sha: str, n: int) -> str:
    """Return the SHA ``n`` commits before ``sha`` (inclusive of ``sha``).

    If the repo has fewer than ``n`` commits in the ancestry, returns
    the root commit's SHA. The ``--ancestry-path`` flag is intentionally
    NOT used so merges off the main branch don't truncate the window.
    """
    out = subprocess.check_output(
        ["git", "-C", str(root), "rev-list", f"--max-count={n}", sha],
        text=True,
    )
    shas = out.split()
    if not shas:
        # Defensive: ``sha`` is its own root.
        return sha
    # rev-list returns newest first; the n-th entry from the end is
    # ``n`` commits back from ``sha`` (inclusive of ``sha`` itself).
    return shas[-1]


# ---------------------------------------------------------------------------
# Churn computation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChurnReport:
    """Computed API-churn report (rev 3 J.1 metric)."""

    since_sha: str
    until_sha: str
    window_size_commits: int
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged_count: int
    total_at_since: int
    total_at_until: int

    @property
    def added_count(self) -> int:
        return len(self.added)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def churn_rate(self) -> float:
        denom = max(self.total_at_since, self.total_at_until, 1)
        return (self.added_count + self.removed_count) / denom

    @property
    def stability_rate(self) -> float:
        return 1.0 - self.churn_rate

    @property
    def passes_j1_gate(self) -> bool:
        return self.stability_rate >= J1_GATE_THRESHOLD


def _diff_symbols(
    before: dict[str, str], after: dict[str, str]
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    """Return ``(added, removed, unchanged_count)`` for two snapshots."""
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    added = tuple(sorted(after_keys - before_keys))
    removed = tuple(sorted(before_keys - after_keys))
    unchanged = len(before_keys & after_keys)
    return added, removed, unchanged


def compute_churn(
    root: Path,
    since_sha: str,
    until_sha: str,
    *,
    window_size_commits: int | None = None,
) -> ChurnReport:
    """Compute the API churn between ``since_sha`` and ``until_sha``.

    ``since_sha`` and ``until_sha`` must both be reachable in the
    current git history; the function does NOT verify ancestry (so a
    branch-divergent pair will still produce a valid diff).
    """
    before = _extract_symbols(root, since_sha)
    after = _extract_symbols(root, until_sha)
    added, removed, unchanged = _diff_symbols(before, after)
    return ChurnReport(
        since_sha=since_sha,
        until_sha=until_sha,
        window_size_commits=window_size_commits or DEFAULT_WINDOW_SIZE,
        added=added,
        removed=removed,
        unchanged_count=unchanged,
        total_at_since=len(before),
        total_at_until=len(after),
    )


# ---------------------------------------------------------------------------
# Output formatting.
# ---------------------------------------------------------------------------


def _format_text(report: ChurnReport) -> str:
    """Human-readable single-page summary."""
    lines: list[str] = []
    lines.append("API Churn Report (rev 3 J.1)")
    lines.append("=" * 60)
    lines.append(f"Since SHA: {report.since_sha}")
    lines.append(f"Until SHA: {report.until_sha}")
    lines.append(
        f"Window:   {report.window_size_commits} commits "
        f"({report.since_sha[:8]}..{report.until_sha[:8]})"
    )
    lines.append("")
    lines.append(
        f"Public surface: {report.total_at_since} -> {report.total_at_until} "
        f"({report.total_at_until - report.total_at_since:+d})"
    )
    lines.append(f"Added symbols:    {report.added_count}")
    lines.append(f"Removed symbols:  {report.removed_count}")
    lines.append(f"Unchanged:        {report.unchanged_count}")
    lines.append("")
    lines.append(f"Churn rate:       {report.churn_rate:.3f}")
    lines.append(f"Stability rate:   {report.stability_rate:.3f}")
    lines.append(
        f"J.1 gate (>= {J1_GATE_THRESHOLD:.2f}): "
        f"{'PASS' if report.passes_j1_gate else 'FAIL'}"
    )
    if report.added:
        lines.append("")
        lines.append("Added:")
        for name in report.added:
            lines.append(f"  + {name}")
    if report.removed:
        lines.append("")
        lines.append("Removed:")
        for name in report.removed:
            lines.append(f"  - {name}")
    return "\n".join(lines)


def _to_json_dict(report: ChurnReport) -> dict[str, object]:
    """Convert ``ChurnReport`` to a JSON-friendly dict (rev 3 J.1 schema)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "since": report.since_sha,
        "until": report.until_sha,
        "window_size_commits": report.window_size_commits,
        "added": list(report.added),
        "removed": list(report.removed),
        "unchanged_count": report.unchanged_count,
        "added_count": report.added_count,
        "removed_count": report.removed_count,
        "total_at_since": report.total_at_since,
        "total_at_until": report.total_at_until,
        "churn_rate": round(report.churn_rate, 6),
        "stability_rate": round(report.stability_rate, 6),
        "j1_gate_threshold": J1_GATE_THRESHOLD,
        "passes_j1_gate": report.passes_j1_gate,
    }


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api_churn_report.py",
        description=(
            "Per-wave public-symbol churn report "
            "(framework-internal-metrics rev 3 §2 J.1)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_report = sub.add_parser(
        "report",
        help="Compute the API churn over a git window.",
    )
    p_report.add_argument(
        "--since", type=str, default=None,
        help="Start commit SHA (inclusive). Default: derived from --window-size.",
    )
    p_report.add_argument(
        "--until", type=str, default="HEAD",
        help="End commit SHA (inclusive). Default: HEAD.",
    )
    p_report.add_argument(
        "--window-size", type=int, default=DEFAULT_WINDOW_SIZE,
        help=(
            "Number of commits back to span when --since is not given. "
            f"Default: {DEFAULT_WINDOW_SIZE}."
        ),
    )
    p_report.add_argument(
        "--root", type=Path, default=None,
        help="Repository root. Default: parent of this script's directory.",
    )
    p_report.add_argument(
        "--json", action="store_true",
        help="Emit JSON to stdout (or to --output).",
    )
    p_report.add_argument(
        "--output", type=Path, default=None,
        help="Write the JSON artifact to <path>.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.command != "report":
        parser.error(f"unknown command: {args.command!r}")
    root = args.root or Path(__file__).resolve().parent.parent
    if not (root / ".git").exists():
        print(f"error: {root} is not a git repository", file=sys.stderr)
        return 2
    until_sha = _resolve_sha(root, args.until)
    if args.since is not None:
        since_sha = _resolve_sha(root, args.since)
    else:
        since_sha = _nth_commit_back(root, until_sha, args.window_size)
    report = compute_churn(
        root, since_sha, until_sha,
        window_size_commits=args.window_size,
    )
    if args.json:
        payload = with_host_fingerprint(_to_json_dict(report))
        text = json.dumps(payload, indent=2, sort_keys=True)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n")
        print(text)
    else:
        print(_format_text(report))
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    with_host_fingerprint(_to_json_dict(report)),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
    return 0 if report.passes_j1_gate else 1


if __name__ == "__main__":
    sys.exit(main())
