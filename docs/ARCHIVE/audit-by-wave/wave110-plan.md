# Wave 110 — Fix Bug 1 + Bug 2 in Kanzi N=1000 framework arms

## Context

Wave 109.A retry (`commit 36fd031`) surfaced two latent bugs in the Kanzi
N=1000 framework arms, both surfaced by threading `--seed` (Wave 108.A,
commit f609b2b):

| Arm | Path | Error |
|---|---|---|
| `framework_synthetic` | `tools/sweep_kanzi_n1000_framework_paper_metrics.py` | 1000/1000 records `bridge_failed:RuntimeError` |
| `framework_inv_proj` | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` | First record crashes in `_velocity_field`: `mat1 and mat2 shapes cannot be multiplied (64x512 and 3x256)` |

Both bugs pre-date Wave 108.A — Wave 108.A only wired `torch.manual_seed`
through, it did not write any new code paths. The bugs were simply never
exercised end-to-end at N=1000 because every prior sweep either (a) was
N=10 hand-picked, or (b) only ran the baseline arm at N=1000.

## Root-cause analysis (READ-ONLY audit, this is the plan phase)

### Bridge contract (tools/kanzi_latent_to_coord.py)

The bridge was rewritten by Wave 95.P3.C to **unconditionally** apply the
trained `_apply_project_out_inv` Linear(512 → 4) projection before FSQ
snap. Lines 218-227:

```python
x_flat = x_t.reshape(B_dim * L_dim, -1).float()  # (B*L, 512)
x_4d = _apply_project_out_inv(x_flat)  # (B*L, 4)
```

This means **the bridge only accepts `x_t` of shape `(B, L, 512)`** —
the post-`project_out` (n_channels_decoder=512) space. Anything else
raises RuntimeError on `_apply_project_out_inv`.

### Bug 1: `framework_synthetic` mode (root cause + 3 fix options)

`_synthesize_x_final_synthetic(record_idx, seed, codebook_dim=4)` at
`tools/_kanzi_sweep_runner.py:96-108` emits `(L=64, codebook_dim=4)` —
**NOT `(64, 512)`**. The 4-d shape was correct under the Wave 91 bridge
contract (which expected pre-`project_out` 4-d codes), but the Wave 95
bridge rewrite now requires 512-d post-`project_out` codes. The
`σ=1e-3` magnitude is a red herring — the crash is the matmul shape
mismatch, NOT an FSQ collapse.

#### Three fix options

| Option | Description | LOC | Risk | Notes |
|---|---|---|---|---|
| **A. Synthesize 512-d (RECOMMENDED)** | Change `codebook_dim=4` → `codebook_dim=512`. The σ=1e-3 noise floor stays — it's well below KANZI_LATENT_CLAMP=6.0 and produces diverse post-`project_out` codes that the trained Linear(512→4) can map to non-trivial 4-d codes. Wave 96.A diagnostic showed scale-up eliminates the collapse; this is the Wave 96.B-equivalent fix for the project_out⁻¹ path. | 1-2 | low | Matches Wave 96.B precedent (`_synthesize_x_final_real` returns (64, 512)). |
| B. Add `projector` flag to bridge | Bridge branches: `projector="project_out_inv"` → apply Linear(512→4) (current); `projector="fsq_codes"` → skip Linear, use raw 4-d directly. Then `framework_synthetic` passes `projector="fsq_codes"`. | 10-15 | medium | Restores Wave 91 semantics but adds a code path. Larger blast radius (bridge is shared). |
| C. Drop `framework_synthetic` mode | Delete the mode entirely, only keep `framework_inv_proj`. Update CLI + audit doc to note Wave 91-92 synthetic mode retired. | 5 (delete) | low | Loses the cheap sanity-check arm. Wave 91-92 historical data unaffected (still in verification_outputs). |

**Recommendation: Option A** — 1-2 LOC, matches Wave 96.B precedent, preserves both arms.

### Bug 2: `framework_inv_proj` mode (root cause + 3 fix options)

`_synthesize_x_final_real(adapter, record_idx, seed)` at
`tools/_kanzi_sweep_runner.py:111-140` calls `adapter.solve_ode(bundle,
cond, seed=int(seed)+int(record_idx))`. The adapter's velocity field in
default (`synthetic`) mode returns shape `(KANZI_STATE_SHAPE = (64, 64))`
— NOT `(64, 512)`. The `(64, 512)` shape assumption in `_synthesize_x_final_real`'s
docstring (line 117) and the Wave 96.B narrative (lines 204-211) assume
**real torch mode** (`KANZI_ABSTRACT_STATE_SHAPE` → `KANZI_REAL_STATE_SHAPE`).
The bridge then reshapes to `(64, 512)` and crashes in
`_velocity_field`/`_apply_project_out_inv`.

#### Three fix options

| Option | Description | LOC | Risk | Notes |
|---|---|---|---|---|
| **A. Construct adapter in real mode (RECOMMENDED)** | Force `kanzi_adapter = KanziAdapter(..., force_mode="real")` (or the existing `--real` / `force_mode_real` CLI flag from Wave 41.B). Real mode wires the actual `_torch_velocity_field` which emits `(L, n_channels_decoder=512)`. | 3-5 (1 CLI flag + 1 if/else) | low | Mirrors Wave 41.B `--force-mode real` pattern. Verified via `--help` already exposes this. |
| B. Map (64, 64) → (64, 512) via tiled projection | Add a fixed Linear(64→512) (random-init or zero-pad) inside `_synthesize_x_final_real`. Bridge receives (64, 512) and proceeds. | 5-10 (Linear + tests) | medium | Introduces a meaningless transform; framework arm becomes meaningless. |
| C. Drop `framework_inv_proj` mode | Same as Bug 1 Option C. Delete the mode entirely. | 5 (delete) | low | Loses the Wave 95.P3.C testbed. |

**Recommendation: Option A** — 3-5 LOC, no new math, uses the existing
Wave 41.B `--force-mode real` infrastructure.

## Acceptance criteria (per commit)

### Wave 110.A — Fix Bug 1 (framework_synthetic collapse)

Commit title: `Wave 110.A: Fix framework_synthetic 4-d→512-d shape mismatch in Kanzi sweep runner`

| # | Criterion | Verification |
|---|---|---|
| 1 | `_synthesize_x_final_synthetic` emits shape `(64, 512)` instead of `(64, 4)` | `python -c "from tools._kanzi_sweep_runner import _synthesize_x_final_synthetic; import numpy as np; x = _synthesize_x_final_synthetic(0, seed=42); assert x.shape == (64, 512); print(x.shape, np.linalg.norm(x))"` |
| 2 | Sweep completes N=1000 records without `bridge_failed:RuntimeError` | `pytest tests/ -k "test_kanzi_latent_to_coord or test_sweep_kanzi" -v` all PASS |
| 3 | Per-record index diversity ≥ Wave 96.D threshold (>500 unique codewords across N=1000) | Run N=100 sweep with `--limit 100 --seed 42`, count unique idx values |
| 4 | `pytest tests/ -k d4 -q` → 72/72 PASS | Bash output |
| 5 | `mkdocs build --strict` → EXIT=0 | Bash output |

### Wave 110.B — Fix Bug 2 (framework_inv_proj shape mismatch)

Commit title: `Wave 110.B: Fix framework_inv_proj by forcing KanziAdapter real mode (n_channels_decoder=512)`

| # | Criterion | Verification |
|---|---|---|
| 1 | `run_kanzi_sweep(mode="framework_inv_proj", ...)` constructs adapter with `force_mode="real"` | Grep + Read tools/_kanzi_sweep_runner.py:340-360 |
| 2 | Sweep completes N=1000 records without `_velocity_field` shape crash | Run `--limit 10 --seed 42` smoke test |
| 3 | Per-record index diversity ≥ Bug 1 acceptance threshold | Same as #3 above |
| 4 | `pytest tests/ -k d4 -q` → 72/72 PASS | Bash output |
| 5 | `mkdocs build --strict` → EXIT=0 | Bash output |

### Wave 110.C — Re-run Kanzi N=1000 sweep (both arms)

Commit title: `Wave 110.C: Re-run Kanzi N=1000 framework arms with Bug 1+2 fixes`

| # | Criterion | Verification |
|---|---|---|
| 1 | Baseline arm N=1000 JSON written, all 6 paper metrics present | Read `/tmp/w110c_kanzi_baseline_seed42/kanzi_n1000_paper_metrics.json` |
| 2 | framework_synthetic arm N=1000 JSON written, per-metric Δ computed | Read `/tmp/w110c_kanzi_framework_synthetic_seed42/kanzi_n1000_paper_metrics.json` |
| 3 | framework_inv_proj arm N=1000 JSON written, per-metric Δ computed | Read `/tmp/w110c_kanzi_framework_inv_proj_seed42/kanzi_n1000_paper_metrics.json` |
| 4 | Determinism: re-run baseline with `--seed 7`, per-record sigma=0 across all 6 metrics | Diff two baseline JSONs, report max sigma |
| 5 | Per-metric Δ + Bonferroni-corrected p-values computed | Python script output |
| 6 | `pytest tests/ -k d4 -q` → 72/72 PASS | Bash output |

### Wave 110.D — Final synthesis + Wave 109.A closure

Commit title: `Wave 110.D: Author wave110-final-synthesis.md + close Wave 109.A follow-up`

| # | Criterion | Verification |
|---|---|---|
| 1 | `docs/audit/wave110-final-synthesis.md` authored with per-arm table + σ_A + p-values | File exists |
| 2 | `docs/audit/wave109-a-kanzi-n1000.md` updated additively to note Bug 1+2 now fixed | Grep |
| 3 | `docs/audit/wave96a-diagnose-collapse.md` cross-referenced | Grep |
| 4 | `pytest tests/ -k d4 -q` → 72/72 PASS | Bash output |
| 5 | `mkdocs build --strict` → EXIT=0 | Bash output |

## Hard rules (apply to every agent)

- **NO push** (user-gated).
- **NO** read of paper-draft.md / cover_letter.md / supplementary.md
  into agent context (cite SHAs only).
- **NO** modify Wave 109.D paper-package updates (already committed at
  `7254cc3`).
- **NO** modify adapter code beyond Bug 1+2 surgical fixes (Wave 95+
  already touched the bridge).
- **DO** add regression tests that prove the shape contract.
- **DO** append to existing audit docs additively (no destructive edits).

## Resource budget

- W110.A: ~30 min wallclock + <10 LOC
- W110.B: ~30 min wallclock + <10 LOC
- W110.C: ~80 min wallclock (waits for baseline sweep loop, ETA from prior wave ~70 min; both framework arms ~10 min each after fix)
- W110.D: ~20 min wallclock
- Total: ~3 hours wallclock + audit + commits


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
