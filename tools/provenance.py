"""Provenance helpers for the experiment drivers.

Written 2026-10-27 after an audit found that four sweep drivers recorded the
literal string `PENDING` in the `commit_sha` field, so 540 of 541 MNIST cells
(and every cell from the other three drivers) could not be tied to a code
version. The field is cheap to fill and expensive to reconstruct later, so it
lives in one place rather than being copied per driver.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def git_provenance(repo_root: Path | None = None) -> tuple[str | None, bool | None]:
    """``(HEAD sha, tree dirty?)`` for the checkout an artifact was produced in.

    Returns ``(None, None)`` when git is unavailable rather than raising: a
    missing sha is a caveat on the artifact, not a reason to lose the run.
    """
    cwd = repo_root or REPO_ROOT
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd, capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    return (sha or None), bool(status.strip())


__all__ = ["REPO_ROOT", "git_provenance"]
