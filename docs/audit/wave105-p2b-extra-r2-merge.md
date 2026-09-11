# Wave 105 P2-B — _extra / _r2 Companion Merge Audit

**Status:** PARTIAL — 1 of 5 companions merged.
**Scope:** `adaptive_reflow/algorithm/blender.py` + `blender_extra.py`.

## Summary

Wave 105 P2-B aimed to merge 5 companion files (~3500 LOC) back into their
canonical modules:

| Companion | Canonical | LOC (before) | Status |
|---|---|---|---|
| `blender_extra.py` | `blender.py` | 580 → 36 shim | **DONE** (-544 LOC) |
| `merge_operator_extra.py` | `merge_operator.py` | 801 → 801 | DEFERRED |
| `merge_r2.py` | `merge_operator.py` | 276 → 276 | DEFERRED |
| `round2_extra.py` | `policy_driver.py` | 428 → 428 | DEFERRED |
| `scheduler_extra.py` | `scheduler/_core.py` | 1275 → 1275 | DEFERRED |
| `scheduler_r2.py` | `scheduler/_core.py` | 273 → 273 | DEFERRED |

## Accomplished — Blender merge

`adaptive_reflow/algorithm/blender.py` grew from **789 → 1226 LOC**
(+437 LOC; the canonical now owns the merged surface).
`adaptive_reflow/algorithm/blender_extra.py` shrank from **580 → 36 LOC**
(-544 LOC; now a thin re-export shim).

**Net LOC reduction:** -107 LOC for this single companion.
**Verified:** all 4 classes (`OTLinearBlender`, `MultiTemperatureDistanceDecayBlender`,
`JointOTLinearBlender`, `BarycentricBlender`) and `derive_default_memory_fraction`
remain importable via either `adaptive_reflow.algorithm.blender` or
`adaptive_reflow.algorithm.blender_extra` with identical class objects.

## Deferred — 4 companions

The remaining merges (`merge_operator_extra.py`, `merge_r2.py`,
`round2_extra.py`, `scheduler_extra.py`, `scheduler_r2.py`) require:

1. **Name collisions**: `merge_r2.py` and `merge_operator_extra.py` each
   define a `MultiSourceKalmanMergeOperator` class with incompatible
   signatures (`var1`/`var2` vs `prior_variance`/`dynamic_variances`).
   Resolving requires renaming one of them (R2 suffix), then updating
   tests that depend on the canonical name.

2. **Cross-file imports**: `round2_extra.py` imports
   `MultiChannelJitteredConstantScheduler` from `scheduler_extra.py`,
   which in turn depends on `_core.py`. The merge requires either
   inlining 1200+ LOC of scheduler code into policy_driver.py or
   breaking scheduler into a subpackage (out of P2-B scope).

3. **High LOC risk**: The remaining files total ~3053 LOC. A single
   merge mistake would silently break scheduler / merge-operator
   semantics for 1000+ tests across D.4 vectors + algorithm suites.

These deferred merges will be picked up by Wave 106 / Wave 107 with
dedicated subagent focus per file (parallel work, scoped risk).

## Verification

```
pytest tests/test_algorithm/test_blender.py -q  →  30 passed
pytest tests/test_d4_regression_vectors.py      →  30 passed
pytest tests/test_adapters/test_regression_vectors.py  →  42 passed
python -c "from adaptive_reflow.algorithm.scheduler._core import
              CosineAnnealScheduler, CodimensionSheetScheduler,
              NFEAwareMemoryScheduler"  →  PASS
python -c "from adaptive_reflow.algorithm.blender_extra import
              OTLinearBlender, BarycentricBlender,
              JointOTLinearBlender,
              MultiTemperatureDistanceDecayBlender"  →  PASS
uv run python -m mkdocs build --strict  →  PASS (14.26 s)
```

## Constraints honoured

- No scheduler / adapter / runner / merge-operator BEHAVIOR changed.
- All canonical `__all__` exports preserved (no rename of any
  scheduler / blender / merge-operator class).
- `batched_runner.py` and `perturbation.py` untouched.
- `tools/eval/` subpackage and `run_real_ckpt_eval.py` shim untouched.

---

Wave 105 P2-B (partial) — single-commit, low-risk merge.
