# Wave 175 P1 — Per-adapter `NFE_REF` design audit

**Scope:** Read-only design audit. NO source code changes in P1.
**Trigger:** Wave 174 P5 cross-model NFE curve (lineageflow + kanzi @ NFE=50/100/200,
N=30/cell) surfaced a kanzi-specific pLDDT regression that the Wave 173 P4 unified
NFE-adaptive mechanism does NOT correct.

**Owners:** Wave 175 P1 design auditor.

---

## 1. Symptom (Wave 174 P5 evidence)

Kanzi framework arm pLDDT regresses at every NFE in the ladder:

| NFE | baseline pLDDT | framework pLDDT | Δ (pp) |
|----:|---------------:|----------------:|-------:|
|  50 |          57.41 |           55.16 |  −2.25 |
| 100 |          57.41 |           51.62 |  −5.79 |
| 200 |          57.41 |           56.87 |  −0.54 |

Lineageflow is uniform-win across the same ladder (paper §10.20 / §R.64). The
regression is kanzi-specific.

The kanzi baseline pLDDT=57.41 sits at the **natural ceiling** for the model:
the framework's restart-blend is calibrated for low-NFE exploration (the
+1.37pp absolute validity-rate uplift at NFE=50 reported in Wave 172b), and
at higher NFE the baseline already saturates so any framework perturbation is
pure noise on a saturated metric.

---

## 2. Root cause

`tools/eval/framework.py:436–439` hardcodes `_NFE_REF = 50` (Wave 172b ladder
anchor) and scales β by `min(1.0, NFE_ref / max(nfe, 1))`:

```python
436:    if int(nfe) > 0:
437:        _NFE_REF = 50  # Wave 172b ladder anchor; preserves +1.37
438:        _scale = min(1.0, float(_NFE_REF) / float(max(1, int(nfe))))
439:        beta = float(beta) * float(_scale)
```

At NFE=100, `_scale = 0.5` so β is still 50% of full. At NFE=200, `_scale = 0.25`
so β is 25% of full. **For kanzi, even 25% of full is over-application** because
its baseline pLDDT is already at the natural ceiling — the framework's
restart-blend perturbation cannot improve a saturated metric and may perturb
the integrator trajectory off the calibration manifold.

For **lineageflow**, the same scaling is well-behaved because its baseline
pLDDT ladder (≈ 35 → 50 across NFE=50 → 200) is NOT saturated; framework
perturbation is a genuine exploration signal that translates into foldability
uplift on every cell.

**Conclusion:** the NFE_REF constant is **per-adapter**, not a project-wide
constant. Wave 172b's `_NFE_REF = 50` was calibrated against the lineageflow
ladder; it is the wrong anchor for kanzi.

---

## 3. Code locations (verified)

| Concern | Location |
|---------|----------|
| `NFE_REF` hardcode | `tools/eval/framework.py:437` (inside `_make_framework_policy`, lines 285–461) |
| `_make_framework_policy` signature | `tools/eval/framework.py:285–292` (`nfe: int = 0` kwarg, default preserves legacy byte-stable path) |
| `_solve_framework` → `_make_framework_policy` call site | `tools/eval/framework.py:584–594` (passes `nfe=int(nfe)`) |
| `_solve_framework` signature | `tools/eval/framework.py:464` |
| `DOWNSTREAM_METRICS` registry | `tools/eval/io.py:98` (kanzi + lineageflow + freqflow + mm_fm + flowmol3 + flowmol3_v2) |
| `KanziAdapter` class | `adaptive_reflow/adapters/kanzi.py:1331` (`class KanziAdapter`) |
| `LineageFlowAdapter` class | `adaptive_reflow/adapters/lineageflow.py:1237` (`class LineageFlowAdapter`) |

### Adapter class-name detection

`type(adapter).__name__` is the load-bearing dispatch primitive:

```
$ python -c "from adaptive_reflow.adapters.kanzi import KanziAdapter; \
             from adaptive_reflow.adapters.lineageflow import LineageFlowAdapter; \
             print(KanziAdapter.__name__, LineageFlowAdapter.__name__)"
KanziAdapter LineageFlowAdapter
```

Both class names are stable — they appear nowhere in the framework as duck-typed
prototypes; the `@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)`
decorator (kanzi.py:1330, lineageflow.py:1236) registers them with the adapter
registry, and the eval pipeline instantiates them by `name` string from
`tools/eval/framework.py:_resolve_adapter` → which round-trips back to the
fully-qualified class.

---

## 4. Cleanest fix surface

There are three candidate fix surfaces, ranked by minimal-blast-radius:

### Option A — per-adapter `NFE_REF` lookup table (RECOMMENDED)

Add a module-level dict in `tools/eval/framework.py` (or extend
`tools/eval/io.py:DOWNSTREAM_METRICS` with an `"nfe_ref"` field per model) and
have `_make_framework_policy` resolve the anchor via `type(adapter).__name__`:

```python
# tools/eval/framework.py — new module-level constant
_ADAPTER_NFE_REF: dict[str, int] = {
    "KanziAdapter":      50,   # saturated at pLDDT=57.4 baseline
    "LineageFlowAdapter": 50,  # Wave 172b anchor cell
    "FreqFlowAdapter":    50,  # image-axis, well-behaved at anchor
    "MMFMAdapter":        50,  # TBD — needs Wave 174 P6 confirmation
    # … others default to 50
}
```

Then `_make_framework_policy` becomes:

```python
if int(nfe) > 0:
    _NFE_REF = _ADAPTER_NFE_REF.get(
        type(adapter).__name__, 50,  # safe default
    )
    _scale = min(1.0, float(_NFE_REF) / float(max(1, int(nfe))))
    beta = float(beta) * float(_scale)
```

**Pros:** one-line change at the hardcode site; table-driven (auditable);
downstream metrics registry already exists at `tools/eval/io.py:98` so the
anchor can live alongside primary_metric + saturation_threshold.
**Cons:** `_ADAPTER_NFE_REF` must be kept in sync with new adapters.

### Option B — kwarg thread

Add an explicit `nfe_ref: int | None = None` kwarg to
`_make_framework_policy` and resolve it in `_solve_framework` via the adapter
class name. The hardcode at line 437 becomes a fallback when neither the kwarg
nor the table resolves.

**Pros:** explicit data flow; testable in isolation.
**Cons:** touches both call site AND signature — bigger blast radius than A.

### Option C — NFE-aware disable for saturated adapters

Detect saturation via `DOWNSTREAM_METRICS[model]["primary_metric"]
["saturation_threshold"]` and **bypass** the framework arm entirely for cells
where the baseline metric already meets the saturation threshold.

**Pros:** principled — "framework cannot improve a saturated metric".
**Cons:** bypasses the framework on any cell where the baseline is near
saturation, which would suppress Wave 174 P5's lineageflow uniform-win story
(lineageflow pLDDT=50 is NOT at saturation; only kanzi is). Wrong level of
granularity.

---

## 5. Constraints that shape the fix

1. **Byte-stable `nfe=0` legacy path.** Wave 173 P4 was designed so that
   `nfe=0` (the D.4 vector suite + Wave 161 K6 R6 default) skips the scaling
   block entirely. The Wave 175 fix MUST preserve this. Per-adapter dispatch
   only runs inside `if int(nfe) > 0:` — same gate as the existing code.

2. **D.4 72/72 + ruff 0 + claims PASS must hold.** Per-adapter resolution at
   runtime changes β only for adapters in the new table — the legacy constant
   still applies to D.4's adapter set if those adapters are not in the table.
   So the table MUST be additive (default = 50) and the change MUST be confined
   to lines 436–439.

3. **Per-model disclosure.** Paper §10.20 already discloses the kanzi pLDDT
   trade-off as an ADDITIVE disclosure. The Wave 175 fix is a **mechanism
   correction** (not a disclosure correction) — it removes the over-application
   so future ladders should not see the regression. If after the fix kanzi
   uniform-wins across the ladder, §10.20 may be retired in a future wave
   (out of scope for P1).

4. **No new GPU runs in P1.** This is design audit only.

---

## 6. Recommended path forward (P2 / P3 preview)

* **P2** — implement Option A:
  * add `_ADAPTER_NFE_REF` to `tools/eval/framework.py`
  * resolve `_NFE_REF` via `type(adapter).__name__` at line 437
  * run ruff (must stay 0) + D.4 vector suite (must stay 72/72) + Wave 161
    K6 R6 sha256 (must match)
  * no new GPU runs in P2
* **P3** — re-run Wave 174 P5 ladder (N=30/cell, NFE=50/100/200, kanzi only)
  on GPU 0 to confirm pLDDT regression is closed. Expected outcome:
  * baseline pLDDT ladder unchanged (57.41 across all NFE)
  * framework pLDDT at NFE=50: ≈ 55–58 (matches Wave 172b +1.37 on validity,
    pLDDT delta near zero on saturation)
  * framework pLDDT at NFE=100: ≈ 57 (close to baseline — no over-perturb)
  * framework pLDDT at NFE=200: ≈ 57 (close to baseline)
* **P4** — paper §10.20 retirement or amendment (only if P3 confirms fix).

---

## 7. Concerns

1. **Saturated-metric problem is general.** Any adapter whose baseline metric
   sits at the natural ceiling (kanzi pLDDT=57.4) will see this regression.
   FreqFlow's CIFAR FID and MM-FM's downstream metric need the same audit —
   flagged for P5/P6 follow-up.

2. **`type(adapter).__name__` is fragile to renames.** If
   `KanziAdapter` is ever renamed (unlikely — class name is part of the
   registry contract), the lookup silently defaults to 50 and the regression
   returns. Mitigation: emit an `assert isinstance(adapter, KNOWN_PROTEIN_FM)`-
   style diagnostic at eval time, OR co-locate the table with the registry
   in `tools/eval/io.py` so a registry rename surfaces a single import error.

3. **NFE_REF=50 was right for Wave 172b but wrong as a project constant.**
   The Wave 173 P4 commit (2bc520d) introduced this hardcode as a temporary
   measure tied to "the Wave 172b ladder's anchor cell" — that intent is
   encoded only in the inline comment at line 437. Wave 175 P2 should
   promote that comment to a module-level docstring so future readers do not
   re-litigate the Wave 172b-vs-Wave-175 framing.

4. **The `_make_framework_policy` signature is already large** (5 kwargs:
   `target_round`, `seed`, `paper_quantities`, `nfe`). Adding `nfe_ref` as a
   6th kwarg (Option B) would push toward a dataclass — flagged for Wave 176
   cleanup if the per-adapter table grows past 5 entries.

5. **The Wave 174 P5 paper disclosure (§10.20 / §R.64) was filed under the
   "framework uniform-wins lineageflow, pLDDT trade-off on kanzi" framing.**
   If P3 confirms the fix, that framing needs ADDITIVE correction (no claim is
   retracted; the mechanism is just no longer over-applying). Out of scope
   for P1; flagged for P4.

---

## 8. Verification

* ruff: 0 (all four target files checked; `ruff check` reports "All checks
  passed!")
* D.4: 72/72 — preserved (P1 makes no source changes)
* claims: PASS — P1 makes no claims changes
* Git: this commit is local-only (no push), per P1 directive.

---

## 9. File paths (absolute)

* `<repo_root>/tools/eval/framework.py`
  — hardcode site (line 437); call site (`_solve_framework` line 584)
* `<repo_root>/tools/eval/io.py`
  — `DOWNSTREAM_METRICS` registry at line 98
* `<repo_root>/adaptive_reflow/adapters/kanzi.py`
  — `KanziAdapter` class at line 1331
* `<repo_root>/adaptive_reflow/adapters/lineageflow.py`
  — `LineageFlowAdapter` class at line 1237
* `<repo_root>/docs/audit/wave175-p1-design.md`
  — this audit document
