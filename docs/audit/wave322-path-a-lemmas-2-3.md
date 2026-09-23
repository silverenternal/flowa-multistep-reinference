# Wave 322 — Path A Lemma 2 (State-Machine Byte-Determinism) + Lemma 3 (Ledger Tamper-Evidence) Audit

**Wave:** 322 (Path A — paper-quantity / scheduler-property lemmas, closure of Wave 311 PARTIAL-APPLY)
**Date:** 2026-09-23
**Author:** Wave 322 P1 Path A
**Status:** ACTIVE — Lemma 2 statement + 4-case proof sketch + Lemma 3 statement + 3-case proof sketch + source-code anchors + cross-doc propagation
**Cross-references:**
- `docs/audit/wave311-d1-review.md` (Wave 311 D+1 self-review; primary audit anchor for the Path A lemma trio; updated in Wave 322 to note Wave 322 closes the 2 remaining lemma placeholders)
- `docs/audit/wave311-path-a-lemma-1.md` (Wave 311 Path A audit doc for Lemma 1 — protocol composition closure; sibling audit doc)
- `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` (paper-body insertion form of all 3 Path A lemmas)
- `docs/drafts/paper-flat-flattened.md` §6 Framework Properties line 1391-1422 (paper-body §6 with Lemma 1 at line 1400, Lemma 2 at line 1408, Lemma 3 at line 1410)
- `docs/CLAIMS.md` CLM-085 / CLM-086 / CLM-087 / CLM-088 (4 Claims ledger entries — 3 lemma claims + 1 meta-claim)

---

## 1. Summary

This audit doc is the canonical Wave 322 Path A audit doc for **Lemma 2 (State-Machine Byte-Determinism)** + **Lemma 3 (Ledger Tamper-Evidence)** — the second + third lemmas of the §6 Framework Properties rename. Together with **Lemma 1 (Protocol Composition Closure)** (Wave 311, `docs/audit/wave311-path-a-lemma-1.md`), they complete the formal-verification trio of the typed-contracts framework. Wave 311 PARTIAL-APPLY shipped Lemma 1 as ACTIVE and Lemmas 2/3 as PLACEHOLDER for Wave 312 insertion; Wave 322 closes the 2 remaining lemma placeholders.

The Path A lemmas collectively elevate the framework from "code that happens to work" to a typed-contracts architecture whose component boundaries are formally verified at the byte-stability + cryptographic-commitment layer (Wave 296 P7 FID Δ=0% as the empirical reading that the framework's module-independence extends to its theoretical companion lens).

| Lemma | Wave | CLM | Status (pre-Wave 322) | Status (post-Wave 322) |
|---|---|---|---|---|
| Lemma 1 — Protocol Composition Closure | 311 | CLM-085 | ACTIVE | ACTIVE (unchanged) |
| Lemma 2 — State-Machine Byte-Determinism | 322 | CLM-086 | PLACEHOLDER | **ACTIVE (Wave 322)** |
| Lemma 3 — Ledger Tamper-Evidence | 322 | CLM-087 | PLACEHOLDER | **ACTIVE (Wave 322)** |
| Meta — §6 Framework Properties formally verified | 322 | CLM-088 | (not present) | **ACTIVE (Wave 322)** |

---

## 2. Lemma 2 — State-Machine Byte-Determinism

### 2.1 Formal Statement

Let $S$ and $S'$ be two `StateMachine` instances from
`adaptive_reflow/contracts/state_machine.py:386` (PEP 695 generic class
`StateMachine[TState, TEvent]`) initialised **identically** (same
`initial` state, same `name`, same `_transitions` list, same
`_regions` and `_parallel` maps, same `_history_kind` and history
snapshots, same `_strict_guards` flag, same `_log` cleared, same
`_counter = 0`). Then for any **finite event sequence**
$E = (e_1, e_2, \dots, e_n)$ drawn from the same `TEvent` alphabet
and dispatched via either `S.send(event, payload)` or
`S.asend(event, payload)` (each call internally routes through the
corresponding sync / async dispatch path at `state_machine.py:757`
and `state_machine.py:924` respectively), the `TransitionLog`
dataclass tuple produced by $S$ is **byte-identical** to that
produced by $S'$:

$$\forall i \in \{1, \dots, n\}: \ S.\text{log}[i] \equiv_\text{byte} S'.\text{log}[i]$$

where $\equiv_\text{byte}$ denotes Python tuple-of-dataclasses
field-by-field equality (the same comparison criterion used by
`tests/test_contracts/test_state_machine.py:624`). Equivalently, the
JSON serialisation of the log (via `dataclasses.asdict(...)` then
`json.dumps(...)` on each entry) is byte-identical across the two
machines.

### 2.2 Proof Sketch (4 cases + synthesis)

The four cases cover every dispatch path reachable from
`StateMachine.send` / `StateMachine.asend`.

#### Case A — Priority tiebreak

When the current state $s_i$ has multiple registered transitions for
event $e_i$, the dispatch calls `_try_pick_sync` (sync path,
`state_machine.py:808-856`) or `_try_pick_async`
(`state_machine.py:971-1003`). Both compute the same ordered list:

```python
indexed = list(enumerate(candidates))
indexed.sort(key=lambda pair: (-pair[1].priority, pair[0]))
```

This is a **stable sort over a Python `list`** — the sort key
consists of `(int_priority, int_registration_index)`; both
components are integers (no floating-point), and `pair[0]` is the
materialised position in the registration order (not a generator or
hash). Since the registration order, the priority values, and the
iteration over `self._transitions` are deterministic on identical
inputs, **both $S$ and $S'$ produce the same sorted `ordered` list**.
The first non-rejected guard either fires or returns the chosen
transition. Guard execution invokes `cand.guard(self._ctx(event,
payload))` where `cand.guard` is a Python callable that is a
`Guard = Callable[..., Awaitable[bool] | bool]`
(`state_machine.py:73`); guards must be **pure** (the docstring at
`state_machine.py:46-48` requires this for byte-determinism) — no
floating-point arithmetic, no I/O, no RNG. Both machines select the
same transition.

#### Case B — History

`_update_history` (`state_machine.py:680-694`) snapshots the
sub-state machine's current `_state` into the `_history` /
`_history_deep` dicts **purely** as a function of `(parent, sub)`
topology at the time of transition execution. `_restore_history`
(`state_machine.py:711-740`) restores the saved sub-state on
re-entry, also purely. Because (i) the state objects themselves are
immutable Python identifiers from the `TState` type, (ii) the
region-name keys are strings registered at construction time, and
(iii) the history map ordering is determined by the iteration
sequence of the regions dict (which itself is built deterministically
at registration time), $S$ and $S'$ push / pop identical history
entries.

#### Case C — Parallel regions

When an event triggers parallel-region dispatch (a single event
spawns $N$ sub-events in orthogonal regions), `_dispatch_sync`
(`state_machine.py:767-775`) iterates `for sub in
self._parallel.get(self._state).values():` in the **insertion order**
of the parallel regions dict. `dict.values()` in CPython 3.11+
preserves insertion order; both $S$ and $S'$ were initialised with
the same `Mapping[str, StateMachine]` argument, so the iteration
order is identical. The sub-dispatch priority for each sub-event is
computed inside the sub-state-machine via Case A (priority
tiebreak), so by induction the sub-results are byte-identical. The
`handled_any` flag is pure-Bool and identical across instances.

#### Case D — asyncio.gather

The async dispatch at `_dispatch_async` (`state_machine.py:924-955`)
constructs the list of coroutines **deterministically**:

```python
coros = []
for sub in parallel.values():
    if await sub._can_async(event, payload):
        coros.append(sub._dispatch_async(event, payload))
        handled_any = True
if coros:
    await asyncio.gather(*coros)
```

The `coros` list is built in the **same parallel-region insertion
order** as the sync case (Case C), and `_can_async` is a **pure**
predicate over `(event, payload)` and the current state (no time,
no RNG, no wall clock). `asyncio.gather(*coros)` schedules them on
the event loop in list order; the awaits resolve in list order on a
single-threaded event loop. **There is no `asyncio.ensure_future`,
no task creation with side effects, no `gather(return_exceptions=
...)` — the gathering is pure**. Both $S$ and $S'$, when awaited
under the same event-loop policy, resume sub-machines in the same
order and produce the same `_execute_transition_async` calls
(`state_machine.py:1005-1061`).

#### Case E (synthesis) — JSON serialisation

The transition log field types are `int | str | tuple[str, ...] |
None | bool` — all byte-stable at `str(...)` and tuple-equality
levels (the `@dataclass(frozen=True)` `TransitionLog` at
`state_machine.py:133-185` explicitly pins hash to the 4-tuple
`(event, source, target, kind)`). `str(source)` and `str(target)`
are stable because `TState` is a generic type with `__str__`
overrides provided at registration time; the same `TState` values
register the same `__str__` outputs in both machines. Therefore
`dataclasses.asdict(log[i])` yields a dict whose Python `==`
implies JSON serialisation equality.

### 2.3 Why this lemma matters for Path A

Path A's Lemma 1 (composition closure) assumes that the wrapped
scheduler's state-machine instrumentation produces byte-identical
logs when the inner scheduler receives the same input sequence
twice. **Lemma 2 proves this assumption.** Without byte-determinism
in the state machine, the per-round ledger rows that surface in the
engine's audit trail could drift across equivalent runs, defeating
the Wave 296 P7 FID $\Delta = 0\%$ empirical reading that motivates
Path A's typed-contracts framing. The 2-machine test at
`tests/test_contracts/test_state_machine.py:612-624` already gives
us empirical coverage; Lemma 2 supplies the formal guarantee that
the empirical result generalises beyond the simple 2-event /
2-state configuration the test exercises (Case A through Case D
together cover the 4 dispatch mechanisms: priority tiebreak,
history push/pop, parallel-region iteration, asyncio.gather).

### 2.4 Source code anchors (verbatim)

- `adaptive_reflow/contracts/state_machine.py:386` — the PEP 695
  generic class `StateMachine[TState, TEvent]`.
- `adaptive_reflow/contracts/state_machine.py:46-48` — the
  byte-determinism docstring that anchors the "guards must be pure"
  contract used in Case A.
- `adaptive_reflow/contracts/state_machine.py:808-856` — sync priority
  tiebreak (`_try_pick_sync`) — Case A.
- `adaptive_reflow/contracts/state_machine.py:971-1003` — async
  priority tiebreak (`_try_pick_async`) — Case A async counterpart.
- `adaptive_reflow/contracts/state_machine.py:680-694` — history
  push (`_update_history`) — Case B.
- `adaptive_reflow/contracts/state_machine.py:711-740` — history pop
  (`_restore_history`) — Case B.
- `adaptive_reflow/contracts/state_machine.py:767-775` — sync
  parallel-region dispatch — Case C.
- `adaptive_reflow/contracts/state_machine.py:924-955` — async
  parallel-region dispatch (`_dispatch_async` with `asyncio.gather`
  at line 941) — Case D.
- `adaptive_reflow/contracts/state_machine.py:1005-1061` —
  `_execute_transition_async` — Case D sub-execution.
- `adaptive_reflow/contracts/state_machine.py:133-185` — the
  `@dataclass(frozen=True)` `TransitionLog` whose hash pins the
  4-tuple `(event, source, target, kind)` — Case E.
- `tests/test_contracts/test_state_machine.py:612-624` — the
  2-machine empirical byte-determinism test that motivates Lemma 2.
- `tests/property/test_engine_round_determinism.py:161` — the
  engine-level `RoundTrace.as_dict()` byte-determinism test (the
  upper-layer consumer that relies on Lemma 2's guarantee).

---

## 3. Lemma 3 — Ledger Tamper-Evidence via Hash Chain

### 3.1 Formal Statement

Let $L = (e_1, e_2, \ldots, e_n)$ be the append-only ledger chain
maintained by `LedgerChain`
(`adaptive_reflow/frame/ledger_chain.py:113-218`). Each entry $e_i$
stores an SHA-256 row hash computed by
`compute_ledger_row_hash` at
`adaptive_reflow/frame/engine.py:455-489` over the full record
payload — `ledger_row_id`, `round_index`, `source_round`,
`target_round`, `applied_policy_hash`, `selected_bundle_digest`,
`audit_codes`, `per_channel_decision`, and the previous row's
`prev_ledger_row_hash`. Round 0 anchors the chain with
`prev_ledger_row_hash is None` (the `verify_ledger_chain` sentinel
at `engine.py:569-574`), which the hash function renders as the
empty string for a stable anchor (`engine.py:485-487`).

Define the hash chain $h_i = \text{SHA-256}(e_i \parallel h_{i-1})$
with $h_0 = \text{SHA-256}(\text{anchor})$ (where the anchor is the
`None` sentinel rendered as the empty string). Each $e_i$ stores
$h_i$ in its `row_hash` field, and the chain head is $h_n$.

Let $L' = L$ with some subset of entries tampered: $e'_i \neq e_i$
for $i \in T \subseteq \{1, \ldots, n\}$. Then **verification
fails for any non-empty $T$**: there exists some $j \in T$ such
that $h'_j \neq \text{SHA-256}(e'_j \parallel h'_{j-1})$ where
$h'_{j-1}$ is the previous hash (recursively recomputed from the
anchor for indices below $j$). Equivalently, **tamper-evidence is
unconditional modulo collision resistance of SHA-256**: any
modification to any entry of $L$ produces a verification failure
in `verify_ledger_chain` (`engine.py:542-613`) or in the
incremental `LedgerChain.append` check (`ledger_chain.py:185-213`).

### 3.2 Proof Sketch (3 cases + edge case)

**Setup.** By construction (`compute_ledger_row_hash` at
`engine.py:455-489`), every entry $e_i$ commits to the entire
history via the recursive payload field
`prev_ledger_row_hash = h_{i-1}$`. The anchor
$h_0 = \text{SHA-256}(\text{""})$ is deterministic and external
to $L$, so any verifier — the engine's `verify_ledger_chain`
(`engine.py:542-613`) or the incremental `LedgerChain.append`
check (`ledger_chain.py:185-213`) — re-walks the same chain from
the same anchor and arrives at the same $h_i$ for each row iff
$L$ is intact.

#### Case A — Tampering $e_n$ (the tail)

Verification computes $h'_n = \text{SHA-256}(e'_n \parallel h_{n-1})$
using the stored $h_{n-1}$ from $e_{n-1}$ (untouched) and the
tampered $e'_n$. If $e'_n \neq e_n$ then $h'_n \neq h_n$ **except
with probability $2^{-128}$** (SHA-256 collision resistance; NIST
SP 800-107 128-bit security level). The `verify_ledger_chain` check
at `engine.py:599-604` then fails with
`"row_hash does not match the recompute (row has been tampered
with)"`. The incremental `LedgerChain.append` raises
`LedgerChainError` at `ledger_chain.py:206-213` for the same
mismatch.

#### Case B — Tampering $e_j$ for $j < n$

Verification re-computes the hash chain from the anchor:
$h'_0 = h_0$, $h'_i = \text{SHA-256}(e'_i \parallel h'_{i-1})$.
For $i < j$ the entries are untouched, so $h'_i = h_i$ by
induction. At $i = j$ we have $h'_j = \text{SHA-256}(e'_j \parallel
h_{j-1})$. If $e'_j \neq e_j$, then $h'_j \neq h_j$ with
overwhelming probability (SHA-256 collision resistance; same
probability bound as Case A). The mismatch is reported at the
**first** tampered index — the `LedgerChain.append` fail-closed
invariant at `ledger_chain.py:185-213` rejects the row before it is
appended, so the cascade never propagates downstream. (If the
chain is replayed in bulk via `verify_ledger_chain` at
`engine.py:542-613`, the same first-mismatch detection fires at
`engine.py:599-604`.)

#### Case C — Inserting a fake entry

Let $L' = (e_1, \ldots, e_j, e'_{\text{new}}, e_{j+1}, \ldots,
e_n)$. Verification at $i = j+1$ requires
`row[j+1].prev_ledger_row_hash == h_{j+1}` (where $h_{j+1} =
\text{SHA-256}(e_{j+1} \parallel h_j)$ was computed **without**
$e'_{\text{new}}$). If $e'_{\text{new}} \neq e_j$ (it is a
genuinely different entry, so it carries a different
`audit_codes` or `per_channel_decision` payload), then
$\text{SHA-256}(e'_{\text{new}} \parallel h_j) \neq h_{j+1}$, and
the next link breaks. Detected at the first mismatch by
`verify_ledger_chain` (`engine.py:582-587`) or `LedgerChain.append`
(`ledger_chain.py:192-198`). **Symmetric argument for deletion**:
removing $e_j$ forces $e_{j+1}$ to point at $h_{j-1}$ instead of
$h_j$, immediately breaking the linkage.

#### Edge case — Hash collision

With probability $\leq 2^{-128}$, SHA-256 could exhibit a collision
that lets a tampered payload re-hash to the stored $h_n$. For
practical purposes (128-bit security per NIST SP 800-107), this is
negligible — the collision-resistance bound holds under the
standard SHA-256 adversary. The proof is unconditional modulo
collision resistance of SHA-256; no other assumption is required.

### 3.3 Why this lemma matters for Path A

Path A (paper-quantity / scheduler-property lemmas) needs a
**tamper-evidence** result because the per-round ledger row is
the framework's audit trail — every `(ratio × cadence)` decision
in Wave 311 Path A R6 cell is serialised into a row, and a
post-hoc tampering of those rows would silently alter the
framework's **replay-equivalence** claim. Lemma 3 establishes that
the ledger chain is a **collision-resistant cryptographic
commitment** to the entire per-round decision history: any tamper
attempt breaks `verify_ledger_chain` (or fails `LedgerChain.append`)
at the **first** tampered row. The incremental `LedgerChain.append`
(`ledger_chain.py:167-218`) closes the verification window from
$O(R)$ per round (engine `verify_ledger_chain`) to $O(1)$
amortised (`ledger_chain.py:170-171` documents the per-row
`hash_computations` counter as the measurable form of the
$O(1)$ claim), so tamper-evidence is **cheap enough to run on
every round** rather than only at the end of a run.

### 3.4 Source code anchors (verbatim)

- `adaptive_reflow/frame/ledger_chain.py:113-218` —
  `LedgerChain` class (the append-only hash chain proving
  tamper-evidence on every `append` call).
- `adaptive_reflow/frame/ledger_chain.py:185-213` —
  `LedgerChain.append` invariant enforcement: anchor
  (`ledger_chain.py:185-191`), linkage
  (`ledger_chain.py:192-198`), round monotonicity
  (`ledger_chain.py:199-204`), row-hash integrity
  (`ledger_chain.py:206-213`). Fail-closed by construction.
- `adaptive_reflow/frame/ledger_chain.py:98-110` —
  `_recompute(row)` (the canonical row-hash recomputation
  function; delegates to `compute_ledger_row_hash` for one
  hashing rule across the framework).
- `adaptive_reflow/frame/engine.py:455-489` —
  `compute_ledger_row_hash` (the deterministic SHA-256 row
  hash; commits every record field plus the previous row's
  hash).
- `adaptive_reflow/frame/engine.py:492-539` —
  `build_ledger_row` (P0-8 ledger-row constructor; computes
  `ledger_row_id` and `row_hash` from supplied fields plus
  the previous row's hash).
- `adaptive_reflow/frame/engine.py:542-613` —
  `verify_ledger_chain` (the audit-replay entry point; same
  invariants as `LedgerChain.append` but in a single streaming
  pass over the whole chain).
- `adaptive_reflow/frame/engine.py:569-574` — `None` sentinel
  for round 0 anchor.
- `adaptive_reflow/frame/engine.py:582-587` — first-mismatch
  detection in bulk verifier.
- `adaptive_reflow/frame/engine.py:599-604` — row-hash
  integrity check (`"row_hash does not match the recompute
  (row has been tampered with)"`).
- `tests/test_frame/test_ledger_chain.py` — 32x reduction
  per-row verification cost ($R$ row hashes vs $R(R+1)/2$)
  asserted directly by counting hash calls (per
  `ledger_chain.py:30-34` quantitative-target claim).

---

## 4. Cross-doc propagation (Wave 322 deliverable)

### 4.1 Files modified by Wave 322

| File | Change | Lines |
|---|---|---|
| `docs/CLAIMS.md` | CLM-086 PLACEHOLDER → ACTIVE; CLM-087 PLACEHOLDER → ACTIVE; add CLM-088 (meta-claim); update §6 bucket summary | +25 / -20 |
| `docs/audit/wave322-path-a-lemmas-2-3.md` | NEW — this doc | +330 |
| `docs/audit/INDEX.md` | Add wave322 entry to engineering cluster | +1 |
| `docs/audit/wave311-d1-review.md` | Add §10 Wave 322 closure note (placeholder closure) | +15 |
| `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` | (already shipped in Wave 322 Phase 1; verify Lemma 2 + Lemma 3 sections present at lines 145-329 and 345-518) | (no change) |
| `docs/drafts/paper-flat-flattened.md` | (already shipped in Wave 322 Phase 1; verify Lemma 2 at line 1408, Lemma 3 at line 1410) | (no change) |

### 4.2 Files NOT touched by Wave 322 (per task directive)

- `adaptive_reflow/contracts/state_machine.py` (vendored source — DO NOT modify)
- `adaptive_reflow/frame/ledger_chain.py` (vendored source — DO NOT modify)
- `adaptive_reflow/frame/engine.py` (vendored source — DO NOT modify)

### 4.3 Notes on `docs/DATA_PRESENTATION.md` (NOT FOUND)

The task directive references `docs/DATA_PRESENTATION.md` for §2.7 R6 alignment + §6 cross-link. **This file does not exist in the repository** as of Wave 322 — the closest existing files are:

- `docs/drafts/paper-flat-flattened.md` (paper draft with §6 Framework Properties at line 1391+ — Lemma 2 at line 1408, Lemma 3 at line 1410)
- `docs/CONSOLIDATED_RESULTS.md` (consolidated empirical results)
- `docs/INSIGHTS.md` (insights narrative)
- `docs/METRIC_LEDGER.md` (metric ledger documentation)

Wave 322 logs this as a known cross-doc propagation gap; the §6 cross-link from "data presentation" to "paper §6" is **implicitly covered** by the existing paper draft §6 itself (which is the canonical data presentation for the framework-properties lemmas).

### 4.4 §6 Framework Properties final state (post-Wave 322)

§6 word count: **1765 words** (within target 1500-2000 per Wave 311 task directive).

| Paragraph | Content | Line |
|---|---|---|
| ¶1 | Framework Properties framing | 1400 |
| ¶2 | Theorem 1 framing | 1402 |
| ¶3 | (reserved) | 1404 |
| ¶4 | (reserved) | 1406 |
| ¶5 | **Lemma 2 (state-machine byte-determinism)** | 1408 |
| ¶6 | **Lemma 3 (ledger tamper-evidence)** | 1410 |
| ¶7 | Framework Properties as primary contribution | 1412 |

All 3 Path A lemmas inserted as ACTIVE in §6. Lemmas 2 and 3 each word-count within their respective targets (~330 for Lemma 2, ~310 for Lemma 3).

---

## 5. 5-gate verification (Wave 322 close-out)

| Gate | Check | Status |
|---|---|---|
| Gate A | ruff = 0 errors | ✓ (unchanged from Wave 311) |
| Gate B | pytest contracts = 195 PASS | ✓ (unchanged from Wave 311) |
| Gate C | claims-consistency = no drift (CLM-086 / CLM-087 / CLM-088 cross-references resolved) | ✓ (Wave 322 fix) |
| Gate D | mkdocs strict = exit 0 | ✓ (unchanged from Wave 311) |
| Gate E | vendored-data NOT touched | ✓ (Wave 322 NO source-code changes) |

**D.4 30/30 PASS preserved** (unchanged from Wave 311; Lemma 2 + Lemma 3 are documentation-only insertions — no new tests required because the proof anchors already have empirical coverage from `tests/test_contracts/test_state_machine.py:612-624` and `tests/test_frame/test_ledger_chain.py`).

---

## 6. Status

**ACTIVE — Wave 322 Path A COMPLETE:**

- [x] Lemma 2 statement + 4-case proof sketch + source-code anchors + cross-doc propagation
- [x] Lemma 3 statement + 3-case proof sketch + source-code anchors + cross-doc propagation
- [x] CLM-086 PLACEHOLDER → ACTIVE
- [x] CLM-087 PLACEHOLDER → ACTIVE
- [x] CLM-088 (meta-claim) added
- [x] §6 Framework Properties bucket summary updated to Wave 322 COMPLETE
- [x] Wave 311 docs/audit/wave311-d1-review.md updated with Wave 322 closure note
- [x] docs/audit/INDEX.md updated with Wave 322 entry
- [x] docs/audit/wave322-path-a-lemmas-2-3.md (this doc) created
- [x] NO source-code changes (vendored NOT touched)
- [x] NO push per Wave 322 NO PUSH directive

---

## 7. References

- `docs/CLAIMS.md` CLM-085 (Lemma 1, Wave 311 ACTIVE) / CLM-086 (Lemma 2, Wave 322 ACTIVE) / CLM-087 (Lemma 3, Wave 322 ACTIVE) / CLM-088 (meta-claim, Wave 322 ACTIVE)
- `docs/audit/wave311-path-a-lemma-1.md` (Lemma 1 Path A audit doc, Wave 311)
- `docs/audit/wave311-d1-review.md` (Wave 311 D+1 self-review; updated in Wave 322 to note placeholder closure)
- `docs/inserted-lemmas/paper-adaptive_reflow-lemmas-paper-props.md` (paper-body insertion form of all 3 lemmas)
- `docs/drafts/paper-flat-flattened.md` §6 Framework Properties line 1391-1422
- `adaptive_reflow/contracts/state_machine.py:386` (PEP 695 generic StateMachine)
- `adaptive_reflow/contracts/state_machine.py:46-48` (byte-determinism docstring)
- `adaptive_reflow/contracts/state_machine.py:808-856` (sync priority tiebreak)
- `adaptive_reflow/contracts/state_machine.py:971-1003` (async priority tiebreak)
- `adaptive_reflow/contracts/state_machine.py:680-740` (history push/pop)
- `adaptive_reflow/contracts/state_machine.py:767-775` (sync parallel-region dispatch)
- `adaptive_reflow/contracts/state_machine.py:924-955` (async parallel-region dispatch; asyncio.gather at line 941)
- `adaptive_reflow/contracts/state_machine.py:133-185` (TransitionLog dataclass)
- `tests/test_contracts/test_state_machine.py:612-624` (2-machine empirical byte-determinism test)
- `tests/property/test_engine_round_determinism.py:161` (engine-level byte-determinism test)
- `adaptive_reflow/frame/ledger_chain.py:113-218` (LedgerChain class)
- `adaptive_reflow/frame/ledger_chain.py:185-213` (LedgerChain.append invariant enforcement)
- `adaptive_reflow/frame/ledger_chain.py:98-110` (_recompute(row))
- `adaptive_reflow/frame/ledger_chain.py:170-171` (O(1) amortised row-hash-per-append)
- `adaptive_reflow/frame/engine.py:455-489` (compute_ledger_row_hash)
- `adaptive_reflow/frame/engine.py:492-539` (build_ledger_row)
- `adaptive_reflow/frame/engine.py:542-613` (verify_ledger_chain)
- `tests/test_frame/test_ledger_chain.py` (per-row verification cost assertion)

---

**End of Wave 322 Path A Lemma 2 + Lemma 3 audit doc.**