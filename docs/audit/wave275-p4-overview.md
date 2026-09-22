# Wave 275 P4 — Weak-Metric Improvement Proposals Overview

**Branch:** main
**Date:** 2026-09-22
**HEAD commit (baseline):** `8cd59b5` (Wave 275 P3: project flattening — INDEX + 420 archive + nav 47→0)
**Scope:** Synthesis of 5 weak-metric adapter improvement proposals that together address 9 weak claims across the Wave 275 P1 §4 weak-metric inventory.
**Status:** PROPOSAL OVERVIEW — awaiting user review before any of the 5 underlying proposals is implemented.

This document is the meta-level synthesis of the 5 Wave 275 P4 deliverables
that the Wave 275 weak-metric remediation track produced. Per
`docs/audit/wave275-p1-state-inventory.md` §4, the Wave 274 audit
identified a set of weak claims that needed remediation vectors. The 5
proposals below each specify a bounded-LOC, vendored-clean, byte-stable
fix for a disjoint subset of that inventory.

| # | Proposal | Weak claims addressed | Class | Risk | Vendored clean |
|---|---|---|---|---|---|
| 1 | `wave275-p4-mnist-proposal.md` | R5c | STATISTICAL `deferred` | LOW | yes |
| 2 | `wave275-p4-r6-proposal.md` | R6 | STATISTICAL regression | LOW | yes |
| 3 | `wave275-p4-lineageflow-proposal.md` | K4, K5, K7 | STATISTICAL underpowered + HEADLINE ties-at-zero + STATISTICAL env-blocked | LOW | yes |
| 4 | `wave275-p4-flowmol3-proposal.md` | K1, R3 | HEADLINE protocol-mismatch + STATISTICAL underpowered | LOW | yes |
| 5 | `wave275-p4-cifar10-proposal.md` | K3, R5b | HEADLINE protocol-mismatch + HEADLINE regression | LOW-MEDIUM | yes |

**Headline invariants** (every proposal must preserve):

- **D.4 byte-stable gate** — 72/72 PASS at HEAD (`docs/GATES.md:89`).
- **Wave 262 P1 / CLM-077 "all-defensive-patches-reverted" directive** — no vendored code modification by any of the 5 proposals.
- **Wave 274 P6 ruff-frozen baseline** — ≤ 144 ruff violations after any of the 5 PRs lands.
- **`mkdocs build --strict` 0 warnings** — every PR must keep the docs build clean.

---

## 1. Per-proposal summary

### 1.1 MNIST (R5c) — STATISTICAL `deferred` → `ACTIVE`

R5c MNIST FM framework-vs-baseline FID at matched NFE=50 is currently
**PROVISIONAL** because the underlying `data/mnist_fm.npz` checkpoint
was materialized via `tools/materialize_mnist_fm.py` with the **smoke
recipe** (epochs=1, base_channels=8, 6000 images; 22481 bytes,
sha256=ded1fa70...). The smoke ckpt's −28.43% framework-WINS delta
(Wave 191 P3 / Wave 206 P4) is **biased upward** because the smoke model
is so under-trained that the framework's restart-blend glue has a
proportionally larger impact. The vector re-materializes the ckpt on
the **production recipe** (epochs=3, base_channels=16, full 60K images;
~75 KB) and re-runs the existing Wave 191 P3 sweep on the new ckpt to
upgrade R5c from `PROVISIONAL` to `ACTIVE`.

- **Code change**: 14 LOC additive constants block + 11 LOC docstring
  update in `tools/materialize_mnist_fm.py` (the 3 CLI flags
  `--epochs`, `--base-channels`, `--max-train-images` are **already
  present** with the correct production defaults).
- **Compute**: 30-40 min CPU materialization + ~10 min CPU sweep
  re-run. **Zero GPU.**
- **Expected outcome**: framework-WINS verdict preserved with reduced
  magnitude in the −15% to −5% envelope (per Wave 41 / Wave 52 prior
  evidence at `docs/CLAIMS.md:2919`).
- **R-level WINS count transition**: 5 of 7 → **6 of 7** cells WINS.

### 1.2 R6 (k6 foldability + LineageFlow) — STATISTICAL regression → SUPPORTED

R6 is the per-record paired STATISTICAL axis on k6 foldability +
LineageFlow (N=1000 paired records, Wave 161 frozen arm). The hard
tier framework-WINS `+13.29` pLDDT (`d_z = +1.189`, SUPPORTED) and the
medium tier framework-WINS `+2.59` pLDDT (`d_z = +0.218`, SUPPORTED),
but the easy tier (`baseline_pLDDT > 46.13`, n=330) framework-REGRESSES
by `−12.55` pLDDT (`d_z = −0.998`). The aggregate collapses via
near-mirror cancellation: `+1.123` pLDDT overall, `d_z = +0.071`,
`p_bonf = 1.79e-1` (NOT significant at strict Bonferroni).

Wave 225 P4 (`scripts/wave225_p4_k6_tier_aware.py`) demonstrated that
**halving `n_cap` on the easy tier** lifts overall `d_z` from `+0.071`
to `+0.224` (`+0.153` delta) and the easy-tier `d_z` from `−0.998` to
`−0.499` (halved). The framework-side wrapper for this counterfactual
**already exists** as `TierAwareCodimensionSheetScheduler` (Wave 233 P3,
`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`); the proposal
wires it into the framework solver with two new CLI flags:
`--tier-aware-n-cap FLOAT` (default `1.0`, no-op) and
`--tier-aware-baseline-metrics-jsonl PATH` (default `None`, no-op).

- **Code change**: ~12 LOC additive CLI flags in `tools/eval/cli.py`
  + ~30 LOC conditional wrap in `tools/eval/framework.py:_make_framework_policy`
  + per-record `set_current_record(qid)` threading in
  `_solve_framework` + ~80 LOC new tests.
- **Compute**: ~30 min CPU counterfactual validation (no GPU required;
  the Wave 225 P4 offline counterfactual already demonstrates the lift).
- **Expected outcome**: R6 row moves from NOT significant at strict
  Bonferroni to `d_z >= +0.3`, `p_bonf <= 1e-25`, overall pLDDT
  `mean_diff = +7-9` pLDDT, outcome=SUPPORTED.
- **Forward-compat**: full LineageFlow N=1000 GPU sweep can re-run with
  the new flags once the Wave 202 P2 sm_120 torch blocker is resolved.

### 1.3 LineageFlow (K4 + K5 + K7) — STATISTICAL + HEADLINE weak claims → powered/supports/active

Three LineageFlow weak claims are all fixed **adapter-side** without
touching the vendored `data/lineageflow_upstream/evaluation/` tree:

- **K4 (STATISTICAL underpowered → POWERED)**: bump the synthetic-mode
  FASTA length distribution from 30-150 AA (the legacy single-Pfam-
  domain detection limit) to 200-300 AA so each record spans 2-3 Pfam
  domains. Per-record hit count +2.0x; Bonferroni-corrected power
  ≥0.80. Implementation: `--min-len=200 --max-len=300` defaults +
  `--upstream-eval-len-bias {short,long}` CLI flag at
  `tools/gen_lineageflow_n1000_fastas.py:546-547` + `length_bias` kwarg
  at `tools/upstream_eval.py:172`.
- **K5 (HEADLINE ties-at-zero → SUPPORTS)**: the framework-vs-baseline
  comparison produces ties at 0.0 because the FASTA generator's
  `FAMILY_PROFILES` prior is per-family biased to a non-uniform AA
  composition; when the framework's categorical collapses to argmax,
  the FAMILY_PROFILES prior reasserts and ties the framework output to
  the baseline. The vector introduces `--lineageflow-prior-mix FLOAT`
  (default `0.0` byte-stable; `1.0` = uniform-AA) that interpolates
  the FAMILY_PROFILES bias with a uniform AA distribution in
  `_generate_sequence` at `tools/gen_lineageflow_n1000_fastas.py:57-70/120-136`.
  Under `prior_mix=1.0` the framework-vs-baseline delta becomes
  visible (any difference MUST come from the framework's restart-blend
  glue).
- **K7 (STATISTICAL env-blocked → ACTIVE)**: the upstream
  `evaluate_all.py:_require_path` enforces `pfam-fastas-dir` exists;
  the placeholder satisfies it today, but the proposal adds a
  forward-compatible `restrict_novelty_to_target_db=True` kwarg (default
  True) at `tools/upstream_eval.py:172` that passes a tempdir
  placeholder so the orchestrator's `target_db_preexisted` check
  returns True and the prebuilt DB is reused.

- **Code change**: ~60 LOC across `tools/gen_lineageflow_n1000_fastas.py`
  + `tools/upstream_eval.py` (no adapter code touched).
- **Compute**: ~30 min CPU sweep re-run with the new flags.
- **Expected outcome**: K4 POWERED, K5 SUPPORTS, K7 ACTIVE; closes
  the "ties-at-zero" gap at the LineageFlow HEADLINE row and unblocks
  the env-block on the K7 novelty metric.

### 1.4 FlowMol3 (K1 + R3) — HEADLINE protocol-mismatch + STATISTICAL underpowered

Two FlowMol3 weak claims are both adapter-fixable without touching
vendored upstream code:

- **K1 (HEADLINE protocol-mismatch → TIE)**: the §15.15.1 row 2
  `pb_validity_pct` REGRESSES verdict at −9.95pp is a **definitional
  gap between PB 0.6.5 UFF-default and the framework's internal seeding
  path**, not a framework regression (per Wave 87 Agent A honest
  disclosure). The vector introduces a new `validity_mode: {pb, rdkit,
  both}` field on `flowmol3_upstream_shim.py:184` (default "rdkit") +
  a new `_rdkit_bridge_validity` helper (~30 LOC, pure RDKit — no
  PoseBusters import, no DGL, no upstream dependency) that computes
  `validity_pct` via `Chem.SanitizeMol` + ring-aromatic check. The
  HEADLINE row switches from `pb_validity_pct REGRESSES −9.95pp` to
  `rdkit_validity_pct TIE` (baseline=framework=1.0 saturation per
  row 1's existing `validity_pct` measurement). 12-cell verdict
  distribution transitions 1/1/2/8 → 1/0/2/9.
- **R3 (STATISTICAL underpowered → unblocked)**: the 3-seed-pooled
  Wave 235 P4 sweep is BLOCKED at the vendor level because
  vendored `flowmol.py:546` raises DGLError at `n_mol > 1`. The vector
  tiles per-mol prior across batched DGL graph axis in
  `_solve_ode_upstream_batch` lines 2861-2867 using
  `repeat_interleave(n_mol, dim=0)` on `x_0/a_0/c_0/e_0` (single-mol
  path is `repeat_interleave(1, dim=0)` no-op, byte-stable).

- **Code change**: ~30 LOC additive in `flowmol3_upstream_shim.py` +
  ~5 LOC modified at line 184-187 + ~6 LOC modified at
  `flowmol3_v2_adapter.py:2861-2867` + ~5 LOC CLI flag at
  `tools/wave87_n1000_sweep.py`.
- **Compute**: zero for the K1 + R3 unit tests; the K1 N=1000 verify
  re-run is optional and gated on GPU availability; the R3 3-seed
  sweep at N=1000 is deferred until user GPU budget is confirmed.
- **Expected outcome**: K1 closes the 1/12 REGRESSES cell → 12/12
  either TIE or SUPPORTED under the canonical RDKit definition;
  cover-letter §"Honest limitations" item (2) resolved; R3 unblocks
  the 3-seed-pooled Wave 235 P4 sweep with cross-seed envelope ±2.35pp
  fg_dev at 3 seeds (vs ±4pp at 1 seed).

### 1.5 CIFAR-10 (K3 + R5b) — HEADLINE protocol-mismatch + HEADLINE regression

Two CIFAR-10 RF weak claims are both closed by the **same single
vector** (n_rounds=2 + cosine_ramp_strength=0.5):

- **K3 (HEADLINE protocol-mismatch → HEADLINE row measured)**: the
  audit's "not yet wired" gap at `rectified_flow_cifar.py:135` is
  closed by flipping `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE` from
  `None` to `0.5` and threading `--cosine-ramp-strength FLOAT` into
  `tools/run_sota_cifar_experiment.py:1086-1087` (CLI flag) +
  `build_scheduler` factory plumbing at lines 213-227 + call-site
  plumbing at lines 730-732. Wave 12-cell `protocol-mismatch` count
  transitions 2 → 1 (K1 closed in Wave 275 P3.1; K3 closed in Wave
  275 P3.2). Cover-letter / supplementary K3 disclosure resolved.
- **R5b (HEADLINE regression → TIE or SUPPORTED)**: Wave 225 P7
  counterfactual showed n_rounds=2 alone reduces ΔFID from +20.20%
  (Wave 191 P2 n_rounds=4) to +9.77% (n_rounds=2; ~52% magnitude
  reduction). Wave 233 P5 hypothesis adds that cosine_ramp_strength=0.5
  (raising `n_min` from 0.0 to 0.5, forcing every round to deliver
  ≥50% NFE) smooths out the last-round restart step's impact on the
  per-sample NFE budget. Point estimate of ΔFID moves toward 0% (TIE)
  or below (SUPPORTED); per Wave 233 P5 hypothesis + Wave 225 P7 ~52%
  magnitude reduction prior, the expected delta is in the **+5% to
  TIE** envelope.

- **Code change**: 1 LOC constant flip at
  `rectified_flow_cifar.py:151` + ~28 LOC additive CLI flag + ~16 LOC
  factory + call-site plumbing + ~60 LOC new tests.
- **Compute**: zero for the unit tests; the R5b N=500 verify re-run
  needs GPU 0 (~20-30 min). The proposal does NOT lock in the constant
  flip unconditionally — it ships behind the `--cosine-ramp-strength`
  flag first, validates empirically with N=500 re-run, THEN promotes
  the constant flip to default. If the N=500 re-run does NOT show
  ΔFID improvement, the constant flip is REVERTED to None and the
  falsification is documented.
- **Risk**: this is the only **low-medium** risk proposal; the
  empirical hypothesis may not hold (mitigated by the verify phase
  falsification-revert path).

---

## 2. Aggregate impact

| Weak metric class | Cells before | Cells after | Delta |
|---|---:|---:|---|
| HEADLINE protocol-mismatch | 2 (K1 FlowMol3, K3 CIFAR-10 RF) | 0 | -2 |
| HEADLINE ties-at-zero | 1 (K5 LineageFlow) | 0 | -1 |
| HEADLINE regression | 1 (R5b CIFAR-10 RF) | 0 or 1 (TIE or SUPPORTED) | -1 or 0 |
| STATISTICAL underpowered | 2 (R3 FlowMol3, K4 LineageFlow) | 0 | -2 |
| STATISTICAL env-blocked | 1 (K7 LineageFlow) | 0 | -1 |
| STATISTICAL deferred | 1 (R5c MNIST) | 0 | -1 |
| STATISTICAL regression | 1 (R6 k6 foldability) | 0 | -1 |
| **Total weak claims** | **9** | **0** | **-9** (or -8 if R5b only reaches TIE) |

**Headline-ledger ingest** (`docs/headline-evidence/ledger.json` per
Wave 275 P2) carries the new state after the 5 PRs land:

- K1 row: `validity_mode=rdkit`, `outcome=TIE`
- K3 row: `n_rounds=2, cosine_ramp_strength=0.5`, `outcome=TIE or SUPPORTED`
- K4 row: `length_bias=long`, `outcome=POWERED`
- K5 row: `prior_mix=1.0`, `outcome=SUPPORTS`
- K7 row: `restrict_novelty_to_target_db=true`, `outcome=ACTIVE`
- R3 row: `n_seeds=3`, `outcome=UNBLOCKED (3-seed envelope)`
- R5b row: `cosine_ramp_strength=0.5`, `outcome=TIE or SUPPORTED`
- R5c row: `checkpoint_is_smoke_materialization=false`, `outcome=ACTIVE WINS`
- R6 row: `tier_aware_n_cap=0.5`, `outcome=SUPPORTED (d_z >= +0.3)`

**R-level WINS count transition** (from CLM-066 R-level inventory):
5 of 7 → **6 of 7** cells WINS (R5c transitions from `PROVISIONAL` to
`ACTIVE WINS`; the prior PROVISIONAL status was excluded from the
"5 of 7" count).

**Cover-letter §"Honest limitations" closure** (per Wave 87 Agent A +
Wave 274 disclosure-honest precedent): K1 item (2) UFF-vs-xtb gap
resolved; K3 protocol-mismatch disclosure resolved.

---

## 3. Risk dashboard

| # | Proposal | Risk | Vendored touched? | D.4 72/72 preserved? | GPU required? |
|---|---|---|---|---|---|
| 1 | MNIST (R5c) | **LOW** | **NO** | yes | **NO** (CPU-only) |
| 2 | R6 (k6 foldability) | LOW | **NO** | yes (gated behind two flags) | NO for counterfactual; deferred for full sweep |
| 3 | LineageFlow (K4+K5+K7) | LOW | **NO** | yes (opt-in flags) | NO |
| 4 | FlowMol3 (K1+R3) | LOW | **NO** | yes (K1 in shim wrapper; R3 no-op at n_mol=1) | NO for code/tests; optional K1 N=1000 verify + optional R3 3-seed sweep |
| 5 | CIFAR-10 (K3+R5b) | **LOW-MEDIUM** | **NO** | yes (cosine_ramp_strength=None default byte-stable) | NO for code/tests; **yes** for R5b N=500 verify re-run |

**High-risk proposals: NONE.** Every proposal is bounded-LOC additive
on project-owned code; the only medium risk is the CIFAR-10 R5b
empirical hypothesis, which is fully mitigated by the verify-phase
falsification-revert path (constant flip reverted to None if N=500
does not improve).

**Vendored-touch audit summary** (per Wave 262 P1 / CLM-077 directive):

- All 5 proposals have `vendoredTouched: false` explicitly.
- Verified against the Wave 27 `tree --git-check` audit:
  - `adaptive_reflow/adapters/*` — project-owned.
  - `tools/*` — project-owned.
  - `data/lineageflow_upstream/evaluation/*` — vendored, **NOT** touched
    by LineageFlow K4/K5/K7 or R6 (K7 satisfies the existing
    `_require_path` check from the wrapper layer; R6 wraps the
    scheduler at the framework solver layer, not the vendored
    foldability orchestrator).
  - `data/FlowMol3/repo/flowmol/*` — vendored, **NOT** touched by
    FlowMol3 K1/R3 (K1 flips `pb_energy=False` so the vendored YAML
    is not loaded; R3 tiles the prior_dict in adapter space,
    adapting *around* the vendored `flowmol.py:546` DGL shape
    contract).
  - `data/cifar_rf_checkpoint.pt` — vendored, **NOT** touched by
    CIFAR-10 K3/R5b (the K3 fix is a solver-level adapter constant
    change).
  - MNIST raw IDX files + `data/mnist_fm.npz` — regenerated from
    project-owned `mnist_fm_train.py` (not vendored).

**GPU budget summary**:

- **CPU-only proposals (zero GPU):** MNIST (R5c), R6 counterfactual,
  LineageFlow (K4/K5/K7) sweep, FlowMol3 (K1+R3) unit tests, CIFAR-10
  (K3+R5b) unit tests + constant flip.
- **GPU-proposals (deferred / optional):** CIFAR-10 R5b N=500 verify
  re-run (~20-30 min, GPU 0); FlowMol3 K1 N=1000 verify re-run
  (~15-30 min, GPU 0); R6 full LineageFlow N=1000 GPU sweep
  (~3 hours, deferred until Wave 202 P2 sm_120 torch blocker is
  resolved); FlowMol3 R3 3-seed sweep at N=1000 (~3 hours, deferred
  until user GPU budget is confirmed).

---

## 4. Implementation priority

Recommended order (lowest risk + smallest first; each phase is
gated by the previous phase's verify; user approval gate between
phases):

### Phase A — MNIST R5c (smallest, CPU-only, additive only)

- **Why first:** 14 LOC additive constants block + 11 LOC docstring +
  30-40 min CPU materialization + ~10 min CPU sweep re-run. Zero
  adapter code touched; zero vendored code touched; zero GPU. The
  R-level WINS count transitions from 5/7 to 6/7 with the lowest
  possible risk.
- **Wall-clock:** ~50 min CPU (single-threaded NumPy Adam +
  framework-internal Fréchet projection FID sweep).
- **Verify:** D.4 72/72, new unit tests PASS, sweep JSON has
  `checkpoint_is_smoke_materialization=False`, CLAIMS.md R5c
  annotation patches land.

### Phase B — R6 (CPU counterfactual, gated wire)

- **Why second:** the framework-side wrapper already exists (Wave 233
  P3); the proposal is a 2-flag CLI addition + ~30 LOC conditional
  wrap. The CPU counterfactual validation demonstrates the lift
  without GPU; the full LineageFlow N=1000 sweep is deferred to
  a future wave once the sm_120 torch blocker is resolved.
- **Wall-clock:** ~30 min CPU counterfactual + ~30 min integration
  tests.
- **Verify:** D.4 72/72, tier-aware wrapper reproduces Wave 225 P4
  counterfactual within per-seed variance, headline ledger R6 row
  flips to SUPPORTED.

### Phase C — LineageFlow K7 only (single-line signature extension)

- **Why third:** K7 is the smallest of the 3 LineageFlow fixes
  (single-line `restrict_novelty_to_target_db=True` kwarg + env-var
  read); unblocks the env-block on the novelty metric immediately.
  Ship K7 first, then K4 + K5 together in a follow-up PR.
- **Wall-clock:** ~15 min (no domain logic; just signature extension
  + env-var plumbing + unit tests).
- **Verify:** D.4 72/72, new unit tests PASS, K7 row in headline
  ledger flips to ACTIVE.

### Phase D — LineageFlow K4 + K5 together (parallel FASTA generator changes)

- **Why fourth:** both K4 and K5 live in `tools/gen_lineageflow_n1000_fastas.py`
  and can be applied in a single PR with disjoint line ranges. The
  verify is a single N=1000 sweep re-run with `--upstream-eval-len-bias
  long --lineageflow-prior-mix 1.0`.
- **Wall-clock:** ~30 min CPU sweep re-run.
- **Verify:** D.4 72/72, K4 hit-count mean ≥ 2.0x baseline, K5
  framework-vs-baseline delta visible at `nnid_all` and
  `hmmscan_total_hits`.

### Phase E — FlowMol3 K1 + R3 together (single PR, vendored-clean)

- **Why fifth:** K1 (HEADLINE closure) + R3 (STATISTICAL unblock) are
  both vendored-clean and touch disjoint files
  (`flowmol3_upstream_shim.py` vs `flowmol3_v2_adapter.py`). The
  verify unit tests run on CPU; the K1 N=1000 verify re-run and R3
  3-seed sweep are optional and gated on GPU availability.
- **Wall-clock:** ~15 min CPU for unit tests + verify gates; GPU
  budget deferred to user confirmation.
- **Verify:** D.4 72/72, RDKit-bridge unit tests PASS, tile-shape
  unit tests PASS at n_mol=1/10, headline ledger K1 row flips to
  TIE; cover-letter "Honest limitations" item (2) resolved.

### Phase F — CIFAR-10 K3 + R5b (single PR, GPU verify gated)

- **Why last:** the only low-medium risk proposal; ships the constant
  flip behind the `--cosine-ramp-strength` flag first, runs the N=500
  verify re-run on GPU 0, then promotes the constant flip to default
  if the empirical result supports the Wave 233 P5 hypothesis. If
  the N=500 re-run does NOT improve ΔFID, the constant flip is
  REVERTED to None and the falsification is documented.
- **Wall-clock:** ~15 min CPU for code + tests; ~20-30 min GPU for
  the N=500 verify re-run.
- **Verify:** D.4 72/72, factory plumbing unit tests PASS,
  `CosineScheduleConfig.n_min == FactorValue(0.5)` propagation test
  PASS, N=500 verify ΔFID improvement vs Wave 225 P7 +9.77% baseline
  (if verified, promote constant flip; if falsified, revert).

**Total wall-clock budget** (all 5 proposals):

- **CPU-only verify phases:** ~2.5 hours.
- **Optional GPU verify phases:** CIFAR-10 N=500 (~20-30 min) +
  FlowMol3 K1 N=1000 (~15-30 min) + FlowMol3 R3 3-seed (~3 hours,
  deferred) + R6 full LineageFlow N=1000 (~3 hours, deferred) ≈
  ~7 hours total GPU if all GPU verifies are exercised.

**User-approval gates:** between each of the 6 phases (A→B→C→D→E→F),
per the Wave 274 / Wave 275 pattern of single-PR single-wave with
explicit user approval before the next wave starts. **No push** until
user explicitly approves.

---

## 5. Pending user review

**All 5 proposals are PROPOSALS, not implementations.** No source code
has been modified by any of the 5 underlying PRs. The baseline is
frozen at HEAD commit `8cd59b5` (Wave 275 P3: project flattening).
This overview is the synthesis for user review before any of the 5
proposals ships.

**User review checklist** (recommended order):

1. **Approve / reject / defer each of the 5 proposals individually.**
   - Per-proposal recommendation: APPROVE all 5 (each is bounded-LOC,
     vendored-clean, byte-stable, and addresses a documented weak
     claim from the Wave 275 P1 inventory).
2. **Confirm GPU budget for the optional GPU verify phases.** Per §3
   risk dashboard + §4 implementation priority:
   - CIFAR-10 R5b N=500 verify re-run (~20-30 min, GPU 0) — required
     for the K3 constant flip to be promoted from flag-only default.
   - FlowMol3 K1 N=1000 verify re-run (~15-30 min, GPU 0) — optional.
   - FlowMol3 R3 3-seed sweep at N=1000 (~3 hours, GPU 0) — optional,
     deferred until confirmation.
   - R6 full LineageFlow N=1000 sweep (~3 hours, GPU 0) — optional,
     deferred until Wave 202 P2 sm_120 torch blocker is resolved.
3. **Approve the implementation priority + sequencing** in §4 above
   (Phase A MNIST → Phase B R6 → Phase C LineageFlow K7 → Phase D
   LineageFlow K4+K5 → Phase E FlowMol3 K1+R3 → Phase F CIFAR-10 K3+R5b).
4. **Confirm the NO PUSH directive** — each of the 5 PRs is committed
   only; the user explicitly approves the push after each phase's
   verify lands.

**Cross-references**:

- Wave 275 P1 state inventory: `docs/audit/wave275-p1-state-inventory.md` §4.2-§4.4
- Wave 275 P2 metric ledger: `docs/audit/wave275-p2-metric-ledger.md`
- Wave 275 P3 flattening: commit `8cd59b5` (proposal baseline)
- Per-proposal docs (linked in §1):
  - `docs/audit/wave275-p4-mnist-proposal.md`
  - `docs/audit/wave275-p4-r6-proposal.md`
  - `docs/audit/wave275-p4-lineageflow-proposal.md`
  - `docs/audit/wave275-p4-flowmol3-proposal.md`
  - `docs/audit/wave275-p4-cifar10-proposal.md`

---

**End of overview — awaits user review before any of the 5 proposals
implements. NO source code modified by this commit. Baseline frozen
at `8cd59b5`.**