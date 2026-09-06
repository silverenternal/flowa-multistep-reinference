# Wave 57 Agent C — FlowMol3 upstream CTMC math + framework restart-blend interaction

**Date:** 2026-09-07
**Wave:** 57, Agent C
**Scope:** READ-ONLY deep-dive into FlowMol3's upstream CTMC math and how the
framework's restart-blend interacts with it.
**Goal:** Identify *why* the 3/3 NFE=10 cells regress uniformly (-15.94% mean
delta_pct per `wave57-pattern-investigation.md`) and propose a smart fix.

Sources read (all in `data/FlowMol3/` and the live adapter):
* `data/FlowMol3/repo/readme.md` (v3 paper framing + arXiv:2508.12629)
* `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` (`campbell_step`,
  `gat_step`, integrator, rate schedule)
* `data/FlowMol3/repo/flowmol/models/flowmol.py` (canonical feat order,
  defaults — `default_n_timesteps=250`)
* `data/FlowMol3/references/REFERENCE_MANIFEST.md` (REOS pkl + paper-parity
  paths)
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (current adapter — read
  `_channel_aware_blend`, `apply_restart_distribution`, `_sample_native_state`,
  `_real_velocity_field`, `_ctmc_real_velocity_field_ex`, `_build_ctmc_rate_matrix`,
  `solve_ode`)

---

## 1. FlowMol3 CTMC math summary (the bits that matter)

### 1.1 Canonical state

FlowMol3's native state is the heterogeneous tuple
`(x, a, c, e) ~ (coords, atom-type, charge, bond-type)` (`flowmol.py:25-27`).
The state is updated on `[0, 1]` via four parallel channels:

* **`x`** (per-atom positions, `(n_atoms, 3)` float) — continuous, ODE via a
  linear-interpolant vector field (`EndpointVectorField`).
* **`a`, `c`, `e`** — categorical (atom-type / formal-charge / bond-type).
  Sampled via CTMC (Continuous-Time Markov Chain) on a discrete state space
  augmented with a mask token.

Per `flowmol.py:25-27`:

```python
canonical_feat_order = ['x', 'a', 'c', 'e']
```

Per `flowmol.py:60-61`, when `explicit_aromaticity=False` (default for
GEOM-Drugs, our pinned ckpt), `n_bond_types = 4` (kekulized: none / single
/ double / triple) + 1 mask token = 5 bond tokens. The atom logit width is
`n_atom_types=11` (10 elements + fake), charge width is 6 (formal charges
-2..+3).

### 1.2 The CTMC rate kernel (Campbell-style)

Per `ctmc_vector_field.py:414-461`, `campbell_step` is the per-step kernel for
the (a, c, e) channels:

```text
x1         ~ Categorical(p_1_given_t)            # model-predicted endpoint
unmask_p   = clamp(dt * (α'(t) + η·α(t)) / (1 - α(t)), 0, 1)
mask_p     = clamp(dt * η, 0, 1)                 # only the stochasticity injects remasking
will_unmask = (high-confidence purity sampling or uniform)
will_mask   = Bernoulli(mask_p) on currently-unmasked tokens
xt[will_unmask] = x1[will_unmask]               # absorb
if not last_step:
    xt[will_mask] = mask_token                  # re-mask (NOT applied on last step)
```

Two key facts:

1. **`α(t)` is per-feature** — each of (a, c, e) gets its own
   `alpha_t[feat_idx]`, `alpha_t_prime[feat_idx]` read from
   `InterpolantScheduler`. So the CTMC rates are not just functions of
   time `t`; they are functions of the per-feature progress schedule.
2. **Re-masking is conditional on `not last_step`** — the very last
   integration step is greedy (no re-mask). All earlier steps trade off
   unmask-progress vs stochasticity-induced re-mask. This is the
   *self-correction* mechanism that makes Campbell-style CTMC robust to
   early-step mistakes: any token that got sampled wrongly at step
   `s_idx` can be re-masked and re-sampled at step `s_idx+1`.

### 1.3 Default upstream config (per `flowmol.py:29-66`)

| knob | default | meaning |
|---|---|---|
| `default_n_timesteps` | **250** | upstream's recommended Euler step count |
| `stochasticity` (`eta`) | 0.0 (training), **8.0** (sampling default) | rate of backward jumps (re-masking) |
| `high_confidence_threshold` | 0.0 (training), **0.9** (sampling) | purity-sampling gate |
| `cat_temperature_schedule` | `'decay'` (decay_max=0.8, decay_a=2) | softens the endpoint prediction at early steps |
| `forward_weight_schedule` | `'beta'` (a=0.25, b=0.25, max=10) | GAT-style reweighting; not used when `dfm_type='campbell'` |
| `distort_p` | 0.7 | P(scramble noise sample) at training time |
| `distort_t` | 0.25 | t-perturbation magnitude |
| `fake_atom_p` | 0.0 (no fake atoms) | if > 0, n_atom_types += 1 |

The recommended sampling config (per `flowmol.py` and the published
readme §"Using FlowMol3") is **`n_timesteps=250` with stochasticity=8.0
and high_confidence_threshold=0.9**. Anything below 50 NFE is far outside
the published envelope.

### 1.4 What happens at low NFE (NFE=10)

The rate equation above is:

```text
unmask_prob = dt * (α'(t) + η·α(t)) / (1 - α(t))
mask_prob   = dt * η
```

At NFE=10 we have `dt = 1/10 = 0.1`. With η=8.0 (default sampling
stochasticity) we get:

* `mask_prob ≈ 0.1 * 8.0 = 0.8` — **80% of unmasked tokens get
  re-masked at every step**.
* `unmask_prob` is bounded by `[0, 1]` but the `(α'(t) + η·α(t)) / (1-α(t))`
  ratio is large at small `t` (α≈0), so `unmask_prob ≈ 0.1 * (large / 1) = 0.1..1`.
  At small `t`, `unmask_prob` clamps to 1.

Net effect: at NFE=10 the chain runs through 10 large jumps, with each
jump having a high chance of partially un-masking (1.0) AND a high
chance of partially re-masking (0.8). This is *high-variance* sampling
by design — the rate kernel is calibrated for NFE=250 where each
`dt=0.004` keeps `mask_prob ≈ 0.032` (manageable) and gives 250 chances
to settle.

### 1.5 Equivariant x channel (not CTMC)

The x channel is continuous, integrated by the same Euler loop
(`ctmc_vector_field.py:328-334`) using `self.vector_field(x_t, x_1, ...)`
from the parent `EndpointVectorField`. **The CTMC is ONLY over
(a, c, e).** The x channel is a vanilla ODE — and ODE error at NFE=10 is
~10x larger than at NFE=100, but that's a generic low-NFE problem, not
specific to FlowMol3.

---

## 2. Framework's restart-blend interaction with FlowMol3 CTMC

### 2.1 What the framework does at the restart boundary

Per `flowmol3_v2_adapter.py:2008-2148`, `apply_restart_distribution` runs
at the *start* of round `r+1` for every sample that needs re-inference
(scheduler picks). It does:

1. Pull `prior_entry` from the `_native_states` LRU cache (the endpoint of
   round `r`'s integration, shape `(x, a, c, e)` with the predicted
   `(x_1_pred, a_1_pred, c_1_pred, e_1_pred)` stored).
2. Sample a *fresh* prior `fresh = _sample_native_state(restart_seed)` with
   `restart_seed = SHA256(policy_hash || next_round)[:8]` — this is a
   **completely new independent draw** from `_sample_x0/_a0/_c0/_e0`
   (lines 447-495). The fresh draw is uniformly random `~ N(0, I)` with
   5% bond-sprinkle.
3. Beta-blend them via `_channel_aware_blend` (lines 1057-1232):

```text
# continuous channels
out["x"] = m_coord * prior["x"] + (1 - m_coord) * fresh["x"]
out["c"] = m_charge * prior["c"] + (1 - m_charge) * fresh["c"]

# discrete channels (categorical resample)
keep = rng.random(shape) < m_pair
out["e"] = np.where(keep, prior_e, fresh_e)
out["a"] = np.where(keep_a, prior_a, fresh_a)
```

   The `m_*` defaults to `0.5` (when the policy omits a per-channel
   `beta_by_channel`).

4. Detach (`detach_proof=True` at every channel boundary) and feed the
   blended bundle as the new round-0 prior.

### 2.2 The problem — the framework's "fresh" sample is NOT the FlowMol3 prior

The FlowMol3 upstream prior is `x_0 ~ N(0, I_3)` and `a_0, e_0` uniform
Categorical + mask-token sprinkle. **Our adapter's `_sample_x0` and
`_sample_e0` (lines 447-495) implement an approximate version:**

```python
def _sample_x0(seed, n_atoms):
    return rng.standard_normal((n_atoms, 3))    # matches upstream N(0,I)

def _sample_e0(seed, n_atoms):
    e = np.full((n, n), N_BOND_TYPES - 1)        # mostly no-bond (matches "no edges")
    for i,j: if rng.random() < 0.05:
        e[i,j] = randint(0, N_BOND_TYPES - 1)   # 5% sprinkle (upstream is more sophisticated)
```

Two discrepancies vs upstream:

1. **No mask tokens**. Upstream's `x_t` is the full prior for x but
   `a_t / c_t / e_t` are *initialized to the mask token* with probability
   `1 - α_t(0)` (which is 1.0 at t=0). See
   `ctmc_vector_field.py:121-127` and `:134`. Our prior has every atom
   pre-typed (uniform Categorical over the real labels) and every bond
   pre-typed (mostly no-bond). The framework therefore starts the chain
   with **zero rate information** for the (a, c, e) channels at t=0:
   every position is "fully unmasked" (none are at the mask token),
   which is the OPPOSITE of what Campbell-style CTMC expects at t=0.
2. **No `distort_p` / `distort_t` perturbation** that upstream applies
   during training/sample preprocessing.

### 2.3 The combined effect at NFE=10

Round 1: framework draws a fresh prior, runs `solve_ode` for NFE=10 Euler
steps on (a, c, e) with the adapter's CTMC kernel. **But every token
starts UNMASKED** (because our prior isn't masked). The CTMC step's
`will_unmask = ... * (xt == mask_index)` filter (line 446) is therefore
satisfied only by tokens that got re-masked in earlier rounds. On a
fresh prior, NO tokens get unmasked, so the rate equation collapses —
the chain is static.

In practice this is masked because the adapter's `_real_velocity_field`
falls back to the **linear-interpolant** endpoint prediction when
`ctmc_enabled=False` (or when `mask_index` is never reached), and the
partial-fidelity head just returns softmax logits. So round 1 with
fresh prior at NFE=10 = "single-shot linear-interpolant Euler at NFE=10"
which is *not* catastrophically bad — it's just vanilla NFE=10 inference.

Round 2 (restart boundary): framework blends round-1's endpoint with a
fresh prior. The blended `x = 0.5·x_endpoint + 0.5·x_fresh` is a
random-purturbation halfway back to the prior. The blended discrete
channels keep ~50% of round-1's (already-noisy) labels and replace 50%
with fresh uniform random.

**This is the corruption**. At NFE=10, round-1's endpoint was already a
high-variance sample (large dt, 80% mask_prob); blending it 50/50 with a
fresh draw throws away 50% of the converged signal and replaces it with
independent uniform randomness. Round 2's CTMC integrator then re-evolves
from this corrupted starting state — but it has only 10 more steps, and
the `(1-α(t))` denominator is small near `t=1`, making the rates very
small (which is the regime where the integrator is supposed to settle
but can't, because dt is too big).

Net: framework leaves round 1 in a worse state than baseline's
single-pass at NFE=10, because the framework replaced half the
already-noisy convergence with fresh noise.

### 2.4 Why NFE>=50 doesn't regress

At NFE=50, `dt = 1/50 = 0.02`. Round 1's endpoint is much closer to the
data manifold (lower per-step error). Round 2's 50/50 blend is now
perturbing a *more accurate* endpoint, so the relative damage is smaller.
At NFE=200, `dt = 1/200 = 0.005` — round 1's endpoint is essentially
the model's best single-pass guess, and the framework's multi-round
smoothing actually helps (it averages over multiple restarts; this is
the JMAA Theorem-1 mechanism).

### 2.5 Summary of the interaction

| mechanism | NFE=10 damage | NFE=50 damage | NFE=200 damage |
|---|---|---|---|
| Framework 50/50 blend with fresh uniform noise | HIGH (round-1 endpoint already high-var) | MEDIUM | LOW |
| Framework's prior lacks mask tokens (CTMC cold-start issue) | HIGH (chain doesn't re-anchor at t=0) | MEDIUM | LOW |
| Adapter's `ctmc_enabled=True` flag (Stage-3 of Workflow R) | Helps a bit but doesn't fix blend math | Helps | Helps |
| Framework's monotonic NFE trend | -15.94% (3/3 regress) | -8.53% (1/3 support) | +1.13% (2/3 support) |

The framework's restart-blend **does not corrupt** the FlowMol3 CTMC
rates in the sense of changing them — it just inserts a *wrong* prior
at the restart boundary. The CTMC then re-evolves from the wrong prior
in 10 more steps, which is not enough to recover. At higher NFE, the
extra steps let the chain forget the bad prior.

---

## 3. Three fix options

### Option 1: NFE-adaptive (skip restart at low NFE)

**Idea**: in the framework's scheduler, when the current NFE is below
some threshold (e.g. 20 or 30), **don't apply restart-blend at all** —
let the single-pass baseline run.

**Mechanism**: add a per-adapter NFE guard in `apply_restart_distribution`
or in the scheduler's restart policy. When `effective_nfe < threshold`,
return `state` unchanged (no blend) and emit an audit code like
`flowmol3adapter_restart_skipped_low_nfe`.

**Pros**:
* Simple (1-line guard + audit code).
* Does NOT change any framework invariant (just short-circuits the
  restart boundary).
* Compatible with any underlying sampler (works for FlowMol3,
  Kanzi, LineageFlow, etc.).

**Cons**:
* Throws away framework's value-add at low NFE (which is exactly where
  the user sees the regression).
* The "right" threshold is empirical (20? 30? 50?).
* Bypasses the JMAA Theorem-1 mechanism entirely — we're saying "framework
  cannot help here, just run baseline".

**Implementation cost**: ~10 LOC in the adapter + ~5 LOC scheduler guard
+ 1 regression test that asserts framework ≡ baseline at NFE<20.

### Option 2: Model-specific alpha tuning (lower blend coefficient)

**Idea**: lower the framework's blend `m_*` defaults for FlowMol3 (from
0.5 to e.g. 0.2 or 0.1), so the framework keeps ~80-90% of the
prior endpoint and only blends a small fresh perturbation.

**Mechanism**: pass per-channel `beta_by_channel` from a new
FlowMol3-aware `RestartPolicy`. E.g.

```python
RestartPolicy(
    policy_hash="flowmol3_low_alpha_v1",
    beta_by_channel={
        ChannelName("coordinate"): 0.9,  # 90% blend, very little fresh noise
        ChannelName("charge"): 0.9,
        ChannelName("raw_pair"): 0.9,
    },
)
```

(`m_* = 1 - beta_*`, so `beta=0.9 → m=0.1`.)

**Pros**:
* Keeps the framework's restart-blend mechanism intact.
* Math-motivated: the more accurate the prior (low NFE → high variance),
  the LESS fresh noise you want to inject. Higher NFE → can blend more.
* Generalizes: any adapter can ship a per-channel beta set.

**Cons**:
* Still corrupts the prior (just by less). Doesn't fix the cold-start
  mask-token issue.
* Risk of under-correcting: at NFE=10 we may need `m=0` to recover, but
  `m=0` is equivalent to no restart at all (returns to Option 1).
* Empirical: needs a sweep to find the right `beta_*` per adapter.

**Implementation cost**: ~30 LOC (new `FlowMol3LowAlphaRestartPolicy`
class, registry entry, scheduler wiring) + ~3 regression tests + 1
ablation sweep to pick the alpha.

### Option 3: Upstream starter (start round-2 from FlowMol3's predicted x1)

**Idea**: instead of blending the prior endpoint with a *fresh* prior
draw, blend the prior endpoint with **a single Euler step from the
prior at the current time** — i.e. a *self-resample* that walks back
one step and forward again. This is "soft restart" rather than
"hard restart".

**Mechanism**: replace `_sample_native_state(restart_seed)` with

```python
def _sample_soft_restart(prior_entry, model, t0=0.5, n_steps=5):
    # Start from prior_entry["x"], evolve backward to t0, forward to t=1
    # with only n_steps (the "half-step" restart).
    return soft_restart_state(prior_entry, model, t0, n_steps)
```

The fresh state is therefore NOT independent uniform noise — it's the
*model's own guess* about what the molecule should look like, run for
a small number of steps from a perturbed prior.

**Pros**:
* Mathematically clean: the fresh state is on the data manifold
  (model-predicted), not in the prior distribution.
* Preserves FlowMol3's CTMC math: the new starting state has the
  right statistical structure for the (a, c, e) chain to anchor on.
* Closest to what JMAA Theorem 1 describes: "re-inference" should
  use the model's own beliefs, not uniform noise.

**Cons**:
* Requires running the model N_steps on each restart — adds compute
  (mitigated: N_steps is small, e.g. 5).
* Requires the adapter to expose its model (or a stateless sampler).
* The adapter's partial-fidelity head isn't a real FlowMol3; the
  "soft restart" prediction is just a readout of the same head —
  this may not give much signal beyond what round 1 already did.

**Implementation cost**: ~80 LOC (new `_sample_soft_restart_state`
helper, integrated into `apply_restart_distribution`, fallback to
`_sample_native_state` when model is unavailable) + ~5 regression
tests + a `ctmc_enabled` toggle for the soft path.

---

## 4. Recommendation

**Recommend Option 1 (NFE-adaptive guard) for the immediate fix** +
**Option 3 (soft restart) as a follow-up for the general
FlowMol3 / Kanzi / LineageFlow case.**

Rationale:

1. **Option 1 is the cheapest correctness fix.** The data shows the
   framework strictly hurts at NFE=10. The most defensible engineering
   call is "don't restart when restart cannot help". This unblocks the
   Wave 57 ablation by turning the 3/3 NFE=10 regression into
   framework-equivalent-to-baseline, which is what an honest reading of
   the math predicts (framework's restart-blend assumes a converged
   prior, which doesn't exist at NFE=10).

2. **Option 1 has the cleanest falsifiable claim.** It's the easiest
   to test (compare baseline vs framework at NFE=10 with the guard
   active; expect framework ≡ baseline up to numerical noise).

3. **Option 3 is the principled long-term fix.** It addresses the
   structural issue: the framework's "fresh prior" is not what
   FlowMol3's CTMC is designed for. The soft restart aligns the
   framework's restart mechanism with FlowMol3's underlying math and
   JMAA's Theorem 1 framing. It costs more (compute + adapter
   surface) but generalizes across all adapters with discrete CTMC
   channels (FlowMol3, Kanzi's discrete AA tokens, LineageFlow's
   discrete family labels).

4. **Option 2 is a tactical workaround, not a principled fix.** Lowering
   the alpha trades regression severity for marginal gains at higher
   NFE; it doesn't address the cold-start mask-token issue and would
   need per-adapter empirical sweeps every time a new model is added.

Suggested implementation sequence (Wave 58+):

1. **Wave 58 — Option 1 implementation**:
   * Add `nfe_threshold: int = 20` to `FlowMol3V2Adapter`.
   * In `apply_restart_distribution`, if the current `effective_nfe < 20`,
     emit `flowmol3adapter_restart_skipped_low_nfe` and return `state`
     unchanged.
   * Add `test_apply_restart_distribution_nfe_guard` regression test.
   * Re-run the 9-cell sweep; expect the 3 NFE=10 cells to flip
     from -15.94% mean to ~0% (framework ≡ baseline).

2. **Wave 59 — Option 3 design**:
   * Author `_sample_soft_restart_state` with a clean Protocol-level
     `soft_restart()` method that adapters can implement.
   * Pilot on FlowMol3 + Kanzi (both have discrete CTMC channels).
   * Document the math in `docs/theory/DEVIATIONS.md` (additive).

3. **Wave 60 — Option 3 evaluation**:
   * Re-run the 9-cell sweep with soft-restart active.
   * Compare to Wave 58's Option-1 baseline.
   * If soft restart recovers the NFE=10 cells AND improves NFE>=50,
     ship as the new default for CTMC-class adapters.

---

## 5. Files read for this audit

* `data/FlowMol3/repo/readme.md` (131 lines, full read)
* `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` (511 lines, full read)
* `data/FlowMol3/repo/flowmol/models/flowmol.py` (lines 1-80 sampled for
  canonical_feat_order + defaults)
* `data/FlowMol3/references/REFERENCE_MANIFEST.md` (110 lines, full read —
  context for paper-parity metrics)
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (lines 1-2148
  sampled; key sections: `_channel_aware_blend` 1057-1232,
  `_sample_native_state` 498-511, `apply_restart_distribution`
  2008-2148, `_real_velocity_field` 914-1049,
  `_ctmc_real_velocity_field_ex` 1306-1446,
  `_build_ctmc_rate_matrix` 1240-1283)

No files were modified.

---

## 6. Files changed

None (READ-ONLY audit per Wave 57 scope).
