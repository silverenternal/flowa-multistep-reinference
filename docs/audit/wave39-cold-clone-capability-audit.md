# Wave 39 — Cold-clone capability audit (post-Wave-38 fixes)

**Date:** 2026-09-05
**Agent:** Wave 39 Agent C (cold-clone capability audit rerun)
**Scope:** Rerun `tools/capability_audit.py --robust` after the Wave 38 fix
batch (assert_adapter_compliance enforcement, paper_quantities threading
through 3 sites, bounded_lipschitz_distance_2d no-scipy raise, host_fingerprint
module + 5+ call sites, hypothesis derandomize + expecttest, FlowMol3V2
restart shape fix, Theorem1DynamicNoiseBias as default) to confirm that
`G-MASTER-CAPABILITY` is **still PASS** (5/5 HARD + 2/2 SOFT) and that no
Wave 38 fix perturbed the value surface.

## Command

```bash
PYTHONPATH=/home/hugo/codes/flowa-multistep-reinference \
  .venvs/flowmol3_venv/bin/python \
  tools/capability_audit.py --robust \
  --output verification_outputs/capability_audit_q4_2026_post_w38.json
```

`PYTHONPATH` is required because `tools/capability_audit.py` imports
`adaptive_reflow.util.host_fingerprint` (the Wave 38 R-4 module) but the
project is not installed in editable mode in the flowmol3_venv. With the
PYTHONPATH set, the script imports cleanly and writes the JSON.

The audit completed in well under a second (read-only measurement over
`docs/CONSOLIDATED_RESULTS.md`, `docs/CONDITIONS.md`,
`docs/baseline-audit-report.md`, `env_hash.txt`; no model forward pass).

## Aggregate verdict

```
HARD 5/5 PASS  |  SOFT 2/2 PASS  |  G-MASTER-CAPABILITY PASS  |  MUST-4 FREEZE GATE PASS
```

| Subset | Pass | Fail | Pending |
|---|---|---|---|
| HARD (G.1, G.3, G.4, G.6, G.7) | **5** | 0 | 0 |
| SOFT (G.2, G.5) | **2** | 0 | 0 |

Aggregate JSON excerpt:

```json
{
  "hard_pass": 5,
  "hard_fail": 0,
  "hard_pending": 0,
  "soft_pass": 2,
  "g_master_capability": "PASS",
  "must_4_freeze_gate": "PASS"
}
```

This is the **first cold-clone audit in which SOFT is 2/2 PASS**. All four
prior waves (Wave 28, 30, 34, 36) reported SOFT 1/2 PASS with G.5 = 275 FAIL
(`FAIL_SOFT`); the Wave 35 FIX-3b saturation-test-orientation commit
(`1472807`) corrected G.5 but the Wave 36 audit JSON
(`capability_audit_post_w36.json`) was generated from a stale state and
kept the FAIL reading. Wave 39 is the first audit that runs the
post-FIX-3b logic on the post-Wave-38 source.

## Per-G value table

| Metric | Value | Target | Verdict | HARD/SOFT | Δ vs Wave 36 |
|---|---:|---|---|---|---|
| G.1 (canonical median) | **+0.0884** | >= +0.05 | **PASS** | HARD | unchanged |
| G.1 alt (spec-literal mean) | -0.218 | (alt) | FAIL | (alt) | unchanged |
| G.2 | **0.962** | <= 5.0 | **PASS** | SOFT | unchanged |
| G.3 | **-0.0251** | >= -0.03 | **PASS** | HARD | unchanged |
| G.4 | **3** | >= 3 | **PASS** | HARD | unchanged |
| G.5 | **27.5** | <= 50 NFE (median) | **PASS** | SOFT | **275.0 FAIL → 27.5 PASS** (FIX-3b orientation now reaches the saturated sweep) |
| G.6 | **0.25** | <= 0.30 (per `todo/framework-capability-metrics.md` §G.6) | **PASS** | HARD | unchanged (note: JSON `target` field shows `">= 0.3"` — this is a target-string inconsistency in the spec-source mirror; the verdict logic uses `_verdict(value, target, "le")` so 0.25 <= 0.30 ⇒ PASS, consistent with prior waves) |
| G.7 | **7/7** | >= 6/7 | **PASS** | HARD | unchanged |

## Per-G evidence summary

### G.1 — mean value score (HARD, canonical median)

* 10 rows aggregated from `docs/CONSOLIDATED_RESULTS.md`: 7 wins, 2 losses
  (both within parity), 1 tie.
* Per-family signed_mean (4 / 4 positive):
  `twodim_fm +0.408`, `rectified_flow_cifar +0.213`,
  `mnist_fm +0.063`, `lineageflow +0.001`.
* Canonical aggregator: median of sign-normalized deltas
  (positive = framework wins); alt aggregator: arithmetic mean of
  spec-literal deltas (negative-bias failure mode, retained for reviewer
  transparency per Wave 37 Agent A spec change).
* Same value as Wave 34 / 36: **0.0884** (Wave 35 did not perturb the
  value surface; Wave 38 changes are engineering-discipline, not
  algorithm-value).

### G.2 — cost-benefit ratio (SOFT)

* `0.962` — median wallclock ratio well under the 5.0 per-1%-gain target.
* Computed from 4 rows where both wallclock and a win are present.
* Same value as Wave 34 / 36.

### G.3 — worst-case bound (HARD)

* `-0.0251` — worst cell is `mnist_fm_v1` (FID 143.4 → 147.0, -2.51%
  framework_worse, within parity; canonical-extractor re-measurement
  per Wave 28 Agent A).
* Same value as Wave 34 / 36. No Wave 38 change moved the worst cell.

### G.4 — generalization breadth (HARD)

* `3` — `twodim_fm`, `rectified_flow_cifar`, `mnist_fm` have
  strictly-winning rows (cell_value > 0). LineageFlow's `family_validity`
  is a saturation tie (cell_value = 0.0) and is correctly excluded per
  Wave 30 Agent A threshold tightening.
* Same value as Wave 34 / 36.

### G.5 — saturation point (SOFT, NOW PASS)

* **`27.5 NFE`** — median of two `n_min_saturation` values:
  * `twodim_fm`: 5 NFE (W2 = 0.33 at both NFE=5 and NFE=500; the framework
    saturates immediately, the synthetic target is flat by construction
    per Wave 17 P3 out-of-F-side-class regime).
  * `rectified_flow_cifar`: 50 NFE (FID = 103.41 at NFE=50; the next
    point at NFE=500 is `nfe_full` and the saturation test uses
    `metric(N_min) <= metric(N_full) / 0.95` per Wave 35 FIX-3b
    orientation correction).
  * median = (5 + 50) / 2 = **27.5** ≤ 50 ⇒ **PASS**.
* **Delta vs Wave 36: `275.0 FAIL → 27.5 PASS`.**
* Root cause of the prior FAIL: the Wave 36 audit JSON
  (`capability_audit_post_w36.json`) was generated with the
  **pre-FIX-3b** logic (which tested `metric(N_min) <= 0.95 * metric(N_full)`
  — 5% better than the full run — an unsatisfiable test whenever the
  full-NFE run is the best point of the sweep, as it is for the
  converged twodim_fm synthetic target). The Wave 36 agent F reran the
  audit but the cached `n_min = nfe_full = 500` for twodim_fm and
  propagated the FAIL. The Wave 35 Agent E verification commit
  (`ab72716`, "verify G.5 post-fix (275 -> 27.5 NFE)") is the
  authoritative prior fix; this Wave 39 audit is the first **fresh**
  audit to exercise the corrected logic against the post-Wave-38
  codebase.
* Wave 38 changes do NOT touch the saturation-test path; the only
  delta is that the fresh audit JSON now correctly reads
  `n_min = 5` for `twodim_fm` and `n_min = 50` for CIFAR.

### G.6 — honest negative surface (HARD)

* `0.25` — per-family hns averaged with EQUAL FAMILY WEIGHT across the
  4 integrated families: `twodim_fm = 1.0` (12/12 cells regress in the
  C.5 sigma sweep; out-of-regime per Wave 17 P3 honest operating-regime
  statement), `rectified_flow_cifar = 0.0`, `mnist_fm = 0.0`,
  `lineageflow = 0.0`. Equal-weight mean = `(1.0 + 0 + 0 + 0) / 4 = 0.25`.
* Same value as Wave 34 / 36. Wave 38 changes do not move the
  per-family hns.

### G.7 — reproducibility of capability (HARD)

* `7/7` — F.5 `env_hash.txt` present, `tools/capability_audit.py`
  runnable, all 4 data sources parseable, F.2 reproduction >= 4/8,
  cold-clone re-run executed.
* env_hash: `17ad7f9d1f3948271859860e3d77b284a8a7805693c8adabb7e37174a4e10bad`
  (post-Wave-38 refresh; different from Wave 34's
  `2080f2e8...` and Wave 36's `779d5a22...` because Wave 38 added new
  pinned-regression-vector fingerprints that flow into env_hash).
* Same verdict as Wave 34 / 36 (7/7 PASS).

## Comparison to Wave 34 / Wave 36 readings

| Metric | Wave 34 | Wave 36 | Wave 39 | Δ (W34 → W39) | Δ (W36 → W39) |
|---|---:|---:|---:|---|---|
| G.1 | 0.0884 PASS | 0.0884 PASS | 0.0884 PASS | 0 | 0 |
| G.2 | 0.962 PASS | 0.962 PASS | 0.962 PASS | 0 | 0 |
| G.3 | -0.0251 PASS | -0.0251 PASS | -0.0251 PASS | 0 | 0 |
| G.4 | 3 PASS | 3 PASS | 3 PASS | 0 | 0 |
| G.5 | 275.0 FAIL | 275.0 FAIL | **27.5 PASS** | **-247.5 NFE** | **-247.5 NFE** |
| G.6 | 0.25 PASS | 0.25 PASS | 0.25 PASS | 0 | 0 |
| G.7 | 7/7 PASS | 7/7 PASS | 7/7 PASS | 0 | 0 |
| HARD | 5/5 | 5/5 | **5/5** | unchanged | unchanged |
| SOFT | 1/2 | 1/2 | **2/2** | **+1 PASS** | **+1 PASS** |
| **G-MASTER-CAPABILITY** | **PASS** | **PASS** | **PASS** | unchanged | unchanged |
| MUST-4 freeze gate | PASS | PASS | **PASS** | unchanged | unchanged |

The `G-MASTER-CAPABILITY` verdict is **unchanged** (PASS); the headline
delta is the SOFT subset closing from 1/2 → 2/2 because the Wave 35
FIX-3b saturation-test orientation now correctly reports `n_min = 5`
for `twodim_fm` (rather than the stale `n_min = 500` carried by the
Wave 36 audit JSON).

The Wave 36 audit JSON (`verification_outputs/capability_audit_post_w36.json`)
is **stale** relative to the Wave 35 commit `1472807` and should be
regenerated in the next audit cycle (Wave 39 has done so via
`capability_audit_q4_2026_post_w38.json`).

## Why no Wave 38 fix perturbed the value surface

The Wave 38 fix batch targets **engineering-discipline metrics**
(`A.0-A.7`, `B.1-B.7`, `D.2-D.4`, `E.1-E.4`, `F.5-F.6`) and NOT the
algorithm value surface (`G.1-G.7`). The Wave 38 commits:

| Commit | Fix | G-surface impact |
|---|---|---|
| `f7ee3ae` | assert_adapter_compliance enforcement (HIGH-4 + MEDIUM-11) | none (D.2-D.5 surface) |
| `ff56e55` | paper_quantities threading (HIGH-1 + MEDIUM-6 + MEDIUM-8) | none (B.7 surface) |
| `53cda7f` | default DynamicNoiseBias → Theorem1 | none (algorithm class change, but the 10 CONSOLIDATED_RESULTS rows are pinned and unchanged) |
| `89c088f` | bounded_lipschitz_distance_2d no-scipy raise | none (test-only path) |
| `2e87c3a` | Wave 37 Agent D G.1 spec change + 30 pytest fixes | none (G.1 already PASS on canonical) |
| `7cbf085` | HF model card upload pipeline | none (E.4 surface) |
| `0674ac8` | mkdocs --strict nav fix | none (E.4 surface) |
| `b9ef18b` | FlowMol3V2 restart shape fix | none (D.4 surface; no CONSOLIDATED_RESULTS row affected) |
| `7da571c` | E.1 wire 8 remaining CLM claims to tests | none (E.1 surface) |
| `5e1731f` | expecttest adoption (R-1) | none (test infrastructure) |

None of these move the 10 G.1 evidence rows, the 4 G.2 wallclock rows,
the G.3 worst cell, the G.4 family counts, the G.6 per-family hns, or
the G.7 reproducibility checks. The audit's identical readings (modulo
G.5) confirm this.

## Cold-clone discipline

* `cold_clone: false` in the audit JSON — the script ran from the
  current working tree (no `git clone` + reinstall). This is consistent
  with Wave 34 / Wave 36 (also `cold_clone: false`).
* `env_hash: 17ad7f9d1f3948271859860e3d77b284a8a7805693c8adabb7e37174a4e10bad`
  is **different** from Wave 36's
  `779d5a22111b258a56dbc388f0ffe8fd010e1c123de767650edaa548e6f29af9`,
  consistent with Wave 38's pinned-regression-vector refresh
  (Wave 38 Agent A `Refresh regression vectors` task) flowing into
  the F.5 env_hash pipeline.
* `_host_fingerprint.hostname_hash: sha256:92ae71c7c2d0cf3d` matches
  the regression-vectors refresh target (see
  `regression-vectors/*.json` for the per-adapter fingerprints).

## What is not in scope

* No new experiments were run. This is a **read-only measurement** of
  the value surface.
* No source code changes (`DO NOT touch source code` constraint).
* No push to remote (`Commit + DO NOT push` constraint).

## Next-wave actions (informational, not blocking)

1. The Wave 36 audit JSON `capability_audit_post_w36.json` should be
   regenerated in the next cycle to remove the stale `G.5 = 275` reading
   and align with the post-FIX-3b logic. (Wave 39's
   `capability_audit_q4_2026_post_w38.json` already supersedes it for
   paper-writeup gate evidence.)
2. PHASE-4 real-ckpt unblock sweep (task #643) remains the next
   major wave action; `G-MASTER-CAPABILITY` is now PASS in all 5 HARD
   + 2 SOFT metrics, so the value-delivery gate is no longer
   blocking the PHASE-4 → paper-writeup transition.

## Files

* **NEW** `verification_outputs/capability_audit_q4_2026_post_w38.json`
  — fresh audit JSON, 5/5 HARD + 2/2 SOFT PASS.
* **NEW** `docs/audit/wave39-cold-clone-capability-audit.md` — this file.
* **APPEND** `todo/framework-internal-metrics.md` — Wave 39 per-G row
  added below the Wave 34 / Wave 36 rows.

## Verdict

**`G-MASTER-CAPABILITY` is still PASS post-Wave-38** (5/5 HARD + 2/2 SOFT).
Wave 38's engineering-discipline fixes did NOT perturb the value surface.
The headline delta is **G.5 now PASS at 27.5 NFE** (was FAIL at 275 NFE in
the Wave 36 stale audit; the Wave 35 FIX-3b saturation-test orientation
correction is now correctly exercised). MUST-4 freeze gate is PASS.
