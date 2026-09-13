# `todo/STATUS.md` — current execution status

**Updated:** 2026-09-13. Engineering repair and TODO execution are authorized;
the goal remains active. No push has been authorized.

## Current evidence and next gates

- Engineering fixes through `fee9352` cover import isolation, feature-only
  FID, fail-closed real Kanzi loading, resumable sweeps and bounded protocol
  property tests. See [engineering audit](../docs/audit/engineering-audit-2026-09-13.md).
- Full default-thread pytest completed: **5155 passed, 196 skipped**, exit 0
  in 588.37 seconds, through `fee9352`. A completed
  two-thread run had 5154 passed, 196 skipped and one Lumina byte-hash failure;
  an isolated default-thread repeat passed. Golden vectors were not changed.
- CI static checks are not green: Ruff 0.15.22 reports 926 findings across
  source/tests, including missing names. Mypy against the project interpreter
  reports 988 errors in 70 files. Earlier all-PASS gate tables
  below are historical, not current readiness evidence.
- Kanzi real N=20 single-rollout diagnostic and actual resume succeeded.
  This does not satisfy calibrated bridge, independent held-out proteins,
  multi-round reconstruction or N=1000 scientific acceptance.
- Twodim controlled protocol correction is being validated in an isolated
  worktree: continuous state, measured velocity queries, exact sample count,
  joint W2 and restart-guard comparison. Old quick outputs are exploratory.
- BRAI model/ESM-2 resources and execution protocol are under audit. CIFAR
  N=200 matched-NFE=50 produced regression, not the planned improvement.

The six active root plans and unmet acceptance requirements are listed in
[open requirements](../docs/audit/open-requirements.md). Execution order:
finish engineering gates, verify corrected experiment protocols, run bounded
controls and acceptance sweeps, then update dependent synthesis/submission
material. A negative result must be recorded without changing the acceptance
threshold or silently marking the hypothesis supported.

The following snapshot is preserved for provenance. Its commit counts,
resource estimates, directory listing and gate verdicts are not current.

---

# Historical Wave 99.D snapshot

**Last updated:** 2026-09-10 (Wave 99.D — real N=1000 Kanzi final synthesis)
**Wave:** Wave 99.D final synthesis (this wave) — closes W2 ON MEASURABILITY+DIRECTION; DEFER on magnitude pending Wave 100+ N=1000 framework arm
**Push state:** 327 unpushed commits on `main`, `push_risk = LOW` (user-gated)

---

## One-line current verdict

> **W2 = PARTIALLY CLOSED** (measurability + direction closed at N=10 framework arm; magnitude deferred to Wave 100+). Wave 99.B verdict: Kanzi `reconstruction_kabsch_rmsd_A` REGRESSES_BY_+0.864_Å (Bonferroni p = 4.6e-7 ≪ 0.0083) at N=10 framework arm vs N=1000 baseline; 5 codebook metrics NOT_SIGNIFICANT at Bonferroni α=0.0083. Architectural explanation (Wave 92c §5): framework's continuous-latent endpoint lives in post-`project_out` (n_channels_decoder=512) space, and the nearest-neighbour L2 projection onto `FSQ.implicit_codebook` loses ~0.86 Å vs canonical `DAE.encode → DAE.decode`. Forward projection at N=1000 framework arm: 95% CI of Δ tightens ±0.19 Å → ±0.02 Å — enough to defend a magnitude claim. Wave 100+ queued (~16.7 hours wall-clock on `kanzi_venv` CPU sidecar).

---

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

---

## Tier 3 final state (3/3 SOTA models)

| Model | Composite axis (designed) | Paper axis N=1000 |
|---|---|---|
| **FlowMol3** | **+0.1182 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`fg_dev` -0.0235, 4.05σ), 1/4 REGRESSES (`pb_validity_pct` UFF-vs-xtb definitional gap) |
| **LineageFlow** | **+0.2083 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`hmmscan_total_hits` +116%, p<1e-10) |
| **Kanzi** | **+0.1895 SUPPORTED** (Wave 52 byte-stable) | **Wave 99.B: 1/6 REGRESSES_BY_+0.86_Å on `reconstruction_kabsch_rmsd_A`** (Bonferroni p = 4.6e-7, N=10 framework arm) + 4/6 NOT_SIGNIFICANT + 1/6 BORDERLINE on `codebook_utilization` |
| **3/3 composite axis** ✅ | | **2-3/14 paper-metric cells framework_improves, 1/14 REGRESSES_BY_+0.86_Å on Kanzi (architectural cost, Wave 92c §5)** |

---

## What's in flight (must finish before ICLR submission)

| Wave | Task | Status | Wall-clock |
|---|---|---|---|
| **Wave 100+** | N=1000 Kanzi framework paper-metric sweep (close W2 magnitude) | queued (~16.7h on kanzi_venv CPU) | ~17h |
| **Wave 94** | Cover letter + paper §1/§7 final + supplementary + checklist | partial — Wave 99.D updated cover letter; Wave 94 closes §7 final | ~2-3h |
| Wave 92d (OPT-IN) | N=5000 sweep on all 3 Tier 3 models | waiting for user OK | ~4-8h |

---

## Verification gates (all PASS as of Wave 99.D)

- **D.4 byte-stable:** 18/18 adapters PASS (162 vectors, 9 per adapter) via `tools/run_regression_vector_audit.py verify`
- **G-MASTER capability:** 7/7 PASS (hard_pass=5, soft_pass=2)
- **mkdocs build --strict:** EXIT=0
- **Per-test suites touched in Wave 99.D:** all PASS (docs-only this wave)

---

## 4 一区 reviewer weaknesses — final status

| # | Weakness | Status | Closed by |
|---|---|---|---|
| **W1** | FlowMol3 `pb_validity_pct = 0.43` vs paper `0.919` | ✅ **CLOSED** | Wave 90 (PB-xtb pipeline real wire, commit `fe95293`) |
| **W2** | Kanzi framework arm NOT_MEASURABLE | ⚠️ **PARTIALLY CLOSED** (measurability+direction closed; magnitude DEFERRED to Wave 100+ N=1000 framework arm) | Wave 91 (bridge `dfe0f4e`) + Wave 92a (constants fix `73c6978`) + Wave 92b (N-samples `60dcbb7`) + Wave 95 (project_out⁻¹ `378dc4a`) + Wave 96 (diverse endpoints + reality check + production N=10 sweep) + Wave 97 (N=1000 hard assertion) + Wave 98 (GPU watchdog + SOTA defaults) + Wave 99.B/C/D (verdict + paper + cover letter + STATUS update) |
| **W3** | N=1000 too small | ⚠️ **DEFER (OPT-IN)** | Wave 92d (N=5000 sweep, optional) — N=1000 + Wave 93 power analysis is defensible per master plan §5b |
| **W4** | 2/12 framework_improves cells | 🔄 **in reframing** | Wave 93 Phase 2 (statistical power + Bonferroni + 12-row table) — verdict evolution `2/12 SUPPORTED` → `4/12 SUPPORTED + 6/12 TIE + 2/12 UNDERPOWERED` |

---

## Push state

- **327 unpushed commits** on `main` ahead of `origin/main` (`git log @{u}..main | wc -l = 327`)
- **`push_risk = LOW`** (D.4 18/18 PASS; G-MASTER 7/7; mkdocs EXIT=0; no broken-test pre-push)
- **NO push** (user-gated per locked-in constraint since Wave 11)

---

## File inventory (current state)

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

---

## Cross-references for this close-out

- `todo/INDEX.md` — master entry point (Wave 56 + Wave 92-93 update pending)
- `todo/planned/tier3-final-close-master-plan.md` — W91-94 cascade plan
- `docs/push-ready-summary.md` — final pre-push synthesis (Wave 89 + Wave 91 + Wave 92 additive)
- `docs/audit/wave92a-kanzi-fix-constants.md` — Wave 92a audit
- `docs/audit/wave93-phase1-statistical-power.md` — Wave 93 Phase 1 audit (when committed)
- `verification_outputs/kanzi_n1000_framework_paper_metrics_real/` — Wave 92c final output (target)

---

## MUST-1..5 at close-out

- **MUST-1** G-FRAMEWORK-HEALTH HARD gates — **PASS** (28/28 internal HARD + 5/5 group-G HARD)
- **MUST-2** G-MASTER-PHASE-3 per-model checks — **PASS** (Kanzi + LineageFlow real-ckpt forward verified)
- **MUST-3** framework-core glue extracted — **PASS** (Wave 44 close-out: 5 adapters import `adaptive_reflow.core/`)
- **MUST-4** group-G capability metrics cold-clone — **PASS** (`must_4_freeze_gate = PASS`)
- **MUST-5** pushed to `origin/main` — **NOT DONE, user-gated.** 326 unpushed commits; `push_risk = LOW`; every other gate green.

---

## Open follow-ups

1. **Wave 92c** (in flight): N=1000 Kanzi framework paper-metric — closes W2 measurability
2. **Wave 93 Phase 2** (in flight): per-cell CI + Bonferroni + reframe §7.6 — closes W4 reframing
3. **Wave 94**: ICLR 2027 submission package — cover letter + paper §1/§7 final + supplementary + checklist
4. **Wave 92d (OPT-IN)**: N=5000 sweep on all 3 Tier 3 models — closes W3 (defer until Wave 92c/93/94)
5. **FreqFlow / MM-FM**: indefinitely deferred (no upstream ckpt / no shipped adapter)
6. **CI dashboard**: composite-aware check in `tools/capability_audit.py`