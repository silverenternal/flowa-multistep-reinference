"""GAP-44 — the paper-quantity channels are live on R1, and off by default.

Four properties, matching the gap's acceptance criteria:

1. the R1 driver's channel builder yields an **active**
   :class:`PaperQuantitiesCache` (:attr:`~PaperQuantitiesCache.is_active` is
   ``True``) and an adapter that carries the profile;
2. ``_compute_paper_quantities`` returns ``None`` for the default adapter and a
   populated dict for the wired one — this is the single switch that decides
   whether the framework takes the constant-β path;
3. the codimension-sheet ``n_cap`` stops saturating at ``1.0`` once the profile
   is forwarded into the scheduler base;
4. the default path is unchanged: no profile on the adapter, no paper
   quantities, and the codimension-sheet vector is the degenerate all-ones one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.eval.framework import (  # noqa: E402
    _compute_paper_quantities,
    _make_framework_policy,
)
from tools.gen_lineageflow_n1000_fastas import (  # noqa: E402
    _build_lineageflow_adapter,
    _build_profile_residual_channels,
    _codimension_sheet_n_cap_vector,
)

FAMILY_ID = "PF00072.24"
SEED = 42


@pytest.fixture(scope="module")
def channels():  # noqa: ANN201
    profile_fn, cache = _build_profile_residual_channels()
    assert profile_fn is not None and cache is not None, (
        "adaptive_reflow is importable in the test environment"
    )
    return profile_fn, cache


def test_cache_is_active_and_carries_the_four_quantities(channels) -> None:
    _profile_fn, cache = channels
    assert cache.is_active is True
    assert cache.stats()["is_active"] == 1
    for name in ("sheet_A", "packing_B", "cell_C", "e_rho"):
        value = getattr(cache, name)
        assert value is not None, name
        assert value == value, f"{name} must not be NaN"


def test_r1_adapter_carries_the_profile(channels) -> None:
    profile_fn, _cache = channels
    adapter = _build_lineageflow_adapter(
        FAMILY_ID, SEED, profile_residual_fn=profile_fn
    )
    assert adapter is not None
    assert adapter.profile_residual_fn is profile_fn


def test_paper_quantities_flip_from_none_to_populated(channels) -> None:
    profile_fn, _cache = channels
    off = _build_lineageflow_adapter(FAMILY_ID, SEED)
    on = _build_lineageflow_adapter(FAMILY_ID, SEED, profile_residual_fn=profile_fn)
    assert off is not None and on is not None

    assert _compute_paper_quantities(off, None, round_index=0) is None
    pq = _compute_paper_quantities(on, None, round_index=0)
    assert pq is not None
    assert set(pq) == {"sheet_A", "packing_B", "exterior_gap"}
    assert all(isinstance(v, float) and v == v for v in pq.values())


def test_codimension_sheet_n_cap_is_no_longer_degenerate(channels) -> None:
    profile_fn, _cache = channels
    degenerate = _codimension_sheet_n_cap_vector(None, seed=SEED, n_rounds=4)
    wired = _codimension_sheet_n_cap_vector(profile_fn, seed=SEED, n_rounds=4)

    assert degenerate == pytest.approx([1.0] * 4, abs=1e-5)
    assert len(wired) == 4
    # Every round strictly below the n_max ceiling, i.e. beta > 0 and the
    # restart blend is no longer an identity map.
    assert all(0.0 < n < 1.0 - 1e-3 for n in wired), wired
    assert max(wired) - min(wired) > 0.0, "the vector must vary across rounds"


def test_default_path_is_byte_stable(channels) -> None:
    """No profile => constant-β path, identical to the pre-GAP-44 contract."""
    profile_fn, _cache = channels
    off = _build_lineageflow_adapter(FAMILY_ID, SEED)
    assert off is not None
    assert off.profile_residual_fn is None

    policy = _make_framework_policy(
        off, target_round=0, seed=SEED, paper_quantities=None, nfe=150
    )
    on = _build_lineageflow_adapter(FAMILY_ID, SEED, profile_residual_fn=profile_fn)
    pq = _compute_paper_quantities(on, None, round_index=0)
    wired = _make_framework_policy(
        on, target_round=0, seed=SEED, paper_quantities=pq, nfe=150
    )
    # The legacy constant-β path yields one value for every channel; the
    # paper-quantity path yields a different (smaller, n_cap-driven) one.
    legacy_values = set(policy.beta_by_channel.values())
    wired_values = set(wired.beta_by_channel.values())
    assert len(legacy_values) == 1
    assert next(iter(legacy_values)) == pytest.approx(1.0 / 6.0, abs=1e-9)
    assert wired_values != legacy_values


def test_adapter_rejects_a_non_callable_profile() -> None:
    from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter  # noqa: E402

    with pytest.raises(TypeError, match="profile_residual_fn_must_be_callable_or_none"):
        LineageFlowAdapter(
            family_id=FAMILY_ID,
            force_mode="synthetic",
            seed_offset=SEED,
            profile_residual_fn=42,  # type: ignore[arg-type]
        )
