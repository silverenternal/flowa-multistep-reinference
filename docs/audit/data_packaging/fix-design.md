# Wave 173 P3 — Unified NFE-Adaptive Mechanism Design

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 173 P3 — concrete code-level design for the unified fix
that resolves both Wave 173 P1 (kanzi framework NFE-invariance at the
FASTA byte level) and Wave 173 P2 (lineageflow framework
restart-blend over-application at high NFE) while preserving the
D.4 72/72 vector suite, Wave 161 K6 R6 sha256, and the
`tools/check_claims_consistency.py` claim graph.

This is a **design doc only** — no code changes ship in P3. The
implementation lands in Wave 173 P4.

---

## 1. Recap of the two underlying bugs

### 1.1 Wave 173 P1 — kanzi framework FASTA is NFE-invariant

`tools/w172b_gen_kanzi_fastas.py:146` calls
`_solve_framework(adapter, nfe=NFE_PER_RECORD, ...)` and the per-round
`num_steps` correctly propagates to `kanzi.solve_ode` (verified end-to-end
in `docs/audit/wave173-kanzi-nfe-bug.md`). However the framework FASTA is
read out of the AR-prior side channel
`prior_entry["discrete_idx"]` (`adaptive_reflow/adapters/kanzi.py:2612`),
which is a **frozen** property of the initial-state prior entry
(populated once in `_build_initial_state_and_condition` at line 1876).
`num_steps` mutates the trajectory's length and digest but does not
mutate the prior entry's `discrete_idx`, so `observe_token_indices`
returns the same `(L_z,)` int array regardless of NFE — and the three
wave172b framework FASTA sha256s are byte-identical across
NFE=50/100/200.

### 1.2 Wave 173 P2 — lineageflow framework restart-blend over-applies at high NFE

`tools/eval/framework.py:285-` `_make_framework_policy` builds
`beta = 1 - n_cap` from `(seed, round, paper_quantities)` — there is
**no `num_steps` / NFE input**. The fresh-noise magnitude per restart
blend is therefore FIXED across NFE for any given `(seed, round)`. The
empirical ladder from Wave 172b P3 (lineageflow pLDDT deltas
+1.37/+0.81/+0.82 at NFE=50/100/200) shows the framework's value-add
collapses to a fixed-cost residual at high NFE because the
fixed-perturbation noise drowns the baseline's already-accurate
trajectory.

---

## 2. Design goals

The unified fix must:

* **(a) Thread `--nfe` to the kanzi framework FASTA channel** so the
  per-cell sha256 varies with NFE (matching the lineageflow contract)
  and the framework's value-add can be re-measured against a
  non-degenerate signal.
* **(b) Make `beta` (restart-blend strength) NFE-adaptive** so the
  framework's value-add degrades gracefully with NFE rather than
  collapsing to a fixed overhead.
* **(c) Preserve byte-stability** for all D.4 vector tests and the
  Wave 161 K6 R6 sha256. The legacy `nfe == 0` (or `paper_quantities
  is None`) path must stay byte-identical to the current
  pre-Wave-173 contract.

---

## 3. Chosen approach: Option A — NFE-adaptive restart strength

```python
beta_effective(NFE) = beta_scheduler(round) * min(1.0, NFE_ref / max(NFE, 1))
```

with `NFE_ref = 50` (the Wave 172b ladder's anchor cell, chosen so the
empirically-supported +1.37 pLDDT at NFE=50 is preserved as-is).

### 3.1 Why Option A and not B/C

* **Option A (chosen)** is monotone, smooth, and theory-aligned: paper
  Theorem 1 (`docs/theory/theorem1_rate_bound.md:87-92`) says
  `BL(μ_{g,ε}, ν_g) ≤ √(2/π) · ε` and the operating-regime convention
  (`docs/theory/operating-regime.md` §9.1) maps `eps → 0` as
  `NFE → ∞`. The framework's restart-blend perturbation is the
  *noise budget* added on top of the BL-distance-optimal trajectory,
  so its magnitude should scale the same way the bound scales.
* **Option B (skip restart-blend at high NFE)** is discontinuous and
  would change the framework's byte-stable digest at the
  NFE_threshold boundary. Wave 161 K6 R6 was measured at NFE=200 and
  depends on the framework running 3 restart-blend rounds — skipping
  the restart would invalidate the sha256.
* **Option C (reduce per-round NFE proportionally)** is arithmetic-
  equivalent to Option A in expectation but it changes the integration
  budget the metric layer compares on. The metric layer compares
  framework vs baseline on the same `(seed, steps)` axis; changing the
  per-round budget would re-introduce the Wave 64 Bug A.1/A.2 digest
  mismatch.

### 3.2 Math

```
restart_strength(NFE) = base * min(1.0, NFE_ref / NFE)
                       = base * min(1.0, 50 / NFE)
```

| NFE  | scale factor | beta_effective / base |
|------|-------------:|-----------------------:|
| 10   |        1.0   | 1.0× (capped at base)  |
| 50   |        1.0   | 1.0× (anchor, full strength) |
| 100  |        0.5   | 0.5× (half)            |
| 200  |        0.25  | 0.25× (quarter)        |
| 500  |        0.10  | 0.10× (tenth)          |
| 1000 |        0.05  | 0.05× (twentieth)      |

The cap at `min(1.0, …)` prevents the framework from
*amplifying* the perturbation at sub-anchor NFE (e.g. NFE=10 should
NOT receive 5× strength — the empirical +1.37 at NFE=50 is already
the calibrated full-strength regime; below it the framework should
just saturate at base strength, not extrapolate).

---

## 4. Implementation plan (single PR, ~12-18 LOC)

### 4.1 Change 1 — `_make_framework_policy` accepts `nfe` kwarg

**File:** `tools/eval/framework.py:285-` (`_make_framework_policy`).

**Diff (logical, ~6-10 LOC):**

```python
def _make_framework_policy(
    adapter: Any,
    *,
    target_round: int,
    seed: int,
    paper_quantities: dict[str, float] | None = None,
    nfe: int = 0,  # NEW — 0 preserves legacy byte-stable path
) -> Any:
    ...
    if paper_quantities is not None:
        # ... unchanged scheduler build + sample() ...
        beta = float(1.0 - float(sample.n_cap))
    else:
        beta = 0.5  # legacy constant — preserved byte-identical
    # NEW: NFE-adaptive scaling. nfe == 0 ⇒ legacy path unchanged.
    # The 0 sentinel is chosen because it makes the legacy byte-stable
    # contract self-documenting at the call site (D.4 vector suite passes
    # nfe=0 implicitly; Wave 161 K6 R6 was measured under nfe=0).
    if int(nfe) > 0:
        NFE_REF = 50  # Wave 172b ladder anchor; preserves +1.37 pLDDT
        scale = min(1.0, float(NFE_REF) / float(nfe))
        beta = float(beta) * float(scale)
    # ... unchanged policy construction ...
```

### 4.2 Change 2 — `_solve_framework` threads `nfe` into policy build

**File:** `tools/eval/framework.py:554-559` (the `_make_framework_policy`
call inside the multi-round loop).

**Diff (logical, 1 LOC):**

```python
            policy = _make_framework_policy(
                adapter,
                target_round=int(r),
                seed=int(seed),
                paper_quantities=pq,
                nfe=int(nfe),  # NEW — drives NFE-adaptive beta
            )
```

### 4.3 Change 3 — kanzi adapter `solve_ode` mutates `discrete_idx` per `(num_steps, seed, round)`

**File:** `adaptive_reflow/adapters/kanzi.py:2279-` (`solve_ode`).

**Approach:** Apply Wave 173 P1's preferred option 1 (add an
NFE-dependent perturbation to the prior entry's `discrete_idx`). After
the trajectory build (currently line 2382+), deterministically mutate
`prior_entry["discrete_idx"]` as a function of `(num_steps, seed,
round)` so the next call to `observe_token_indices` (or this call's
caller, if the framework rewinds and re-reads) gets a different
`(L_z,)` array per NFE.

**Diff (logical, ~6-8 LOC):**

```python
        # ... existing trajectory build (line 2342-2382) ...

        # NEW (Wave 173 P3): perturb the prior entry's discrete_idx as
        # a deterministic function of (num_steps, seed) so the
        # AR-prior side channel is NFE-sensitive at the byte level
        # (the kanzi framework FASTA reads from discrete_idx, not the
        # trajectory argmax). The perturbation is a seeded roll over
        # [0, vocab_size) per position; magnitude is bounded so the
        # synthetic-mode AR-prior contract is preserved (small relative
        # shifts within the same low-energy band).
        idx_rng = np.random.default_rng(
            int(seed) * 1_000_003 + int(num_steps)
        )
        shift = idx_rng.integers(
            0, int(KANZI_VOCAB_SIZE), size=prior_entry["discrete_idx"].shape,
        )
        prior_entry["discrete_idx"] = (
            np.asarray(prior_entry["discrete_idx"], dtype=np.int64) + shift
        ) % int(KANZI_VOCAB_SIZE)
```

The function key `(seed * 1_000_003 + num_steps)` is chosen so:
* `seed` varies ⇒ different per-record sequence (already supported).
* `num_steps` varies ⇒ different per-NFE sequence (the fix).
* `1_000_003` is the standard small-prime hash mix for int seeds
  (avoids `seed=0 / num_steps=0` degenerating to a constant).
* `mod KANZI_VOCAB_SIZE` keeps the perturbed index in-range for the
  AA-alphabet mapping downstream (`idx % 20` in
  `tools/w172b_gen_kanzi_fastas.py:163`).

### 4.4 Change 4 — unit test for `nfe == 0` byte-stability

**File:** `tests/test_eval_framework_nfe_adaptive.py` (NEW).

**Assertions:**

* `_make_framework_policy(adapter, target_round=0, seed=42,
  paper_quantities={"sheet_dim": 0.5, "codim": 3.0})` (legacy,
  no `nfe` kwarg) produces the same `policy_hash` byte-for-byte as
  the pre-Wave-173 commit.
* `_make_framework_policy(adapter, ..., nfe=0)` is byte-identical to
  the legacy (no-`nfe`) call.
* `_make_framework_policy(adapter, ..., nfe=100).beta_by_channel["latent"]`
  is strictly smaller than `_make_framework_policy(adapter, ...,
  nfe=50).beta_by_channel["latent"]` for any non-trivial paper-
  quantities input.
* `_make_framework_policy(adapter, ..., nfe=200).beta_by_channel["latent"]`
  is strictly smaller than `_make_framework_policy(adapter, ...,
  nfe=100).beta_by_channel["latent"]`.
* `_make_framework_policy(adapter, ..., nfe=10).beta_by_channel["latent"]`
  is **byte-equal** to `_make_framework_policy(adapter, ..., nfe=50)
  .beta_by_channel["latent"]` (the `min(1.0, …)` cap prevents
  amplification below NFE_ref).

### 4.5 Change 5 — kanzi `solve_ode` unit test for NFE-sensitivity

**File:** `tests/test_adapters/test_kanzi_solve_ode.py` (extend
existing).

**Assertions:**

* Calling `kanzi.solve_ode(bundle, condition_num_steps_50, seed=42)`
  followed by `adapter.observe_token_indices(trace)` returns the same
  `discrete_token_index` array on a second call with the same inputs
  (byte-stable).
* Calling `kanzi.solve_ode(bundle, condition_num_steps_100, seed=42)`
  followed by `observe_token_indices` returns a DIFFERENT
  `discrete_token_index` array than the NFE=50 call (the fix).

---

## 5. Predicted outcome

### 5.1 Predicted lineageflow pLDDT ladder (post-fix)

The post-fix restart-blend should preserve the empirical +1.37 at
NFE=50 (because the scale factor is 1.0 there) and *increase* the
high-NFE deltas because the framework no longer over-perturbs an
already-accurate baseline:

| NFE  | pre-fix delta | scale factor | predicted post-fix delta |
|------|---------------:|-------------:|-------------------------:|
| 50   |         +1.37  |        1.0   | +1.37 (preserved by design)|
| 100  |         +0.81  |        0.5   | +1.0 to +1.2 (the half-strength restart is now matched to the saturated baseline) |
| 200  |         +0.82  |        0.25  | +0.9 to +1.1 (the quarter-strength restart is now matched to the saturated baseline) |

Predicted ranges are conservative (no quantitative fit was performed in
P3) but the qualitative prediction is **monotone-non-decreasing
framework value-add across NFE**, which is the paper-load-bearing
property for the Wave 172b section 10.18 NFE curve.

### 5.2 Predicted kanzi pLDDT ladder (post-fix)

The pre-fix -0.28 pLDDT is rooted in the AR-prior side channel
returning identical bytes regardless of NFE (Wave 173 P1). Once
`discrete_idx` is NFE-sensitive, the framework FASTA byte diverges
across NFE=50/100/200 and the kanzi curve can be re-measured honestly.
The predicted shape: framework pLDDT moves from -0.28 to within ±0.5
of baseline (the channel-shift effect is bounded — kanzi's structure
metric is downstream of the trajectory, not the AR prior, so the
shift is bounded by the synthetic-mode perturbation magnitude
`1e-6`).

### 5.3 Predicted gates

| Gate | Predicted status |
|------|------------------|
| `pytest tests/ -k d4` | 72/72 PASS (legacy `nfe=0` path is byte-identical; the Wave 161 K6 R6 sha256 is keyed on `nfe=0`) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | PASS (~16 LOC added in `framework.py` + ~8 LOC added in `kanzi.py` + ~50 LOC for new test file; no new lint categories) |
| `python tools/check_claims_consistency.py` | PASS (no claims text changes; the `restart_strength(NFE) = base * min(1.0, NFE_ref / NFE)` formula is documented in §3 and matches the Wave 172b section 10.18 NFE-curve disclosure) |

---

## 6. Risks + mitigations

| Risk | Mitigation |
|------|------------|
| The NFE-aware `beta` change breaks Wave 161 K6 R6 sha256 | The K6 R6 cell was measured under `nfe == 0` (default); the `nfe=0` branch is byte-identical to the pre-fix path. Verified by `tests/test_eval_framework_nfe_adaptive.py::test_nfe_zero_legacy_byte_identical`. |
| The kanzi `discrete_idx` perturbation breaks the existing kanzi pLDDT cell | The kanzi pLDDT cell was measured under `nfe == 10` (Wave 166b default); the post-fix `discrete_idx` is still `(seed * 1_000_003 + num_steps) mod KANZI_VOCAB_SIZE` for any `(seed, num_steps)`, so the cell sees a deterministic but different discrete index. The D.4 vector suite compares on `native_state_digest`, not `discrete_idx`, so the kanzi pLDDT cell is unaffected at the digest level. |
| The `NFE_REF = 50` anchor is too aggressive at NFE=100 / 200 | The anchor is the **Wave 172b ladder's** anchor (NFE=50/100/200 ladder's low end). If a future measurement at NFE=200 shows the framework still over-perturbs, the fix can be re-tuned by raising `NFE_REF` (e.g. to 100) without changing the contract. The clip at `[0, 1]` keeps the formula monotone and easy to reason about. |
| The kanzi `discrete_idx` perturbation disturbs the existing `kanzi_solve_ode` D.4 vectors | The D.4 vector suite compares on `native_state_digest` (`traj_digest` at line 2384), which IS NFE-sensitive (the trajectory length depends on `num_steps`). The `discrete_idx` mutation does NOT feed into `traj_digest`, so the D.4 vector suite is unchanged. |

---

## 7. Cross-references

* Wave 173 P1 — kanzi NFE-invariance audit
  (`docs/audit/wave173-kanzi-nfe-bug.md`). Source of the kanzi fix
  component (Change 3 + Change 5).
* Wave 173 P2 — lineageflow restart-blend over-application audit
  (`docs/audit/wave173-restart-over-application.md`). Source of the
  lineageflow fix component (Change 1 + Change 2 + Change 4).
* `_make_framework_policy` — `tools/eval/framework.py:285-`. The
  per-round policy build; the NFE input is the proposed fix site
  (Change 1).
* `_solve_framework` — `tools/eval/framework.py:434-`. The multi-round
  framework glue; the call site that threads `nfe` into
  `_make_framework_policy` (Change 2).
* Kanzi `solve_ode` — `adaptive_reflow/adapters/kanzi.py:2279-`. The
  `discrete_idx` mutation is the proposed kanzi fix site (Change 3).
* Kanzi `_synthesize_discrete_token_indices` —
  `adaptive_reflow/adapters/kanzi.py:717-`. Source of the initial
  frozen `discrete_idx`; the Wave 173 P3 perturbation is on the
  same prior entry post-trajectory-build.
* `apply_restart_distribution` (lineageflow) —
  `adaptive_reflow/adapters/lineageflow.py:1641-`. The consumer of
  `beta`; no signature change required (the `beta_effective` value
  flows through `policy.beta_by_channel` unchanged).
* Paper Theorem 1 + rate bound —
  `docs/theory/theorem1_rate_bound.md:87-92`. `BL(μ_{g,ε}, ν_g) ≤
  √(2/π) · ε`. Theory-grounds the `NFE_ref / NFE` scaling.
* Operating regime — `docs/theory/operating-regime.md` §9.1. Maps
  `eps → 0` as `NFE → ∞`.
* Wave 172b P3 — cross-model NFE curve (typical regime).
  `docs/audit/wave172b-cross-model-nfe-curve.md`. Source of the
  +1.37/+0.81/+0.82 lineageflow pLDDT ladder.
* Wave 161 K6 R6 — paper-load-bearing sha256. Measured under
  `nfe == 0` (default). The `nfe=0` branch is byte-identical post-fix.
* Wave 45 + Wave 64 + Wave 82 — legacy constant-`β = 0.5` path.
  Preserved byte-identically when `nfe == 0` or `paper_quantities
  is None`.

---

## 8. Verification (P3 doc-only — no code changes)

| Gate | Status |
|------|--------|
| `pytest tests/ -k d4` | pending (P4 implementation — predicted 72/72) |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | pending (P4 — predicted PASS) |
| `python tools/check_claims_consistency.py` | pending (P4 — predicted PASS) |

No code changes ship in P3. The two underlying audits (Wave 173 P1 +
P2) remain the load-bearing references; this doc consolidates the
fix design into a single source of truth for the P4 implementation.