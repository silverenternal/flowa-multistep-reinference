# Wave 301 Day 2 — Path A Prose-Proof Formalization + Paper A Full Draft

**Date:** 2026-09-23
**Mode:** PLAN ONLY (READ-ONLY against source code)
**Author:** Wave 301 Day 2 execution planning agent
**Predecessor:** `docs/audit/wave301-day1-execution-plan.md` (Day 1 RESOLUTION + structure lock — must be complete before Day 2 begins)
**Input file under eventual modification:** `docs/drafts/paper-flat-flattened.md` (post-Day-1 state: ~1069 lines, 11-section Wave 299 canonical structure)
**Constraint:** Day 2 produces prose + LaTeX, NOT destructive edits; Wave 268 strict-clean applies only to deletion steps, not to §2/§8/§11 fresh-writing additions.
**Gating:** Day 2 is **gated on Day 1 completion** (RESOLUTION pass executed + structure presented to user + 5-gate suite re-baselined).

---

## 0. CRITICAL GUARD — READ BEFORE EXECUTING

**Day 2 does NOT execute until Day 1 RESOLUTION pass has produced a verified, user-sanity-checked 11-section structure.**

The Day 2 plan writes three NEW sections (§2 Related Work, §8 Reproducibility, §11 Conclusion) and inserts §3 Theoretical Guarantees prose in the main text while deferring 5-6 lemmas to supplementary. If Day 1 RESOLUTION has not run, the line-number anchors below (post-RESOLUTION target positions) will be wrong and the additions will collide with legacy content.

**Pre-execution prerequisites (all required):**

1. Day 1 RESOLUTION pass complete (`paper-flat-flattened.md` reduced to ~1069 lines, 11-section structure)
2. Day 1 5-gate baseline re-established (D.4 30/30, ruff 0, mkdocs strict 0, claims no-drift, vendored untouched)
3. Day 1 user sanity check on structure passed
4. Day 0 §6 Theoretical Lenses decision recorded (recommended: drop entirely per DeepSeek "Paper A 不包含 JMAA")
5. Day 0 §10 Future Work decision recorded (recommended: fold into §8 Limitations)
6. Day 0 figure count decision recorded (recommended: 3-4 figures + 2-3 tables for TNNLS page budget)
7. Day 0 timeline selection (8-10 day compressed vs 12-15 day full-quality)

If any of the above are missing, **STOP** and re-engage user.

---

## 1. Scope Statement (Day 2 deliverable + non-scope)

### 1.1 IN SCOPE for Day 2

**Path A prose-proof formalization** — produce 6-8 protocol algebra lemmas + 4 proof sketches, written in prose (no z3 / coq / lean), each citing the exact source-of-truth file:line as ground truth:

| Lemma / sketch | Maps to | Source-of-truth anchor |
|---|---|---|
| Lemma 1: SchedulerProtocol interface closure | protocol algebra | `adaptive_reflow/algorithm/scheduler/protocols.py:157-289` |
| Lemma 2: PolicyDriverProtocol `beta -> memory_fraction` direction (Contract 3.1) | protocol algebra | `adaptive_reflow/algorithm/policy_driver.py:181-285` |
| Lemma 3: MergeOperator bounded-update contract (P0-3 / P2-4) | protocol algebra | `adaptive_reflow/algorithm/merge/merge_operator.py:248-340` |
| Lemma 4: RestartBlenderProtocol `prior + fresh + m -> bundle` (Contract 3.1 polarity) | protocol algebra | `adaptive_reflow/algorithm/blender/blender.py:425-470` |
| Lemma 5: CapabilityToken handshake closed-set ⊆ supported_channels | cross-protocol | `adaptive_reflow/frame/engine.py:1273-1313` |
| Lemma 6: Typed four-port auto-wrap migration correctness (3-layer protocol) | cross-protocol | `adaptive_reflow/contracts/condition.py:33-507` |
| Sketch 1: State-machine byte-determinism | SM theory | `adaptive_reflow/contracts/state_machine.py:832-911` |
| Sketch 2: Ledger integrity via SHA-256 chain (fail-closed) | ledger theory | `adaptive_reflow/frame/engine.py:455-613` + `adaptive_reflow/frame/ledger_chain.py:113-218` |
| Sketch 3: CapabilityToken handshake error diagnosability | handshake theory | `adaptive_reflow/frame/engine.py:1273-1313` |

**Total: 6 lemmas + 3 proof sketches** — fits the "6-8 lemmas" estimate from Wave 300 P2 self-eval within the 12-day prose-proof budget, **compressed to a single day** at the cost of coverage depth (see §6 below).

**Fresh-writing for 3 missing sections:**

| Section | Target word count | Source-of-truth |
|---|---|---|
| §2 Related Work | 600-800 words | 3-layer prior-art: (1) FM inference acceleration (Diffusion/NFE distillation, consistency models, ReFlow/InstaFlow); (2) FM theoretical frameworks (score-SDE, flow matching OT, JMAA — as companion only); (3) typed ML system contracts (Protocols, type classes, capability-based security) |
| §8 Reproducibility | 600-800 words | SHA-256 ledger chain + D.4 30/30 byte-stability + Wave 286/290/268/296 feature inventory + vendored purity invariant |
| §11 Conclusion | 200-300 words | Restate 4-contribution summary + Paper B pointer (no JMAA theory) + adapter-coverage roadmap |

**LaTeX integration plan** (output as a sub-section of this doc, executed only on Day 4):

- IEEEtran class file `IEEEtran.cls` (TNNLS template) — `\documentclass[journal]{IEEEtran}`
- New `\newtheorem{lemma}{Lemma}` + `\newtheorem{sketch}{Proof Sketch}` environments
- Section 6 Theoretical Guarantees placement: 1.5 pages max per Wave 300 §6 verdict — mapped to **§3 Framework (formalization section)** in main text, NOT a separate §6 per DeepSeek's structure (DeepSeek renumbers Theoretical Lenses out of existence in Paper A).

### 1.2 OUT OF SCOPE for Day 2 (deferred)

- Full 6-lemma + 3-sketch LaTeX typesetting → Day 4 (IEEEtran conversion)
- Figure generation (TikZ or matplotlib figures) → Day 5
- Supplementary material prose-proofs (full Path A: 12-day target) → Day 5 supplementary expansion
- §6 Theoretical Lenses removal (Day 1 RESOLUTION already handled; Day 2 only writes §3 framework prose)
- Bibliographic entry creation (BibTeX) → Day 6 (only references actually cited in Day 2 prose)

### 1.3 Day 2 deliverable summary

- `docs/audit/wave301-day2-execution-plan.md` — THIS DOCUMENT (read-only output, never edits)
- `docs/audit/wave301-day2-lemmas.md` — 6 lemmas + 3 proof sketches in LaTeX-ready prose (~4500-5500 words; this is the prose that goes into paper §3 + supplementary)
- `docs/audit/wave301-day2-section-2.md` — §2 Related Work draft (600-800 words)
- `docs/audit/wave301-day2-section-8.md` — §8 Reproducibility draft (600-800 words)
- `docs/audit/wave301-day2-section-11.md` — §11 Conclusion draft (200-300 words)
- **Sections 6, 7, 9, 10 in this document** — execution sequencing + LaTeX integration plan + verification + risks

---

## 2. Source-of-Truth Inventory (verified at start of Day 2)

### 2.1 Protocol surface (4 protocols for algebra lemmas)

| Protocol | File:line | Method signatures (informal) |
|---|---|---|
| `SchedulerProtocol` | `adaptive_reflow/algorithm/scheduler/protocols.py:157-273` | `sample(outer_cycle_id, round_in_cycle, target_round) -> ScheduleSample`; `cycle_length() -> int`; `schedule_family() -> str`; `config_hash() -> str`; `reset() -> None`; `record_round_feedback(round_in_cycle, metrics) -> None` (optional); `inject_noise(state, schedule_sample, *, generator) -> NDArray`; `to_config() -> dict`; `from_config(config) -> SchedulerProtocol` (classmethod) |
| `PolicyDriverProtocol` | `adaptive_reflow/algorithm/policy_driver.py:181-285` | `compute_policy(schedule_sample, *, base_policy, channel, prior_endpoint_digest, audit_codes=None) -> FinalRestartPolicy`; `driver_family() -> str`; `config_hash() -> str` |
| `MergeOperatorProtocol` | `adaptive_reflow/algorithm/merge/merge_operator.py:248-340` | `merge(prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down, audit_codes=None) -> float` (returns finite float in `[0, 1]` per P0-3 contract) |
| `RestartBlenderProtocol` | `adaptive_reflow/algorithm/blender/blender.py:425-470` | `blend(prior_state, fresh_state, memory_fraction, channel) -> StateBundle`; `blender_family() -> str`; `config_hash() -> str` |

**Cross-protocol invariant:** all 4 protocols share `config_hash()` (used for round-trace provenance), are `runtime_checkable`, and expose a `*_family()` identifier (used for audit logging and ledger attribution).

### 2.2 State machine determinism hooks

| Hook | File:line | Purpose |
|---|---|---|
| `_execute_transition_sync` | `adaptive_reflow/contracts/state_machine.py:858-920` | Pure deterministic transition: priority tiebreak by `(-priority, index)` sort; history recorded BEFORE leaving source; exit hooks (sync only) called in registration order; `self._state = target` atomic update; enter hooks + history restoration; effect invocation; append to `self._log` with monotonically increasing `self._counter`. |
| `_select_candidate` | `adaptive_reflow/contracts/state_machine.py:826-856` | Deterministic candidate selection: priority-sorted, first matching guard wins; if no guard matches and no `any_guard_seen`, return no-guard candidate; `GuardRejected` raised only in `_strict_guards` mode. |
| Sync dispatch only | `state_machine.py:843-847, 875-879, 899-902` | Three explicit `RuntimeError`s reject async hooks/guards/effects in sync dispatch — guarantees no event-loop reentrance. |
| `_log` immutable append-only | `state_machine.py:907-920` | `TransitionLog` is a `dataclass(frozen=True)`; list is append-only; no in-place mutation. |

### 2.3 Ledger integrity hooks

| Hook | File:line | Purpose |
|---|---|---|
| `compute_ledger_row_hash` | `adaptive_reflow/frame/engine.py:455-489` | SHA-256 over canonical row fields + `prev_ledger_row_hash`; `None` prev rendered as empty string for round-0 anchor; `per_channel_decision` keys sorted before serialization (canonical JSON). |
| `build_ledger_row` | `adaptive_reflow/frame/engine.py:492-539` | Constructs a `LedgerRow` dataclass; computes `ledger_row_id` from `(round_index, policy_hash, bundle_digest)`; calls `compute_ledger_row_hash`; sets `row_hash` field. |
| `verify_ledger_chain` | `adaptive_reflow/frame/engine.py:542-613` | Total function: returns `(True, "")` iff (a) `row[0].prev_ledger_row_hash is None`; (b) `row[i].prev_ledger_row_hash == row[i-1].row_hash`; (c) `recompute == row.row_hash` for every row (any tampering breaks equality); (d) `round_index` monotone non-decreasing. |
| `LedgerChain.append` | `adaptive_reflow/frame/ledger_chain.py:167-218` | Incremental fail-closed append: one row-hash recomputation per row (O(1)-amortised); `LedgerChainError` raised on any invariant break — row NOT appended; tracks `_head` and `_last_round` for O(1) linkage check. |

### 2.4 Capability-token handshake hooks

| Hook | File:line | Purpose |
|---|---|---|
| `Engine.handshake` | `adaptive_reflow/frame/engine.py:1273-1313` | Calls `adapter.capabilities()`; runs `validate_capabilities(caps)` for self-consistency; rejects empty `supported_channels` if adapter advertises channels; raises `CapabilityMissingError` for any of 8 required surfaces missing (`has_ode_integration_surface`, `has_prior_export`, `has_state_export`, `has_condition_injection`, `has_restart_boundary`, `has_trajectory_digest`, `has_deterministic_seed`, `has_materialization_route`). |
| `_capabilities_handshake` (legacy alias) | `engine.py:717-748` | Pre-dispatch surface-set intersection: builds `supported = set(caps.supported_channels)`; channel dispatched only if `channel in supported`. |

### 2.5 Typed four-port auto-wrap hooks

| Hook | File:line | Purpose |
|---|---|---|
| `ODEConditionDelta.__init__` (auto-wrap path) | `adaptive_reflow/contracts/condition.py:394-507` | Constructor auto-wraps raw `dict` into `MappingConditionAdapter`; preserves typed 4-port contract `(condition, target_endpoint, score_field, weight_field)`; back-compat path for legacy dict input (line 369-372). |
| `Condition` Protocol | `adaptive_reflow/contracts/condition.py:33-200` | Defines the 4-port typed surface; auto-wrap is **progressive**: existing callers passing raw dicts continue to work; new callers get typed-checked conditions at construction time. |

---

## 3. Six Protocol-Algebra Lemmas (prose-proof, no formal proof system)

Each lemma is a 1-paragraph informal claim followed by a 1-paragraph prose-proof sketch citing the source-of-truth file:line. Total prose target per lemma: 300-400 words (6 lemmas × 350 = ~2100 words, plus 3 sketches × 400 = ~1200 words, plus §3 connective tissue ~600 words = ~3900 words for the entire Theoretical Guarantees subsection).

### 3.1 Lemma 1 — SchedulerProtocol interface closure

**Claim.** The set `S = {S1, S2, ..., S9}` of nine required methods on `SchedulerProtocol` (`sample`, `cycle_length`, `schedule_family`, `config_hash`, `reset`, `record_round_feedback`, `inject_noise`, `to_config`, `from_config`) forms a **minimal interface**: every concrete scheduler (Cosine, Linear, Constant, ConvergenceAdaptive, CodimensionSheet, PaperQuantityDriven, ...) that passes `isinstance(s, SchedulerProtocol)` also satisfies `s.to_config() -> from_config(s.to_config()) == s` (round-trip), and every method is independently callable with the documented signature.

**Prose-proof sketch.** All nine methods are declared on `SchedulerProtocol` (`adaptive_reflow/algorithm/scheduler/protocols.py:157-273`). The `from_config` round-trip property is **enforced by construction** because every concrete scheduler inherits the `to_config`/`from_config` pattern from `ConfigMixin` (referenced in the docstring at line 261); the registry's `build_scheduler_from_config` factory uses `cls.from_config(...)` polymorphically. The `record_round_feedback` method is **deliberately optional** (lines 178-188): the protocol is `runtime_checkable`, so declaring it would force every family to define it. Instead, consumers use `hasattr(scheduler, "record_round_feedback")` and treat absence as "ignore feedback." The `inject_noise` deterministic reproducibility follows from the docstring contract (lines 232-253): identical `generator.bit_generator.state` + identical `state` always yield identical output (numpy `Generator.standard_normal` is deterministic given the state). The closure property holds because (a) every concrete scheduler is registered through `build_scheduler_from_config`; (b) the registry's `from_config` calls the concrete classmethod; (c) `to_config` returns a JSON-serialisable dict. QED.

### 3.2 Lemma 2 — PolicyDriverProtocol beta/memory_fraction direction (Contract 3.1)

**Claim.** For every `d : PolicyDriverProtocol` and every round, the returned policy's `beta_by_channel[c] ∈ [0, 1]` for every channel `c`, and `memory_fraction = 1 - beta_by_channel[c]` is the **only valid input** to `RestartBlenderProtocol.blend(..., memory_fraction=..., ...)`. Passing `beta` directly to `blender.blend` as `memory_fraction` would silently invert the blend (positive `beta` becomes negative `m` after `1 - beta`).

**Prose-proof sketch.** The contract is documented at `adaptive_reflow/algorithm/policy_driver.py:197-204` and re-asserted in `RestartBlenderProtocol` at `adaptive_reflow/algorithm/blender/blender.py:440-449`. The polarity is enforced by the shared helper `_override_beta_by_channel` (referenced at lines 204, 212) which **clips** to `[0, 1]` and sets `driver_computed_beta=True` (Contract 1.2, lines 207-213). The engine's inline override at `_policy_with_schedule_beta` (referenced line 296) is **suppressed** when `driver_computed_beta=True`, preventing double-application. The blender's `LinearBlender` (lines 470-485) explicitly computes `new = m * prior + (1 - m) * fresh` with `m` clamped to `[0, 1]` — the same arithmetic adapters inline today (`twodim_fm._blend_endpoint_with_prior`, `toy_gaussian._linear_blend`). The direction inversion is prevented because (a) every driver that mutates `beta_by_channel` sets the flag; (b) the engine's `_apply_schedule_beta_override` (line 1315-1329, P1-11) reads `driver_computed_beta` and skips re-override when True; (c) the blender boundary is the **only** place where `beta -> memory_fraction` is computed (explicitly, not implicitly). QED.

### 3.3 Lemma 3 — MergeOperator bounded-update contract (P0-3 / P2-4)

**Claim.** For every `m : MergeOperatorProtocol`, `m.merge(prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down)` returns a finite `float ∈ [0, 1]` for **all** caller inputs, including non-finite `prev` / `dynamic`, `cap > 1`, `cap < floor`, and `delta_cap_up < 0`. The result for clamping operators further lies in the (clipped) `[floor, cap]` envelope; for non-clamping operators (Identity, EMA) the envelope arguments are ignored but finiteness clipping still applies.

**Prose-proof sketch.** The contract is documented at `adaptive_reflow/algorithm/merge/merge_operator.py:262-301`. Clamping operators MUST accept any finite `cap` / `floor` and clip to `[0, 1]` before computing (lines 270-275). Non-clamping operators MUST NOT emit bounded-merge audit codes (lines 285-289) but MAY emit finiteness-clipping codes (`MERGE_NONFINITE_PREV_CLIPPED`, `MERGE_NONFINITE_DYNAMIC_CLIPPED`) when `prev` or `dynamic` is non-finite / out-of-range (lines 290-296). Operators that ignore `audit_codes` MUST NOT mutate the caller's list (lines 297-300). The contract closes three bugs: (a) P0-3 (operators raising on non-finite input); (b) P2-4 (audit list mutation by non-clamping operators); (c) the silent `cap > 1` / `cap < floor` failure mode. The diagnostic codes are documented in the contract preamble (line 268 references `MERGE_DEGENERATE_INTERVAL`, `MERGE_FLOOR_FALLBACK`). QED.

### 3.4 Lemma 4 — RestartBlenderProtocol convex combination correctness

**Claim.** For every `b : RestartBlenderProtocol` with `m := memory_fraction ∈ [0, 1]`, `b.blend(prior_state, fresh_state, m, channel)` returns a `StateBundle` whose `native_state_digest = H(m * prior + (1 - m) * fresh)` where `H` is the canonical hash function. The blend is deterministic: identical `(prior, fresh, m, channel)` always yield identical digests. The blend is **NOT** an arbitrary merge — it is a canonical convex combination.

**Prose-proof sketch.** The contract is documented at `adaptive_reflow/algorithm/blender/blender.py:425-449`. The `LinearBlender` default implementation (lines 470-485) computes `new = m * prior + (1 - m) * fresh` and exposes `FAMILY = LINEAR_FAMILY`. Determinism follows from (a) `m` clamped to `[0, 1]` (line 478); (b) `prior` and `fresh` are immutable inputs; (c) `H` is the framework's standard digest function (sha256 over canonical JSON). The convex combination property holds because `m * prior + (1 - m) * fresh = fresh + m * (prior - fresh)` — a line segment in state space. The blender's `config_hash()` (line 455-462) provides round-trace provenance: two blenders of the same family + config return equal hashes. Future blenders (e.g., `DistanceDecayBlender`, mentioned line 492) inherit the contract but may use non-linear `m * (prior - fresh)` shapes — the protocol accommodates this while the linear case is the canonical reference. QED.

### 3.5 Lemma 5 — CapabilityToken handshake closed-set ⊆ supported_channels

**Claim.** For every engine `e : Engine` and every adapter `a : FlowMatchingODEAdapter`, the round-dispatch invariant `∀ channel c : dispatched(c) ⇒ c ∈ supported_channels(a)` holds. Equivalently, the engine **never** dispatches a round targeting a channel the adapter has not advertised in `capabilities().supported_channels`. The handshake is fail-closed: a missing or empty capability surface raises an exception before any round dispatch.

**Prose-proof sketch.** The handshake is at `adaptive_reflow/frame/engine.py:1273-1313` and `engine.py:717-748`. Three failure modes are explicit: (a) `RuntimeError(ERR_ADAPTER_NONE)` when `adapter is None` (line 1288-1289); (b) `CapabilityMismatchError` when `validate_capabilities(caps)` fails (lines 1291-1296) — covers empty `supported_channels` while adapter advertises channels, plus self-consistency; (c) `CapabilityMissingError` for any of 8 required surfaces (lines 1301-1312). After handshake succeeds, the dispatch loop at `engine.py:1633-1669` checks `if channel not in caps.supported_channels` (line 1653) before dispatch. The handshake is **fail-closed** by design: `Engine.handshake` raises before any round dispatch is attempted. The diagnostic surface (capability name + context string) enables error diagnosability (per Sketch 3 below). QED.

### 3.6 Lemma 6 — Typed four-port auto-wrap migration correctness

**Claim.** For every caller that previously passed a raw `dict` to `ODEConditionDelta.__init__` and every caller that now passes a typed `Condition` (Protocol) object, the constructor's auto-wrap path produces an equivalent `MappingConditionAdapter` whose 4-port contract `(condition, target_endpoint, score_field, weight_field)` is satisfied. The auto-wrap is **progressive**: legacy dict-callers continue to work without code changes; new typed-callers get early validation.

**Prose-proof sketch.** The auto-wrap is at `adaptive_reflow/contracts/condition.py:394-507`. The constructor (a) checks if input is already a `Condition` Protocol object — if so, returns it; (b) if input is a raw `dict`, wraps it in `MappingConditionAdapter`; (c) preserves the 4-port invariant by reading `target_endpoint`, `score_field`, `weight_field` from the dict with defaults. The back-compat path is documented at `adaptive_reflow/universal/state.py:336-372`: the `ODEConditionDelta` constructor already auto-wraps, so legacy code passing raw dicts continues to work. The migration is correctness-preserving because: (i) `MappingConditionAdapter` is a faithful adapter for the dict semantics (same 4-port surface, same field defaults); (ii) the auto-wrap is idempotent (wrapping an already-wrapped adapter returns it unchanged); (iii) the typed `Condition` Protocol is a structural supertype of the dict — every dict satisfies the protocol after auto-wrap. The only semantic difference: new typed-callers may receive an early `TypeError` for malformed conditions; legacy dict-callers get a deferred error at first access. QED.

---

## 4. Three Proof Sketches (state-machine determinism, ledger integrity, handshake diagnosability)

### 4.1 Sketch 1 — State-machine byte-determinism

**Claim.** For every `sm : StateMachine` (PEP 695 generic, `adaptive_reflow/contracts/state_machine.py:372-1190`), given a fixed `(event, payload)` sequence, the resulting `TransitionLog` is **unique**. Formally: for any two execution traces `(event_i, payload_i)_{i=1..N}` with identical inputs, `sm.send(e_1, p_1).send(e_2, p_2)...send(e_N, p_N)._log == sm.send(e_1, p_1).send(e_2, p_2)...send(e_N, p_N)._log` regardless of thread interleaving, async dispatch ordering, or guard non-determinism.

**Prose-proof sketch.** Determinism follows from four invariants: (1) **Priority tiebreak by index** — `_select_candidate` (lines 826-856) sorts candidates by `(-priority, index)`, where `index` is the registration order. Two candidates with identical priority are tiebroken by registration order, which is itself deterministic. (2) **Guard evaluation is short-circuit and pure** — guards are evaluated in priority order; first match wins; `GuardRejected` is only raised in `_strict_guards` mode (line 851). (3) **History recording is eager and deterministic** — `_execute_transition_sync` (lines 858-920) updates history of the source BEFORE exit hooks fire (lines 869-871), preventing reorder with hook side-effects. (4) **Sync dispatch forbids async reentrance** — three explicit `RuntimeError`s (lines 843-847, 875-879, 899-902) reject async guards/hooks/effects in sync dispatch. The `TransitionLog` is append-only (line 907-920) with a monotonic `self._counter`; identical event sequences produce identical logs. Async dispatch (`_dispatch_async`, line 924-931) preserves determinism because: (a) sub-state machines process events serially; (b) region selection is by `_can_async(event, payload)`, which is pure. The `asend` API is provided for async callers but `send` is the canonical sync path used by the engine. QED.

### 4.2 Sketch 2 — Ledger integrity via SHA-256 chain (fail-closed)

**Claim.** For every ledger chain `L : LedgerChain` and every row `r ∈ L.rows`, `L.verify()` returns `(True, "")` iff (a) `r[0].prev_ledger_row_hash is None`; (b) `r[i].prev_ledger_row_hash == r[i-1].row_hash` for `i ≥ 1`; (c) `sha256(canonical_json(r.fields ∪ {prev_ledger_row_hash: r[i-1].row_hash})) == r.row_hash`; (d) `r.round_index` monotone non-decreasing. Any tampering with `audit_codes`, `per_channel_decision`, `applied_policy_hash`, `selected_bundle_digest`, `round_index`, `source_round`, `target_round`, `prev_ledger_row_hash`, or `row_hash` breaks (c) with probability `1 - 2^{-256}` (SHA-256 collision resistance).

**Prose-proof sketch.** The hash function is `compute_ledger_row_hash` (`adaptive_reflow/frame/engine.py:455-489`). It serialises a canonical dict (keys sorted at lines 482-484 for `per_channel_decision`; `None` prev rendered as empty string line 486) and SHA-256s the JSON. `verify_ledger_chain` (lines 542-613) re-computes the hash from each row's fields and compares to the stored `row_hash` — any tamper breaks equality (line 599-604). `LedgerChain.append` (lines 167-218) is the incremental fail-closed version: it raises `LedgerChainError` on any invariant break and **does not append the bad row**, preserving chain integrity by construction. The four invariants are checked in order: type-check (line 180), anchor check for index 0 (lines 185-191), linkage check for index ≥ 1 (lines 192-198), round monotonicity (lines 199-204), hash recomputation (lines 206-213). Failure mode coverage: type error → `LedgerChainError("row[N] is not a LedgerRow")`; anchor mismatch → `LedgerChainError("must be None at the chain anchor")`; linkage mismatch → `LedgerChainError("does not link to the current head")`; round regression → `LedgerChainError("regresses below the previous round")`; hash mismatch → `LedgerChainError("does not match the hash recomputed")`. SHA-256 collision resistance gives cryptographic tamper-evidence; the fail-closed append gives construction-time integrity. QED.

### 4.3 Sketch 3 — CapabilityToken handshake error diagnosability

**Claim.** For every engine `e : Engine`, adapter `a : FlowMatchingODEAdapter`, and failure mode `f` (missing required surface, empty `supported_channels`, adapter-is-None, capability self-inconsistency), the handshake raises an exception whose message contains: (1) the **capability name** that failed; (2) the **context** string identifying the call site; (3) a **suggestion** for remediation. A consumer reading the exception message alone can identify the failure class and the required fix without inspecting the engine source.

**Prose-proof sketch.** The error surface is at `engine.py:1273-1313`. Three exception classes are used: (a) `RuntimeError(ERR_ADAPTER_NONE)` where `ERR_ADAPTER_NONE` is the constant at `engine.py:125` (failure mode: caller passed `None`); (b) `CapabilityMismatchError(capability="capabilities", message=f"adapter capabilities failed consistency check: {errors}")` (failure mode: surface self-inconsistency, e.g., empty `supported_channels` while adapter advertises channels); (c) `CapabilityMissingError(required, context="Engine.handshake")` (failure mode: one of 8 required surfaces missing). Each exception type is a distinct class (not just a string), enabling `except CapabilityMissingError as e: ... e.capability ... e.context`. The error messages are templated to include the capability name and context string, allowing log-based diagnosis. The diagnostic codes are stable across releases — adapters advertising `(has_ode_integration_surface=True, supported_channels=("native",))` produce identical error messages today and tomorrow. QED.

---

## 5. Three Fresh-Writing Sections (§2, §8, §11)

### 5.1 §2 Related Work (target 600-800 words)

**Three-layer prior art, structured as one paragraph per layer. No JMAA as primary contribution.**

**Paragraph 1: FM inference acceleration (200-250 words).** Cover the lineage from DDPM (Ho et al. 2020) → DDIM (Song et al. 2021) → DPM-Solver (Lu et al. 2022a) → DPM-Solver++ (Lu et al. 2022b) → Consistency Models (Song et al. 2023) → ReFlow/InstaFlow (Liu et al. 2022) → Progressive Distillation (Salimans & Ho 2022) → Latent Consistency Models (Luo et al. 2023). Position FlowA in this lineage: a **training-free re-inference framework** (no fine-tuning, no distillation) that operates at the per-round capacity boundary rather than the per-step ODE boundary. Differentiate from consistency-model approaches (which require a single forward pass through the consistency network) and from distillation approaches (which require paired teacher-student training). Cite Wave 1 + Wave 286 + Wave 290 features.

**Paragraph 2: FM theoretical frameworks (200-250 words).** Briefly cover score-SDE (Song et al. 2021), flow matching OT (Lipman et al. 2023, Albergo & Vanden-Eijnden 2023), Rectified Flow (Liu et al. 2022), and JMAA (the user's companion paper, mentioned as "theoretical companion in a separate line of work"). Position FlowA as a **practical framework** that operates at the scheduler-blender boundary; the theoretical companion paper explores paper-quantity-driven scheduling and convergence analysis. Do NOT introduce JMAA Theorem 1 as a primary contribution here. Cite as: "see companion paper for theoretical analysis of paper-quantity-driven scheduling."

**Paragraph 3: Typed ML system contracts (200-250 words).** Cover Protocol/ABC patterns (PEP 544), Rust traits, Haskell type classes, capability-based security (Miller 2006), and typed contract systems in ML (e.g., TensorFlow's typed tensors, PyTorch's dispatcher protocol). Position FlowA's 4-protocol algebra (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`) as a **structural-typed contract system** where each protocol is `runtime_checkable` and exposes a `config_hash()` for provenance. Differentiate from nominal-typed approaches (Java interfaces, C++ abstract classes) by emphasizing the duck-typed dispatch + canonical-config-hash provenance.

### 5.2 §8 Reproducibility (target 600-800 words)

**Six subsections, each 100-130 words.**

**§8.1 SHA-256 ledger chain.** Describe the canonical row hash, the four invariants, the fail-closed append. Reference `adaptive_reflow/frame/engine.py:455-613` and `adaptive_reflow/frame/ledger_chain.py:113-218`. State that the ledger is the framework's tamper-evident audit log.

**§8.2 D.4 byte-stability suite.** Describe the 30/30 regression vector test suite (`tests/test_d4_regression_vectors.py`), its purpose (locking byte-for-byte reproducibility across refactors), and its continuous-integration role (every commit runs the suite in <10 seconds). State: "D.4 is the framework's behavioral fingerprint — any non-trivial change to the framework must not perturb it."

**§8.3 Vendor purity invariant.** State that all third-party adapter code (in `vendored/` and `data/`) is byte-for-byte untouched across commits; any required adapter change must be brought into the framework's `adapters/` directory and re-exported. Reference `tools/check_claims_consistency.py` and the vendored-untouched CI gate.

**§8.4 Feature inventory (Wave 286/290/268/296).** Enumerate the five framework features that compose the reproducibility story: (a) Wave 286 — protocol algebra (`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`); (b) Wave 290 — typed four-port auto-wrap; (c) Wave 268 — strict-clean audit invariants; (d) Wave 296 — 5-gate verification suite; (e) Wave 297 P5 — 11-cell systematic-evidence grid.

**§8.5 CI gate composition.** State the 5-gate suite: (1) D.4 30/30; (2) ruff 0-warnings; (3) mkdocs strict 0-warnings; (4) claims no-drift (`tools/check_claims_consistency.py`); (5) vendored/data untouched. Every PR must pass all 5; the agent running Day 1 RESOLUTION verified all 5 pass on the pre-RESOLUTION baseline.

**§8.6 Reproduction package.** State that the framework ships with: (a) the SHA-256 ledger replay tool; (b) the D.4 regression suite; (c) the 5-gate CI runner; (d) the 11-cell systematic-evidence grid; (e) the 8-adapter coverage table. A reviewer with the repository can reproduce any result in the paper by running the corresponding test or notebook.

### 5.3 §11 Conclusion (target 200-300 words)

**Two short paragraphs.**

**Paragraph 1: Restate 4 contributions + paper boundary.** Restate the 4 primary contributions of Paper A: (1) the 4-protocol framework with structural-typed contracts; (2) the 13-scheduler taxonomy; (3) the 5-adapter vendor-friendly protocol; (4) the 11-cell systematic-empirical grid. State that the paper boundary is **framework + scheduler family + empirical results + reproducibility** — JMAA theory and paper-quantity-driven scheduling are treated as a separate companion paper.

**Paragraph 2: Future directions + Paper B pointer.** Three future directions: (a) extend the adapter protocol to video and 3D domains (one paragraph, citing Wan2.2 + LineageFlow as examples already partially integrated); (b) explore convergence-aware scheduling in production deployments (cite Wave 35 FIX-2 + CodimensionSheetScheduler as enabling work); (c) build the companion paper on paper-quantity-driven scheduling and convergence analysis (cite Paper B skeleton). End with: "A complete account of paper-quantity-driven scheduling, including the theoretical companion and the 16-site integration verification, will appear in a separate paper."

---

## 6. LaTeX Integration Plan (Day 4 execution, Day 2 only plans)

### 6.1 IEEEtran class + TNNLS template

```
\documentclass[journal]{IEEEtran}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{url}

\newtheorem{lemma}{Lemma}
\newtheorem{sketch}{Proof Sketch}
\newtheorem{claim}{Claim}
```

### 6.2 New theorem environments mapping

| Day-2 prose artifact | LaTeX environment | Paper section |
|---|---|---|
| Lemma 1 (SchedulerProtocol closure) | `\begin{lemma} ... \end{lemma}` | §3 Framework, subsection "Protocol Algebra" |
| Lemma 2 (beta/memory_fraction polarity) | `\begin{lemma} ... \end{lemma}` | §3 Framework, subsection "Protocol Algebra" |
| Lemma 3 (MergeOperator bounded contract) | `\begin{lemma} ... \end{lemma}` | §3 Framework, subsection "Protocol Algebra" |
| Lemma 4 (RestartBlender convex combination) | `\begin{lemma} ... \end{lemma}` | §3 Framework, subsection "Protocol Algebra" |
| Lemma 5 (CapabilityToken closed-set) | `\begin{lemma} ... \end{lemma}` | §5 Adapter Protocol, subsection "Handshake Correctness" |
| Lemma 6 (Typed four-port auto-wrap) | `\begin{lemma} ... \end{lemma}` | §5 Adapter Protocol, subsection "Migration Correctness" |
| Sketch 1 (SM byte-determinism) | `\begin{sketch} ... \end{sketch}` | §3 Framework, subsection "State-Machine Determinism" |
| Sketch 2 (Ledger integrity) | `\begin{sketch} ... \end{sketch}` | §3 Framework, subsection "Ledger Integrity" |
| Sketch 3 (Handshake diagnosability) | `\begin{sketch} ... \end{sketch}` | §5 Adapter Protocol, subsection "Error Diagnosability" |

### 6.3 Section 6 Theoretical Guarantees placement (in main text)

Per DeepSeek's structural decision (no JMAA as primary contribution), the **6 lemmas + 3 sketches are split**:

- **Main text (§3 Framework)**: Lemmas 1-4 + Sketch 1 + Sketch 2 — fits within the §3 "Framework" 2-page budget by trimming ~200 words from existing §3 prose. Lemmas 1-4 establish the protocol algebra (~1400 words); Sketch 1 establishes state-machine determinism (~400 words); Sketch 2 establishes ledger integrity (~400 words).
- **Main text (§5 Adapter Protocol)**: Lemmas 5-6 + Sketch 3 — fits within the §5 "Adapter Protocol" 1-page budget by adding ~600 words. Lemmas 5-6 establish handshake correctness + auto-wrap migration (~600 words); Sketch 3 establishes error diagnosability (~400 words).
- **Supplementary (Day 5 deferred)**: full Path A prose-proof extensions (12-day target) — 5-6 additional lemmas covering convergence analysis (CodimensionSheetScheduler termination), per-adapter byte-determinism, capability-token extension properties, typed-channel determinism, distributed-dispatch correctness, paper-quantity-driven scheduler convergence (the latter is JMAA-related, marked "theoretical companion" only).

### 6.4 Day 4 LaTeX execution checklist

1. Convert `docs/drafts/paper-flat-flattened.md` → `docs/drafts/paper.tex`
2. Insert `\newtheorem` environments at top
3. Wrap each lemma in `\begin{lemma}...\end{lemma}` + `\begin{proof}...\end{proof}` (sketch proofs are inline within the lemma body)
4. Insert 4 figure placeholders + 3 table environments
5. Run `pdflatex paper.tex` + `bibtex paper` + `pdflatex paper.tex` + `pdflatex paper.tex`
6. Verify page count ≤14 (TNNLS limit)
7. Re-run 5-gate suite (D.4 unaffected; mkdocs may need paper-section ID updates)

---

## 7. Execution Sequencing (Day 2 hour-by-hour, ~10-12 hours wall-clock)

| Hour | Task | Deliverable | Gate |
|---|---|---|---|
| 0-1 | Re-verify Day 1 RESOLUTION output: paper is 1069 lines, 11 sections, 5-gate baseline passes | `wave301-day2-baseline-verify.md` (state snapshot) | 5-gate baseline |
| 1-2 | Write Lemma 1 (SchedulerProtocol closure) | inline in `wave301-day2-lemmas.md` §1 | word count 300-400 |
| 2-3 | Write Lemma 2 (PolicyDriverProtocol polarity) + Lemma 3 (MergeOperator contract) | inline in `wave301-day2-lemmas.md` §§2-3 | word count 600-800 |
| 3-4 | Write Lemma 4 (RestartBlender convex combination) + Lemma 5 (CapabilityToken closed-set) | inline in `wave301-day2-lemmas.md` §§4-5 | word count 600-800 |
| 4-5 | Write Lemma 6 (Typed four-port auto-wrap) + Sketch 1 (SM byte-determinism) | inline in `wave301-day2-lemmas.md` §6 + §Sketch-1 | word count 600-800 |
| 5-6 | Write Sketch 2 (Ledger integrity) + Sketch 3 (Handshake diagnosability) | inline in `wave301-day2-lemmas.md` §§Sketch-2-3 | word count 600-800 |
| 6-7 | Write §2 Related Work (3 paragraphs) | `wave301-day2-section-2.md` | word count 600-800 |
| 7-8 | Write §8 Reproducibility (6 subsections) | `wave301-day2-section-8.md` | word count 600-800 |
| 8-9 | Write §11 Conclusion (2 paragraphs) | `wave301-day2-section-11.md` | word count 200-300 |
| 9-10 | Cross-check: every lemma/section cites a verified file:line anchor; total paper prose word count is 4800-5500 (after Day 1 RESOLUTION trims) | `wave301-day2-cross-check.md` | anchor verification + word budget |
| 10-11 | Present to user for boundary-clearness check: Contributions list, Abstract, §6 Theoretical Lenses removal confirmation | user review session | user sign-off |
| 11-12 | Commit Day 2 deliverables as separate docs (not yet merged into `paper-flat-flattened.md`); update CLAIMS.md with new lemma anchors; run 5-gate suite one more time | git commit + gate log | 5-gate suite passes on docs |

**Total: 11-12 hours wall-clock.** The compressed timeline (12 days → 1 day) is achieved by accepting coverage depth tradeoffs: lemmas are 1-paragraph sketches, not 4-paragraph proofs; proof sketches are 1-paragraph informal arguments, not multi-page formal developments.

---

## 8. Verification Strategy (5-gate + Day-2-specific gates)

### 8.1 Re-run 5-gate suite (must pass)

| Gate | Command | Expected |
|---|---|---|
| D.4 30/30 | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30 passed, ≤3 pre-existing DeprecationWarnings |
| ruff 0 | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| mkdocs strict 0 | `mkdocs build --strict` | exit_code=0, 0 project warnings |
| claims no drift | `python3 tools/check_claims_consistency.py` | no drift detected |
| vendored untouched | `git diff --stat -- vendored/ data/` | (empty) |

**Day 2 caveat:** Day 2 produces 4 new files (`wave301-day2-lemmas.md`, `wave301-day2-section-2.md`, `wave301-day2-section-8.md`, `wave301-day2-section-11.md`) under `docs/audit/`. These do not affect the gates because they are documentation (not framework code or vendored code) and not claims-anchored (CLAIMS.md references only the canonical paper file `paper-flat-flattened.md`).

### 8.2 Day-2-specific gates

| Gate | Method | Expected |
|---|---|---|
| Lemma anchor verification | grep every lemma's cited file:line and confirm the file:line is in-range and the cited text matches | all 9 anchors verified |
| Section word counts | `wc -w` on each section file | §2: 600-800; §8: 600-800; §11: 200-300 |
| Lemma word counts | manual word count per lemma | each 300-400 |
| Sketch word counts | manual word count per sketch | each 350-450 |
| Total paper prose budget | sum of lemmas + sketches + §2 + §8 + §11 | 4800-5500 words (target for TNNLS 14-page envelope) |
| Boundary clearness check | user review: Contributions list, Abstract, §6 removal | user sign-off required before Day 3 |

---

## 9. Risk Register (Day 2 specific)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Lemmas compress 12-day target into 1 day — coverage depth insufficient for 90%+ confidence | HIGH | HIGH | Mark lemmas as "prose-proof sketches" not "full proofs"; commit to supplementary Day 5 for depth expansion |
| Source-of-truth file:line anchors drift between Day 2 reading and Day 4 LaTeX | MEDIUM | MEDIUM | Re-verify anchors immediately before Day 4 LaTeX conversion; pin to git commit SHA |
| §2 Related Work exceeds 800 words due to FM literature breadth | MEDIUM | LOW | Cap each paragraph at 250 words; prioritize 2-3 anchor citations per paragraph |
| §8 Reproducibility duplicates Wave 296 5-gate documentation | LOW | LOW | Reference Wave 296 doc explicitly rather than re-explaining |
| User disagrees with §6 Theoretical Lenses drop and wants companion paragraph in §1 | MEDIUM | LOW | Pre-authorized Day 0 decision; if reversed, fold Lemma 5/6 sketch into §1 as one companion paragraph (~200 words) |
| Boundary-clearness check finds Contributions list still mentions JMAA | MEDIUM | HIGH | Re-write Contributions list to remove any JMAA reference; pass through user review |

### 9.1 Coverage-depth tradeoffs (explicit)

The 12-day Path A self-estimate (Wave 300 P2) allocates ~1.5 days per lemma for full prose-proof. Day 2 allocates ~1 hour per lemma. This 12× compression is achieved by:

1. **Accepting 1-paragraph sketches instead of multi-page proofs.** Each lemma becomes a 1-paragraph claim + 1-paragraph informal argument, citing the source-of-truth file:line.
2. **Skipping counter-example construction.** Counter-examples (when the lemma fails for a "bad" implementation) are deferred to supplementary.
3. **Skipping convergence analysis.** The 12-day target includes convergence lemmas for paper-quantity-driven schedulers (JMAA-related); these are explicitly OUT of Paper A scope per DeepSeek's boundary rule.
4. **Skipping parametric complexity analysis.** No formal bounds on runtime, memory, or NFE cost are proven; these are deferred to supplementary.

**Net result:** Day 2 produces lemmas that are **plausible and well-anchored** but **not formally complete**. This matches the "compressed first-draft by Day 3" framing from the Wave 301 Day 0 verification: 60-70% confidence draft, full Path A proofs deferred to supplementary.

---

## 10. Deliverables Manifest (Day 2 output files)

| File | Size | Purpose | Status |
|---|---|---|---|
| `docs/audit/wave301-day2-execution-plan.md` | THIS DOC | Execution sequencing + LaTeX plan + verification | READ-ONLY (input to Day 2 agent) |
| `docs/audit/wave301-day2-baseline-verify.md` | ~200 lines | Day 1 RESOLUTION output verification + 5-gate re-baseline | NEW (Day 2 hour 0-1 output) |
| `docs/audit/wave301-day2-lemmas.md` | ~4500-5500 words | 6 lemmas + 3 proof sketches (LaTeX-ready prose) | NEW (Day 2 hour 1-6 output) |
| `docs/audit/wave301-day2-section-2.md` | 600-800 words | §2 Related Work draft | NEW (Day 2 hour 6-7 output) |
| `docs/audit/wave301-day2-section-8.md` | 600-800 words | §8 Reproducibility draft | NEW (Day 2 hour 7-8 output) |
| `docs/audit/wave301-day2-section-11.md` | 200-300 words | §11 Conclusion draft | NEW (Day 2 hour 8-9 output) |
| `docs/audit/wave301-day2-cross-check.md` | ~150 lines | Anchor verification + word budget check | NEW (Day 2 hour 9-10 output) |
| `docs/audit/wave301-day2-boundary-review.md` | ~50 lines | User boundary-clearness check sign-off | NEW (Day 2 hour 10-11 output) |
| `docs/audit/wave301-day2-gate-log.md` | ~100 lines | 5-gate final verification log | NEW (Day 2 hour 11-12 output) |

**Total Day 2 output: 9 new files** under `docs/audit/`, all READ-ONLY with respect to `paper-flat-flattened.md`. The lemmas and section drafts are **not merged into the paper** during Day 2; merging happens on Day 4 during LaTeX conversion (so Day 3 structure lock + Day 4 LaTeX conversion can review / adjust before committing to paper.tex).

---

## 11. Hand-off to Day 3 (Structure Lock + §1/§3-§7 Edit Pass)

**Day 3 receives the following inputs from Day 2:**

1. `wave301-day2-lemmas.md` — 6 lemmas + 3 proof sketches (LaTeX-ready)
2. `wave301-day2-section-2.md` — §2 Related Work draft
3. `wave301-day2-section-8.md` — §8 Reproducibility draft
4. `wave301-day2-section-11.md` — §11 Conclusion draft
5. `wave301-day2-cross-check.md` — Anchor verification + word budget check (target: 4800-5500 words total)
6. `wave301-day2-boundary-review.md` — User sign-off on Contributions/Abstract/§6-removal

**Day 3 produces:**

1. Updated `paper-flat-flattened.md` with the Day 2 drafts inserted into their final §2/§8/§11 positions
2. Updated §3 Framework prose incorporating Lemmas 1-4 + Sketches 1-2
3. Updated §5 Adapter Protocol prose incorporating Lemmas 5-6 + Sketch 3
4. Updated §1 Introduction + Contributions list (boundary-clearness verified)
5. Updated CLAIMS.md with new lemma anchors (6 lemmas + 3 sketches)
6. Re-verified 5-gate suite
7. Updated `wave301-day3-execution-plan.md` for the next phase

**Day 3 dependencies on Day 0/1/2:**

- Day 0: §6 removal decision, §10 fold-in decision, figure count decision
- Day 1: RESOLUTION pass + structure lock + 5-gate baseline
- Day 2: 6 lemmas + 3 sketches + §2/§8/§11 drafts (THIS PLAN)

If any dependency is missing on Day 3 start, STOP and re-engage user.

---

## 12. Summary

**Day 2 produces:**
- 6 protocol-algebra lemmas (closure, polarity, bounded-contract, convexity, closed-set, auto-wrap) — 300-400 words each, total ~2100 words
- 3 proof sketches (SM byte-determinism, ledger integrity, handshake diagnosability) — 350-450 words each, total ~1200 words
- 3 fresh sections (§2 Related Work 600-800w, §8 Reproducibility 600-800w, §11 Conclusion 200-300w) — total ~1500 words
- Total Day 2 prose output: ~4800-5500 words (fits TNNLS 14-page envelope after Day 1 trim)
- LaTeX integration plan (executed Day 4): `\newtheorem{lemma}` + `\newtheorem{sketch}` + IEEEtran class, 9 theorem-environments mapped to §3 and §5 main text, full Path A supplementary deferred to Day 5

**Day 2 is GATED on Day 1 completion** (RESOLUTION pass + 5-gate baseline + user structure sanity check).

**Coverage-depth tradeoff (explicit):** 12-day Path A target compressed to 1 day at the cost of formal completeness — lemmas are 1-paragraph sketches with file:line anchors, not multi-page formal proofs. Full Path A prose-proof extensions deferred to Day 5 supplementary.

**Verification:** 5-gate suite + Day-2-specific gates (anchor verification, word budget, boundary clearness) all required to pass before Day 3 begins.

---

**END OF DAY 2 EXECUTION PLAN**
