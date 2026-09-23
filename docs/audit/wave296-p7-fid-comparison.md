# Wave 296 P7 — CIFAR-10 FID comparison: cosine baseline vs cosine + full JMAA theory

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs (anchors):**
- `docs/audit/wave296-p5-activation-log.md` (P5 — 16/16 sites activation log)
- `docs/audit/wave296-p6-backward-compat.md` (P6 — byte-identical R-cell backward-compat)
- `docs/audit/wave291-p5-3seed-results.md` (P5 — headliner 3-seed verification)
- `docs/audit/wave290-p3-batched-harness.md` (P3 — batched framework_cifar harness, ~30× speedup)

**Source driver:** `/tmp/wf296_p7_fid_compare.py` (NOT in repo; sweep-time file)
**Reuses:** `tools.batched_framework_cifar.run_batched_records`
**Adapter factory:** `tools.run_sota_cifar_experiment._make_adapter`
**FID path:** subprocess to `tools.compute_cifar_fid.main` (torchvision IMAGENET1K_V1
extractor; flowmol3_venv has torch + pytorch-fid; framework venv has neither).

---

## 0. TL;DR

| Metric | Result |
|---|---|
| **fidBaseline** (Cell A: cosine, flag=False) | **415.28917866845916** |
| **fidFullTheory** (Cell B: cosine + JMAA, flag=True, profile=real_g) | **415.28917866845916** |
| **deltaPct** | **+0.0000%** |
| **samples byte-identical?** | **YES** (max_abs_delta = 0.0) |
| **Sites consumed (Cell A)** | **0** (Engine flag=False → cache=None → no sites active) |
| **Sites consumed (Cell B)** | **16** (Engine flag=True → cache active → 8 A-class + 8 B-class sites) |
| **Verdict** | **`no_effect`** (delta < 0.5% threshold) |
| D.4 30/30 byte-stability | **PRESERVED** (30/30 PASS) |
| Paper-quantities + JMAA integration tests | **99/99 PASS** |
| ruff diagnostics | **0** (no framework files touched) |
| Vendored touched | **NO** |

---

## 1. Method

Two cells, both at `N=200, num_steps=2, num_rounds=2, seed=42, solver=euler,
device=cpu` against the standard CIFAR-10 reference (`data/cifar10_test_ref.npz`):

| Cell | Scheduler | Engine | `paper_quantities_cache` |
|---|---|---|---|
| **A — Cosine baseline** | `CosineAnnealScheduler(cycle_length=2, n_min=0.0)` (no profile) | `Engine()` (default — `enable_full_jmaa_theory=False`) | `None` |
| **B — Cosine + full JMAA** | `CosineAnnealScheduler(cycle_length=2, n_min=0.0, profile_residual_fn=real_g_for_cifar)` | `Engine(enable_full_jmaa_theory=True, paper_quantities_cache=PaperQuantitiesCache(profile_residual_fn=real_g_for_cifar))` | active (16 sites registered) |

Both cells use the **batched harness** (`tools/batched_framework_cifar.run_batched_records`)
which bypasses `Engine.run_round` and calls `adapter.batched_inference` directly
on each round. The `schedule_n_caps` are sampled from the active scheduler:

```python
n_caps = [sample(r).n_cap for r in range(num_rounds)]  # both cells → [1.0, 0.0]
```

Per Wave 296 P6 §2.1 and Wave 291 P5 §1, the **cosine schedule's `n_cap` is
independent of the `profile_residual_fn`** — the profile contributes the
audit-code label `cosine_paper_quantity_wired:A_g=...` (computed once at
construction; cached as `scheduler.sheet_A`) but does NOT alter the schedule
trajectory. Both cells therefore schedule the same `[1.0, 0.0]` n_cap
sequence, which with `num_steps=2` translates to step counts `[2, 1]`
(`max(1, round(n_cap * num_steps))`).

The site-activation log is captured directly from each Engine via
`engine.consume_a_class_sites()` and `engine.consume_b_class_sites()`
(per Wave 296 P3 + P4 contract). Cell A's Engine has cache=None so both
hooks are no-ops (return 0). Cell B's Engine has an active cache so both
hooks consume all 16 sites (8 A-class + 8 B-class).

---

## 2. Results

### 2.1 Per-cell summary

| Cell | n_caps | audit_codes (round 0) | samples byte-equal? | FID | Sites |
|---|---|---|---|---:|---:|
| A (flag=False) | `[1.0, 0.0]` | `("cosine_baseline",)` | — | 415.2892 | 0 |
| B (flag=True, profile=real_g) | `[1.0, 0.0]` | `("cosine_baseline", "cosine_paper_quantity_wired:A_g=0.854946")` | **YES** (Δ=0.0) | 415.2892 | 16 |

### 2.2 FID comparison

| Metric | Value |
|---|---:|
| FID_A (cosine baseline, flag=False) | 415.28917866845916 |
| FID_B (cosine + JMAA, flag=True, profile=real_g) | 415.28917866845916 |
| FID_B − FID_A | 0.0 |
| (FID_B − FID_A) / FID_A × 100 | **+0.0000%** |

### 2.3 Site activation log

**Cell A (flag=False)** — `cache = None`, so `consume_a_class_sites()` and
`consume_b_class_sites()` are no-ops (return 0). Per Wave 296 P6 §2.1 R5b
finding: **0 sites active**, no audit trail.

**Cell B (flag=True, profile=real_g_for_cifar)** — `cache.is_active = True`,
so the engine activates all 16 sites from the Wave 292 P1 inventory:

| # | Site name | Class | File:line (per Wave 296 P5) |
|---:|---|---|---|
| 1 | `solver_hint` | A | `algorithm/dynamics.py:132-145` (`_floor_dt`) |
| 2 | `dt_floor` | A | `algorithm/dynamics.py:132-145` (`_floor_dt`) |
| 3 | `alpha_floor` | A | `algorithm/dynamics.py:742-748` (`BFNDynamics.step`) |
| 4 | `noise_bias` | A | `algorithm/perturbation/dynamic_noise_bias.py:172` |
| 5 | `merge_floor` | A | `algorithm/merge/merge_operator.py:402-437` |
| 6 | `policy_C` | A | `algorithm/policy_driver.py:505` |
| 7 | `profile` | A | `adapters/profile_residual.py:189-202` |
| 8 | `fid` | A | `eval/fid_theorem_aligned.py:498` |
| 9 | `mfpqa` | B | `algorithm/integrator.py:530` |
| 10 | `evidence` | B | `algorithm/scheduler/evidence_driven.py:248` |
| 11 | `lipschitz` | B | `eval/lipschitz_diagnostic.py:461` |
| 12 | `evaluator` | B | `eval/posterior_selection_evaluator.py:1-9` |
| 13 | `checker` | B | `theory/checkers.py:176` |
| 14 | `sheet_cell` | B | `eval/posterior_selection_evaluator.py:279-303` |
| 15 | `regime` | B | `algorithm/scheduler/regime_selector.py:786` |
| 16 | `derivation` | B | `algorithm/_derivation.py:771` |

`consume_a_class_sites()` returned **8** (all A-class sites freshly
activated), `consume_b_class_sites()` returned **8** (all B-class sites
freshly activated), total **16** (matches the Wave 296 P5 16/16 invariant).

---

## 3. Verdict

**`no_effect`** (FID delta = 0.0000%, samples byte-identical, max_abs_delta = 0.0).

The "integration is wired but has small effect" framing of the task spec
applies here, with the magnitude being **below the 0.5% threshold** —
specifically **zero** at this configuration. Per Wave 296 P6 §2.1 R5b and
Wave 291 P5 §5, the cosine baseline with `cycle_length=2, n_min=0.0` is
byte-stable under the `enable_full_jmaa_theory` flag flip, and the
`profile_residual_fn` argument to `CosineAnnealScheduler` does NOT alter
the schedule trajectory — only the audit-code label
(`cosine_paper_quantity_wired:A_g=0.854946`).

The JMAA theory is **fully wired through the Engine** (16/16 sites
activated, `PaperQuantitiesCache.is_active=True`, snapshots stored,
`engine._paper_quantities_*_snapshot` non-None, `engine._paper_quantities_derivation_e_rho=1e-4`)
but the per-site runtime effect is zero for adapters that don't consult
the cache snapshots — and the CIFAR rectified-flow adapter is exactly
such an adapter (it integrates the UNet velocity field directly without
consulting `paper_quantities.solver_hint/dt_floor/alpha_floor/...`).

This is the **expected behaviour** per Wave 296 P6's backward-compat
invariant: the `enable_full_jmaa_theory` flag is a **wiring-on /
wiring-off switch** that preserves D.4 byte-stability when off and
activates the cache when on. The CIFAR-10 adapter is the canonical
"non-consulting" adapter — the JMAA theory DOES NOT reach the integration
loop. To prove the theory reaches the integration loop, one would need
an adapter that consults the cache snapshots (e.g. an `AdaptivePolicyDriver`
or `MultiFidelityPaperQuantityStep` consumer) — which the CIFAR-10
adapter does not.

**Significance interpretation:** the JMAA integration is wired (16/16
sites), the per-site scheduler profile is computed (`A_g=0.854946`),
but the adapter's velocity field does not consult any of it. The
delta is 0% **for this adapter / scheduler family combination**. On a
scheduler family that DOES consult the profile (e.g.
`CodimensionSheetScheduler` with `profile_residual_fn=real_g` and a
non-trivial `eps_implicit`), the profile lever is significant
(Wave 291 P5 §5: `codim_real_g` mean Δ% vs `codim_none` = +10.721%,
t=20.872, p=2.288e-03 at the 3-seed level) — but the cosine baseline
does not exercise that lever.

---

## 4. Invariants

| Invariant | Status |
|---|---|
| D.4 30/30 PASS | **PASS** (`pytest tests/test_d4_regression_vectors.py -q` → 30 passed) |
| Paper-quantities + JMAA integration tests | **PASS** (`pytest tests/test_paper_quantities_cache.py tests/test_full_jmaa_integration.py -q` → 99 passed) |
| Claims no drift | **PASS** (no CLAIMS.md edits; this doc does not modify any claim) |
| ruff 0 on touched files | **PASS** (no framework files modified; `/tmp/wf296_p7_fid_compare.py` is sweep-time, not committed) |
| mkdocs 0 warnings | **PASS** (`docs/audit/` is `not_in_nav` per `mkdocs.yml`) |
| Vendored NOT touched | **PASS** (no edits under `vendored/`, `data/`, or any third-party tree) |
| Framework source NOT touched | **PASS** (`adaptive_reflow/` is byte-untouched; only `/tmp/wf296_p7_fid_compare.py` added) |
| Working tree clean | **PASS** (`git status` → "nothing to commit, working tree clean") |

---

## 5. Artifacts

| Artifact | Purpose | Location |
|---|---|---|
| Sweep driver | runs Cell A + Cell B + FID computation + byte-stability check | `/tmp/wf296_p7_fid_compare.py` (NOT in repo) |
| Output dir | Cell A/B samples, summary.json | `/tmp/wf296-p7-fid-compare/` |
| `summary.json` | machine-readable comparison output | `/tmp/wf296-p7-fid-compare/summary.json` |
| Audit doc | this file | `docs/audit/wave296-p7-fid-comparison.md` |

### 5.1 summary.json excerpt

```json
{
  "fid_delta": 0.0,
  "delta_pct": 0.0,
  "verdict": "no_effect",
  "byte_stability": {
    "samples_byte_identical": true,
    "max_abs_delta": 0.0,
    "n_caps_match": true
  },
  "cell_A": {
    "engine_flag": false,
    "n_caps": [1.0, 0.0],
    "fid": 415.28917866845916,
    "total_sites_consumed": 0
  },
  "cell_B": {
    "engine_flag": true,
    "n_caps": [1.0, 0.0],
    "audit_codes": [["cosine_baseline", "cosine_paper_quantity_wired:A_g=0.854946"], ...],
    "fid": 415.28917866845916,
    "total_sites_consumed": 16
  }
}
```

---

## 6. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave296-p7-fid-comparison.md` (this file)
- **prior docs cited:** wave296-p5, wave296-p6, wave291-p5, wave290-p3
- **code references:** `tools.batched_framework_cifar.run_batched_records`; `tools.compute_cifar_fid.main`; `/tmp/wf296_p7_fid_compare.py`
- **FID path:** subprocess to `/home/hugo/codes/flowa-multistep-reinference/.venvs/flowmol3_venv/bin/python` invoking `tools/compute_cifar_fid.py` (extractor family `inceptionv3_torchvision_IMAGENET1K_V1`)
- **extractor family:** `inceptionv3_torchvision_IMAGENET1K_V1` (not byte-comparable to `inceptionv3_tfport` per Wave 1 P0-1 caveat)
- **seeds:** 42
- **cells completed:** 2 / 2
- **FID delta:** +0.0000% (byte-identical)
- **verdict:** `no_effect`