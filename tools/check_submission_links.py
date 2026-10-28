#!/usr/bin/env python3
"""Check the local GitHub links in ``tnnls_submission/*.md``.

Every ``github.com/silverenternal/flowa-multistep-reinference/blob/main/<path>``
link in the submission package is resolved against the working tree.  Missing
targets are classified as:

* ``archived`` — the same basename exists under ``docs/ARCHIVE/`` (the Wave 266
  reorganisation moved the audit docs without rewriting the links);
* ``elsewhere`` — the same basename exists somewhere else in the repo;
* ``absent`` — no file with that basename exists.

Template links (``<path>``, ``<file>``, ``...``) are ignored: they are prose,
not links.

Exit status is 0 only when no ``absent`` target remains (``archived`` and
``elsewhere`` are reported but tolerated — those are basename matches, not
proof the link is right, so a reviewer should still repoint them).  Pass
``--no-strict`` to get the historical always-zero behaviour.

Usage
-----
    python3 tools/check_submission_links.py
    python3 tools/check_submission_links.py --json
    python3 tools/check_submission_links.py --no-strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = REPO_ROOT / "tnnls_submission"
LINK_RE = re.compile(
    r"https://github\.com/silverenternal/flowa-multistep-reinference"
    r"/blob/main/([^\)\s]+)"
)

#: Targets allowed to stay absent.  Keep empty; an entry here must name a
#: real reason in the comment and be removed once the file lands.
KNOWN_ABSENT: frozenset[tuple[str, str]] = frozenset()


def _is_template(path: str) -> bool:
    return any(tok in path for tok in ("<", ">", "...", "`", "*"))


def _find_by_basename(name: str) -> list[str]:
    hits: list[str] = []
    for base in (REPO_ROOT / "docs", REPO_ROOT / "scripts",
                 REPO_ROOT / "tools", REPO_ROOT / "adaptive_reflow",
                 REPO_ROOT / "verification_outputs"):
        if not base.exists():
            continue
        for path in base.rglob(name):
            if ".venvs" in path.parts:
                continue
            hits.append(str(path.relative_to(REPO_ROOT)))
    return sorted(hits)


def collect() -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for md in sorted(SUBMISSION.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1).split("#")[0]
            if _is_template(target):
                continue
            key = (md.name, target)
            if key in seen:
                continue
            seen.add(key)
            path = REPO_ROOT / target
            if path.exists():
                status = "ok"
                candidates: list[str] = []
            else:
                candidates = _find_by_basename(Path(target).name)
                if any(c.startswith("docs/ARCHIVE/") for c in candidates):
                    status = "archived"
                elif candidates:
                    status = "elsewhere"
                else:
                    status = "absent"
            rows.append(
                {
                    "source": md.name,
                    "target": target,
                    "status": status,
                    "candidates": candidates[:4],
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="always exit 0 (pre-2026-10-29 behaviour)",
    )
    args = parser.parse_args(argv)

    rows = collect()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    unexempt = [
        row
        for row in rows
        if row["status"] == "absent"
        and (row["source"], row["target"]) not in KNOWN_ABSENT
    ]
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for status in ("absent", "elsewhere", "archived"):
            for row in rows:
                if row["status"] != status:
                    continue
                print(f"{status:9s} {row['target']}  <- {row['source']}")
                for candidate in row["candidates"]:
                    print(f"          candidate: {candidate}")
        print()
        print(
            "links="
            + str(len(rows))
            + " "
            + " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        )
        if unexempt:
            print(
                f"FAIL: {len(unexempt)} absent link target(s) with no "
                "KNOWN_ABSENT exemption",
                file=sys.stderr,
            )
    if unexempt and not args.no_strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
