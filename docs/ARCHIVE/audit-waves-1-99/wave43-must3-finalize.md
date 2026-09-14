# Wave 43 — MUST-3 finalize audit (PARTIAL stays PARTIAL, honest accounting)

**Date:** 2026-09-05
**Agent:** Wave 43 Agent A (WF2)
**Scope:** verify whether Wave 42 WF2 (must3-shrink) lifted MUST-3 from
PARTIAL → PASS, and update `todo/framework-freeze-checklist.md`
accordingly.

## TL;DR

**MUST-3 remains PARTIAL** as of end-of-Wave-43. The Wave 42 D.1
shrinks landed cleanly (4 commits, no pytest regressions, see
`wave43-pytest-pollution-fix.md`), but the resulting per-adapter
import footprint uses the **older** P2-9 helper
(`adaptive_reflow.adapters._adapter_common`) rather than the **new**
framework-core glue (`adaptive_reflow.core.{ckpt_loader,
diffusers_wrapper, graph_wrapper, vae_decoder}`) that MUST-3
explicitly gates on.

| MUST-3 acceptance gate | Status |
|---|---|
| ≥5 adapters import from `adaptive_reflow/core/` | **NOT MET** (2 adapters: flowmol3 + self_flow) |
| Per-adapter LOC reduction across the 5 shrunk adapters | **MET** (4 net-shrunk, flowmol3 flat) |
| 0 pytest regressions | **MET** (976 passed, 0 failed) |
| All 16 registered adapters pass `assert_adapter_compliance` | **MET** (D.3 unchanged from Wave 38: 257/257 hand-written + 90/(90+24 skip) auto-battery) |
| MUST-3 status flips PARTIAL → PASS in `framework-freeze-checklist.md` | **NOT FLIPPED** — gate condition #1 (≥5 adapters import from core) is not met. |

This file documents the honest accounting and updates the checklist
with a Wave-43 close-out section that records the actual state.

## 1. Wave 42 WF2 commits — what they actually did

| Commit | Subject | Adapter | Adopted `adaptive_reflow/core/`? | Adopted `_adapter_common`? |
|---|---|---|---|---|
| `491eca3` | Wave 42 Agent A: mnist_fm per-adapter refactor (D.1 shrink) | mnist_fm | **No** | **Yes** (`NativeStateCache`, `seed_from_ids`, `digest_state`) |
| `09c08c0` | Wave 42 Agent B: twodim_fm D.1 shrink (delegate to _adapter_common) | twodim_fm | **No** | **Yes** (same set) |
| `1d3cd2f` | Wave 42 Agent C: rectified_flow_cifar D.1 shrink | rectified_flow_cifar | **No** | **Yes** (same set) |
| `16c8c3a` (in part) | Wave 40 Agent B / Wave 42 Agent D: self_flow D.1 shrink | self_flow | **Yes** (`core.ckpt_loader`, `core.diffusers_wrapper`) | Yes |
| `7d18e33` | Wave 41 Agent B: FlowMol3 v1 adapter — MUST-3 per-adapter refactor onto core/ | flowmol3 | **Yes** (`core.graph_wrapper`) | (already used core from Wave 24) |

So out of the 5 "shrunk" adapters, only **2** (flowmol3, self_flow)
consume `adaptive_reflow/core/`. The other 3 (mnist_fm, twodim_fm,
rectified_flow_cifar) consume `_adapter_common` — the same P2-9 helper
that has been around since Wave 38. From a MUST-3 perspective, those 3
shrinks are **not framework-core glue adoption**, they are a different
kind of refactor (deduplicating inlined helper functions across
adapters).

This is a real mismatch between the **agent task brief** (which said
"4 adapters shrunk") and the **MUST-3 acceptance gate** (which requires
≥5 adapters on `adaptive_reflow/core/`). The Wave 42 agents appear to
have prioritized the lighter-touch `_adapter_common` extraction over
the deeper `core/` refactor — likely because the D.4 regression
vectors block adoption of `core.diffusers_wrapper.DiffusersForwardWrapper`
in mnist_fm / twodim_fm (per `wave42-self-flow-shrink.md` §9
follow-ups).

## 2. Per-adapter LOC accounting

| Adapter | Before Wave 42 | After Wave 42 | Delta |
|---|---|---|---|
| mnist_fm | 957 | 924 | **−33** |
| twodim_fm | 1472 | 1466 | **−6** |
| rectified_flow_cifar | 1356 | 1317 | **−39** |
| self_flow | 1449 | 1488 | **+39** (refactor rationale docstring + framework-core call-site commentary outpaces the inlined-glue removal; see `wave42-self-flow-shrink.md` §5) |
| flowmol3 | (Wave 41 baseline) | (Wave 41 baseline) | **0** (already shrunk Wave 41) |

**Net of 5 shrinks: −39 LOC across the 4 Wave 42 commits + 0 from
flowmol3.** Self-Flow's growth is honest: the inlined glue shrunk
(~15 LOC executable) but the docstring + comments grew (~65 LOC).
Per-adapter **executable code** went down everywhere; **total file
LOC** went down in 3/4 Wave 42 commits and up in self_flow (whose
adoption was the deepest).

## 3. Why MUST-3 cannot flip to PASS yet

The MUST-3 contract (`todo/framework-freeze-checklist.md` §MUST-3)
sets the adoption gate at "≥ 2 of the 4 RANKING adapters (Kanzi,
FreqFlow, MM-FM, LineageFlow) must consume `adaptive_reflow.core`"
(Wave 24 framing) — rephrased by Wave 42 as "≥5 adapters" (broader
threshold). The current state:

| Adapter family | Count of `from adaptive_reflow.core` imports |
|---|---|
| flowmol3 | 1 (graph_wrapper) |
| self_flow | 2 (ckpt_loader + diffusers_wrapper) |
| kanzi | **0** (still inline `OrderedDict` + hand-rolled `_load_torch_model`) |
| freqflow | **0** (same) |
| mmfm | **0** (same) |
| lineageflow | **0** (blocked on upstream `core` source per Wave 39 Agent B) |
| mnist_fm | **0** (uses `_adapter_common`) |
| twodim_fm | **0** (uses `_adapter_common`) |
| rectified_flow_cifar | **0** (uses `_adapter_common`) |

**Total = 2 adapters.** The MUST-3 gate condition "≥5" is not met.

The 3 adapters that *could* trivially adopt `core.ckpt_loader.resolve_candidate_paths`
+ `load_state_dict_strict_safe` (mnist_fm, twodim_fm,
rectified_flow_cifar) all carry the same `*_resolve_weights_path` +
hand-rolled `torch.load + state.get("model", state)` pattern that
self_flow just collapsed (see `wave42-self-flow-shrink.md` §2 + §4).
A future "Wave 44 MUST-3 close" agent could apply the same pattern
to those 3 adapters, lifting the count from 2 to 5. **That work is
not in scope for Wave 43** — this agent's task is verify + finalize,
not drive new shrinks.

## 4. Kanzi / FreqFlow / MM-FM status (deferred per Wave 38/42 scope)

The PHASE-3 trio (Kanzi, FreqFlow, MM-FM) are gated on:

| Adapter | blocker |
|---|---|
| **Kanzi** | per Wave 41 Agent A, Kanzi does carry an `_load_torch_model`-style hand-rolled `state.get("model", state)` chain. Adopting `core.ckpt_loader.load_state_dict_strict_safe` is a ~10-LOC refactor that Wave 41 Agent A left as a follow-up (out of scope — Wave 41 was focused on `@implements` decorator + `force_mode` flag). |
| **FreqFlow** | Same shape as Kanzi. Not yet refactored. Per Wave 38 Agent A scope decision, FreqFlow's framework-core adoption was deferred. |
| **MM-FM** | Wave 21.5 re-spawn noted MM-FM's torch-mode path needs upstream-side alignment (DiT-XL/2 wrapper compatibility) — not yet attempted. |

A future wave could lift the count from 2 to 5 by adding Kanzi +
FreqFlow + one of {mnist_fm, twodim_fm, rectified_flow_cifar} to
the `core/` consumer list. The 2-of-4 Kanzi/FreqFlow/MM-FM
sub-gate is also not met today.

## 5. Framework-freeze-checklist update

This commit appends a "Wave 43 close-out" section to the existing
MUST-3 entry that records the actual state (PARTIAL, 2/5 core
consumers, no flips). The status field at the top of the MUST-3
section stays **PARTIAL** until either:
- 3+ more adapters adopt `adaptive_reflow/core/` (preferred path),
  OR
- the MUST-3 acceptance gate is renegotiated (the user can
  acknowledge `_adapter_common` adoption as equivalent to
  `adaptive_reflow/core/` adoption — a lower-threshold reading that
  would flip the gate to PASS today).

## 6. Files changed in this audit

- `todo/framework-freeze-checklist.md` — appenditive Wave 43 close-out
  section under MUST-3
- `docs/audit/wave43-must3-finalize.md` (this file)
- (no adapter / framework / core code changes)

## 7. Follow-ups for Wave 44+

- **Wave 44 MUST-3 close agent**: pick 3 of the 4 (mnist_fm,
  twodim_fm, rectified_flow_cifar, Kanzi) and apply the same
  `core.ckpt_loader.resolve_candidate_paths` +
  `load_state_dict_strict_safe` refactor that self_flow just shipped.
  All 3 lightweight adapters are mechanical ports of the
  `wave42-self-flow-shrink.md` §2 + §4 pattern.
- **Wave 44 FreqFlow**: FreqFlow has a different pattern (no
  `*_resolve_weights_path`; checkpoint is loaded directly via
  `safetensors`). It needs the `core.diffusers_wrapper` adoption,
  not the ckpt_loader adoption. Different agent scope.
- **Wave 44 MM-FM**: blocked on upstream-DiT-XL/2 alignment.
  Deferred.
- **Kanzi @implements** (Wave 41 Agent A 1-line fix) is already
  shipped. Kanzi's framework-core refactor is the next step.
