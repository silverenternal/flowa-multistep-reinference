#!/usr/bin/env python3
"""Convenience wrapper for ``tools/hf_pipeline.py``.

Mirrors the project's existing wrapper convention (e.g.
``scripts/capture_env_hash.py`` delegates to no helper; this wrapper
delegates to ``tools/hf_pipeline.py`` for the actual upload work).

The wrapper exists so contributors can run the upload pipeline without
remembering the ``tools.`` package prefix::

    .venvs/flowmol3_venv/bin/python scripts/upload_model_card.py \\
        --model kanzi --upload-dry-run

The script preserves the underlying CLI verbatim: every flag
(``--model``, ``--repo-id``, ``--upload-dry-run``, ``--render-only``,
``--output``, ``--commit-message``, ``--token``) is forwarded to
:func:`tools.hf_pipeline.main`. No additional logic lives here.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make ``tools/`` importable without an install step. Mirrors the
# sys.path manipulation pattern used by ``scripts/capture_env_hash.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.hf_pipeline import main as _hf_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(_hf_main())
