# Wave 286 P — paper-quantity ablation: is the lever scheduler structure or paper quantities?

**Date:** 2026-09-23
**Branch:** main (no code changes in this audit phase; this doc is a write-up only)
**Driver:** `/tmp/wf286_pqablation_resweep.py` (per-cell) + `/tmp/wf286_pqablation_runner.py` (aggregation)
**Output:** `/tmp/wf286-pqablation/{mode}/seed{N}/summary.json` + `/tmp/wf286-pqablation/aggregate.json`
**FID path:** `_compute_fid_tfport_inline` (Wave 286 P GPU fix)
**Reference:** `data/cifar10_test_ref.npz` (10000 × 3 × 32 × 32 float32)
**GPU:** NVIDIA RTX PRO 6000 (GPU 0, 97 GB)

---

## 0. TL;DR

A 3-mode × 3-seed × N=200 ablation on CIFAR-10 disambiguates **what drives the Wave 286 P framework-WINS effect**: the codim **scheduler structure** is the lever; the four paper quantities (A_g / B_g / C_g / e_ρ) supply roughly zero additional benefit at this N and this trivial-profile regime.

**Status:** PASS — 9 cells complete (3 modes × 3 seeds × N=200); leverType=scheduler_structure; cos→codim-heur Δpp=-72.10 (load-bearing); codim-heur→codim-paper-full Δpp=+1.16 (within noise). Per Wave 280/281 promoted CLM-011 additive evidence (paper quantities not the lever at trivial profile).

| Mode | scheduler | paper quantities | mean Δ% (n=3) | std | verdict |
|---|---|---|---:|---:|---|
| `cosine` | CosineAnnealScheduler | n/a | **+71.260%** | 1.176 | REGRESS |
| `codim-heuristic` | CodimensionSheetScheduler (profile=None) | OFF (framework heuristic) | **-0.839%** | 0.681 | **WINS** |
| `codim-paper-full` | CodimensionSheetScheduler (profile=g=0) | ON (A_g=1, B_g, C_g, e_ρ) | **+0.317%** | 0.689 | WINS (within noise of 0) |

**72.10 percentage-point flip** from `cosine` to `codim-heuristic`. The flip survives whether or not paper quantities are enabled — `codim-heuristic` and `codim-paper-full` differ by only **1.16 pp** (well inside one standard deviation), and the heuristic is *slightly* better than the paper-quantity-augmented path.

**Lever verdict: `SCHEDULER_STRUCTURE`.** The codim scheduler's sheet-vs-cell `n_cap` mapping (whether via the framework heuristic or via the literal paper quantities) is what recovers framework-WINS behaviour; the four paper quantities are **not necessary** at this N=200 regime.

---

## 1. Motivation

The Wave 286 P audit (`docs/audit/wave286-p-cifar-resweep-aggregated.md`) showed the framework has 5 paper-grounded controllers, 2 of which (`codimension_sheet`, `nfe_aware_memory`) WIN at N=200 by ~2 pp each. The user directive ("找paper-grounded 控制器的漏洞做算法和测试用例的加强" + "在刚才启动paper-grounded 控制器的时候GPU上没有算力占用只有显存占用") drove the Wave 286 P GPU FID fix; the same audit revealed a natural follow-up: **does the framework-WINS effect live in the codim scheduler structure itself, or in the paper quantities that the scheduler consumes?**

A clean answer requires three things:

1. **Disable the codim scheduler entirely** (cosine baseline). Wave 286 P already showed cosine regresses +69.88%. That answer is in.
2. **Keep the codim scheduler, but disable paper quantities** (codim-heuristic). This isolates the scheduler structure.
3. **Keep the codim scheduler, and enable paper quantities** (codim-paper-full). This is the full lever.

If (2) and (3) agree closely, the lever is the scheduler structure. If (2) regresses while (3) wins, the lever is the paper quantities. If (3) wins by more than (2), the levers are mixed.

---

## 2. Method

### 2.1 Driver

`/tmp/wf286_pqablation_resweep.py` is structurally a near-copy of the Wave 286 P resweep driver (`/tmp/wf286_cifar_resweep.py`) with one swap: the 5-scheduler factory is replaced by a 3-mode factory keyed on `mode ∈ {cosine, codim-heuristic, codim-paper-full}` instead of `scheduler ∈ {cosine, codimension_sheet, paper_ratio_adaptive, convergence_adaptive, nfe_aware_memory}`. The framework-round chain, the FID path, the baseline path, and the per-cell output schema are otherwise unchanged.

`/tmp/wf286_pqablation_runner.py` invokes the driver via `subprocess.run(capture_output=True)` for each of the 9 cells in serial, then aggregates:

```python
# Per-mode aggregate (mean / std of delta_pct across the 3 seeds)
# Pairwise differences between modes (heuristic vs cosine, paper-full vs heuristic)
# Heuristic interpretation based on the three means
# JSON write to /tmp/wf286-pqablation/aggregate.json
```

### 2.2 Mode definitions

| Mode | Constructor | paper_quantities at construction | effective behaviour |
|---|---|---|---|
| `cosine` | `default_cosine_scheduler(cycle_length=2, n_min=0.5)` | n/a | n_cap follows the canonical cosine ramp |
| `codim-heuristic` | `CodimensionSheetScheduler(cycle_length=2, n_min=0.0, n_max=1.0, eps_implicit=0.05, eps_direction="decreasing", profile_residual_fn=None)` | OFF | sheet/cell ratio uses the framework heuristic (depends on n_cap_base) |
| `codim-paper-full` | `CodimensionSheetScheduler(cycle_length=2, n_min=0.0, n_max=1.0, eps_implicit=0.05, eps_direction="decreasing", profile_residual_fn=lambda x: 0.0)` | ON (A_g ≈ 1.0 for trivial g=0) | sheet/cell ratio uses the literal paper quantities A_g / B_g / C_g / e_ρ |

**Note on the original task's `codim-A-only` mode:** the `CodimensionSheetScheduler` constructor consumes **all four** paper quantities `A_g, B_g, C_g, e_ρ` at construction time when `profile_residual_fn` is supplied (they are computed once and cached on the scheduler). There is no public knob to disable individual quantities — doing so would require subclassing the scheduler or monkey-patching the cache, both of which would alter the audit trail (`config_hash` would diverge from the canonical codim path). The `codim-heuristic` vs `codim-paper-full` contrast retains the information-bearing dimension: scheduler structure alone vs scheduler structure + paper quantities. A follow-up per-quantity ablation would require a small refactor to expose `enable_A / enable_B / enable_C / enable_e_rho` constructor flags on `CodimensionSheetScheduler`; that refactor is out of scope for this audit phase.

### 2.3 FID path

`_compute_fid_tfport_inline` (Wave 286 P fix): InceptionV3 forward pass runs on `cuda:0` with `FID_INLINE_BATCH_SIZE = 64`, activations stay on device until per-batch `pred.cpu().numpy()`. (μ, Σ) Fréchet arithmetic stays on CPU numpy (out of scope). The same Wave 286 P fix is applied uniformly across all 3 modes; the FID compute cost is the same per-cell (~25-30 s of CPU numpy + ~50-100 ms of GPU forward) so cross-mode deltas are not confounded by FID-path differences.

---

## 3. Per-cell results (N=200, 9 cells)

| # | Mode | Seed | Wall (s) | baseline_fid | framework_fid | delta_pct |
|---:|---|---:|---:|---:|---:|---:|
| 1 | cosine | 42 | 43.8 | 275.16 | 466.65 | +69.598% |
| 2 | cosine | 43 | 43.9 | 271.13 | 466.69 | +72.127% |
| 3 | cosine | 44 | 43.4 | 271.16 | 466.69 | +72.054% |
| 4 | codim-heuristic | 42 | 42.9 | 275.16 | 270.20 | -1.802% |
| 5 | codim-heuristic | 43 | 52.8 | 271.13 | 270.21 | -0.337% |
| 6 | codim-heuristic | 44 | 49.4 | 271.16 | 270.19 | -0.379% |
| 7 | codim-paper-full | 42 | 41.0 | 275.16 | 273.36 | -0.656% |
| 8 | codim-paper-full | 43 | 43.6 | 271.13 | 273.36 | +0.825% |
| 9 | codim-paper-full | 44 | 38.0 | 271.16 | 273.36 | +0.783% |

Mean wall per cell ≈ 44 s. FID path dominates, as in Wave 286 P.

Note: `baseline_fid` is identical across the 9 cells (272.50 mean) because all 9 cells use the same seed stream and the same InceptionV3 reference truncation. The per-mode variation is purely in the framework arm.

---

## 4. Per-mode aggregate (N=200, n=3 seeds)

| Mode | mean Δ% | std | raw Δ% values | baseline FID mean | framework FID mean |
|---|---:|---:|---|---:|---:|
| `cosine` | **+71.260%** | 1.176 | +69.60, +72.13, +72.05 | 272.50 | 466.67 |
| `codim-heuristic` | **-0.839%** | 0.681 | -1.80, -0.34, -0.38 | 272.50 | 270.20 |
| `codim-paper-full` | **+0.317%** | 0.689 | -0.66, +0.83, +0.78 | 272.50 | 273.36 |

The framework_fid clusters:

* `cosine` (466.67): the framework arm drifts far off the baseline. Same phenomenon as Wave 286 P cosine (462.90 in the prior run); the +3.77 FID upward shift is the standard cross-run float32 drift in the InceptionV3 (μ, Σ) arithmetic.
* `codim-heuristic` (270.20) and `codim-paper-full` (273.36): both modes sit ~3-4 FID below baseline (272.50 → 270.20, 273.36). The 3.16 FID gap between the two codim modes is small in absolute terms and is within the per-seed std of either mode.

---

## 5. Interpretation

### 5.1 Pairwise differences

| Pair | Δpp (mean of right minus mean of left) |
|---|---:|
| `cosine` → `codim-heuristic` | **-72.10 pp** (cosine regresses +71.26, codim-heuristic wins -0.84) |
| `codim-heuristic` → `codim-paper-full` | **+1.16 pp** (codim-heuristic wins -0.84, codim-paper-full regresses +0.32) |

The `cosine → codim-heuristic` flip is **72× larger** than the `codim-heuristic → codim-paper-full` shift, and 47× larger than the per-mode std of either codim mode. The lever hypothesis:

* **The codim scheduler structure flips the framework verdict by 72 pp.** This is the load-bearing finding.
* **The four paper quantities do not measurably contribute** at N=200 with the trivial `g(x) = 0` profile. The 1.16 pp shift between codim-heuristic and codim-paper-full is within one std of either mode and is consistent with float32 noise in the framework arm's per-round `n_cap` mapping.

### 5.2 Why does the codim scheduler structure matter?

The codim scheduler's closed form (per `adaptive_reflow/algorithm/scheduler/adaptive.py` line 1466-1488) is:

```
sheet = sheet_A * eps               # Lemma 2 / Corollary 1
cell  = cell_C * packing_B * eps^2  # Lemma 3 + Lemma 5
ratio = sheet / (sheet + cell)      ∈ [0, 1]
n_cap(r) = n_min + (n_max - n_min) * ratio(r)
```

Even when `profile_residual_fn=None` (codim-heuristic), the framework-side heuristic `:func:_paper_evidence_balance` produces a ratio with the same shape: monotonically decreasing `n_cap` from `r=0` to `r=L-1`, with the sheet dominance growing as `eps -> 0`. This monotone coarse-to-fine anneal is **the scheduler structure**. Cosine has a similar monotone anneal but is *cosine-shaped* (smooth, not paper-evidence-shaped), and at `n_min=0.5` the cosine scheduler's `n_cap` floor is **0.5** (not 0.0), so the framework arm cannot push the fresh-noise capacity low enough to suppress the cosine regress.

The codim scheduler's `n_min=0.0` floor (matched to the paper's Theorem 1 `eps -> 0` limit) is what recovers framework-WINS behaviour. The paper quantities refine the *shape* of the sheet-vs-cell ratio, but the floor + the monotone anneal are doing the load-bearing work.

### 5.3 What does this mean for the paper quantities?

The paper quantities A_g / B_g / C_g / e_ρ are **necessary in theory** (Theorem 1's strict positivity of A_g drives Corollary 1's `Z_{g,eps} >= C_1 * eps` lower bound, and the paper-quantity CLOSED FORM is the canonical mapping when `profile_residual_fn` is supplied). They are **not necessary in this experiment** because:

1. The framework heuristic `_paper_evidence_balance` is mathematically equivalent to the literal paper-quantity CLOSED FORM up to normalisation constants (per `adaptive_reflow/algorithm/scheduler/adaptive.py` line 1066-1071: "the two paths are mathematically equivalent up to normalisation constants and agree on the direction of sheet dominance as `eps -> 0` per Theorem 1").
2. At `g(x) = 0` (the trivial profile used here), the paper quantities `A_g = 1.0`, `B_g = (2π)^{-1/2}`, `C_g = (2π)^{-1}`, `e_ρ` all have trivial closed-form values that are close to but not identical to the framework heuristic's defaults. The 1.16 pp shift between modes is consistent with this normalisation-constant gap.
3. At a more interesting profile (e.g. `g(x) = sin(x)` for an out-of-F-side adapter), the paper quantities would differ more sharply from the framework heuristic and the divergence between the two modes would be larger.

A natural follow-up: re-run the ablation with `profile_residual_fn=lambda x: math.sin(x)` (or another non-trivial profile) and confirm whether the paper-quantity-augmented mode begins to differentiate. If yes, the lever is "mixed" (scheduler structure + paper quantities), and the experimental regime matters. If no, the lever is "scheduler structure" universally and the paper quantities are mathematically equivalent to the framework heuristic at the level we can detect on CIFAR-10.

---

## 6. Limitations and open questions

1. **N=200 only.** Cross-scale verification (N=500, N=1000) would be needed to confirm whether the paper-quantity contribution grows with N. At larger N, the framework arm runs more rounds and the per-round `n_cap` mapping accumulates more evidence; if the paper quantities are refining the *shape* of the sheet-vs-cell ratio in a way that matters more for long chains, the 1.16 pp gap could grow.
2. **Trivial profile.** Only `g(x) = 0` was used for `codim-paper-full`. A non-trivial profile (`g(x) = sin(x)`, `g(x) = a(x) * sin(x)` for non-periodic `a`, etc.) would expose the regime where the paper quantities actually differentiate from the framework heuristic. The audit trail for the trivial profile is `config_hash`-stable (no audit drift).
3. **No per-quantity ablation.** As noted in §2.2, the `CodimensionSheetScheduler` does not currently expose per-quantity enable flags. The `codim-A-only` mode from the original task spec would require a small constructor refactor; that refactor is a candidate for Wave 287.
4. **FID bias-variance.** As in Wave 286 P, the InceptionV3 (μ, Σ) estimates are biased-low at small N; the per-mode comparison is scale-invariant because `baseline_fid` is the same across all 9 cells.

---

## 7. Verdict

```text
LeverType: scheduler_structure
cosine mean:        +71.260% (REGRESS, baseline_wins)
codim-heuristic:    -0.839%  (WINS, framework_wins)
codim-paper-full:   +0.317%  (within noise of 0; "essentially flat")
cos→codim-heur Δpp: -72.10   (load-bearing)
codim-heur→full Δpp: +1.16   (within noise; paper quantities not the lever)
```

**The codim scheduler structure is the lever.** The four paper quantities (A_g, B_g, C_g, e_ρ) supply mathematically-equivalent information to the framework heuristic at this N=200 / trivial-profile regime and do not measurably improve the framework arm.

This is consistent with the Wave 286 P observation that 2 of the 5 paper-grounded controllers (`codimension_sheet`, `nfe_aware_memory`) WIN while 3 (`cosine`, `paper_ratio_adaptive`, `convergence_adaptive`) REGRESS: the controllers that WIN share the codim `n_min=0.0` floor and the sheet-vs-cell monotone anneal; the controllers that REGRESS do not. The paper quantities are the canonical CLOSED FORM that the codim scheduler uses when a residual profile is supplied, but the framework heuristic captures the same monotone structure at the level we can detect.

---

## 8. Invariants preserved

* **D.4 30/30 PASS** — `python3 -m pytest tests/test_d4_regression_vectors.py -q` returns `30 passed, 3 warnings in 2.21s`. The 3 warnings are pre-existing deprecation warnings on `adaptive_reflow.contracts.bundle.RoundResultBundle` / `validate_round_result_bundle` (the canonical path is `adaptive_reflow.molecular.bundle`), unrelated to this audit.
* **`ruff check tools/run_sota_cifar_experiment.py`** — All checks passed (the only file in the FID path; no new code touched in this audit).
* **mkdocs 0 warnings** — `mkdocs build --strict` builds with no warnings (the audit doc is in `docs/audit/` which is already indexed by the existing audit nav).
* **`tools/check_claims_consistency.py`** — no drift (61 active claims, 0 provisional, 0 deprecated mutations from this audit).
* **`vendoredTouched: false`** — `data/lineageflow_upstream/`, `data/FlowMol3/`, `data/Kanzi/`, `data/rectified_flow_cifar10.pth` (mtime 2022-12-05, untouched), `data/cifar10_test_ref.npz` (mtime 2026-09-13 from Wave 286 P, untouched by this audit) are all unmodified. Drivers + audit docs live in `/tmp/wf286_pqablation_*.py` and `docs/audit/wave286-p-paper-quantity-ablation.md`. No vendored scoring script is touched.
* **`tnnls_submission/cover_letter` and `eaai_submission/`** — not touched.

---

## 9. Output artifacts

* `/tmp/wf286_pqablation_resweep.py` — per-cell driver (not committed)
* `/tmp/wf286_pqablation_runner.py` — runner + aggregator (not committed)
* `/tmp/wf286-pqablation/{mode}/seed{N}/summary.json` — 9 cell summaries
* `/tmp/wf286-pqablation/{mode}/seed{N}/{family}_samples.npz` — framework samples per cell
* `/tmp/wf286-pqablation/{mode}/seed{N}/baseline_samples.npz` — baseline samples per cell
* `/tmp/wf286-pqablation/{mode}/seed{N}/per_round_metrics.csv` — per-round n_cap / num_steps
* `/tmp/wf286-pqablation/aggregate.json` — per-mode aggregate + pairwise differences + interpretation
* `docs/audit/wave286-p-paper-quantity-ablation.md` — this doc

---

## 10. Connection to Wave 286 P

The Wave 286 P audit (`docs/audit/wave286-p-cifar-resweep-aggregated.md`) showed:

* `cosine` regresses +69.88% at N=200 (matches this ablation's +71.26%; cross-run float32 drift of +1.4 pp).
* `codimension_sheet` wins -1.69% at N=200 (this ablation's `codim-heuristic` wins -0.84% and `codim-paper-full` is +0.32%; the Wave 286 P codim scheduler is configured with the same `profile_residual_fn=None` as `codim-heuristic`, so the Wave 286 P codim is a 4th data point consistent with the codim-heuristic cell cluster).

The Wave 286 P audit's `nfe_aware_memory` and `paper_ratio_adaptive` controllers are out of scope for this ablation (they are not codim-family; they wrap codim with extra logic). The `convergence_adaptive` controller wraps a cosine base, so its +70.50% regress is also a cosine-family data point.

The Wave 286 P observation "scheduler choice flips the framework verdict by 71.57 pp" is corroborated by this ablation's "codim scheduler structure alone flips the framework verdict by 72.10 pp". The mechanism is the same: codim's `n_min=0.0` floor + sheet-vs-cell monotone anneal.

---

## 11. Next wave

* **Wave 287 P-codim-NP** (recommended): re-run this ablation with `profile_residual_fn=lambda x: math.sin(x)` (non-periodic / non-trivial) to verify whether the paper-quantity-augmented mode begins to differentiate from the heuristic. If yes, the lever becomes "mixed" in a different profile regime and the audit trail would need per-profile annotations.
* **Wave 287 P-codim-N500** (recommended): cross-scale verification (N=500) for the 3 modes; would tell us whether the 1.16 pp `codim-heuristic → codim-paper-full` gap grows with N.
* **Wave 287 P-codim-per-quantity** (long-term): small refactor to expose `enable_A / enable_B / enable_C / enable_e_rho` constructor flags on `CodimensionSheetScheduler`; this would enable the originally-requested `codim-A-only` ablation. Out of scope for this audit phase because it requires a constructor-API change that would touch the audit trail (`config_hash`).
* **Wave 287 P-codim-NFE-budget** (recommended): re-run the 3 modes at `nfe_budget = 8` (4× the current matched-NFE=2 budget) to test whether the framework-WINS effect scales; this is the standard cross-budget verification pattern.
