"""GAP-37 — the R3 paired-design fix (``--shared-prior``).

The canonical R3 driver keyed each batch's prior on ``arm_name``, so the
baseline and framework arms built *independent* priors and the "paired" test was
really two-sample. ``--shared-prior`` drops ``arm_name`` from the key so both
arms build the *same* prior. These CPU tests pin that contract without touching
torch / the GPU.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_driver():
    """Import ``scripts/wave338_p5_r3_n1000_paired`` (torch-free at import)."""
    for p in (str(REPO_ROOT), str(REPO_ROOT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("wave338_p5_r3_n1000_paired")


def test_shared_prior_key_is_arm_independent() -> None:
    mod = _load_driver()
    base = mod._make_batch_id(arm_name="baseline", seed_base=42, batch_idx=3,
                              shared_prior=True)
    fw = mod._make_batch_id(arm_name="framework", seed_base=42, batch_idx=3,
                            shared_prior=True)
    assert base == fw == "seed42-batch3"


def test_legacy_key_includes_arm() -> None:
    mod = _load_driver()
    base = mod._make_batch_id(arm_name="baseline", seed_base=42, batch_idx=3,
                              shared_prior=False)
    fw = mod._make_batch_id(arm_name="framework", seed_base=42, batch_idx=3,
                            shared_prior=False)
    assert base == "baseline-seed42-batch3"
    assert fw == "framework-seed42-batch3"
    assert base != fw


def test_shared_prior_key_varies_with_seed_and_batch() -> None:
    mod = _load_driver()
    keys = {
        mod._make_batch_id(arm_name="baseline", seed_base=s, batch_idx=b,
                           shared_prior=True)
        for s in (42, 43, 44) for b in (0, 1)
    }
    assert len(keys) == 6  # distinct prior per (seed, batch), no collisions


def test_driver_exposes_shared_prior_flag(capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load_driver()
    with pytest.raises(SystemExit) as exc:
        mod.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--shared-prior" in out


def test_generate_arm_accepts_shared_prior_kwarg() -> None:
    mod = _load_driver()
    import inspect

    params = inspect.signature(mod._generate_arm).parameters
    assert "shared_prior" in params
    assert params["shared_prior"].default is False
