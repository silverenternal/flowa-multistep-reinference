# Lemma 1 — Protocol Composition Closure

**Wave:** 311 (Path A — paper-quantity / scheduler-property lemmas)
**Date:** 2026-09-23
**Author:** Wave 311 P1 Path A
**Status:** ACTIVE lemma statement + 4-step proof sketch
**Cross-reference:** `docs/audit/wave311-d1-review.md` (audit doc that motivates this lemma)

---

## Lemma 1 (Protocol Composition Closure — Path A)

### Formal Statement

Let $A$ and $B$ be two protocol classes (instantiations of
`SchedulerProtocol` — see `adaptive_reflow/algorithm/scheduler/protocols.py:157`)
that individually satisfy the three scheduler-properties
$P_{A}$ and $P_{B}$:

- **Cache coherence** — every read of a memoized quantity returns the
  same float object that the corresponding write deposited
  (`_LazyMemoCachedEvaluationCost` pattern,
  `adaptive_reflow/framework/paper_quantities_cache.py:139`).
- **Idempotence** — applying the protocol twice on the same input
  returns the same output as one application (the `clear()` /
  `reset()` cycle does not invalidate cached quantities; see
  `paper_quantities_cache.py:551`).
- **Monotonicity** — the per-round `n_cap` is non-decreasing in
  `outer_cycle_id` for constant-family schedulers, or bounded by the
  cache's monotonicity window for paper-quantity-driven families.

Then the **composition** $A \circ B$ — the wrapper scheduler with
inner scheduler $B$ — satisfies $P_A \wedge P_B$ **provided** that

   (i) $A$'s cache-write schedule is **monotonically contained** in
       $B$'s cache-read schedule: every site at which $A$ deposits a
       quantity is reached before any site at which $B$ reads it
       (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158` is the
       canonical example: the tier-aware wrapper writes tier
       assignments at `set_baseline_metrics` time, before the inner
       `CodimensionSheetScheduler` reads them at `sample` time).
   (ii) $A$'s **idempotence radius** is at least as large as $B$'s
       monotonicity window: re-applying $A$ within the same window
       cannot invalidate a quantity that $B$ still considers
       monotonic.

### Proof Sketch (4 steps)

**Step 1 — Cache coherence preserved.**
By hypothesis (i), every cache-write event $w \in W_A$ precedes every
cache-read event $r \in R_B$ in the composition's call order (the
wrapper's `sample` method delegates to the inner scheduler after
its own tier-assignment writes). Because $A$ writes first, the
`PaperQuantitiesCache.get()` method (line 173 of
`paper_quantities_cache.py`) finds the slot in the `_value` state
rather than the `_NOT_COMPUTED` sentinel. The cache's lazy-memo
contract therefore holds for the composition: $B$'s reads see exactly
the floats $A$ deposited, and the floats are bit-identical to those
$B$ would have computed alone (the wrapper never re-runs the
producer callable — it only re-uses $A$'s outputs).

**Step 2 — Idempotence preserved.**
Apply the induction on each component separately. For $A$: re-invoking
$A$ on identical inputs returns identical outputs (idempotence of
$A$). For $B$: the same holds by hypothesis. The composition
$A \circ B$ is idempotent because (a) $A$'s second invocation
produces the same wrapper state as the first, so $B$ receives the
same input it received the first time; (b) $B$'s second invocation
on that same input produces the same output as the first. The
`reset()` / `clear()` boundary does not invalidate this argument
because `PaperQuantitiesCache.clear()` preserves the four memo slots
(line 551: "does not drop the cached quantities").

**Step 3 — Monotonicity preserved.**
If $A$ is monotonically non-decreasing in its input (constant
family: `outer_cycle_id` is the only input, and `n_cap` is fixed),
and $B$ is monotonically non-decreasing in its input (paper-
quantity family: `n_cap_base(r)` is bounded by the cache's
monotonicity window, see `tier_aware.py:158` and the `easy_tier_nfe_
reduction_factor` default of `1.0`), then $A \circ B$'s output is
the wrapper's monotonically-bounded output composed with $B$'s
monotonically-bounded output. By hypothesis (ii), the wrapper's
idempotence radius covers $B$'s monotonicity window, so $B$'s
monotonicity is not invalidated by re-application of $A$.

**Step 4 — Conclusion by transitivity.**
$P_A \wedge P_B$ holds on the composition: cache coherence (Step 1),
idempotence (Step 2), and monotonicity (Step 3). The three properties
are individually sufficient for the engine's per-round scheduling
contract (`SchedulerProtocol.sample` at line 191 of `protocols.py`
and `CodimensionSheetScheduler.sample`'s downstream use), so the
composition preserves the engine-visible behaviour of either
component taken alone. ∎

### Why this lemma matters for Path A

Path A (paper-quantity / scheduler-property lemmas) needs a closure
result because the framework's R6 tier-aware scheduler is precisely
a composition of $A$ = `TierAwareCodimensionSheetScheduler` and $B$
= `CodimensionSheetScheduler`. The lemma guarantees that the
tier-aware wrapper does not invalidate any property the inner
scheduler guarantees — which is the property the engine relies on
when it routes per-round schedules into the protocol-quantity
path. Wave 311's D+1 audit doc (`docs/audit/wave311-d1-review.md`)
documents the line-number drift that this lemma's proof prevents
in future waves: a wrapper that silently broke cache coherence
would surface as audit-doc drift on the wrapper's `__init__` /
`sample` boundary, not as a state-machine violation.

### Source code anchors (verbatim)

- `adaptive_reflow/algorithm/scheduler/protocols.py:157` —
  `SchedulerProtocol` runtime-checkable Protocol class (the class $A$
  and $B$ conform to).
- `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` —
  `TierAwareCodimensionSheetScheduler` (the canonical $A \circ B$
  composition).
- `adaptive_reflow/framework/paper_quantities_cache.py:139` —
  `_LazyMemoCachedEvaluationCost` (the cache-coherence slot used in
  Step 1).
- `adaptive_reflow/framework/paper_quantities_cache.py:551` —
  `PaperQuantitiesCache.clear()` (the idempotence-preserving
  boundary used in Step 2).
- `adaptive_reflow/algorithm/policy_driver.py:181` —
  `PolicyDriverProtocol` (sister protocol used in the Lemma 2 /
  Lemma 3 stack; referenced for context, not invoked by Lemma 1).
- `adaptive_reflow/contracts/state_machine.py:828–856` — state-machine
  dispatch (the byte-determinism hook of Lemma 2; referenced here
  to anchor the lemma trio).

---

## Lemma 2 + Lemma 3 (Forward References)

This document ships Lemma 1 of the Path A lemma trio. Lemma 2
(state-machine byte-determinism) and Lemma 3 (ledger tamper-evidence)
are slated for Wave 312 / Wave 313 insertions. The protocol-
composition closure proven here is a prerequisite for Lemma 2
(state-machine hooks are called from inside protocol compositions)
and independent of Lemma 3 (which addresses ledger invariants
outside the protocol stack).