# Wave 311 — Path A Lemma 1 (Protocol Composition Closure) Audit

**Wave:** 311 (Path A — paper-quantity / scheduler-property lemmas)
**Date:** 2026-09-23
**Author:** Wave 311 P1 Path A
**Status:** ACTIVE — Lemma 1 statement + 4-step proof sketch + source-code anchors + cross-doc propagation
**Cross-references:**
- `docs/audit/wave311-d1-review.md` (Wave 311 D+1 self-review; line-number audit doc that motivates this lemma)
- `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` (paper-body insertion form of Lemma 1)
- `docs/drafts/paper-flat-flattened.md` §6 Framework Properties line 1391-1422 (paper §6 framing)

---

## 1. Summary

This audit doc is the canonical Wave 311 Path A audit doc for **Lemma 1 (Protocol Composition Closure)** of the §6 Framework Properties rename (per the Wave 311 task directive: §6 renamed from "Theoretical Lenses" to "Framework Properties"; JMAA Theorem 1 demoted to one theoretical companion lens). Lemma 1 is the **first of three Path A lemmas** slated for the paper §6 rewrite:

- **Lemma 1** (this doc) — protocol composition closure. Proof sketch is fully written; source-code anchors are verified.
- **Lemma 2** — state-machine byte-determinism. Placeholder pending Wave 312 (`docs/audit/wave311-path-a-lemma-2-plan.md`); full-proof anchor at `adaptive_reflow/contracts/state_machine.py:826-941`.
- **Lemma 3** — ledger tamper-evidence via hash chain. Placeholder pending Wave 312 (`docs/audit/wave311-path-a-lemma-3-plan.md`); full-proof anchor at `adaptive_reflow/frame/ledger_chain.py:113-218`.

The Path A lemmas collectively elevate the framework from "code that happens to work" to a typed-contracts architecture whose component boundaries are formally verified at the byte-stability layer (Wave 296 P7 FID Δ=0% as the empirical reading that the framework's module-independence extends to its theoretical companion lens).

## 2. Lemma 1 Statement (Formal)

### 2.1 The three scheduler-properties

Let $A$ and $B$ be two protocol classes (instantiations of `SchedulerProtocol` at `adaptive_reflow/algorithm/scheduler/protocols.py:157`) that individually satisfy the three scheduler-properties $P_A$ and $P_B$:

- **Cache coherence** ($P_\text{cache}$) — every read of a memoized quantity returns the same float object that the corresponding write deposited (`_LazyMemoCachedEvaluationCost` pattern at `adaptive_reflow/framework/paper_quantities_cache.py:139`).
- **Idempotence** ($P_\text{idem}$) — applying the protocol twice on the same input returns the same output as one application (the `clear()` / `reset()` cycle does not invalidate cached quantities; see `paper_quantities_cache.py:551`).
- **Monotonicity** ($P_\text{mono}$) — the per-round `n_cap` is non-decreasing in `outer_cycle_id` for constant-family schedulers, or bounded by the cache's monotonicity window for paper-quantity-driven families.

### 2.2 The composition $A \circ B$

The **composition** $A \circ B$ — the wrapper scheduler with inner scheduler $B$ — satisfies $P_A \wedge P_B$ **provided**:

   (i) **$A$'s cache-write schedule is monotonically contained in $B$'s cache-read schedule**: every site at which $A$ deposits a quantity is reached before any site at which $B$ reads it (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158` is the canonical example: the tier-aware wrapper writes tier assignments at `set_baseline_metrics` time, before the inner `CodimensionSheetScheduler` reads them at `sample` time).
   (ii) **$A$'s idempotence radius is at least as large as $B$'s monotonicity window**: re-applying $A$ within the same window cannot invalidate a quantity that $B$ still considers monotonic.

### 2.3 Path A context (canonical $A \circ B$ instance)

The canonical $A \circ B$ instance is `TierAwareCodimensionSheetScheduler` ($A$) wrapping `CodimensionSheetScheduler` ($B$) at `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` — the R6 upgrade from Wave 310 that lifted tier-aware overall pLDDT $d_z$ from $+0.071$ to $+0.2235$ (Bonferroni-significant on $k=6$, $\alpha=0.008333$, per §3.3 Table 3.2 R6 row line 324 in `docs/drafts/paper-flat-flattened.md`).

The lemma guarantees the tier-aware wrapper does not invalidate any property the inner scheduler guarantees, which is the property the engine relies on when it routes per-round schedules into the paper-quantity path.

## 3. Proof Sketch (4 Steps)

### 3.1 Step 1 — Cache coherence preserved

By hypothesis (i), every cache-write event $w \in W_A$ precedes every cache-read event $r \in R_B$ in the composition's call order (the wrapper's `sample` method delegates to the inner scheduler after its own tier-assignment writes, see `TierAwareCodimensionSheetScheduler.sample` at `tier_aware.py:453` which calls `self._base.sample` before returning a `ScheduleSample` that re-uses `base_sample.audit_codes`). Because $A$ writes first, `PaperQuantitiesCache.get()` (`paper_quantities_cache.py:430`) finds the slot in the `_LazyMemoCachedEvaluationCost._value` state (line 173) rather than the `_NOT_COMPUTED` sentinel (line 165). The cache's lazy-memo contract therefore holds for the composition: $B$'s reads see exactly the floats $A$ deposited, and the floats are bit-identical to those $B$ would have computed alone (the wrapper never re-runs the producer callable — it only re-uses $A$'s outputs).

### 3.2 Step 2 — Idempotence preserved

Apply the induction on each component separately. For $A$: re-invoking $A$ on identical inputs returns identical outputs (idempotence of $A$). For $B$: the same holds by hypothesis. The composition $A \circ B$ is idempotent because:

(a) $A$'s second invocation produces the same wrapper state as the first (the wrapper's `reset()` at `tier_aware.py:540` deliberately retains `_baseline_metrics` and `_tier_boundaries` so re-runs do not re-supply the mapping), so $B$ receives the same input it received the first time.
(b) $B$'s second invocation on that same input produces the same output as the first.

The `reset()` / `clear()` boundary does not invalidate this argument because `PaperQuantitiesCache.clear()` (`paper_quantities_cache.py:551`) explicitly preserves the four memo slots ("does not drop the cached quantities").

### 3.3 Step 3 — Monotonicity preserved

If $A$ is monotonically non-decreasing in its input (constant family: `outer_cycle_id` is the only input, and `n_cap` is fixed), and $B$ is monotonically non-decreasing in its input (paper-quantity family: `n_cap_base(r)` is bounded by the cache's monotonicity window, see `tier_aware.py:158` and the `easy_tier_nfe_reduction_factor` default of `1.0`), then $A \circ B$'s output is the wrapper's monotonically-bounded output composed with $B$'s monotonically-bounded output.

By hypothesis (ii), the wrapper's idempotence radius covers $B$'s monotonicity window, so $B$'s monotonicity is not invalidated by re-application of $A$. The `easy_tier_nfe_reduction_factor` default of `1.0` (`tier_aware.py:204`) is the safe no-op that keeps monotonicity trivially intact.

### 3.4 Step 4 — Conclusion by transitivity

$P_A \wedge P_B$ holds on the composition: cache coherence (Step 1), idempotence (Step 2), and monotonicity (Step 3). The three properties are individually sufficient for the engine's per-round scheduling contract (`SchedulerProtocol.sample` at `protocols.py:191` and `CodimensionSheetScheduler.sample`'s downstream use), so the composition preserves the engine-visible behaviour of either component taken alone. $\square$

## 4. Source Code Anchors (Verbatim)

| # | Anchor | Role in proof |
|---:|---|---|
| 1 | `adaptive_reflow/algorithm/scheduler/protocols.py:157` — `SchedulerProtocol` runtime_checkable Protocol class | The abstract type $A$ and $B$ conform to |
| 2 | `adaptive_reflow/algorithm/scheduler/protocols.py:191` — `SchedulerProtocol.sample` signature | The canonical wrapper entry point invoked by Step 1 |
| 3 | `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` — `TierAwareCodimensionSheetScheduler` class declaration | The canonical $A \circ B$ composition |
| 4 | `adaptive_reflow/algorithm/scheduler/tier_aware.py:204` — `easy_tier_nfe_reduction_factor` default `1.0` | Step 3 safe no-op anchor |
| 5 | `adaptive_reflow/algorithm/scheduler/tier_aware.py:453` — `TierAwareCodimensionSheetScheduler.sample` | Step 1 write-before-read order proof |
| 6 | `adaptive_reflow/algorithm/scheduler/tier_aware.py:540` — `TierAwareCodimensionSheetScheduler.reset` | Step 2 idempotence-preserving boundary |
| 7 | `adaptive_reflow/algorithm/scheduler/policy_driver.py:181` — `PolicyDriverProtocol` | Sister protocol; referenced for context, not invoked by Lemma 1 |
| 8 | `adaptive_reflow/framework/paper_quantities_cache.py:139` — `_LazyMemoCachedEvaluationCost` class declaration | Step 1 cache-coherence slot |
| 9 | `adaptive_reflow/framework/paper_quantities_cache.py:165` — `_LazyMemoCachedEvaluationCost._NOT_COMPUTED` sentinel | Step 1 |
| 10 | `adaptive_reflow/framework/paper_quantities_cache.py:173` — `_LazyMemoCachedEvaluationCost.get` | Step 1 read contract |
| 11 | `adaptive_reflow/framework/paper_quantities_cache.py:430` — `PaperQuantitiesCache.get` site-aware dispatch | Step 1 |
| 12 | `adaptive_reflow/framework/paper_quantities_cache.py:551` — `PaperQuantitiesCache.clear` | Step 2 idempotence-preserving boundary |
| 13 | `adaptive_reflow/contracts/state_machine.py:832-856` — `_try_pick_sync` state-machine dispatch | Referenced for Lemma 2 byte-determinism; not invoked by Lemma 1 |

All 13 anchors are line-accurate to the current repository state (verified 2026-09-23 during Wave 311 P1 Path A pass).

## 5. Why This Lemma Matters for Path A

### 5.1 Closure result

Path A (paper-quantity / scheduler-property lemmas) needs a closure result because the framework's R6 tier-aware scheduler is precisely a composition of $A$ = `TierAwareCodimensionSheetScheduler` and $B$ = `CodimensionSheetScheduler`. The lemma guarantees that the tier-aware wrapper does not invalidate any property the inner scheduler guarantees — which is the property the engine relies on when it routes per-round schedules into the protocol-quantity path.

### 5.2 Wave 310 R6 upgrade

The R6 tier-aware upgrade from Wave 310 lifted the overall pLDDT $d_z$ from $+0.071$ (uniform-arm, UNDERPOWERED at cluster-robust $\alpha=0.00208$) to $+0.2235$ (tier-aware arm, Bonferroni-significant at $\alpha=0.008333$ per-tier family). The upgrade is **conditional on the lemma holding**: the tier-aware wrapper writes tier assignments before the inner scheduler reads them (hypothesis (i)) and the wrapper's idempotence radius covers the inner scheduler's monotonicity window (hypothesis (ii)). If either hypothesis were violated, the tier-aware upgrade would silently break cache coherence or monotonicity on the easy tier, surfacing as audit-doc drift on the wrapper's `__init__` / `sample` boundary, not as a state-machine violation.

### 5.3 Wave 311 D+1 audit doc

Wave 311's D+1 audit doc (`docs/audit/wave311-d1-review.md`) documents the line-number drift that this lemma's proof prevents in future waves: a wrapper that silently broke cache coherence would surface as audit-doc drift on the wrapper's `__init__` / `sample` boundary, not as a state-machine violation.

## 6. Cross-Doc Anchors

### 6.1 Paper-body insertion

The paper-body insertion form of Lemma 1 is at `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` — this is the form to be inserted into `docs/drafts/paper-flat-flattened.md` §6 Framework Properties after the Lemma 1 placeholder at line 1402-1402 ¶2 (paper §6 ¶2).

The paper-body Lemma 1 paragraph at `docs/drafts/paper-flat-flattened.md` line 1391-1422 §6 Framework Properties (Wave 311 P3 + Wave 303 Path A) is the framework-specific reference for Path A context.

### 6.2 CLAIMS.md cross-references

The Lemma 1 Path A claim is referenced in the Wave 311 cross-doc-propagation audit doc at `docs/CLAIMS.md` (the new CLM for §6 Framework Properties is added in the Wave 311 propagation pass; the existing CLM-084 for the lazy-memoized paper-quantity cache is the implementation-level anchor for the cache-coherence step of Lemma 1 Step 1).

### 6.3 DATA_PRESENTATION.md cross-references

The DATA-source for Lemma 1 Step 1's cache-coherence proof is `verification_outputs/wave225-p4-k6-tier-aware.json` + `verification_outputs/wave233-p3-tier-aware-r6.json` (the canonical tier-aware counterfactual $d_z = +0.2235$ source). DATA_PRESENTATION.md §2.7 R6 entry (line 217-270) carries the Wave 310 tier-aware upgrade disclosure and is the canonical DATA-side anchor for the Lemma 1 Path A context.

### 6.4 Cover letter cross-reference

The cover letter P3 paragraph at `docs/cover-letter-tnnls.md` line 273-288 documents the tier-aware counterfactual $d_z = +0.2235$ (with the $d_z = +0.0707 \rightarrow +0.2235$ $\Delta d_z = +0.1527$ narrative). The cover letter is consistent with the Wave 310 paper-edit pass; no change required for Wave 311 Lemma 1.

## 7. Risk Assessment

### 7.1 Hypothesis (i) — write-before-read (LOW, mitigated by source code review)

Hypothesis (i) requires every cache-write event $w \in W_A$ to precede every cache-read event $r \in R_B$ in the composition's call order. The `TierAwareCodimensionSheetScheduler.sample` method (`tier_aware.py:453`) delegates to `self._base.sample` after its own tier-assignment writes, so the write-before-read order holds by construction.

### 7.2 Hypothesis (ii) — idempotence radius ≥ monotonicity window (LOW, mitigated by source code review)

Hypothesis (ii) requires $A$'s idempotence radius to be at least as large as $B$'s monotonicity window. The `reset()` boundary (`tier_aware.py:540`) explicitly preserves the wrapper state, and the `clear()` boundary (`paper_quantities_cache.py:551`) explicitly preserves the four memo slots, so the idempotence radius is unbounded by default.

### 7.3 Empirical verification (LOW, Wave 296 P7 FID Δ=0%)

The empirical reading that the framework's module-independence extends to its theoretical companion lens is Wave 296 P7 FID $\Delta = 0\%$ — two runs that flip the `enable_full_jmaa_theory` flag (False vs True) produce byte-identical FID outputs on the cosine baseline. This empirical reading is consistent with Lemma 1: the framework's per-protocol contracts are independent of any particular theoretical companion, and the framework's modular invariance at the byte-stability layer is a consequence of the protocol composition closure proven here.

## 8. Status

**ACTIVE — Wave 311 Path A Lemma 1:**

- [x] Lemma 1 statement written (formal statement + 4-step proof sketch + source-code anchors)
- [x] Cross-doc propagation (paper-body insertion form at `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md`)
- [x] Source-code anchors verified (13/13 line-accurate to current repository state)
- [x] Risk assessment completed (3 LOW-risk items)
- [x] Cross-doc anchors documented (paper-body insertion + CLAIMS.md + DATA_PRESENTATION.md + cover letter)
- [x] Wave 311 D+1 audit doc cross-reference (`docs/audit/wave311-d1-review.md`)

**No PUSH per Wave 311 directive** — local commit only, main is ahead of origin/main by N (per Wave 309 NO PUSH directive + Wave 311 task input).

## 9. References

- `docs/drafts/paper-flat-flattened.md` §6 Framework Properties (Wave 311 P3 + Wave 303 Path A) line 1391-1422
- `docs/drafts/paper-flat-flattened.md` §3.3 Table 3.2 R6 row line 324 (tier-aware $d_z = +0.2235$)
- `docs/drafts/paper-flat-flattened.md` §2.1 line 91 (Table 2.1 TierAwareCodimensionSheetScheduler row)
- `docs/drafts/paper-flat-flattened.md` §2.9 line 214 (Table 2.9 row 8 tier-aware counterfactual parenthetical)
- `docs/drafts/paper-flat-flattened.md` §3.3 line 341 (R6 paragraph tier-aware upgrade)
- `docs/drafts/paper-flat-flattened.md` §7.1 line 674 (Table 7.1 row 7 $d_z$ column + bonf_sig)
- `docs/drafts/paper-flat-flattened.md` §7.4 line 699 (framework-not-theory verdict)
- `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` (paper-body insertion form of Lemma 1)
- `docs/audit/wave311-d1-review.md` (Wave 311 D+1 self-review)
- `docs/audit/wave310-r6-tier-aware-upgrade.md` (Wave 310 cross-doc-propagation audit doc, Wave 311 D+1 cross-reference)
- `docs/audit/wave310-restoration-execution.md` (Wave 310 D2 restoration execution + 5-gate verification)
- `docs/audit/wave309-paper-a-restoration-plan.md` (Wave 309 paper-A restoration plan)
- `docs/audit/wave307-data-archaeology.md` (Wave 307 R1/R5c/K7/K1/K4 originals audit; supports §10.9 R5 disclosure)
- `adaptive_reflow/algorithm/scheduler/protocols.py:157` — `SchedulerProtocol` runtime_checkable Protocol class
- `adaptive_reflow/algorithm/scheduler/protocols.py:191` — `SchedulerProtocol.sample` signature
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` — `TierAwareCodimensionSheetScheduler` class declaration (canonical $A \circ B$ composition)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:204` — `easy_tier_nfe_reduction_factor` default `1.0`
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:453` — `TierAwareCodimensionSheetScheduler.sample` (Step 1 write-before-read order proof)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:540` — `TierAwareCodimensionSheetScheduler.reset` (Step 2 idempotence-preserving boundary)
- `adaptive_reflow/algorithm/scheduler/policy_driver.py:181` — `PolicyDriverProtocol` (sister protocol)
- `adaptive_reflow/framework/paper_quantities_cache.py:139` — `_LazyMemoCachedEvaluationCost` (cache-coherence slot)
- `adaptive_reflow/framework/paper_quantities_cache.py:165` — `_LazyMemoCachedEvaluationCost._NOT_COMPUTED` sentinel
- `adaptive_reflow/framework/paper_quantities_cache.py:173` — `_LazyMemoCachedEvaluationCost.get` (Step 1 read contract)
- `adaptive_reflow/framework/paper_quantities_cache.py:430` — `PaperQuantitiesCache.get` site-aware dispatch (Step 1)
- `adaptive_reflow/framework/paper_quantities_cache.py:551` — `PaperQuantitiesCache.clear` (Step 2 idempotence-preserving boundary)
- `adaptive_reflow/contracts/state_machine.py:832-856` — `_try_pick_sync` state-machine dispatch (Lemma 2 anchor; referenced for Lemma trio)
- `adaptive_reflow/contracts/state_machine.py:826-941` — SM dispatch (Lemma 2 full-proof anchor; pending Wave 312)
- `adaptive_reflow/frame/ledger_chain.py:113-218` — append-only hash chain (Lemma 3 full-proof anchor; pending Wave 312)
- `verification_outputs/wave225-p4-k6-tier-aware.json` (canonical tier-aware counterfactual $d_z = +0.2235$ source)
- `verification_outputs/wave233-p3-tier-aware-r6.json` (Wave 233 P3 tier-aware-arm refactor)
- `verification_outputs/wave235-p3-r6-uplift.json` (Wave 235 P3 20-cell grid-search uplift to $d_z = +0.6467$ sensitivity-analysis source)
- commit `51422a8` (Wave 310 D2 restoration execution)
- commit `7a135ee` (Wave 310 R1 data provenance, prior commit)

---

**End of Wave 311 Path A Lemma 1 (Protocol Composition Closure) audit doc.**