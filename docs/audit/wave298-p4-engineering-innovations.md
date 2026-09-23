# Wave 298 P4 — Engineering Innovations Audit (tools + utilities)

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY audit of **engineering innovations** — the tools,
utilities, and harness patterns the project ships that other research
groups could adopt. Per the user directive "再深挖一下创新点" (dig
deeper into innovation points), this doc complements Wave 298 P1
(code-level architectural innovations), Wave 298 P2 (methodological
innovations), and Wave 298 P3 (reproducibility innovations) by focusing
on the **fourth leg**: reusable tools that close the gap between "a
paper-grounded theory" and "a runnable, GPU-efficient, adversarially
stress-tested experiment".

**Prior docs (anchors):**
- `docs/audit/wave298-p1-code-innovations.md` (W298 P1 — code-level)
- `docs/audit/wave298-p2-methodology-innovations.md` (W298 P2 — process)
- `docs/audit/wave298-p3-reproducibility-innovations.md` (W298 P3 — guarantees)
- `docs/audit/wave290-p3-batched-harness.md` (W290 P3 — batched harness design)
- `docs/audit/wave287-p-adversarial-sweep.md` (W287 P — adversarial sweep)
- `docs/audit/wave230-p1-b-g-diagnosis.md` (W230 P1 — empirical residual profile)
- `docs/audit/wave291-p5-3seed-results.md` (W291 P5 — paired-tmc 3-seed verification)
- `tools/METRIC_LEDGER.md` (canonical entry points for the framework)

---

## 0. TL;DR — five strongest engineering innovations (ranked)

| Rank | Innovation | file:line | Reusable pattern (other research could adopt) |
|:---:|---|---|---|
| 1 | **Batched framework harness** | `tools/batched_framework_cifar.py:120-243` | A `tools/`-layer harness that bypasses per-record `engine.run_round` overhead while preserving byte-determinism + FID equivalence — **~28-35× wall speedup** with zero source changes to `adaptive_reflow/`. |
| 2 | **Adversarial scheduler stress matrix** | `tools/adversarial_scheduler_test.py:112-921` | A `(scheduler × pathological_input)` matrix test that distinguishes *genuine silent-failure bugs* (FAIL_crash / FAIL_naN / FAIL_negative / FAIL_exceeds_n_max) from *intentional fail-closed defensive rejections* (FAIL_rejected_by_design). |
| 3 | **Empirical `profile_residual_fn` adapter-agnostic residual interface** | `adaptive_reflow/adapters/profile_residual.py:312-431` | A `Callable[[float], float]` interface that converts empirical-residual distributions (LineageFlow pLDDT, Kanzi RMSD, FlowMol3 fg_dev) into the closed-form `g(s)` expected by `sheet_evidence_A` + Lemma 5 — adapter-agnostic, byte-stable, sin-modulated. |
| 4 | **Theorem-aligned FID evaluator** | `adaptive_reflow/eval/fid_theorem_aligned.py:498-759` | An InceptionV3 FID evaluator that emits per-round `TheoremAlignedFIDResult` carrying `(A_g, B_g, C_g, e_rho)` plus a regime-violation flag and an `O(eps)` paper-implied bound check — back-compat with the legacy `FIDProtocol` is byte-stable. |
| 5 | **Bounded-Lipschitz convergence diagnostic** | `adaptive_reflow/eval/lipschitz_diagnostic.py:106-253, 256-321` | A `lipschitz_modulus + tail_modulus ≤ constant / sqrt(N)` test for whether a per-round `selection_ratio` series converged smoothly vs oscillated its way to a high terminal value; complementary to `FID(r)`. |

**Strongest candidates that did NOT make the top-5** (full list in §6):
- **Per-adapter `run_sota_*_experiment.py` sweep driver template** — 9 first-class drivers (2D, CIFAR, HiDream-I1, Lumina-Image-2.0, Wan2.2, FlowMol3 V2, GraphBFN, ProtBFN-AbBFN, comparison) that share one structure (baseline vs framework, scheduler rows, per-round CSV, summary.json).
- **Wave 290 codim lever sweep driver extension** — `--batched-harness` flag toggles between per-record (full audit) and batched (FID-only) paths without changing `adaptive_reflow/`.
- **Wave 287 P-adversarial taxonomy** — `FAIL_rejected_by_design` distinguishes intentional fail-closed from unexpected crashes (a clean answer to "is this a bug or a guard?").
- **Lipschitz-convergence `LipschitzConvergenceReport.as_metrics()` ledger-shape projection** (`adaptive_reflow/eval/lipschitz_diagnostic.py:177-193`) — every diagnostic flattens to a homogeneously-numeric dict so it drops into the hash-chained ledger.

---

## 1. Innovation #1 — Batched Framework Harness (Wave 290 P3)

### 1.1 What it is

A `tools/`-layer harness (`tools/batched_framework_cifar.py`) that
**bypasses** the per-record `engine.run_round` loop and instead calls
`RectifiedFlowCIFARAdapter.batched_inference` directly on a `(B, 3, 32, 32)`
batch tensor for each round of an outer cycle. The harness:

- Generates `n_records` initial noise vectors in one `(B, 3, 32, 32)`
  tensor on the chosen device; each round `r` calls
  `batched_inference` with seed `seed + r` (matching the per-record
  driver's `seed_base * 1000 + ...` contract at the batched aggregate
  level). The full UNet forward runs in one shot, amortising the
  kernel-launch gap that dominated the per-record path.
- Preserves byte-determinism: same `(seed, num_rounds, num_steps,
  weights, solver, schedule_n_caps)` → same trajectory batch byte-for-
  byte. Verified on 16-record synthetic mode in Wave 290 P3 §4.
- Preserves FID equivalence to `adapter.batched_inference` to floating-
  point byte. Verified via the Wave 290 P4 fixpoint-FID methodology.
- Skips the per-record `ledger_row` emit (the codim lever sweep only
  consumes the final batched FID, not the round-by-round ledger trail).

### 1.2 Speedup vs literature

The CIFAR-10 RF case shows the kernel-launch floor. The per-record
loop processes 200 records × 2 rounds in **10.45 s (cosine) / 16.62 s
(codim)** because each `engine.run_round` invokes `adapter.solve_ode`
on a single `(1, 3, 32, 32)` UNet forward. The same algorithm run
through the batched harness processes 200 records × 2 rounds in
**~0.30-0.60 s** — a **~28-35× wall reduction** that closes the 35-55×
framework-vs-batched-baseline gap that the W290 P1 audit confirmed.

| Cell | Wall (per-record) | Wall (batched) | Speedup |
|---|---:|---:|---:|
| cosine (200 rec × 2 rounds, steps=[2,1]) | **10.45 s** | **~0.30 s** | **~35×** |
| codim  (200 rec × 2 rounds, steps=[2,2]) | **16.62 s** | **~0.60 s** | **~28×** |

### 1.3 Why this is novel vs literature

| Literature norm | This project |
|---|---|
| "Re-inference is slow; live with it" | A `tools/`-layer harness that bypasses the per-record loop and amortises kernel-launch gap — **without modifying the framework source** |
| Batching requires rewriting the runner | A `batched_inference` entry point already exposed by the adapter (Wave 281 onward) is enough; the harness is a thin wrapper |
| Speed-vs-fidelity tradeoff | Byte-deterministic + FID-equivalent to the per-record driver (verified) |
| One-off benchmark; no byte-stable chain | `ROUND_SEED_OFFSET = 1` (line 112) + `np.random.default_rng(seed)` byte-equivalence argument documented in the docstring; D.4 30/30 preserved |

### 1.4 Why a NEW tool, not a modification

The harness lives at the `tools/` layer and never touches
`adaptive_reflow/`. The framework source remains pristine: D.4 30/30,
ruff 0, mkdocs 0 warnings all hold without re-verification. The
`adapter.batched_inference` entry point it depends on is the
already-existing vanilla inference path (Wave 281 onward), so the
harness requires NO framework-side additions.

### 1.5 What it does NOT do (honest scope)

The batched harness exists to answer the question "how fast could a
framework-equivalent batched path be?" It does **not** replace
`engine.run_round` — every per-record audit code, ledger row,
`StateBundle` provenance trail, and final-restart distribution that the
full framework emits is skipped here on purpose. Operators who need the
full audit ledger must still run `tools.run_sota_cifar_experiment` or
`tools.wf289_codim_lever_driver`.

### 1.6 Reusable pattern (any other research could adopt)

The pattern is general: **wrap any per-record framework loop with a
`tools/`-layer harness that bypasses the framework overhead for
FID-only end-to-end sweeps, while preserving byte-determinism via a
documented seed contract**. Concretely:

```python
def run_batched_records(adapter, *, n_records, num_steps, seed,
                        solver="euler", num_rounds=2,
                        schedule_n_caps=None) -> NDArray[np.float64]:
    # round 0: batched_inference (draws its own fresh noise)
    # round r>0: _integrate_from_state (inline, mirrors batched_inference
    #            exactly, uses adapter._batched_torch_velocity_field)
```

This pattern transfers directly to any adapter that exposes
`batched_inference` (LineageFlow, FlowMol3 V2, GraphBFN, etc.). Wave
290 P3 limited the prototype to CIFAR-10 because that's where the
per-record kernel-launch floor was highest; the same pattern can be
generalised to NFE ≥ 5 and to protein/molecule/chemistry adapters.

### 1.7 file:line evidence

| Concern | file:line |
|---|---|
| Public API + byte-determinism argument | `tools/batched_framework_cifar.py:120-180` |
| `ROUND_SEED_OFFSET = 1` seed contract | `tools/batched_framework_cifar.py:103-112` |
| Inline `_integrate_from_state` (matches `batched_inference` exactly) | `tools/batched_framework_cifar.py:246-336` |
| CLI + `_compute_fid` reuse from `tools.run_sota_cifar_experiment` | `tools/batched_framework_cifar.py:344-462` |
| Companion driver extension `--batched-harness` flag (in `/tmp/`) | `/tmp/wf289_codim_lever_driver.py` (NOT in repo) |

---

## 2. Innovation #2 — Adversarial Scheduler Stress Matrix (Wave 287 P)

### 2.1 What it is

A `tools/`-layer harness (`tools/adversarial_scheduler_test.py`) that
subjects **5 paper-grounded controllers**
(`codim`, `paper_ratio`, `convergence`, `evidence_driven`, `nfe_aware`)
to **5 pathological paper-quantity vectors** (all_zeros,
extreme_ratios, nan_inf, negative_lipschitz, tiny_all) and verifies the
framework does NOT:

1. crash (uncaught exception in `sample()` or `record_round_feedback()`),
2. produce NaN in `n_cap`,
3. produce a negative `n_cap`,
4. exceed `n_max = 1.0` (the canonical envelope),
5. silently corrupt downstream state (NaN in shift history, EMA, etc.).

The classification is **pessimistic**: the worst observed outcome per
`(scheduler, input)` pair wins, so a single NaN downgrades a whole row
even when subsequent rounds would have been clean. The taxonomy
distinguishes four FAIL verdicts:

- `FAIL_crash` — uncaught exception (genuine framework bug).
- `FAIL_naN` — NaN in `n_cap` (silent failure).
- `FAIL_negative` — `n_cap < -1e-9`.
- `FAIL_exceeds_n_max` — `n_cap > 1 + 1e-9`.
- `FAIL_rejected_by_design` — the framework's explicit defensive guard
  raised a documented `ValueError`. **This is intentional fail-closed
  behaviour, NOT a framework bug** — the framework rejected the
  invalid input loudly rather than producing a silent NaN. Surfaced
  separately so callers can distinguish guards from bugs.

### 2.2 The adversarial inputs

| Name | Paper quantities |
|---|---|
| `all_zeros` | `A_g = B_g = C_g = e_rho = 0` (degenerate) |
| `extreme_ratios` | `A_g = 1e15`, `B_g = 1e-15`, `C_g = 0`, `e_rho = 0` (30 orders of magnitude spread) |
| `nan_inf` | `A_g = NaN`, `B_g = +inf`, `C_g = -inf`, `e_rho = 0` (NaN/inf propagation) |
| `negative_lipschitz` | `A_g = -1.0`, others = 1.0 (physically invalid) |
| `tiny_all` | `A_g = B_g = C_g = e_rho = 1e-100` (paper boundary, legal) |

### 2.3 Why this is novel vs literature

| Literature norm | This project |
|---|---|
| "Stress test = random inputs" | A *taxonomy* of adversarial inputs aligned with the paper quantity (paper Theorem 1 / Lemma 5 hypotheses — `A_g > 0`, finite, non-negative) so each input targets a specific paper hypothesis. |
| "Bug vs intentional guard" — collapsed into a single fail-class | This harness distinguishes `FAIL_crash` (genuine bug) from `FAIL_rejected_by_design` (intentional fail-closed defensive guard). Operators can read the matrix and know which cells are silent-failure bugs vs framed-as-bugs but actually-correct. |
| One-off fuzz test | The harness runs every `(scheduler, input)` cell **twice** with the same seed and asserts byte-equal `n_cap` sequences — the D.4 byte-stability contract is checked at the same time as the adversarial sweep. |
| Scheduler-specific test code per controller | One uniform `_RunResult` dataclass + one verdict matrix renderer; new schedulers drop in by adding one factory + one runner to the `SCHEDULERS` dict. |

### 2.4 Reusable pattern (any other research could adopt)

The pattern is general: **stress-test any paper-grounded controller
against adversarial inputs aligned with the paper hypotheses, classify
verdicts pessimistically, and distinguish silent-failure bugs from
intentional fail-closed guards**. The framework's `_is_known_defensive_rejection`
predicate (lines 421-447) is the key — it pattern-matches documented
`ValueError` messages from the controller's defensive guards.

```python
def _is_known_defensive_rejection(exc: BaseException) -> bool:
    if not isinstance(exc, ValueError):
        return False
    msg = str(exc)
    defensive_signatures = (
        "paper quantities must be finite",
        "paper quantities must be non-negative",
        # ...
    )
    return any(sig in msg for sig in defensive_signatures)
```

This pattern transfers to any other closed-form controller (PID
controllers in classical control, adaptive step-size controllers in
ODE solvers, etc.). The 5-cell × 5-controller matrix scales linearly;
adding a new controller is O(1) lines via the `SCHEDULERS` registry.

### 2.5 file:line evidence

| Concern | file:line |
|---|---|
| 5 adversarial inputs as frozen dataclasses | `tools/adversarial_scheduler_test.py:100-138` |
| 5 schedulers in the `SCHEDULERS` registry | `tools/adversarial_scheduler_test.py:404-410` |
| `FAIL_rejected_by_design` taxonomy + guard detector | `tools/adversarial_scheduler_test.py:142-154, 421-447` |
| Verdict matrix + per-cell n_cap trace renderers | `tools/adversarial_scheduler_test.py:551-595, 727-867` |
| D.4 byte-stability double-run check | `tools/adversarial_scheduler_test.py:528-540` |
| CLI + audit note write + exit code | `tools/adversarial_scheduler_test.py:875-921` |

---

## 3. Innovation #3 — Empirical `profile_residual_fn` Adapter-Agnostic Residual Interface

### 3.1 What it is

A module (`adaptive_reflow/adapters/profile_residual.py`) that exposes a
uniform `Callable[[float], float]` interface for converting an
empirical-residual distribution into the closed-form `g(s)` expected by
`sheet_evidence_A` + Lemma 5 / Proposition 3. The interface is
**adapter-agnostic**: any first-party adapter can register a
`profile_residual_fn` factory and the framework will pick it up.

Three concrete factories ship today:

| Adapter | Empirical residual | Source |
|---|---|---|
| `LineageFlowAdapter` | `(1 - pLDDT / 100)` per-record | Wave 206 P1 N=1000 baseline `metrics.jsonl` |
| `KanziAdapter` | reconstruction RMSD Gaussian (mean 0.902, std 0.137) | Wave 206 P2 R2_kanzi_reconstruction_rmsd_A |
| `FlowMol3V2Adapter` | fg_dev Gaussian (mean 0.638, SEM-derived std 0.183) | Wave 82 statistical_power_at_n1000 |

Each factory:

1. Draws N=100 residuals from the empirical (Gaussian or empirical-
   record) distribution with `seed=42`.
2. Sorts the samples and places them on a uniform grid over `[-K, K]`
   (default `K = 8`, matching `sheet_evidence_A`).
3. Defines the empirical residual profile `r(s)` by linear
   interpolation between consecutive `(s_i, residual_i)` pairs
   (extrapolation holds the endpoint value).
4. **Wave 230 P1 fix**: wraps the empirical residual into a
   cell-structured `g(s) = (r(s) / r̄) * sin(s)` where `r̄` is the
   sample mean. This is required because the empirical residual samples
   are all POSITIVE, so the sorted linear interpolant is monotonically
   increasing — it has NO zeros, and `root_cell_packing_B` correctly
   returns `B_g = 0` (a degenerate case where the bound degenerates to
   `C_g · e_ρ`). The `sin(s)` factor restores the cell structure:
   zeros at `s = kπ` (`k = -2, -1, 0, 1, 2` within `[-K, K] = [-8, 8]`).

### 3.2 Why this is novel vs literature

| Literature norm | This project |
|---|---|
| "Empirical residual" = a fixed vector | An adapter-agnostic `Callable[[float], float]` interface that any adapter can plug into `sheet_evidence_A`; the framework consults the registry (`PROFILE_RESIDUAL_FN_REGISTRY`) per `adapter_class` name. |
| Naive centred design `(r - r̄) * sin(s)` adds an extra zero | The Wave 230 P1 `relative residual design` `r(s)/r̄ * sin(s)` carries the empirical information in the *amplitude* of `g` rather than introducing additional zeros — preserving the canonical `sin(s)` zero spacing of `π ≈ 3.14`, which trivially satisfies `ρ < d/4` for any reasonable `ρ`. |
| Numerical closure over residuals is hidden | The wrapper is **pure composition of byte-stable primitives**: sorted samples → uniform grid → linear interpolation → sin-modulation. Two calls with identical inputs return bit-identical floats. |
| One residual sample per adapter | N=100 residuals from a documented empirical distribution with a fixed seed (42); fallback to analytic Gaussian if the JSONL is unavailable on a fresh checkout. |

### 3.3 The Wave 230 P1 design trade-off (documented choice)

The naive centred design `(residual - mean) * sin(s)` adds an extra
zero at the point where `residual(s) = mean`. For Kanzi/FlowMol3 this
extra zero lands within ~0.27 of `s = 0`, violating the Lemma 5
disjoint-cell constraint `ρ < d/4` for the default `ρ = 0.1` (it
requires `d > 0.4`). The relative residual design avoids this by
carrying the empirical information in the *amplitude* of `g` (via the
`residual/mean` envelope) rather than introducing additional zeros —
preserving the canonical `sin(s)` zero spacing of `π ≈ 3.14`. See
`docs/audit/wave230-p1-b-g-diagnosis.md` for the full root-cause
analysis.

### 3.4 Reusable pattern (any other research could adopt)

The pattern is general: **expose a `Callable[[float], float]`
"residual profile" interface that any domain-specific adapter can
plug in; the framework's paper-quantities machinery stays
adapter-agnostic**. Concretely:

```python
# In the framework's paper-quantities evaluator:
def sheet_evidence_A(g: Callable[[float], float], *, K=8.0, h=0.01):
    # integrate |g(s)| / sqrt(1 + g(s)^2) on the canonical grid
    ...

# In the adapter module:
def lineageflow_profile_residual_fn(*, K=8.0, n_samples=100, seed=42):
    residuals = _sample_lineageflow_residuals(n_samples, seed=seed)
    s_grid, r_grid = _linear_interp_grid(residuals, K=K)
    residual_fn = _build_profile_fn(s_grid, r_grid)
    mean_residual = sum(residuals) / float(len(residuals))
    return _wrap_with_sin_modulation(residual_fn, mean_residual)

PROFILE_RESIDUAL_FN_REGISTRY = {
    "LineageFlowAdapter": lineageflow_profile_residual_fn,
    "KanziAdapter": kanzi_profile_residual_fn,
    "FlowMol3V2Adapter": flowmol3_profile_residual_fn,
}
```

This pattern transfers to any adapter that can produce an empirical
residual distribution (FID residuals, RMSD, reconstruction error,
W2 distance, etc.). The 3-line `_build_profile_fn` +
`_wrap_with_sin_modulation` skeleton is the unit of reuse; the
adapter-specific part is the residual sampler.

### 3.5 file:line evidence

| Concern | file:line |
|---|---|
| `_linear_interp_grid` (sorted samples → uniform grid) | `adaptive_reflow/adapters/profile_residual.py:116-141` |
| `_build_profile_fn` (byte-stable linear interpolant) | `adaptive_reflow/adapters/profile_residual.py:144-186` |
| `_wrap_with_sin_modulation` (Wave 230 P1 cell-structure fix) | `adaptive_reflow/adapters/profile_residual.py:189-236` |
| Per-adapter factories (3 adapters) | `adaptive_reflow/adapters/profile_residual.py:312-392` |
| Registry + `profile_residual_fn_registry` factory | `adaptive_reflow/adapters/profile_residual.py:400-430` |

---

## 4. Innovation #4 — Theorem-Aligned FID Evaluator

### 4.1 What it is

A module (`adaptive_reflow/eval/fid_theorem_aligned.py`) that extends
the legacy `InceptionV3FIDEvaluator` with a theorem-aligned surface
binding the four paper quantities `(A_g, B_g, C_g, e_rho)` from
`adaptive_reflow.contracts.paper_quantities` to the standard
Gaussian-Fréchet arithmetic. Three obligations are added:

1. `compute_per_round` emits one `TheoremAlignedFIDResult` per round,
   carrying the four paper constants plus the regime flag
   `eps^2 < e_rho / log(2)` (Lemma 4 asymptotic regime).
2. `assert_convergence_rate` checks monotonic decrease and the
   quantitative `O(eps)` regression bound
   `FID(r) ≤ C_paper * eps_r` where
   `C_paper = (C_g * B_g + 1 / e_rho) / A_g` — a framework-defined
   aggregate, not a paper-stated constant (the paper's Theorem 1
   constant is `A_g > 0`).
3. `PerRoundFIDTracker.run` orchestrates the round loop and consumes
   the framework's `eps_schedule` (read-only — does NOT mutate
   scheduler state) plus a profile `g` for which a `nu_g` reference
   is built by `NuGReferenceRegistry`.

The numerical contract for the Fréchet arithmetic is **unchanged**: it
is delegated to `InceptionV3FIDEvaluator._compute_frechet_distance_inner`,
so no numerical regression can be introduced through this module.
Back-compat with the legacy `FIDProtocol` is byte-stable.

### 4.2 Why this is novel vs literature

| Literature norm | This project |
|---|---|
| FID is one number per checkpoint | Per-round `TheoremAlignedFIDResult` carrying `(A_g, B_g, C_g, e_rho)` + regime flag + paper-implied constant. The audit trail records the paper quantities in lock-step with the FID, so a reviewer can see why the FID moved (or didn't). |
| FID regression = "did FID go up or down?" | `assert_convergence_rate` checks **monotonicity** + **O(eps)** + Lemma 4 regime — three orthogonal failure modes. |
| Reference FID is a fixed dataset | `NuGReferenceRegistry` builds the reference from a profile `g` via Monte-Carlo rejection sampling on `q_g / Q_g`; cache keyed by SHA-256 of `g` on the canonical paper grid. Different profiles yield genuinely different `nu_g` references. |
| Analytic vs Monte-Carlo trade-off | An analytic Gaussian fallback (`_analytic_nu_g_gaussian`) is exposed for `monte_carlo_n == 0`; preserves byte-stability for unit tests that need a fast `(ref_mu, ref_sigma)` pair. |

### 4.3 Honest disclaimer (in the docstring)

The module's own docstring warns:

> **This module does not compute the paper's Theorem 1 distance.** It
> computes a Gaussian-Fréchet distance on `R^{2048}` InceptionV3
> features. The paper's Theorem 1 is bounded-Lipschitz (Fortet-Mourier)
> convergence `mu_{g,eps} --BL--> nu_g` between probability measures
> on the *ambient plane* `R^2`. Different metric, different space,
> different constants: the two agree only in the qualitative sense
> that both go to zero as `eps -> 0`.

The paper's statement is computed for real, on `R^2`, by
`planar_bl_convergence_witness` (built on
`bounded_lipschitz_distance_2d`, an exact BL distance between planar
empirical measures), and is surfaced through `adaptive_reflow.theory.checkers`
via `theorem1_bl_convergence_witness` and the unified
`Theorem1StatementChecker`. The theorem-aligned FID here is a
**regression gate** (monotonicity + O(eps) bound), not a proof of
Theorem 1.

### 4.4 Reusable pattern (any other research could adopt)

The pattern is general: **layer a paper-quantity-aware "verdict"
interface over an existing Fréchet-distance (or other bounded) metric,
keeping the legacy single-shot FID byte-stable**. The two-tier design:

```python
# Tier 1: legacy FID (unchanged)
FIDResult(value, is_finite, feature_dim, n_samples)

# Tier 2: theorem-aligned FID (new)
TheoremAlignedFIDResult(
    value, is_finite, feature_dim, n_samples,
    epsilon, A_g, B_g, C_g, e_rho,
    regime_check_ok, paper_implied_constant,
)

# Per-round orchestration
FIDPerRoundResult(round_index, epsilon, result, paper_bound_O_eps)
```

This pattern transfers to any bounded metric (Lipschitz distance, JS
divergence, total variation). The key insight is **back-compat by
projection**: `TheoremAlignedFIDResult.as_fid_result()` projects back
to a byte-stable `FIDResult` so legacy consumers don't break.

### 4.5 file:line evidence

| Concern | file:line |
|---|---|
| `PaperQuantitiesSnapshot` (frozen 4-quantity bundle + knobs) | `adaptive_reflow/eval/fid_theorem_aligned.py:116-201` |
| `TheoremAlignedFIDResult` (per-FID 4-quantity fields) | `adaptive_reflow/eval/fid_theorem_aligned.py:204-243` |
| `NuGReferenceRegistry` (cache + analytic/MC fallback) | `adaptive_reflow/eval/fid_theorem_aligned.py:298-365` |
| `_analytic_nu_g_gaussian` (closed-form fallback) | `adaptive_reflow/eval/fid_theorem_aligned.py:383-454` |
| `_fit_nu_g_gaussian` (Monte-Carlo rejection sampling) | `adaptive_reflow/eval/fid_theorem_aligned.py:457-495` |
| `InceptionV3TheoremAlignedFIDEvaluator.compute_per_round` | `adaptive_reflow/eval/fid_theorem_aligned.py:526-572` |
| `assert_convergence_rate` (monotonicity + O(eps)) | `adaptive_reflow/eval/fid_theorem_aligned.py:613-696` |
| `PerRoundFIDTracker.run` (round-loop orchestration) | `adaptive_reflow/eval/fid_theorem_aligned.py:699-759` |
| Honest disclaimer in docstring | `adaptive_reflow/eval/fid_theorem_aligned.py:1-31` |

---

## 5. Innovation #5 — Bounded-Lipschitz Convergence Diagnostic

### 5.1 What it is

A module (`adaptive_reflow/eval/lipschitz_diagnostic.py`) that adds a
**shape** diagnostic for per-round metric series — answering "did this
trajectory converge *smoothly* or oscillate its way to a high terminal
value?". The headline quantity is:

```
tail_modulus = max_k |r_{k+1} - r_k| / du
```

where `du = 1 / (L - 1)` is the schedule's normalised round spacing.
This is the smallest `L` for which the trajectory is `L`-Lipschitz as
a function of normalised progress `u in [0, 1]`. The convergence
criterion is the standard Monte-Carlo rate: with `N` endpoints per
round the ratio is estimated to `O(1 / sqrt(N))`, so a *converged*
trajectory's tail must not move by more than that estimation noise:

```python
tail_modulus * du <= constant / sqrt(N)
```

The module also exposes `bounded_lipschitz_distance`, the exact
dual-bounded-Lipschitz distance between two 1-D empirical measures:

```
d_BL(p, q) = mean_i min(|x_(i) - y_(i)|, B)
```

over matched order statistics — the truncation at `B = 2` being
exactly the `||f||_inf ≤ 1` constraint. It gives a bounded (hence
always finite) convergence measure between a round's endpoint
population and the reference, where an unbounded `W1` could be
dominated by a single outlier.

### 5.2 Why this is novel vs literature

| Literature norm | This project |
|---|---|
| "Convergence" = terminal value of a metric | A *shape* diagnostic: tail Lipschitz modulus vs the MC rate. A run that oscillates its way to a high terminal value is rejected by `within_rate=False` even when the terminal value is high. |
| Unbounded `W1` distance | Bounded-Lipschitz distance `d_BL` (truncated mean of matched order statistics, capped at `B`). Always finite; outliers bounded. |
| One diagnostic per run | Per-round explicit modulus + tail modulus + monotone_tail flag; report is self-describing (carries `n_rounds`, `n_samples`, `tail_fraction`, `constant` echoes). |
| Numbers in a docstring | `as_metrics()` projects to a flat homogeneously-numeric dict (`lipschitz_modulus`, `lipschitz_tail_modulus`, `lipschitz_tail_increment`, ...) so it drops into the hash-chained ledger rows (`BatchedTrajectoryResult.per_round_metric`). |

### 5.3 Reusable pattern (any other research could adopt)

The pattern is general: **add a Lipschitz-modulus diagnostic on top of
any per-round metric series, where the convergence criterion is the
MC rate `constant / sqrt(N)`**. The headline ratio:

```python
ratio = tail_modulus * spacing  # = max raw tail round-to-round move
rate_bound = constant / sqrt(n_samples)  # = MC noise floor
within_rate = (ratio <= rate_bound)  # = converged?
```

This pattern transfers to any per-round metric (`FID`, `W2`,
`selection_ratio`, `coverage`, etc.). The
`LipschitzConvergenceReport.as_metrics()` dict is the unit of reuse —
it drops into any ledger that consumes homogeneously-numeric dicts.

### 5.4 file:line evidence

| Concern | file:line |
|---|---|
| `lipschitz_modulus` (discrete Lipschitz modulus) | `adaptive_reflow/eval/lipschitz_diagnostic.py:106-133` |
| `LipschitzConvergenceReport` (frozen report with echoes) | `adaptive_reflow/eval/lipschitz_diagnostic.py:136-193` |
| `evaluate_lipschitz_convergence` (headline verdict) | `adaptive_reflow/eval/lipschitz_diagnostic.py:196-253` |
| `bounded_lipschitz_distance` (1-D BL distance) | `adaptive_reflow/eval/lipschitz_diagnostic.py:256-321` |
| `planar_bl_convergence_witness` (R^2 BL exact) | `adaptive_reflow/eval/lipschitz_diagnostic.py` (further down — exact planar Theorem 1 distance) |
| Honest disclaimer in module docstring | `adaptive_reflow/eval/lipschitz_diagnostic.py:1-58` |

---

## 6. Other strong engineering innovations (full list, not ranked)

### 6.1 Per-adapter `run_sota_*_experiment.py` sweep driver template

The project ships 9 first-class `tools/run_sota_*_experiment.py`
drivers (2D, CIFAR, HiDream-I1, Lumina-Image-2.0, Wan2.2, FlowMol3 V2,
GraphBFN, ProtBFN-AbBFN, comparison). All share one structure:

- **Baseline** = single-round `__replay` (one round of
  `apply_restart_distribution + solve_ode`); adapter's fresh prior at
  `t=0` is the starting point.
- **Framework** = N schedulers × `--n-rounds` rounds ×
  `--framework-samples` independent chains.
- **Outputs**: `baseline_samples.npz`, `{scheduler}_samples.npz`,
  `comparison.md`, `per_round_metrics.csv`, `summary.json`.

The pattern transfers to any new first-party adapter — copy a driver,
swap the `ADAPTER_FACTORY` + the FID math, ship a comparison table.

### 6.2 Wave 290 codim lever sweep driver extension (`--batched-harness`)

The `/tmp/wf289_codim_lever_driver.py` (NOT in repo, per the user's
"claude相关的不要commit" directive) adds a `--batched-harness` flag
that toggles between per-record (full audit) and batched (FID-only)
paths without changing `adaptive_reflow/`. This is the Wave 290 P3
answer to "why does codim drag GPU utilisation down?" — the
per-record loop pays a 35-55× wall penalty for kernel launch, and the
batched path closes the gap. The driver extension is the **user-facing
switch**; the batched harness is the **implementation**.

### 6.3 Wave 287 P-adversarial taxonomy — `FAIL_rejected_by_design`

The adversarial sweep classifies four FAIL verdicts:

- `FAIL_crash` — unexpected uncaught exception (genuine bug)
- `FAIL_naN` — NaN in `n_cap` (silent failure)
- `FAIL_negative` — `n_cap < -1e-9`
- `FAIL_exceeds_n_max` — `n_cap > 1 + 1e-9`
- `FAIL_rejected_by_design` — documented `ValueError` from an
  intentional fail-closed defensive guard

The last verdict is the key novelty: it answers "is this cell a bug or
a guard?" without conflating the two. Operators reading the verdict
matrix can immediately see that `codim / nan_inf` and `codim /
negative_lipschitz` are *guarded* (intentional fail-closed), not
*bugged* (silent NaN).

### 6.4 Lipschitz-convergence `LipschitzConvergenceReport.as_metrics()` ledger-shape projection

A 12-line method (`adaptive_reflow/eval/lipschitz_diagnostic.py:177-193`)
that flattens the `LipschitzConvergenceReport` dataclass into a
homogeneously-numeric dict:

```python
def as_metrics(self) -> dict[str, float]:
    return {
        "lipschitz_modulus": float(self.modulus),
        "lipschitz_tail_modulus": float(self.tail_modulus),
        "lipschitz_tail_increment": float(self.tail_increment),
        "lipschitz_rate_bound": float(self.rate_bound),
        "lipschitz_within_rate": 1.0 if self.within_rate else 0.0,
        "lipschitz_terminal_value": float(self.terminal_value),
        "lipschitz_monotone_tail": 1.0 if self.monotone_tail else 0.0,
    }
```

Booleans are widened to `0.0 / 1.0` so the dict stays homogeneously
numeric, ready for direct insertion into a hash-chained ledger row.
This is the *ledger-shape projection* pattern — every diagnostic in
the project exposes an `as_metrics()`-style method that drops into
the same ledger schema.

### 6.5 Wave 290 P4 fixpoint-FID methodology

A methodology (documented in `docs/audit/wave290-p4-benchmark-fixed.md`)
that verifies the batched harness is **FID-equivalent** to
`adapter.batched_inference` to floating-point byte. The methodology:

- Pick a representative `--seed` + `--num-steps` (e.g. seed=42, num_steps=2).
- Run `batched_inference` to get `baseline_samples.npz` + `baseline_fid`.
- Run the batched harness to get `harness_samples.npz` + `harness_fid`.
- Assert `|baseline_fid - harness_fid| < 1e-3` AND
  `harness_samples == baseline_samples` (byte-equal).

This pattern transfers to any "batched vs per-record" equivalence
test — pick a reference metric, run both paths, assert
metric-equivalence AND byte-equivalence.

### 6.6 Wave 291 P5 paired-tmc 3-seed verification

A methodology (documented in `docs/audit/wave291-p5-3seed-results.md`)
that re-runs the headline cells on 3 seeds (41, 42, 43) and reports
the cosine baseline's framework_fid σ as the noise band for byte-
stability claims: STRONG ≤ 1σ, PARTIAL ≤ 2σ, WEAK > 2σ. Most papers
do not separate byte-stability from effect size; this methodology
does. The pattern: report `mean ± σ` and a verdict bucket per cell.

---

## 7. Engineering-innovation impact assessment (cross-reference)

| Innovation | Wave | Byte-stable? | Ruff 0? | Vendored NOT touched? | Pattern reusable across adapters? |
|---|---|---|---|---|---|
| Batched framework harness | W290 P3 | YES (D.4 30/30) | YES | YES | YES (any adapter with `batched_inference`) |
| Adversarial scheduler stress matrix | W287 P | YES (double-run D.4 check) | YES | YES | YES (any closed-form controller) |
| Empirical `profile_residual_fn` interface | W229 P3 / W230 P1 | YES (sorted + sin-modulated) | YES | YES | YES (any adapter with empirical residual) |
| Theorem-aligned FID evaluator | W11 / W12 / W14 | YES (legacy path delegated) | YES | YES | YES (any bounded metric, any profile) |
| Bounded-Lipschitz convergence diagnostic | W11 / W12 | YES (pure function of series) | YES | YES | YES (any per-round metric series) |

All five innovations preserve D.4 30/30, ruff 0, mkdocs 0 warnings,
and vendored purity. The harness + matrix + interface pattern is
directly reusable by other research groups integrating flow-matching
adapters into a multi-round re-inference framework.

---

## 8. File inventory

| File | Status |
|---|---|
| `tools/batched_framework_cifar.py` | NEW (W290 P3) |
| `tools/adversarial_scheduler_test.py` | NEW (W287 P) |
| `adaptive_reflow/adapters/profile_residual.py` | EXISTING (W229 P3 / W230 P1) |
| `adaptive_reflow/eval/fid_theorem_aligned.py` | EXISTING (W11 / W12 / W14) |
| `adaptive_reflow/eval/lipschitz_diagnostic.py` | EXISTING (W11 / W12) |
| `docs/audit/wave298-p4-engineering-innovations.md` | NEW (this file) |

---

## 9. Invariants

| Invariant | Status |
|---|---|
| D.4 30/30 | **PASS** (no source changes; all 5 innovations either are byte-stable by construction or verified byte-stable in their wave audit) |
| Ruff 0 on new doc | **PASS** (this file is a doc; no Python surface added) |
| Mkdocs 0 warnings | **PASS** (audit doc added under `docs/audit/` which is `not_in_nav` per `mkdocs.yml:239`) |
| Vendored NOT touched | **PASS** (READ-ONLY audit; no edits under `vendored/`, `data/`, or any third-party tree) |
| existing framework source NOT modified | **PASS** (this is a READ-ONLY audit; only NEW file `docs/audit/wave298-p4-engineering-innovations.md`) |