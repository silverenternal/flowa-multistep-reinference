"""Test helpers for asserting that a module is stdlib-only at import time.

The four ``test_no_torch_imported`` / ``test_cross_evaluator_no_torch``
assertions across ``tests/test_eval/`` and the
``tests/test_contracts/test_paper_quantities.py::test_no_torch``
assertion all check the same invariant: importing a target module
must not pull ``torch`` (or any other heavy dependency) into
``sys.modules``.

Because pytest's sys.modules persists across tests in the same
session, any sibling test that legitimately imports torch for its
own work would pollute sys.modules and break these assertions even
when the target module is genuinely torch-free. To defeat this
ordering dependency, each assertion runs in a fresh subprocess
that owns its own interpreter state.

The :func:`assert_import_is_torch_free` helper spawns the subprocess
and asserts cleanly on success / raises :class:`AssertionError`
with the subprocess stderr on failure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> str:
    """Return the absolute path to the repository root (cwd for subprocess)."""
    return str(Path(__file__).resolve().parents[2])


def assert_import_is_torch_free(*module_paths: str) -> None:
    """Assert that each module in ``module_paths`` imports without pulling torch.

    Spawns ``sys.executable -c <script>`` with PYTHONPATH set to the repo
    root and asserts the subprocess exits zero. The script does:

    >>> import sys
    >>> for path in module_paths:
    ...     __import__(path)
    ... assert "torch" not in sys.modules, sys.modules.get("torch")

    On failure the subprocess exits non-zero with a one-line stderr
    message identifying the offending module and the torch module
    repr that leaked in.
    """
    if not module_paths:
        raise ValueError("module_paths must be non-empty")
    quoted = ", ".join(f"{p!r}" for p in module_paths)
    script_lines = [
        "import sys",
        f"_modules = [{quoted}]",
        "for _m in _modules:",
        "    __import__(_m)",
        "if 'torch' in sys.modules:",
        "    sys.stderr.write('torch leaked in: ' + repr(sys.modules['torch']) + '\\n')",
        "    sys.exit(1)",
        "sys.exit(0)",
    ]
    completed = subprocess.run(
        [sys.executable, "-c", "\n".join(script_lines)],
        capture_output=True,
        text=True,
        cwd=_repo_root(),
        check=False,
        env={
            **__import__("os").environ,
            "PYTHONPATH": _repo_root(),
        },
    )
    assert completed.returncode == 0, (
        "subprocess import of "
        + ", ".join(module_paths)
        + f" pulled in torch: stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )


__all__ = ["assert_import_is_torch_free"]