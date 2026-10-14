"""CPU-only tests for the GAP-32 FlowMol3 x-channel sampler helpers.

The sampler's heavy path needs torch + DGL + the vendored FlowMol3 repo, so
these tests cover only the pure helpers (config fingerprint, arm roster,
per-molecule confidence) that must stay correct without a GPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

import gap32_flowmol3_sampler as sampler  # noqa: E402


def test_arm_roster_matches_r6_family() -> None:
    assert sampler.ARM_ORDER == (
        "vanilla",
        "fastdllm",
        "abcache",
        "lediflow",
        "flowa",
    )
    assert sampler.EXTERNAL_ARMS == ("fastdllm", "abcache", "lediflow")


def test_solver_config_defaults_mirror_r6() -> None:
    cfg = sampler.SolverConfig()
    assert cfg.nfe == sampler.DEFAULT_NFE == 250
    assert cfg.fastdllm_threshold == sampler.DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD
    assert cfg.abcache_warmup == sampler.DEFAULT_ABCACHE_WARMUP_STEPS
    assert cfg.abcache_interval == sampler.DEFAULT_ABCACHE_RECOMPUTE_INTERVAL
    assert cfg.abcache_qlen == sampler.DEFAULT_ABCACHE_QUEUE_LENGTH
    assert cfg.lediflow_alpha == sampler.DEFAULT_LEDIFLOW_PRIOR_ALPHA
    assert cfg.lediflow_seed == sampler.DEFAULT_LEDIFLOW_PRIOR_SEED
    assert cfg.lediflow_scale == sampler.DEFAULT_LEDIFLOW_PRIOR_SCALE
    assert cfg.flowa_n_rounds == sampler.DEFAULT_FLOWA_N_ROUNDS
    assert cfg.flowa_beta == sampler.DEFAULT_FLOWA_BETA


def test_config_fingerprint_is_deterministic_and_sensitive() -> None:
    a = sampler.config_fingerprint(sampler.SolverConfig())
    b = sampler.config_fingerprint(sampler.SolverConfig())
    assert a == b
    assert len(a) == 64
    # A changed solver budget must change the fingerprint.
    c = sampler.config_fingerprint(sampler.SolverConfig(nfe=251))
    assert c != a
    # A changed framework recipe must change the fingerprint.
    d = sampler.config_fingerprint(sampler.SolverConfig(flowa_beta=0.25))
    assert d != a


def test_per_molecule_relative_l2_identity_is_zero() -> None:
    torch = pytest.importorskip("torch")
    a = torch.tensor([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [1.0, 1.0, 0.0]])
    node_batch_idx = torch.tensor([0, 0, 1])
    rel = sampler._per_molecule_relative_l2(a, a.clone(), node_batch_idx, 2)
    assert rel.shape == (2,)
    assert float(rel.abs().max()) == 0.0


def test_per_molecule_relative_l2_groups_by_molecule() -> None:
    torch = pytest.importorskip("torch")
    # Molecule 0: a == b (rel 0). Molecule 1: a == 2*b (rel 0.5).
    a = torch.tensor([[1.0, 0.0], [3.0, 0.0], [4.0, 0.0]])
    b = torch.tensor([[1.0, 0.0], [3.0, 0.0], [2.0, 0.0]])
    node_batch_idx = torch.tensor([0, 0, 1])
    rel = sampler._per_molecule_relative_l2(a, b, node_batch_idx, 2)
    assert float(rel[0]) == 0.0
    assert float(rel[1]) == pytest.approx(0.5, abs=1e-6)
