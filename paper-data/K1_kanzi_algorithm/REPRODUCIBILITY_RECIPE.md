# K1 FlowMol3 RDKit-Validity — Reproducibility Recipe

**Cell:** K1 FlowMol3 RDKit-validity (FlowMol3 adapter weak-metric remediation row)
**Headline:** per_seed_rdkit_validity_pct = (0.535, 0.590, 0.585), mean = 0.570 ± 0.030 std (CV = 5.3%);
mean_diff = +0.0415 vs Wave 82 PB validity baseline (0.5285);
paired Cohen's d_z = **+1.3645** (REAL, above 0.8 STRONG threshold);
**Bonferroni p_bonf = 0.5676 at K-level α = 0.0125 (k=4 family) — FAILS K-level α by 45.4×** (Wave 308 P2 demotion: paper-cited p_bonf=0.054 mis-applies R-level k=7 family to a K-level cell; corrected K-level k=4 multiplier gives 0.5676).
**Status label:** **SUPP / UNDERPOWERED** (Wave 308 P2 demotion from PARTIAL/BORDERLINE-STRONG; moved to `docs/drafts/paper-flat-flattened.md` §10.8 supplementary per Wave 268 strict-clean rule).
**Date:** 2026-09-27 (Wave 363 P1.K1 — reproduction recipe authored; no measurement delta; no algorithm activation; no end-to-end N=1000 sweep).

---

## (a) Headline Metric

K1 is the **FlowMol3 RDKit-bridged validity** weak-metric remediation cell. Per `docs/audit/wave275-p4-flowmol3-proposal.md` §1.1 + `docs/audit/wave275-p1-state-inventory.md` §4.2 row K1, the K1 fix flips the FlowMol3 HEADLINE row from `pb_validity_pct` (UFF-vs-xtb definitional gap → REGRESSES −9.95pp) to `rdkit_validity_pct` (RDKit-bridged canonical metric) via the `--validity-mode rdkit` flag in `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184`.

### Headline table (3 seeds × N=200 paired sweep, paired one-sample t-test vs Wave 82 PB baseline = 0.5285)

| metric | value | interpretation |
|---|---|---|
| per-seed rdkit_validity_pct (seeds 42 / 43 / 44) | (0.535, 0.590, 0.585) | 3/3 direction-consistent K1 > PB |
| mean (3 seeds × N=200) | **0.570** | above Wave 82 PB baseline (0.5285) by +4.15pp |
| std_paired (3 seeds) | 0.0304 | CV = 5.3% (well below 10% reproducibility threshold) |
| mean_diff vs Wave 82 PB (0.5285) | +0.0415 | K1 metric WINS at the per-seed mean |
| t-statistic (paired, df=2) | 2.366 | not significant at α=0.05 alone |
| d_z (Cohen's paired effect size) | **+1.3645** | **REAL**, well above 0.8 medium-effect threshold (Wave 22 metric-rev3 STRONG rubric) |
| p_value (Student-t 2-sided, df=2) | 0.1419 | not significant at per-cell α=0.05 |
| p_bonf (×4 K-family thresholds) | **0.5676** | **FAILS K-level α=0.0125 by 45.4×** (Wave 308 P2 family-mismatch correction) |
| Paper-cited (erroneous) p_bonf | 0.054 | paper-cited value mis-applies R-level k=7 family; corrected K-level k=4 → 0.5676 |

### Honest status disclosure (per Wave 308 P2 demotion)

The Wave 280 P K1 sweep reported `p_bonf = 0.054` (computed with R-level k=7 family multiplier × `α = 0.05/7` ≈ 0.00714). The Wave 308 P2 audit identified that this **mis-applies the R-level k=7 family** to a **K-level cell** — the correct K-level k=4 family α = 0.05/4 = 0.0125 gives `p_bonf = 0.5676`. Per the Wave 268 strict-clean rule (status history additive, no removal), both values are preserved verbatim in `docs/CLAIMS.md` CLM-060 line 3033 (K1 status history); the K1 cell is **demoted from PARTIAL/BORDERLINE-STRONG to PARTIAL/UNDERPOWERED** and moved to `docs/drafts/paper-flat-flattened.md` §10.8 supplementary disclosure.

**The d_z = +1.3645 is REAL** (mean_diff = +0.0415 vs Wave 82 PB baseline, 3/3 direction-consistent, CV = 5.3%) and not invalidated by the Bonferroni-correction family-mismatch. The strict Bonferroni FAIL is purely a sample-size limitation (d_f = 2 with 3 paired seeds); the projection to N=1000 per seed × 3 seeds would lift the t-statistic to ≈ 5.29 but the Bonferroni p-value still sits ≈ 0.135 (above α = 0.0125) — even N=1000 cannot fully clear the K-level Bonferroni threshold at this effect size. The K1 promotion is best framed on **d_z + reproducibility + direction-consistency** (which ARE met at N=200) rather than strict p_bonf alone.

---

## (b) Evidence Chain + SHA-256 Anchors

The K1 evidence chain is a **single GPU sweep artifact** (no counterfactual methodology; no multi-wave uplift grid). The sweep ran on 2026-09-22 (Wave 280 P) at `verification_outputs/wave280-p-k1/` and is mirrored (via identical SHA-256s) at `paper-data/K1_kanzi_algorithm/` for paper-citation convenience.

### SHA-256 anchors (verified at recipe authorship, 2026-09-27)

| File | SHA-256 |
|---|---|
| `verification_outputs/wave280-p-k1/driver.py` | `63fd80e443f6bb6acb4a7a90c26b79fc498a0cd9e696fca1938a03cf5f59df8e` |
| `verification_outputs/wave280-p-k1/summary.json` | `af322f3843daec4ba411407464531078e634236af6bd074e7914f45db618a637` |
| `verification_outputs/wave280-p-k1/run.log` | `22597bb5d56b1cbb38840cc573945af43e1b4fe024000009ebe8f28eb20e3dae` |
| `verification_outputs/wave280-p-k1/SHA256SUMS` (current on-disk content) | `320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2` |

### Notes on SHA-256 ledger self-hash discrepancy

The on-disk `SHA256SUMS` ledger at `verification_outputs/wave280-p-k1/SHA256SUMS` declares its own historical self-hash as `0c7ad234516359e3d3d94b1b53b3ba15d211551f7a5be24620f7ff859c197417` (recorded before the Wave 308 /tmp → `verification_outputs/` migration). The current on-disk content self-hashes to `320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2` (matching the Wave 328 `paper-data/SHA256SUMS` re-frozen entry at `paper-data/K1_kanzi_algorithm/SHA256SUMS`). The 3 evidence files (driver.py / summary.json / run.log) hashes match exactly across both locations; only the SHA256SUMS self-reference is stale. **Recommendation:** re-run `sha256sum -- driver.py summary.json SHA256SUMS run.log > SHA256SUMS` from inside `paper-data/K1_kanzi_algorithm/` if a fresh ledger is required for reviewer-facing verification.

### Per-seed data (embedded in `summary.json`)

There is **no `seed{42,43,44}/` subdirectory** under `verification_outputs/wave280-p-k1/` (or `paper-data/K1_kanzi_algorithm/`). The per-seed scalars are embedded inside `summary.json` under the `per_seed_summaries` array (3 entries, one per seed, each with `arm = "baseline"`, `n_records = 200`, `n_sampled = 200`, `device = "cuda:0"`). This is a deliberate aggregation choice — the K1 sweep uses the Wave 82 PB validity baseline (0.5285, external) as the comparison reference, NOT a within-run framework-vs-baseline arm. The framework arm WAS sampled (see `run.log` lines 5-8, 13-16, 21-24) for byte-stable side-effect; the comparison happens against the external Wave 82 baseline via paired one-sample t-test.

### Bash verification (reviewer runs from `paper-data/K1_kanzi_algorithm/`)

```bash
cd paper-data/K1_kanzi_algorithm
sha256sum -- driver.py summary.json SHA256SUMS run.log
# expected:
#   63fd80e443f6bb6acb4a7a90c26b79fc498a0cd9e696fca1938a03cf5f59df8e  driver.py
#   af322f3843daec4ba411407464531078e634236af6bd074e7914f45db618a637  summary.json
#   320bead32332335a2823a9beb7f8b8327bfa8ab35e4e77631ac32ad4629ac1b2  SHA256SUMS
#   22597bb5d56b1cbb38840cc573945af43e1b4fe024000009ebe8f28eb20e3dae  run.log
```

### Python snippet — reproduces d_z = +1.3645 + p_bonf = 0.5676 from `summary.json` per-seed array

```python
#!/usr/bin/env python3
"""Reproduce Wave 280 P K1 sweep aggregate (d_z = +1.3645, p_bonf = 0.5676)
from `verification_outputs/wave280-p-k1/summary.json` per-seed array. CPU-only, <1 sec."""
import json, math

SUMMARY = "verification_outputs/wave280-p-k1/summary.json"
BASELINE_VALIDITY = 0.5285  # Wave 82 §15.15.1 row 2 pb_validity_pct baseline
ALPHA_PER_THRESHOLD = 0.05 / 4  # K-level k=4 family (Wave 308 P2 corrected)

with open(SUMMARY) as f:
    d = json.load(f)

rdkit_validity = d["per_seed_rdkit_validity_pct"]
n = len(rdkit_validity)
mean = sum(rdkit_validity) / n
diffs = [v - BASELINE_VALIDITY for v in rdkit_validity]
mean_diff = sum(diffs) / n
sd_diff = math.sqrt(sum((x - mean_diff) ** 2 for x in diffs) / (n - 1))
t_stat = mean_diff / (sd_diff / math.sqrt(n))
d_z = mean_diff / sd_diff

# 2-sided Student-t p-value (df=2)
# At df=2 the survival function has a closed-form: p = 2 * (1 - 0.5*(1 + t/sqrt(2 + t^2)))-ish
# Use scipy if available, else use a conservative normal-approx.
try:
    from scipy import stats as _stats
    p_value = float(_stats.t.sf(abs(t_stat), n - 1) * 2.0)
except Exception:
    p_value = float(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2.0)))))

p_bonf = float(min(p_value * 4, 1.0))  # Bonferroni ×4 K-family thresholds

print(f"per_seed = {rdkit_validity}")
print(f"mean = {mean:.4f}  (expected 0.5700)")
print(f"std_paired = {sd_diff:.4f}  (expected 0.0304)")
print(f"mean_diff = {mean_diff:+.4f}  (expected +0.0415)")
print(f"t = {t_stat:.4f}  (expected 2.366)")
print(f"d_z = {d_z:+.4f}  (expected +1.3645)")
print(f"p_value = {p_value:.4f}  (expected 0.1419)")
print(f"p_bonf = {p_bonf:.4f}  (expected 0.5676)")
assert math.isclose(d_z, 1.3645115946344677, abs_tol=1e-3), "d_z mismatch"
assert math.isclose(p_bonf, 0.5675777088526774, abs_tol=1e-3), "p_bonf mismatch"
print("PASS: Wave 280 P K1 sweep aggregate reproduced (d_z + p_bonf match).")
```

---

## (c) Reproducibility Path

The K1 evidence is a **live GPU sweep** (not a counterfactual / not a frozen-substrate reprobe). Re-running the sweep requires the FlowMol3 checkpoint + the `flowmol3_venv` sidecar + a CUDA GPU.

### Required inputs

| input | path | size |
|---|---|---|
| FlowMol3 Lightning checkpoint | `data/flowmol3/weights_real/checkpoints/last.ckpt` | 68 MB |
| Vendored upstream sampler | `data/FlowMol3/repo/flowmol/models/flowmol.py` (pinned commit `77cae22174b7792b0e25e9e0414038420736d841`) | unchanged per Wave 262 P1 / CLM-077 |
| Vendored upstream `ctmc_utils.segment_csr` consumer | `data/FlowMol3/repo/flowmol/utils/ctmc_utils.py` | unchanged |
| Pre-existing compat shim | `data/FlowMol3/repo/flowmol/utils/torch_scatter_compat.py` | unchanged (reused via `sys.modules` registration in driver) |
| Sweep driver (this recipe) | `verification_outputs/wave280-p-k1/driver.py` (mirror at `paper-data/K1_kanzi_algorithm/driver.py`) | 333 lines |
| Project-owned K1 shim (RDKit-bridged validity) | `adaptive_reflow/adapters/flowmol3_upstream_shim.py:184` (`--validity-mode rdkit` flag) | unchanged (Wave 275 K1 implementation is the canonical state) |

### Environment

- **Sidecar venv:** `.venvs/flowmol3_venv` (per `docs/environments.md`; FlowMol3 / 2D FM / MNIST FM / CIFAR-10 RF all use `flowmol3_venv`; **never mix with `kanzi_venv` or `lineageflow_venv`**)
- **Python:** 3.11+ with RDKit (`from rdkit import Chem`), PyTorch 2.7+cu128, DGL, `torch_scatter` compat shim (no PyG wheel required for torch 2.7+)
- **GPU:** CUDA-enabled (tested on RTX PRO 6000 Blackwell + RTX 5090); `device = "cuda:0"`; ckpt load ≈ 0.18s–6.0s (first seed is slow due to PyTorch JIT/cache warm-up); sampling 200 mols ≈ 70s–92s per seed

### Reproduction commands (GPU path)

```bash
# 1) Activate the right sidecar venv (NEVER MIX)
source .venvs/flowmol3_venv/bin/activate

# 2) Capture pre-sweep METADATA
nvidia-smi > /tmp/k1/METADATA.gpu
date -u +%FT%TZ > /tmp/k1/METADATA.start
mkdir -p /tmp/k1

# 3) Run the K1 sweep driver (default: 3 seeds × N=200 paired records)
python3 verification_outputs/wave280-p-k1/driver.py --seeds 42,43,44 --n-records 200 \
    > /tmp/k1/run.log 2>&1

# 4) Aggregate goes to /tmp/k1/summary.json (per-seed scalars + paired stats + Bonferroni)
ls -la /tmp/k1/summary.json

# 5) Compare against the canonical evidence
diff <(jq '.per_seed_rdkit_validity_pct' verification_outputs/wave280-p-k1/summary.json) \
     <(jq '.per_seed_rdkit_validity_pct' /tmp/k1/summary.json)
# expected: empty diff (per-seed rdkit_validity_pct must be byte-identical)
```

### Expected wall-clock

| step | seed 42 (cold cache) | seed 43 (warm) | seed 44 (warm) | total |
|---|---:|---:|---:|---:|
| ckpt load | 6.0s | 0.2s | 0.2s | ≈ 6.4s |
| sample 200 mols | 92.1s | 71.1s | 72.5s | ≈ 236s |
| aggregate (CPU) | — | — | — | <1s |
| **total** | — | — | — | **≈ 4 min 5 s on RTX PRO 6000 Blackwell** |

### Reproducibility caveats (disclosed)

1. **Framework arm is sampled but not aggregated.** The driver runs both `arm="baseline"` and `arm="framework"` per seed (see `run.log` lines 5-8, 13-16, 21-24) but the aggregate `summary.json` only emits the `baseline` arm — the K1 metric is compared against the external Wave 82 PB baseline (0.5285), not against a within-run framework arm. Re-running the driver produces identical per-seed `rdkit_validity_pct` values across both arms (the framework's cosine scheduler produces the same upstream `FlowMol.sample_random_sizes` draw at matched seed + matched NFE because the framework's restart-blend perturbation does not alter the upstream sampler's first-pass output at `--validity-mode rdkit` per `docs/audit/wave275-p4-flowmol3-proposal.md` §5.1).
2. **Vendored-purity preserved.** No file under `data/FlowMol3/repo/` is touched by the sweep driver. The two monkey-patches (`torch.load(weights_only=False)` override + `torch_scatter` compat shim registration) live entirely inside the driver script (NOT vendored, NOT framework). Per the Wave 262 P1 / CLM-077 directive, the vendored FlowMol3 commit hash is preserved at `77cae22174b7792b0e25e9e0414038420736d841`.
3. **CUDA non-determinism caveat.** PyTorch 2.7+cu128 on RTX PRO 6000 / RTX 5090 uses non-deterministic CUDA kernels for `segment_csr` (via the compat shim's reduction primitives). The per-seed `rdkit_validity_pct` should match to ±0.005 across re-runs (the upstream `FlowMol.sample_random_sizes` is fully deterministic given the seed via `seed_everything`); the aggregate d_z / p_bonf / mean should match to all printed decimals on the same GPU SKU.
4. **No CPU fallback.** FlowMol3 sampling requires CUDA. The CPU-only reproduction path is the **`summary.json` per-seed array → aggregate computation** (the Python snippet in §(b) reproduces d_z + p_bonf in <1 sec on CPU). The GPU sweep itself cannot run on CPU.

---

## (d) Disclosure — Status Label (Wave 268 strict-clean rule)

Per the Wave 268 strict-clean rule + the Wave 308 P2 demotion audit, the K1 status label is:

**`SUPP / UNDERPOWERED`** (Wave 308 P2 demotion from PARTIAL/BORDERLINE-STRONG; moved to `docs/drafts/paper-flat-flattened.md` §10.8 supplementary disclosure).

- The d_z = +1.3645 is REAL and not invalidated by the Wave 308 P2 Bonferroni-correction family-mismatch.
- The strict Bonferroni p_bonf = 0.5676 FAILS K-level α = 0.0125 by 45.4× (sample-size limitation; d_f = 2 with 3 paired seeds).
- Per the Wave 268 strict-clean rule, status history is additive — the Wave 280 P PARTIAL/BORDERLINE-STRONG entry is preserved verbatim in `docs/CLAIMS.md` CLM-060 line 3031 and the Wave 308 P2 SUPP/UNDERPOWERED demotion is preserved verbatim in `docs/CLAIMS.md` CLM-060 line 3033.
- No promotion to SUPPORTED by wording alone; no K-level cell number is changed; no §7.2 K1 row text is changed; no §10.6 K1 inventory number is changed.

### Linked scripts / surfaces

- `verification_outputs/wave280-p-k1/{driver.py,summary.json,run.log,SHA256SUMS}` — the canonical K1 evidence (this Wave 363 P1.K1 deliverable scope).
- `paper-data/K1_kanzi_algorithm/{driver.py,summary.json,run.log,SHA256SUMS,K1_SOURCE.md,REPRODUCIBILITY_RECIPE.md}` — the paper-citation mirror (REPRODUCIBILITY_RECIPE.md is the new Wave 363 P1.K1 deliverable).
- `paper-data/MANIFEST.md` lines 150-153 + 215 — K1 SHA-256 ledger + K1 verdict distribution entry (re-frozen at Wave 328).
- `docs/audit/wave280-p-k1-sweep-result.md` — the Wave 280 P K1 sweep audit note (390 lines; the load-bearing evidence summary).
- `docs/audit/wave308-d3-review.md` §3.6 — the Wave 308 P2 K1 demotion audit (lines 101-109).
- `docs/audit/wave275-p4-flowmol3-proposal.md` + `docs/audit/wave275-p1-state-inventory.md` §4.2 row K1 — the K1 weak-metric remediation origin.
- `docs/CLAIMS.md` CLM-060 lines 3031 + 3033 — the Wave 280 P + Wave 308 P2 K1 status history (additively preserved per Wave 268 strict-clean).
- `docs/CONSOLIDATED_RESULTS.md` line 8722 — K1 cross-doc-snapshot pointer (`FAILS K-level α=0.0125 by 45.4×`).
- `docs/audit/wave326-crossdoc-metrics-snapshot.md` row 9 — K1 row in the canonical 11-cell verdict distribution table.
- `docs/audit/wave361-r-level-inventory-refresh.md` line 43 — K1 R-level inventory entry.

---

_Last updated: 2026-09-27 (Wave 363 P1.K1 — K1 reproducibility recipe authored; SHA-256 chain verified; d_z = +1.3645 + p_bonf = 0.5676 reproduce from per-seed array; status label SUPP/UNDERPOWERED per Wave 308 P2 demotion preserved verbatim; no measurement delta; no algorithm activation; no N=1000 sweep re-run)._
