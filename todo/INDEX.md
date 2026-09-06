# `todo/INDEX.md` — Master entry point

**Date:** 2026-09-07
**Purpose:** curated entry point for the 56 files in `todo/`. New readers
should read the [Reading order](#reading-order-for-new-readers) section
first. Each section below groups files by purpose and links the most
important ones to start with.

---

## Current state summary

> **As of 2026-09-07: 5/5 G-MASTER PASS, 41/41 CLM claims, 18/18 regression
> vectors, 107 algorithm uplifts. Tier 3: Kanzi + LineageFlow
> `composite_verdict = framework_improves`, FlowMol3 metric-axis
> implementation closed (measurement in flight). 211+ unpushed commits,
> `push_risk` LOW.**

| Bucket | Status (2026-09-07) |
|---|---|
| **G-MASTER gate** | 5/5 PASS (G.1 / G.2 / G.3 / G.4 / G.6 / G.7) + G.5 SOFT-FAIL |
| **CLM claims** | 41/41 = 100 % test-coupled (target ≥ 70 % cleared with margin) |
| **D.4 regression vectors** | 18/18 = 100 % pinned across all 18 integrated adapters |
| **D.5 conformance battery** | 90/90 passed (8 checks × 14 adapters) |
| **Algorithm uplifts** | 107 hit target (Round 1 + Round 2) |
| **B.7 property-based** | ≥ 40 % ratio achieved across `tests/test_property_based/` |
| **C.7 SBC** | 6/6 stochastic algorithms pass χ² at N=200 + N=1000 |
| **Tier 3 real-ckpt** | Kanzi + LineageFlow `composite_verdict = framework_improves`; FlowMol3 composite landed (Wave 53) + measurement in flight |
| **Push state** | 211+ unpushed commits; `push_risk = LOW` (per `wave46-master-synthesis.md` §6) |
| **MUST-1..5** | MUST-1/2/3/4 = PASS; MUST-5 = user-gated push |

**Tier 3 model roster (active):** Kanzi (ICLR 2026, protein) · LineageFlow (ICML 2026, protein) · FlowMol3 (molecule, in flight).
**Tier 3 model roster (deferred per 2026-09-05 directive):** FreqFlow · MM-FM (no upstream ckpt / no shipped adapter).

**Open gaps (post-push follow-ups):**
1. FlowMol3 real-ckpt eval (`composite_verdict` measurement runs in flight; final numbers depend on Wave 53 audit)
2. FreqFlow / MM-FM (no upstream ckpt — indefinitely deferred)
3. MUST-3 formal flip to PASS in `framework-freeze-checklist.md` (5+ adapters on core; final verify pending)
4. Tier 3 paper §Tier 3 + figure regeneration after Wave 53 closes
5. CI dashboard — composite-aware check on `tools/capability_audit.py`

See `wave46-master-synthesis.md` §7 for the full risk register and
`wave46-master-synthesis.md` §8 for the full follow-up list.

---

## Sections

### 1. Plan files — `algo-improvement-*.md` (26 files)

All 26 algorithm-improvement plan files. **All 26 are CLOSED** (commit
landed; status in `STATUS.md`). Indexed here for traceability.

| File | Status | Commit / Wave |
|---|---|---|
| `algo-improvement-assert_adapter_compliance.md` | CLOSED Wave 38 | `f7ee3ae` |
| `algo-improvement-conformance-battery.md` | done Wave 15 C | `4d30f41` |
| `algo-improvement-convergence-order.md` | done Wave 18 C.6 + W20 P1 | `d7cd65b`, `53e5d52` |
| `algo-improvement-D4-regression-vectors.md` | CLOSED Wave 38 | `b88b32f` |
| `algo-improvement-E1-claim-test-coupling-batch2.md` | CLOSED Wave 38 | `7da571c` |
| `algo-improvement-env-hash.md` | done Wave 15 P1 | `43b862d` |
| `algo-improvement-expecttest-adoption.md` | CLOSED Wave 38 | `5e1731f` |
| `algo-improvement-f2-reproduction.md` | done Wave 15 F | `e397528` |
| `algo-improvement-failure-modes.md` | done Wave 17 P2 (Algo D) | — |
| `algo-improvement-FlowMol3V2-restart-fix.md` | CLOSED Wave 38 | `b9ef18b` |
| `algo-improvement-hf-model-card-pipeline.md` | CLOSED Wave 38 | `7cbf085` |
| `algo-improvement-host-fingerprint.md` | CLOSED Wave 38 | `d55b601` |
| `algo-improvement-hypothesis-derandomize.md` | CLOSED Wave 38 | `15621b7` |
| `algo-improvement-mkdocs-strict-nav.md` | CLOSED Wave 38 | `0674ac8` |
| `algo-improvement-mutation-apply-survivor.md` | CLOSED Wave 38 | `5e1731f` |
| `algo-improvement-mutation-testing.md` | done Wave 18 F.6 | `6ec3385` |
| `algo-improvement-no-scipy-raise.md` | CLOSED Wave 38 | `89c088f` |
| `algo-improvement-operating-regime.md` | done Wave 17 P3 (CRITICAL gap) | — |
| `algo-improvement-paper-quantities-threading.md` | CLOSED Wave 38 | `ff56e55` |
| `algo-improvement-planar-bl-repoint.md` | done Wave 14 A | `6d12744` |
| `algo-improvement-property-based-testing.md` | done Wave 17 P1 (B.7) | — |
| `algo-improvement-rate-bound.md` | done Wave 15 B | `f9d34e1` |
| `algo-improvement-sbc.md` | done Wave 18 C.7 | `c0e2fe2` |
| `algo-improvement-stochastic-fm-orphan.md` | done Wave 39 | (deleted) |
| `algo-improvement-traceability-hardening.md` | done Wave 15 A | `3ead25f` |
| `algo-improvement-uplift-isolation.md` | done Wave 14/15 rescue | `a1f8650` |

### 2. Phase plans — `PHASE-1..4`

| File | Status | Wave |
|---|---|---|
| `PHASE-1-framework-and-theory.md` | done | Wave 11 + Wave 12 (commit `ebc0550` + `e0238ab`) |
| `PHASE-2-model-complexity-analysis.md` | done | Wave 19 P1A1 (`a6e574d`; 3 per-model analysis files + RANKING.md) |
| `PHASE-3-glue-layer-improvement.md` | done | Wave 24 + Wave 38 + Wave 39 (4 core glue modules + Protocol enforcement) |
| `PHASE-4-model-integration-iteration.md` | in_progress | Kanzi + LineageFlow active; FreqFlow + MM-FM DEFERRED |

### 3. Wave result validations

| File | Status | Outcome |
|---|---|---|
| `wave10-result-validation.md` | done | LineageFlow integration shipped; "any FM improves" claim partial-evidence (binary saturation caveat) |
| `wave11-result-validation.md` | done | JMAA theory-driven refactor shipped; 10 Protocol surfaces + 52 conformance tests |
| `wave12-result-validation.md` | done | 7 A1 audit fixes (`e0238ab`, pushed) |
| `wave13-metrics-research-result.md` | done | framework-internal-metrics rev 2 (research-aligned + adversarial verify) |
| `wave14-result-validation.md` | done | Algorithm improvement A + 9 baseline audits; Theorem1StatementChecker re-pointed (`6d12744`) |

### 4. Master synthesis docs

| File | Purpose |
|---|---|
| `wave43-problems-review.md` | 6 concrete problems after Wave 41/42 + Wave 43 ultracode plan |
| `wave45-adapter-fix-master-plan.md` | 3 adapter-layer fixes (Kanzi GPT-prior restart + entropy metric + LineageFlow classifier-aware restart) + F-1/F-2/F-3 prereqs |
| `wave46-master-synthesis.md` | **MASTER** — composite benchmark formula + LineageFlow glue + push-ready state (start here for the Tier 3 close-out story) |
| `gap-plan-wave32.md` | 13 gap plans synthesized from Wave 32 Agent A/B/C audits; **all 14 gaps CLOSED in Wave 38** |

For new readers of the recent Tier 3 work, **`wave46-master-synthesis.md`
is the single best entry point** — it explains the 4 pathologies, the
composite benchmark formula, the glue layer abstraction, and the push-ready
state in one document.

### 5. Model-specific — `models/`

| File | Status | Venue / Domain |
|---|---|---|
| `models/README.md` | template | — |
| `models/RANKING.md` | done (Wave 19) | Integration-difficulty ranking (FreqFlow / MM-FM / Kanzi) |
| `models/kanzi.md` | active | ICLR 2026, protein flow-AE (505 MB ckpt downloaded) |
| `models/lineageflow.md` | active (Wave 10 BLOCKED → Wave 45 unblocked) | ICML 2026, protein (10.5 GB ckpt, 657M ESM-2-650M) |
| `models/freqflow.md` | done (PHASE-2 analysis); DEFERRED in PHASE-4 | CVPR 2026, image SiT-XL/2 (no upstream ckpt) |
| `models/mm-fm.md` | done (PHASE-2 analysis); DEFERRED in PHASE-4 | CVPR 2026, image DiT-XL/2 (no shipped adapter) |

### 6. Operational & governance

| File | Purpose |
|---|---|
| `STATUS.md` | **single source of truth** — auto-updated per wave; current state + last completed wave + next actions |
| `framework-freeze-checklist.md` | MUST-1..5 freeze criteria with current PASS/FAIL status |
| `GATES.md` | master gate definitions (binding rule: every todo/ task must have an acceptance gate) |
| `PUSH-READY.md` | push-readiness summary (2026-09-05: VERDICT READY, user-gated) |
| `push-unpushed-commits.md` | push-protocol + Wave 12 push log (since superseded by 211+ unpushed commits) |
| `decisions.md` | architecture decision log D-001.. (append-only) |
| `lessons-learned.md` | cross-cutting patterns LL-001.. (append-only) |
| `RISK-REGISTER.md` | forward-looking risks + mitigations (different from `lessons-learned.md`) |
| `EXECUTION-PLAN.md` | pending tasks broken into ~110 atomic subtasks (15-60 min each) |
| `TIMELINE.md` | phase durations + "project done" definition |
| `LOOP.md` | per-model lifecycle + iteration mechanism + stop conditions |
| `framework-internal-metrics.md` | rev 2 ship-ready; A-F metric groups + entry gates per phase |
| `framework-internal-metrics-rev3-plan.md` | rev 3 plan (research-aligned + capability group G folded in) |
| `framework-capability-metrics.md` | group G capability metrics (folded into rev 3 plan) |
| `paper-writeup.md` | paper writeup task (done Wave 19 P2 — `2f436f1`) |
| `rerun-wave10-with-refactored-framework.md` | Wave 19 P1A2 rerun (done; verdict=not_supported, decision metric saturated) |

---

## Reading order (for new readers)

1. **`README.md`** — directory structure + when to add new files + current focus
2. **`STATUS.md`** — current state + last completed wave + next actions
3. **`framework-freeze-checklist.md`** — MUST-1..5 freeze criteria (what "done" means)
4. **`wave46-master-synthesis.md`** — master synthesis of the Tier 3 / composite-benchmark / push-ready story (the load-bearing narrative)

After those four, branch by interest:
- **Algorithm / theory depth:** `PHASE-1-framework-and-theory.md` → `framework-internal-metrics.md` → `wave46-master-synthesis.md` §3 (composite formula)
- **Per-model glue:** `models/RANKING.md` → the specific `models/<name>.md` → `PHASE-3-glue-layer-improvement.md`
- **Push protocol:** `PUSH-READY.md` → `push-unpushed-commits.md` → `RISK-REGISTER.md`
- **Decision history:** `decisions.md` → `lessons-learned.md` → `RISK-REGISTER.md`

---

## Cross-references

- `todo.json` (project root) — machine-readable task index
- `git log origin/main..HEAD` — 211+ unpushed commits (Wave 11 → Wave 54)
- `docs/CONSOLIDATED_RESULTS.md` — single source of truth for experimental evidence
- `docs/CLAIMS.md` — 41 documented CLM claims (all 41 test-coupled)
- `docs/baseline-audit-report.md` — 9 metrics + Wave 30+ re-audit
- `framework-freeze-checklist.md` — MUST-1..5 with current PASS/FAIL
- `verification_outputs/capability_audit_q3_2026.json` — current capability gate values (G.1..G.7)
- `docs/theory/theorem1_rate_bound.md` — NEW (Wave 15 B)
- `env_hash.txt` — NEW (Wave 15 Phase 1)
- `requirements-lock.txt` — NEW (Wave 15 Phase 1)
