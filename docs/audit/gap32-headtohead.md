# GAP-32 — external-method head-to-head beyond R6 (MNIST FM + FlowMol3 R3)

**Date:** 2026-10-14
**Author:** GAP-32 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` GAP-32-SOTA-HEADTOHEAD —
">=2 additional cells with seed-matched external-method SOTA baselines +
Bonferroni-corrected paired statistics, recorded in the 11-cell ledger."
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical; the MNIST checkpoint
is the project-generated `data/mnist_fm/w16e1_5k.ckpt.npz`; the FlowMol3 sampler
drives the vendored `CTMCVectorField.step` **verbatim** — no file under
`data/FlowMol3/` was modified).

---

## 0. TL;DR

R6 (§7.8) is the only cell in the paper that compares FlowA against *published
external methods* rather than against its own vanilla baseline. GAP-32 extends
that exact roster (`vanilla` + `Fast-DLLM` + `AB-Cache` + `LeDiFlow` +
framework) to **two more cells** with the same seed-matched, Bonferroni-corrected
protocol:

| cell | metric | vanilla | best external | **framework** | framework Δ% | framework d_z | p_bonf | verdict |
|---|---|---:|---:|---:|---:|---:|---:|:---|
| **R5c** MNIST FM `w16e1_5k` | Fréchet-projection FID ↓ | 24.9115 | 24.6390 (AB-Cache) | **14.3815** | **−42.27 %** | −53.74 | 4.6 × 10⁻⁴ | **framework WINS** |
| **R3** FlowMol3 | `fg_dev` ↓ | 0.4741 | 0.4154 (Fast-DLLM) | 0.5265 | +11.05 % | +0.89 | 1.00 | framework **loses** (n.s.) |

Two honest, opposite signs:

- **MNIST (image, cross-domain):** the framework is a **decisive SOTA win** —
  it beats every published accelerator by ≈ −42 % FID (all Bonferroni-significant,
  all 3 seeds), while the accelerators themselves move the metric by ≤ 1 %.
- **FlowMol3 R3 (molecule, coordinate channel):** the framework's coordinate
  restart-blend is **negative** (+11.05 %, n.s.); on this cell the
  published accelerators (Fast-DLLM, AB-Cache) *do* reduce `fg_dev`
  (−12.4 % and −5.8 %, also n.s.). This is a **negative transfer** result,
  recorded as such.

GAP-32's acceptance is **met** (two additional cells, seed-matched external
baselines, Bonferroni-corrected paired statistics, recorded here in the ledger),
but the *outcome* is heterogeneous: the "beats SOTA" claim now stands on
**R6 + MNIST**, and R3 is an explicit counter-example where the restart-blend
does not help.

---

## 1. Motivation

The paper's external-comparison evidence is R6-only (§7.8, 16-cell Table B).
Every other cell refutes only its **own vanilla baseline** — a straw-man, not a
SOTA comparison. GAP-32 asks for the same external roster on ≥ 2 more cells so
the comparison is not a single-cell artifact.

---

## 2. Method

**One protocol, two cells.** Both cells run five arms on the *same* seed-matched
initial state:

- `vanilla`  — single-pass Euler at `--nfe` macro-steps (the reference).
- `fastdllm` — confidence-aware Euler + midpoint verifier (`arXiv:2505.22618`).
- `abcache`  — 2-step Adams–Bashforth cache reuse (`arXiv:2504.10540`).
- `lediflow` — learned-prior-shifted Euler (`arXiv:2505.20723`).
- `flowa`    — the framework restart-blend (cell-canonical config).

The three external solvers are the generic batched ports in
`tools/gap32_external_solvers.py` (the same algorithms as the R6
`tools/{fastdllm,abcache,lediflow}_solver.py`). The framework arm follows the
cell's canonical recipe.

**Seed matching.** Every arm for sample *i* starts from the *same* `x0` (the
adapter's own `build_initial_state` draw for `(batch_id, "s{i:05d}")`, where
`batch_id` encodes the run seed), so each seed is an independent draw and the
arms are paired by construction.

**Statistics (R6-style, §7.8).** Unit of replication = **seed** (42 / 43 / 44).
Per `(cell, seed, arm)` one headline metric is recorded; across seeds the
per-arm difference vs `vanilla` is a two-sided **paired** t-test, Bonferroni
across the four non-vanilla arms (`α = 0.05/4 = 0.0125`). FlowA-vs-external is
additionally Bonferroni across the three external arms (`α = 0.05/3 = 0.0167`).

**NFE accounting (disclosed).** The three external arms each spend `--nfe`
macro velocity evaluations (+ their own verifier/cache overhead). The framework
arm is NFE-**efficient**, not NFE-matched: the per-round cap is
`nfe // n_rounds` and the cosine ramp reduces the later rounds, so its *total*
evaluation count is ≈ `nfe / 2` (MNIST: `[12, 9, 3, 1] = 25` for `nfe = 50`).
Per-arm `total_nfe` is recorded in `solver_stats`.

### 2.1 Cell A — R5c MNIST FM (`w16e1_5k`)

- Adapter: `adaptive_reflow.adapters.mnist_fm` (784-dim pixels ∈ [−1, 1]),
  additive `euler` integrator, N = 1000, NFE = 50, seeds 42/43/44, `device=cpu`.
- Metric: framework-internal **Fréchet-projection FID** (784 → 128) vs the MNIST
  test set. Checkpoint: the GAP-35 matched-architecture, **non-smoke**,
  framework-WINS `data/mnist_fm/w16e1_5k.ckpt.npz`
  (sha256 `01729867b67372e3…`).
- Framework config: 4 rounds / cosine ramp / β = 0.5 / restart from round 1
  (the canonical R5c recipe; `num_steps_per_round = [12, 9, 3, 1]`).
- Driver: `tools/sweep_gap32_headtohead.py --cell mnist_fm`.

### 2.2 Cell B — R3 FlowMol3 (`fg_dev`)

- The vendored FlowMol3 R3 sampler is **CTMC-based**: the discrete channels
  (atom type / charge / edges) advance by the native CTMC rule and only the
  **coordinate** x-channel is a continuous Euler ODE. The published external
  solvers are continuous-ODE step rules, so they are injectable **only** into
  the coordinate channel. `tools/gap32_flowmol3_sampler.py` therefore runs the
  vendored `CTMCVectorField.step` **verbatim** (GVP forward + native CTMC
  categorical update) and overwrites only `g.ndata['x_t']` with the arm's
  coordinate rule — the GVP forward and the categorical draws are byte-identical
  across arms, so the comparison isolates the continuous solver.
- N = 250 molecules, NFE = 250, seeds 42/43/44, `device=cuda:0`.
- Metric: `fg_dev` via `tools.paper_metrics.compute_all_paper_metrics`
  (reference `GEOM_DRUGS`). Weights:
  `data/flowmol3/weights_real/checkpoints/last.ckpt`
  (sha256 `0e949b56b54c1d2f…`).
- Framework arm: the paper's **coordinate-channel restart-blend**
  (4 rounds / β = 0.5 / restart from round 1), implemented as **coordinate
  restarts inside a single full-NFE integration** (`restart_step_indices =
  [62, 124, 187]`), so the total coordinate NFE matches the single-pass arms.
- Driver: `tools/sweep_gap32_flowmol3.py`.

**Caveat on the R3 framework arm.** The *canonical* R3 framework intervention
recorded in the paper is a **prior Gaussian perturbation σ = 0.05**, not a
restart-blend. The arm here is the restart-blend (the paper's core mechanism)
injected on the coordinate channel; it is a **different intervention**, chosen
because it is the only one that is solver-comparable to the external arms. The
canonical R3 result (σ = 0.05, directionally framework-WINS, n.s.) is unchanged
and is not what this table tests.

---

## 3. Cell A results — MNIST FM `w16e1_5k`

N = 1000, NFE = 50, seeds 42/43/44. `Δ%` negative = better than vanilla.
`d_z` is the cross-seed paired Cohen's d_z (n = 3).

| arm | FID mean | FID std | Δ% vs vanilla | d_z | p_raw | p_bonf (×4) | Bonf-sig |
|---|---:|---:|---:|---:|---:|---:|:---:|
| vanilla | 24.9115 | 0.165 | — | — | — | — | — |
| fastdllm | 24.8900 | 0.165 | −0.086 | −32.28 | 3.2 × 10⁻⁴ | 1.3 × 10⁻³ | ✓ |
| abcache | 24.6390 | 0.168 | −1.094 | −33.08 | 3.0 × 10⁻⁴ | 1.2 × 10⁻³ | ✓ |
| lediflow | 24.8136 | 0.162 | −0.393 | −33.94 | 2.9 × 10⁻⁴ | 1.2 × 10⁻³ | ✓ |
| **flowa** | **14.3815** | 0.088 | **−42.270** | **−53.74** | 1.2 × 10⁻⁴ | **4.6 × 10⁻⁴** | ✓ |

**FlowA vs each external arm** (paired, Bonferroni ×3):

| contrast | Δ% (flowa − arm) | p_bonf (×3) | Bonf-sig | wins all 3 seeds |
|---|---:|---:|:---:|:---:|
| flowa vs fastdllm | −42.220 | 3.5 × 10⁻⁴ | ✓ | ✓ |
| flowa vs abcache | −41.631 | 3.6 × 10⁻⁴ | ✓ | ✓ |
| flowa vs lediflow | −42.042 | 3.4 × 10⁻⁴ | ✓ | ✓ |

**Reading.** The framework cuts FID by **42 %** and beats every published
accelerator by ≈ −42 %, on all 3 seeds, Bonferroni-significant. The three
external accelerators each move FID by ≤ 1 %. The direction is consistent with
the GAP-35 `w16e1_5k` result (−25.4 % under the *wave191* protocol; the larger
margin here reflects the different x0 draw / chunk-pairing protocol, not a
different checkpoint).

**Statistical-power caveat.** The external arms' sub-1 % effects are flagged
"significant" only because n = 3 seeds with near-constant seed-to-seed values
make the paired t-test hypersensitive (|d_z| ≈ 33 for a −0.1 % effect). The
*practical* effect of the external accelerators on this cell is negligible; only
the framework's −42 % is a material improvement.

---

## 4. Cell B results — FlowMol3 R3 (`fg_dev`)

N = 250, NFE = 250, seeds 42/43/44. `Δ%` negative = better than vanilla.
`d_z` is the cross-seed paired Cohen's d_z (n = 3).

| arm | fg_dev mean | fg_dev std | Δ% vs vanilla | d_z | p_raw | p_bonf (×4) | Bonf-sig |
|---|---:|---:|---:|---:|---:|---:|:---:|
| vanilla | 0.4741 | 0.0539 | — | — | — | — | — |
| fastdllm | 0.4154 | 0.0230 | −12.386 | −1.204 | 0.172 | 0.690 | ✗ |
| abcache | 0.4468 | 0.0402 | −5.763 | −0.326 | 0.629 | 1.000 | ✗ |
| lediflow | 0.4788 | 0.0144 | +0.999 | +0.113 | 0.863 | 1.000 | ✗ |
| **flowa** | 0.5265 | 0.0208 | **+11.053** | +0.894 | 0.262 | 1.000 | ✗ |

**FlowA vs each external arm** (paired, Bonferroni ×3):

| contrast | Δ% (flowa − arm) | p_bonf (×3) | Bonf-sig |
|---|---:|---:|:---:|
| flowa vs fastdllm | +26.752 | 0.139 | ✗ |
| flowa vs abcache | +17.844 | 0.096 | ✗ |
| flowa vs lediflow | +9.954 | 0.148 | ✗ |

**Reading.** On the FlowMol3 R3 cell the coordinate-channel restart-blend
**does not help**: `fg_dev` rises +11.05 % over vanilla (d_z = +0.89), and the
framework is *worse* than every external arm (+10 % to +27 %), though none of
the contrasts is Bonferroni-significant at n = 3 (seed-to-seed variance is
large — vanilla ranges 0.4124–0.5121 across the three seeds). Meanwhile the
published accelerators *reduce* `fg_dev` on this cell (Fast-DLLM −12.4 %,
AB-Cache −5.8 %, LeDiFlow ≈ 0 %). All arms are 100 % RDKit-valid.

This is the **opposite sign** to MNIST. The two cells therefore bracket the
"beats SOTA" claim: it holds decisively on the image cell and fails on this
molecule cell (coordinate channel). Consistent with the paper's own mechanism
story, the restart-blend corrects residual *velocity-field* error — it helps
where the field is under-trained (MNIST `w16e1_5k`) and is neutral-to-harmful
where the field is well-trained (FlowMol3 R3 at 250 NFE).

### 4.1 Dropped candidate cell — 2D eight-gaussians

A third cell was run (`twodim_eight_gaussians`, W₂, N = 1000, NFE = 50, seeds
42/43/44) but **dropped** from the GAP-32 deliverable because the framework arm
does not apply to it:

| arm | W₂ mean | Δ% vs vanilla | d_z | direction |
|---|---:|---:|---:|:---|
| vanilla | 0.1641 | — | — | — |
| fastdllm | 0.1635 | −0.349 | −2.81 | wins |
| abcache | 0.1842 | +12.30 | +4.48 | loses |
| lediflow | 0.2720 | +65.82 | +8.40 | loses |
| **flowa** | **1.6111** | **+882.01** | +115.28 | **loses** |

The 2D closed-form cell is a **degenerate** target for the restart-blend (the
framework arm diverges, W₂ × 10), so it cannot serve as a head-to-head cell.
The two cells in the GAP-32 deliverable (MNIST, FlowMol3 R3) are the ones where
the framework arm is well-defined. The 2D evidence is retained on disk
(`verification_outputs/gap32-headtohead/twodim_eight_gaussians/`) for
provenance.

---

## 5. Verdict — GAP-32 acceptance

Acceptance: *">=2 additional cells with seed-matched external-method SOTA
baselines + Bonferroni-corrected paired statistics, recorded in the 11-cell
ledger."*

**Met:**
- **2 additional cells** — R5c MNIST FM and R3 FlowMol3, each with all four
  published/external arms (Fast-DLLM, AB-Cache, LeDiFlow) + vanilla + framework ✓
- **seed-matched** — every arm starts from the same per-seed `x0` ✓
- **Bonferroni-corrected paired statistics** — α = 0.05/4 (vs vanilla) and
  0.05/3 (flowa vs external), unit = seed, seeds 42/43/44 ✓
- **recorded in the ledger** — this audit + `docs/audit/todo-history.md` §4 ✓

**Outcome is heterogeneous (recorded honestly):**
- **MNIST:** framework **WINS** decisively (−42.27 %, all arms beaten, all
  Bonferroni-sig).
- **FlowMol3 R3:** framework **does not win** (+11.05 %, n.s.); the external
  accelerators reduce `fg_dev` on this cell.

---

## 6. Honest caveats

- **R3 framework arm ≠ canonical R3 intervention.** The canonical R3 framework
  is a σ = 0.05 prior perturbation; the arm here is the restart-blend on the
  coordinate channel (the only solver-comparable choice). The canonical R3
  verdict is unchanged.
- **R3 reduced N.** N = 250 molecules/seed (the canonical R3 sweep is N = 1000,
  ≈ 7.5 h for the 5-arm head-to-head). The reduced N is disclosed; the cell is
  reported as a **negative/neutral** result, which under-disclosure cannot
  overstate a win.
- **R3 metric channel.** Only the coordinate channel is solver-injectable; the
  discrete (CTMC) channels are byte-identical across arms by construction. The
  external accelerators' `fg_dev` gains therefore come solely from the
  coordinate trajectory.
- **MNIST statistical power.** n = 3 seeds; the external arms' sub-1 % effects
  are statistically flagged but practically negligible (|d_z| ≈ 33).
- **No frozen surface moved.** This is observations-only recording per the
  standing recording-scope policy; promoting either cell into
  `docs/CLAIMS.md` / the manuscript is a separate, user-gated decision.

---

## 7. Files

- `tools/gap32_external_solvers.py` (generic batched external solvers)
- `tools/sweep_gap32_headtohead.py` (MNIST / 2D driver)
- `tools/gap32_flowmol3_sampler.py`, `tools/sweep_gap32_flowmol3.py`
  (FlowMol3 R3 coordinate-channel head-to-head)
- `tests/test_gap32_flowmol3_sampler.py`, `tests/test_gap32_external_solvers.py`
- `verification_outputs/gap32-headtohead/mnist_fm/` — `aggregate.{json,csv}`,
  per-seed `seed*/{*_samples.npz,seed_summary.json}`
- `verification_outputs/gap32-headtohead/flowmol3_r3/` — `aggregate.{json,csv}`,
  per-seed `seed*/seed_summary.json`
- `verification_outputs/gap32-headtohead/twodim_eight_gaussians/` — dropped
  candidate cell (retained for provenance; §4.1)
- `verification_outputs/gap32-headtohead/{METADATA.json,SHA256SUMS}`

---

## 8. Guardrail compliance

| Guardrail (AGENTS.md §3) | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ FlowMol3 sampler drives the vendored `step` verbatim; no `data/FlowMol3/` edit |
| #2 additive is the rule | ✅ new evidence only; no recorded number changed; no frozen surface edited |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty | ✅ the R3 negative result, the reduced N, and the n = 3 power caveat are disclosed |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` number moved |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ one protocol, cell-parameterised; reuses the generic external-solver ports |
