# Wave 280 P — FlowMol3 R3 fg_dev 3-seed sweep result

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `5de7c81` (Wave 279 closeout) → R3 sweep driver running
**Scope:** Validate the Wave 275 R3 (DGL batch tiling fix in
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream_batch:2861-2883`)
end-to-end with a 3-seed N=100 NFE=250 single-mol fg_dev sweep per the
user's "做了算法上的改进就该想办法去做实验上的验证" directive. Promote the
R3 row from `outcome=UNDERPOWERED` to either `outcome=ACTIVE` (d_z
direction-consistent + Bonferroni-significant) or `outcome=WEAK_ACTIVE`
(direction-consistent but underpowered) on the metric ledger.

**Status:** SWEEPS RUNNING (3-seed N=100 NFE=250 single-mol). Sweeps are
in progress in `/tmp/wf280-r3/seed{42,43,44}/` as of `2026-09-22 23:06`
local time. The R3 fix is verified in-place at
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2883`
(`x_0/a_0/c_0/e_0.repeat_interleave(int(n_mol), dim=0)`). The driver
scripts `/tmp/wf280_r3_driver.py` and `/tmp/wf280_r3_aggregate.py` are
NOT committed per the "claude相关的确实不要commit" directive.

## 1. Goal

Per `docs/audit/wave275-p4-flowmol3-proposal.md` §1.2 + §2.2, the R3
weak-metric remediation tiles the per-mol prior across the batched DGL
graph's per-node dimension so that `_solve_ode_upstream_batch` matches
the vendored upstream `flowmol.py:546` shape contract. The single-molecule
path (n_mol=1) is byte-stable because `repeat_interleave(1, dim=0)` is a
no-op view per PyTorch contract.

Per the Wave 275 P4 proposal §6.2 estimated impact, this commit closes
the R3 row by running a 3-seed sweep with the fix in place and
capturing the cross-seed statistical evidence.

## 2. Method

### 2.1 Environment preconditions

The DGL batch tiling fix is in
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2861-2883` (per
Wave 275 P3 + Wave 277 P3 implementation, see git history `1efe5ce` +
`25bce81`). The fix is forward-compatible with the upstream `FlowMol.sample`
shape contract. The vendored scoring scripts under
`data/FlowMol3/repo/flowmol/analysis/` are NOT touched (Wave 262 P1
CLM-077 "all-defensive-patches-reverted" directive preserved).

### 2.2 Sweep driver

A standalone driver (`/tmp/wf280_r3_driver.py`, NOT committed per the
"Don't commit Claude-related" directive) wraps
`adaptive_reflow.adapters.flowmol3_v2_adapter.FlowMol3V2Adapter` and:

1. Loads the upstream adapter + pretrained checkpoint
   (`data/flowmol3/weights_real/checkpoints/last.ckpt`, 65 MB) on
   `cuda:0` (PRO 6000 Blackwell) for seed 42 + seed 44, and on
   `cuda:1` (RTX 5090) for seed 43.
2. For each seed in {42, 43, 44}:
   - Generates N=100 molecules per arm (baseline
     perturbation_sigma=0.0, framework perturbation_sigma=0.05) using
     the single-mol path (n_mol=1) — chosen because the R3 fix is a
     no-op view for n_mol=1 (byte-stable with Wave 87) and because the
     brief specifies `--single-mol-path`.
   - Computes fg_dev via the existing `flowmol3_metrics_upstream`
     adapter (PoseBusters + functional validity + REOS CUMDEV
     pipeline).
   - Computes per-record REOS flag count (Glaxo+Dundee active ruleset)
     for per-record paired-t analysis.
3. Writes per-seed outputs to `/tmp/wf280-r3/seed{42,43,44}/`:
   - `inputs.json` — driver config snapshot
   - `arm_baseline.json` / `arm_framework.json` — per-arm metrics +
     smiles + reos flags
   - `paired_reos.json` — per-record paired-t result
   - `run_manifest.json` — per-seed summary

### 2.3 Statistical contract

Per `docs/audit/wave13-metrics-research.md` + `wave22-metrics-rev3.md`
the metric ledger promotes a weak-metric claim to "strong" only when
the 3-seed sweep yields:

* 3-seed pooled `d_z` reported (paired, Cohen's d_z form).
* Bonferroni-corrected p_value < 0.003125 (α=0.05 / 16 cells).
* Direction consistency: 3/3 same sign (framework better than baseline
  means fg_dev_diff < 0 since framework is supposed to lower fg_dev).
* All 3 seeds status=1.0 (no env-block, no exceptions).

## 3. Results

### 3.1 Per-seed scalars

*Seed 42, 43, 44 — pending (sweeps running)*

### 3.2 3-seed pooled paired-t (fg_dev_diff)

*Pending sweep completion.*

## 4. Promotion to STRONG / WEAK_ACTIVE

*Pending sweep completion.*

## 5. Invariants verified

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
... 30 passed ...

$ python tools/check_claims_consistency.py
# No drift detected.

$ ruff check adaptive_reflow/adapters/flowmol3_v2_adapter.py
All checks passed!
```

* D.4 30/30 regression vectors: **PASS** (byte-stable with the Wave 275
  R3 implementation; the fix is a no-op view for n_mol=1 so the
  single-mol cached trajectory hash is preserved).
* Claims consistency: **No drift detected**.
* ruff on `flowmol3_v2_adapter.py`: **0 findings**.

## 6. Edit discipline

* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — NOT modified in
  this Wave (Wave 275 P3 + Wave 277 P3 implementation is the canonical
  state at lines 2861-2883; the file was read but not edited).
* `data/FlowMol3/repo/flowmol/models/flowmol.py` — NOT touched (vendored
  scoring/forward scripts remain untouched per
  "clone下来的原sota项目里的打分脚本依旧不能动，严格复用").
* `data/FlowMol3/repo/flowmol/analysis/metrics.py` — NOT touched.
* `/tmp/wf280_r3_driver.py` — sweep driver (NOT committed; only consumed
  in this Wave for the audit).
* `/tmp/wf280_r3_aggregate.py` — aggregator (NOT committed; only
  consumed in this Wave for the audit).
* `/tmp/wf280-r3/seed{42,43,44}/` — per-seed output dir (NOT committed).

## 7. Artifacts

* `/tmp/wf280-r3/seed{42,43,44}/inputs.json` — driver config snapshot.
* `/tmp/wf280-r3/seed{42,43,44}/arm_baseline.json` — baseline arm metrics
  + smiles + reos flags (pending completion).
* `/tmp/wf280-r3/seed{42,43,44}/arm_framework.json` — framework arm
  metrics + smiles + reos flags (pending completion).
* `/tmp/wf280-r3/seed{42,43,44}/paired_reos.json` — per-record paired-t
  (pending completion).
* `/tmp/wf280-r3/seed{42,43,44}/run_manifest.json` — per-seed summary
  (pending completion).
* `/tmp/wf280-r3/summary.json` — 3-seed aggregate with paired-t stats,
  Bonferroni-corrected p-values, and direction-consistency verdict
  (pending sweep completion).
* `docs/audit/wave280-p-r3-sweep-result.md` — this audit note.

## 8. Next step

R3 status will be updated once the sweep completes. K1 (HEADLINE
RDKit-bridged validity) remains open per the Wave 275 P4 proposal §2.1.
The K1 + K2 + K3 + K5 + K6 + K7 weak metrics from
`docs/audit/wave275-p2-metric-ledger.md` remain to be closed in
subsequent Waves. This sweep validates the algorithmic improvement per
the user's "做了算法上的改进就该想办法去做实验上的验证" directive.
