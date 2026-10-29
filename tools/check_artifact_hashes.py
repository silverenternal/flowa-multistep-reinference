#!/usr/bin/env python3
"""Verify the artifact hashes quoted in the two root READMEs.

The manuscript artifacts (``docs/drafts/paper-A-final.{md,tex,pdf}``) are
cited by SHA-256 in ``README.md`` and ``README.zh.md`` so that a reviewer can
confirm they hold the shipped bytes.  Those citations are the *only*
machine-checkable claim about the artifacts outside ``tnnls_submission/``,
and ``tools/verify_submission_readiness.py`` deliberately skips the root
READMEs (its claims scanner is scoped to ``docs/``), so nothing watched them.

They rotted exactly once: the 2026-10-27 packaging rebuild moved the three
artifacts to a 12-page PDF, and both READMEs kept quoting the superseded
2026-10-12 pass-#11 readings (``0586a564…`` / ``a9883fc9…``, 25,959 words,
11 pages) for two days.  ``tnnls_submission/MANIFEST.md`` had the correct
values throughout — the drift was purely between the two surfaces.

Rule: on any README line that names an artifact, every 64-hex token on that
line must equal the file's real digest.  A line that names an artifact but
carries no digest is ignored (prose references such as the reproducibility
recipe are legitimate); historical readings belong in the audit trail, not in
the README.

Usage
-----
    python3 tools/check_artifact_hashes.py
    python3 tools/check_artifact_hashes.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("README.md", "README.zh.md")
ARTIFACTS = (
    "docs/drafts/paper-A-final.md",
    "docs/drafts/paper-A-final.tex",
    "docs/drafts/paper-A-final.pdf",
)
HEX_RE = re.compile(r"\b[0-9a-f]{64}\b")
# The READMEs cite the manuscript source and the PDF; the ``.tex`` is a build
# intermediate that is hashed in ``tnnls_submission/SHA256SUMS`` instead.  It
# is still validated here when quoted, but not required to be quoted.
REQUIRED_CITED = (
    "docs/drafts/paper-A-final.md",
    "docs/drafts/paper-A-final.pdf",
)


def real_hash(rel: str) -> str | None:
    path = REPO_ROOT / rel
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan() -> list[dict[str, object]]:
    """Return one record per (source, line, artifact) citation."""
    records: list[dict[str, object]] = []
    hashes = {rel: real_hash(rel) for rel in ARTIFACTS}
    for name in SOURCES:
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for rel in ARTIFACTS:
                if Path(rel).name not in line:
                    continue
                quoted = HEX_RE.findall(line)
                if not quoted:
                    continue
                actual = hashes[rel]
                bad = [q for q in quoted if q != actual]
                records.append(
                    {
                        "source": name,
                        "line": lineno,
                        "artifact": rel,
                        "quoted": quoted,
                        "actual": actual,
                        "status": "ok" if not bad else "stale",
                    }
                )
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    records = scan()
    stale = [r for r in records if r["status"] != "ok"]
    covered = {r["artifact"] for r in records}
    uncited = [rel for rel in REQUIRED_CITED if rel not in covered]

    if args.json:
        json.dump(
            {"checked": len(records), "stale": stale, "uncited": uncited},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        for r in stale:
            print(
                f"{r['source']}:{r['line']}: {r['artifact']} quotes "
                f"{r['quoted']} but the file is {r['actual']}"
            )
        for rel in uncited:
            print(f"{rel}: no SHA-256 citation found in {', '.join(SOURCES)}")
        print(f"citations={len(records)} stale={len(stale)} uncited={len(uncited)}")

    return 1 if stale or uncited else 0


if __name__ == "__main__":
    sys.exit(main())
