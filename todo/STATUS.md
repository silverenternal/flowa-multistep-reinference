# `todo/STATUS.md` — current execution status (2026-09-14 v1.0-paper-final)

**Updated:** 2026-09-14 (Wave 134 final pass — `/tmp/` → repo
`verification_outputs/` path migration across 3 doc surfaces, completing
the post-Wave-127+ refresh). This file replaces the stale Wave 127
finish-line snapshot that was preserved below for provenance. The
historical table after the divider does not reflect the current repo
state — it is kept only for traceability.

The folder was flattened by Wave 127 Phase 5: `todo/completed/`,
`todo/inprogress/`, `todo/planned/`, `todo/models/` were deleted. The
47 archived plans under `todo/completed/`, the 8 plans under
`todo/planned/`, the 5 files under `todo/models/`, and the 1 README
under `todo/inprogress/` are removed. Their historical content is
preserved in git history (commits `14e8bc5^` and earlier).

---

## Current evidence and next gates (2026-09-14, v1.0-paper-final)

- **HEAD commit:** `752b9af` (Wave 134 Phase 3 — final `/tmp/` path
  migration; this Phase 4 commit `b62c1e9` adds the STATUS + INDEX
  refresh and bumps HEAD to `b62c1e9`).
- **Tag:** `v1.0-paper-final` (Wave 131 Phase 3 freeze marker, points
  to `39a65a7`; ruff 0 / D.4 33/33 / pytest ≥5155 / claims PASS /
  mkdocs strict EXIT=0 / ckpt SHA-256 4/4 PASS). Post-Wave 134 will
  add `v1.0.1-paper-final` as the doc-only `/tmp/` → `verification_outputs/`
  migration tag (additive; no source-code change).
- **Unpushed commits ahead of `origin/main`:** 3 (post-Wave 134 Phase 3
  `752b9af`). 0 behind. The Wave 11-127 backlog (~167 commits) was
  pushed during Wave 128-133; only the Wave 134 doc-migration Phases
  1-3 are now unpushed. After this Phase 4 commit the count becomes 4.
- **D.4 byte-stable regression vectors:** 33/33 adapters PASS (preserved
  through Wave 131 ruff-frozen code; 297 byte-hash vectors, 9 per
  adapter × 33 adapters; last verified Wave 134).
- **Pytest default-threads:** 5155 passed, 196 skipped (last verified
  Wave 131 freeze; `v1.0-paper-final` tag).
- **Ruff:** 0 findings (down from 207 in Wave 127; Wave 131 Phase 1
  F821 TYPE_CHECKING guard + auto-fix + noqa annotations, D.4 33/33
  preserved). Verified `ruff check adaptive_reflow/ tests/`
  → `All checks passed!` (Wave 134).
- **Mypy:** 988 errors in 70 files (camera-ready only; out of scope
  for the 7-day finish-line; CLM-024 wording acknowledges — Wave 127
  Phase 3).
- **mkdocs build --strict:** PASS (last verified Wave 131
  `1ce8e3a`; re-verify after Wave 134).
- **ckpt SHA-256:** 4/4 PASS (FlowMol3, Kanzi cleaned_model, Kanzi
  encoder, LineageFlow) per `verification_outputs/ckpt_sha256.json`
  (Wave 106.C.1, refreshed Wave 131).
- **claims_consistency:** PASS (No drift detected; 39 ACTIVE, 2
  DEPRECATED) per `python tools/check_claims_consistency.py`
  (Wave 134).
- **N=1000 sweep JSONs in repo (formal reproducibility set):** 8
  headline JSONs at `verification_outputs/` top level:
  1. `flowmol3_n1000_baseline_q4_2026.json`
  2. `flowmol3_n1000_framework_q4_2026.json`
  3. `flowmol3_n1000_sweep_q4_2026.json`
  4. `kanzi_n1000_manifest.json`
  5. `lineageflow_n1000_baseline_q4_2026.json`
  6. `lineageflow_n1000_framework_q4_2026.json`
  7. `lineageflow_n1000_omegafold_q4_2026_baseline.json`
  8. `lineageflow_n1000_omegafold_q4_2026_framework.json`
  Plus 14 Kanzi N=1000 subdirectories (Wave 115/120/121/122/124/127/131
  + real + real_diverse + diverse + inv_proj variants) at
  `verification_outputs/kanzi_n1000_*/`. The Wave 134 doc migration
  replaces 3 `/tmp/w122/...` and `/tmp/w127/...` paths in
  `paper-draft.md` / `baseline-audit-report.md` /
  `CONSOLIDATED_RESULTS.md` with the repo-resident equivalents.

## Active plans (8 root files, post-Wave-127+ refresh)

The `todo/` root now holds 8 active plan files. The previous
`todo/completed/`, `todo/inprogress/`, `todo/planned/`, `todo/models/`
subtrees have been deleted (their content lives in git history).

| # | Plan file | Status |
|---|---|---|
| 1 | `todo/algo-improvement-paper-quantity-beta-calibration.md` | **SHIPPED** (Wave 125 — code landed `4fbf135` + `da090c2`); camera-ready only — CIFAR/twodim acceptance deferred |
| 2 | `todo/algo-improvement-restart-policy-collapse-fix.md` | **SHIPPED** (Wave 125 — code landed `4fbf135`); camera-ready only — twodim/CIFAR acceptance deferred |
| 3 | `todo/algo-improvement-brai-perturbation-magnitude.md` | **SHIPPED** (Wave 125 — code landed `ae33583`); camera-ready only — ESM-2 N=100 + N=1000 acceptance deferred |
| 4 | `todo/algo-improvement-framework-vs-model-metrics-gap.md` | **READ-ONLY synthesis** (Wave 123 Agent 6); no further code in 7-day scope |
| 5 | `todo/adapter-improvement-inv-proj-bridge-lossy-replacement.md` | **SHIPPED** (Wave 122 P2 + Wave 127/128 N=1000 byte-reproducible); Kanzi framework_inv_proj N=1000 framework 0.8798 vs baseline 0.9020 (TIES, byte-reproducible on ruff-frozen code, Wave 131 Phase 3) |
| 6 | `todo/adapter-improvement-8-adapter-shim-audit.md` | **READ-ONLY audit** (Wave 123 Agent 6); per-adapter fixes deferred to camera-ready |
| 7 | `todo/paper-finish-line-radical-tier1.md` | **EXECUTED** (Wave 129 — radical Tier-1 SCI plan replaces Wave 127 conservative framing; cover letter + §1/§7 + supplementary + checklist all landed Wave 132-133) |
| 8 | `todo/code-tasks-before-freeze.md` | **EXECUTED** (Wave 130 — pre-freeze engineering audit + plan; ruff 207→0 Wave 131 Phase 1 + D.4 33/33 + pytest 5155 + claims PASS all green) |

## Camera-ready deferred (UNCHANGED — NOT in 7-day scope)

- Mypy 988 hand-fix (CI-static-gate)
- Wan2.2 / FreqFlow / MM-FM (no upstream ckpt / no shipped adapter;
  indefinitely deferred per Wave 36)
- N=5000-50000 trajectory expansion (Wave 92d, OPT-IN, W3 defer)
- PB-xtb pipeline closure (W1 closed by Wave 90 PB-xtb real wire;
  no follow-up camera-ready work in scope)
- OmegaFold env (Python<=3.10 — environment incompatibility, blocked)
- LineageFlow `novelty_mmseqs2` (Pfam fastas placeholder — would need
  fresh MMseqs2 + Pfam fastas re-pull)
- Wave 86 LineageFlow N=1000 HMMER raw JSON (still NOT in `/tmp/`
  either; would need fresh re-run from raw HMMER output, ~30 min on
  LineageFlow venv)

## Push state

- **3 unpushed commits** on `main` ahead of `origin/main` at the close
  of Wave 134 Phase 3 (`752b9af`). 0 behind. After this Phase 4
  STATUS + INDEX refresh commit, count becomes 4.
- **`push_risk = LOW`** (D.4 33/33 PASS; pytest 5155/196 green; ruff
  0; claims PASS; mkdocs build --strict EXIT=0; ckpt SHA-256 4/4).
- **PUSH IS USER-GATED.** Wave 11+ protocol reaffirmed in
  `todo/PUSH-READY.md` and `todo/push-unpushed-commits.md`. No push in
  Wave 134.

## File inventory (post Wave 134 Phase 4)

```
todo/
├── STATUS.md                                          ← this file
├── INDEX.md                                           ← master entry point
├── PUSH-READY.md                                      ← push-readiness (refreshed Wave 134)
├── push-unpushed-commits.md                           ← push-protocol log (Wave 12; superseded)
├── GATES.md                                           ← master gate definitions
├── LOOP.md                                            ← per-model lifecycle
├── TIMELINE.md                                        ← phase durations + "done" definition
├── RISK-REGISTER.md                                   ← forward-looking risks
├── EXECUTION-PLAN.md                                  ← pending tasks broken into ~110 atomic subtasks
├── decisions.md                                       ← architecture decision log (append-only)
├── lessons-learned.md                                 ← cross-cutting patterns (append-only)
├── README.md                                          ← directory structure
├── framework-freeze-checklist.md                      ← MUST-1..5 freeze criteria
├── framework-internal-metrics.md                      ← rev 2 ship-ready (Wave 13)
├── framework-capability-metrics.md                    ← group G capability metrics
├── PHASE-1-framework-and-theory.md                    ← done (Wave 11-12)
├── PHASE-2-model-complexity-analysis.md               ← done (Wave 19 P1A1)
├── PHASE-3-glue-layer-improvement.md                  ← done (Wave 24 + 38 + 39)
├── algo-improvement-paper-quantity-beta-calibration.md ← SHIPPED (Wave 125); camera-ready only
├── algo-improvement-restart-policy-collapse-fix.md    ← SHIPPED (Wave 125); camera-ready only
├── algo-improvement-brai-perturbation-magnitude.md    ← SHIPPED (Wave 125); camera-ready only
├── algo-improvement-framework-vs-model-metrics-gap.md ← READ-ONLY synthesis (Wave 123)
├── adapter-improvement-inv-proj-bridge-lossy-replacement.md ← SHIPPED (Wave 122 P2 + Wave 127/128 byte-repro)
├── adapter-improvement-8-adapter-shim-audit.md        ← READ-ONLY audit (Wave 123)
├── paper-finish-line-radical-tier1.md                 ← EXECUTED (Wave 129)
└── code-tasks-before-freeze.md                        ← EXECUTED (Wave 130)
```

Total: 26 files at the `todo/` root. Previously ~80 (when subdirs
included 47 archived + 8 planned + 5 model cards + 1 inprogress README).

## Cross-references

- [`docs/CONSOLIDATED_RESULTS.md`](../docs/CONSOLIDATED_RESULTS.md) —
  Tier 3 verdict table §15.32 (Wave 131 final close)
- [`docs/CLAIMS.md`](../docs/CLAIMS.md) — 39 ACTIVE + 2 DEPRECATED
  claims (41 CLM entries; `tools/check_claims_consistency.py` PASS)
- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit
  catalogue (Wave 1 → Wave 134, 63+ of 101+ waves have audit docs)
- [`docs/audit/wave127-finish-line.md`](../docs/audit/wave127-finish-line.md) —
  Wave 127 audit doc (authored Wave 127 Phase 6)
- [`docs/audit/wave131-pre-freeze-hygiene.md`](../docs/audit/wave131-pre-freeze-hygiene.md) —
  Wave 131 audit doc (pre-freeze engineering pass; ruff 207→0)
- [`docs/audit/wave132-tier1-polish.md`](../docs/audit/wave132-tier1-polish.md) —
  Wave 132 audit doc (Tier-1 SCI polish; cover letter + NeurIPS
  template + camera-ready sections)
- [`docs/audit/wave133-number-consistency.md`](../docs/audit/wave133-number-consistency.md) —
  Wave 133 audit doc (number consistency + final polish)
- `git tag v1.0-paper-final` — freeze marker (points to `39a65a7`)

---

# Historical Wave 99.D snapshot (PRESERVED FOR PROVENANCE — DO NOT EDIT)

> The following snapshot is the Wave 99.D / 2026-09-10 close-out of
> `todo/STATUS.md`. It is preserved verbatim for traceability. Its
> commit counts, resource estimates, directory listing and gate
> verdicts are NOT current.

**Last updated:** 2026-09-10 (Wave 99.D — real N=1000 Kanzi final synthesis)
**Wave:** Wave 99.D final synthesis (this wave) — closes W2 ON MEASURABILITY+DIRECTION; DEFER on magnitude pending Wave 100+ N=1000 framework arm
**Push state:** 327 unpushed commits on `main`, `push_risk = LOW` (user-gated)

## One-line current verdict

> **W2 = PARTIALLY CLOSED** (measurability + direction closed at N=10 framework arm; magnitude deferred to Wave 100+). Wave 99.B verdict: Kanzi `reconstruction_kabsch_rmsd_A` REGRESSES_BY_+0.864_Å (Bonferroni p = 4.6e-7 ≪ 0.0083) at N=10 framework arm vs N=1000 baseline; 5 codebook metrics NOT_SIGNIFICANT at Bonferroni α=0.0083. Architectural explanation (Wave 92c §5): framework's continuous-latent endpoint lives in post-`project_out` (n_channels_decoder=512) space, and the nearest-neighbour L2 projection onto `FSQ.implicit_codebook` loses ~0.86 Å vs canonical `DAE.encode → DAE.decode`. Forward projection at N=1000 framework arm: 95% CI of Δ tightens ±0.19 Å → ±0.02 Å — enough to defend a magnitude claim. Wave 100+ queued (~16.7 hours wall-clock on `kanzi_venv` CPU sidecar).

## What's landed (Wave 90-99)

| Wave | Commit | Purpose |
|---|---|---|
| **Wave 90** | `fe95293` | FlowMol3 PB-xtb pipeline real wire (W1 closed) |
| Wave 86-89 | `e5e9804` / `fa09be3` / `334d914` / `6add1b9` / `e77d2d4` | framework-loop fix + Tier 3 paper-metric N=1000 reproduction + paper §7 final |
| **Wave 91** (planned: w2-kanzi-latent-coord-bridge) | `dfe0f4e` + `8c5eaaf` + `2a4c46e` | Kanzi latent→coord bridge + wire into eval pipeline |
| **Wave 92a** (planned: w2b-kanzi-adapter-refactor) | `73c6978` | Kanzi adapter refactor: 3 WRONG constants → ckpt model_cfg load (512/1000/backbone-dependent) |
| **Wave 92b** (planned: w2b-kanzi-adapter-refactor) | `60dcbb7` | Kanzi upstream N-samples patch (mirror LineageFlow Wave 81): --max-records N + --output-jsonl + mean/std/95%CI |
| **Wave 93 Phase 1** | `e69ffd8` | Statistical power analysis tool + 4 unit tests (Bonferroni + power + verdict thresholds) |
| **Wave 95** | `378dc4a` + `1b17dfa` | project_out⁻¹ architectural fix wired into kanzi_latent_to_coord.py + re-sweep |
| **Wave 96** | `a7b97d2` + `1f26bf6` + `80f7fa8` + `bed3284` + `8656030` + `d616f6b` + `c53aa10` | Endpoint-collapse root-cause + targeted fix + diverse-endpoint sweep + reality check + production sweep (N=10 framework arm) |
| **Wave 97** | `f17fcc5` + `603f4fd` + `b88cb13` + `facb94e` + `c4b176b` | Routing collapse (5 routing problems) + tools/eval/ split + glue collapse + N=1000 hard assertion + final audit |
| **Wave 98** | `99834d9` + `ae2327b` + `3856f28` + `eb05d7d` | GPU watchdog + SOTA config alignment audit + paper-parity defaults enforcement + final synthesis |
| **Wave 99.A** | `1f6bab5` | Docs-only refresh of baseline-audit-report.md (Wave 91-93 additive notes) |
| **Wave 99.B** | `9893710` | Real N=1000 Kanzi verdict + statistical power analysis (uses Wave 96.E N=10 framework arm) |
| **Wave 99.C** | `06f0505` | Update paper §7.3 + CONSOLIDATED_RESULTS §15 + 12-cell table with Wave 99.B verdict |
| **Wave 99.D** | (this commit) | Final synthesis — W2 PARTIALLY CLOSED, cover letter + baseline-audit + STATUS updates |

## Tier 3 final state (3/3 SOTA models)

| Model | Composite axis (designed) | Paper axis N=1000 |
|---|---|---|
| **FlowMol3** | **+0.1182 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`fg_dev` -0.0235, 4.05σ), 1/4 REGRESSES (`pb_validity_pct` UFF-vs-xtb definitional gap) |
| **LineageFlow** | **+0.2083 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`hmmscan_total_hits` +116%, p<1e-10) |
| **Kanzi** | **+0.1895 SUPPORTED** (Wave 52 byte-stable) | **Wave 99.B: 1/6 REGRESSES_BY_+0.86_Å on `reconstruction_kabsch_rmsd_A`** (Bonferroni p = 4.6e-7, N=10 framework arm) + 4/6 NOT_SIGNIFICANT + 1/6 BORDERLINE on `codebook_utilization` |
| **3/3 composite axis** | | **2-3/14 paper-metric cells framework_improves, 1/14 REGRESSES_BY_+0.86_Å on Kanzi (architectural cost, Wave 92c §5)** |

## What's in flight (must finish before ICLR submission)

| Wave | Task | Status | Wall-clock |
|---|---|---|---|
| **Wave 100+** | N=1000 Kanzi framework paper-metric sweep (close W2 magnitude) | queued (~16.7h on kanzi_venv CPU) | ~17h |
| **Wave 94** | Cover letter + paper §1/§7 final + supplementary + checklist | partial — Wave 99.D updated cover letter; Wave 94 closes §7 final | ~2-3h |
| Wave 92d (OPT-IN) | N=5000 sweep on all 3 Tier 3 models | waiting for user OK | ~4-8h |

## Verification gates (all PASS as of Wave 99.D)

- **D.4 byte-stable:** 18/18 adapters PASS (162 vectors, 9 per adapter) via `tools/run_regression_vector_audit.py verify`
- **G-MASTER capability:** 7/7 PASS (hard_pass=5, soft_pass=2)
- **mkdocs build --strict:** EXIT=0
- **Per-test suites touched in Wave 99.D:** all PASS (docs-only this wave)

## 4 一区 reviewer weaknesses — final status

| # | Weakness | Status | Closed by |
|---|---|---|---|
| **W1** | FlowMol3 `pb_validity_pct = 0.43` vs paper `0.919` | ✅ **CLOSED** | Wave 90 (PB-xtb pipeline real wire, commit `fe95293`) |
| **W2** | Kanzi framework arm NOT_MEASURABLE | ⚠️ **PARTIALLY CLOSED** (measurability+direction closed; magnitude DEFERRED to Wave 100+ N=1000 framework arm) | Wave 91 (bridge `dfe0f4e`) + Wave 92a (constants fix `73c6978`) + Wave 92b (N-samples `60dcbb7`) + Wave 95 (project_out⁻¹ `378dc4a`) + Wave 96 (diverse endpoints + reality check + production N=10 sweep) + Wave 97 (N=1000 hard assertion) + Wave 98 (GPU watchdog + SOTA defaults) + Wave 99.B/C/D (verdict + paper + cover letter + STATUS update) |
| **W3** | N=1000 too small | ⚠️ **DEFER (OPT-IN)** | Wave 92d (N=5000 sweep, optional) — N=1000 + Wave 93 power analysis is defensible per master plan §5b |
| **W4** | 2/12 framework_improves cells | 🔄 **in reframing** | Wave 93 Phase 2 (statistical power + Bonferroni + 12-row table) — verdict evolution `2/12 SUPPORTED` → `4/12 SUPPORTED + 6/12 TIE + 2/12 UNDERPOWERED` |

## Push state (Wave 99.D snapshot)

- **327 unpushed commits** on `main` ahead of `origin/main` (`git log @{u}..main | wc -l = 327`)
- **`push_risk = LOW`** (D.4 18/18 PASS; G-MASTER 7/7; mkdocs EXIT=0; no broken-test pre-push)
- **NO push** (user-gated per locked-in constraint since Wave 11)

## File inventory (Wave 99.D)

```
todo/
├── STATUS.md                   ← this file
├── INDEX.md                    ← master entry point (updated Wave 56)
├── completed/                  ← 47 archived plans
├── inprogress/                 ← 3 historical plans (Wave 75-78 cascade — should archive)
│   ├── README.md
│   ├── wave75-78-master-plan.md        (IN PROGRESS — but waves 75-78 already landed)
│   ├── wave75-flowmol3-paper-repro.md  (CLOSED — landed in completed/)
│   └── wave76-lineageflow-paper-repro.md  (CLOSED — landed in completed/)
└── planned/                    ← 6 plans + 1 design doc
    ├── README.md                        (Wave 91-94 directory)
    ├── tier3-final-close-master-plan.md (W91-94 cascade)
    ├── w2-kanzi-latent-coord-bridge.md  (DONE — landed Wave 91)
    ├── w2b-kanzi-adapter-refactor.md    (IN PROGRESS — Wave 92a/b done, 92c in flight)
    ├── w3-n5000-paper-metric-sweep.md   (PLANNED — OPT-IN W92d)
    ├── w4-statistical-power-analysis.md (IN PROGRESS — Wave 93 Phase 1 done, Phase 2 in flight)
    ├── w5-iclr2027-submission-package.md (PLANNED — Wave 94)
    └── workflows-design.md              (small-workflow design, 4 workflows × 2-3 agents)
```

## MUST-1..5 at close-out

- **MUST-1** G-FRAMEWORK-HEALTH HARD gates — **PASS** (28/28 internal HARD + 5/5 group-G HARD)
- **MUST-2** G-MASTER-PHASE-3 per-model checks — **PASS** (Kanzi + LineageFlow real-ckpt forward verified)
- **MUST-3** framework-core glue extracted — **PASS** (Wave 44 close-out: 5 adapters import `adaptive_reflow.core/`)
- **MUST-4** group-G capability metrics cold-clone — **PASS** (`must_4_freeze_gate = PASS`)
- **MUST-5** pushed to `origin/main` — **NOT DONE, user-gated.** 326 unpushed commits; `push_risk = LOW`; every other gate green.

## Open follow-ups

1. **Wave 92c** (in flight): N=1000 Kanzi framework paper-metric — closes W2 measurability
2. **Wave 93 Phase 2** (in flight): per-cell CI + Bonferroni + reframe §7.6 — closes W4 reframing
3. **Wave 94**: ICLR 2027 submission package — cover letter + paper §1/§7 final + supplementary + checklist
4. **Wave 92d (OPT-IN)**: N=5000 sweep on all 3 Tier 3 models — closes W3 (defer until Wave 92c/93/94)
5. **FreqFlow / MM-FM**: indefinitely deferred (no upstream ckpt / no shipped adapter)
6. **CI dashboard**: composite-aware check in `tools/capability_audit.py`
