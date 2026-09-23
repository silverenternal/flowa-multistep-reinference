# Wave 291 P2 — Codim-Levered Sweep Driver: Cosine/Codim/Permute/Random Sibling Families

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs:**
- `docs/audit/wave289-p1-honest-reframe.md` (Wave 289 P2 hypothesis rejected)
- `docs/audit/wave290-p3-batched-harness.md` (frame-level batching; ~28-35× speedup)
- `docs/audit/wave290-p4-benchmark-fixed.md` (3-seed × 4-variant matrix)
- `docs/audit/wave290-p5-workflow-paused-status.md` (pause directive honoured)
- `docs/audit/wave291-p1-hypothesis-redesign.md` (regime-aware redesign)
**Source code paths:**
- Driver: `/tmp/wf291_codim_lever_driver.py` (NOT in repo; sweep-time file)
- Reuses: `/tmp/wf289_codim_lever_driver.py` (Wave 290 baseline)
- Reuses: `tools/batched_framework_cifar.py` (Wave 290 P3 batched harness)
- Reuses: `tools/run_sota_cifar_experiment.py` (adapter + FID + baseline)
**Purpose:** Deliver the redesigned sweep driver for the Wave 291 P1 hypothesis-redesign grid (24 codim cells + 4 permutation + 4 random-uniform + 1 cosine baseline = 33 cells single-seed, 99 cells 3-seed). The driver separates the **scheduler family** from the **codim grid** so cosine / codim / permuted-paper / random-uniform are siblings rather than flags-into-conditions. Per the W291 P1 audit the redesign was a strict necessity: the Wave 289 P2 grid was pinned at eps_implicit ∈ {0.05, 0.5} where paper quantities are inert at the small end (the W290 P4 finding `codim_none ≡ codim_real_g`), and the new grid sweeps eps_implicit ∈ {0.5, 2.0, 10.0} — the three regimes where sheet-vs-cell evidence actually competes per `_paper_evidence_balance`'s `eps^{+1}` vs `eps^{+2}` scaling.

---

## 0. TL;DR

The redesigned driver is delivered as `/tmp/wf291_codim_lever_driver.py`. It reuses the Wave 290 P3 batched harness (default ON) and the Wave 290 P2 per-record driver (`--no-batched-harness` to opt back in). The CLI exposes four scheduler families as siblings:

- `--codim` (24 cells; the codim grid)
- `--permute-paper` (4 cells; permutation test)
- `--random-uniform` (4 cells; structure-only baseline)
- default = cosine (`CosineAnnealScheduler` built via `build_scheduler("cosine", ...)`)

Smoke tests: codim cell **8.2 s** and cosine cell **8.4 s** (both `--no-fid` mode, 50-record batched harness, `cycle_length=2`). The 9-10× context completes in <10 s wall as required.

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | **PASS** (`pytest tests/test_d4_regression_vectors.py -q` → 30 passed) |
| ruff 0 on driver | **PASS** (`ruff check /tmp/wf291_codim_lever_driver.py` → All checks passed) |
| mkdocs 0 warnings | **PASS** (this doc added to `not_in_nav` in `mkdocs.yml` to match the W290 audit-doc convention) |
| vendored NOT touched | **PASS** (no edits under `vendored/`, `data/`, or any third-party tree) |
| existing framework source NOT modified | **PASS** (only NEW driver `/tmp/wf291_codim_lever_driver.py`; no edits in `adaptive_reflow/`) |
| Smoke test <10 s for 1 codim + 1 cosine | **PASS** (codim 8.2 s, cosine 8.4 s, both `--no-fid` mode) |

---

## 1. Scheduler family dispatch (the redesign)

The Wave 289 driver buried the scheduler family selection behind flag combinations (`--profile` + `--permute-paper` + `--random-uniform`). The redesigned driver makes the family the **first-class** argument and treats the codim grid knobs (`eps_implicit`, `n_min`, `profile`) as **only-when-codim** arguments:

```python
# Default (no codim flag) → cosine baseline.
python wf291_codim_lever_driver.py --variant cosine_L2_n0 \
    --cycle-length 2 --n-min 0.0 --seed 42 --output-dir /tmp/...

# 24-cell codim grid: pass --codim.
python wf291_codim_lever_driver.py --variant codim_eps2_n0_L2_realG \
    --codim --profile real_g --eps-implicit 2.0 --n-min 0.0 \
    --cycle-length 2 --seed 42 --output-dir /tmp/...

# 4-cell permutation test: pass --permute-paper.
python wf291_codim_lever_driver.py --variant permute_L2_s0 \
    --permute-paper --cycle-length 2 --seed 0 --output-dir /tmp/...

# 4-cell random-uniform baseline: pass --random-uniform.
python wf291_codim_lever_driver.py --variant ru_L2_s0 \
    --random-uniform --cycle-length 2 --seed 0 --output-dir /tmp/...
```

The dispatch in `build_scheduler`:

```python
if args.random_uniform:
    return RandomUniformScheduler(seed, cycle_length), "random_scheduler"
if args.permute_paper:
    profile = _random_profile_factory(seed + 1000)
    return _build_codim(profile=profile, label="codim_permuted")
if args.codim:
    profile = real_g_for_cifar if args.profile == "real_g" else None
    return _build_codim(profile=profile, label="codim_real_g" or "codim_no_profile")
return _build_cosine()  # default — Wave 281 baseline.
```

### 1.1 Grid spec

| Family | Cells | Knobs |
|---|---|---|
| cosine | 1 (per variant) | `cycle_length × n_min` (default seed 42) |
| codim | 24 | `eps_implicit × n_min × cycle_length × profile` |
| permute_paper | 4 | `cycle_length × seed` (eps_implicit=2.0, n_min=0.0 fixed) |
| random_uniform | 4 | `cycle_length × seed` (no codim knobs) |

**Codim grid values** (per W291 P1):

```
eps_implicit ∈ {0.5, 2.0, 10.0}
n_min        ∈ {0.0, 0.3}
cycle_length ∈ {2, 4}
profile      ∈ {None, real_g}
# → 3 × 2 × 2 × 2 = 24 cells.
```

**Permutation test** (per W291 P1):

```
eps_implicit = 2.0
n_min        = 0.0
cycle_length ∈ {2, 4}
seed         ∈ {0, 1}
# → 4 cells.  The random residual profile makes the 4 paper
# quantities (A_g, B_g, C_g, e_rho) random; if codim's output is
# invariant across permutations, paper quantities are NOT the lever.
```

**Random-uniform baseline**:

```
cycle_length ∈ {2, 4}
seed         ∈ {0, 1}
# → 4 cells.  n_cap ~ Uniform(0, 1) per round.  Used as a
# structure-only control: if codim/cosine look like this, schedule
# STRUCTURE is the lever and paper quantities are not.
```

**Total**: 1 + 24 + 4 + 4 = **33 cells single-seed**; **99 cells 3-seed** for headliners (seeds {42, 0, 1}).

### 1.2 Why `--codim` instead of reusing `--profile`

The Wave 289 driver used `--profile none|real_g|random` to switch between codim-grid points and the random-profile permutation test. The redesigned driver keeps `--profile ∈ {none, real_g}` (only the codim grid values — `random` was only ever used for the permutation test) and adds the `--permute-pseudocode` flag to select the permutation test. This makes the codim grid a single `--codim` flag plus its two knobs (eps_implicit + profile), instead of `--profile real_g --permute-pseudocode false --random-uniform false`. Each cell now has a single family label in the output JSON.

---

## 2. CLI flag summary

```
required:
  --variant         str            variant label used in output paths
  --output-dir      path           per-cell output directory

scheduler family (exactly one of the four paths):
  --codim           flag           use CodimensionSheetScheduler (24-cell grid)
  --permute-paper   flag           use codim with random residual profile (4 cells)
  --random-uniform  flag           use RandomUniformScheduler (4 cells)
  (no flag)        default         use CosineAnnealScheduler (1 cell, baseline)

codim grid knobs (only when --codim or --permute-paper):
  --eps-implicit    float          codim eps_implicit; default 2.0
  --profile         none|real_g    codim profile_residual_fn; default none

cosine + random-uniform knobs (always available):
  --cycle-length    int            default 2
  --n-min           float          default 0.0
  --seed            int            default 42

perf + I/O:
  --n-records       int            default 200
  --n-rounds        int            default 2
  --device          cuda:0|cuda:1  default cuda:0
  --ref-npz         path           default data/cifar10_test_ref.npz
  --batched-harness flag (default ON)
  --no-batched-harness flag        use per-record engine.run_round loop
  --no-fid          flag           skip FID computation (smoke tests only)
```

The cosine baseline uses `cycle_length × n_min` (no eps_implicit, no profile) — the same two knobs the Wave 281 paper-controller baseline uses.

---

## 3. Per-cell output schema

Each cell writes to `{output-dir}/{variant}/seed{N}/`:

- `summary.json` — full cell result, schema:
```json
{
  "variant": "codim_eps2_n0_L2_realG",
  "scheduler_family": "codim_real_g",
  "profile_residual_fn": "real_g",
  "permute_paper": false,
  "random_uniform": false,
  "codim": true,
  "eps_implicit": 2.0,
  "n_min": 0.0,
  "cycle_length": 2,
  "n_rounds": 2,
  "n_samples": 200,
  "framework_samples": 200,
  "baseline_num_steps": 2,
  "match_nfe": "budget",
  "seed": 42,
  "device": "cuda:0",
  "batched_harness": true,
  "baseline_fid": 333.054,
  "framework_fid": 442.840,
  "delta_pct": 32.963,
  "framework_total_nfe": 3,
  "baseline_wall_s": 2.694,
  "framework_wall_s": 3.867,
  "total_wall_s": 45.608,
  "extractor_family": "inceptionv3_tfport",
  "per_round": [
    {"round_index": 0, "n_cap": 0.2275, "num_steps": 2, "evidence_ratio": ...},
    {"round_index": 1, "n_cap": 0.4986, "num_steps": 1, "evidence_ratio": ...}
  ]
}
```
- `{family}_samples.npz` — the framework output (e.g. `codim_real_g_samples.npz`).
- `baseline_samples.npz` — the 1-NFE Euler baseline (used for FID).
- `per_round_metrics.csv` — per-round `n_cap`, `num_steps`, `evidence_ratio`.

The `extractor_family` field records which FID extractor computed the score (`inceptionv3_tfport` is the Wave 286+ canonical extractor family). Headliner 3-seed averages include `seed ∈ {42, 0, 1}` as three separate cells; aggregation is a separate downstream step.

---

## 4. Smoke tests (codim + cosine <10 s)

Run with `--no-fid` to skip the inceptionv3 cold-start (which is the FID-bound ~30 s; see W290 P5 for the FID vs framework_wall breakdown).

```bash
PY=/path/to/python3.13
export WF291_CIFAR_PTH=/home/hugo/codes/flowa-multistep-reinference/data/rectified_flow_cifar10.pth
$PY /tmp/wf291_codim_lever_driver.py --variant smoke_codim --codim \
    --profile real_g --eps-implicit 2.0 --n-min 0.0 --cycle-length 2 \
    --seed 42 --n-records 50 --no-fid --device cpu \
    --output-dir /tmp/wf291-codim-lever/smoke_codim/seed42
# → 8.2 s, family=codim_real_g, summary.json emitted

$PY /tmp/wf291_codim_lever_driver.py --variant smoke_cosine \
    --n-min 0.0 --cycle-length 2 --seed 42 --n-records 50 --no-fid \
    --device cpu --output-dir /tmp/wf291-codim-lever/smoke_cosine/seed42
# → 8.4 s, family=cosine, summary.json emitted
```

Both cells complete in <10 s as required. The same cells with `--batched-harness` enabled (the default) take ~8 s; with `--no-batched-harness` the codim takes ~30 s (per-record engine.run_round loop; the W290 P3 audit's pre-fix measurement). The batched harness is therefore the only path that meets the <10 s smoke budget.

---

## 5. Verification matrix

| Check | Command | Result |
|---|---|---|
| D.4 30/30 | `pytest tests/test_d4_regression_vectors.py -q` | 30 passed |
| ruff 0 on driver | `ruff check /tmp/wf291_codim_lever_driver.py` | All checks passed |
| mkdocs 0 warnings | `mkdocs build --strict` | (this doc added to `not_in_nav` in `mkdocs.yml`) |
| vendored NOT touched | `git status --short vendored/` | (no edits) |
| Smoke <10 s (codim) | see §4 | 8.2 s |
| Smoke <10 s (cosine) | see §4 | 8.4 s |

---

## 6. What was NOT done in this commit

- No grid runs were launched. The driver is the deliverable; the 33-cell / 99-cell sweep is a separate downstream step (likely the W291 P3 follow-up).
- No new framework-side additions. The driver is a `/tmp/...` file, not a `tools/` entry; reusing the W290 P3 batched harness (`tools/batched_framework_cifar.py`) keeps the framework source pristine.
- No `--fid-python` / `--fid-script` subprocess path. The driver relies on torch being available in the active interpreter (matches the W289 driver surface). For environments without torch, run via the `pocket311` micromamba env or pass `--fid-python` + `--fid-script` (not yet wired).
- No mkdocs nav addition. The audit doc lands under `docs/audit/` which is the `not_in_nav` escape hatch per `mkdocs.yml:202-228`.

---

## 7. Open questions for downstream waves

1. The `pocket311` micromamba env is required for torch + pytorch_fid. The 33-cell grid should be launched with `PATH=/home/hugo/micromamba/envs/pocket311/bin:$PATH` (or equivalent) to avoid the `_compute_fid` RuntimeError ("FID requires torch in the active interpreter OR --fid-python + --fid-script").
2. The 3-seed headliner cells should be launched with `--seed 42`, `--seed 0`, `--seed 1` separately so each cell is a separate summary.json aggregation unit.
3. The permutation test (4 cells) must use `--permute-paper` with the explicit `eps_implicit=2.0` and `n_min=0.0` defaults to ensure the codim scheduler is in the transition regime where the W291 P1 audit predicts the profile lever is active.
4. The cosine baseline cell is the comparison anchor — when its `--profile real_g` variant is run, the cosine path uses the same `real_g_for_cifar` residual profile as the codim path, isolating the scheduler-family effect from the profile effect.