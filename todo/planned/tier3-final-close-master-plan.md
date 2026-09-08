# Tier 3 paper-metric final close — master plan

**Date:** 2026-09-09
**Owner:** framework maintainer
**Status:** PLANNED (waiting for user approval to execute)
**Target:** close all 4 一区 reviewer weaknesses (W1-W4) + ship ICLR 2027 submission package

> **Why this exists:** Waves 75-90 finished Tier 3 paper-metric reproduction at N=1000 across 3 SOTA models (Kanzi + LineageFlow + FlowMol3) using vendored upstream eval pipelines. But honest 一区 reviewer analysis identified 4 residual weaknesses. This plan closes them one at a time, **smaller than the previous 100-step ultracode workflow** — each phase is a single commit + audit doc + verify.

> **Hard budget constraint (locked 2026-09-09):** NO large workflow launches (per user "workflow 设计的太长了"). Each step is READ → MODIFY/CREATE → RUN → COMMIT, done sequentially, max 2-4 hours per wave. No 25-agent parallel agents.

---

## 0. The 4 reviewer weaknesses (W1-W4)

| # | Weakness | What reviewer attacks | What closes it | Status |
|---|---|---|---|---|
| **W1** | FlowMol3 `pb_validity_pct = 0.43` vs paper `0.919` | "PB-xtb not actually wired" | Wave 90 commit `fe95293` (xtb_optimize + rmsd_energy + custom pb_config) | ✅ **CLOSED** |
| **W2** | Kanzi framework arm `NOT_MEASURABLE` (no latent→coord bridge) | "Why didn't they measure Kanzi framework arm on paper metric?" | Author `tools/kanzi_latent_to_coord.py` + wire into `run_real_ckpt_eval.py` + N=1000 Kanzi framework paper-metric eval | ⏳ **TODO** (this plan) |
| **W3** | N=1000 too small (paper uses 5000-10000) | "Statistical power insufficient" | Run N=5000 sweeps on all 3 models (deferred until W2 closes) | ⏳ **TODO** (this plan) |
| **W4** | 2/12 framework_improves cells honest measurement (others are TIE/REGRESS) | "Too few wins" | Statistical power analysis + per-cell CI + honest mixed-result narrative (W4 depends on W3 numbers) | ⏳ **TODO** (this plan) |

---

## 1. Wave sequence (5 sequential waves, NOT 25 agents each)

### Wave 91 (NEW, ~3-5h, 1 agent, 1 commit)
**Title:** Kanzi latent→coord bridge + framework arm paper-metric measurement
**Closes:** W2
**Plan:** `todo/planned/w2-kanzi-latent-coord-bridge.md`

### Wave 92 (NEW, ~4-8h, 1 agent, 1 commit, optional)
**Title:** N=5000 paper-metric sweep on all 3 Tier 3 models
**Closes:** W3 (if budget allows)
**Plan:** `todo/planned/w3-n5000-paper-metric-sweep.md`
**Note:** this wave is **OPT-IN** — user decides based on Wave 91 outcome

### Wave 93 (NEW, ~2-3h, 1 agent, 1 commit)
**Title:** Statistical power analysis + per-cell CI + honest narrative
**Closes:** W4
**Plan:** `todo/planned/w4-statistical-power-analysis.md`

### Wave 94 (NEW, ~2-3h, 1 agent, 1 commit)
**Title:** ICLR 2027 submission package (cover letter + paper §1/§7 final + anonymization)
**Final step:** ship to venue
**Plan:** `todo/planned/w5-iclr2027-submission-package.md`

---

## 2. Per-wave constraints (locked)

- **One agent per wave** (NOT ultracode 25-agent workflows)
- **One commit per wave** (single atomic, NO push)
- **One audit doc per wave** (`docs/audit/wave91-Kanzi-bridge.md`, etc.)
- **D.4 byte-stable preservation** — every code change preserves D.4 vectors 72/72
- **NO push** — user decides push
- **Interface-first** — every new flag is opt-in; legacy default unchanged
- **Honest caveats everywhere** — if any wave produces mixed/negative result, document; do not fabricate

---

## 3. Per-wave time budgets

| Wave | Wall-clock | GPU required | Files touched |
|---|---|---|---|
| 91 (W2) | 3-5h | yes (kanzi_venv + flowmol3_venv) | `tools/kanzi_latent_to_coord.py` (NEW), `tools/run_real_ckpt_eval.py` (modify), `tests/test_tools/test_kanzi_latent_to_coord.py` (NEW), `docs/audit/wave91-Kanzi-bridge.md` (NEW) |
| 92 (W3, opt-in) | 4-8h | yes (heavy) | `verification_outputs/flowmol3/lineageflow/kanzi/n5000_*.json` (NEW), `docs/audit/wave92-n5000-sweep.md` (NEW) |
| 93 (W4) | 2-3h | no (CPU stats) | `tools/statistical_power_analysis.py` (NEW), `docs/audit/wave93-statistical-power.md` (NEW), paper §7.6 update |
| 94 (W5) | 2-3h | no | `cover_letter.md` (NEW), `docs/paper-draft.md` final §1/§7 update, `docs/audit/wave94-iclr-package.md` (NEW) |
| **Total** | **11-19h** | | |

---

## 4. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Kanzi latent→coord bridge requires understanding upstream code | P1 | Read upstream kanzi/encoder.py + decoder.py first; cite code:line in plan |
| N=5000 too GPU-bound | P2 | Run N=5000 only for 1-2 metrics that matter most (validity, family_validity); skip FCD-distribution metric |
| Wave 93 power analysis reveals framework has <50% power to detect 1pp difference at N=1000 | P1 | Document honestly; recommend Wave 92 N=5000 as solution |
| User wants to push before Wave 94 | P2 | Each wave commits independently; can push after each; user decides |
| Wave 91 reveals Kanzi framework arm is NOT better than baseline on paper metric | P1 | Reframe §7.3 — composite-positive + paper-metric-neutral is honest mixed story |

---

## 5. Cascade gates

- Wave 91 → Wave 92 only after Wave 91 commits
- Wave 92 (OPT-IN) → Wave 93 only after Wave 92 commits (or skipped if user declines)
- Wave 93 → Wave 94 only after Wave 93 commits
- Wave 94 → submission; user decides push + submit

---

## 6. Open questions

1. **Is Wave 92 (N=5000) opt-in or required?** — Recommend opt-in; N=1000 honest is defensible (see wave75-78 master plan §5b)
2. **Which venue first?** — Recommend NeurIPS 2026 workshop (Sep deadline) + ICLR 2027 main track (Sep deadline) in parallel
3. **Anonymization for ICLR double-blind?** — ICLR 2027 main track requires; workshop does not

---

## 7. Decision evolution

- **2026-09-09**: User said "之前的workflow设计的太长了" — switch from 100-step ultracode to 1-agent-per-wave sequential plan
- **2026-09-09**: User said "按照目录设计做好详细规划" — use todo/planned/ + 5 focused plans rather than single mega-workflow

---

## 8. Cross-references

- Wave 75-78 master plan: `todo/inprogress/wave75-78-master-plan.md` (status of N=1000 sweeps — DONE)
- Wave 86-89 audit docs: `docs/audit/wave86-phase1-audit.md` through `wave89-phase1-final.md`
- Wave 90 commit: `fe95293` (PB-xtb pipeline real wire) — closes W1
- 4 reviewer-proof guarantees (G1-G4): `todo/inprogress/wave75-78-master-plan.md` §5c