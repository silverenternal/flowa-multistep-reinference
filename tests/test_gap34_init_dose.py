"""GAP-34 — R1 init dose-response: the sampler save/restore contract.

``generate_init_only`` monkey-patches the module-global
``lineageflow._synthesize_latent_like_tensor`` to install the tau-temperature
init sampler. It must **restore** the original on exit, otherwise a later
``init_tau <= 0`` call (which returns the canonical near-uniform sampler) would
silently see a previous tau's sampler instead of the D-004 collapse anchor.

These tests use a fake adapter (no model load) so they stay fast.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_tool():
    for p in (str(REPO_ROOT), str(REPO_ROOT / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("r1_d004b_attribution")


class _FakeAdapter:
    def build_initial_state(self, batch_id, sample_id):  # noqa: ANN001
        return object()

    def solve_ode(self, bundle, cond, seed):  # noqa: ANN001
        return object()

    def observe_token_indices(self, trace, paper_quantities=None,  # noqa: ANN001
                              temperature=1.0, rng=None):
        return {"0": np.zeros((1, 1), dtype=np.int64)}


def test_generate_init_only_restores_canonical_sampler(tmp_path: Path) -> None:
    mod = _load_tool()
    lf = pytest.importorskip("adaptive_reflow.adapters.lineageflow")
    from tools.gen_lineageflow_n1000_fastas import FAMILY_PROFILES

    orig = lf._synthesize_latent_like_tensor
    adapters = {fam: _FakeAdapter() for fam in FAMILY_PROFILES}

    mod.generate_init_only(
        tmp_path / "c1", n=2, seed=42, nfe=10, min_len=30, max_len=40,
        init_source="random-simplex", init_tau=2.0, adapters=adapters,
    )
    # the global must be restored, so a later tau<=0 call sees the canonical sampler
    assert lf._synthesize_latent_like_tensor is orig
    assert mod._make_tau_sampler(0.0) is orig


def test_tau_zero_does_not_poison_the_global(tmp_path: Path) -> None:
    """The regression: tau=2.0 then tau=0.0 must leave the canonical sampler.

    Without the restore, the tau=2.0 call leaves the global patched; the later
    tau=0.0 call then captures *that* sampler as ``saved`` and the collapse
    anchor is silently replaced by the tau=2.0 sampler.
    """
    mod = _load_tool()
    lf = pytest.importorskip("adaptive_reflow.adapters.lineageflow")
    from tools.gen_lineageflow_n1000_fastas import FAMILY_PROFILES

    orig = lf._synthesize_latent_like_tensor
    adapters = {fam: _FakeAdapter() for fam in FAMILY_PROFILES}
    kwargs = dict(n=1, seed=42, nfe=10, min_len=30, max_len=40,
                  init_source="random-simplex", adapters=adapters)

    mod.generate_init_only(tmp_path / "hot", init_tau=2.0, **kwargs)
    assert lf._synthesize_latent_like_tensor is orig  # not left patched

    mod.generate_init_only(tmp_path / "cold", init_tau=0.0, **kwargs)
    assert lf._synthesize_latent_like_tensor is orig  # still canonical
    assert mod._make_tau_sampler(0.0) is orig
