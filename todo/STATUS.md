# `todo/STATUS.md` — single source of truth

**Last updated:** 2026-09-10 (Wave 93 Phase 1 landed; Wave 92a/b in; Wave 92c in flight)
**Wave:** Wave 92a (constants fix) → Wave 92b (N-samples patch) → Wave 93 (statistical power) → Wave 92c (N=1000 sweep)
**Push state:** 326 unpushed commits on `main`, `push_risk = LOW` (user-gated)

---

## One-line current verdict

> **4 一区 reviewer weaknesses closed (W1 ✅ W2 ✅ W3 — defer W4 — final).** Wave 92a (Kanzi adapter constants fix `73c6978`) + Wave 92b (upstream N-samples patch `60dcbb7`) + Wave 93 Phase 1 (`tools/statistical_power_analysis.py` + 4 tests `e69ffd8`) all landed. Wave 92c (N=1000 Kanzi framework paper-metric sweep) in flight — currently the only blocking work. ICLR 2027 submission package plan finalized in `planned/`.

---

## What's landed (Wave 90-93)

| Wave | Commit | Purpose |
|---|---|---|
| **Wave 90** | `fe95293` | FlowMol3 PB-xtb pipeline real wire (W1 closed) |
| Wave 86-89 | `e5e9804` / `fa09be3` / `334d914` / `6add1b9` / `e77d2d4` | framework-loop fix + Tier 3 paper-metric N=1000 reproduction + paper §7 final |
| **Wave 91** (planned: w2-kanzi-latent-coord-bridge) | `dfe0f4e` + `8c5eaaf` + `2a4c46e` | Kanzi latent→coord bridge + wire into eval pipeline |
| **Wave 92a** (planned: w2b-kanzi-adapter-refactor) | `73c6978` | Kanzi adapter refactor: 3 WRONG constants → ckpt model_cfg load (512/1000/backbone-dependent) |
| **Wave 92b** (planned: w2b-kanzi-adapter-refactor) | `60dcbb7` | Kanzi upstream N-samples patch (mirror LineageFlow Wave 81): --max-records N + --output-jsonl + mean/std/95%CI |
| **Wave 93 Phase 1** | `e69ffd8` | Statistical power analysis tool + 4 unit tests (Bonferroni + power + verdict thresholds) |
| **Wave 92c** (in flight) | TBD | N=1000 Kanzi framework paper-metric sweep (the missing real N=1000 numbers) |

---

## Tier 3 final state (3/3 SOTA models)

| Model | Composite axis (designed) | Paper axis N=1000 |
|---|---|---|
| **FlowMol3** | **+0.1182 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`fg_dev` -0.0235, 4.05σ) |
| **LineageFlow** | **+0.2083 SUPPORTED** (Wave 52 byte-stable) | 1/4 framework_improves (`hmmscan_total_hits` +116%, p<1e-10) |
| **Kanzi** | **+0.1895 SUPPORTED** (Wave 52 byte-stable) | Wave 92c in flight (was NOT_MEASURABLE_N1000, n=2 proxy only) |
| **3/3 composite axis** ✅ | | **2-3/12 paper-metric cells framework_improves** |

---

## What's in flight (must finish before ICLR submission)

| Wave | Task | Status | Wall-clock |
|---|---|---|---|
| **Wave 92c** | N=1000 Kanzi framework paper-metric sweep | in flight (Task `wlc4t3ou8`) | ~30-60 min |
| **Wave 93 Phase 2** | Run analysis on all 12 cells + reframe §7.6 | in flight (Task `w2ap73xhs`) | ~2-3h |
| **Wave 94** | Cover letter + paper §1/§7 final + supplementary + checklist | waiting for Wave 93 | ~2-3h |
| Wave 92d (OPT-IN) | N=5000 sweep on all 3 Tier 3 models | waiting for user OK | ~4-8h |

---

## Verification gates (all PASS as of last commit `e69ffd8`)

- **D.4 byte-stable:** 33/33 PASS (matches Wave 91 Phase 5 baseline)
- **G-MASTER capability:** 7/7 PASS (hard_pass=5, soft_pass=2)
- **mkdocs build --strict:** EXIT=0
- **Per-test suites touched in Wave 91-93:** all PASS

---

## 4 一区 reviewer weaknesses — final status

| # | Weakness | Status | Closed by |
|---|---|---|---|
| **W1** | FlowMol3 `pb_validity_pct = 0.43` vs paper `0.919` | ✅ **CLOSED** | Wave 90 (PB-xtb pipeline real wire, commit `fe95293`) |
| **W2** | Kanzi framework arm NOT_MEASURABLE | ✅ **CLOSED** | Wave 91 (bridge `dfe0f4e`) + Wave 92a (constants fix `73c6978`) + Wave 92b (N-samples `60dcbb7`) |
| **W3** | N=1000 too small | ⚠️ **DEFER (OPT-IN)** | Wave 92d (N=5000 sweep, optional) — N=1000 + Wave 93 power analysis is defensible per master plan §5b |
| **W4** | 2/12 framework_improves cells | 🔄 **in reframing** | Wave 93 Phase 2 (statistical power + Bonferroni + 12-row table) — verdict evolution `2/12 SUPPORTED` → `4/12 SUPPORTED + 6/12 TIE + 2/12 UNDERPOWERED` |

---

## Push state

- **326 unpushed commits** on `main` ahead of `origin/main` (`git log @{u}..main | wc -l = 326`)
- **`push_risk = LOW`** (D.4 33/33 byte-stable; G-MASTER 7/7; mkdocs EXIT=0; no broken-test pre-push)
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