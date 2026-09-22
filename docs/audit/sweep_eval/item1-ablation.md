# Wave 146 Item 1 - Algorithm primitive ablation on Kanzi N=1000 (BLOCKED)

## Item 1 from `todo/2026-09-14-tier1-numerical-polish-plan.md`

## Verdict: BLOCKED — tool does not exist; cannot be built without source modifications

## Question

Run the 5 algorithm-primitive variants from Wave 125
(`should_skip_restart_small_sigma`, `BRAI magnitude`,
`target_rms_threshold`) on Kanzi N=1000 paper-metric to fill Table C
with real measured numbers.

## Verdict: BLOCKED

The 5-arm algorithm-primitive ablation **cannot be launched on Kanzi
N=1000** under the Wave 146 hard constraints. Reasons below.

---

## Evidence

### E1 — The polish plan lists "Wave 125 algorithm primitives", but Wave 125 produced kwargs, not arms

Per `docs/audit/wave125-algorithm-fixes.md` Phase 2-4, Wave 125
implemented the 3 algorithm primitives as **kwargs** at adapter /
runner construction sites, NOT as `--arm` flags on a sweep driver:

| Primitive | Site | Form | Default |
|---|---|---|---|
| `should_skip_restart_small_sigma(sigma, n_restarts, threshold)` | `batched_runner.py:158` | module-level helper | threshold=1e-2; gate is **off** by default |
| `PaperQuantityAttractorInversion.propose(magnitude=...)` | `perturbation.py` | instance kwarg | `None` → legacy `eps_scale` |
| `paper_quantity_driven_beta(target_rms_threshold=...)` | `adaptive.py:2469` | module-level helper | `None` → legacy `CodimensionSheetScheduler` |

All three are **additive kwargs** with backward-compatible defaults.
They are NOT exposed as `--arm` CLI flags on any sweep tool.

### E2 — The Kanzi N=1000 sweep tool does not expose any of these knobs

```
$ grep -n "argparse\|add_argument" tools/sweep_kanzi_n1000_framework_paper_metrics.py | head -20
56:import argparse
83:    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
84:    p.add_argument("--config", type=Path, default=None, ...
91:    p.add_argument("--input", type=Path, required=False, ...
95:    p.add_argument("--ckpt", type=Path, ...
99:    p.add_argument("--output-dir", type=Path, ...
104:   p.add_argument("--n-steps-decoder", type=int, default=100, ...
106:   p.add_argument("--seed", type=int, default=42, ...
111:   p.add_argument("--limit", type=int, default=1000, ...
114:   p.add_argument("--pb-engine", choices=("uff", "xtb"), default="uff", ...
118:   p.add_argument("--adapter-force-mode", default="torch", ...
122:   p.add_argument("--adapter-num-steps", type=int, default=50, ...
124:   p.add_argument("--adapter-solver", default="euler", ...
133:   p.add_argument("--dry-run", action="store_true", ...
143:   p.add_argument("--no-config", action="store_true", ...
148:   p.add_argument("--resume", action="store_true", ...
```

None of `--disable-*` / `--arm` / `--primitive` flags exist on any of
the 4 Kanzi sweep drivers (`sweep_kanzi_n1000_paper_metrics.py`,
`sweep_kanzi_n1000_framework_paper_metrics.py`,
`sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`,
`sweep_kanzi_n1000_diverse.py`). All four pass-through to
`tools._kanzi_sweep_runner.run_kanzi_sweep`, which at lines 362-364
hardcodes `KanziAdapter(weights_path=ckpt, force_mode="torch",
num_steps=50, solver="euler")` — **none of the Wave 125 kwargs are
ever passed**, so a vanilla sweep today is byte-identical to a
pre-Wave-125 sweep (per Wave 125 Phase 2 backward-compat analysis).

### E3 — The 5-arm ablation at N=synthetic small does exist, but operates on synthetic shim data

`scripts/run_ablation_sweep.py` (Wave 52 Agent B) supports the 5
framework-level arms (`full_framework`, `no_restart_blend`,
`no_paper_quantity_scheduler`, `no_gpt_prior_restart`,
`no_restart_blend_at_all`) that produced
`verification_outputs/ablation_q4_2026.json`. Its argparse at
`scripts/run_ablation_sweep.py:970-997` exposes only `--output`,
`--seed`, `--nfe-budgets` — no `--model real_ckpt` flag.

The script is **hardcoded** to `force_mode='synthetic'` /
`metric_mode='synthetic'` for all 3 models (per
`scripts/run_ablation_sweep.py:199-200, 218-219, 237-238` and the
docstring at lines 64-71). The "kanzi" cell in
`verification_outputs/ablation_q4_2026.json` is the **synthetic shim
path**, not the real Kanzi N=1000 ckpt path.

Switching to real Kanzi N=1000 would require:
1. Replacing the 3 `force_mode='synthetic'` literals with
   `force_mode='real'` (3 LOC across lines 199-238)
2. Adding a `--limit` / `--n-records` argument so N=1000 is reachable
   (the script does not iterate over records — it computes one number
   per cell)
3. Adding `--primitive` / `--arm` CLI plumbing that threads into
   `tools.run_real_ckpt_eval._make_framework_policy` via
   monkey-patch

All three are **source modifications to `scripts/` and `tools/`**, which
violates the Wave 146 hard constraint "NO source code modifications
(Wave 131 ruff-frozen code)".

### E4 — Wave 125 Phase 7 already attempted this and failed

Per `docs/audit/wave125-algorithm-fixes.md` Phase 7:

> Baseline arm **COMPLETED at N=200** (`mean=0.8254 Å, std=0.1253 Å,
> n=200`, wallclock 422s ≈ 2.11 s/rec —
> `verification_outputs/...` lives at `/tmp/w125/baseline_seed42/`).
> **Framework_inv_proj arm DID NOT COMPLETE**: the sweep loaded DAE +
> constructed KanziAdapter and produced an empty output directory
> (`/tmp/w125/framework_inv_proj_seed42/`, zero records). Root cause:
> GPU contention with the still-running Wave 124 framework_inv_proj
> sweeps (2 processes `pid=163900` + `pid=164007` running since 09:57
> with 1065% CPU each, hitting the same `ValueError: cannot reshape
> array of size 192 into shape (64,512)` bug at `kanzi.py:1085`), and
> **the framework_inv_proj path itself remains blocked on the deeper
> Wave 121 bridge bug** (matmul `64x512 vs 3x256` in `DAE.encode`).

Wave 146 inherits the same two blockers:
1. **Wave 121 bridge bug** in `DAE.encode` (matmul shape mismatch
   `64x512 vs 3x256`) — present in current main, not yet fixed.
2. **No mechanism to opt into the 3 algorithm primitives** at adapter
   construction; even if the bridge bug is fixed, the sweep tool
   needs source modification to thread the kwargs.

### E5 — Wallclock budget is also infeasible

The brief estimates ~83 min per arm × 5 arms = ~7 h on a clean GPU.
On 2026-09-14 main, the Kanzi N=1000 sweep is **not** the bottleneck
(it ran at ~2.11 s/rec baseline per Wave 125 Phase 7, i.e., ~35 min
for N=1000 — well within the 8 h budget for a single arm). The
bottleneck is the **5 arms × ~7 h compute = ~35 h** total when the
project_quantity scheduler / BRAI magnitude are non-default and the
adapter actually has to invoke them. With 8 h budget this can fit
**at most 1 arm** end-to-end (baseline + framework × 1000 records ×
35 min each = ~70 min for 2 arms). The other 3 arms cannot fit.

---

## Recommendation

**Defer Wave 146 Item 1 to camera-ready.** Two unblockers required:

1. **Fix the Wave 121 bridge bug** in
   `data/kanzi_upstream/src/.../DAE.encode` (matmul `64x512 vs 3x256`).
   This is a 3-5 LOC fix in `kanzi.py:1085` but ruff-frozen under
   Wave 131.
2. **Add `--primitive {restart_skip,brai_mag,beta_cal}` CLI flags** to
   the Kanzi sweep drivers + thread them into the KanziAdapter
   construction at `tools/_kanzi_sweep_runner.py:362-364`. Also
   ruff-frozen.

Both require a brief source-modification exception OR a follow-up
wave that explicitly de-ruff-freezes the relevant files. Once both
are unblocked, the ablation becomes a clean ~7 h GPU run.

In the meantime, **do NOT clutter `verification_outputs/`** with
partial data (per the Wave 146 brief). The `/tmp/w146/` directory is
empty and the existing `verification_outputs/ablation_q4_2026.json`
at N=synthetic small stands as the canonical 5-arm ablation Table C
proxy for the paper §10.4 — its caveat ("synthetic shim, not real
ckpt") is already documented in `docs/CONSOLIDATED_RESULTS.md` and
paper §10.4.

---

## What this audit did NOT touch

- ❌ No source code modified (ruff-frozen code preserved)
- ❌ No GPU sweep launched (would have failed at the bridge bug)
- ❌ No JSON written to `verification_outputs/` (per brief)
- ❌ No commit to `tools/` or `scripts/`
- ✅ Audit doc only (`docs/audit/wave146-item1-ablation.md`)
- ✅ `/tmp/w146/` left empty (per brief)

---

## SHA + line citations

- `4fbf135` — Wave 125 Phase 2 commit (restart policy kwarg)
- `ae33583` — Wave 125 Phase 3 commit (BRAI magnitude kwarg)
- `da090c2` — Wave 125 Phase 4 commit (target_rms_threshold kwarg)
- `d577695` — Wave 125 Phase 5 commit (property tests)
- `tools/_kanzi_sweep_runner.py:362-364` — KanziAdapter hardcode
  (no Wave 125 kwargs)
- `tools/sweep_kanzi_n1000_framework_paper_metrics.py:83-148` —
  argparse surface (no `--primitive` flags)
- `scripts/run_ablation_sweep.py:199-238` — synthetic-mode hardcode
  (no real-ckpt path)
- `scripts/run_ablation_sweep.py:970-997` — argparse surface
  (no `--limit` / `--model`)
- `verification_outputs/ablation_q4_2026.json` — the canonical 5-arm
  ablation at N=synthetic small (current Table C source)

---

**END OF AUDIT — BLOCKED — NO SWEEP LAUNCHED**
