# Wave 181 P1 — AB-Cache setup (training-free diffusion cache-reuse baseline)

**Date:** 2026-09-18
**Branch:** main (HEAD `b406369`, pre-Wave-181 state)
**Scope:** Wave 181 P1 — install / set up AB-Cache (the second
closest training-free diffusion inference acceleration competitor)
for head-to-head comparison with FlowA on the R6 task (LineageFlow
protein gen).

---

## 1. Goal

Set up an AB-Cache baseline in our environment so Wave 181 P2 can
run it on the R6 task (LineageFlow NFE=100/200, seeds 42/43/44) and
Wave 181 P3 can compare 4 arms — vanilla / Fast-DLLM / AB-Cache /
FlowA — on ΔpLDDT + ΔscPerplexity vs vanilla baseline.

Reference: AB-Cache (Yu et al. 2024, "AB-Cache: Training-Free
Acceleration of Diffusion Models via Adams-Bashforth Cached Feature
Reuse", `arXiv:2504.10540`,
https://github.com/aSleepyTree/AB-Cache).

---

## 2. Availability status

### 2.1 Repo location

| item                     | value                                                                  |
|--------------------------|------------------------------------------------------------------------|
| upstream repo URL (task) | https://github.com/AntResearch/AB-Cache (NOT FOUND — 404)              |
| upstream repo URL (real) | https://github.com/aSleepyTree/AB-Cache (CLONED OK)                    |
| cloned at                | `/tmp/AB-Cache/` (depth-1, via `git clone --depth 1`)                  |
| tree                     | `flux_our.py`, `pipeline_flux_our.py`, `flux_base.py`, `pipeline_flux.py`, `pab.py`, `clipscore.py`, `base.py` |

The task prompt's stated URL `https://github.com/AntResearch/
AB-Cache` does not resolve (404 from `git clone`). WebSearch
confirmed the canonical implementation is under the personal GitHub
account `aSleepyTree/AB-Cache` (the same paper's authors — Yu,
Zou, Shao, Zhang, Xu, Huang, Zhao, Cun, Zhang — USTC/Fudan/CUHK/
Great Bay University). A separate project with the same name
(`andresnds/AB-Cache`) is the "Attention Balance Cache" paper
(`arXiv:2412.18888`) — a different paper entirely; not the one
referenced by the task.

### 2.2 Compatibility with our environment

**AB-Cache is NOT directly usable on our continuous flow-matching
tasks** (LineageFlow, Kanzi). AB-Cache's two contributions are:

1. **Cached feature reuse** — caches the last N velocity field
   outputs and reuses them across consecutive macro-steps. This
   contribution IS conceptually applicable to continuous ODE
   integration on the (L, K) state surface, but the cached-feature
   surface (transformer hidden states) has no direct analog in our
   per-position categorical surface.

2. **2-step (or 4-step) explicit Adams-Bashforth extrapolation** —
   uses the last two cached velocity outputs to compute a
   higher-order step **without** calling the velocity field:
   ``x_{n+1} = x_n + dt * (2 * v_n - v_{n-1})``. This contribution
   IS directly applicable to continuous flow matching with no
   architectural changes — the velocity field is a pure function
   ``(x, t) -> v(x, t)`` and can be cached/reused on the same
   surface as the Euler baseline.

### 2.3 Chosen approach: AB-Cache-equivalent for continuous FM

Since the upstream AB-Cache repo cannot drive LineageFlow / Kanzi
out-of-the-box, we implement an **AB-Cache-equivalent solver** that
adapts the **periodic-2-step Adams-Bashforth cache-reuse** principle
to the continuous-ODE setting.

**Algorithm (continuous-FM analog):**

For each macro-step ``t_i → t_{i+1}``:

1. **Decision rule** (periodic, mirrors `flux_our.py:928`):
   * If ``i < warmup_steps`` (default 2): **recompute** Euler step.
   * Else if ``(i - warmup_steps - 1) % recompute_interval == 0``
     (default ``recompute_interval=6``): **recompute** Euler step.
   * Else: **cache-reuse** Adams-Bashforth step (no NFE).
2. **Recompute path** (1 NFE): take Euler step
   ``x_next = x_cur + dt * v(x_cur, t_i)``; enqueue ``v(x_cur, t_i)``
   to the cache.
3. **Cache-reuse path** (0 NFE): take 2-step Adams-Bashforth step
   ``x_next = x_cur + dt * (2 * v_n - v_{n-1})`` using the last
   two cached velocity outputs; cache is NOT updated.

This mirrors AB-Cache's `step()` (line 115-116) where the
"enable_cache" path applies `prev_sample = sample + (sigma_next -
sigma) * (2 * self.f[0] - self.f[1])`. For continuous FM, the
decision is between "trust the cached velocity outputs (AB
extrapolation, 0 NFE)" and "recompute the Euler step (1 NFE,
refreshes the cache)".

**Effective NFE**: ``warmup_steps + ceil((nfe - warmup_steps) /
recompute_interval)`` — for NFE=50 with default settings:
``2 + ceil(48 / 6) = 10 NFE`` (5x speedup over baseline Euler).
For NFE=100: ``2 + ceil(98 / 6) = 19 NFE`` (~5.3x speedup).

---

## 3. Files created

| path                                                              | purpose                                                                 |
|-------------------------------------------------------------------|-------------------------------------------------------------------------|
| `tools/abcache_solver.py`                                         | AB-Cache-equivalent solver (continuous-FM analog): periodic 2-step Adams-Bashforth cache-reuse ODE solver |
| `tools/w181_gen_abcache_fastas.py`                                | Wave 181 FASTA generator: drives the solver against LineageFlow adapter and emits wave-180-format FASTAs |
| `/tmp/w181/fastas/abcache_lineageflow_nfe{N}_seed{S}.fasta`       | (output dir; populated by Wave 181 P2)                                 |
| `/tmp/w181/fastas/abcache_lineageflow_nfe{N}_seed{S}.manifest.json` | per-cell manifest (Wave 181 P2 output)                              |
| `/tmp/w181/fastas/abcache_lineageflow_nfe{N}_seed{S}.solver_stats.json` | per-cell aggregated solver stats (mean effective NFE, recompute / reuse counts, cache reuse rate) for the audit doc |

The solver module is reusable beyond Wave 181 — any future
continuous-FM model (Kanzi, MM-FM, FreqFlow) can use the same
cache-reuse pattern by passing its `velocity_field(x, t)` callable
to `solve_ode_abcache`.

---

## 4. Smoke test (N=2, NFE=50, seed 42)

Verified end-to-end on the lineageflow_venv (synthetic mode):

```
$ .venvs/lineageflow_venv/bin/python tools/w181_gen_abcache_fastas.py \
    --n 2 --nfe 50 --seed 42 --outdir /tmp/w181/smoke
wrote /tmp/w181/smoke/abcache_lineageflow_nfe50_seed42.fasta (n=2) in 1.42s
```

Per-family solver stats (NFE=50, warmup=2, recompute_interval=6):

```json
{
  "PF00005.27": {
    "n_records": 1,
    "effective_nfe_mean": 10.0,
    "effective_nfe_std": 0.0,
    "n_recompute_steps_mean": 10.0,
    "n_cache_reuse_steps_mean": 40.0,
    "cache_reuse_rate_mean": 0.8
  },
  "PF00072.24": {
    "n_records": 1,
    "effective_nfe_mean": 10.0,
    "effective_nfe_std": 0.0,
    "n_recompute_steps_mean": 10.0,
    "n_cache_reuse_steps_mean": 40.0,
    "cache_reuse_rate_mean": 0.8
  }
}
```

Effective NFE = 10 (matches the predicted
``2 + ceil(48 / 6) = 10``), cache reuse rate = 0.8 (40 of 50
macro-steps used cache-reuse), confirming the solver runs at
~5x the baseline Euler NFE budget and demonstrates the expected
periodic cache-reuse behavior.

At NFE=100 (smoke test): effective NFE = 19, cache reuse rate = 0.81.
The cache reuse rate is stable across NFE values (limited by the
ratio of warmup steps to the trajectory length).

FASTA headers follow the wave-179/180 convention:

```
>abcache_seed0|family=PF00005.27
LPGKADQNGIKPHFWHPRADCGDKACEGISPALPCAHDMNMWCECGMIDHYNRNCLPPSADMYLGHFWCFWPVGLPPWHHVYKYFKHFTHSYAYMDNCQRPPITDGD
>abcache_seed1|family=PF00072.24
CELMIDHPWIMPVFHPFGENTGRIAEFNELEDLCFWFDTQDQDINFFNNAAAAHFRPNDGYKRALICVSCILVRIAAMDYITSPCIASACLMGGKWTVPKLWLGFSKGALHKVHPPYMFKRCN
```

---

## 5. Solver unit checks

Verified solver invariants:

* **Trajectory shape**: ``(nfe+1, 256, 33)`` matches the Euler
  baseline surface so downstream callers don't need to
  special-case the AB-Cache path.
* **NFE=50 default** → effective_nfe=10, recompute=10, reuse=40,
  rate=0.800 (matches ``2 + ceil(48/6) = 10``).
* **NFE=100 default** → effective_nfe=19, recompute=19, reuse=81,
  rate=0.810 (matches ``2 + ceil(98/6) = 19``).
* **warmup_steps=0** raises ``warmup_steps_must_be_at_least_
  queue_length-1_to_seed_cache`` (algorithm integrity guard).
* **queue_length=5, warmup=4** → final queue len = 5, effective
  NFE = 12 (warmup=4 + ceil(46/6) = 4 + 8 = 12), demonstrating
  the queue_length knob is wired correctly for the 4-step AB
  variant (paper line 119).
* **Edge cases**: nfe=0 raises, negative warmup_steps raises,
  recompute_interval=0 raises, queue_length=1 raises.

---

## 6. Methodology notes for Wave 181 P2 + P3

* **Per-cell matrix** (mirror wave 180 / wave 179 / wave 178 P6
  dispatch): 2 models (lineageflow, kanzi) × 3 NFE (50, 100, 200)
  × 3 seeds (42, 43, 44) × N=30 records = 540 records total. (For
  the headline R6 task, lineageflow only — kanzi comparison is a
  follow-up if time permits.)
* **Eval pipeline** unchanged from wave 179 P3: foldability + ESMFold
  pLDDT + scPerplexity on the same `tools.eval` harness.
* **Comparison arms**: vanilla (baseline.fasta, bare RNG, Wave 81)
  vs Fast-DLLM-equivalent (fastdllm.fasta, Wave 180 P2) vs
  AB-Cache-equivalent (abcache.fasta, this module) vs FlowA
  (framework.fasta, Wave 45 multi-round restart-blend). The
  comparison Δ is `metric(arm) - metric(vanilla)`, computed per
  (model, NFE, seed) cell.
* **Expected finding** (pre-Wave-181 P2 speculation, to be
  verified): AB-Cache-equivalent should sit between vanilla and
  FlowA on pLDDT (worse than FlowA — restart-blend + classifier
  awareness exploit Pfam-family structure that simple cache-reuse
  cannot reach). The result is publishable as §10.27 of the
  paper: "FlowA vs Fast-DLLM vs AB-Cache on R6 task — NFE-matched
  comparison".

---

## 7. Limitations + honest caveats

1. **Adapter mode**: smoke test ran on **synthetic** LineageFlow mode
   (no 9.788 GB ckpt dependency). The real LineageFlow torch ckpt
   should drop in unchanged because the solver consumes any
   `velocity_field(x, t)` callable — `make_lineageflow_velocity_field`
   already calls the adapter's internal `_velocity_field` method
   (which delegates to `_torch_velocity_field` when the ckpt is
   loaded).

2. **No classifier-free guidance**: the paper applies AB-Cache to
   CFG outputs (`noise_pred = neg + scale * (pos - neg)`,
   `pipeline_flux_our.py:945-960`); we skip the CFG path because
   FlowA's LineageFlow adapter is not CFG-based (continuous flow
   matching, no CFG in the R6 task).

3. **Queue length defaults to 2**: we default to `queue_length=2`
   (2-step Adams-Bashforth) per the paper's primary reported
   setting (`flux_our.py:116`). The 4-step variant
   (`flux_our.py:119`) is wired (`queue_length=5` knob is exposed)
   but not used in the headline smoke test.

4. **Cache-reuse is "blind" to step stability**: AB-Cache's
   decision rule is purely periodic (`i % 6 != 0`), unlike
   Fast-DLLM's confidence-based skip which adapts to the local
   trajectory stability. AB-Cache thus has **worse worst-case
   behavior** on unstable trajectories (cache-reuse on a step
   where the velocity field changes rapidly can cause significant
   drift) but **better average-case behavior** on stable
   trajectories (no per-step confidence overhead). The
   head-to-head on the R6 task will quantify this trade-off.

5. **Apples-to-apples budget**: the AB-Cache solver runs at
   `effective_nfe = warmup_steps + ceil((nfe - warmup_steps) /
   recompute_interval)` effective NFE (not `nfe`). For the
   apples-to-apples "matched effective NFE" comparison, Wave 181
   P2 should also report `effective_nfe` per cell so the P3
   aggregation can pair AB-Cache cells with FlowA / Fast-DLLM
   cells of the same effective budget. Wave 181 P3 may also need
   to sweep `--nfe` in {10, 19, 38, ...} to match AB-Cache's
   effective budget (10, 19, 38 for the default
   warmup/interval).

---

## 8. Audit summary

| metric                              | value                                                          |
|-------------------------------------|----------------------------------------------------------------|
| AB-Cache repo cloned                | yes — `/tmp/AB-Cache/` (aSleepyTree/AB-Cache, depth-1) — note: AntResearch URL 404'd |
| AB-Cache directly usable            | NO — image-diffusion (Flux) only                               |
| AB-Cache-equivalent implemented     | yes — `tools/abcache_solver.py` + `tools/w181_gen_abcache_fastas.py` |
| Solver smoke test                   | PASSED (NFE=50/100, N=2)                                       |
| Solver unit checks                  | PASSED (5 invariants: trajectory shape, NFE=50/100, ws=0 raises, queue_length=5) |
| Output format parity with wave 180  | yes — `>abcache_seed<i>|family=<PF>` headers, AA-sequence bodies |
| Output dir                          | `/tmp/w181/fastas/abcache_lineageflow_nfe<NFE>_seed<SEED>.fasta` |
| Adapter coverage                    | synthetic-mode LineageFlow (real ckpt drop-in compatible)       |
| Solver effective NFE (NFE=50)       | 10 (5x speedup over baseline Euler)                            |
| Solver effective NFE (NFE=100)      | 19 (~5.3x speedup over baseline Euler)                         |
| Cache reuse rate (NFE=50)           | 0.8 (40 of 50 macro-steps)                                     |

**Status:** P1 setup complete. Wave 181 P2 (run AB-Cache-equivalent
on the 540-record R6 task matrix) is ready to launch.
