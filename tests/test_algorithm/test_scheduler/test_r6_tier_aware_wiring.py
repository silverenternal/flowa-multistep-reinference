"""CPU tests for the Wave 275 P4 / GAP-01 R6 tier-aware restart-blend wiring.

Covers three layers:

1. the ``{qid: plddt_mean}`` loader over the Wave 161 frozen foldability JSONL;
2. the :class:`TierAwareCodimensionSheetScheduler` easy/hard behaviour with
   the frozen boundaries (34.56 / 46.13 per Wave 198 P3);
3. the gen-script ``_framework_emit_sequence`` forwarding the tier-aware
   kwargs into ``_solve_framework`` (the load-bearing GAP-01 wire).

No GPU, no checkpoint, no vendored change.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.algorithm.scheduler.tier_aware import (
    TierAwareCodimensionSheetScheduler,
    _compute_tier_boundaries,
)

FROZEN_JSONL = (
    Path(__file__).resolve().parents[3]
    / "verification_outputs"
    / "k6_foldability_n1000_w161_q3_2026"
    / "baseline"
    / "foldability"
    / "foldability.jsonl"
)


def test_load_baseline_metrics_jsonl() -> None:
    from tools.gen_lineageflow_n1000_fastas import _load_baseline_metrics_jsonl

    if not FROZEN_JSONL.exists():
        pytest.skip("frozen Wave 161 foldability JSONL not present")
    m = _load_baseline_metrics_jsonl(FROZEN_JSONL)
    assert len(m) == 1000
    assert m["q0"] == pytest.approx(32.61540540540541)
    assert all(isinstance(k, str) and isinstance(v, float) for k, v in m.items())


def test_frozen_tier_boundaries_match_wave198() -> None:
    if not FROZEN_JSONL.exists():
        pytest.skip("frozen Wave 161 foldability JSONL not present")
    from tools.gen_lineageflow_n1000_fastas import _load_baseline_metrics_jsonl

    m = _load_baseline_metrics_jsonl(FROZEN_JSONL)
    low, high = _compute_tier_boundaries(m, (0.33, 0.67))
    assert low == pytest.approx(34.56, abs=0.01)
    assert high == pytest.approx(46.13, abs=0.01)


def test_tier_aware_reduces_easy_and_passes_hard() -> None:
    from adaptive_reflow.algorithm.scheduler.adaptive import (
        CodimensionSheetScheduler,
    )

    base = CodimensionSheetScheduler(
        cycle_length=20, n_min=0.0, n_max=1.0,
        eps_implicit=0.05, eps_direction="decreasing", seed=0,
    )
    # Easy record (baseline pLDDT 81.91 > 46.13) and hard record (32.75).
    mapping = {"q5": 81.91, "q4": 32.75}
    sched = TierAwareCodimensionSheetScheduler(
        base=base,
        easy_tier_nfe_reduction_factor=0.5,
    )
    sched.set_baseline_metrics(mapping)
    # Pin the Wave 198 P3 / frozen boundaries so the classification is the
    # realistic one (set_baseline_metrics would derive 2-record quantiles).
    sched._tier_boundaries = (34.56, 46.13)

    sched.set_current_record("q5")
    easy_sample = sched.sample(0, 0, 0)
    assert sched.last_tier == "easy"
    base_sample = base.sample(0, 0, 0)
    assert easy_sample.n_cap == pytest.approx(0.5 * base_sample.n_cap, abs=1e-9)

    sched.set_current_record("q4")
    hard_sample = sched.sample(0, 0, 0)
    assert sched.last_tier == "hard"
    assert hard_sample.n_cap == pytest.approx(base_sample.n_cap, abs=1e-9)


def test_gen_script_forwards_tier_aware_kwargs(monkeypatch) -> None:
    """``_framework_emit_sequence`` must forward the tier-aware kwargs."""
    import tools.gen_lineageflow_n1000_fastas as gen
    import tools.run_real_ckpt_eval as rre
    from adaptive_reflow.adapters.lineageflow import AMINO_ACID_CATEGORICAL

    captured: dict[str, object] = {}

    class _Trace:
        pass

    def _fake_solve_framework(adapter, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return _Trace(), 0.0

    class _Adapter:
        def observe_token_indices(self, trace, *, paper_quantities=None,
                                  temperature=1.0, rng=None):  # type: ignore[no-untyped-def]
            return {str(AMINO_ACID_CATEGORICAL): np.zeros(5, dtype=np.int64)}

    monkeypatch.setattr(rre, "_solve_framework", _fake_solve_framework)
    monkeypatch.setattr(gen, "TIER_AWARE_N_CAP", 0.5)
    monkeypatch.setattr(gen, "TIER_AWARE_BASELINE_METRICS", {"q5": 81.91, "q4": 32.75})
    monkeypatch.setattr(gen, "NFE_PER_RECORD", 50)
    monkeypatch.setattr(gen, "RESTART_MIN_NFE", 20)

    seq = gen._framework_emit_sequence(
        _Adapter(), family_id="PF00005.27", length=5, seed=0,
        temperature=1.0, record_id="q5",
    )
    assert seq is not None
    assert captured["tier_aware_n_cap"] == 0.5
    assert captured["tier_aware_baseline_metrics"] == {"q5": 81.91, "q4": 32.75}
    assert captured["current_record_id"] == "q5"


def test_framework_policy_tier_aware_beta_on_constant_path() -> None:
    """The constant-β (LineageFlow) branch must build the tier-aware wrapper.

    GAP-01 discovery (2026-10-13): the wrapper was previously built ONLY
    inside ``if paper_quantities is not None``, so LineageFlow (no
    ``profile_residual_fn``) always took β = 0.5 and the R6 live arm was
    byte-identical to the uniform arm. The as-designed materialization
    (user-selected) raises the easy-tier β to ``1 - 0.5 * n_cap_base``.
    """
    from tools.eval.framework import _make_framework_policy

    class _Caps:
        channel_domains = ("latent",)

    class _Adapter:
        def capabilities(self):  # type: ignore[no-untyped-def]
            return _Caps()

    bm = {"q0": 30.0, "q1": 40.0, "q2": 81.9}  # hard / medium / easy

    def _beta(qid: str) -> float:
        p = _make_framework_policy(
            _Adapter(), target_round=0, seed=42,
            paper_quantities=None, nfe=0,
            tier_aware_n_cap=0.5, tier_aware_baseline_metrics=bm,
            current_record_id=qid,
        )
        return float(next(iter(p.beta_by_channel.values())))

    assert _beta("q2") == pytest.approx(0.75)  # easy: n_cap 0.5 -> 0.25
    assert _beta("q0") == pytest.approx(0.5)   # hard: passthrough
    assert _beta("q1") == pytest.approx(0.5)   # medium: passthrough

    # Legacy default (no flags) must stay byte-stable at β = 0.5.
    p = _make_framework_policy(
        _Adapter(), target_round=0, seed=42, paper_quantities=None, nfe=0,
    )
    assert float(next(iter(p.beta_by_channel.values()))) == pytest.approx(0.5)

    # Flags set but empty mapping -> legacy β = 0.5 (safe no-op).
    p = _make_framework_policy(
        _Adapter(), target_round=0, seed=42, paper_quantities=None, nfe=0,
        tier_aware_n_cap=0.5, tier_aware_baseline_metrics={},
        current_record_id="q2",
    )
    assert float(next(iter(p.beta_by_channel.values()))) == pytest.approx(0.5)


def test_sensitivity_patch_preserves_tier_aware_beta(monkeypatch) -> None:
    """The Wave 186 P2 β override must NOT clobber the tier-aware β.

    Without the bypass in ``_apply_sensitivity_patches`` the patch would
    reset every record's β to ``beta_base`` and the R6 live sweep would
    silently degenerate to the uniform arm.
    """
    import tools.eval.framework as F
    import tools.eval.io as io_mod
    import tools.gen_lineageflow_n1000_fastas as gen
    import tools.run_real_ckpt_eval as rre

    orig_policy = F._make_framework_policy
    orig_shim = rre._make_framework_policy
    orig_nfe = dict(io_mod.ADAPTER_NFE_REF)
    monkeypatch.setattr(gen, "_PATCHES_APPLIED", False)
    try:
        gen._apply_sensitivity_patches(beta_base=0.5, nfe_ref=50)

        class _Caps:
            channel_domains = ("latent",)

        class _Adapter:
            def capabilities(self):  # type: ignore[no-untyped-def]
                return _Caps()

        bm = {"q0": 30.0, "q1": 40.0, "q2": 81.9}
        easy = F._make_framework_policy(
            _Adapter(), target_round=0, seed=42, paper_quantities=None, nfe=0,
            tier_aware_n_cap=0.5, tier_aware_baseline_metrics=bm,
            current_record_id="q2",
        )
        assert float(next(iter(easy.beta_by_channel.values()))) == pytest.approx(0.75)
        hard = F._make_framework_policy(
            _Adapter(), target_round=0, seed=42, paper_quantities=None, nfe=0,
            tier_aware_n_cap=0.5, tier_aware_baseline_metrics=bm,
            current_record_id="q0",
        )
        assert float(next(iter(hard.beta_by_channel.values()))) == pytest.approx(0.5)
    finally:
        F._make_framework_policy = orig_policy
        rre._make_framework_policy = orig_shim
        io_mod.ADAPTER_NFE_REF.clear()
        io_mod.ADAPTER_NFE_REF.update(orig_nfe)
