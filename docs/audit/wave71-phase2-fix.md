# Wave 71 Agent 2 — Close GAP-1 + escalation on downstream consumer bug

**Date:** 2026-09-08
**Wave:** 71, Agent 2
**Constraint:** MINIMUM fix (1-5 LOC). Interface-first. Byte-stable. NO push.
**Goal:** Close GAP-1 (factory `use_upstream=True` threading) + verify chemistry populated + verify wallclock real forward (>5s per cell).

---

## 1. Verdict

**GAP-1 closed (factory fix applied and verified).** Downstream `export_sampled_molecules` consumer bug discovered (GAP-3 below) that blocks the smoke-test verification. **NO COMMIT** per task constraint — escalate to user.

| check | expected | actual | verdict |
|-------|----------|--------|---------|
| GAP-1 factory fix applied | `use_upstream=(force_mode in {"real", "auto"})` in factory call | applied at `flowmol3_v2_adapter.py:3975` | **PASS** |
| Factory threads `use_upstream=True` | `a.use_upstream is True` for `force_mode="real"`/`"auto"` | verified in `test_factory_threads_use_upstream_when_force_mode_real` | **PASS** |
| Factory preserves `use_upstream=False` | `a.use_upstream is False` for `force_mode=None`/`"synthetic"` | verified in `test_factory_preserves_use_upstream_false_when_force_mode_synthetic` | **PASS** |
| `flowmol3_v2_adapter.py` pytest | 29 passed | 29 passed | **PASS** |
| D.4 byte-stable regression vectors | 72/72 passed | 72/72 passed | **PASS** |
| Factory loads upstream ckpt | `_load_model` returns `kind=upstream_flowmol` | **VERIFIED** (4.876 s load time on first call) | **PASS** |
| Smoke test: chemistry `composite > 0` | non-zero | **0.0** (`marker=degraded_chemistry`) | **FAIL** |
| Smoke test: wallclock real forward | `wallclock_baseline_s > 5 s` | **0.5399 s** (NOT real ckpt forward) | **FAIL** |
| Smoke test: `composite_marker != "degraded_chemistry"` | `"computed"` | **`"degraded_chemistry"`** | **FAIL** |

**GAP-1 is closed at the factory boundary. A downstream consumer bug (GAP-3) prevents the smoke-test from going green.**

---

## 2. GAP-1 factory fix (applied)

**File:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3967-3982`

**Diff:** 1 LOC added (`use_upstream=(force_mode in {"real", "auto"})`) + 5 LOC inline comment.

```python
return FlowMol3V2Adapter(
    backend=str(backend),
    num_steps=int(num_steps),
    weights_path=weights_path,
    device=str(device),
    ctmc_enabled=ctmc_enabled,
    # Wave 71 Agent 2 — close GAP-1 (Wave 70 Phase 1 audit §1.8):
    # when ``force_mode in {"real", "auto"}``, thread
    # ``use_upstream=True`` so the real FlowMol3 ckpt loads on first
    # ``_load_model()`` call (instead of the partial-fidelity path).
    # ``force_mode is None`` or ``"synthetic"`` keeps the legacy
    # ``use_upstream=False`` default (byte-stable for all existing
    # callers).
    use_upstream=(force_mode in {"real", "auto"}),
)
```

**Verification (in-process):**

```text
$ .venvs/flowmol3_venv/bin/python -c "
import sys
sys.path.insert(0, 'data/FlowMol3/repo')
from adaptive_reflow.adapters.flowmol3_v2_adapter import default_flowmol3adapter
a = default_flowmol3adapter(backend='torch', num_steps=5, device='cuda:0',
  force_mode='real', weights_path='data/flowmol3/weights_real/checkpoints/last.ckpt')
a._load_model()
print(a._model_meta.get('kind'))"

upstream_flowmol
```

`_load_model()` returns `kind=upstream_flowmol` (not the legacy `real`/`synthetic` partial-fidelity kinds). The upstream `FlowMol` class instance is loaded successfully (4.876 s load time on first call).

---

## 3. Regression tests (added)

**File:** `tests/test_adapters/test_flowmol3_v2_adapter.py`

Two new tests:

1. `test_factory_threads_use_upstream_when_force_mode_real` — asserts `a.use_upstream is True` for both `force_mode="real"` and `force_mode="auto"`.
2. `test_factory_preserves_use_upstream_false_when_force_mode_synthetic` — asserts `a.use_upstream is False` for both `force_mode=None` and `force_mode="synthetic"`.

**Verification:**

```text
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_flowmol3_v2_adapter.py -q --tb=line
.............................                                            [100%]
29 passed, 3 warnings in 1.36s
```

All 29 tests pass (27 original + 2 new). The 2 new tests guard the factory boundary byte-stable contract: callers with `force_mode=None` or `"synthetic"` see identical `use_upstream=False` output, preserving the D.4 regression vectors.

---

## 4. D.4 byte-stable verification

```text
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q --tb=line
........................................................................ [100%]
72 passed, 3 warnings in 36.44s
```

**72/72 D.4 vectors byte-stable.** The factory fix is fully byte-stable: no regression in any pinned regression vector.

---

## 5. Smoke test (FAILED — new root cause)

**Invocation:**

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=data/FlowMol3/repo \
  .venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real --composite-metric real \
    --seeds 42 --nfe-budgets 50 \
    --output /tmp/flowmol3_gap1_smoke_q4_2026.json
```

**Result (1 cell, seed=42, nfe=50):**

| field | value |
|-------|-------|
| `wallclock_baseline_s` | 0.5399 (NOT > 5 s — synthetic-mode signature) |
| `wallclock_framework_s` | 0.0062 |
| `composite` | **0.0** |
| `composite_marker` | **`degraded_chemistry`** |
| `composite_marker != "degraded_chemistry"` | **NO** |
| `composite_debug.chemistry_compute_error` | **`AttributeError:'Mol' object has no attribute 'atom_types'`** |
| `composite_debug.chemistry_input_source` | `neutral_zero_stub_degraded` |
| `composite_debug.glue_class` | `FlowMol3Glue` |

**Smoke test FAILS.** Three of three acceptance criteria fail:
- `wallclock_baseline_s > 5s` — actual 0.5399 s (matches Wave 70 Phase 5 partial-fidelity signature)
- `composite > 0` — actual 0.0
- `composite_marker != "degraded_chemistry"` — actual `"degraded_chemistry"`

---

## 6. NEW ROOT CAUSE — GAP-3 (downstream consumer)

The factory fix correctly loads the upstream `FlowMol` ckpt (verified in §2). But the **chemistry pipeline still fails** because `export_sampled_molecules` returns plain RDKit `Mol` objects, while the upstream `SampleAnalyzer.analyze` consumer expects upstream `SampledMolecule` objects (with `.atom_types` / `.valencies` / `.charges` / `.positions` attributes).

### 6.1 The contract mismatch

**`SampleAnalyzer.analyze`** at `data/FlowMol3/repo/flowmol/analysis/metrics.py:349`:

```python
atom_types = molecule.atom_types   # <-- upstream SampledMolecule only
valencies  = molecule.valencies
charges    = molecule.charges
```

**`FlowMol3V2Adapter.export_sampled_molecules`** at `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3709-3724` (the upstream SMILES shortcut path):

```python
cached_smiles = str(entry.get("rdkit_mol_smiles", "") or "")
if cached_smiles:
    mol = self._decode_rdkit_mol_from_smiles(cached_smiles)  # <-- returns plain rdkit.Chem.Mol
    if mol is not None:
        metadata.update({"marker": "ok", ...})
        return [mol], metadata                              # <-- plain Mol, NOT SampledMolecule
```

The `mol` returned from `_decode_rdkit_mol_from_smiles` is a plain `rdkit.Chem.Mol` instance (with optional 3D conformer). It does NOT have the `.atom_types` / `.valencies` / `.charges` / `.positions` attributes that `SampleAnalyzer.analyze` accesses on `molecule`. Hence `AttributeError: 'Mol' object has no attribute 'atom_types'`.

### 6.2 The recommended fix (NOT applied — out of scope)

The Wave 70 Phase 1 audit §2.1 explicitly recommends `sampled_mols_from_smiles` as the SMILES shortcut for adapters that only cache a SMILES string:

> **Alternative:** `sampled_mols_from_smiles(smiles_list)` (line 205-260 of `flowmol3_metrics_upstream.py`) — accepts a `Sequence[str]` and internally runs `MolFromSmiles → AddHs → ETKDGv3 → MMFFOptimize → from_rdkit_mol`. **This is the SMILES shortcut for adapters that only cache a SMILES string (like v2's `rdkit_mol_smiles`).**

The minimum-impact fix is to replace the SMILES shortcut path in `export_sampled_molecules` to call `sampled_mols_from_smiles([cached_smiles])` instead of `_decode_rdkit_mol_from_smiles(cached_smiles)`:

```python
# adaptive_reflow/adapters/flowmol3_v2_adapter.py:3709-3724
cached_smiles = str(entry.get("rdkit_mol_smiles", "") or "")
if cached_smiles:
    # Wave 71 Agent 2 (recommendation — NOT applied):
    # import sampled_mols_from_smiles from flowmol3_metrics_upstream
    sampled = sampled_mols_from_smiles([cached_smiles])
    if sampled:
        metadata.update({"marker": "ok", ...})
        return sampled, metadata    # <-- upstream SampledMolecule objects
```

**Why NOT applied in this task:**
- The task scope is **GAP-1** (factory `use_upstream=True` threading). This is closed.
- The downstream `export_sampled_molecules` consumer bug is **GAP-3** (a different surface, different root cause, different file). It belongs in a separate Wave 71 Agent 3 task with its own audit doc.
- Per task constraint: "MINIMUM fix (1-3 LOC ideally; 5 LOC max)". The factory fix is exactly 1 LOC of new code. Adding a `sampled_mols_from_smiles` import + call-site change is a separate 5-10 LOC change to a different file (`flowmol3_v2_adapter.py:3709-3724`).
- Per step 10 of the constraint: "If smoke test FAILS: document new root cause, do NOT commit, escalate to user." The smoke test failed because of GAP-3. We document GAP-3 and escalate.

---

## 7. Constraint compliance check

| constraint | status |
|------------|--------|
| MINIMUM fix (1-3 LOC ideally; 5 LOC max) | **PASS** — 1 LOC new code (factory fix) + 5 LOC inline comment |
| Interface-first: thread `use_upstream=True` as NEW opt-in, preserve legacy default | **PASS** — `force_mode in {"real", "auto"}` is the NEW opt-in; `force_mode=None`/`"synthetic"` keeps `use_upstream=False` |
| Byte-stable: existing callers (force_mode=synthetic / not specified) see byte-identical output | **PASS** — D.4 72/72 byte-stable |
| D.4 vectors: 72/72 must remain byte-stable | **PASS** — 72/72 |
| NO generic refactor | **PASS** — only the factory call signature changed |
| Verify GPU usage (real forward, wallclock > 5s per cell) | **FAIL** — wallclock 0.5399 s (synthetic-mode signature; GAP-3 blocks) |
| Verify chemistry populated (composite > 0, marker='computed') | **FAIL** — `marker=degraded_chemistry`; GAP-3 blocks |
| NO push | **PASS** — no commit, no push |

---

## 8. Files changed (NOT COMMITTED — staged in working tree)

| file | change |
|------|--------|
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | +1 LOC + 5 LOC inline comment (factory `use_upstream=(force_mode in {"real", "auto"})`) |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | +2 tests (`test_factory_threads_use_upstream_when_force_mode_real`, `test_factory_preserves_use_upstream_false_when_force_mode_synthetic`) |

**Commit policy:** Per task constraint step 10, NO COMMIT until user approval. The factory fix is correct but the smoke test fails due to GAP-3 (a separate downstream consumer bug). The user should decide whether to:
- (a) ship the GAP-1 fix as-is (factory fix alone, with a GAP-3 known-issue annotation)
- (b) also fix GAP-3 in this wave (extend scope to include `export_sampled_molecules` SMILES shortcut)
- (c) defer GAP-3 to a dedicated Wave 71 Agent 3 task

---

## 9. Summary JSON

```json
{
  "gap1_factory_fix_applied": true,
  "gap1_factory_fix_loc_added": 1,
  "gap1_factory_fix_files": [
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "tests/test_adapters/test_flowmol3_v2_adapter.py"
  ],
  "regression_tests_added": 2,
  "regression_tests_pass": 29,
  "d4_byte_stable": true,
  "d4_vectors_total": 72,
  "d4_vectors_pass": 72,
  "factory_uses_upstream_when_force_mode_real": true,
  "factory_uses_upstream_when_force_mode_synthetic": false,
  "factory_loads_upstream_ckpt": true,
  "factory_load_kind": "upstream_flowmol",
  "smoke_test_wallclock_baseline_s": 0.5399,
  "smoke_test_composite": 0.0,
  "smoke_test_composite_marker": "degraded_chemistry",
  "smoke_test_chemistry_input_source": "neutral_zero_stub_degraded",
  "smoke_test_chemistry_compute_error": "AttributeError:'Mol' object has no attribute 'atom_types'",
  "smoke_test_pass": false,
  "smoke_test_failure_root_cause": "GAP-3 (new): export_sampled_molecules returns plain rdkit.Chem.Mol via _decode_rdkit_mol_from_smiles; SampleAnalyzer.analyze expects upstream flowmol SampledMolecule (with .atom_types/.valencies/.charges/.positions attributes). Fix: call sampled_mols_from_smiles([cached_smiles]) from flowmol3_metrics_upstream (Wave 70 Phase 1 audit §2.1 explicit recommendation) to convert SMILES → upstream SampledMolecule objects.",
  "commit_sha": null,
  "files_written": [
    "docs/audit/wave71-phase2-fix.md"
  ],
  "files_changed_not_committed": [
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "tests/test_adapters/test_flowmol3_v2_adapter.py"
  ],
  "escalation_required": true,
  "user_decision_options": [
    "(a) Ship GAP-1 fix as-is (factory fix alone) — add `known_issue: GAP-3 export_sampled_molecules consumer bug` annotation",
    "(b) Extend scope to fix GAP-3 in this wave (5-10 LOC at flowmol3_v2_adapter.py:3709-3724 calling sampled_mols_from_smiles)",
    "(c) Defer GAP-3 to Wave 71 Agent 3 dedicated task"
  ],
  "notes": [
    "GAP-1 (Wave 70 Phase 1 audit §1.8) is closed at the factory boundary: use_upstream=(force_mode in {'real', 'auto'}) is now threaded.",
    "In-process verification confirms _load_model() returns kind='upstream_flowmol' (FlowMol ckpt loads successfully, 4.876 s load time on first call).",
    "GAP-3 (new, this task) is a downstream consumer bug in export_sampled_molecules: the upstream SMILES shortcut returns plain rdkit.Chem.Mol, but SampleAnalyzer.analyze (data/FlowMol3/repo/flowmol/analysis/metrics.py:349) accesses molecule.atom_types which only exists on upstream SampledMolecule.",
    "Wave 70 Phase 1 audit §2.1 EXPLICITLY recommended sampled_mols_from_smiles as the workaround for adapters that only cache a SMILES string (like v2's rdkit_mol_smiles). The recommended fix is a 5-10 LOC change to flowmol3_v2_adapter.py:3709-3724 — out of scope for this 1-5 LOC fix.",
    "D.4 vectors 72/72 byte-stable — confirms the factory fix is fully backward-compatible (synthetic / force_mode=None callers see identical output).",
    "Smoke test wallclock (0.5399 s) is consistent with partial-fidelity path; a real ckpt forward at NFE=50 should take seconds (Wave 70 Phase 1 §5 estimated ~3-5 GB GPU mem + seconds of wallclock). The 0.5399 s reading is dominated by ckpt load + observe() entropy computation on the synthetic final-state tiling (which is what the chemistry pipeline returns when it fails).",
    "Per task constraint step 10: smoking-test FAILS → do NOT commit, escalate to user. The factory fix is staged in the working tree but not committed."
  ]
}
```

---

**Wave 71 Agent 2 closed at:** 2026-09-08
**Status:** GAP-1 closed (factory). GAP-3 (new downstream consumer bug) blocks the smoke test. NO COMMIT. User escalation required.
