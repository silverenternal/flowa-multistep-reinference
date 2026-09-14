# Wave 49 Agent C — Framework Theorem 1 narrative vs FlowMol3 actual math

**Date:** 2026-09-07
**Wave:** Wave 49 Agent C
**Owner:** framework maintainer
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Sources consulted (READ-ONLY):**
- `data/FlowMol3/repo/readme.md`
- `data/FlowMol3/repo/configs/flowmol3.yml`
- `data/FlowMol3/repo/flowmol/models/flowmol.py`
- `data/FlowMol3/repo/flowmol/models/vector_field.py`
- `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py`
- `data/FlowMol3/repo/flowmol/models/interpolant_scheduler.py`
- `data/FlowMol3/repo/flowmol/analysis/metrics.py`
- `data/FlowMol3/repo/fm3_evals/readme.md`
- `docs/theory/operating-regime.md` (framework Theorem 1 narrative)
- `docs/theory/theorem1_rate_bound.md`
- `adaptive_reflow/adapters/flowmol3.py` (DTB-G2 placeholder adapter)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (real adapter wrapping FlowMol3)
- `adaptive_reflow/universal/adapter.py::FlowMatchingODEAdapter` (Protocol)
- `adaptive_reflow/framework/interfaces.py`

**Goal:** compare the framework's math story (paper Theorem 1
BL-convergence + paper-quantity signals `sheet_A`, `packing_B`,
`cell_C`, `e_rho`) against FlowMol3's actual math (CTMC flow matching
on a heterogeneous `(x, a, c, e)` graph state) and identify concrete
mismatches + glue-layer additions needed.

---

## 1. Framework's math story (recap)

The framework's narrative is built on **one specific paper**:
the JMAA paper (Theorem 1, line 87-92 + Corollary 1 line 165 +
Lemmas 2-5). The narrative (per `docs/theory/operating-regime.md`
+ `docs/theory/theorem1_rate_bound.md`) is:

### 1.1 Setting

- A 1-D-sheet target `g : R → R` with the curve
  `{(x, g(x)) : x ∈ R}` in `R²`.
- Noise-perturbed residual posterior
  `μ_{g,ε} = {(x, g(x) + ε·z) : x ~ N(0,1), z ~ N(0,1)}`.
- Its `ε → 0` limit `ν_g` is concentrated on the sheet.

### 1.2 Theorem 1 (BL-convergence)

```
BL(μ_{g,ε}, ν_g) ≤ √(2/π) · ε            (g-independent constant)
```

This is the **rate-bound guarantee**: as the residual noise shrinks,
the BL distance to the sheet shrinks at rate `O(ε)`. Framework
exposes this as `adaptive_reflow.theory.rate_bound.check_explicit_rate_bound`
+ `ExplicitRateBoundReport`.

### 1.3 Paper-quantity signals

The framework grounds four paper-derived quantities that drive the
multi-round engine:

| Signal | Paper reference | Meaning |
|---|---|---|
| `sheet_A` (sheet evidence) | Lemma 2 (line 131-132) | Posterior mass on the 1-D sheet |
| `packing_B` (root-cell packing) | Lemma 5 (line 132) | Disjoint-cell constraint `ρ < d/4` |
| `cell_C` (per-cell coefficient) | Lemma 3 (line 132) | Cell-side contribution |
| `e_rho` (exterior gap) | Lemma 4 (line 132, 135-138) | `\|F_g\|^2 ≥ e_rho` away from the sheet |

These map onto scheduler control via the ratio

```
sheet = sheet_A * eps
cell  = cell_C * packing_B * eps²
ratio = sheet / (sheet + cell)         → drives n_cap (Wave 31)
```

(`docs/theory/operating-regime.md` §5 + §10).

### 1.4 Operating regime claim

> Framework's multi-round re-inference provides corrective value
> **iff** `sheet_A · ε ≫ cell_C · packing_B · ε²` (Corollary 1,
> line 165) holds with a comfortable margin.

Empirically (Wave 17 Phase 2, `docs/CONDITIONS.md`), this regime
is **falsified on `twodim_fm`** (2-D Gaussian → analytic target,
no 1-D-sheet structure). The framework has not been measured
on FlowMol3's heterogeneous `(x, a, c, e)` state.

---

## 2. FlowMol3's actual math story

FlowMol3's paper (arXiv:2508.12629) and its open-source
implementation tell a very different story. Below is the math
grounded in `data/FlowMol3/repo/`.

### 2.1 State space (heterogeneous, graph-shaped)

FlowMol3's native state is the tuple `(x, a, c, e)` over a
per-molecule graph with `n_atoms` nodes and `~n_atoms²` edges:

- `x ∈ R^{N×3}` — per-atom 3-D coordinates (continuous; the
  framework's "coordinate" channel)
- `a ∈ {0, 1}^{N×K_atom}` — per-atom atom-type logits, one-hot
  with a mask token appended under CTMC (discrete; the **adapter
  drops this** — see `flowmol3.py:88-96` "atom type is a model-local
  label, not an adaptive-reflow evidence surface")
- `c ∈ {0, 1}^{N×K_charge}` — per-atom formal charge logits
  (discrete; the framework's "charge" channel)
- `e ∈ {0, 1}^{E×K_bond}` — per-edge bond-order logits
  (discrete; the framework's "raw_pair" channel)

The graph topology is **variable** per molecule (DGL graphs;
`flowmol.py:417-440`). The framework's `flowmol3_v2_adapter`
declares `FLOWMOL3_CHANNELS = ("coordinate", "charge", "raw_pair")`
(Wave 41 D.1 shrink; `flowmol3.py:97`).

### 2.2 Loss (CTMC, not velocity-MSE)

`flowmol.py:202-224` and `ctmc_vector_field.py:14-15`:

```
parameterization ∈ {endpoint, vector-field, dirichlet, ctmc}
total_loss = Σ_f total_loss_weights[f] * loss_f
```

For the canonical FlowMol3 model (`configs/flowmol3.yml`:
`parameterization: ctmc`), each **categorical** feature (`a`,
`c`, `e`) is trained with `nn.CrossEntropyLoss` against a
**target index** — *not* a velocity-MSE target. The continuous
feature (`x`) is trained against the endpoint (positions at
`t=1`).

The CTMC interpolation is **`α_t · x_1 + (1 - α_t) · x_0`** for
positions (the standard linear blend, `interpolant_scheduler.py:148`)
and a **mask-and-unmask** process for categoricals (CTMC flow
matching per `ctmc_vector_field.py:122-141`): each node's atom
type starts as the MASK token, then is unmasked one round at a
time with probability proportional to `α'_t + η·α_t` (Campbell
discrete flow, `ctmc_vector_field.py:430-431`).

### 2.3 Interpolant schedules (not 1-D-sheet)

`interpolant_scheduler.py:131-153`:

- Linear: `α_t = t`, `α'_t = 1` (per-feature constant).
- Cosine: `α_t = 1 − cos²(π/2 · t^ν)` (FlowMol3 default,
  `configs/flowmol3.yml:108-118` — all four features linear, but
  cosine is supported).

**There is no 1-D-sheet `g(x)` in FlowMol3.** The targets are
**empirical distributions of molecules** (GEOM-Drugs
3-D conformers), not analytic curves in `R²`. The "sheet"
structure the JMAA paper analyses does not exist.

### 2.4 Integration scheme (CTMC forward Euler + Heun-ish)

`ctmc_vector_field.py:145-285` `integrate`:

1. Build time grid `t = linspace(0, 1, n_timesteps)` (default
   `n_timesteps=250`, `configs/flowmol3.yml:46`,
   `flowmol.py:46-47`).
2. For each step `s_i` from `t_{i}` to `t_{i+1}`:
   - Predict the per-node endpoint `dst_dict = vector_field(g, t_i)`
     (GVP-GNN denoising graph, `vector_field.py:212-293`).
   - **Positions (x)**: explicit Euler
     `x_{t+dt} = x_t + dt · v_θ(x_t, t_i)` (line 334).
   - **Categoricals (a, c, e)**: Campbell step — unmask with
     `unmask_prob = dt·(α'_t + η·α_t)/(1 − α_t)` (line 430),
     mask with `mask_prob = dt·η` (line 431), high-confidence
     unmasking (`purity_sampling`) gates which nodes get
     unmasked based on the model's confidence (`hc_thresh=0.9`
     in the canonical config).
3. No multi-round re-inference loop, no restart-blend, no
   scheduler-side sheet sampling.

This is a **single-pass, fixed-grid, position-Explicit-Euler +
categorical-Campbell** integrator. The framework's
`paper_quantities` and `CodimensionSheetScheduler` machinery is
**orthogonal** to this — it acts on the `(x, a, c, e)` state
*between* calls to `model.integrate`, not inside it.

### 2.5 Evaluation metrics (chemistry, not BL distance)

`flowmol/analysis/metrics.py` + `fm3_evals/readme.md`:

The FlowMol3 paper does **not** report BL distance, sheet-vs-cell
ratio, or paper-quantity `e_rho`. The reported metrics are:

- **Validity**: `frac_valid_mols`, `frac_connected`, `avg_frag_frac`,
  `avg_num_components` (rdkit-based, `metrics.py:172-240`).
- **Stability**: `frac_atoms_stable`, `frac_mols_stable_valence`
  (`metrics.py:111-117`, valency table lookup).
- **Energy**: MMFF94 energies, Jensen-Shannon divergence against
  training set (`metrics.py:259-270`).
- **Functional groups + ring systems**: REOS flags (`Glaxo`,
  `Dundee`), cumulative REOS deviation
  (`metrics.py:415-430`).
- **PoseBusters**: full pb benchmark for structural validity
  (`metrics.py:154-164`).
- **Geometry (xTB)**: GFN2-xTB optimization, RMSD vs initial
  geometry (`fm3_evals/geometry/xtb_optimization.py`,
  `fm3_evals/geometry/rmsd_energy.py`).

`n_timesteps=250` is the canonical inference budget
(`configs/flowmol3.yml:46`). The framework's
`Wave 14 baseline audit N=5000` measures
`fr_atoms_within_0.5 = 0.8012` (FlowMol3 paper's headline
metric) — see `docs/theory/operating-regime.md` §3.2.

---

## 3. Mismatches (concrete list)

The framework's paper-quantity narrative is grounded in the
**JMAA paper**, which analyses a **1-D-sheet-on-R²** residual
posterior. FlowMol3 is **3-D molecular generation with
heterogeneous `(x, a, c, e)` graph state + categorical CTMC
flow**. The mismatches are structural, not parametric.

### M1 — Velocity field is NOT on R²

- **Framework:** `v_θ(x, t) : R² → R²`, sheet `{(x, g(x))}`,
  Theorem 1 in `R²`.
- **FlowMol3:** `v_θ` is a **GVP-GNN denoising graph** that takes
  a DGL graph `g` (variable nodes/edges) and emits a *predicted
  endpoint* `dst_dict = {x, a, c, e}` at each step
  (`vector_field.py:212-293`). The continuous `x` channel uses
  Explicit Euler with the same `α'_t` interpolant; the categorical
  channels use Campbell CTMC, not ODE.
- **Consequence:** Theorem 1's BL bound `BL ≤ √(2/π) · ε` does
  not apply — there is no 1-D sheet to converge to. Even the
  planar witness (`planar_bl_convergence_witness`) is meaningless
  for a graph state.

### M2 — Categoricals are CTMC, not ODE

- **Framework:** everything is a velocity field `v_θ` integrated
  via an ODE solver (Heun / RK4 / DOPRI5); `paper_quantities` are
  continuous scalars.
- **FlowMol3:** three of four features (`a`, `c`, `e`) are
  **discrete** and updated by **Campbell CTMC mask/unmask**
  (`ctmc_vector_field.py:414-461`), not by an ODE. The framework
  has no first-class categorical-CTMC integration path; the
  Continuous + Discrete channels in `AdapterCapabilities` are
  treated as one-shot endpoints, not as multi-step stochastic
  processes.
- **Consequence:** the framework's `n_cap` (which controls ODE
  integration steps per round) does not control the CTMC
  unmasking budget. The framework's `noise_bias` injection is
  a Gaussian-on-`x` perturbation; it does **not** affect the
  CTMC mask/unmask probabilities.

### M3 — Per-feature interpolant schedules, not single α_t

- **Framework:** one global `ε → 0` schedule (Theorem 1 limit).
- **FlowMol3:** each of the four features has its own
  `α_t` (`flowmol.py:344-376`, `interpolant_scheduler.py:97-112`).
  The framework's `eps_per_round(r) = eps_0 · (1 - u_r)` is a
  **single scalar**; FlowMol3's `α'_t_f` for `f ∈ {x, a, c, e}`
  is a **4-vector** with per-feature cosine exponent `ν_f`.
- **Consequence:** `paper_selection_ratio(r) =
  sheet_A·ε / (sheet_A·ε + cell_C·packing_B·ε²)` collapses
  FlowMol3's per-feature schedule into a single scalar that
  may not match the bottleneck feature (typically `e`, the
  bond order).

### M4 — Sheet-vs-cell decomposition is degenerate for (x, a, c, e)

- **Framework:** `sheet_A` = posterior mass on 1-D curve;
  `packing_B` = disjoint-cell constraint; `cell_C` =
  per-cell coefficient; `e_rho` = exterior gap.
- **FlowMol3:** the "sheet" is **the set of valid molecules**
  — an empirical, not analytic, set. There is no analytic
  `g(x)` profile that the velocity field matches on the
  support. The atomic-coordinate space is 3-D; the discrete
  spaces are `K_atom × K_charge × K_bond` categorical products.
- **Consequence:** `validate_g_admissible` (`adaptive_reflow.theory.validation`)
  fails closed for FlowMol3 (no `g` profile). The framework's
  paper-quantity layer reports `N/A` and the
  `CodimensionSheetScheduler` falls back to the framework-side
  heuristic closed form (`docs/theory/operating-regime.md` §10.2).
  This is the same degeneration the framework documents for
  `twodim_fm` (§2.2).

### M5 — Empirical evaluation is chemistry-specific, not BL

- **Framework:** `BL(μ_{g,ε}, ν_g)`, sheet-vs-cell evidence
  ratio, `expected_upper_bound`.
- **FlowMol3:** `frac_atoms_within_0.5`, `frac_valid_mols`,
  `frac_connected`, REOS cumulative deviation, MMFF energy
  JS-divergence, PoseBusters pass rate, xTB RMSD/energy. None
  of these are BL-distances to a 1-D sheet.
- **Consequence:** the framework's
  `check_explicit_rate_bound` produces a `False` /
  `NotInFsideClassError` for FlowMol3 (out-of-F-side-class
  profile); the chemistry metrics have to live in a parallel
  metric layer.

### M6 — Restart policy is not geometry-aware

- **Framework:** restart = "blend prior and fresh sample by
  `β = 1 - memory_fraction`" per channel
  (`docs/theory/operating-regime.md` §5, Wave 31).
- **FlowMol3:** there is no notion of "prior geometry" — the
  prior is a CTMC MASK token for categoricals and a centered
  Gaussian for positions (`flowmol.py:417-440`). The framework's
  `apply_restart_distribution` blending in `flowmol3.py:344-388`
  reduces to `blended = m·prior + (1−m)·fresh`, which on the
  CTMC side just means "increase the mask-token probability
  by `1−m`". The chemistry-correct restart would re-invoke
  `vector_field.sample_conditional_path` with the same `α_t`
  schedule, not blend logits.
- **Consequence:** the framework's restart on FlowMol3 is
  *semantically* a "soft re-mask", not a geometry-aware
  re-anchoring. The Wave 38 F-2 fix (`docs/audit/wave45-f2-fix.md`)
  made the `apply_restart_distribution` signatures match, but
  the chemistry-side restart policy is still under-specified.

### M7 — Self-conditioning vs framework re-inference

- **Framework:** multi-round re-inference with merge operator
  (`BoundedMergeOperator`, Wave 33 P2-W33-B) is the value-add.
- **FlowMol3:** `vector_field.py:269-289` *already does* a
  self-conditioning pass — with `scprop=0.5` probability at
  training, and **always** on the first inference step. The
  re-inference loop in the framework risks duplicating
  self-conditioning rather than adding new information, unless
  the merge operator explicitly uses *different noise samples*
  or *different temperature schedules*.
- **Consequence:** the framework-vs-baseline gap on FlowMol3
  is **structurally smaller** than on adapters without
  self-conditioning (twodim_fm, mnist_fm). The empirical
  evidence (`docs/CONDITIONS.md` Wave 14 baseline audit) shows
  framework-vs-baseline gap is mostly NEGATIVE at low NFE.

### M8 — Noise injection is on a different channel

- **Framework:** `inject_forward_noise` injects Gaussian noise
  on the continuous channels (`coordinate`, `charge`) via
  `paper_quantities.e_rho` / `sheet_A`.
- **FlowMol3:** the canonical "forward noise" on `a`, `c`, `e`
  is the **mask token**, not Gaussian noise
  (`ctmc_vector_field.py:126`). On `x`, the forward noise is
  Gaussian (`interpolant_scheduler.py:148-150`), but at the
  *interpolant* level, not at the restart level.
- **Consequence:** the framework's `inject_forward_noise`
  injects Gaussian noise on `x`, then FlowMol3's `integrate`
  already adds Gaussian noise at every interpolant step. The
  two noise sources **stack**, doubling the noise budget and
  biasing `cell_C` upward.

---

## 4. Where they *do* align

Despite the structural mismatches, there are four points of
contact where the framework's math story is genuinely meaningful
for FlowMol3:

1. **Endpoint parameterization is a velocity field at heart.**
   The CTMC parameterization's positions channel uses
   `x_t = (1 - α_t) · x_0 + α_t · x_1` (linear interpolant) and
   the explicit Euler step is `x_{t+dt} = x_t + dt · (α'_t · (x_1
   − x_0))` (`ctmc_vector_field.py:333-334`). The
   `α'_t · (x_1 − x_0)` term IS a velocity — FlowMol3 just
   parameterizes it as "predict the endpoint x_1 and compute
   the implied velocity" rather than directly predicting the
   velocity. So Theorem 1's `v_θ(x, t)` is recoverable from
   FlowMol3's `dst_dict['x']` and `α'_t`.

2. **`BL(μ, ν)` is computable on the coordinate subspace.**
   Restricting to the continuous `x` channel and to a *fixed*
   molecule size, FlowMol3's velocity field defines a family of
   measures `μ_{ε_f}` (one per `α_t` schedule) and the limit
   `ν` is the empirical GEOM-Drugs 3-D distribution. The planar
   BL witness (`planar_bl_convergence_witness`) does not apply
   (3-D, not 2-D), but a 3-D BL witness would apply. The
   framework's `bounded_lipschitz_distance_2d` is **the wrong
   dimension** for FlowMol3; a `bounded_lipschitz_distance_3d`
   would be the right primitive.

3. **`paper_quantities` are computable on `x` if we define a
   1-D profile.** The framework's `sheet_evidence_A` and
   `root_cell_packing_B` are defined for a 1-D sheet `g(x)`,
   but the same machinery applies to a **slice** of FlowMol3's
   `(x, a, c, e)` state when projected onto a fixed atom-type
   configuration. For example, conditioning on `(a, c, e)` and
   asking "given a fixed molecule topology, how concentrated is
   the position distribution on a 1-D curve in `R^{3·N}`?" is
   a meaningful sheet-vs-cell question. The framework does not
   expose this slicing primitive today.

4. **Restart boundary as "re-mask" is honest.** The framework's
   `apply_restart_distribution` mapping (M6 above) is *honest*:
   blending the prior at the CTMC level really is re-masking
   some atoms/edges with probability `1−m`. The semantic
   mismatch (geometry-aware vs re-mask) is a *naming* issue,
   not a *correctness* issue — the framework's restart is a
   valid perturbation on the CTMC process.

---

## 5. Concrete glue-layer additions

The framework needs **FlowMol3-specific glue** in five places
to make `paper_quantities` and Theorem 1 meaningful for FlowMol3.
These are concrete, code-shaped proposals (READ-ONLY audit only,
not implementation).

### 5.1 Add a FlowMol3-specific `paper_quantities` carrier

**Where:** new file
`adaptive_reflow/adapters/_flowmol3_paper_quantities.py`.

**What:** a structured carrier with **two subspaces**:

```
@dataclass(frozen=True)
class FlowMol3PaperQuantities:
    # Continuous subspace (x channel) — maps to framework sheet-A/packing-B
    sheet_A_x: float            # sheet evidence on x
    packing_B_x: float          # root-cell packing on x
    cell_C_x: float             # per-cell coefficient on x
    e_rho_x: float              # exterior gap on x

    # Categorical subspace (a, c, e channels) — FlowMol3-specific
    ctmc_unmask_rate: float     # E[unmask_prob] over (a, c, e)
    ctmc_mask_rate: float       # E[mask_prob] over (a, c, e)
    confidence_threshold: float # hc_thresh (canonical 0.9)
    self_condition_active: bool # scprop pass (canonical True at t=0)

    # Aggregated framework signals (Theorem 1)
    sheet_A_aggregate: float    # min over channels (worst-case)
    packing_B_aggregate: float
    cell_C_aggregate: float
    e_rho_aggregate: float
    aggregate_ratio: float      # drives n_cap
```

**Why:** the framework's `paper_quantities` is currently a
**continuous-only** carrier (sheet-A/packing-B/cell-C/e-rho).
For FlowMol3 we need to surface the categorical-CTMC quantities
*in addition to* the continuous ones, and aggregate them into
framework-comparable scalars. The aggregation rule
("min over channels") matches the framework's
bottleneck-driven scheduler semantics.

### 5.2 Add a FlowMol3-specific restart policy

**Where:** new file
`adaptive_reflow/adapters/_flowmol3_restart_policy.py`.

**What:** a `RestartPolicy` subclass with **two modes**:

```
class FlowMol3RestartPolicy:
    mode: Literal["re_mask_categorical", "resample_position"]
    beta: float                  # from framework policy.beta_by_channel
    confidence_threshold: float  # forwards to CTMC
    ctmc_stochasticity: float    # eta parameter for campbell_step

    def apply_to(self, state: StateBundle) -> StateBundle:
        if mode == "re_mask_categorical":
            # Re-apply the mask token to a fraction `1 - beta` of
            # the categorical features (a, c, e) in state.channels
            for ch in ("raw_pair", "charge"):
                state = re_mask_channel(state, ch, prob=1-beta)
        elif mode == "resample_position":
            # Re-sample the continuous position (coordinate) from
            # the centered-Gaussian prior with std=1.0 (the
            # FlowMol3 default, configs/flowmol3.yml:65)
            state = resample_position_from_prior(state, std=1.0)
        return state
```

**Why:** the framework's generic `apply_restart_distribution`
(M6 above) treats all channels uniformly; for FlowMol3 we want
the chemistry-correct perturbation: re-mask discrete features
(their natural "noise injection") and re-sample positions from
the centered Gaussian (their natural prior). This is what
`flowmol.sample_prior` does on cold start
(`flowmol.py:417-440`).

### 5.3 Add a FlowMol3-specific metric layer

**Where:** new file
`adaptive_reflow/adapters/_flowmol3_metrics.py`.

**What:** compute **chemistry-specific** metrics, not just
NLL/BL:

```
def compute_flowmol3_metrics(
    sampled_molecules: list[SampledMolecule],
    training_set: SampledMoleculeSet,
) -> dict[str, float]:
    return {
        "frac_valid_mols":       ...,
        "frac_atoms_within_0.5": ...,
        "frac_connected":        ...,
        "avg_frag_frac":         ...,
        "frac_mols_stable":      ...,
        "reos_cum_dev":          ...,
        "energy_js_div":         ...,
        # Framework-side:
        "framework_ratio_aggregate": sheet_A_eps / (sheet_A_eps + cell_C_packing_B_eps2),
    }
```

**Why:** the Wave 14 baseline audit measures
`fr_atoms_within_0.5 = 0.8012` against the FlowMol3 paper's
`0.8058`. The framework's `W₂` (2-D Wasserstein) and BL
distance are *meaningless* for FlowMol3; the framework needs
to compute the chemistry-correct metrics from the upstream
`SampledMolecule` objects, not from a 2-D Wasserstein on the
final coordinates.

### 5.4 Add a FlowMol3-specific integration-step counter

**Where:** new file
`adaptive_reflow/adapters/_flowmol3_nfe.py`.

**What:** the framework's "NFE" is **ODE function evaluations**
(Heun = 2 per step, RK4 = 4 per step). FlowMol3's "NFE" is:

```
nfe_flowmol3 = n_timesteps * (
    1                          # vector_field forward (positions)
    + n_categorical_features   # campbell_step per (a, c, e)
    + (1 if self_condition else 0)
)
```

The framework's `paper_quantities.n_cap` (driving
`CodimensionSheetScheduler`) needs to be **rescaled** to
FlowMol3's NFE to compare apples-to-apples with the
canonical `n_timesteps=250` budget.

**Why:** the framework-vs-baseline gap at NFE=50 vs
FlowMol3's NFE=250 is structurally incomparable. A
**FlowMol3-aware NFE accounting** is a prerequisite for the
matched-NFE claim (`docs/operating-regime.md` §3.2).

### 5.5 Add a FlowMol3-specific Theorem 1 interpretation

**Where:** `docs/theory/theorem1_rate_bound.md` addendum
(or a new `docs/theory/theorem1_flowmol3.md`).

**What:** a **subset interpretation** for FlowMol3:

> Theorem (FlowMol3 subset interpretation, Wave 49 Agent C).
> Restrict the FlowMol3 velocity field to the continuous `x`
> channel and to a fixed atom-type configuration `(a*, c*, e*)`.
> Then the conditional velocity field
> `v_θ^{a*, c*, e*}(x, t) : R^{3N} → R^{3N}` defines a family
> of measures `μ_ε^{a*, c*, e*}` on `R^{3N}` with limit
> `ν^{a*, c*, e*}`, the empirical 3-D distribution of GEOM-Drugs
> conformers with that topology. Theorem 1's BL bound
> `BL(μ_ε, ν) ≤ √(2/π) · ε` applies **in this subspace** with
> the same g-independent constant. The categorical-CTMC
> channels are not covered by Theorem 1.

**Why:** this gives the framework a **honest** statement of
where Theorem 1 applies for FlowMol3 (the continuous x
subspace, with categorical conditioning) and where it does
not (the joint `(x, a, c, e)` space). The framework's
`check_explicit_rate_bound` can be extended to accept a
`subspace=` argument that scopes the bound.

---

## 6. Operating regime statement (corrected for FlowMol3)

With the glue additions above, the framework's operating
regime for FlowMol3 can be honestly stated:

> **Theorem (Empirical operating regime — FlowMol3, Wave 49 C).**
> On FlowMol3 (GEOM-Drugs, CTMC parameterization,
> `n_timesteps=250`):
>
> 1. The framework's Theorem 1 BL-convergence claim applies
>    **only on the continuous `x` subspace** (with categorical
>    conditioning), not on the joint `(x, a, c, e)` state.
> 2. The framework's `paper_quantities` machinery is **structurally
>    ill-conditioned** on FlowMol3 (no analytic 1-D profile `g`),
>    same as on `twodim_fm`. The `aggregate_ratio` (min over
>    channels) is the bottleneck signal.
> 3. The framework's restart policy is **honest but chemistry-
>    loose**: re-masking discrete features is the correct CTMC
>    perturbation; resampling positions from the centered
>    Gaussian prior is the correct continuous perturbation. The
>    framework's generic `LinearBlender` is neither.
> 4. The framework-vs-baseline gap at matched NFE is **structurally
>    smaller** than on adapters without self-conditioning, because
>    FlowMol3 already does a self-conditioning pass on the first
>    inference step (`vector_field.py:269-289`).
> 5. Evaluation metrics must be **chemistry-specific**
>    (`frac_atoms_within_0.5`, `frac_valid_mols`, REOS cum-dev,
>    energy JS-div) — not `W₂` or BL.

**Forward path:** implementing §5.1-5.4 would let the framework
make FlowMol3 a Tier-3-style claim (real-ckpt framework-vs-baseline)
on chemistry-correct metrics, with the paper-quantity layer acting
as a bottleneck signal rather than a sheet-vs-cell decomposition.

---

## 7. Cross-references

- `docs/theory/operating-regime.md` — framework's Theorem 1 narrative
- `docs/theory/theorem1_rate_bound.md` — explicit BL rate bound
- `data/FlowMol3/repo/readme.md` — FlowMol3 paper README
- `data/FlowMol3/repo/flowmol/models/flowmol.py` — FlowMol3 model
- `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` — CTMC integration
- `data/FlowMol3/repo/flowmol/models/interpolant_scheduler.py` — `α_t` schedules
- `data/FlowMol3/repo/flowmol/analysis/metrics.py` — chemistry metrics
- `data/FlowMol3/repo/fm3_evals/readme.md` — paper's evaluation recipe
- `adaptive_reflow/adapters/flowmol3.py` — DTB-G2 placeholder adapter
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — real adapter
- `adaptive_reflow/universal/adapter.py::FlowMatchingODEAdapter` — Protocol
- `docs/audit/wave45-f2-fix.md` — Wave 45 F-2 fix (eval pipeline signatures)
- `docs/CONDITIONS.md` — Wave 14 baseline audit (matched-NFE comparison)

---

## 8. Acceptance

**Gate name:** `G-WAVE-49-MATH-COMPARISON`.

**Pass conditions:**
- This doc exists with ≥ 4 sections + mismatch list (M1-M8) +
  concrete glue additions (5.1-5.5).
- Commit + (no push per task scope).

**Out of scope (Wave 49 Agent C is READ-ONLY):**
- Implementation of §5.1-5.4 (Wave 50 candidate).
- Re-running FlowMol3 paper-parity N=5000 with the chemistry-
  correct metric layer (requires GPU).
- Replacing the DTB-G2 placeholder with the real
  `flowmol3_v2_adapter` for the matched-NFE comparison.
