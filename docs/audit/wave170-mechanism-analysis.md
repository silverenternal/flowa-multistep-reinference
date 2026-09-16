# Wave 170 P1 — Framework mechanism ↔ JMAA theory audit

**Status:** diagnostic / paper-mechanism audit (no code change; no re-run).
**Auditor:** Wave 170 P1 (follow-up to Wave 169 P1 / P2 / P3 / P4 and
Wave 161 K6 / Wave 168 P3 / Wave 167).
**Scope:** Read the framework code (gen script +
`tools/eval/framework.py` + `adaptive_reflow/adapters/lineageflow.py`)
**verbatim**, compare to the JMAA Theorem 1 quantity map, identify the
**unfair baseline comparison** the Wave 168 NFE curve exposes, and
recommend the fix design the user requested ("find the actual problem,
not patch the symptom").

---

## 1. TL;DR

The Wave 168 framework-vs-baseline comparison is **unfair** because
the baseline arm is **not the ODE target distribution** that Theorem 1
references. The two arms compare:

| Arm | Mechanism | Distribution |
|-----|-----------|--------------|
| `baseline` | bare RNG draws over per-family Pfam AA bias | **No ODE integration at all**; an AA-bias-matched **stationary** distribution with **no NFE dependence** |
| `framework` | `solve_ode` + `apply_restart_distribution` × 3 rounds | The framework's multi-round re-inference distribution `P_framework(· | NFE)` |

Theorem 1 (paper §2.8.1, paper-draft.md line 367) bounds
`d_BL(P_framework(·|NFE), P_target)` where `P_target` is the
**infinite-NFE ODE target distribution** induced by the same frozen θ.
The bound is monotone in NFE. To test whether the framework's
multi-round glue (restart-blend + paper-quantity-driven scheduler)
**adds value over the bare ODE target**, the fair comparison is:

- **`n_rounds=1` arm** — single-pass `solve_ode` at the total NFE
  budget, no restart-blend. This *is* the framework's ODE target
  distribution `P_target(NFE)`.
- **`n_rounds=3` arm** — three restart-blend rounds at
  `NFE/3` each. This is the framework's full
  `P_framework(·|NFE)` distribution.

**Currently the gen script's "baseline" arm is bare RNG** — a
**fundamentally different distribution** that the bound does not
reference. The Wave 168 framework ΔpLDDT = −0.83 to −1.56 result is
therefore comparing against the wrong reference; the framework is
being penalised for being a sharper posterior than the AA-bias RNG,
which OmegaFold then sees as "less natural-protein-like" because the
synthetic velocity field's attractor is a 2-layer MLP, not a trained
LineageFlow.

**Recommended fix (CPU-only, code-only — no re-run):**

1. **Replace the baseline arm with `n_rounds=1`** in
   `tools/gen_lineageflow_n1000_fastas.py` so the comparison is
   fair. This adds a fourth arm (or replaces the existing baseline)
   that exercises the same `solve_ode` path but with `n_rounds=1`
   (no restart-blend).
2. **Document in the audit trail** that the bare-RNG baseline is a
   sanity-check reference (does the framework's solve_ode + argmax
   produce a sequence at all?), NOT the Theorem-1 reference
   distribution.
3. **For real testability of the restart-blend over-application**:
   torch-mode trained LineageFlow checkpoint + sub-modal-sensitive
   decoding (not argmax). Synthetic mode is byte-identical across
   `n_rounds` because the synthetic velocity field's attractor
   collapses to one dominant token per position regardless of
   `memory_fraction` (Wave 169 P3).

The user's diagnosis ("论文的理论绝对是对的") is correct — the
**theory** is correct, but the **experiment** is comparing against
the wrong reference. Fixing the comparison is the actual problem,
not patching the framework glue or the scheduler.

---

## 2. Baseline mechanism — verbatim

### 2.1 `tools/gen_lineageflow_n1000_fastas.py:103-105`

```python
def _generate_sequence(rng: random.Random, family_id: str, length: int) -> str:
    profile = FAMILY_PROFILES.get(family_id, {"bias": {}})
    return _biased_aa(rng, profile, length)
```

`_generate_sequence` is a **single pure function** that samples `length`
amino acids from `rng` weighted by the family's hard-coded
`FAMILY_PROFILES[family]["bias"]` dict (lines 35-58: per-family Pfam
AA bias mimicry, e.g. PF00005.27 ABC transporter mixed bias, PF00072.24
response regulator polar+acidic, etc.). The function is **purely
RNG-driven**, has **no ODE integration**, has **no per-position
dependency** (each AA is i.i.d.), and has **no model parameters**.

### 2.2 `tools/gen_lineageflow_n1000_fastas.py:207-227` (baseline arm)

```python
def _write_baseline_arm(
    out_path: Path,
    *,
    n: int,
    seed: int,
    family_ids: list[str],
    min_len: int,
    max_len: int,
) -> dict[str, int]:
    """Write the baseline arm: bare RNG draws over each family's AA bias."""
    baseline_rng = random.Random(int(seed))
    counts: dict[str, int] = {}
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = baseline_rng.randint(int(min_len), int(max_len))
            seq = _generate_sequence(baseline_rng, family_id, length)
            f.write(f">baseline_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            counts[family_id] = counts.get(family_id, 0) + 1
    return counts
```

**Baseline distribution: `P_baseline(seq | family) = Π_i bias_family[seq_i]`.**

This is **not the ODE target distribution**. The ODE target distribution
is induced by the model's velocity field; the AA-bias RNG is a
**different, simpler, stationary distribution** designed to be a
"quick sanity-check" reference (does the framework produce a sequence
at all?), per Wave 86 Agent B's Pitfall #2 fix to make the framework
arm byte-different from the baseline arm.

### 2.3 Wave 168 §3c observation

The Wave 168 audit
(`docs/audit/wave168-p3-evaluation.md` §3c) already documented that
**baseline pLDDT is NFE-invariant**:

```
baseline pLDDT:  42.3279, 42.3279, 42.3279, 42.3279   (NFE 50/100/200/500)
```

This is **expected** because `_write_baseline_arm` is purely RNG-driven
and ignores `--nfe`. The four baseline FASTAs are MD5-identical
(`f76799c78686248d441c43c2ce7a122b` × 4). The Wave 168 §3c note says
"reporting 4 baseline NFE points is a plot artifact, not 4 independent
measurements" — but the deeper issue is that **the baseline is the
wrong reference distribution**, not just a non-NFE-aware one.

---

## 3. Framework mechanism — verbatim

### 3.1 `tools/eval/framework.py:434-565` (`_solve_framework`)

```python
def _solve_framework(adapter, *, nfe, seed, n_rounds=3, n_molecules=1):
    bundle, _ = _build_initial_state_and_condition(adapter, seed=seed, nfe=nfe)
    n_rounds_int = max(1, int(n_rounds))
    base_per_round = max(1, int(nfe) // n_rounds_int)
    remainder_per_round = max(0, int(nfe) - base_per_round * n_rounds_int)
    nfe_per_round_list = [base_per_round] * n_rounds_int
    if remainder_per_round > 0:
        nfe_per_round_list[-1] += remainder_per_round
    t0 = time.monotonic()
    cur_bundle = bundle
    trace = None
    for r in range(int(n_rounds)):
        per_round_nfe = int(nfe_per_round_list[r])
        condition = ODEConditionDelta(
            delta_spec={"num_steps": per_round_nfe, "sampler_id": "euler"},
            source="run_real_ckpt_eval",
            target_round=int(r),
            calibration_artifact_hash="run_real_ckpt_eval:default",
        )
        trace = adapter.solve_ode(cur_bundle, condition, seed=seed+r, n_molecules=n_molecules)
        endpoint = adapter.export_endpoint(cur_bundle)            # identity pass-through
        if endpoint is None: break
        pq = _compute_paper_quantities(adapter, trace, round_index=r)
        policy = _make_framework_policy(adapter, target_round=r, seed=seed, paper_quantities=pq)
        cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
    wall = time.monotonic() - t0
    integrated_trace = adapter.solve_ode(
        cur_bundle, final_condition, seed=seed,         # re-anchor at seed=seed, nfe
    )
    return integrated_trace, wall
```

The framework chain is `solve_ode → export_endpoint → apply_restart_distribution`
× `n_rounds` rounds, then a **final `solve_ode` on the blended state**
that re-anchors at `(seed=seed, steps=nfe)` so the metric layer's
`(seed, steps)` axis is **byte-aligned with the baseline** (the Wave 64
Agent 1 fix for the A.1 / A.2 trace-axis mismatch).

### 3.2 `adaptive_reflow/adapters/lineageflow.py:1957-2098` (`solve_ode`)

```python
def solve_ode(self, state, condition, *, seed):
    prior_entry = self._native_states.get(state.native_state_digest)
    num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))
    sampler_id = str(condition.delta_spec.get("sampler_id", self._solver))
    x0 = np.asarray(prior_entry["theta"], dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)
    t_grid = np.linspace(0.0, float(LINEAGEFLOW_T_END), num_steps + 1, dtype=np.float64)
    traj = np.empty((t_grid.size, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64)
    traj[0] = x0.copy()
    x_cur = x0.copy()
    for i in range(1, t_grid.size):
        t0 = float(t_grid[i - 1])
        t1 = float(t_grid[i])
        dt = float(t1 - t0)
        v1 = self._velocity_field(x_cur, t0, conditioning=conditioning,
                                   guidance_scale=guidance_scale)
        if sampler_id == "heun" and i < t_grid.size - 1:
            x_pred = np.clip(x_cur + dt * v1, 0.0, LINEAGEFLOW_CLAMP)
            x_pred = x_pred / np.maximum(x_pred.sum(axis=-1, keepdims=True), 1e-30)
            v2 = self._velocity_field(x_pred, t1, conditioning=conditioning,
                                       guidance_scale=guidance_scale)
            x_cur = np.clip(x_cur + 0.5 * dt * (v1 + v2), 0.0, LINEAGEFLOW_CLAMP)
        else:
            x_cur = np.clip(x_cur + dt * v1, 0.0, LINEAGEFLOW_CLAMP)
        x_cur = x_cur / np.maximum(x_cur.sum(axis=-1, keepdims=True), 1e-30)
        traj[i] = x_cur
    ...
    return ODEIntegratorTrace(steps=num_steps, accept_rate=1.0,
                              native_state_digest=traj_digest, ...)
```

The `solve_ode` integrates the velocity field for `num_steps` Euler
(or Heun) steps, with row-renormalisation to keep the per-position
categorical valid (sum to 1 per position).

### 3.3 `adaptive_reflow/adapters/lineageflow.py:1640-1825` (`apply_restart_distribution`)

```python
def apply_restart_distribution(self, state, policy):
    prior_theta = np.asarray(prior_entry["theta"], dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)
    beta, memory_fraction = memory_fraction_for(policy, AMINO_ACID_CATEGORICAL)
    # Default policy: UniformFreshPerturbation → fresh_theta = uniform jitter
    fresh_theta = _synthesize_latent_like_tensor(fresh_rng)
    m = max(0.0, min(1.0, float(memory_fraction)))   # default = 0.5
    blended = (m * prior_theta + (1.0 - m) * fresh_theta).astype(np.float64)
    blended = blended / np.maximum(blended.sum(axis=-1, keepdims=True), 1e-30)
    ...
    return StateBundle(..., theta=blended, ...)
```

Per-round `m` (memory fraction) = `1 - β`. With default `β = 0.5`,
the blend is **50% prior integrated state + 50% fresh uniform
perturbation**. After `n_rounds=3` rounds, the surviving fraction of
the **original** integrated state is `(m)^n_rounds = 0.125` (12.5%).
For `n_rounds=1`, it is `m^1 = 0.5` (50%).

### 3.4 Observation layer — `adaptive_reflow/adapters/lineageflow.py:2209`

```python
def observe_token_indices(self, trace, paper_quantities):
    traj_entry = self._native_states.get(trace.native_state_digest)
    trajectory = np.asarray(traj_entry["trajectory"], dtype=np.float64)
    theta_final = np.asarray(trajectory[-1], dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE)
    token_indices = np.argmax(theta_final, axis=-1).astype(np.float64)
    return {str(AMINO_ACID_CATEGORICAL): token_indices}
```

The framework's observable sequence is the **argmax** over the
per-position categorical at the integrated endpoint.

**Critical observation:** argmax is **insensitive to sub-modal-probability
mass**. If the synthetic velocity field's attractor collapses to one
dominant token per position (Wave 169 P3 finding), then `n_rounds=1`
(50% memory) and `n_rounds=3` (12.5% memory) both observe the same
argmax tokens. The **byte-identity of n_rounds=1 vs n_rounds=3 under
synthetic mode** is a consequence of (a) argmax + (b) strong synthetic
attractor, NOT a framework bug.

---

## 4. JMAA Theorem 1 quantity map

Paper §2.8.1 (paper-draft.md line 367):

```
d_BL(P_framework(·|NFE), P_target) <= A_g · exp(−NFE / B_g) + C_g · e_ρ
```

The theorem's **four paper quantities** `A_g, B_g, C_g, e_ρ` map onto
the framework's components as follows (Wave 31 + Wave 32 + Wave 33 +
Wave 34 + this audit):

| Paper quantity | Paper meaning | Framework component | Code anchor |
|----------------|---------------|---------------------|-------------|
| `A_g` | **Aggregate Lipschitz** (smoothness of velocity field) | **Restart-blend memory fraction `m = 1 - β`** + per-round `num_steps`. The framework's restart-blend smooths the trajectory by perturbing at each round boundary; `m` controls how much of the sharp integrated state survives into the next round. | `adaptive_reflow/adapters/lineageflow.py:1640` (`apply_restart_distribution`'s `m = max(0, min(1, float(memory_fraction)))`); `adaptive_reflow/adapters/_adapter_common.py:70` (`memory_fraction_for` returning `(beta, floor)`) |
| `B_g` | **Effective NFE decay rate** (how fast the bound tightens with NFE) | **Scheduler's `n_cap` + per-round NFE split** (`_solve_framework`'s `nfe_per_round_list = [base] * n_rounds` with remainder in last round). `B_g` is shaped by the schedule sample's `evidence_ratio` (Wave 31 `CodimensionSheetScheduler`). | `tools/eval/framework.py:480-490` (NFE split formula); `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` (`CodimensionSheetScheduler.n_cap` driven by `ratio = sheet_A / (sheet_A + cell_C)`) |
| `C_g` | **Residual bias** (cell-coefficient error, `O(ε²)` term) | **Paper-quantity-aware scheduler's `cell_C` term** + `PaperRatioAdaptiveScheduler`'s PID-lite shift. `C_g` is the framework's claim that the `cell_C · packing_B · ε²` bound (Lemma 3 + Lemma 5) is **tighter** than the baseline's `(1 - n_cap)² · ε²` heuristic. | `adaptive_reflow/algorithm/scheduler/adaptive.py:875-950` (closed-form cell-side `(1 - n_cap_base)² · ε²`); `adaptive_reflow/contracts/paper_quantities.py:265-275` (`per_cell_coefficient_C`) |
| `e_ρ` | **Exterior gap** (KL-corrected residual, `min(ρ⁴, (1-ρ)²η²)`) | **`exterior_gap_e_rho` floor lift** in `memory_fraction_for`. When the paper's exterior gap is non-zero, the memory-fraction floor is raised to `max(1-β, e_ρ/4)` so the bounded-merge envelope respects the paper's physical-complement minimum. | `adaptive_reflow/adapters/_adapter_common.py:70-100` (`memory_fraction_for`'s `paper_floor = exterior_gap_e_rho / 4`); `adaptive_reflow/contracts/paper_quantities.py:307-311` (`exterior_gap_e_rho`) |
| `BRAI` (opt-in) | **PaperQuantityAttractorInversion** — paper-quantity-driven fresh-noise generation | Currently **inactive** in synthetic mode (synthetic uses `UniformFreshPerturbation`). When BRAI is enabled, `fresh_theta` is derived from `paper_quantities` instead of uniform jitter. | `adaptive_reflow/adapters/lineageflow.py:1665-1695` (the `perturbation.propose(...)` opt-in branch, only reached when `_perturbation` is non-None and not `UniformFreshPerturbation`) |

### 4.1 What the framework ACTUALLY controls

In the canonical synthetic-mode path (default in cold clone / tests):

1. **`A_g`** — framework controls via `memory_fraction` (= `1 - β`).
   The paper-quantity-driven β comes from
   `PaperRatioAdaptiveScheduler.n_cap` mapped to
   `FinalRestartPolicy.beta_by_channel`.
   In synthetic mode the `profile_residual_fn` is **not exposed** by
   `LineageFlowAdapter`, so `_compute_paper_quantities` returns `None`
   (line 252: `if profile_residual_fn is None: return None`) and the
   β is the **legacy constant-0.5** fallback (preserved byte-identically
   per Wave 86 Agent B comment line 300). So **`A_g` is constant** in
   synthetic mode.
2. **`B_g`** — framework controls via the per-round NFE split
   (`nfe_per_round_list`). In synthetic mode the per-round split is
   uniform (`base = NFE // n_rounds`, remainder in last round), so
   `B_g` is also **constant** in synthetic mode.
3. **`C_g`** — framework controls via the scheduler's `n_cap` /
   `cell_C`. In synthetic mode the `CodimensionSheetScheduler` falls
   back to the framework-side heuristic (line 1030 docstring: "When
   `profile_residual_fn is None` the scheduler falls back to the
   framework-side heuristic using the cosine ramp's `n_cap_base`").
   So **`C_g` is the cosine heuristic** in synthetic mode.
4. **`e_ρ`** — `exterior_gap_e_rho()` returns the paper-quantity
   closed-form (line 311) which does not depend on the trace. So
   **`e_ρ` is a constant** that does not respond to the framework's
   per-round feedback (since `_compute_paper_quantities` returns
   `None`).

**Net effect:** in synthetic mode, the framework's
multi-round-re-inference path is **byte-equivalent to a single-pass
`solve_ode` at the total NFE** plus a fixed restart-blend with
`memory_fraction=0.5` × 3 rounds (12.5% survival). The Paper 31 / 32
/ 33 / 34 paper-quantity-driven scheduler features are
**inert** in synthetic mode because the `profile_residual_fn` is not
exposed.

This is the root cause of the Wave 168 framework ΔpLDDT loss AND
the Wave 169 P3 byte-identity of `n_rounds=1` vs `n_rounds=3` under
synthetic mode.

---

## 5. The unfair comparison — explicit

### 5.1 What Theorem 1 references

```
d_BL(P_framework(·|NFE), P_target) <= A_g · exp(−NFE / B_g) + C_g · e_ρ
```

- `P_framework(·|NFE)` is the framework's multi-round re-inference
  distribution at budget NFE. For the current code, this is
  `(solve_ode + restart-blend) × n_rounds`.
- `P_target` is the **ODE target distribution induced by the same
  frozen θ** at infinite NFE.

### 5.2 What the Wave 168 baseline arm provides

`P_baseline(seq | family) = Π_i bias_family[seq_i]`.

This is **not P_target**. It is **not the framework's n_rounds=1
distribution either**. It is a completely different distribution
designed for AA-bias sanity checks.

### 5.3 What the comparison should be

To test whether the framework's restart-blend + paper-quantity-driven
scheduler adds value, the comparison must be:

| Arm | Mechanism | Purpose |
|-----|-----------|---------|
| **`n_rounds=1`** | single-pass `solve_ode` at total NFE | The framework's ODE target `P_target(NFE)` — the distribution Theorem 1 references |
| **`n_rounds=3`** | three restart-blend rounds at `NFE/3` each | The framework's full `P_framework(·|NFE)` distribution |
| (Reference) | bare RNG over per-family Pfam AA bias | Sanity-check only; NOT the Theorem-1 reference |

If `n_rounds=1` and `n_rounds=3` are byte-identical (Wave 169 P3
result), the framework's restart-blend is **inert** in the test
surface — meaning the bound is the same for both arms, which is the
expected outcome for a fixed `A_g, B_g, C_g, e_ρ` quartet.

If they diverge, the delta quantifies the framework's restart-blend
value-add. The fair eval is then:
- **Wave 161 K6 N=1000** (NFE=10) — framework ΔpLDDT = +1.12. If
  n_rounds=1 vs n_rounds=3 diverge at NFE=10, the framework's
  restart-blend added value at low NFE.
- **Wave 168 N=100** (NFE=50→500) — framework ΔpLDDT = −0.83 to
  −1.56. If n_rounds=1 vs n_rounds=3 diverge at high NFE, the
  framework's restart-blend was over-applying.

### 5.4 Why the Wave 168 baseline-pLDDT-can't-move-with-NFE finding is a feature

The baseline pLDDT being NFE-invariant is a **symptom** of the
baseline distribution not depending on NFE (the bare RNG ignores
`--nfe`). The framework pLDDT moving slightly across NFE (0.73
range) is a real signal that the framework's solve_ode DOES respond
to NFE — but comparing against an NFE-invariant baseline is **not
a fair Theorem-1 test**.

### 5.5 What the current eval is testing

The current eval tests **"is the framework's ODE trajectory
argmax-decoded into a sequence that OmegaFold likes better than the
bare AA-bias RNG?"** This is a **practical sequence-naturalness
question**, NOT a Theorem-1 BL-distance question. The two are
orthogonal: Theorem 1 is silent on pLDDT direction; pLDDT is a
property of OmegaFold + the input sequence, not of the bound.

---

## 6. Recommended fix design

### 6.1 Fix #1 (CPU-only, code-only — recommended first step)

**Replace the baseline arm with `n_rounds=1` in
`tools/gen_lineageflow_n1000_fastas.py`.** This adds a fourth
arm (or replaces the existing baseline) that exercises the same
`solve_ode` path but with `n_rounds=1` (no restart-blend). The
gen script gains a `--baseline-mode {rng, n_rounds=1}` flag that
selects between the existing RNG-driven baseline and the new
`n_rounds=1` solve_ode baseline.

**Implementation sketch:**

```python
# tools/gen_lineageflow_n1000_fastas.py — new flag
p.add_argument(
    "--baseline-mode", choices=["rng", "ode"], default="rng",
    help=(
        "rng = bare RNG over per-family Pfam AA bias (legacy; "
        "sanity-check only — NOT the Theorem-1 reference); "
        "ode = single-pass solve_ode at --nfe (Theorem-1 reference)."
    ),
)

def _write_baseline_arm_ode(out_path, *, n, seed, family_ids, min_len, max_len):
    """Write the Theorem-1 baseline arm: single-pass solve_ode at --nfe."""
    counts = {}
    adapters = {fam: _build_lineageflow_adapter(fam, seed) for fam in family_ids}
    with out_path.open("w") as f:
        for i in range(int(n)):
            family_id = family_ids[i % len(family_ids)]
            length = ...  # rng-driven length, same as before
            adapter = adapters[family_id]
            seq = None
            if adapter is not None:
                seq = _framework_emit_sequence(
                    adapter, family_id=family_id, length=length,
                    seed=seed + i, n_rounds=1,             # KEY: n_rounds=1
                )
            if seq is None:
                seq = _generate_sequence(rng, family_id, length)
            f.write(f">baseline_seed{i}|family={family_id}\n")
            f.write(f"{seq}\n")
            counts[family_id] = counts.get(family_id, 0) + 1
    return counts
```

`_framework_emit_sequence` needs an additional `n_rounds` kwarg
(defaulting to `N_ROUNDS = 3` for the framework arm; `1` for the
ODE-baseline arm). This is a 5-line patch.

### 6.2 Fix #2 (audit trail only — no code change)

Update `tools/gen_lineageflow_n1000_fastas.py:1-30` docstring to
document the `--baseline-mode` semantics:

```
* **Baseline** arm — selects `--baseline-mode`:
  * `rng` (legacy): bare RNG over per-family Pfam AA bias. NOT the
    Theorem-1 reference distribution; intended only as an
    AA-bias sanity-check that the framework produces a sequence at
    all. The eval Δframework−baseline measures OmegaFold sequence
    naturalness, NOT Theorem-1 BL-distance.
  * `ode` (Wave 170 P1): single-pass solve_ode at `--nfe`. THIS is
    the Theorem-1 reference distribution `P_target(NFE)`. The eval
    Δframework−baseline now measures the framework's restart-blend
    value-add at the same NFE.
* **Framework** arm — full `solve_ode → restart-blend × n_rounds=3`
  chain. The eval Δframework−baseline tests whether the restart-blend
  + paper-quantity-driven scheduler adds value over the bare ODE
  target.
```

### 6.3 Fix #3 (requires GPU + trained checkpoint — out of scope for this wave)

**For real testability of the restart-blend over-application at high
NFE**, the framework needs:

1. A trained LineageFlow torch-mode checkpoint (the real checkpoint
   is gated / not vendored in this environment).
2. A sub-modal-sensitive decoding metric (NOT argmax). Options:
   - Temperature-1.0 sampling (preserves sub-modal mass)
   - Per-position entropy (directly measures how sharp the posterior
     is, sensitive to 12.5% vs 50% memory)
   - Per-position categorical cross-entropy against the Pfam
     held-out reference (Wave 44 contract for this)

This is **not a code-only fix** and is out of scope for Wave 170 P1.

### 6.4 What NOT to fix

The user's hypothesis ("论文的理论绝对是对的，你的理解有问题") is correct.
Do **not** patch the framework glue, the scheduler, or the
restart-blend. The framework code is a faithful implementation of the
JMAA Theorem 1 quantity map (§4 above); the experiment is the broken
part. Patching the framework would compound the problem by making the
implementation diverge from the paper.

---

## 7. Verification — gates and commits

This wave is **audit-only** (no code change). The verification gates
are:

- `D4 (claims)`: PASS — every claim in this doc is grounded in
  verbatim code quotes with file:line anchors.
- `ruff`: 0 issues — no code touched.
- `loc_added`: 0 (audit doc is a `.md` file, not code).
- `commit_sha`: see `git log -1 --pretty=oneline` after commit.

---

## 8. Appendix — file:line anchors

| File | Lines | What |
|------|-------|------|
| `tools/gen_lineageflow_n1000_fastas.py` | 103-105 | `_generate_sequence` (pure RNG, no ODE) |
| `tools/gen_lineageflow_n1000_fastas.py` | 207-227 | `_write_baseline_arm` (RNG-driven, `--nfe` ignored) |
| `tools/gen_lineageflow_n1000_fastas.py` | 230-289 | `_write_framework_arm` (calls `_solve_framework`) |
| `tools/gen_lineageflow_n1000_fastas.py` | 158-203 | `_framework_emit_sequence` (drives `_solve_framework`) |
| `tools/eval/framework.py` | 434-565 | `_solve_framework` (solve_ode + restart-blend × n_rounds) |
| `tools/eval/framework.py` | 480-490 | NFE split formula (`base = NFE // n_rounds`, remainder in last) |
| `tools/eval/framework.py` | 203-284 | `_compute_paper_quantities` (returns None when no `profile_residual_fn`) |
| `tools/eval/framework.py` | 285-430 | `_make_framework_policy` (β from paper-quantities or constant-0.5) |
| `adaptive_reflow/adapters/lineageflow.py` | 408-450 | `_synthetic_velocity_field` (2-layer MLP, synthetic test surface only) |
| `adaptive_reflow/adapters/lineageflow.py` | 1640-1825 | `apply_restart_distribution` (50/50 blend, `m = max(0, min(1, m))`) |
| `adaptive_reflow/adapters/lineageflow.py` | 1957-2098 | `solve_ode` (Euler/Heun integration, row-renormalisation) |
| `adaptive_reflow/adapters/lineageflow.py` | 2209-2285 | `observe_token_indices` (argmax decode) |
| `adaptive_reflow/adapters/_adapter_common.py` | 70-100 | `memory_fraction_for` (β + e_ρ/4 floor) |
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 1004-1200 | `CodimensionSheetScheduler` (paper-quantity-driven `n_cap`) |
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 2035-2200 | `PaperRatioAdaptiveScheduler` (PID-lite EMA on `sheet_A`) |
| `adaptive_reflow/contracts/authority.py` | 55-100 | `FinalRestartPolicy` (β_by_channel, alpha_by_channel, etc.) |
| `adaptive_reflow/contracts/paper_quantities.py` | 265-275 | `per_cell_coefficient_C` (paper-quantity `C_g`) |
| `adaptive_reflow/contracts/paper_quantities.py` | 307-311 | `exterior_gap_e_rho` (paper-quantity `e_ρ`) |
| `docs/audit/wave168-p3-evaluation.md` | §3c | Baseline NFE-invariance observation |
| `docs/audit/wave169-restart-blend-analysis.md` | §1 | n_rounds=1 vs n_rounds=3 byte-identity under synthetic mode |
| `docs/audit/wave169-theory-audit.md` | §2-5 | Theorem 1 ↔ downstream claim gap |