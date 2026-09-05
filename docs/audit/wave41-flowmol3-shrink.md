# Wave 41 — FlowMol3 v1 adapter: per-adapter refactor onto framework core

**Task:** MUST-3 PARTIAL close, `gap-plan-wave32.md` #12 (D.1 shrink adapters).
**Scope:** `adaptive_reflow/adapters/flowmol3.py` (1 of 5 adapters in this wave).
**Date:** 2026-09-05.
**Status:** applied; 15/15 adapter tests pass.

## 1. Why this adapter, and what was actually found

MUST-3 shipped four framework-core glue modules in `adaptive_reflow/core/`
(`ckpt_loader`, `diffusers_wrapper`, `graph_wrapper`, `vae_decoder`) with
**zero per-adapter imports** — the per-adapter refactor was deferred. This
agent took `flowmol3.py`.

The honest finding up front: **`flowmol3.py` was already the smallest real
adapter in the tree** (492 lines vs 3272 for `flowmol3_v2_adapter.py`, 1755
for `kanzi.py`, 1537 for `freqflow.py`). It is the DTB-G2 *placeholder* — it
loads no checkpoint, calls no diffusers pipeline, and decodes no VAE latent.
Three of the four core modules therefore have no surface to attach to here.

So this was **not** a large line-count win, and reporting one would be
misleading. What was available, and what was taken:

| Inlined glue found | Disposition |
|---|---|
| `validate_state_bundle` + `raise CapabilityMissingError`, copy-pasted **6×** | collapsed into one `_require_valid()` helper |
| `to_engine_caps()` — 18-line manual field-by-field copy into `AdapterCapabilities` | replaced with an `**asdict(self)` splat (field names already matched 1:1) |
| `StateBundle(...)` reconstructed field-by-field **2×** (12 kwargs each) | replaced with `dataclasses.replace()` |
| `import hashlib as _hl` / `import json as _json` inside a method body | hoisted to module level |
| `apply_restart_distribution` — an inlined **no-op** with a hand-rolled digest | now delegates to `core.graph_wrapper` (see §2) |

## 2. The real win: `core.graph_wrapper` adoption + a latent bug

FlowMol3's native state is `(x, a, c, e)` — atom positions, atom types,
formal charges, bond/edge features. That is **graph-shaped**, and
`core/graph_wrapper.py` was written with exactly this consumer in mind; its
own source says `DEFAULT_NODE_FEATURE_DIM` is the *"atomic-feature dimension
used by FlowMol3 / ProtBFN / LineageFlow / GraphBFN"*. FlowMol3 v1 is the
intended first consumer and had simply never been wired up.

`apply_restart_distribution` previously returned the state unchanged with a
digest built as:

```python
new_digest = _make_tensor_ref(
    "post_restart", source=state.native_state_digest, policy_id=id(policy)
)
```

**`id(policy)` is a process-local memory address.** The restart digest was
therefore *not* reproducible across processes — a silent violation of the
B.2 byte-stability contract. Verified empirically, two separate interpreters
on the same input:

```
OLD digest: flowmol3:ad82ab85a758b642
OLD digest: flowmol3:82bff1961ee35817     <- differs
```

The refactored path builds deterministic prior/fresh `GraphPayload`s seeded
from the bundle identity, blends them through the framework's canonical
restart mixer `blend_graph_features(prior, fresh, m)` (`blended = m * prior
+ (1 - m) * fresh`), and digests the result via `GraphPayload.digest()`.
`m` is read from `policy.beta_by_channel`, averaged over the adapter's
declared channels and clamped to `[0, 1]`.

Same check after the refactor — stable across processes, and genuinely
driven by `beta` (i.e. the core mixer is exercised, not stubbed):

```
two separate processes, beta=0.5:
  flowmol3:restart:66b9c431e46d5b72010b0e2e2c55c0ad699d6b954473ced474ccbe9490660da2
  flowmol3:restart:66b9c431e46d5b72010b0e2e2c55c0ad699d6b954473ced474ccbe9490660da2

beta sweep:
  0.00 -> flowmol3:restart:f3ce821b5350750dc5053
  0.25 -> flowmol3:restart:a07a6f05461a920dec4f8
  0.75 -> flowmol3:restart:762e58d18f7ac52710252
  1.00 -> flowmol3:restart:02a00ee1e2b5af6ee9abb
  policy=None -> f3ce821b5350750dc5053   (== beta 0.0, full refresh: prior behaviour preserved)
```

## 3. Line counts — reported straight

| Measure | Before | After | Delta |
|---|---|---|---|
| **Executable code lines** | 276 | 264 | **−12** |
| Docstring lines | 118 | 157 | +39 |
| Comment lines | 38 | 40 | +2 |
| Blank lines | 60 | 75 | +15 |
| **Total file lines** | 492 | 536 | **+44** |

Read this honestly: **the inlined glue did shrink (−12 executable lines),
but the file as a whole grew.** The growth is documentation plus the new
restart-blend code path, which replaced a no-op with a real implementation.
Deleting the duplicated glue alone would have removed roughly 45 lines; the
restart implementation and its docs added them back.

D.1's stated target is an **adapter line-count *median* ≤ 500 across 18
adapters** (`todo/framework-internal-metrics.md` §D.1), currently ~1500. It
is not a per-adapter cap, and `flowmol3.py` sits far below the median at
either 492 or 536, so this delta does not move the D.1 metric in either
direction. The adapters that actually move that median are the four
1500–3300-line ones; that remains open work.

## 4. New dependencies

`adaptive_reflow.adapters.flowmol3` now imports from
`adaptive_reflow.core.graph_wrapper`:

- `GraphPayload` — graph-shaped payload carrier (type annotation)
- `blend_graph_features` — canonical restart mixer
- `random_graph_payload` — deterministic seeded payload builder

This is the **first per-adapter consumer of `adaptive_reflow.core`**, which
until now shipped with zero adapter imports.

Stdlib additions: `json`, and `dataclasses.{asdict, replace}`.

No new third-party dependency: `graph_wrapper` is stdlib + numpy at module
level (torch / DGL / PyG stay behind lazy imports), and numpy is already a
hard framework dependency.

## 5. What was deliberately NOT changed

`_make_tensor_ref` and the digest pre-images used by `build_initial_state`,
`solve_ode`, and `inject_forward_noise` are **byte-frozen**. They are pinned
by the D.4 regression vector `regression-vectors/flowmol3.json`, whose
`output_sha256` hashes a record containing `native_state_digest` and
`integrator_config_hash`. Changing the `repr((label, sorted(parts.items())))`
encoding would break the D.4 HARD gate. A note to that effect now sits in
the `_make_tensor_ref` docstring so a future refactor does not trip on it.

`apply_restart_distribution` was safe to change because the D.4 audit tool
(`tools/run_regression_vector_audit.py`) never calls it — its per-condition
record covers `build_initial_state → compose_condition → solve_ode →
observe_endpoint → export_trajectory` only. Confirmed by re-running the
vector tests (§6).

`FlowMol3Capabilities` is retained as a public name (imported by the test
suite) even though it largely mirrors `AdapterCapabilities`; only its
projection method was deduplicated.

## 6. Verification

```
tests/test_adapters/test_flowmol3_adapter.py ......... 15 passed
```

The task brief said 22 tests; the file contains **15** (its own header claims
13, also stale). No tests were added or removed by this refactor — 15 passed
before, 15 pass after.

Cross-suite regression check — D.4 vectors, the full 18-adapter vector
suite, protocol conformance, deep protocol audit, and the registry:

```
tests/test_d4_regression_vectors.py
tests/test_adapters/test_regression_vectors.py
tests/test_universal/test_adapter_protocol_conformance.py
tests/test_adapters/test_protocol_deep_audit.py
tests/test_writer/test_registry.py
  -> 757 passed, 70 skipped
```

The 70 skips are pre-existing and unrelated (missing `data/mnist_fm.npz`
weights, absent `easydict` for `wan2_2_video`, etc.). The D.4 `flowmol3`
re-run test in particular re-derives the pinned hashes on this host and
passes, confirming §5.

## 7. Follow-ups for the other four agents in this wave

- The `_require_valid` collapse and the `dataclasses.replace` substitution
  are mechanical and apply to every adapter carrying the same copy-pasted
  `validate_state_bundle` block. Worth checking in `self_flow.py`,
  `twodim_fm.py`, `mnist_fm.py`, `rectified_flow_cifar.py`.
- Any adapter whose digest incorporates `id(...)`, a `datetime`, or a
  `PYTHONHASHSEED`-sensitive value has the same cross-process instability
  bug found here. Grep for `id(` inside digest construction.
- The real D.1 median win is in `flowmol3_v2_adapter.py` (3272),
  `protbfn_abbfn_adapter.py` (2168), `hidream_i1.py` (1980), and
  `lumina_image_2_0.py` (1849) — these are the checkpoint/diffusers/VAE
  adapters that `core.ckpt_loader`, `core.diffusers_wrapper`, and
  `core.vae_decoder` were actually written for.
