"""GAP-90 — the sweep summary must be able to name the code that produced it.

Two provenance fields were wrong in every MNIST artifact written before
2026-10-27: ``sweep_command`` was a hardcoded template naming a different
``--output-dir`` and ``--seed``, and ``commit_sha`` was the literal string
``"PENDING"`` (540 of 541 cells). These tests pin the replacements so the
sentinel cannot come back.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.wave191_p3_mnist_sweep import git_provenance  # noqa: E402

_MODULE = REPO_ROOT / "scripts" / "wave191_p3_mnist_sweep.py"


def test_git_provenance_returns_a_full_sha() -> None:
    sha, dirty = git_provenance()
    if sha is None:
        # git unavailable: the contract is (None, None), not an exception.
        assert dirty is None
        return
    assert re.fullmatch(r"[0-9a-f]{40}", sha), sha
    assert isinstance(dirty, bool)


def test_commit_sha_is_not_a_sentinel() -> None:
    source = _MODULE.read_text()
    assert '"commit_sha": "PENDING"' not in source
    assert "'commit_sha': 'PENDING'" not in source
    # The field is still written — this is a fix, not a deletion.
    assert '"commit_sha": commit_sha' in source
    assert '"commit_dirty": commit_dirty' in source


def test_sweep_command_is_the_argv_not_a_template() -> None:
    source = _MODULE.read_text()
    assert '"sweep_command": shlex.join([sys.executable, *sys.argv])' in source
    # The old template named a fixed output directory and seed.
    assert "verification_outputs/wave191-p3-mnist-n1000 --seed" not in source
