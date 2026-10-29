#!/usr/bin/env python3
"""Resolve every relative markdown link in the repo's documentation.

GitHub resolves a relative link against the directory of the file that
contains it.  When a document is moved, or when a link is written as if the
repository root were the current directory, the link silently stops working:
the text still renders, the target 404s, and nothing in the test suite
notices.

Scope: ``docs/**/*.md`` (excluding ``docs/ARCHIVE/``), repository-root
``*.md`` and ``tnnls_submission/**/*.md``.  Links inside fenced code blocks
and inline code spans are ignored -- they are examples, not links.

Each broken link is classified by the *smallest* fix that would make it work:

``root-relative``  the target resolves from the repository root
``docs-relative``  the target resolves from ``docs/``
``moved``          exactly one file with that basename exists outside ARCHIVE
``archived``       exactly one file with that basename exists under ARCHIVE
``ambiguous``      several files share that basename
``missing``        no file with that basename exists anywhere

Only ``missing`` and ``ambiguous`` are hard failures; the first three are
reported because they still 404 on GitHub and should be rewritten.

Usage
-----
    python3 tools/check_doc_links.py
    python3 tools/check_doc_links.py --json
    python3 tools/check_doc_links.py --quiet
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = frozenset({
    ".git", ".venvs", ".mypy_cache", ".pytest_cache", "__pycache__",
    "data", "node_modules", "site",
})

#: Files whose broken links are deliberate: historical records that quote a
#: path as it stood at the time.  Keep empty where possible.
#:
#: The one entry is a *shipped artifact*, not a document: the supplementary
#: bundle's README is byte-identical to its copy inside
#: ``tnnls_submission/supplementary_bundle.zip`` (14,087 bytes, pinned by
#: ``MANIFEST.md``), so rewriting its links here would desynchronise the
#: repository from the zip a reviewer downloads.  Its two relative targets are
#: also meaningless inside the zip, where ``docs/`` is not shipped at all.
#: Repaired only if the bundle is rebuilt.
FROZEN: frozenset[str] = frozenset({
    "tnnls_submission/supplementary_bundle/headline_evidence/README.md",
})

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code so examples are not links."""
    text = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


def _is_external(target: str) -> bool:
    return (
        not target
        or target.startswith(("http://", "https://", "mailto:", "#", "/"))
        or any(tok in target for tok in ("<", ">", "*", "{", "}"))
        or target == "..."
    )


def _index() -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = collections.defaultdict(list)
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        index[path.name].append(path)
    return index


def _sources() -> list[Path]:
    out = list(REPO_ROOT.glob("docs/**/*.md"))
    out += list(REPO_ROOT.glob("*.md"))
    out += list(REPO_ROOT.glob("tnnls_submission/**/*.md"))
    return sorted(p for p in out if "ARCHIVE" not in p.relative_to(REPO_ROOT).parts)


def _iter_links(md: Path):
    """Yield (label, target) for every non-external link in ``md``."""
    text = _strip_code(md.read_text(encoding="utf-8", errors="replace"))
    for match in LINK_RE.finditer(text):
        target = match.group(2).strip().split("#")[0].strip()
        if _is_external(target):
            continue
        yield match.group(1), target


def count_links() -> int:
    """Total number of relative links scanned."""
    return sum(1 for md in _sources() for _ in _iter_links(md))


def collect() -> list[dict]:
    index = _index()
    rows: list[dict] = []
    for md in _sources():
        rel = str(md.relative_to(REPO_ROOT))
        seen: set[str] = set()
        for _label, target in _iter_links(md):
            if target in seen:
                continue
            seen.add(target)
            if (md.parent / target).exists():
                continue
            if (REPO_ROOT / target).exists():
                status, hint = "root-relative", target
            elif (REPO_ROOT / "docs" / target).exists():
                status, hint = "docs-relative", "docs/" + target
            else:
                hits = index.get(Path(target).name, [])
                live = [h for h in hits if "ARCHIVE" not in h.parts]
                arch = [h for h in hits if "ARCHIVE" in h.parts]
                if len(live) == 1:
                    status, hint = "moved", str(live[0].relative_to(REPO_ROOT))
                elif not live and len(arch) == 1:
                    status, hint = "archived", str(arch[0].relative_to(REPO_ROOT))
                elif len(live) > 1:
                    status, hint = "ambiguous", ", ".join(
                        str(h.relative_to(REPO_ROOT)) for h in live[:3]
                    )
                elif len(arch) > 1:
                    status, hint = "ambiguous", ", ".join(
                        str(h.relative_to(REPO_ROOT)) for h in arch[:3]
                    )
                else:
                    status, hint = "missing", ""
            rows.append({"source": rel, "target": target, "status": status,
                         "hint": hint})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rows = collect()
    checked = count_links()
    counts = collections.Counter(r["status"] for r in rows)
    hard = [r for r in rows
            if r["status"] in ("missing", "ambiguous") and r["source"] not in FROZEN]

    if args.json:
        print(json.dumps(rows, indent=1))
        print(f"checked={checked} broken={len(rows)} "
              + " ".join(f"{k}={v}" for k, v in sorted(counts.items())),
              file=sys.stderr)
    else:
        if not args.quiet:
            for row in rows:
                print(f"{row['status']:14s} {row['source']}  ->  {row['target']}")
                if row["hint"]:
                    print(f"{'':14s}   {row['hint']}")
        print(f"checked={checked} broken={len(rows)} "
              + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if hard:
        print(f"FAIL: {len(hard)} unresolved link(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
