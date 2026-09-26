# Wave 364 P1 — Gap-selection memo (8 high-impact gaps from the 39-gaps inventory)

**Date:** 2026-09-27
**Author:** Wave 364 P1 gap-selection-memo agent (USER AUTHORIZED, NO PUSH)
**Wave:** 364 P1 (planning memo — ADDITIVE documentation, NO source code changes)
**Scope:** Enumerate the 8 high-impact gaps from the 39-gaps inventory that Wave 364 will address additively (G3, G11, G15, G20, G31, G32, G34, G38). For each gap, document: gap_id + severity + paper-section / tnnls-section + fix-proposal + files-to-touch.

---

## 1. Purpose (smallest next action first)

The Wave 364 wave is a **gap-close-out wave** that addresses a 39-gaps inventory (the full list of pre-submission editorial / consistency gaps identified at the Wave 363 P2 master-verifier cycle). Of those 39, 8 are high-impact gaps that survive the Wave 268 strict-clean ADDITIVE-only filter — i.e. each can be closed by an ADDITIVE paragraph / section append / cross-reference without modifying any existing number, status label, USER_TO_FILL placeholder, or vendored-upstream byte. This memo enumerates the 8 selected gaps with their fix-proposals and the files-to-touch, so that downstream Wave 364 sub-agents (P2 = G3 close, P3 = G11 close, P4 = G15 close, P5 = G20 close, P6 = G31 close, P7 = G32 close, P8 = G34 close, P9 = G38 close, in gap-id order) can each operate on their respective gap without re-deriving the fix-spec from the audit trail.

**Smallest next action:** Wave 364 P2 begins the G3 close-out using the fix-proposal in §3.3 below.

---

## 2. Source 39-gaps inventory (status as of 2026-09-27)

The 39-gaps inventory is the consolidated set of pre-submission editorial / consistency gaps identified at the Wave 363 P2 master-verifier cycle. **The inventory is currently dispersed across the codebase** — the canonical sources are:

1. **`docs/drafts/paper-A-final.md`** — inline gap-closure attributions at line 284 (G34), line 370 (G20), line 519 (G3), line 543 (G11). Four gaps are partially closed inline (the section appendices are present, the canonical-statement marker is present); four gaps (G15, G31, G32, G38) are listed in this memo as PENDING close-out.
2. **`docs/audit/wave364-g31.md`** — Wave 364 G31 audit doc (closes G31: 11-cell verdict distribution canonical disaggregation statement at §7.2 of `paper-A-final.md`).
3. **`docs/audit/wave364-g32.md`** — Wave 364 G32 audit doc (closes G32: cover letter §0 date refresh to 2026-09-25).
4. **`docs/drafts/paper-A-final.md` line 284** — Wave 364 G34 closes the Wave 268 strict-clean rule ADDITIVE definition at §3.9 (the inline section header already carries the "Wave 364 G34" attribution marker).
5. **`docs/drafts/paper-A-final.md` lines 519 + 543** — Wave 364 PG3 (line 519) and Wave 364 P G11 (line 543) close the §6.6.1 slope-scaling terminology + proven-claim clarification (G3) and the R5b honest-framing (G11).

Of the 39 gaps, **8 are selected as high-impact for Wave 364 close-out** (the 8 enumerated in §3 below). The remaining 31 are scoped as either: (a) USER-gated (e.g. cover_letter.md USER_TO_FILL fill is per-author, not per-agent); (b) deferred to camera-ready (R3 N=1000 paired full-stack re-verification per §10.5; R6 live-GPU 3-seed × N=1000 paired full-stack re-verification per §10.5; R5a n=30/n=100 paired-t confirmation per `todo/RISK-REGISTER.md` R-022; FreqFlow `nnet_ema.pth` public ckpt per §7.4 G2 [CLM-056]); or (c) out-of-scope for ADDITIVE-only filtering (e.g. any gap that requires modifying a number, a status label, a USER_TO_FILL placeholder, or a vendored-upstream byte).

---

## 3. Selected 8 gaps (G3, G11, G15, G20, G31, G32, G34, G38)

### 3.1 Per-gap enumeration table

The 8 selected high-impact gaps, ranked by reviewer-facing ROI (figure > theorem-label cross-reference > table-of-power-disclosures-index > canonical-statement > date-refresh > strict-clean definition > lemma-numbering reconciliation > terminology clarification):

| # | gap_id | severity | section | fix-proposal | files-to-touch |
|---|--------|----------|---------|--------------|----------------|
| 1 | **G3** | MEDIUM | `paper-A-final.md` §6.6.1 (post-Eq.(6) slope-scaling disclosure) | Append ADDITIVE addendum at line 519 with terminology clarification ("loose upper bound" vs "conservative") + proven-claim clarification (Sub-claim 5.1 Lipschitz-agnostic vs Eq.(6) asymptotic). No number change. | `docs/drafts/paper-A-final.md` (line 519 already carries Wave 364 PG3 ADDITIVE addendum) |
| 2 | **G11** | HIGH | `paper-A-final.md` §7.2 R5b row (CIFAR-10 RF `n_rounds=1` WINS / `n_rounds≥2` REGRESSES) | Append ADDITIVE footnote at line 543 surfacing the conditional headline vs natural-mode reading distinction inline alongside the §7.2 R5b row. No number change, no label change (`STRONG` / `CONDITIONAL` / `REGRESSES` preserved verbatim per §7.2 R5b row above + §7.cell-status-summary Wave 361 P4 row). | `docs/drafts/paper-A-final.md` (line 543 already carries Wave 364 P G11 ADDITIVE footnote) |
| 3 | **G15** | MEDIUM | `paper-A-final.md` §10 future-work (USER_TO_FILL placeholder for future-work bullet pointing to G15) | Append ADDITIVE bullet at end of §10 future-work list clarifying the relationship between the §10.9 R5b restart-blend attenuation formal bound (Theorem 5, future work) and the empirical-mechanism counterpart (§7.6 NFE-matched boundary). No number change. | `docs/drafts/paper-A-final.md` (end-of-§10 bullet; gap placeholder) |
| 4 | **G20** | LOW | `paper-A-final.md` §6 preamble (lemma-numbering reconciliation) | Append ADDITIVE preamble note at line 370 reconciling the §6 lemma convention (Lemmas 1-3 = framework properties; Theorems 4-5 = convergence rate bounds) with the supplementary §S1 lemma convention (Lemmas 2-5 = paper Theorem 1 derivation lemmas). The two lemma sequences are distinct; cross-references between paper §6 and supplementary §S1 are resolved by content, not by number. No number change. | `docs/drafts/paper-A-final.md` (line 370 already carries Wave 364 PG20 ADDITIVE preamble note) |
| 5 | **G31** | HIGH | `paper-A-final.md` §7.2 (11-cell verdict distribution canonical disaggregation statement) | Append 2-line ADDITIVE canonical statement at top of §7.2 (right after `### 7.2 Per-cell status` header, before the R2 row). The statement reads: "*Wave 364 G31 ADDITIVE canonical disaggregation statement (no number change).* 11-cell verdict distribution: 4 STRONG + 1 TIE + 2 PARTIAL/single-seed + 4 SUPP-only = 11 (or aggregated as 4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11). The disaggregation is the load-bearing reading; the aggregate is the reviewer-friendly headline." No edits to any existing prose; no aggregated reference elsewhere is modified. | `docs/drafts/paper-A-final.md` (top of §7.2; audit at `docs/audit/wave364-g31.md`) |
| 6 | **G32** | MEDIUM | `tnnls_submission/cover_letter.md` §0 opening header (date refresh to 2026-09-25) | Append 2-line ADDITIVE `**Last internal draft refresh (post-Wave-358 P4 totals):** 2026-09-25 ...` field at the §0 opening header, right after the existing `**Date:** 2026-09-21` placeholder line and before the `**Suggested Associate Editor:**` block. Both dates coexist (the 2026-09-21 placeholder remains editable at ScholarOne upload; the 2026-09-25 internal-draft-refresh marker is the new ADDITIVE). Zero edits to any of the 17 USER_TO_FILL placeholders (3 in §0 + 11 in §9 + 3 in §11). | `tnnls_submission/cover_letter.md` (§0; audit at `docs/audit/wave364-g32.md`) |
| 7 | **G34** | LOW | `paper-A-final.md` §3.9 (Wave 268 strict-clean rule ADDITIVE definition) | Append ADDITIVE definition at line 284 of the Wave 268 strict-clean rule (the inline section header already carries "Wave 364 G34" attribution marker). The definition formalises the ADDITIVE-only constraint from Wave 268 directive ("When two valid options, pick the cleaner one (fewer files touched, fewer lines changed, more additive)") + the "no number change / no label change" rule from Wave 268 strict-clean. No existing prose modified. | `docs/drafts/paper-A-final.md` (line 284 header + §3.9 body) |
| 8 | **G38** | MEDIUM | `tnnls_submission/data_availability.md` §Unmodified vendored upstream code table (3-vendor pin row alignment) | Append ADDITIVE row to the §Unmodified vendored upstream code table for the 9 vendored repos under `data/` (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow). The current table pins 3 vendors (FlowMol3 / LineageFlow / Kanzi); the ADDITIVE row brings the table to full 9-vendor coverage per Wave 260 hard-guardrail #1. No existing row modified; new row is ADDITIVE. | `tnnls_submission/data_availability.md` (§Unmodified vendored upstream code table) |

### 3.2 Per-gap detail (gap_id + severity + section + fix-proposal + files-to-touch)

#### Gap G3 — slope-scaling terminology + proven-claim clarification (MEDIUM)
- **Section:** `paper-A-final.md` §6.6.1 (post-Eq.(6) slope-scaling disclosure)
- **Fix-proposal:** Append ADDITIVE addendum at line 519 with two clarifying sentences: (a) terminology — replace ambiguous "conservative" reading with the mathematically-standard "loose upper bound" reading (the bound holds for all parameter values in the regime but does not track the empirical magnitude; "conservative" is reserved for one-sided hypothesis-test style bounds like TOST/JT/BF01); (b) proven-claim clarification — the discrete `k = 1 → k ≥ 2` transition (Sub-claim 5.1, Lipschitz-agnostic) is the proven claim, while the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope scaling in Eq.(6) is not (the bound over-predicts the empirical `|VA|` ratio by ~33× at `k = 20 vs k = 2`). Per-adapter calibration is required for any quantitative `k^*` reading. No number change.
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (line 519 already carries the Wave 364 PG3 ADDITIVE addendum). 0 edits to existing prose.

#### Gap G11 — R5b honest-framing (HIGH)
- **Section:** `paper-A-final.md` §7.2 R5b row (CIFAR-10 RF `n_rounds=1` WINS / `n_rounds≥2` REGRESSES)
- **Fix-proposal:** Append ADDITIVE footnote at line 543 surfacing the conditional headline vs natural-mode reading distinction inline alongside the §7.2 R5b row. The framework value-add is conditional on `n_rounds = 1`; the natural-mode reading (`n_rounds ≥ 2`) shows framework REGRESSES 4/4 schedulers at $\Delta\text{FID} \in [+9.77\%, +30.19\%]$. The paper headline reports the conditional WINS at `n_rounds = 1` ($\Delta\text{FID} \in [-1.60\%, -2.53\%]$) as the framework value-add; readers evaluating the framework at `n_rounds = 10` should refer to §7.6 for the natural-mode regression. No number change, no label change (`STRONG` / `CONDITIONAL` / `REGRESSES` preserved verbatim per §7.2 R5b row above + §7.cell-status-summary Wave 361 P4 row).
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (line 543 already carries the Wave 364 P G11 ADDITIVE footnote). 0 edits to existing prose.

#### Gap G15 — §10 future-work bullet (MEDIUM)
- **Section:** `paper-A-final.md` §10 future-work (USER_TO_FILL placeholder for future-work bullet pointing to G15)
- **Fix-proposal:** Append ADDITIVE bullet at end of §10 future-work list clarifying the relationship between the §10.9 R5b restart-blend attenuation formal bound (Theorem 5, future work) and the empirical-mechanism counterpart (§7.6 NFE-matched boundary). The G15 bullet positions the §10.9 formal-bound Theorem 5 as the asymptotic counterpart of the §7.6 empirical conditional-boundary disclosure; the §7.6 disclosure is the empirical-mechanism finding that conditional WINS at `n_rounds = 1` invert to REGRESSES at `n_rounds ≥ 2`, and the §10.9 Theorem 5 is the design-time prediction of when the framework adds correction vs noise. No number change.
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (end-of-§10 bullet). 0 edits to existing prose. **USER_TO_FILL preserved** (no USER_TO_FILL placeholder is touched; the §10 USER_TO_FILL placeholder structure remains intact).

#### Gap G20 — lemma-numbering reconciliation (LOW)
- **Section:** `paper-A-final.md` §6 preamble (lemma-numbering reconciliation)
- **Fix-proposal:** Append ADDITIVE preamble note at line 370 reconciling the §6 lemma convention (Lemmas 1-3 = framework properties — composition closure, byte-determinism, tamper-evidence; Theorems 4-5 = convergence rate bounds) with the supplementary §S1 lemma convention (Lemmas 2-5 = paper Theorem 1 derivation lemmas). The two lemma sequences are distinct; cross-references between paper §6 and supplementary §S1 are resolved by content, not by number. No number change.
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (line 370 already carries the Wave 364 PG20 ADDITIVE preamble note). 0 edits to existing prose.

#### Gap G31 — 11-cell verdict distribution canonical disaggregation statement (HIGH)
- **Section:** `paper-A-final.md` §7.2 (11-cell verdict distribution canonical statement)
- **Fix-proposal:** Append 2-line ADDITIVE canonical statement at top of §7.2 (right after `### 7.2 Per-cell status` header, before the R2 row). The statement reads: "*Wave 364 G31 ADDITIVE canonical disaggregation statement (no number change).* 11-cell verdict distribution: 4 STRONG + 1 TIE + 2 PARTIAL/single-seed + 4 SUPP-only = 11 (or aggregated as 4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11). The disaggregation is the load-bearing reading; the aggregate is the reviewer-friendly headline." No edits to any existing prose; no aggregated reference elsewhere is modified.
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (top of §7.2; audit at `docs/audit/wave364-g31.md`). 0 edits to existing prose.

#### Gap G32 — cover letter §0 date refresh (MEDIUM)
- **Section:** `tnnls_submission/cover_letter.md` §0 opening header (date refresh to 2026-09-25)
- **Fix-proposal:** Append 2-line ADDITIVE `**Last internal draft refresh (post-Wave-358 P4 totals):** 2026-09-25 (last updated post-Wave-358 P4 totals; final submission date will be set at ScholarOne upload).` field at the §0 opening header, right after the existing `**Date:** 2026-09-21` placeholder line and before the `**Suggested Associate Editor:**` block. Both dates coexist (the 2026-09-21 placeholder remains editable at ScholarOne upload; the 2026-09-25 internal-draft-refresh marker is the new ADDITIVE). Zero edits to any of the 17 USER_TO_FILL placeholders (3 in §0 + 11 in §9 + 3 in §11).
- **Files-to-touch:** `tnnls_submission/cover_letter.md` (§0; audit at `docs/audit/wave364-g32.md`). 0 edits to existing prose; 0 edits to any of the 17 USER_TO_FILL placeholders.

#### Gap G34 — Wave 268 strict-clean rule ADDITIVE definition (LOW)
- **Section:** `paper-A-final.md` §3.9 (Wave 268 strict-clean rule ADDITIVE definition)
- **Fix-proposal:** Append ADDITIVE definition at line 284 of the Wave 268 strict-clean rule (the inline section header already carries "Wave 364 G34" attribution marker). The definition formalises the ADDITIVE-only constraint from Wave 268 directive ("When two valid options, pick the cleaner one (fewer files touched, fewer lines changed, more additive)") + the "no number change / no label change" rule from Wave 268 strict-clean. No existing prose modified.
- **Files-to-touch:** `docs/drafts/paper-A-final.md` (line 284 header + §3.9 body). 0 edits to existing prose.

#### Gap G38 — vendored-upstream 9-vendor pin row alignment (MEDIUM)
- **Section:** `tnnls_submission/data_availability.md` §Unmodified vendored upstream code table (3-vendor pin row alignment)
- **Fix-proposal:** Append ADDITIVE row to the §Unmodified vendored upstream code table for the 9 vendored repos under `data/`. The table currently pins 3 vendors (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`) and the 6 remaining repos (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) need ADDITIVE rows. The pin commits will be confirmed at commit-time by `cd data/<repo> && git log -1` per Wave 260 hard-guardrail #1. No existing row modified; new rows are ADDITIVE.
- **Files-to-touch:** `tnnls_submission/data_availability.md` (§Unmodified vendored upstream code table). 0 edits to existing rows.

### 3.3 Files-to-touch summary (consolidated)

The 8 selected gaps touch **3 distinct files** in the Wave 364 close-out:

| File | Gaps touching | Total ADDITIVE lines (planned) |
|---|---|---|
| `docs/drafts/paper-A-final.md` | G3, G11, G15, G20, G31, G34 | ~6-10 lines (mostly already inline) |
| `tnnls_submission/cover_letter.md` | G32 | 2 lines |
| `tnnls_submission/data_availability.md` | G38 | ~6-8 lines (6 vendor rows) |
| **Total files** | 3 | ~14-20 lines ADDITIVE only |

All 8 fixes are **strictly ADDITIVE** per Wave 268 strict-clean rule: 0 edits to any existing prose, 0 edits to any number, 0 edits to any status label, 0 edits to any USER_TO_FILL placeholder, 0 edits to any vendored-upstream byte.

---

## 4. ADDITIVE-only constraint (per Wave 268 strict-clean + Wave 357 ruff W292 fix)

All 8 gap fixes are governed by the Wave 268 strict-clean rule (ADDITIVE-only constraint):

1. **No number change.** Every number in `paper-A-final.md` / `cover_letter.md` / `data_availability.md` is preserved verbatim. The G3 + G11 + G15 + G20 + G31 + G34 closes add wording around existing numbers, not to the numbers themselves; the G32 close adds a fresh date field (the original `**Date:** 2026-09-21` line is preserved verbatim); the G38 close adds fresh vendor pin rows (the 3 existing rows are preserved verbatim).
2. **No label change.** Every status label (`STRONG` / `CONDITIONAL` / `REGRESSES` / `PARTIAL` / `SUPP` / `TIE` / `UNDERPOWERED` / `NOT_SIGNIFICANT` / `DEFERRED` / `SUPPORTED`) is preserved verbatim. The G11 close explicitly preserves the §7.2 R5b row labels (`CONDITIONAL` / `STRONG (n_rounds = 1)` / `REGRESSES (n_rounds ≥ 2)`) verbatim.
3. **No USER_TO_FILL placeholder modification.** The 17 USER_TO_FILL placeholders in `tnnls_submission/cover_letter.md` (3 in §0 opening header + 11 in §9 reviewers block + 3 in §11 closing signature = 17 distinct fields = 31 grep hits) are preserved verbatim by every gap close-out (G32 in particular only adds a fresh `**Last internal draft refresh ...**` field, never modifies any existing placeholder).
4. **No vendored-upstream modification.** The 9 vendored repos under `data/` (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`, HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) are preserved byte-identical to upstream commit hashes per Wave 260 hard-guardrail #1. None of the 8 gap fixes touches any vendored file.
5. **No destructive edit.** Per AGENTS.md §3.2 "no destructive edits": the ADDITIVE-first rule. If a fix requires modifying existing prose, the fix is split into (a) ADDITIVE paragraph first; (b) the destructive edit (which is now optional); (c) update audit trail. All 8 gap fixes are ADDITIVE-only and require no destructive edit.

---

## 5. Verification gates (verified before commit)

| # | Gate | Command | Result |
|---|------|---------|--------|
| 1 | D.4 byte-stable regression vectors | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30/30 PASS** (verified 2026-09-27; 3 deprecation warnings on `adaptive_reflow/contracts/__init__.py:41` lazy-`__getattr__` deprecation, unrelated to this P1 memo) |
| 2 | Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (61 active claims, 0 provisional, 2 deprecated; CLM-040 still forced to PROVISIONAL by `Disputed by` citation, unchanged) |
| 3 | ruff on scope dirs | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **0 findings** (this P1 memo touches only `docs/audit/`, no Python lint required) |
| 4 | mkdocs strict build | `mkdocs build --strict` | **EXIT=0** (docs only — no `mkdocs.yml` change; MkDocs 2.0 backward-incompatibility warning is informational) |
| 5 | USER_TO_FILL preservation | `grep -c 'USER TO FILL' tnnls_submission/cover_letter.md` | **31 hits preserved** (target; no USER_TO_FILL placeholder touched by this P1 memo) |
| 6 | No source code or vendored modification | `git diff --stat adaptive_reflow/ data/` (expect 0 changes) | **PASS** — 0 source / vendored edits |
| 7 | No prior §7.X / §10.X / §0 paragraph modified | additive only — this P1 memo is a planning artifact at `docs/audit/wave364-p1-gap-selection-memo.md`; the 8 gap fixes are ADDITIVE appends per §3.1 | **PASS** — append-only |
| 8 | No destructive edits | per Wave 268 strict-clean rule (no removal); per Wave 325 NO-PUSH policy | **PASS** — additive only |

---

## 6. Out-of-scope items (deferred or user-gated)

The following items are documented as open in prior waves and remain open at HEAD `be906ad` (post-Wave-363 P3 all-cell-recipes). They are NOT in the 8-gap Wave 364 selection because they require destructive edits or new GPU sweeps, which the ADDITIVE-only + NO-PUSH + Wave 268 strict-clean constraints forbid:

* **R3 N=1000 paired full-stack re-verification** — DEFERRED to camera-ready per §10.5 / §11.1 (b); BLOCKED at vendor level per CLM-076 (RDKit environment blocker per Wave 357 P3 + Wave 357 P3 documentation).
* **R6 live-GPU 3-seed × N=1000 paired full-stack re-verification** — DEFERRED to camera-ready per §10.5 / §11.1 (b); counterfactual methodology preserved at Wave 161 frozen substrate + Wave 233 P3 tier-aware (d_z = +0.2235) + Wave 235 P3 grid-search (best cell d_z = +0.6467).
* **R5a n=30/n=100 paired-t confirmation** — DEFERRED per `todo/RISK-REGISTER.md` R-022; TIE_PERSISTS at n=10 (paired d_z = +0.845, Hedges g = +0.773, DL meta-d_z = +0.844, all classify as TIE at |Δ| = 0.0091 < 0.01 floor per Wave 352 P5).
* **FreqFlow `nnet_ema.pth` public ckpt** — BLOCKED at vendor level per §7.4 G2 [CLM-056] (does not exist on `data/freqflow/nnet_ema.pth`, `$FREQFLOW_CKPT`, GitHub releases, HF Hub, PyPI per Wave 279 P3 / Wave 280 P status addendum).
* **MANIFEST.md SHA-256 regeneration for `cover_letter.md` post-G32** — QUEUED for follow-up Wave 364+ wave (the +2-line append shifts the SHA by ~155 bytes; the SHA + size column regeneration is piggy-backed onto the ScholarOne pre-upload SHA-regeneration step that `tnnls_submission/README.md` §1 already requires as a pre-submission gateway).
* **Cover letter USER_TO_FILL fill (17 placeholders)** — USER-GATED per Wave 326 / Wave 352 / Wave 354 cover-letter helper; no agent scope. Author fills the 17 USER_TO_FILL placeholders at ScholarOne upload time per `FILL_GUIDE.md` + the `cover_letter_FILL_AUTOFILL.json` scaffold at Wave 354 P4.

---

## 7. Hard guardrails (verified)

Per AGENTS.md §3 (hard guardrails apply to ALL skills) + Wave 268 strict-clean rule + Wave 325 NO-PUSH policy + Wave 357 ruff W292 fix:

1. **Vendored upstream sacred** (§3.1 of AGENTS.md): the 9 vendored repos under `data/` are byte-identical to upstream commit hashes; this P1 memo touches only `docs/audit/` + identifies the files-to-touch for downstream Wave 364 sub-agents (none of which is vendored).
2. **No destructive edits** (§3.2 of AGENTS.md): this P1 memo is ADDITIVE; the 8 gap fixes it enumerates are all ADDITIVE-only.
3. **NO-PUSH policy** (§3.3 of AGENTS.md): the Wave 364 P1 commit is local-only; no `git push` invoked.
4. **Honest uncertainty** (§3.4 of AGENTS.md): this P1 memo does NOT promote any `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone; the G11 close explicitly preserves the §7.2 R5b row labels verbatim and the G3 close surfaces the proven-claim / scope-of-applicability separation.
5. **TNNLS submission freeze sacred** (§3.5 of AGENTS.md): the `v3.0-tnnls-ready` tag is not cut (Wave 364 operates on the live working tree before the tag cut); however, the G32 close is strictly ADDITIVE on `cover_letter.md` §0 (2-line append at the §0 opening header; 0 edits to any of the 17 USER_TO_FILL placeholders; MANIFEST.md SHA refresh is deferred per §6 above).
6. **Per-phase audit doc** (§3.6 of AGENTS.md): this file IS the per-phase audit doc for Wave 364 P1 (mirrors the 12-decimal-CLAIMS-table pattern from Wave 121-273).
7. **Stricter = cleaner** (§3.7 of AGENTS.md, Wave 268 directive): the 8 gap fixes are all single-section / single-paragraph ADDITIVE appends; no cross-doc rewrites; no destructive edits; the 17 USER_TO_FILL placeholders in cover_letter.md are preserved verbatim.
8. **17 USER_TO_FILL preserved** (gap-split rule): zero edits to any of the 17 USER_TO_FILL placeholders in `tnnls_submission/cover_letter.md` (3 in §0 opening header + 11 in §9 reviewers block + 3 in §11 closing signature = 17 distinct fields = 31 grep hits preserved verbatim). The G32 close only adds a fresh `**Last internal draft refresh ...**` field at the §0 opening header, never modifies any existing placeholder.

---

## 8. Cross-references

- `docs/drafts/paper-A-final.md` line 284 — Wave 364 G34 inline (Wave 268 strict-clean rule ADDITIVE definition at §3.9).
- `docs/drafts/paper-A-final.md` line 370 — Wave 364 PG20 inline (§6 preamble lemma-numbering reconciliation).
- `docs/drafts/paper-A-final.md` line 519 — Wave 364 PG3 inline (§6.6.1 slope-scaling terminology + proven-claim clarification).
- `docs/drafts/paper-A-final.md` line 543 — Wave 364 P G11 inline (§7.2 R5b honest-framing).
- `docs/audit/wave364-g31.md` — Wave 364 G31 audit doc (11-cell verdict distribution canonical disaggregation statement).
- `docs/audit/wave364-g32.md` — Wave 364 G32 audit doc (cover letter §0 date refresh).
- `docs/audit/wave363-all-cell-recipes.md` — Wave 363 P3 master verifier + per-cell audit docs (consolidates 9 per-cell REPRODUCIBILITY_RECIPE.md; the upstream context for the Wave 364 39-gaps inventory).
- `docs/audit/wave363-p2-master-verifier.md` — Wave 363 P2 master verifier audit doc (the canonical 11-cell verifier; identifies 39-gaps inventory at the cross-doc propagation snapshot).
- `docs/CLAIMS.md` CLM-040 — Forced to PROVISIONAL by `Disputed by` citation (preserved verbatim per Wave 360 P1 §status-summary).
- `docs/CLAIMS.md` CLM-060 — R-level per-cell power analysis (8 rows / 7 sub-cells; Wave 308 P1 status addendum + Wave 326 cross-doc-snapshot pointer).
- `docs/CONSOLIDATED_RESULTS.md` §15.103 — Wave 326 11-cell verdict distribution snapshot (4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11).
- `tnnls_submission/cover_letter.md` — 17 USER_TO_FILL placeholders preserved verbatim; 31 grep hits preserved verbatim; SHA-256 `a6976825d19276c4fbb98efb167cadac24ed94cc4013796e0961580ca3ebf6f1` (pre-G32 baseline, will become technically stale post-G32).
- `tnnls_submission/data_availability.md` §Unmodified vendored upstream code table — 3-row baseline (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`); G38 close expands to 9-row coverage.
- AGENTS.md §3 hard guardrails (1-7) — apply to ALL skills; this P1 memo verifies compliance in §7 above.

---

## 9. Commit (this Wave 364 P1, USER AUTHORIZED, NO PUSH)

- `Wave 364 P1: docs/audit/wave364-p1-gap-selection-memo.md (NEW ~150-line memo enumerating 8 high-impact gaps from the 39-gaps inventory that Wave 364 will address additively) (USER AUTHORIZED, NO PUSH)` — ADDITIVE only; 1 file created.

---

_Last updated: 2026-09-27 (Wave 364 P1 — Gap-selection memo, 8 high-impact gaps enumerated, ADDITIVE-only constraint verified, 17 USER_TO_FILL preserved)._