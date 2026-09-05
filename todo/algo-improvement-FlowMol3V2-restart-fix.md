# Algorithm improvement — FlowMol3V2Adapter restart shape crash (NONCONFORMANCE_BUG #1)

**Status:** pending (NEW — Wave 32 audit gap; 5-10 LOC fix + regression test)
**Date:** 2026-09-05
**Priority:** medium (production adapter; affects FlowMol3 v2 integration)
**Depends on:** none
**Owner:** framework maintainer
**Wave:** Wave 33 (target)
**Goal:** fix the `apply_restart_distribution` shape-mismatch crash in
`FlowMol3V2Adapter` (3-channel blend math; per Wave 32 Agent C
`framework-code-review.md` §1.14 [MEDIUM-12] + Wave 29 Agent C
NONCONFORMANCE_BUG #1) + add a regression test.

## Background

Per `docs/audit/adapter-conformance-deep-dive.md` NONCONFORMANCE_BUG #1:
- `FlowMol3V2Adapter.apply_restart_distribution` crashes on shape mismatch
  between the adapter's 3-channel state bundle and the restart blend math
- 3 channels: continuous `coordinate`, continuous `charge`, categorical
  `raw_pair`
- The crash is silent (raises `ValueError` deep in the blend call stack)

Per Wave 32 Agent C (`docs/audit/framework-code-review.md` §1.14 [MEDIUM-12]):
- All three reviewed adapters (`flowmol3_v2_adapter`, `twodim_fm`,
  `lineageflow`) extract `beta_{coord,charge,raw_pair} =
  policy.beta_by_channel.get(...)` with a default of `0.5` when the
  channel is missing
- The default of `0.5` (memory_fraction=0.5) is hard-coded
- If a caller passes a policy with `beta_by_channel = {}` (empty), every
  channel gets the default — **documented behaviour but undocumented in code**

Per Wave 32 Agent A (`docs/audit/gap-audit.md` §2.3):
- **NOT MET** — bug is live; no `todo/` plan file exists

## What to do

### Phase A — Locate the crash site

1. **Read `adaptive_reflow/adapters/flowmol3_v2_adapter.py`**
   - Find the `apply_restart_distribution` method (around line 2021 per
     Wave 32 Agent C audit)
   - Find `_channel_aware_blend` (called from `apply_restart_distribution`)
   - Identify the exact shape-mismatch source

2. **Reproduce the crash** with a minimal failing fixture:
   ```python
   from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
   from adaptive_reflow.contracts import StateBundle
   from adaptive_reflow.policy import RestartPolicy

   adapter = FlowMol3V2Adapter(seed=0)
   bundle = StateBundle.empty(n_samples=1)
   policy = RestartPolicy(beta_by_channel={})  # empty → all defaults

   adapter.apply_restart_distribution(bundle, policy)  # should NOT crash
   ```

### Phase B — Implement the fix (~5-10 LOC)

**Fix option 1: shape validation pre-blend** (recommended):

```python
def apply_restart_distribution(self, bundle, policy):
    """Restart-blend the state bundle per the policy."""
    expected_channels = {"coordinate", "charge", "raw_pair"}
    actual_channels = set(bundle.channels)
    missing = expected_channels - actual_channels
    if missing:
        raise ValueError(
            f"FlowMol3V2Adapter.apply_restart_distribution: "
            f"state bundle missing channels {missing}; "
            f"expected {expected_channels}, got {actual_channels}"
        )
    # ... existing 3-channel blend math ...
```

**Fix option 2: defensive shape coercion** (more invasive):

```python
def _channel_aware_blend(self, bundle, policy):
    """Blend the 3 channels per the policy; raise on shape mismatch."""
    # Coerce each channel to the expected shape before blending
    # ...
```

**Recommendation**: Option 1 (clearer error message; minimal LOC).

### Phase C — Regression test (~30 LOC)

1. **Author `tests/test_adapters/test_flowmol3_v2_restart_shape.py`**:
   ```python
   """Regression test for NONCONFORMANCE_BUG #1: FlowMol3V2Adapter restart shape mismatch."""
   import pytest
   from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
   from adaptive_reflow.contracts import StateBundle
   from adaptive_reflow.policy import RestartPolicy

   @pytest.mark.deterministic
   def test_apply_restart_distribution_with_full_bundle() -> None:
       """Happy path: all 3 channels present → blend succeeds."""
       adapter = FlowMol3V2Adapter(seed=0)
       bundle = StateBundle.empty(n_samples=1)
       bundle = bundle.with_channels(["coordinate", "charge", "raw_pair"])
       policy = RestartPolicy(beta_by_channel={
           "coordinate": 0.7, "charge": 0.6, "raw_pair": 0.5,
       })
       result = adapter.apply_restart_distribution(bundle, policy)
       assert result is not None
       assert set(result.channels) == {"coordinate", "charge", "raw_pair"}

   @pytest.mark.deterministic
   def test_apply_restart_distribution_with_missing_channel_raises() -> None:
       """Negative path: missing channel → clear ValueError."""
       adapter = FlowMol3V2Adapter(seed=0)
       bundle = StateBundle.empty(n_samples=1)
       bundle = bundle.with_channels(["coordinate"])  # missing charge + raw_pair
       policy = RestartPolicy(beta_by_channel={"coordinate": 0.7})
       with pytest.raises(ValueError, match=r"missing channels"):
           adapter.apply_restart_distribution(bundle, policy)
   ```

2. **Run `pytest tests/test_adapters/test_flowmol3_v2_restart_shape.py -v`**
   - Both tests should pass

### Phase D — Verification

1. **Run full `pytest tests/ -v --timeout=60`** — no regression
2. **Run `python tools/capability_audit.py`** — no gate regression
3. **Run `mkdocs build --strict`** — no doc churn

### Phase E — Documentation update

1. **Update `docs/audit/adapter-conformance-deep-dive.md` §2.1** —
   mark NONCONFORMANCE_BUG #1 as RESOLVED (fixed)
2. **Add docstring note to `apply_restart_distribution`** explaining
   the channel-set requirement
3. **Update `docs/baseline-audit-report.md`** if it lists this bug

## Files affected

- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (UPDATE; ~5-10 LOC)
- `tests/test_adapters/test_flowmol3_v2_restart_shape.py` (NEW)
- `docs/audit/adapter-conformance-deep-dive.md` §2.1 (UPDATE; mark RESOLVED)
- `docs/baseline-audit-report.md` (UPDATE if applicable)

## Acceptance

- [ ] `apply_restart_distribution` raises a clear `ValueError` on missing channels
- [ ] Happy path still succeeds (all 3 channels present)
- [ ] 2 regression tests authored and pass
- [ ] `pytest tests/` still passes (no regression)
- [ ] `mkdocs build --strict` still passes
- [ ] `python tools/capability_audit.py` still passes (no gate regression)
- [ ] `docs/audit/adapter-conformance-deep-dive.md` §2.1 marks RESOLVED

## Acceptance gate

Passes if:
1. The shape-mismatch crash is replaced with a clear `ValueError`
2. Both regression tests pass deterministically (B.5 marker)
3. No regression in the full test suite

## Estimated time

~20-30 min (read + fix + test + docs).

## Related cleanup opportunities (within scope of this PR)

Per `docs/audit/framework-code-review.md` §1.14 [LOW-25]:
- All 3 restart_blend adapters truncate `restart_seed` to 32 bits
  via `int(hashlib.sha256(...).hexdigest()[:8], 16)`
- This is consistent across adapters but the seed space is much smaller
  than uint64
- **Mitigation**: use the full 64-bit digest (or document the 32-bit choice)
- **Scope decision**: include in this PR if the change is < 5 LOC; otherwise
  defer to a separate cleanup

Per `docs/audit/framework-code-review.md` §1.14 [LOW-26]:
- `flowmol3_v2_adapter` `_channel_aware_blend` blends discrete channels
  via Gumbel/Maxwell-Boltzmann resampling
- This discrete blend math is NOT exposed via the blender Protocol
- **Mitigation**: surface the categorical blend as a
  `CategoricalAwareBlender.blend(...)` entry-point
- **Scope decision**: defer to a separate PR (the categorical_blender
  refactor is a Phase 3 follow-up)