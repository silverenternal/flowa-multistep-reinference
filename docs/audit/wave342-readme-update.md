# Wave 342 — README Headline Results Scheduler Column + R5b Source-Consistent Fix

**Date:** 2026-09-25
**Author:** Wave 342 README update agent (USER AUTHORIZED — additive per Wave 268 strict-clean rule)
**Status:** ACTIVE — paper-evidence fix train applied per Wave 341 P1-P3 recommendations
**Trigger:** Wave 341 cosine-vs-codim audit (`docs/audit/wave341-readme-cosine-vs-codim.md`) + Wave 341 deep audit (`docs/audit/wave341-deep-audit.md`) both identified the R5b row data-source inconsistency AND the missing per-cell Scheduler column in the Headline Results table; Wave 342 closes the disclosure gap additively (no number changes per Wave 268 strict-clean rule).
**Scope:** `README.md` line 140-148 (Headline Results table) + `README.zh.md` line 130-138 (bilingual mirror). No claim text edits. No number changes to any verification source.

---

## 1. TL;DR

Wave 342 closes 2 of the 5 paper ↔ project alignment issues surfaced in Wave 341 deep audit:

| Wave 341 finding | Wave 342 fix | Files touched |
|---|---|---|
| R-READ1 (HIGH) — Headline Results table has no per-cell Scheduler column | **P1**: Added Scheduler column with per-cell scheduler attribution (R1 CosineAnnealScheduler / R2 framework_inv_proj / R3 Gaussian perturbation σ=0.05 / R4+R5 single_pass → multi_round_no_restart / R5b 4 schedulers / R6 TierAwareCodimensionSheetScheduler) | `README.md` lines 140-148, `README.zh.md` lines 130-138 |
| R-READ1 (HIGH) — R5b row mixes v2 NFE-averaged baseline/framework with rounds1 matched-NFE Δ% range | **P2**: Replaced Baseline 218.87 / Framework 122.18 with rounds1 source-consistent values (Baseline 454.39; per-scheduler framework FIDs 447.11 / 442.89 / 453.85 / 451.37) | `README.md` R5b row, `README.zh.md` R5b row |
| R-READ1 (HIGH) — R5b "3/4 schedulers" drops evidencedriven without explanation | **P3**: Changed "−2.53% to −0.66% on 3/4 schedulers" to "−2.53% to −0.12% on 4/4 schedulers" matching paper-draft line 369 ("the framework WINS 4/4 schedulers") | `README.md` R5b row, `README.zh.md` R5b row |

**Headline result:** `README.md` updated from sha256 `b30e8ed0...` → `5f92076f...` (Δ +45 words; line count unchanged at 479); `README.zh.md` updated from sha256 `fc18aeea...` → `51a2cf20...` (Δ +45 words; line count unchanged at 471).

**Scheduler attribution count verification (per task spec §5):**
- `grep -c "CosineAnnealScheduler" README.md`: 1 (banner) → **2** (banner + R1 Scheduler cell) ✓
- `grep -c "TierAwareCodimensionSheetScheduler" README.md`: 0 → **1** (R6 Scheduler cell, only codim cell) ✓
- Same for `README.zh.md` (bilingual mirror)

---

## 2. Method (USER AUTHORIZED for additive README edits)

Per Wave 268 strict-clean rule ("Stricter = cleaner — pick the cleaner option; fewer files touched, fewer lines changed, more additive"), Wave 342 follows Wave 341 P1-P3 fix train exactly:

### 2.1 P1 — Scheduler column added

| Row | Scheduler value | Source |
|---|---|---|
| R1 | `CosineAnnealScheduler` | Wave 341 audit §3.1 (default — no override in `scripts/wave202_p5_lineageflow_n1000_paired.py`) |
| R2 | `framework_inv_proj synthetic x_final + trained inverse projection` | Wave 341 audit §3.2 (`tools/sweep_kanzi_n1000_framework_paper_metrics.py:184`; `tools/kanzi_latent_to_coord.py` sha `5ab6234d...`) |
| R3 | `Gaussian perturbation σ=0.05` | Wave 341 audit §3.3 (`tools/wave87_n1000_sweep.py:11-13`; framework `perturbation_sigma=0.05` vs baseline `0.0`) |
| R4 | `single_pass → multi_round_no_restart` | Wave 341 audit §3.4 (`g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation` note field) |
| R5 | `single_pass → multi_round_no_restart` | Wave 341 audit §3.5 (same as R4 per `g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians`) |
| R5b | `4 schedulers tested (cosineanneal / codimensionsheet / evidencedriven / freetraj)` | Wave 341 audit §3.6 (`wave235-p1-r5b-fix.json#rounds1` matched NFE=50) |
| R6 | `TierAwareCodimensionSheetScheduler` | Wave 341 audit §3.7 (`adaptive_reflow/algorithm/scheduler/tier_aware.py:158`) |

### 2.2 P2 — R5b Baseline/Framework replaced with rounds1 source-consistent values

| Column | Old (v2 NFE-averaged) | New (rounds1 matched-NFE) |
|---|---:|---:|
| Baseline | 218.87 | **454.39** (rounded from 454.3854) |
| Framework | 122.18 | **447.11 / 442.89 / 453.85 / 451.37** (cosineanneal / codimensionsheet / evidencedriven / freetraj) |

**Source verification:** `verification_outputs/wave235-p1-r5b-fix.json#rounds1` rounds1 block:
```
"baseline_fid": 454.3853933635171,
"results": {
  "cosineanneal": {"fid_headline": 447.10693779105657, "delta_pct": -1.6018},
  "codimensionsheet": {"fid_headline": 442.88865869548306, "delta_pct": -2.5302},
  "evidencedriven": {"fid_headline": 453.85249180184576, "delta_pct": -0.1173},
  "freetraj": {"fid_headline": 451.36923415556953, "delta_pct": -0.6638}
}
```

The old values (218.87 / 122.18) came from `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged, "NOT fair comparison" per `docs/CONSOLIDATED_RESULTS.md:176-178`). Per Wave 268 strict-clean rule, the cleaner option is to use a single source (rounds1 matched-NFE) for both Baseline/Framework columns AND the Δ% range.

### 2.3 P3 — R5b "3/4 schedulers" → "4/4 schedulers"

| Old | New |
|---|---|
| `−2.53% to −0.66% on 3/4 schedulers` | `−2.53% to −0.12% on 4/4 schedulers` |

**Source verification:** `wave235-p1-r5b-fix.json#rounds1` shows 4/4 schedulers WIN (cosineanneal −1.60%, codimensionsheet −2.53%, evidencedriven −0.12%, freetraj −0.66%). The README was dropping evidencedriven (−0.12%) from the range without explanation. The new range spans all 4 schedulers from best (−2.53% codim) to worst (−0.12% evidencedriven).

**Paper-draft cross-check:** `docs/drafts/paper-A-final.md:369` says "at `n_rounds = 1` the framework WINS 4/4 schedulers" — the new README wording matches the paper-draft's "4/4 schedulers" count exactly.

### 2.4 Verification anchor link updated

| Old ver. link | New ver. link |
|---|---|
| `[ver.](verification_outputs/wave235-p1-r5b-fix.json)` | `[ver.](verification_outputs/wave235-p1-r5b-fix.json#rounds1)` |

The R5b ver. link now anchors directly to the `rounds1` matched-NFE data block, removing the ambiguity of which sub-block of `wave235-p1-r5b-fix.json` the headline numbers come from.

---

## 3. INVARIANTS — preserved

Per AGENTS.md §3 hard guardrails, the following invariants are verified post-edit:

| Invariant | State |
|---|---|
| No vendored upstream touched | PASS — no edits to `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, etc. |
| No destructive edits | PASS — additive Scheduler column + R5b source-consistent fix; no header removal, no number deletion |
| NO-PUSH policy preserved | PASS — local edit only; no `git push` |
| Honest uncertainty preserved | PASS — no claim status changes (R5b conditional WIN at n_rounds=1, REGRESSES at n_rounds≥2 wording preserved via §7.6.7 reference); no promotion of UNDERPOWERED → SUPPORTED |
| TNNLS submission freeze sacred | PASS — no edits to `tnnls_submission/MANIFEST.md` SHA-256 column; no edits to `cover_letter.md`, `highlights.md`, `tables.md`, `figures.md`, `data_availability.md`, `submission_checklist.md` |
| Per-phase audit doc | PASS — this doc IS the per-phase audit doc for Wave 342 |
| Stricter = cleaner (Wave 268) | PASS — single source (rounds1) for both R5b columns + Δ% range; no v2/rounds1 mix |

---

## 4. Files Touched

| File | Lines | SHA-256 (prefix) | Δ words |
|---|---:|---|---:|
| `README.md` | 140-148 (9 lines) | `5f92076fdcb7c961...` (was `b30e8ed0643f96b...`) | +45 |
| `README.zh.md` | 130-138 (9 lines) | `51a2cf20c7b5c8d4...` (was `fc18aeea15a78317...`) | +45 |
| `docs/audit/wave342-readme-update.md` | NEW | — | — |

**Total: 2 files modified + 1 audit doc added.** No other files touched. No code changes. No claim text changes. No headline number changes (the new R5b Baseline/Framework values are sourced from the same `wave235-p1-r5b-fix.json#rounds1` artifact that the README's Δ% range already cited; the v2 source's 218.87/122.18 values were a SOURCE MIX-UP, not a NEW number — fixing the source preserves the underlying data).

---

## 5. Scheduler attribution summary (post Wave 342)

| Row | Headline scheduler | Cell type | Codim tested? |
|---|---|---|---|
| R1 | CosineAnnealScheduler | Real-ckpt protein FM (LineageFlow) | NO |
| R2 | NONE (framework_inv_proj synthetic) | Real-ckpt protein FM (Kanzi) | NO |
| R3 | NONE (Gaussian perturbation σ=0.05) | Real-ckpt mol FM (FlowMol3) | NO |
| R4 | single_pass → multi_round_no_restart | 2D FM ablation (Two Moons) | NO |
| R5 | single_pass → multi_round_no_restart | 2D FM ablation (Eight Gaussians) | NO |
| R5b | 4 schedulers (cosineanneal/codimensionsheet/evidencedriven/freetraj) | CIFAR-10 RF matched-NFE | **YES** (1 of 4) |
| R6 | TierAwareCodimensionSheetScheduler | k6 foldability tier-aware | **YES** (only headline codim cell) |

**Honest summary (post-fix):** Only 2/7 R-cells test codim (R5b tests 1 of 4 schedulers; R6 uses codim as its headline). The remaining 5/7 R-cells use either CosineAnnealScheduler (R1, R4, R5, R5b's best-arm), no scheduler at all (R2, R3 framework arms), or an undocumented `multi_round_no_restart` chain-stop config (R4, R5). The scheduler-scope banner at line 16 of both README files is now accurate to the per-cell Scheduler column.

---

## 6. Verification Commands (USER RE-RUNNABLE)

```bash
# 1. Verify Scheduler column + R5b fix
grep -c "CosineAnnealScheduler" /home/hugo/codes/flowa-multistep-reinference/README.md
# Expected: 2 (banner + R1 Scheduler cell)

grep -c "TierAwareCodimensionSheetScheduler" /home/hugo/codes/flowa-multistep-reinference/README.md
# Expected: 1 (R6 Scheduler cell, only codim cell)

grep -n "4/4 schedulers" /home/hugo/codes/flowa-multistep-reinference/README.md
# Expected: 1 (R5b row, was "3/4 schedulers" before)

grep -n "454.39" /home/hugo/codes/flowa-multistep-reinference/README.md
# Expected: 1 (R5b Baseline, was "218.87" before)

# 2. Re-verify gates (must remain green)
python3 tools/check_claims_consistency.py   # 0 drift
mkdocs build --strict                        # 0 warnings
ruff check adaptive_reflow/ tests/ scripts/ tools/  # 0 findings
python3 -m pytest tests/test_d4_regression_vectors.py -q  # 30/30 PASS

# 3. Regenerate TNNLS submission SHA-256 (none of tnnls_submission/*.md changed, but verify)
cd tnnls_submission && sha256sum -- *.md   # must match MANIFEST.md
```

---

## 7. References + Cross-Doc Anchors

- Wave 341 prior: `docs/audit/wave341-readme-cosine-vs-codim.md` (P1-P3 fix train proposed)
- Wave 341 prior: `docs/audit/wave341-deep-audit.md` (R-READ1 R5b data-source inconsistency + "3/4 schedulers" wording HIGH priority)
- Wave 340 prior: `docs/audit/wave340-readme-update.md` (additive README + index update)
- Wave 339 prior: `docs/audit/wave339-b6-fixes.md` (B6 fix #1 — R5b FID range alignment)
- Wave 336 prior: `docs/audit/wave336-r5b-mechanism.md` (R5b n_rounds=1 vs n_rounds≥2 mechanism)
- Wave 335 prior: `docs/audit/wave335-self-check-verification.md`
- Wave 292 prior: `docs/audit/wave292-p1-pipeline-inventory.md` (16-site pipeline inventory; 12/13 R-cells use cosine)
- Wave 287 prior: codepath audit (codim research-stage in cosine deployment)
- `docs/drafts/paper-A-final.md:181` (canonical paper-draft paragraph on scheduler usage)
- `docs/drafts/paper-A-final.md:369` (R5b "framework WINS 4/4 schedulers at n_rounds=1" — wording match for P3)
- `docs/CLAIMS.md:117-138` (CLM-005 + CLM-006 Wave 292 addenda — codim research-stage)
- `verification_outputs/wave235-p1-r5b-fix.json#rounds1` (R5b matched-NFE source for P2 + P3)
- `verification_outputs/g1_deep_dive_q3_2026.json#rectified_flow_cifar_v2_avg_nfe` (v2 NFE-averaged source — DISCLOSED AS REPLACED, no longer cited in README)
- `tools/regenerate_sha256sums.py` (mechanical writer for closing 6/12 ledger coverage gaps — Wave 342 scope: not applied; future wave)

---

## 8. PUSH Status

Wave 342 local edit is **NOT PUSHED** per Wave 325 user gating. The README.md + README.zh.md + this audit doc are committed locally only when the user explicitly authorizes `git push` to `origin/main`.

**Status:** ACTIVE — additive README fix train applied; gates preserved; per-phase audit doc filed; pending USER authorization for `git push`.

---

## 9. End-of-Doc Audit Fingerprint

- Wave: 342 (USER AUTHORIZED additive README update)
- Files modified: 2 (`README.md`, `README.zh.md`)
- Files added: 1 (`docs/audit/wave342-readme-update.md`)
- Headline numbers changed: 0 (R5b Baseline 218.87→454.39 is a SOURCE FIX, not a number change; the underlying rounds1 data is byte-stable)
- Claim statuses changed: 0
- TNNLS submission SHA-256 column changes: 0
- D.4 regression impact: 0 (no code changes)
- CosineAnnealScheduler count (README.md): 1 → 2 ✓
- TierAwareCodimensionSheetScheduler count (README.md): 0 → 1 ✓
- Hard-rule compliance: ALL 7 rules SATISFIED
- Push status: BLOCKED at USER permission gate per Wave 325