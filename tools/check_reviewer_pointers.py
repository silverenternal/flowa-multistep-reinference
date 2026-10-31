#!/usr/bin/env python3
"""Resolve every backticked repository path in the reviewer-facing docs.

``tools/check_doc_links.py`` resolves markdown *links* -- ``[text](target)``.
It deliberately ignores inline code spans, because a code span is usually an
example.  But in this project the code span is also how the docs point at
their evidence: ``tools/verify_reproducibility_smoke.py``,
``docs/headline-evidence/composite_axis_byte_stable/SOURCE.md``,
``verification_outputs/wave183-p4-figure-pLDDT-finer.png``.  Nothing checked
those, so a renamed tool or a moved evidence directory left the pointer
dangling while the prose still read as if it resolved.

Scope is the set of documents a reviewer actually reads:

* ``README.md`` / ``README.zh.md`` / ``AGENTS.md``
* ``docs/README.md`` (the documentation map) and ``docs/PAPER-EVIDENCE.md``
  (the cell-level evidence register)
* ``tnnls_submission/*.md`` (the submission package)

On 2026-10-31 the scope grew to the reader-facing reference pages
(``READER_GLOBS``: the model cards, ARCHITECTURE, environments, configs,
adapter-dependencies, DEPRECATION, PLUG_IN_YOUR_MODEL, GATES and the release
checklist).  None of them was checked before, and 32 of their pointers had gone
dead: eight into audit records that the topic-cluster flatten renamed
(``docs/audit/wave201-p2-foldability-sc-workers-per-gpu.md`` ->
``docs/audit/sweep_eval/p2-foldability-sc-workers-per-gpu.md``), ten at files
that were never committed in any branch
(``tools/run_sota_self_flow_experiment.py``,
``tools/run_sota_lineageflow_experiment.py``,
``tools/check_deprecation_policy.py``), eleven at the archived
``docs/paper-draft.md``, three path errors.  See
``docs/audit/reader-doc-pointers.md``.

Deliberately out of scope, with reasons:

* ``CHANGELOG.md`` -- append-only history; an entry naming a file that was
  later deleted is a true statement about that release.
* ``docs/baseline-audit-report.md`` and ``docs/CONSOLIDATED_RESULTS.md`` --
  evidence ledgers whose rows cite the ``verification_outputs/waveNNN-*``
  artefact of the run that produced them.  Those paths are the address of a
  measurement, not a promise that a file is there today, and 641 of them are
  deliberately historical.

Citations *into* ``docs/audit/`` and ``docs/drafts/`` are **not** exempt.  A
reviewer-facing document that names ``docs/audit/...`` is promising the reader
a record they can open, and the audit tree is reorganised into topic clusters
(``docs/audit/engineering/``, ``docs/audit/stats_method/``, ...) and archived
into ``docs/ARCHIVE/`` often enough that ten such citations had gone stale in
the submission package.  The exemption was removed on 2026-10-30; the ten were
repointed at the record that actually holds the claim.

The check is run in a clean clone as well as in the working tree, because the
two disagree: ``data/`` and ``verification_outputs/`` are gitignored, so a
token can resolve here and resolve to nothing on a reviewer's checkout.  The
five checkpoints the docs name are genuinely not distributed (10.5 GB, 68 MB,
and three small ones the model cards tell the reader to fetch themselves) and
are exempted only while they are actually absent -- the same conditional
exemption ``check_submission_links.py`` uses for its one absent target.

Usage
-----
    python3 tools/check_reviewer_pointers.py
    python3 tools/check_reviewer_pointers.py --json
    python3 tools/check_reviewer_pointers.py --quiet
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Documents a reviewer reads.  ``docs/PAPER-EVIDENCE.md`` is generated but is
#: still a pointer surface: every cell row names its artefact.
SURFACES: tuple[str, ...] = (
    "README.md",
    "README.zh.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/PAPER-EVIDENCE.md",
)

#: Reader-facing reference pages.  These are the pages the mkdocs navigation
#: puts in front of a reviewer; they were outside the gate until 2026-10-31.
READER_GLOBS: tuple[str, ...] = (
    "docs/models/*.model_card.md",
    "docs/ARCHITECTURE.md",
    "docs/DEPRECATION.md",
    "docs/GATES.md",
    "docs/PLUG_IN_YOUR_MODEL.md",
    "docs/adapter-dependencies.md",
    "docs/code-release-checklist.md",
    "docs/configs.md",
    "docs/environments.md",
)

#: ``(document, token)`` -> phrases that justify treating the token as absent.
#: A resolver cannot judge these: "the record this used to cite was retired" is
#: a true statement whose subject is a missing file, and rewriting the path
#: would assert the record is filed somewhere it never was.
#:
#: The exemption is conditional on the prose, the same way ``DECLARED_ABSENT``
#: is conditional on the file being absent: at least one phrase must still
#: appear within ``PROSE_ABSENT_WINDOW`` lines of the token.  Edit the sentence
#: to claim the file exists and the exemption lapses, so the pointer is
#: reported instead of silently trusted.
PROSE_ABSENT: dict[tuple[str, str], tuple[str, ...]] = {
    ("docs/GATES.md", "todo/GATES.md"):
        ("was not carried over",),
    ("docs/ARCHITECTURE.md", "adaptive_reflow/__init__.py"):
        ("top-level `adaptive_reflow/__init__.py`", "does not exist"),
    ("docs/DEPRECATION.md", "tools/check_deprecation_policy.py"):
        ("never committed",),
    ("docs/PLUG_IN_YOUR_MODEL.md", "tools/run_sota_kanzi_experiment.py"):
        ("not yet authored",),
    ("docs/PLUG_IN_YOUR_MODEL.md", "todo/PHASE-4-model-integration-iteration.md"):
        ("retired on",),
    ("docs/adapter-dependencies.md", "docs/models/M.model_card.md"):
        ("upload each",),
    ("docs/code-release-checklist.md",
     "scripts/run_kanzi_n1000_framework_inv_proj_seed42.sh"):
        ("never committed",),
    ("docs/models/kanzi.model_card.md", "todo/models/kanzi.md"):
        ("retired 2026-10-13", "first Kanzi analysis"),
    ("docs/models/freqflow.model_card.md", "todo/models/freqflow.md"):
        ("retired 2026-10-13", "the earlier analysis note"),
}

#: How far from the token the justifying phrase may sit.  Two lines either way
#: covers a sentence that wraps; more would start matching a different
#: paragraph's disclaimer.
PROSE_ABSENT_WINDOW: int = 2

#: Weights the repository deliberately does not carry, so a fresh clone cannot
#: resolve them.  The exemption applies only while the file is genuinely
#: absent: if it exists on disk it must still be checked like any other path.
DECLARED_ABSENT: frozenset[str] = frozenset({
    "data/flowmol3/weights_real/checkpoints/last.ckpt",   # 68 MB
    "data/lineageflow/lineageflow-rp55.ckpt",             # 10.5 GB
    "data/kanzi/kanzi_encoder.pt",                        # card lists 3 layouts
    "data/kanzi_encoder.pt",
    "data/freqflow_ckpt/nnet_ema.pth",                    # card says it is absent
})


def known_absent() -> frozenset[str]:
    """Return the declared-absent tokens that are genuinely absent."""
    return frozenset(
        token for token in DECLARED_ABSENT if not (REPO_ROOT / token).exists()
    )

#: Directory prefixes that name a location inside this checkout.  ``todo`` is
#: here because the directory was retired on 2026-10-13 and six citations into
#: it survived in the submission package; a prefix that no longer exists is
#: exactly the one that needs checking.
PATH_PREFIXES: tuple[str, ...] = (
    "adaptive_reflow", "configs", "data", "docs", "paper-data", "reproduce",
    "scripts", "tests", "tnnls_submission", "todo", "tools",
    "verification_outputs",
)

#: Extensions that make a bare token a path rather than a symbol.
EXTENSIONS: tuple[str, ...] = (
    "bash", "bib", "cc", "cfg", "ckpt", "cpp", "csv", "go", "h", "hpp",
    "html", "ini", "ipynb", "jpeg", "jpg", "js", "json", "jsonl", "lean",
    "lock", "markdown", "md", "npy", "npz", "pdf", "png", "pt", "pth", "py",
    "pyi", "rst", "rs", "sh", "sql", "svg", "tex", "toml", "ts", "tsv",
    "tsx", "txt", "yaml", "yml",
)

TOKEN_RE: re.Pattern[str] = re.compile(
    r"`(?P<path>(?:" + "|".join(PATH_PREFIXES) + r")/[A-Za-z0-9_./-]+?"
    r"\.(?:" + "|".join(sorted(EXTENSIONS, key=len, reverse=True)) + r"))`"
)


def surfaces() -> list[Path]:
    """Return the documents in scope that exist on disk."""
    out = [REPO_ROOT / name for name in SURFACES]
    out += sorted((REPO_ROOT / "tnnls_submission").glob("*.md"))
    for pattern in READER_GLOBS:
        out += sorted(REPO_ROOT.glob(pattern))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in out:
        if path.is_file() and path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _exempt(
    doc: Path, raw: str, absent: frozenset[str], lines: list[str], index: int
) -> bool:
    """True when ``raw`` is undelivered by design or the prose says it is gone."""
    if raw in absent:
        return True
    phrases = PROSE_ABSENT.get((doc.relative_to(REPO_ROOT).as_posix(), raw))
    if not phrases:
        return False
    lo = max(0, index - PROSE_ABSENT_WINDOW)
    hi = min(len(lines), index + PROSE_ABSENT_WINDOW + 1)
    window = "\n".join(lines[lo:hi])
    return any(phrase in window for phrase in phrases)


def collect() -> list[dict[str, str]]:
    """Return one row per dead pointer."""
    absent = known_absent()
    rows: list[dict[str, str]] = []
    for doc in surfaces():
        text = doc.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for lineno, line in enumerate(lines, 1):
            for match in TOKEN_RE.finditer(line):
                raw = match.group("path").rstrip(".,;:")
                if _exempt(doc, raw, absent, lines, lineno - 1):
                    continue
                if (REPO_ROOT / raw).exists():
                    continue
                rows.append({
                    "source": str(doc.relative_to(REPO_ROOT)),
                    "line": str(lineno),
                    "target": raw,
                })
    return rows


def count_pointers() -> int:
    """Return the number of in-scope pointers examined."""
    absent = known_absent()
    total = 0
    for doc in surfaces():
        text = doc.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            for match in TOKEN_RE.finditer(line):
                raw = match.group("path").rstrip(".,;:")
                if _exempt(doc, raw, absent, lines, index):
                    continue
                total += 1
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rows = collect()
    checked = count_pointers()

    if args.json:
        print(json.dumps(rows, indent=1))
        print(f"checked={checked} dead={len(rows)}", file=sys.stderr)
    else:
        if not args.quiet:
            for row in rows:
                print(f"{row['source']}:{row['line']}  ->  {row['target']}")
        print(f"checked={checked} dead={len(rows)}")

    if rows:
        print(f"FAIL: {len(rows)} dead pointer(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
