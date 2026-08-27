# Epsilon-direction audit: `CosineAnnealScheduler` vs. paper Theorem 1

**Scope.** Does the framework's per-round progression `r = 0 .. L-1` move in the
same direction as the paper's asymptotic parameter `eps -> 0`?

**Sources.**
* Paper: `NoiseSelectedRectification_EN.md` (repo root).
* Code: `adaptive_reflow/algorithm/scheduler.py`,
  `adaptive_reflow/schedule/cosine.py`,
  `adaptive_reflow/algorithm/policy_driver.py`,
  `adaptive_reflow/algorithm/runner.py`,
  `adaptive_reflow/adapters/twodim_fm.py`.

**Method.** Read the paper in full; traced `n_cap` from its closed form through
the policy driver, the runner, and into the adapter's restart blend; then
compared the two "start -> end" directions. No code was modified.

---

## Section 1 — The paper's epsilon-direction

### 1.1 What `eps` is

`NoiseSelectedRectification_EN.md:77-80` — the posterior is

```
mu_{g,eps}(A) = (1/Z_{g,eps}) * int_A phi_2(z) exp[-|F_g(z)|^2 / (2 eps^2)] dz
Z_{g,eps}     = int_{R^2} phi_2(z) exp[-|F_g(z)|^2 / (2 eps^2)] dz
```

`eps` is the **observation-noise level** on the constraint `F(z) = 0`
(`:20`, "imposed with noise level `eps > 0`"). It is *not* a step index and
not a temperature on the prior — it multiplies only the residual/likelihood
term. Small `eps` = tight constraint = strong selection.

### 1.2 The limit statement (Theorem 1)

`:88-91`:

```
mu_{g,eps}  --BL-->  nu_g          as eps ↓ 0
mu_{g,eps}( U_z I_z ) = O(eps)     as eps ↓ 0
```

with the limit law (`:82-83`) supported on the codimension-1 sheet:

```
q_g(x) = e^{-x^2/2} / sqrt(1 + g(x)^2),   int phi dnu_g = Q_g^{-1} int phi(x,0) q_g(x) dx
```

So **`eps ↓ 0` is the direction of increasing selection**: mass concentrates on
the chosen codimension-1 component and the countable codimension-2 family is
starved.

### 1.3 The three scale facts that define the direction

| Object | Statement | Location | Scaling |
|---|---|---|---|
| Sheet tube | `eps^{-1} int_T phi p_eps -> (2pi)^{-1/2} int phi(s,0) e^{-s^2/2}/sqrt(1+g(s)^2) ds` | Lemma 2, `:101-103` | `int_T p_eps = Theta(eps^{+1})` |
| Root cells | `int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2`; total `O(eps^2)` | Lemma 3, `:107` | `O(eps^{+2})` |
| Evidence | `Z_{g,eps} >= C_1 eps`; `mu(U I_z) <= C_2 eps` | Corollary 1, `:165-168` | denominator `Theta(eps^{+1})` |
| Complement | `<= e^{-e_rho/(2 eps^2)} = o(eps)` | Lemma 4, `:111-112` | exponentially small |

All exponents are **positive powers of `eps`**. The mechanism (`:153`):

> "The sheet has only one normal direction and has evidence of order `eps`.
> This difference of normal dimension is the selection mechanism."

The cell/sheet ratio is `O(eps^2)/Theta(eps) = O(eps) -> 0`.

### 1.4 The geometric meaning of small `eps` (Lemma 2's rescaling)

`:180-184` — the substitution in the sheet tube `T = {|y| <= 1/2}` is

```
x = s,  y = eps * u          (quoted: "On T = {|y| <= 1/2} use x = s, y = eps u.")
```

The tube in the *ambient* `y` coordinate has width `~eps`. **Small `eps` = thin
tube**; the single Jacobian factor `eps` from `dy = eps du` is exactly the
`eps^{+1}` sheet evidence. An isolated cell gets *two* such factors
(`:156`, "The sheet-tube substitution has one Jacobian factor `eps`, whereas an
isolated cell has two"), which is why it decays faster.

**Paper's direction, one line:** `eps` large -> diffuse ambient posterior, no
selection; `eps ↓ 0` -> thin tube, sheet selected, cells `O(eps)` after
normalization.

---

## Section 2 — The framework's round-direction

### 2.1 `n_cap(r)`: the exact closed form

`CosineAnnealScheduler.sample` does not implement the formula itself; it
delegates (`adaptive_reflow/algorithm/scheduler.py:224`):

```python
n_cap = n_cap_for_round(self._config, round_in_cycle)
```

The canonical closed form is `adaptive_reflow/schedule/cosine.py:219-227`:

```python
u_r = r / (L - 1)                                                  # :219
...
n_cap = n_min + (n_max - n_min) * (1.0 + math.cos(math.pi * u_r)) / 2.0   # :227
```

i.e.

```
n_cap(r) = n_min + (n_max - n_min) * (1 + cos(pi * r / (L - 1))) / 2
```

with the deterministic edge case `L == 1 -> n_max` (`cosine.py:194-195`) and
a defensive clip to `[0, 1]` (`cosine.py:233`). `scheduler.py:226` recomputes
`u_r = r / max(L-1, 1)` for the sample record.

Endpoints (defaults `n_min = 0.0`, `n_max = 1.0`,
`default_cosine_scheduler`, `scheduler.py:296-303`):

* `r = 0`   -> `u_r = 0`, `cos(0) = +1`  -> **`n_cap = n_max = 1.0`**
* `r = L-1` -> `u_r = 1`, `cos(pi) = -1` -> **`n_cap = n_min = 0.0`**

Measured, `L = 8`:

| r | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| `n_cap` | 1.0000 | 0.9505 | 0.8117 | 0.6113 | 0.3887 | 0.1883 | 0.0495 | 0.0000 |
| `memory_fraction` | 0.0000 | 0.0495 | 0.1883 | 0.3887 | 0.6113 | 0.8117 | 0.9505 | 1.0000 |

Strictly decreasing in `r`.

### 2.2 Which convention is it: `memory_fraction = 1 - n_cap` or
`fresh_noise_fraction = n_cap`? — **Both; they are the same statement.**

Verified end-to-end, not assumed:

1. `ScheduleSample.memory_fraction()` returns `1 - n_cap` clipped
   (`scheduler.py:68-78`); the canonical helper agrees
   (`cosine.py:294`: `return float(max(0.0, min(1.0, 1.0 - n_cap)))`).
2. The default policy driver sets `beta = n_cap`
   (`policy_driver.py:284-294`: `n_cap_raw = schedule_sample.n_cap` ...
   `_override_beta_by_channel(base_policy, beta_value=clipped, ...)`).
3. The adapter converts back: `adapters/twodim_fm.py:514-515`
   `beta = float(beta_raw)` / `memory_fraction = 1.0 - beta`.
4. The blend, `adapters/twodim_fm.py:523` with
   `_blend_endpoint_with_prior` (`:290-299`):

```python
blended_x0 = _blend_endpoint_with_prior(fresh_x0, prior_x0, memory_fraction)
# def _blend_endpoint_with_prior(endpoint, prior, m): return m * prior + (1 - m) * endpoint
# => blended_x0 = memory_fraction * prior_x0 + (1 - memory_fraction) * fresh_x0
#              = (1 - n_cap)       * prior_x0 + n_cap                 * fresh_x0
```

`fresh_x0` is drawn `N(0, I_2)` at `twodim_fm.py:522`. The generic blender
carries identical math (`algorithm/blender.py:194-209`,
`m*prior + (1-m)*fresh`), as does the toy adapter
(`adapters/toy_gaussian.py:104-106`, `325-333`).

**Verdict on the convention:**
`n_cap` **is** the fresh-noise fraction — the literal coefficient multiplying
the freshly sampled `N(0, I)` draw. `1 - n_cap` is the retained-prior
(memory) fraction. Both docstring claims are correct and mutually consistent.

### 2.3 Where `n_cap` is consumed (runner)

`adaptive_reflow/algorithm/runner.py`:

* `:453-455` — `sample = self._scheduler.sample(outer_cycle_id, r, target_round + r)`.
* `:456-462` — base policy built with placeholder `beta = 0.0`,
  `beta_from_schedule=True`.
* `:463-468` — `applied_policy = self._driver.compute_policy(sample.as_cosine_schedule_sample(), ...)`;
  with the default `ScheduleDerivedPolicyDriver` this stamps
  `beta_by_channel[c] = n_cap` for every channel.
* `:480-488` — `Engine.run_round(...)` receives that policy; the adapter's
  `apply_restart_distribution` performs the blend of §2.2.
* `:509-515` — the round's metric dict records `n_cap`,
  `memory_fraction = 1 - n_cap`, and `beta`.
* `:532-538` — optional `selection_ratio` from `PosteriorSelectionEvaluator`.
* `:545-546` — `record_round_feedback(r, metric)` for adaptive families.

**Fresh-noise injection amount per round** = `n_cap(r)` — the weight on
`fresh_x0 ~ N(0, I_2)` — falling from `1.0` at `r = 0` to `0.0` at
`r = L-1`.

### 2.4 Physical reading of the endpoints

* `r = 0`, `n_cap = 1.0`: the blend is `0*prior + 1*fresh` — the prior endpoint
  is **entirely discarded**, the round restarts from pure `N(0, I)`. Maximum
  exploration, zero memory.
* `r = L-1`, `n_cap = 0.0`: the blend is `1*prior + 0*fresh` — **no fresh noise
  at all**, the prior endpoint is carried forward verbatim. Maximum
  refinement, full memory.

This is a monotone coarse-to-fine anneal, exactly as
`cosine.py:244-257` and ADR-0010 describe.

---

## Section 3 — Comparison table

| | Paper (`eps`) | Framework (round `r`) |
|---|---|---|
| Control parameter | noise level `eps > 0` on the residual (`:77-80`) | fresh-noise fraction `n_cap(r) in [0,1]` (`cosine.py:227`) |
| Where it acts | divides the residual: `exp(-|F|^2 / 2 eps^2)` | multiplies the fresh `N(0,I)` draw: `n_cap*fresh + (1-n_cap)*prior` (`twodim_fm.py:290-299, 523`) |
| **Start** | `eps` large: fat tube, no selection, posterior ~ ambient prior | `r = 0`: `n_cap = n_max = 1.0`, `memory_fraction = 0`, blend = pure fresh noise |
| **End** | `eps ↓ 0`: tube width `~eps` (`y = eps u`, `:180`), sheet selected, cells `O(eps)` (`:88`) | `r = L-1`: `n_cap = n_min = 0.0`, `memory_fraction = 1.0`, blend = pure prior, no injection |
| Monotonicity | `eps` decreases toward 0 | `n_cap(r)` strictly decreases toward `n_min` |
| Selected object grows | sheet posterior mass -> 1 | prior/memory weight -> 1 (state stops being perturbed) |
| Competing object shrinks | root-cell mass `O(eps) -> 0` (Cor. 1, `:166`) | fresh-noise perturbation `-> 0` |
| Normalizer / denominator | `Z_{g,eps} >= C_1 eps -> 0` linearly (`:165`) | no analogue — the framework normalizes nothing per round |
| Governing exponents | sheet `eps^{+1}`, cell `eps^{+2}` (Lemmas 2, 3) | none — `n_cap` is a linear mixing weight, not an evidence scale |

Correspondence: **`eps ~ n_cap(r)`**, i.e. `r` increasing plays the role of
`eps ↓ 0`.

---

## Section 4 — Verdict

### 4.1 `CosineAnnealScheduler`: **ALIGNED** (with a caveat)

The round progression `r: 0 -> L-1` drives `n_cap: n_max -> n_min`, i.e.
monotonically *less* fresh noise, which is the same sense as the paper's
`eps ↓ 0`. Under the identification `eps ~ n_cap`:

* start of cycle <-> large `eps` <-> weak selection: correct;
* end of cycle <-> `eps -> 0` <-> strong selection / concentration: correct;
* the loop's terminal state (`n_cap = 0`, pure memory, no injection) is the
  fixed point corresponding to `eps = 0`: correct.

No flip is required in `CosineAnnealScheduler`, `n_cap_for_round`,
`memory_fraction_from_schedule`, `ScheduleDerivedPolicyDriver`, or the adapter
blend. The naming is also self-consistent: `n_cap` = fresh-noise capacity,
`1 - n_cap` = memory.

**Caveat (why this is alignment of *sense*, not of *magnitude*).** The
correspondence `eps ~ n_cap` is qualitative only. The paper's `eps` sits inside
`exp(-|F|^2 / 2 eps^2)` and produces the `eps^1` / `eps^2` evidence orders that
*are* the selection mechanism; the framework's `n_cap` is a convex mixing weight
on a state vector. Nothing in the framework computes an evidence integral, so
no round carries an `eps^1`-vs-`eps^2` competition. The scheduler is therefore
**directionally aligned but dimensionally orthogonal**: it is a plausible
surrogate for the `eps` axis, not an instantiation of it. Claims of the form
"round `L-1` realizes Theorem 1's limit" are not supported by the code as
written; only "round `L-1` is the low-noise end of a monotone anneal" is.

### 4.2 `CodimensionSheetScheduler._paper_evidence_balance`: **REVERSED**

This is the one place that explicitly claims to instantiate Theorem 1, and its
`eps` exponents are inverted relative to the paper.

`scheduler.py:1591-1592`:

```python
sheet = 1.0 / max(n_clipped, eps)          # eps^{-1}
cell  = (1.0 - n_clipped) ** 2 / (eps * eps)   # eps^{-2}
return float(sheet / (sheet + cell))
```

and the docstring at `scheduler.py:1564-1566`:

> "Paper Lemma 2 says the sheet's contribution to the round's posterior scales
> like `eps^{-1}`; paper Lemma 3 says each root cell contributes at most
> `O(eps^2)`."

Both halves are wrong or mismatched against the source:

1. **Lemma 2 does not say the sheet scales like `eps^{-1}`.** It says
   `eps^{-1} int_T phi p_eps` *converges to a finite positive constant*
   (`:101-103`), hence `int_T p_eps = Theta(eps^{+1})`. The `eps^{-1}` is the
   rescaling applied to expose the limit, not the sheet's evidence.
   Corollary 1's `Z_{g,eps} >= C_1 eps` (`:165`) states the same positive power.
2. **Lemma 3's bound is `<= C_g e^{-z^2/4} eps^2`** (`:107`), a positive power,
   but the code divides by `eps^2`, turning the paper's *faster-decaying*
   competitor into the *faster-growing* one.

Consequence — the ratio moves the wrong way:

```
paper:  cell/sheet = O(eps^2)/Theta(eps) = O(eps)      -> 0   as eps -> 0  (sheet wins)
code:   cell/sheet = [(1-n)^2/eps^2] / [1/eps] = (1-n)^2/eps -> inf as eps -> 0  (cell wins)
```

Measured `_paper_evidence_balance(n_cap_base=0.5, eps)`:

| `eps` | 0.5 | 0.2 | 0.1 | 0.05 | 0.01 | 0.001 |
|---|---|---|---|---|---|---|
| ratio (claims "sheet share") | 0.6667 | 0.2424 | 0.0741 | 0.0196 | 0.0008 | 0.000008 |

The paper requires this column to tend to **1** as `eps ↓ 0`
(Theorem 1, `:88`). It tends to **0**. Since the value is documented as
"`ratio == 1` means sheet evidence dominates" (`scheduler.py:1573-1574`), the
scheduler currently reports maximal *cell* dominance in precisely the regime
where the paper proves the sheet is selected.

A second, downstream symptom: because the ratio is non-monotone in
`n_cap_base`, the resulting schedule is non-monotone in `r`. Measured, `L = 8`,
defaults:

| r | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| `n_cap` | 1.0000 | 0.5176 | 0.0800 | 0.0264 | **0.0169** | 0.0198 | 0.0524 | 0.0476 |

Capacity bottoms out at `r = 4` and then *rises* — fresh-noise injection
increases again in the second half of the cycle, and `r = L-1` is not the
minimum. That contradicts both the cosine base it composes over and the paper's
monotone `eps ↓ 0` picture.

`scheduler.py:1645-1650` also documents `eps_implicit` as "Paper's Theorem 1
says the sheet dominates as `eps -> 0`; this scheduler treats `eps_implicit` as
a hyperparameter that drives the scheduler's sensitivity" — the first clause is
right, the implementation contradicts it.

### 4.3 Summary

| Component | Verdict |
|---|---|
| `n_cap_for_round` / `CosineAnnealScheduler` round-direction | **Aligned** in sense; orthogonal in mechanism |
| `memory_fraction = 1 - n_cap`; `n_cap` = fresh-noise weight | Consistent, verified end-to-end |
| `ScheduleDerivedPolicyDriver` (`beta = n_cap`) | Aligned |
| `LinearScheduler`, `ExponentialScheduler` | Aligned (both non-increasing in `r`) |
| `PolynomialScheduler`, `SigmoidScheduler` | Aligned / direction-configurable (sigmoid flips with negative `steepness`) |
| `_paper_evidence_balance` / `CodimensionSheetScheduler` | **Reversed** — `eps` exponents inverted vs. Lemmas 2, 3, Cor. 1 |

---

## Section 5 — Proposal (minimal changes)

`CosineAnnealScheduler` needs no change. Two changes are proposed, one
substantive and one documentary. **Neither is applied — this audit is
read-only.**

### 5.1 Fix the inverted exponents in `_paper_evidence_balance`

**File:** `adaptive_reflow/algorithm/scheduler.py`
**Lines:** `1591-1592` (the two expressions), plus the docstring `1564-1574`.

Current:

```python
sheet = 1.0 / max(n_clipped, eps)              # scheduler.py:1591
cell  = (1.0 - n_clipped) ** 2 / (eps * eps)   # scheduler.py:1592
```

Minimal fix — restore the paper's positive powers (Lemma 2: sheet
`Theta(eps^1)`; Lemma 3: cell `O(eps^2)`):

```python
sheet = max(n_clipped, eps)                    # eps^{+1}  (Lemma 2 / Cor. 1)
cell  = (1.0 - n_clipped) ** 2 * eps * eps     # eps^{+2}  (Lemma 3)
```

`ratio = sheet / (sheet + cell)` then tends to `1` as `eps -> 0` for every
`n_clipped < 1`, matching Theorem 1 (`:88`) and Corollary 1's
`mu(U I_z) <= C_2 eps` (`:166`). The guard at `1586-1590` remains valid:
`sheet >= eps > 0`, `cell >= 0`, so the denominator stays positive; the
`if denom <= 0.0` branch stays correctly absent.

Also correct the docstring claim at `scheduler.py:1564-1566` to:

> Paper Lemma 2 gives the sheet tube evidence `Theta(eps)`
> (`eps^{-1} int_T p_eps` converges to a positive constant); paper Lemma 3
> bounds each root cell by `O(eps^2)`. The cell/sheet ratio is therefore
> `O(eps)` and vanishes as `eps -> 0`.

The `(1 - n_clipped)^2` factor is a framework-side heuristic with no paper
counterpart (the paper's cell bound is `C_g e^{-z^2/4} eps^2`, keyed to root
position `z`, not to capacity). It can stay as a tunable weight, but the
docstring should say so rather than attributing it to Lemma 3.

**Blast radius.** `_paper_evidence_balance` is exported
(`scheduler.py:2004`) and used only by `CodimensionSheetScheduler.sample`
(`scheduler.py:1810-1812`) and its tests. Any test asserting the current
decreasing-in-`eps` behaviour encodes the inversion and must be updated
alongside. `PosteriorSelectionEvaluator` computes its `selection_ratio` from
Gaussian mode densities and does not call this helper, so it is unaffected.

### 5.2 No rename needed; one docstring precision fix

`n_cap` / `memory_fraction` are already coherent and already point the same way
as `eps ↓ 0`. Renaming (e.g. `n_cap -> fresh_noise_fraction`) would be churn
across `contracts`, ADR-0010, the ledger schema
(`FreshNoiseCumulativeMassRecord`), and every scheduler — not minimal, and not
required for alignment.

The one wording change worth making, for honesty about §4.1's caveat, is at
`adaptive_reflow/schedule/cosine.py:244-257` and
`adaptive_reflow/algorithm/scheduler.py:15-20`: state that the cycle's
`n_cap` ramp is a *monotone surrogate* for the paper's `eps` axis — same
direction, not the same quantity — so that ADR-0013's "posterior selection
drives the algorithm layer" framing is not read as an implementation of
Theorem 1's evidence competition.

### 5.3 Optional: assert the direction in a test

A cheap regression guard that would have caught §4.2:

```
for eps in [0.5, 0.1, 0.01, 0.001]:  ratio(n, eps) must be non-decreasing as eps decreases
ratio(n, eps) -> 1 as eps -> 0 for any n < 1        # Theorem 1
CodimensionSheetScheduler.sample(...).n_cap must be non-increasing in r  # monotone anneal
```

The third assertion currently fails at `r = 4 -> 5` (0.0169 -> 0.0198).
