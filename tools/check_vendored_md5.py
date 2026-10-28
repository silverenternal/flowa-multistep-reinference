#!/usr/bin/env python3
"""Verify the vendored upstream files against their recorded MD5s.

``tnnls_submission/data_availability.md`` states that the nine files reverted
at Wave 262 are bytewise identical to their upstream commits, and points
reviewers at a verification audit.  That audit was not in the repository (the
cited path 404s), and neither was the MD5 table it referred to.  This script is
the reproducible form of the claim: it hard-codes the MD5 of every file whose
hash was recorded in the Wave 261 P1 inventory or the Wave 261 P5 post-revert
table, and fails if any file has moved.

What this checks
----------------
The bytes on disk today against the bytes recorded when the revert was made.
It does **not** re-fetch the upstream commits, so it cannot detect a case where
the recorded value was wrong from the start.  Re-fetching would need network
access to the nine upstream repositories.

Usage
-----
    python3 tools/check_vendored_md5.py           # table + exit status
    python3 tools/check_vendored_md5.py --quiet   # exit status only
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: (relative path, expected md5, where the expectation is recorded)
EXPECTED: tuple[tuple[str, str, str], ...] = (
    # --- FlowMol3 (commit 77cae22) ---------------------------------------
    ("data/FlowMol3/repo/flowmol/analysis/metrics.py",
     "20a3adbcbf09e631ae5519f5dbf4f117", "wave261-p1 inventory 2.1"),
    ("data/FlowMol3/repo/test.py",
     "fcc620cbf18518e8f907a70adb90b945", "wave261-p1 inventory 2.1"),
    ("data/FlowMol3/repo/dataset_metrics.py",
     "2f7b5f5d73731ac1eec9488273b1a3d5", "wave261-p1 inventory 2.1"),
    # Reverted at Wave 262 P1 (the three silently patched files).
    ("data/FlowMol3/repo/flowmol/analysis/molecule_builder.py",
     "449e98677581fab0474356bfe667fb0d", "wave262-p4 post-revert"),
    ("data/FlowMol3/repo/flowmol/models/flowmol.py",
     "7cca52b0cfff6837214f4297c84f823e", "wave262-p4 post-revert"),
    ("data/FlowMol3/repo/flowmol/utils/ctmc_utils.py",
     "7777b6f887abecdde9dc7ec54d4a84f5", "wave262-p4 post-revert"),
    # --- HiDream-I1 (commit 5f92bab) ------------------------------------
    ("data/HiDream-I1/repo/inference.py",
     "c6c8ecc11450e49d9ed98724ed90eb07", "wave261-p1 inventory 2.2"),
    # --- Lumina-Image-2.0 (commit 4a4d6f8) -------------------------------
    ("data/lumina_image_2_0/repo/sample.py",
     "df86c95f1da227aba4336eefa11e1292", "wave261-p1 inventory 2.4"),
    # --- ProtBFN / AbBFN (commit 869a9af) --------------------------------
    ("data/protbfn_abbfn/repo/sample.py",
     "da30546f362d774d55eb1e6b46212cdd", "wave261-p1 inventory 2.5"),
    # --- Wan2.2 (commit 42bf4cf) -----------------------------------------
    ("data/wan2_2/repo/generate.py",
     "c1af4e1a039ce052cb874475f28caecf", "wave261-p1 inventory 2.6"),
    # --- Kanzi (commit cfed9cf) ------------------------------------------
    ("data/kanzi_upstream/src/kanzi/__init__.py",
     "527ee8d515dc2d75f957dd39eaad9313", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/attention.py",
     "e42867f13b9e7af9775cbe99bc27ddfb", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/cfm.py",
     "31c16cac32d35ea839978e935918c630", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/fsq.py",
     "4d9a6100f6c87e4be886b86916dc9310", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/models.py",
     "33ad14abd38286d62eb250dc203886bc", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/rotary.py",
     "e82a42066612ed3a79832211046961cf", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/train_cb.py",
     "860a31e1660e26e456de7350059667e3", "wave261-p1 inventory 2.7"),
    ("data/kanzi_upstream/src/kanzi/utils.py",
     "ee1e4598dec38bc77b332dc746acea91", "wave261-p1 inventory 2.7"),
    # --- LineageFlow (commit ccef84a), post-revert ----------------------
    ("data/lineageflow_upstream/evaluation/evaluate_all.py",
     "01c3f121e0ca2b8dd65666ed096120da", "wave261-p5 post-revert"),
    ("data/lineageflow_upstream/evaluation/foldability_omegafold.py",
     "c21219e263a70404c5524177dddf78a7", "wave261-p5 post-revert"),
    ("data/lineageflow_upstream/evaluation/novelty_mmseqs2.py",
     "729d5a36d9a4b8fbce398f783336dae7", "wave261-p5 post-revert"),
    ("data/lineageflow_upstream/evaluation/run_foldability.py",
     "8b11a3390518eeb2ddcf5c48d9490d2d", "wave261-p5 post-revert"),
    ("data/lineageflow_upstream/evaluation/self_consistency_esmif.py",
     "a4a0cf3c6e8ebdb2549c82613c060c6a", "wave261-p5 post-revert"),
    # --- FreqFlow (tarball, not git-controlled) -------------------------
    ("data/freqflow_ckpt/upstream/eval.py",
     "a42cb391fa991b06d22a3db473cfa70d", "wave261-p1 inventory 2.9"),
    ("data/freqflow_ckpt/upstream/datasets.py",
     "c6aa2623f6b49d49ecf1c93c69853fb8", "wave261-p1 inventory 2.9"),
)


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def check() -> tuple[list[str], list[tuple[str, str, str]]]:
    """Return (missing paths, (path, expected, actual) mismatches)."""
    missing: list[str] = []
    mismatched: list[tuple[str, str, str]] = []
    for rel, expected, _source in EXPECTED:
        path = REPO_ROOT / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = md5_of(path)
        if actual != expected:
            mismatched.append((rel, expected, actual))
    return missing, mismatched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    missing, mismatched = check()
    if not args.quiet:
        width = max(len(rel) for rel, _, _ in EXPECTED)
        print(f"{'file'.ljust(width)}  {'md5':32s}  status")
        for rel, expected, _source in EXPECTED:
            path = REPO_ROOT / rel
            if not path.is_file():
                status = "MISSING"
            elif any(rel == m[0] for m in mismatched):
                status = "MISMATCH"
            else:
                status = "ok"
            print(f"{rel.ljust(width)}  {expected:32s}  {status}")
        print()
    print(
        f"checked={len(EXPECTED)} missing={len(missing)} "
        f"mismatch={len(mismatched)}"
    )
    for rel in missing:
        print(f"  MISSING  {rel}", file=sys.stderr)
    for rel, expected, actual in mismatched:
        print(
            f"  MISMATCH {rel}\n           expected {expected}\n"
            f"           actual   {actual}",
            file=sys.stderr,
        )
    return 0 if not missing and not mismatched else 1


if __name__ == "__main__":
    sys.exit(main())
