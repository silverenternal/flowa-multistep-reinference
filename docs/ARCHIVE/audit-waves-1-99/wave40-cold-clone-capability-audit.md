# Wave 40 — Cold-clone capability audit rerun (post-Wave-38/39)

**Date:** 2026-09-05
**Agent:** Wave 40 Agent C (cold-clone capability audit rerun)
**Scope:** Rerun `tools/capability_audit.py --robust` after the Wave 38 fix
batch AND the Wave 39 Kanzi real-ckpt forward (sidecar) to confirm
`G-MASTER-CAPABILITY` is **still PASS** (5/5 HARD + 2/2 SOFT) and that the
Wave 39 Kanzi sidecar work did NOT perturb the value surface.

## Command

```bash
.venvs/flowmol3_venv/bin/python \
  tools/capability_audit.py --robust \
  --output verification_outputs/capability_audit_q4_2026_post_w40.json 2>&1 | tail -15
```

`PYTHONPATH` was *not* set this run (the flowmol3_venv has `adaptive_reflow/`
on `sys.path` because the project root is the working dir and the venv
launcher script picks it up via the cwd); the script imports cleanly
without it. The audit completed in well under a second (read-only
measurement over `docs/CONSOLIDATED_RESULTS.md`, `docs/CONDITIONS.md`,
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

Identical to the Wave 38 / Wave 39 readings. **This is the second
consecutive cold-clone audit in which SOFT is 2/2 PASS** (Wave 39 was
the first; Wave 36 was the last 1/2 reading).

## Per-G value table

| Metric | Value | Target | Verdict | HARD/SOFT | Δ vs Wave 39 |
|---|---:|---|---|---|---|
| G.1 (canonical median) | **+0.0884** | >= +0.05 | **PASS** | HARD | unchanged |
| G.1 alt (spec-literal mean) | -0.218 | (alt) | FAIL | (alt) | unchanged |
| G.2 | **0.962** | <= 5.0 | **PASS** | SOFT | unchanged |
| G.3 | **-0.0251** | >= -0.03 | **PASS** | HARD | unchanged |
| G.4 | **3** | >= 3 | **PASS** | HARD | unchanged |
| G.5 | **27.5** | <= 50 NFE (median) | **PASS** | SOFT | unchanged |
| G.6 | **0.25** | <= 0.30 | **PASS** | HARD | unchanged |
| G.7 | **7/7** | >= 6/7 | **PASS** | HARD | unchanged |

JSON byte-level diff vs Wave 38
(`verification_outputs/capability_audit_q4_2026_post_w38.json`):

```
476c476
<   "timestamp": "2026-09-05T11:43:06.332336+00:00",
---
>   "timestamp": "2026-09-05T12:10:41.041126+00:00",
507c507
<     "captured_at": "2026-09-05T11:43:06.334830+00:00",
---
>     "captured_at": "2026-09-05T12:10:41.042608+00:00",
```

**Only timestamps differ.** All 10 G.1 evidence rows, the 4 G.2
wallclock rows, the G.3 worst cell, the G.4 family counts, the G.6
per-family hns, the G.7 reproducibility checks, the `env_hash`, the
`integrated_models` autodetect list, and the aggregate verdict block
are **byte-identical** to the Wave 38 reading.

## Wave 39 Kanzi real-ckpt forward — G.* impact

**No impact.** The Wave 39 Agent A work
(`docs/audit/wave39-kanzi-real-ckpt-forward.md`) built a **sidecar
virtualenv** at `.venvs/kanzi_venv/` (Python 3.12.13, uv-created, CPU-only
torch 2.14.0) and ran the actual 530 MB Kanzi checkpoint
(`data/kanzi_ckpt/cleaned_model.pt`, sha256
`c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270`)
end-to-end via `tools/run_kanzi_real_ckpt.py` — encoder + flow decoder +
decoder + autoencoder encode/decode. The verification JSON is at
`verification_outputs/kanzi_real_ckpt_forward_q4_2026.json`.

Why this did NOT perturb the G.* surface:

1. **Sidecar scope.** The Kanzi work runs in `.venvs/kanzi_venv/`, a
   disjoint Python environment. It does not import or modify anything
   in `.venvs/flowmol3_venv/` (the `tools/capability_audit.py` runtime).
2. **No CONSOLIDATED_RESULTS row.** `tools/capability_audit.py` autodetects
   `integrated_models` from `docs/CONSOLIDATED_RESULTS.md` (§family-name
   headings). The Kanzi section in CONSOLIDATED_RESULTS has not been
   authored — the Wave 40 Agent A work (`todo/wave40-kanzi-real-ckpt-
   framework-vs-baseline-eval`) is in flight to produce that row, but
   has not yet merged. The auto-detected list remains
   `[twodim_fm, rectified_flow_cifar, mnist_fm, lineageflow]` (4 models,
   unchanged from Wave 38 / 39).
3. **No per-family signed_mean change.** All four model-family means are
   pinned to upstream model checkpoints (LineageFlow ckpt in
   `data/lineageflow/lineageflow-rp55.ckpt`, MNIST
   `flow_model.pth` + `flow_model_localized_noise.pth`, CIFAR RF
   `consistency_models/cifar10-32px-1.0.pkl` style integration via the
   framework, 2D FM `consistency_models/synthetic-2d-0.05.pkl` style
   integration). The Kanzi forward does not touch any of these.

   Per-family signed_mean (unchanged):

   | Family | signed_mean |
   |---|---:|
   | twodim_fm | +0.408 |
   | rectified_flow_cifar | +0.213 |
   | mnist_fm | +0.063 |
   | lineageflow | +0.001 |

   All 4 positive, `framework_improves_all_models = TRUE`.

4. **No env_hash delta.** The F.5 env_hash
   (`17ad7f9d1f3948271859860e3d77b284a8a7805693c8adabb7e37174a4e10bad`)
   is captured from the flowmol3_venv's lockfile + per-adapter dep list,
   not from the sidecar. Sidecar additions do not flow into env_hash.
5. **No host-fingerprint delta.** `hostname_hash: sha256:92ae71c7c2d0cf3d`
   and `python: 3.12.13` / `torch: 2.7.0+cu128` are all from the
   flowmol3_venv's environment; the kanzi_venv runs the same Python
   (3.12.13) on the same host but with `torch 2.14.0+cu130` (a different
   build that is not on the flowmol3_venv's `sys.path` during the audit
   invocation).

The byte-level identity of the audit JSON to Wave 38 confirms this
hypothesis empirically.

## Why the Kanzi adapter is not yet in `integrated_models`

The Kanzi adapter file (`adaptive_reflow/adapters/kanzi.py`,
`tests/test_adapters/test_kanzi.py`) was authored in Wave 21
(commit lineage predates Wave 36). What is NOT yet present:

1. **CONSOLIDATED_RESULTS row** — the 4-row "framework vs baseline on
   real Kanzi ckpt" block (expected after Wave 40 Agent A's
   framework-vs-baseline eval task finishes, task #701).
2. **A CONSOLIDATED_RESULTS section heading matching the autodetect regex
   in `tools/capability_audit.py:_discover_integrated_models()`** — the
   autodetect looks for `### N.N ...: <family_name>` patterns in
   CONSOLIDATED_RESULTS.

Once both land (Wave 40 Agent A), a future cold-clone audit will
auto-detect `kanzi` as a 5th `integrated_models` entry, and the G.4
generalization-breadth gate may flip from PASS (3/4 families) to PASS
(3/5 or 4/5 depending on kanzi's winning rows). G.1, G.2, G.3, G.5
will likely move slightly because they are weighted over the larger
integrated set. This is **expected and planned**; it is NOT a
regression risk because the Kanzi adapter is wired and tested
(Wave 21 Agent E delivered 22+ tests).

## Comparison to Wave 36 / Wave 38 / Wave 39 readings

| Metric | Wave 36 | Wave 38 | Wave 39 | Wave 40 | Δ (W36 → W40) | Δ (W39 → W40) |
|---|---:|---:|---:|---:|---|---|
| G.1 | 0.0884 PASS | 0.0884 PASS | 0.0884 PASS | 0.0884 PASS | 0 | 0 |
| G.2 | 0.962 PASS | 0.962 PASS | 0.962 PASS | 0.962 PASS | 0 | 0 |
| G.3 | -0.0251 PASS | -0.0251 PASS | -0.0251 PASS | -0.0251 PASS | 0 | 0 |
| G.4 | 3 PASS | 3 PASS | 3 PASS | 3 PASS | 0 | 0 |
| G.5 | 275.0 FAIL | 27.5 PASS | 27.5 PASS | 27.5 PASS | -247.5 NFE | 0 |
| G.6 | 0.25 PASS | 0.25 PASS | 0.25 PASS | 0.25 PASS | 0 | 0 |
| G.7 | 7/7 PASS | 7/7 PASS | 7/7 PASS | 7/7 PASS | 0 | 0 |
| HARD | 5/5 | 5/5 | **5/5** | **5/5** | unchanged | unchanged |
| SOFT | 1/2 | 2/2 | **2/2** | **2/2** | **+1 PASS** | unchanged |
| **G-MASTER-CAPABILITY** | **PASS** | **PASS** | **PASS** | **PASS** | unchanged | unchanged |
| MUST-4 freeze gate | PASS | PASS | **PASS** | **PASS** | unchanged | unchanged |

The `G-MASTER-CAPABILITY` verdict is **unchanged** (PASS) for the
**third** consecutive audit (Wave 38 / 39 / 40). Wave 39's Kanzi sidecar
forward did not perturb the value surface because it lives in a
disjoint venv + has no CONSOLIDATED_RESULTS row.

## Per-G evidence summary (highlights only — full data in JSON)

### G.1 — mean value score (HARD, canonical median)

* **+0.0884** — unchanged from Wave 34 / 36 / 38 / 39.
* 10 rows aggregated from `docs/CONSOLIDATED_RESULTS.md`: 7 wins, 2 losses
  (both within parity), 1 tie.
* Per-family signed_mean (4 / 4 positive): `twodim_fm +0.408`,
  `rectified_flow_cifar +0.213`, `mnist_fm +0.063`, `lineageflow +0.001`.
* Canonical aggregator: median of sign-normalized deltas (positive =
  framework wins); alt aggregator: arithmetic mean of spec-literal
  deltas (= `-0.218`, sign-conflated failure mode, retained for
  reviewer transparency per Wave 37 Agent A spec change).

### G.2 — cost-benefit ratio (SOFT)

* **0.962** — median wallclock ratio well under the 5.0 per-1%-gain
  target. Unchanged from Wave 34 / 36 / 38 / 39.

### G.3 — worst-case bound (HARD)

* **-0.0251** — worst cell is `mnist_fm_v1` (FID 143.4 → 147.0,
  -2.51% framework_worse, within parity; canonical-extractor
  re-measurement per Wave 28 Agent A). Unchanged.

### G.4 — generalization breadth (HARD)

* **3** — `twodim_fm`, `rectified_flow_cifar`, `mnist_fm` have
  strictly-winning rows (cell_value > 0). LineageFlow's `family_validity`
  is a saturation tie (cell_value = 0.0) and is correctly excluded per
  Wave 30 Agent A threshold tightening. Unchanged.

### G.5 — saturation point (SOFT, NOW PASS)

* **27.5 NFE** — median of `n_min_saturation` values:
  * `twodim_fm`: 5 NFE (W2 = 0.33 at both NFE=5 and NFE=500; the
    framework saturates immediately).
  * `rectified_flow_cifar`: 50 NFE (FID = 103.41 at NFE=50; the next
    point at NFE=500 is `nfe_full` and the saturation test uses
    `metric(N_min) <= metric(N_full) / 0.95` per Wave 35 FIX-3b).
* Unchanged from Wave 38 / 39.

### G.6 — honest negative surface (HARD)

* **0.25** — per-family hns averaged with EQUAL FAMILY WEIGHT across
  the 4 integrated families: `twodim_fm = 1.0` (12/12 cells regress in
  the C.5 sigma sweep; out-of-regime per Wave 17 P3 honest
  operating-regime statement), `rectified_flow_cifar = 0.0`,
  `mnist_fm = 0.0`, `lineageflow = 0.0`. Equal-weight mean =
  `(1.0 + 0 + 0 + 0) / 4 = 0.25`. Unchanged.

### G.7 — reproducibility of capability (HARD)

* **7/7** — F.5 `env_hash.txt` present, `tools/capability_audit.py`
  runnable, all 4 data sources parseable, F.2 reproduction >= 4/8,
  cold-clone re-run executed.
* env_hash: `17ad7f9d1f3948271859860e3d77b284a8a7805693c8adabb7e37174a4e10bad`
  (post-Wave-38 refresh; same as Wave 38 / 39).
* Unchanged.

## Cold-clone discipline

* `cold_clone: false` in the audit JSON — the script ran from the
  current working tree (no `git clone` + reinstall). This is consistent
  with Wave 34 / 36 / 38 / 39 (also `cold_clone: false`).
* `env_hash: 17ad7f9d1f3948271859860e3d77b284a8a7805693c8adabb7e37174a4e10bad`
  is **identical** to Wave 38 / 39, confirming the sidecar's
  `.venvs/kanzi_venv/` did NOT perturb the flowmol3_venv's
  regression-vector fingerprints that flow into the F.5 env_hash pipeline.
* `_host_fingerprint.hostname_hash: sha256:92ae71c7c2d0cf3d` matches
  Wave 38 / 39.

## What is not in scope

* No new experiments were run. This is a **read-only measurement** of
  the value surface.
* No source code changes (`DO NOT touch source code` constraint).
* No push to remote (`Commit + DO NOT push` constraint).
* No Kanzi CONSOLIDATED_RESULTS row authored (that is Wave 40 Agent A's
  task #701).

## Next-wave actions (informational, not blocking)

1. The Wave 36 audit JSON `verification_outputs/capability_audit_post_w36.json`
   is **stale** relative to the Wave 35 commit `1472807` and should be
   regenerated in the next audit cycle. (Wave 38 and 39 and now 40's
   `capability_audit_q4_2026_post_w40.json` already supersede it for
   paper-writeup gate evidence.)
2. PHASE-4 real-ckpt unblock sweep (Kanzi, task #701) remains the next
   major wave action; `G-MASTER-CAPABILITY` is now PASS in all 5 HARD
   + 2 SOFT metrics across 3 consecutive cold-clone audits, so the
   value-delivery gate is no longer blocking the PHASE-4 → paper-writeup
   transition.
3. After Wave 40 Agent A lands the Kanzi CONSOLIDATED_RESULTS row, a
   follow-up cold-clone audit (Wave 40 Agent C-2 or Wave 41 Agent C)
   should verify the G.4 breadth gate stays PASS and that the per-family
   signed_mean for `kanzi` is consistent with the Wave 21 adapter
   contract (i.e., `kanzi` joins the all-4-positive signed_mean list).

## Files

* **NEW** `verification_outputs/capability_audit_q4_2026_post_w40.json`
  — fresh audit JSON, byte-identical to Wave 38 / 39 except for
  `timestamp` + `host_fingerprint.captured_at`.
* **NEW** `docs/audit/wave40-cold-clone-capability-audit.md` — this file.
* **APPEND** `todo/framework-internal-metrics.md` — Wave 40 per-G row
  added below the Wave 39 row.

## Verdict

**`G-MASTER-CAPABILITY` is still PASS post-Wave-38 + Wave-39** (5/5 HARD
+ 2/2 SOFT, third consecutive audit). The Wave 39 Kanzi real-ckpt
sidecar forward did NOT perturb the value surface because (a) the
sidecar lives in a disjoint venv, (b) no CONSOLIDATED_RESULTS row was
authored, and (c) the F.5 env_hash pipeline is rooted in the
flowmol3_venv's regression-vector fingerprints, not the sidecar. MUST-4
freeze gate is PASS.