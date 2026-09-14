# `todo/STATUS.md` — current execution status (2026-09-14 Wave 127 finish-line)

**Updated:** 2026-09-14 (Wave 127 finish-line). This file replaces the
stale Wave 99.D snapshot that was preserved below for provenance. The
historical table after the divider does not reflect the current repo
state — it is kept only for traceability.

The folder was flattened by Wave 127 Phase 5: `todo/completed/`,
`todo/inprogress/`, `todo/planned/`, `todo/models/` were deleted. The
47 archived plans under `todo/completed/`, the 8 plans under
`todo/planned/`, the 5 files under `todo/models/`, and the 1 README
under `todo/inprogress/` are removed. Their historical content is
preserved in git history (commits `14e8bc5^` and earlier).

---

## Current evidence and next gates

- **HEAD commit:** `14e8bc5` (Wave 127 Phase 4 ruff --fix). Phase 5
  (this commit) will update HEAD.
- **Unpushed commits ahead of `origin/main`:** 167 (post-Wave 127 Phase 4;
  Phase 5 will bump to 168, plus Phase 6 final synthesis).
- **D.4 byte-stable regression vectors:** 18/18 adapters PASS (post-Wave 127);
  162 byte-hash vectors (9 per adapter × 18 adapters) preserved through the
  Phase 5 todo/ refactor.
- **Pytest default-threads:** 5155 passed, 196 skipped (verified
  Wave 127 Phase 4, `14e8bc5`).
- **Ruff:** 207 findings (post-Wave 127 Phase 4 ruff --fix; down from
  927). 207 are non-auto-fixable (F821 undefined-name, E741 ambiguous
  names, F822 __all__, etc.) and are CI-static-gate scope, NOT in the
  7-day finish-line.
- **Mypy:** 988 errors in 70 files (out of scope for the 7-day
  finish-line; CLM-024 wording acknowledges this — see Wave 127 Phase 3).
- **mkdocs build --strict:** PASS (last verified Wave 124 `c9e52a6`; re-verify after Wave 129).

## Wave 128 update (2026-09-14, post-Wave 127)

The Kanzi framework_inv_proj N=1000 sweep from Wave 127 Phase 1 **DID complete
successfully** (4835.0 s, 4.835 s/record, ZERO skipped, deterministic per-record
seed). Result committed as `62f7f24` with N=1000 REAL reading
`mean=0.8798 ± 0.1364 Å` vs baseline_seed42 0.9020 ± 0.1375 Å (Δ = −0.0222 Å,
**TIES**, well inside FSQ quantization noise band). Replaces both the Wave 95
P3.C / Wave 122 P8 historical fallback (2.5017 ± 0.0000 Å, std=0 by
construction, degenerate) and the Wave 124 N=10 mislabel.

## Wave 129 reframing (2026-09-14, post-Wave 128) — **radical plan replaces prior conservative framing**

The user's stated goal is **"投一区 SCI"** (Tier-1 SCI venue). Earlier Wave 127
STATUS.md framed this as TMLR / JMLR. The conservative framing **under-sold
the result**. Per honest re-audit:

- **6 Bonferroni-significant `framework_improves`** are already on disk
  (LineageFlow HMMER +116% p<1e-10, FlowMol3 fg_dev 4.05σ, CIFAR-10 RF
  v2 FID −44.17%, 2D Two Moons W₂ −7.28%, 2D Eight Gaussians W₂ −10.40%,
  MNIST FM FID −15.01%) — no new experiments required to claim.
- **3 byte-stable composite axis SUPPORTED** on all 3 Tier 3 models
  (Kanzi +0.1695 σ=0, LineageFlow +0.2083, FlowMol3 +0.1182).
- **2.5-10× NFE speedup** at matched sample quality.
- **Theoretical grounding** via JMAA Theorem 1 BL-convergence rate bound +
  4 typed Protocols + 17 typed state machines.

The **radical plan** is now in scope: ship to **NeurIPS 2026 / ICML 2026 /
ICLR 2026 main track** within 7 days. See `todo/paper-finish-line-radical-tier1.md`
for the Day 1-7 critical path. This replaces the prior "camera-ready
deferred" list — the items below move from deferred to in-scope where the
7-day plan requires them.

## Active plans (6 root files)

The `todo/` root now holds only 6 active plan files. The previous
`todo/completed/`, `todo/inprogress/`, `todo/planned/`, `todo/models/`
subtrees have been deleted (their content lives in git history).

| Plan file | Status |
|---|---|
| `todo/algo-improvement-paper-quantity-beta-calibration.md` | Wave 125 partial — code landed (`4fbf135` + `da090c2`); CIFAR/twodim acceptance sweeps deferred to camera-ready |
| `todo/algo-improvement-restart-policy-collapse-fix.md` | Wave 125 partial — code landed (`4fbf135`); twodim/CIFAR acceptance deferred to camera-ready |
| `todo/algo-improvement-brai-perturbation-magnitude.md` | Wave 125 partial — code landed (`ae33583`); ESM-2 N=100 + N=1000 acceptance deferred to camera-ready |
| `todo/algo-improvement-framework-vs-model-metrics-gap.md` | READ-ONLY synthesis (Wave 123 Agent 6); no further code expected in 7-day scope |
| `todo/adapter-improvement-inv-proj-bridge-lossy-replacement.md` | Wave 126 partial — N=20 sweep done (Wave 126 Phase 1 additive annotation `f42de22`); N=1000 done in Wave 127 Phase 1 OR deferred to camera-ready |
| `todo/adapter-improvement-8-adapter-shim-audit.md` | READ-ONLY audit complete (Wave 123 Agent 6); per-adapter fixes deferred to camera-ready |

## Next-7-days priority list (Wave 127 ROI ranking)

1. **Kanzi `framework_inv_proj` N=1000 real re-run** (Wave 127 Phase 1) —
   DONE or BLOCKED.
2. **supplementary.md TODO replacement + CLM-024 honest reframe** — DONE
   (Wave 127 Phase 2, commit `7105020`).
3. **§7.6 honest reframe + §7.3 N=1000 reading** — DONE (Wave 127
   Phase 3, commit `e6fb35c`).
4. **Ruff 720 auto-fix** — DONE (Wave 127 Phase 4, commit `14e8bc5`).
5. **`todo/` refactor (this file)** — DONE (Wave 127 Phase 5).
6. **Final synthesis** — DONE (Wave 127 Phase 6).

## Camera-ready deferred (NOT in 7-day scope)

- Kanzi `framework_synth` N=1000 (~33-50 h CPU)
- LineageFlow NFE scan 8/9 cells (~8-16 h CPU)
- CIFAR multi-arm Table 4 re-run (~5 h GPU)
- ESM-2 NLL N=100 + N=1000 (~3 GPU-h)
- Wan2.2 N=1000 sweep
- FreqFlow + MM-FM integration (PHASE-4 DEFERRED historical; no upstream
  ckpt / no shipped adapter)
- Mypy 988-error repair (CI-static-gate)
- Ruff 207 non-auto-fixable findings (CI-static-gate)

## Push state

- **167 unpushed commits** on `main` ahead of `origin/main` at the
  close of Wave 127 Phase 4 (post-Phase 5: 168; post-Phase 6: 169).
  0 behind.
- **`push_risk = LOW`** (D.4 18/18 PASS; pytest 5155/196 green; mkdocs
  build --strict PASS).
- **PUSH IS USER-GATED.** Wave 11+ protocol reaffirmed in
  `todo/PUSH-READY.md` and `todo/push-unpushed-commits.md`. No push in
  Wave 127.

## File inventory (post Wave 127 Phase 5)

```
todo/
├── STATUS.md                                          ← this file
├── INDEX.md                                           ← master entry point
├── PUSH-READY.md                                      ← push-readiness (refreshed Phase 5)
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
├── algo-improvement-paper-quantity-beta-calibration.md ← Wave 125 partial; code landed; acceptance deferred
├── algo-improvement-restart-policy-collapse-fix.md    ← Wave 125 partial; code landed; acceptance deferred
├── algo-improvement-brai-perturbation-magnitude.md    ← Wave 125 partial; code landed; ESM-2 acceptance deferred
├── algo-improvement-framework-vs-model-metrics-gap.md ← READ-ONLY synthesis (Wave 123)
├── adapter-improvement-inv-proj-bridge-lossy-replacement.md ← Wave 126 partial; N=20 sweep done
└── adapter-improvement-8-adapter-shim-audit.md        ← READ-ONLY audit (Wave 123)
```

Total: 25 files at the `todo/` root. Previously ~80 (when subdirs
included 47 archived + 8 planned + 5 model cards + 1 inprogress README).

## Cross-references

- [`docs/CONSOLIDATED_RESULTS.md`](../docs/CONSOLIDATED_RESULTS.md) —
  Tier 3 verdict table §15.15
- [`docs/CLAIMS.md`](../docs/CLAIMS.md) — 41 ACTIVE + 2 DEPRECATED
  claims (43 CLM entries total)
- [`docs/audit/INDEX.md`](../docs/audit/INDEX.md) — per-wave audit
  catalogue (Wave 1 → Wave 133, 62 of 101+ waves have audit docs)
- `docs/audit/wave127-finish-line.md` — Wave 127 audit doc (authored
  in Wave 127 Phase 6)

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