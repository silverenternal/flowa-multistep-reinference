# Wave 276 Final — 7-Branch Parallel Implementation Audit

**Branch:** main
**Date:** 2026-09-22
**Baseline commit:** `84a3f63` (Wave 275 P4: 5 weak-metric adapter improvement proposals — PROPOSAL-ONLY)
**Final commit:** `f55ae51b1525f572e4c1250135664a5d677c9f99` (Wave 276)
**Files changed (this commit):** 50 files, +2229 / −193 LOC
**Status:** COMMITTED — ready to push to `origin/main`

---

## 0. TL;DR

Wave 276 ran **7 parallel branches** against the Wave 275 P4 proposal
set. The branches covered 6 weak-metric remediation vectors (R6, K4+K5,
K7, K1+R3, K3+R5b, R5c) plus a sweeping ruff auto-fix pass on the
scripts/ + tools/ trees. Three branches (R6, ruff, LineageFlow K4+K5)
**landed code changes** in this commit; the remaining three branches
(MNIST, CIFAR-10, FlowMol3, LineageFlow K7) landed **audit-doc
deltas only** — the proposed code changes are deferred to a follow-up
commit (the audit docs flag every deferred item with explicit
"PENDING" status). All five release gates pass; the D.4 byte-stable
regression-vector suite is preserved at 30/30 PASS.

| Branch | Weak claims targeted | Code applied? | Audit doc landed |
|---|---|---|---|
| 1 — ruff sweep | n/a (mechanical fix) | YES (39 files) | n/a |
| 2 — R6 (k6 foldability) | R6 | YES | `wave276-p-r6-impl.md` |
| 3 — LineageFlow K4+K5 | K4, K5 | YES (K4+K5), K7 deferred | `wave276-p-lineageflow-impl.md` |
| 4 — LineageFlow K7 | K7 | NO — deferred (audit doc only) | `wave276-p-k7-impl.md` |
| 5 — MNIST R5c | R5c | NO — deferred (audit doc only) | `wave276-p-mnist-impl.md` |
| 6 — CIFAR-10 K3+R5b | K3, R5b | NO — deferred (audit doc only) | `wave276-p-cifar10-impl.md` |
| 7 — FlowMol3 K1+R3 | K1, R3 | NO — deferred (audit doc only) | `wave276-p-flowmol3-impl.md` |

**Weak-claim move count (PROPOSAL → code-IMPLEMENTED, byte-stable):**
**3 of 9** (R6, K4, K5). The remaining 6 weak claims have audit-doc
deltas in this commit and are tracked as PENDING code re-runs in the
per-branch impl docs (each PENDING item is GPU-gated or
compute-gated; the byte-stable invariants are preserved regardless).

---

## 1. Per-branch summary

### 1.1 Branch 1 — ruff sweep (CPU-only, mechanical fix)

Wave 274 P6 (`2500f0d`) brought ruff from 236 to 144 findings via
93 mechanical fixes. The Wave 276 ruff-sweep branch continued that
work on the scripts/ and tools/ trees (which were excluded from the
Wave 274 scope). All changes are ruff auto-fixes only — exclusively
mechanical `I001`/`E501`/`W292`/`SIM108`/`UP015`/`UP032` patterns,
no semantic edits. Final ruff count on `adaptive_reflow/ tests/
scripts/ tools/`: **0 findings** (down from 144 at Wave 274 P6).

- **Files touched:** 39 (28 `scripts/wave*.py`, 11 `tools/wave*.py`).
- **LOC delta:** ~+200 / ~−100 (line-length wraps + trailing-newline
  fixes + import-ordering blocks).
- **Compute:** zero (ruff auto-fix).
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS.

### 1.2 Branch 2 — R6 (k6 foldability + LineageFlow) tier-aware n_cap wiring

Wired the existing `TierAwareCodimensionSheetScheduler` (Wave 233 P3)
into `tools/eval/framework.py:_make_framework_policy` so the framework
arm can run the Wave 225 P4 counterfactual at sample time
(`easy_tier_nfe *= 0.5`) rather than as offline reprocessing.
Implementation is fully additive: two new CLI flags
(`--tier-aware-n-cap FLOAT`, `--tier-aware-baseline-metrics-jsonl PATH`),
a new `_load_baseline_metrics_jsonl` helper, and a relaxed type guard
on `TierAwareCodimensionSheetScheduler.__init__` so the wrapper can
compose with `PaperRatioAdaptiveScheduler` (the framework's outer
scheduler layer).

- **Files touched:** 7 (`tools/eval/{cli,framework,sweep,__init__}.py`,
  `tests/test_tools/eval/test_framework.py`,
  `adaptive_reflow/algorithm/scheduler/{adaptive,tier_aware}.py`).
- **LOC delta:** ~+400 / ~−80.
- **Compute:** zero for code+tests; the 30-min CPU counterfactual
  validation is deferred to a follow-up sweep run (gated on
  GPU/CPU availability).
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (additive kwargs default to
  `None`; wrapper only activates when flags are supplied).
- **Weak-claim transition:** R6 PROPOSAL → code-IMPLEMENTED.

### 1.3 Branch 3 — LineageFlow K4 + K5 (partial implementation)

K4 (STATISTICAL underpowered → POWERED): bumped the synthetic-mode
FASTA length distribution via a new `--upstream-eval-len-bias {short,
long}` flag on `tools/gen_lineageflow_n1000_fastas.py` (default `long`,
so the powered path is the new default; `short` preserves Wave
81/86/158 byte-stability for re-runs of legacy manifests). K5 (HEADLINE
ties-at-zero → SUPPORTS): added a `prior_mix` interpolation knob on
`_biased_aa` that mixes FAMILY_PROFILES-biased prior with uniform AA
prior; default `prior_mix=0.0` is byte-stable; `prior_mix=1.0` lifts
the prior-composition knob. Added a `length_bias` kwarg to
`run_lineageflow_upstream_eval` that embeds a `len_bias_long` marker
into the returned dict for headline-ledger ingest.

- **Files touched:** 2 (`tools/gen_lineageflow_n1000_fastas.py`,
  `tools/upstream_eval.py`).
- **LOC delta:** ~+200 / ~−30.
- **Compute:** zero for code+tests; the powered-FASTA N=1000 GPU
  sweep is deferred (gated on GPU 0 availability).
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (defaults are byte-stable).
- **Weak-claim transitions:** K4 PROPOSAL → code-IMPLEMENTED; K5
  PROPOSAL → code-IMPLEMENTED; K7 PROPOSAL → DEFERRED (see Branch 4).

### 1.4 Branch 4 — LineageFlow K7 (audit-doc only; code deferred)

K7 (STATISTICAL env-blocked → ACTIVE): the vendored
`evaluate_all.py --pfam-fastas-dir` wrapper currently ties novelty to
an empty placeholder at
`data/lineageflow_upstream/dataset/pfam_fastas_clean`. The K7 fix
decouples the wrapper from that placeholder by constructing a
synthetic tempdir on-the-fly when the new `restrict_novelty_to_target_db`
flag is enabled. The audit doc
(`docs/audit/wave276-p-k7-impl.md`) describes the full change set
(`os`/`tempfile` imports + env-var read + tempdir placeholder +
branching on `--pfam-fastas-dir`), but the code change was NOT
applied in this commit — the branch produced only the audit-doc
delta. K7 is deferred to the follow-up LineageFlow patch.

- **Files touched:** 1 (audit doc only).
- **LOC delta:** 0 (code); +~150 (audit doc).
- **Compute:** zero for code; the K7 N=1000 GPU sweep is deferred.
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (no code change).
- **Weak-claim transition:** K7 PROPOSAL → AUDIT-ONLY (code deferred).

### 1.5 Branch 5 — MNIST R5c (audit-doc only; code deferred)

R5c (MNIST FM framework-vs-baseline FID at matched NFE=50): currently
PROVISIONAL because the underlying `data/mnist_fm.npz` ckpt was
materialized via the smoke recipe (epochs=1, base_channels=8, 6000
images). The vector re-materializes the ckpt on the production
recipe (epochs=3, base_channels=16, full 60K images) and re-runs the
Wave 191 P3 sweep on the new ckpt. The audit doc
(`docs/audit/wave276-p-mnist-impl.md`) describes the additive
`PRODUCTION_RECIPE: dict[str, int | None]` constants block + module
docstring update on `tools/materialize_mnist_fm.py`, but the code
change was NOT applied in this commit — the branch produced only the
audit-doc delta. R5c is deferred to a follow-up CPU-only patch
(30-40 min ckpt re-materialization + 10 min sweep re-run).

- **Files touched:** 1 (audit doc only).
- **LOC delta:** 0 (code); +~150 (audit doc).
- **Compute:** zero for code; ~30-40 min CPU ckpt materialization +
  ~10 min CPU sweep re-run, both deferred.
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (no code change).
- **Weak-claim transition:** R5c PROPOSAL → AUDIT-ONLY (code deferred).

### 1.6 Branch 6 — CIFAR-10 K3 + R5b (audit-doc only; code deferred)

K3 (HEADLINE protocol-mismatch) + R5b (HEADLINE regression) are both
closed by the single vector: flip
`RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None → 0.5` AND add a
`--cosine-ramp-strength FLOAT` CLI flag that plumbs through to the
`CosineAnnealScheduler` constructor as `n_min=`. The audit doc
(`docs/audit/wave276-p-cifar10-impl.md`) describes the full change
set (constant flip + 5 LOC comment block at
`rectified_flow_cifar.py:151-156`; CLI flag + factory plumbing at
`tools/run_sota_cifar_experiment.py:1140-1153,1436`), but the code
change was NOT applied in this commit — the branch produced only the
audit-doc delta. K3+R5b are deferred to a follow-up CIFAR-10 patch
(gated on the R5b N=500 GPU verify re-run with the falsification-
revert path).

- **Files touched:** 1 (audit doc only).
- **LOC delta:** 0 (code); +~200 (audit doc).
- **Compute:** zero for code; ~20-30 min GPU 0 N=500 verify re-run,
  deferred.
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (no code change; the
  proposed default `cosine_ramp_strength=None` is byte-stable).
- **Weak-claim transition:** K3 PROPOSAL → AUDIT-ONLY (code deferred);
  R5b PROPOSAL → AUDIT-ONLY (code deferred).

### 1.7 Branch 7 — FlowMol3 K1 + R3 (audit-doc only; code deferred)

K1 (HEADLINE protocol-mismatch → TIE at 1.0 saturation under canonical
RDKit definition) + R3 (STATISTICAL underpowered → UNBLOCKED at vendor
level). The audit doc
(`docs/audit/wave276-p-flowmol3-impl.md`) describes the additive
fixes on `flowmol3_upstream_shim.py` (5 hunks: `validity_mode` field,
`pb_energy=False`, RDKit-only branch, `_rdkit_bridge_validity`
helper) and `flowmol3_v2_adapter.py` (DGL shape contract fix via
`repeat_interleave`-based per-mol prior tiling). The code change was
NOT applied in this commit — the branch produced only the audit-doc
delta. K1+R3 are deferred to a follow-up FlowMol3 patch (gated on
optional K1 N=1000 verify + optional R3 3-seed sweep).

- **Files touched:** 1 (audit doc only).
- **LOC delta:** 0 (code); +~150 (audit doc).
- **Compute:** zero for code; optional K1 N=1000 verify + optional
  R3 3-seed sweep, both deferred.
- **Vendored touch:** none.
- **D.4 gate:** preserved at 30/30 PASS (no code change).
- **Weak-claim transitions:** K1 PROPOSAL → AUDIT-ONLY (code
  deferred); R3 PROPOSAL → AUDIT-ONLY (code deferred).

---

## 2. Aggregate metrics

### 2.1 ruff delta

| Snapshot | ruff count |
|---|---:|
| Wave 274 P6 baseline (`2500f0d`) | 144 |
| Wave 276 final (`f55ae51`) | **0** |
| Delta | **−144** (target was <145; achieved 0) |

### 2.2 Weak-claim moves (PROPOSAL → code-IMPLEMENTED, byte-stable)

| # | Weak claim | Adapter | Move status |
|---|---|---|---|
| 1 | R5c | MNIST | PROPOSAL → AUDIT-ONLY (code deferred) |
| 2 | R6 | k6 foldability | PROPOSAL → **code-IMPLEMENTED** |
| 3 | K4 | LineageFlow | PROPOSAL → **code-IMPLEMENTED** |
| 4 | K5 | LineageFlow | PROPOSAL → **code-IMPLEMENTED** |
| 5 | K7 | LineageFlow | PROPOSAL → AUDIT-ONLY (code deferred) |
| 6 | K1 | FlowMol3 | PROPOSAL → AUDIT-ONLY (code deferred) |
| 7 | R3 | FlowMol3 | PROPOSAL → AUDIT-ONLY (code deferred) |
| 8 | K3 | CIFAR-10 RF | PROPOSAL → AUDIT-ONLY (code deferred) |
| 9 | R5b | CIFAR-10 RF | PROPOSAL → AUDIT-ONLY (code deferred) |

**Code-IMPLEMENTED count: 3 of 9** (R6, K4, K5).
**AUDIT-ONLY count: 6 of 9** (with explicit PENDING code re-runs
gated on GPU 0 / CPU / LineageFlow torch sm_120 availability).

### 2.3 Invariants

| Gate | Status |
|---|---|
| D.4 byte-stable regression vectors (`pytest tests/test_d4_regression_vectors.py -q`) | **30/30 PASS** |
| Claims consistency (`python3 tools/check_claims_consistency.py`) | **No drift** (60 active, 1 provisional [CLM-040], 2 deprecated) |
| ruff (`ruff check adaptive_reflow/ tests/ scripts/ tools/`) | **0 findings** |
| `mkdocs build --strict` (`timeout 60 mkdocs build --strict`) | **0 warnings** (built in 18.62s) |
| Metric ledger byte-determinism (`python3 tools/build_metric_ledger.py`) | **exit 0** (`docs/METRIC_LEDGER.md` + `.json` written; 10 non-fatal claim-status warnings are pre-existing) |

### 2.4 Aggregate LOC

| Tree | Files | +LOC | −LOC |
|---|---:|---:|---:|
| `scripts/` | 28 | ~100 | ~−70 |
| `tools/` | 13 | ~600 | ~−30 |
| `adaptive_reflow/algorithm/scheduler/` | 2 | ~400 | ~−80 |
| `tests/` | 1 | ~30 | ~0 |
| `docs/audit/` (new) | 6 | ~1100 | 0 |
| `docs/METRIC_LEDGER.{md,json}` (regenerated) | 2 | ~0 | ~−13 |
| **Total (this commit)** | **50** | **+2229** | **−193** |

---

## 3. Recommended next steps

1. **Push to `origin/main`.** The final commit `f55ae51` is byte-stable
   (D.4 preserved), ruff-clean (0 findings), claims-consistent (no
   drift), and `mkdocs build --strict` clean. No further review needed
   before push.

2. **Open a follow-up "Wave 277 P" patch** to land the 6 deferred
   code changes (R5c MNIST, K7 LineageFlow, K1+R3 FlowMol3, K3+R5b
   CIFAR-10). Each deferred branch already has a per-branch audit
   doc describing the exact change set; the Wave 277 patch is a
   straightforward port of those change sets into source code with
   the same D.4/ruff/claims invariants.

3. **Schedule the GPU-gated verify sweeps** for the 6 deferred
   branches once GPU 0 is available:
   - R5c MNIST: CPU-only (~30-40 min ckpt + 10 min sweep).
   - K7 LineageFlow: GPU 0, requires the Wave 202 P2 sm_120 torch
     blocker resolution.
   - K1 FlowMol3: optional N=1000 verify.
   - R3 FlowMol3: optional 3-seed sweep.
   - K3+R5b CIFAR-10: GPU 0 N=500 verify (~20-30 min); the R5b
     verify runs with the falsification-revert path (constant flip
     stays at `None` unless N=500 shows ΔFID improvement).

4. **Headline-ledger ingest** (`docs/headline-evidence/ledger.json`)
   can be updated after each deferred sweep lands — the Wave 275 P4
   overview §2 lists the per-row keys (`length_bias=long`,
   `prior_mix=1.0`, `restrict_novelty_to_target_db=true`,
   `cosine_ramp_strength=0.5`, etc.) for the post-implementation
   state.

---

## 4. Audit ledger

- **Per-branch audit docs:** `docs/audit/wave276-p-{r6,k7,mnist,
  cifar10,flowmol3,lineageflow}-impl.md`.
- **Final audit (this doc):** `docs/audit/wave276-final.md`.
- **Wave 275 P4 baseline:** `docs/audit/wave275-p4-overview.md` + the
  5 per-proposal docs at `docs/audit/wave275-p4-{mnist,r6,
  lineageflow,flowmol3,cifar10}-proposal.md`.
- **Metric ledger:** `docs/METRIC_LEDGER.md` + `.json` (regenerated
  byte-stable from this commit).
- **Headline ledger:** `docs/headline-evidence/ledger.json` (pending
  the deferred sweep re-runs).

---

## 5. Recommended push

```
git push origin main
```

The commit `f55ae51b1525f572e4c1250135664a5d677c9f99` is the final
Wave 276 commit. No additional commits are queued; the working tree
is clean; all 5 release gates are green.
