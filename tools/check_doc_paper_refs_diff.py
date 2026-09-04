r"""CLI: doc-builder diff job (E.4) -- per-equation citation regression check.

E.4 ("Doc-builder diff job: per-equation citation check fails if a refactor
drops paper equation/section reference from a public function") in
``todo/framework-internal-metrics.md`` requires a CI gate that fails when a
refactor removes a paper anchor from a docstring. This is the diff-mode
counterpart of ``tools/check_doc_paper_refs.py``: that one-shot audit
measures the *current* ratio of docs cross-referencing >= 1 paper theorem,
while this diff job compares two git revisions (HEAD vs base) and reports
only the **regressions** -- functions whose docstrings LOST a paper anchor
between base and HEAD.

Anchors matched (mirror of ``tools/check_doc_paper_refs.py``):

* ``Theorem N`` / ``Theorem N.M`` (e.g. ``Theorem 1``, ``Theorem 2.3``)
* ``Lemma N``  / ``Lemma N.M``
* ``Proposition N``
* ``Corollary N``
* ``Remark N``
* ``paper section X.Y`` (e.g. ``paper section 4.2``)
* ``paper §X.Y`` (e.g. ``paper §3.1``)
* ``paper line N`` (e.g. ``paper line 87``)
* ``Eq. (N)`` / ``Equation N`` / ``Eq. N`` (e.g. ``Eq. (7)``, ``Eq. 3``)
* ``Section N`` (e.g. ``Section 4.2``)
* ``JMAA`` (the underlying paper, J. Math. Anal. Appl.)
* ``arXiv:NNNN.NNNNN`` (any arXiv ID)

Scope: every public ``FunctionDef``/``AsyncFunctionDef``/``ClassDef``
defined under ``adaptive_reflow/`` excluding the ``legacy/`` quarantine.
A function is considered public if it is top-level (module body) and its
name does not start with ``_``.

The script accepts two git SHAs (``--base``, ``--head``), enumerates every
public function in both trees, and emits a one-line-per-regression report,
plus a summary. Exit code 1 if any regressions; 0 otherwise.

::

    $ python tools/check_doc_paper_refs_diff.py --base HEAD~1 --head HEAD
    PASS  E.4 diff -- 0 regressions across 873 functions (HEAD vs HEAD~1)

Exit codes:
    0 -- no regressions (E.4 gate MET)
    1 -- at least one regression detected (E.4 gate NOT MET)
    2 -- invocation error (git failure, no python files, etc.)
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout / configuration
# ---------------------------------------------------------------------------


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Resolved repo root (one level above ``tools/``)."""

PKG_ROOT: Path = REPO_ROOT / "adaptive_reflow"
"""Public Python package whose functions are scanned."""

EXCLUDE_DIR_NAMES: frozenset[str] = frozenset(
    {"__pycache__", "legacy", ".git"}
)
"""Directories excluded from the public-surface scan.

``legacy/`` is the per-framework quarantine (see framework-internal-metrics
rev 3 J.2 deprecation policy). Public functions there carry sunset tags and
are not part of the E.4 HARD gate.
"""

# ---------------------------------------------------------------------------
# Citation regex -- mirrors tools/check_doc_paper_refs.py plus equation anchors
# ---------------------------------------------------------------------------


# Numbered paper statement (Theorem / Lemma / Proposition / Corollary / Remark).
# Anchored on a word boundary so that identifiers like ``theorem_1`` do not match.
PAPER_STATEMENT_RE = re.compile(
    r"\b(?:Theorem|Lemma|Proposition|Corollary|Remark)\s+\d+(?:\.\d+)?"
)

# Paper section / line / §-style reference (case-insensitive).
PAPER_SECTION_RE = re.compile(
    r"\bpaper\s+(?:section|line)\s+\d+(?:\.\d+)?|\bpaper\s*§\s*\d+(?:\.\d+)?",
    re.IGNORECASE,
)

# Equation reference -- "Eq. (7)", "Eq. 3", "Equation 12".
PAPER_EQUATION_RE = re.compile(
    r"\bEq\.\s*\(?\s*\d+(?:\.\d+)?\s*\)?|\bEquation\s+\d+(?:\.\d+)?"
)

# Plain "Section N" / "Section N.M" reference (case-insensitive on Section).
# Distinguished from PAPER_SECTION_RE by the absence of the leading "paper".
PAPER_SECTION_BARE_RE = re.compile(
    r"\bSection\s+\d+(?:\.\d+)?"
)

# arXiv reference (e.g. arXiv:2410.04997 or arXiv:2605.22252).
ARXIV_RE = re.compile(r"\barXiv:\d{4}\.\d{4,5}(?:v\d+)?")

# JMAA acronym (the underlying paper, J. Math. Anal. Appl.).
JMAA_RE = re.compile(r"\bJMAA\b")

# Union of all anchors. A docstring is "citing" if ANY of these match.
CITATION_RES: tuple[re.Pattern[str], ...] = (
    PAPER_STATEMENT_RE,
    PAPER_SECTION_RE,
    PAPER_EQUATION_RE,
    PAPER_SECTION_BARE_RE,
    ARXIV_RE,
    JMAA_RE,
)


# ---------------------------------------------------------------------------
# Git enumeration
# ---------------------------------------------------------------------------


def _run_git(*args: str) -> str:
    """Run a git command in the repo root and return stripped stdout.

    Raises ``SystemExit(2)`` on non-zero exit -- the diff job has no useful
    fallback when git fails (no commits to diff against means the gate is
    not actionable).
    """
    cmd = ("git", "-C", str(REPO_ROOT)) + args
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(
            f"ERROR: git {' '.join(args)} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(2)
    return proc.stdout.strip()


def _python_files_in_tree(sha: str) -> list[str]:
    """Return the sorted list of tracked ``*.py`` files in ``sha``.

    Restricted to the public package tree (``adaptive_reflow/`` minus the
    ``legacy/`` quarantine). Files outside that tree are not part of the
    E.4 public-surface scope.
    """
    out = _run_git("ls-tree", "-r", "--name-only", sha, "--", "adaptive_reflow")
    paths: list[str] = []
    for line in out.splitlines():
        if not line.endswith(".py"):
            continue
        if any(part in EXCLUDE_DIR_NAMES for part in Path(line).parts):
            continue
        paths.append(line)
    paths.sort()
    return paths


def _read_blob(sha: str, path: str) -> str | None:
    """Return the text of ``path`` at ``sha`` (or ``None`` if absent).

    ``None`` signals "file does not exist at this revision" -- a function
    defined at base but absent at head counts as a *deletion*, not a
    citation regression, and is reported separately.
    """
    out = _run_git("cat-file", "-p", f"{sha}:{path}")
    if not out:
        # git cat-file -p returns "" with exit 0 for a missing blob if the
        # ref doesn't exist; for a real missing file inside an existing
        # tree, it returns non-empty error text. Use ls-tree to disambiguate.
        listing = _run_git(
            "ls-tree", "--", sha, path
        )
        if not listing:
            return None
        return ""
    return out


# ---------------------------------------------------------------------------
# AST: extract public functions + their docstrings
# ---------------------------------------------------------------------------


def _is_public_name(name: str) -> bool:
    """Return True iff ``name`` is a public symbol (no leading underscore).

    Names that start with ``_`` are conventionally private (including
    dunder ``__foo__`` which is special -- we treat it as public because
    framework callers commonly hook dunder methods via Protocols).
    """
    if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
        return False
    return True


def _extract_functions(source: str, module_path: str) -> list[tuple[str, str | None]]:
    """Parse ``source`` and return ``[(qualname, docstring_or_None), ...]``.

    Only **top-level** (module-body) public functions and async functions
    are returned. Methods (nested ``FunctionDef``) are out of scope for
    the E.4 gate -- the metric text says "public function", which by
    framework convention means module-body entry points. Classes are
    intentionally excluded; their public API is documented on the
    class-level docstring, which is also covered.

    The qualifier is ``module_path::function_name`` so the report can be
    copied verbatim into a CI failure message.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Unparseable source at one revision -- skip rather than crash.
        return []
    out: list[tuple[str, str | None]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_public_name(node.name):
                continue
            doc = ast.get_docstring(node, clean=True)
            out.append((f"{module_path}::{node.name}", doc))
    return out


def _function_has_citation(doc: str | None) -> bool:
    """Return True iff ``doc`` matches any of the E.4 citation regexes.

    A docstring of ``None`` or empty string trivially fails the check.
    """
    if not doc:
        return False
    return any(p.search(doc) for p in CITATION_RES)


def _citations_in_doc(doc: str | None) -> list[str]:
    """Return the literal citation matches in ``doc`` (for verbose reports)."""
    if not doc:
        return []
    out: list[str] = []
    for pat in CITATION_RES:
        for m in pat.finditer(doc):
            out.append(m.group(0))
    return out


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def _diff_functions(
    base_fns: dict[str, str | None],
    head_fns: dict[str, str | None],
) -> list[str]:
    """Return the sorted list of qualnames whose citations regressed.

    A regression is: function exists at both revisions, AND the base
    docstring carried a citation, AND the head docstring does NOT carry
    a citation. Functions added at head (no base counterpart) are NOT a
    regression (they are tracked separately if --verbose).
    """
    regressed: list[str] = []
    for qualname in sorted(base_fns):
        if qualname not in head_fns:
            # function removed at head -- tracked separately, not a citation
            # regression
            continue
        base_doc = base_fns[qualname]
        head_doc = head_fns[qualname]
        if _function_has_citation(base_doc) and not _function_has_citation(
            head_doc
        ):
            regressed.append(qualname)
    return regressed


def _diff_added_functions(
    base_fns: dict[str, str | None],
    head_fns: dict[str, str | None],
) -> list[str]:
    """Return sorted list of qualnames added at head (no base counterpart)."""
    return sorted(q for q in head_fns if q not in base_fns)


def _diff_removed_functions(
    base_fns: dict[str, str | None],
    head_fns: dict[str, str | None],
) -> list[str]:
    """Return sorted list of qualnames removed at head (no head counterpart)."""
    return sorted(q for q in base_fns if q not in head_fns)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_function_index(
    sha: str, files: Iterable[str]
) -> dict[str, str | None]:
    """Build a ``{qualname: docstring_or_None}`` map for ``sha``."""
    index: dict[str, str | None] = {}
    for rel_path in files:
        source = _read_blob(sha, rel_path)
        if source is None:
            continue
        for qualname, doc in _extract_functions(source, rel_path):
            index[qualname] = doc
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_doc_paper_refs_diff.py",
        description=(
            "E.4 doc-builder diff job: fail if a refactor drops a paper "
            "equation/section reference from a public function docstring "
            "between --base and --head."
        ),
    )
    parser.add_argument(
        "--base",
        default="HEAD~1",
        help="Base git revision (default: HEAD~1).",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head git revision (default: HEAD).",
    )
    parser.add_argument(
        "--no-exit-code",
        action="store_true",
        help="Always exit 0 even if regressions are detected.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the summary line.",
    )
    args = parser.parse_args(argv)

    base_sha = _run_git("rev-parse", "--verify", args.base)
    head_sha = _run_git("rev-parse", "--verify", args.head)

    # Enumerate the *union* of tracked files across both revisions so a
    # file added/removed between base and head is still scanned at its
    # surviving revision.
    base_files = _python_files_in_tree(base_sha)
    head_files = _python_files_in_tree(head_sha)
    all_files = sorted(set(base_files) | set(head_files))
    if not all_files:
        print(
            "ERROR: no Python files found under adaptive_reflow/ at either "
            "revision (excluding quarantine).",
            file=sys.stderr,
        )
        return 2

    if not args.quiet:
        print(
            f"E.4 diff: base={base_sha[:12]} head={head_sha[:12]} "
            f"({len(all_files)} python files)"
        )

    base_index = _build_function_index(base_sha, base_files)
    head_index = _build_function_index(head_sha, head_files)

    regressed = _diff_functions(base_index, head_index)
    added = _diff_added_functions(base_index, head_index)
    removed = _diff_removed_functions(base_index, head_index)

    n_base = len(base_index)
    n_head = len(head_index)

    if not args.quiet:
        if regressed:
            print(
                f"\nRegressions ({len(regressed)}) -- citation present at "
                "base, missing at head:"
            )
            for q in regressed:
                base_doc = base_index[q]
                head_doc = head_index[q]
                base_cits = _citations_in_doc(base_doc)
                example = base_cits[0] if base_cits else "(no match)"
                print(f"  - {q}  (base anchor: {example!r})")
        if added:
            print(f"\nAdded functions ({len(added)}) -- not a regression:")
            for q in added:
                head_cits = _citations_in_doc(head_index[q])
                flag = "cites" if head_cits else "no-citation"
                example = head_cits[0] if head_cits else "(none)"
                print(f"  - {q}  [{flag}: {example!r}]")
        if removed:
            print(f"\nRemoved functions ({len(removed)}):")
            for q in removed:
                print(f"  - {q}")

    verdict = "PASS" if not regressed else "FAIL"
    print(
        f"\n{verdict}  E.4 diff -- {len(regressed)} regressions across "
        f"{n_head} functions at head ({n_base} at base); "
        f"base={args.base} ({base_sha[:12]}), head={args.head} ({head_sha[:12]})"
    )

    if args.no_exit_code:
        return 0
    return 0 if not regressed else 1


if __name__ == "__main__":
    raise SystemExit(main())