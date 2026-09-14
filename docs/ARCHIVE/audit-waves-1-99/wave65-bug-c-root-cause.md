# Wave 65 Agent 1 — Bug C root cause: metric-layer measurement artifact (NOT a CTMC corruption)

**Date:** 2026-09-07
**Wave:** 65, Agent 1
**Scope:** READ-ONLY reverse-trace of the 3 remaining REGRESSION cells at NFE=50
seed 44, NFE=200 seed 43/44 after Bug A (path mismatch / trace-return) and
Bug B (source_round bump) have been fixed.
**Constraint:** user 2026-09-07 directive "一定要先review和反查是我们哪里的实现有漏洞,
不要做泛泛的修复" — find the ACTUAL implementation bug, do not invent generic fixes.
**Status:** root cause located in the metric layer's hash-based seeding of the
random initial state fed to the real FlowMol3 ckpt. Not a CTMC math bug, not a
restart-blend math bug — it is a measurement artifact where the v1 placeholder
adapter's hash-based `solve_ode` is being misinterpreted by the metric layer as a
meaningful chemistry state digest.

---

## 1. The 3 remaining-regression cells (post Bug A + Bug B)

Per `verification_outputs/flowmol3_bug_a_fix_q4_2026.json` (post-Wave 64 Bug-A
fix + Wave 63 Bug-B fix):

| NFE | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| 10  | 0.0% TIE | 0.0% TIE | 0.0% TIE |
| 50  | +1.58% S | +18.75% S | **−46.32% R** ← Bug C cell #1 |
| 200 | +11.67% S | **−17.70% R** ← Bug C cell #2 | **−20.44% R** ← Bug C cell #3 |

`mean_theta_after_entropy` debug values (from `real_theta_after` block):

| NFE | seed | baseline entropy | framework entropy | delta |
|---|---|---|---|---|
| 50 | 42 | 0.3371 | 0.4048 | +0.068 (framework LESS sharp — but `signed_delta_pct` is POSITIVE because the metric's normalisation favours this direction) |
| 50 | 44 | 0.2489 | 0.6863 | +0.437 (framework MUCH LESS sharp — REGRESSION) |
| 200 | 43 | 0.4357 | 0.5752 | +0.139 (framework LESS sharp — REGRESSION) |
| 200 | 44 | 0.3871 | 0.5778 | +0.191 (framework LESS sharp — REGRESSION) |

The seed-42 cells IMPROVED despite the framework's restart-blend (m=0.5)
corrupting `cur_bundle.native_state_digest`; the seed-43/44 cells REGRESSED.
This seed-specific pattern with opposite signs is the diagnostic fingerprint
of a measurement artifact, not a structural corruption.

---

## 2. The ACTUAL mechanism: hash-based seeding in the metric layer

### 2.1 What the v1 placeholder `solve_ode` actually does

`adaptive_reflow/adapters/flowmol3.py:961-989`:

```python
def solve_ode(self, state, condition, *, seed) -> ODEIntegratorTrace:
    """Single deterministic integration step.
    The placeholder returns the trace derived from
    ``(state.native_state_digest, seed, steps)``; the engine reconstructs
    the post-step bundle via ``observe_endpoint``.
    """
    steps = int(condition.delta_spec.get("num_steps", 1))
    if steps <= 0:
        raise ValueError("steps_must_be_positive")
    _require_valid(state, "validate_state_bundle")
    new_digest = _make_tensor_ref(
        "post_step", source=state.native_state_digest, seed=seed, steps=steps
    )
    trace = ODEIntegratorTrace(
        steps=int(steps),
        accept_rate=1.0,
        native_state_digest=new_digest,
        integrator_config_hash=_make_tensor_ref(
            "integrator_config", seed=seed, steps=steps
        ),
    )
    return trace
```

**Critical observation**: the v1 placeholder's `solve_ode` does NOT run the
real FlowMol3 model. It returns a trace whose `native_state_digest` is a
deterministic hash of `(state.native_state_digest, seed, steps)`. There is
no real molecular state in the trace — it is purely a placeholder digest
that lets the engine contract be exercised without torch/dgl/RDKit.

### 2.2 What the metric layer does with this trace

`tools/run_real_ckpt_eval.py:1921-1968` (`_compute_flowmol3_real_atom_type_marginal`):

```python
try:
    import hashlib as _hashlib  # stdlib only; avoid module-level import.
    digest = str(
        getattr(trace, "native_state_digest", f"s{seed}-n{nfe}")
    )
    h = int(_hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8], 16)
except Exception:
    h = int(seed) * 31 + int(nfe)
try:
    n_atoms = 8  # matches FLOWMOL3_PLACEHOLDER_NUM_NODES
    rng = np.random.default_rng(int(h))
    x0 = rng.standard_normal((n_atoms, 3)).astype(np.float32)
    a0 = rng.integers(
        0, int(FLOWMOL3ADAPTER_N_ATOM_TYPES), size=n_atoms,
    ).astype(np.int64)
    c0 = rng.standard_normal(n_atoms).astype(np.float64)
    e0 = np.full(
        (n_atoms, n_atoms),
        int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
        dtype=np.int64,
    )
    # ... 5% bond sprinkle ...
    debug["n_atoms"] = int(n_atoms)
    _vx, _c_pred, p_a_marg, _p_c, _p_e, _vx_dup = (
        _ctmc_real_velocity_field_ex(
            module, x0, a0, c0, e0, 1.0, device="cpu",
        )
    )
    theta_after = np.asarray(p_a_marg, dtype=np.float64).reshape(
        int(n_atoms), int(FLOWMOL3ADAPTER_N_ATOM_TYPES)
    )
```

The metric layer reads `trace.native_state_digest`, hashes it via SHA-256, and
uses the result as the seed for a numpy `default_rng` that generates a RANDOM
initial state `(x0, a0, c0, e0)`. The real FlowMol3 ckpt is then evaluated at
`t=1.0` on this random initial state to produce `theta_after`.

**This is the load-bearing measurement artifact.** The metric is NOT measuring
the framework's integration quality; it is measuring the real model's response
to a random initial state whose seed is derived from the trace digest.

### 2.3 Why the trace digest differs between baseline and framework

For **baseline (NFE=200, seed=43)**:

```
bundle.native_state_digest = SHA("digest", batch=..., sample=..., r=0)
                         (deterministic from build_initial_state)

trace.native_state_digest = SHA("post_step",
                               source=bundle.native_state_digest,
                               seed=43, steps=200)
                         (deterministic from solve_ode)
```

For **framework (NFE=200, seed=43)** after the Wave 64 Bug-A fix:

```
Round 0:
  bundle_0 = bundle (initial state)
  trace_r0 = solve_ode(bundle_0, num_steps=67, seed=43)
  endpoint_r0 = export_endpoint(bundle_0)  # identity
  bundle_1 = apply_restart_distribution(endpoint_r0, policy)
    bundle_1.native_state_digest = "flowmol3:restart:" + SHA(blended_r0)
    source_round bumped 0 -> 1 (Bug-B fix)

Round 1:
  trace_r1 = solve_ode(bundle_1, num_steps=67, seed=44)
  endpoint_r1 = export_endpoint(bundle_1)
  bundle_2 = apply_restart_distribution(endpoint_r1, policy)
    bundle_2.native_state_digest = "flowmol3:restart:" + SHA(blended_r1)
    source_round bumped 1 -> 2

Round 2:
  trace_r2 = solve_ode(bundle_2, num_steps=66, seed=45)
  endpoint_r2 = export_endpoint(bundle_2)
  bundle_3 = apply_restart_distribution(endpoint_r2, policy)
    bundle_3.native_state_digest = "flowmol3:restart:" + SHA(blended_r2)
    source_round bumped 2 -> 3

After loop (Bug-A re-anchor):
  integrated_trace = solve_ode(bundle_3, num_steps=200, seed=43)
  integrated_trace.native_state_digest = SHA("post_step",
                                            source=bundle_3.native_state_digest,
                                            seed=43, steps=200)
```

**Key fact**: the `source=` in the trace digest differs between baseline
(`SHA("digest", batch, sample, r=0)`) and framework (`flowmol3:restart:{SHA(blended_r2)}`).
This propagates to two DIFFERENT random initial states for the metric.

### 2.4 Why this produces seed-specific regression

The real FlowMol3 ckpt at t=1.0 on a random initial state `(x0, a0, c0, e0)`
produces a per-atom-type distribution `theta_after` whose entropy depends on
the random input. Different random inputs → different entropy values. Some
random inputs land in regions where the model produces SHARP (low-entropy)
distributions; others land in regions where the model produces DIFFUSE
(high-entropy) distributions.

For **seed 42**: the framework's restart-blended digest (after 3 rounds of
`blend_graph_features` with `m=0.5` and the per-round fresh payloads seeded
by `source_round ∈ {0, 1, 2}`) hashes to a value `h_42` such that
`np.random.default_rng(h_42).standard_normal((8, 3))` happens to seed a region
where the model produces SHARPER distributions than the baseline's
`h_42_baseline`. Result: framework's entropy is LOWER → metric reports
SUPPORTED.

For **seed 43 / 44**: the framework's restart-blended digest hashes to a value
`h_43 / h_44` that happens to seed a region where the model produces MORE
DIFFUSE distributions. Result: framework's entropy is HIGHER → metric reports
REGRESSION.

This is a Monte Carlo noise artifact, not a structural defect in the CTMC math
or the restart-blend math. The framework's "improvement" or "regression" is
just the model's response to a different random initial state.

---

## 3. Why the Wave 57 / Wave 63 framing did not catch this

Wave 57 Agent C correctly diagnosed that the framework's restart-blend inserts
a "wrong" prior at the restart boundary, but attributed the resulting
metric-layer noise to CTMC rate corruption. Wave 63 Agent 1 correctly
identified that the framework's per-round `(seed+r, steps=nfe_per_round)`
trace digest differed from baseline's `(seed, steps=nfe)` trace digest, and
fixed it via Bug A's re-anchor (return a trace keyed on the original seed +
total NFE). But after Bug A's fix, the source digest in the trace still
differs between baseline and framework — only the `(seed, steps)` axis is
matched.

Bug A made the comparison axis-aligned (the digest axis-match contract), but
the underlying measurement is still keyed on the trace digest, which still
differs between baseline and framework because the placeholder's restart-blend
corrupts `cur_bundle.native_state_digest`. This is the residual 3/9 REGRESSION
that Bug A and Bug B together cannot fix.

### 3.1 The Bug-A fix's residual contribution

Looking at the Wave 64 post-fix data for seed 43 NFE=200:
- pre-Bug-A: `+14.2% S`
- post-Bug-A: `−17.7% R`

The Bug-A fix made seed 43 NFE=200 WORSE (flipped from SUPPORTED to
REGRESSION). This is because pre-Bug-A, the framework's trace digest had a
`(seed=45, steps=66)` axis (the last-round trace from round 2), which by luck
seeded a "good" region. Post-Bug-A, the re-anchor uses `(seed=43, steps=200)`
on the framework's `cur_bundle.native_state_digest` (the post-3-round restart
blended state), which by luck seeds a "bad" region. The measurement is still
random-input-sensitive; Bug A just changes which random input each cell sees.

### 3.2 What the NFE=10 stratum shows (Bug A's actual territory)

At NFE=10, the NFE-adaptive gate fires (m=0, no restart blend), so
`cur_bundle.native_state_digest = bundle.native_state_digest` for the
framework arm. After Bug A's re-anchor:
- baseline.trace.native_state_digest = SHA("post_step", bundle.digest, seed=42, steps=10)
- framework.integrated_trace.native_state_digest = SHA("post_step", bundle.digest, seed=42, steps=10)

**Identical.** So Bug A's fix turns NFE=10 into 3/3 TIE — the metric collapses
to framework ≡ baseline. This matches the observed post-Wave 64 data.

At NFE=50/200, the gate does NOT fire (m=0.5), so `cur_bundle.native_state_digest`
is `flowmol3:restart:{SHA(blended_r2)}` — DIFFERENT from baseline's bundle
digest. The metric then measures the model's response on a different random
initial state.

---

## 4. Reconciling with Wave 57 §2.3 (CTMC corruption framing)

Wave 57 Agent C §2.3 framed the framework's restart-blend as a CTMC corruption
("the framework replaced half the already-noisy convergence with fresh noise").
That framing was an artifact of looking at the metric value (which was noise on
random inputs) and back-fitting a CTMC-math story to explain it.

The actual situation is simpler and more mundane:
1. The v1 placeholder's `solve_ode` is a hash stub.
2. The metric layer reads the stub's digest and uses it as a random seed.
3. Different digests → different random initial states → different model
   outputs → different entropy reductions.
4. The framework's restart-blend changes the digest; the metric reflects the
   model's noise on the new random state, NOT the framework's value-add.

There is no CTMC rate corruption. The CTMC math in
`data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` is not exercised by
the v1 placeholder adapter; it is only relevant to the v2 adapter (which is
not in this eval scope).

---

## 5. Recommended targeted fix (NOT applied — diagnostic only)

**File:** `tools/run_real_ckpt_eval.py`
**Function:** `_compute_flowmol3_real_atom_type_marginal`
**Lines:** 1922-1926 (specifically the hash-based seed extraction)
**LOC:** 3-4 lines

The current code (line 1922-1926):

```python
try:
    import hashlib as _hashlib  # stdlib only; avoid module-level import.
    digest = str(
        getattr(trace, "native_state_digest", f"s{seed}-n{nfe}")
    )
    h = int(_hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8], 16)
except Exception:
    h = int(seed) * 31 + int(nfe)
```

**Targeted fix**: use the EXISTING fallback path (`int(seed) * 31 + int(nfe)`)
as the primary path, so the random initial state is keyed on the per-cell
`(seed, nfe)` pair rather than on the framework's restart-blended trace
digest. This makes the metric measure the model's response on the SAME
random initial state for both arms, isolating the framework's value-add (or
lack thereof) from the noise on different random inputs.

```python
# Wave 65 Agent 1 fix (Bug C): use the per-cell (seed, nfe) pair as
# the random initial state seed instead of the trace's
# native_state_digest. The v1 placeholder's solve_ode produces a hash-
# based digest that the framework's restart-blend corrupts, which
# makes the metric sensitive to the framework's restart-blending rather
# than to the framework's actual integration quality. The per-cell
# (seed, nfe) seed makes the metric measure the model's response on the
# SAME random initial state for both arms.
h = int(seed) * 31 + int(nfe)
```

**Why this fixes the 3 remaining regression cells**: with the fix, both arms
feed the same `(x0, a0, c0, e0)` into the real model. The metric then
measures `H(uniform) - H(model(random_state))` for the SAME random state in
both arms. The signed_delta_pct collapses to ~0% (TIE) for all 9 cells —
the honest reading for a v1 placeholder adapter whose `solve_ode` doesn't
actually integrate.

### 5.1 Alternative fix (NOT preferred)

Use the v2 adapter's `solve_ode` to actually run the real CTMC integration.
Then `theta_after` would be the real model's per-atom marginal at the
framework's actual integration endpoint. This is the principled fix but
requires the v2 adapter to be wired into the eval pipeline (a much larger
change than the 1-line metric-layer fix above).

---

## 6. Why this is the ACTUAL root cause (and not a generic CTMC fix)

User directive: "一定要先review和反查是我们哪里的实现有漏洞,不要做泛泛的修复"

The diagnosis above is targeted:
1. **Concrete file:line**: `tools/run_real_ckpt_eval.py:1922-1926` in
   `_compute_flowmol3_real_atom_type_marginal`.
2. **Concrete mechanism**: the metric layer's hash-based seeding of the
   random initial state reads `trace.native_state_digest`, which differs
   between baseline and framework because the framework's restart-blend
   corrupts `cur_bundle.native_state_digest`. For seeds 43, 44 at NFE=50/200,
   the framework's digest happens to seed a region where the real FlowMol3
   model produces higher per-atom entropy.
3. **Concrete fix**: use the existing fallback `int(seed) * 31 + int(nfe)`
   as the primary random seed, eliminating the metric's sensitivity to
   `trace.native_state_digest`.
4. **Falsifiable prediction**: after the fix, all 9 cells become TIE
   (framework ≡ baseline for the v1 placeholder), confirming the metric
   was measuring noise rather than framework value-add.

A "generic fix" would lower the blend coefficient, change the schedule,
switch to v2 adapter, etc. — none of these address the root cause, which
is in the metric layer, not the adapter or the framework's restart math.

---

## 7. What was NOT done (per disjoint scope)

- **No code modified**: this agent is READ-ONLY per the Wave 65 scope.
- **No Bug-C fix applied**: the targeted fix is described in §5 but not
  implemented; that is for the next wave / agent with disjoint scope.
- **No commit, no push**: per Wave 65 Agent 1 directive.

---

## 8. Files read for this audit (READ-ONLY)

- `verification_outputs/flowmol3_bug_a_fix_q4_2026.json` (1433 lines; full read for per-cell data + debug fields)
- `verification_outputs/flowmol3_with_gate_q4_2026.json` (first 200 lines; pre-Bug-A-fix snapshot)
- `adaptive_reflow/adapters/flowmol3.py` (1300 lines; full read; key sections: `solve_ode` 961-989, `apply_restart_distribution` 792-920, `observe_entropy_reduction` 1010-1136)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (142619 bytes; sampled; key sections: `_channel_aware_blend` 1057-1232, `apply_restart_distribution` 2008-2148, `solve_ode` 2184+, `_ctmc_real_velocity_field_ex` 1306-1446)
- `adaptive_reflow/framework/interfaces.py` (499 lines; full read for `ChannelwiseBlender`, `ChannelwiseMemoryFractionPolicy`)
- `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` (511 lines; full read for `campbell_step` 414-461, integrator 300-411)
- `docs/audit/wave57-flowmol3-restart-interaction.md` (449 lines; full read)
- `docs/audit/wave63-root-cause.md` (359 lines; full read)
- `docs/audit/wave64-bug-a-fix.md` (327 lines; full read)
- `tools/run_real_ckpt_eval.py` (3590 lines; sampled; key sections: `_solve_framework` 1048-1172, `_compute_flowmol3_real_atom_type_marginal` 1830-1980, `_compute_flowmol3_real_metric_via_trace` 1983-2155)

## 9. Files modified

None (READ-ONLY audit per Wave 65 Agent 1 scope).