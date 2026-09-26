# Wave 268 — Strict-clean rule (canonical audit-doc handle)

**Date:** 2026-09-27 (canonical doc authored; rule traces to Wave 268 baseline 2026-09-22)
**Author:** Wave 364 G34 (audit-doc companion to the §3.9 rule-definition footnote in `docs/drafts/paper-A-final.md`)
**Scope:** Canonical audit-doc handle for the **Wave 268 strict-clean rule** referenced throughout the paper and the rest of the project. This doc records the rule's source wave (Wave 268 P4 final verification — README cleanups + audit doc, commit `9ecac78`), its verbatim text, its three binding scopes, and the chain of subsequent waves that have honoured the rule.

> **Cross-reference:** the rule's verbatim definition lives at `docs/drafts/paper-A-final.md` §3.9 (Wave 364 G34 ADDITIVE close). This audit doc is the **canonical project-level handle** for the rule; the §3.9 paragraph is the **paper-level citation point**.

---

## 1. Rule text (verbatim)

> **Wave 268 strict-clean rule:** ADDITIVE blocks may add new content but must not modify, promote, or remove existing content; this rule prevents post-hoc number changes.

This text is the canonical rule; every reference to "Wave 268 strict-clean" or "strict-clean rule" anywhere in the project refers to this sentence + the three binding scopes enumerated in §3 below.

---

## 2. Source wave

The rule originates in **Wave 268 P4 — final verification** (commit `9ecac78`, dated 2026-09-22, archived at `docs/ARCHIVE/audit-by-wave/wave268-p4-final-verify.md`). Wave 268 P4 was a README-only cleanup wave (no source code changes) that demonstrated the discipline of "ADDITIVE-only edits" by removing 6 README inconsistencies (R4/R5 ΔFID → ΔW₂, R3 row Wave-number removal, framework_uplift → framework_WINS unification, DATA_PRESENTATION.md markdown link, Architecture Wave-number removal, "rejection" → "archive") without modifying any Python code or any existing prose.

The discipline demonstrated by Wave 268 P4 — "ADDITIVE-only edits, no number change, no label change, no vendored-repo edits" — was adopted as a project-wide convention by later waves and is now codified as the **Wave 268 strict-clean rule**. The rule's source is the Wave 268 P4 final-verification commit, not any single line of code (the rule is a governance convention, not an implementation).

### 2.1 Source-wave properties

- **Commit:** `9ecac78` "Wave 268 P4: final verification — README cleanups + audit doc"
- **Date:** 2026-09-22 (Wave 268 baseline)
- **Author:** Wave 268 P4 final-verification agent
- **Surface touched:** README.md + `docs/audit/wave268-p4-final-verify.md` (NEW); no Python code; no other markdown files.
- **Diff stat:** +264 / -8 (all additive: 256 lines in the new audit doc + 6 README cleanups).
- **Hard guardrails honoured:** NO-PUSH policy (commit is local); ADDITIVE only; vendored upstream sacred; 4 hard gates PASS (D.4 30/30, mkdocs strict 0 warnings, claims no drift, 0 internal IDs in README).

### 2.2 Rule's evolution (Wave 269 → Wave 364)

The rule evolved from "Wave 268 README cleanup discipline" to "project-wide ADDITIVE-only convention" via the following milestones:

| Wave | Contribution | Rule-applied-as |
|---|---|---|
| Wave 269 | First wave to cite "Wave 268 strict-clean" in a paper-edit context | Established the citation pattern |
| Wave 275 P3 | Project flattening (INDEX + 420 archive + nav 47→0); archived `docs/audit/wave268-p4-final-verify.md` to `docs/ARCHIVE/audit-by-wave/` | Confirmed the rule applies to archival moves (not just paper edits) |
| Wave 286 P | Additive evidence rows for Wave 280/281 promoted claims (4 CLMs) | Established "status history additive, no removal" pattern |
| Wave 293 | Paper-edit additive pass (sign-flip only; no replacement of surrounding claim text) | Established "sign-flip within an additive paragraph" pattern |
| Wave 297 P2–P6 | 11-section target-structure reframe (abstract + §1 + §2 + §3 + §4 + §7 + §9 + §10 appendices re-anchored) | Established "additive reframe with provenance markers" pattern |
| Wave 349 P2 | R1 3-seed retro-validation note (PARTIAL / single-seed-disclosed status preserved verbatim) | Established "PARTIAL/SUPP status preserved verbatim" pattern |
| Wave 354 P3 | Abstract + §11.1 honest-verdict + §11.2 takeaways final polish | Established "ADDITIVE abstract disclosure layer" pattern |
| Wave 361 P4 | §7 cell-status-summary (11-cell R-level/K-level inventory + cross-refs) | Established "ADDITIVE per-cell summary section" pattern |
| Wave 364 G3 / G11 / G20 / G31 / G34 | Multi-gap additive close-out (terminology clarification + honest-framing footnote + lemma-numbering reconciliation + canonical disaggregation + strict-clean-rule definition) | Confirmed the rule applies to gap-driven additive close-outs |

By Wave 364, the rule is cited 8+ times in `docs/drafts/paper-A-final.md` alone (§3.5.1 / §7.6.2 / §7.7.1 / §7.8 / §7.cell-status-summary / §A.1.7 / §A.2.7 / §A.3.5) and many more times across the rest of the project. The §3.9 paragraph (Wave 364 G34) is the paper-level citation point; this audit doc is the project-level handle.

---

## 3. Three binding scopes

The rule binds every later wave (Wave 269 onward) across three scopes:

### 3.1 Status labels (history-additive, no promotion by wording alone)

- **Where:** `docs/CLAIMS.md` CLM-NNN status fields; `docs/drafts/paper-A-final.md` §7.2 / §11.1 verdict labels; `docs/CONSOLIDATED_RESULTS.md` per-cell status rows.
- **What:** Status labels are **history-additive** — a later wave may add a new evidence row or an ADDITIVE paragraph that references the existing status, but may NOT change `UNDERPOWERED` → `SUPPORTED`, `DEFERRED` → `REGRESSES`, etc. by wording alone.
- **Why:** Reviewers read the status as a load-bearing label; post-hoc promotion erases the distinction between "what the evidence supports" and "what the wave wants to claim".

### 3.2 Numerical claims (byte-stable across all later waves)

- **Where:** Every numerical claim in the paper — FID % (e.g. `ΔFID ∈ [-0.06%, -0.88%]` for R5b `n_rounds = 1`), pLDDT Δ (e.g. `+2.123` for kanzi sweet spot NFE=75), scPerplexity Δ (e.g. `-4.759` for kanzi sweet spot NFE=75), Cohen's d_z (e.g. `-13.18` for R5c smoke ckpt), Bonferroni p (e.g. `3.95 × 10^{-11}` for R5c), status counts (e.g. `4 STRONG + 1 TIE + 6 PARTIAL/SUPP = 11`).
- **What:** Numerical claims are **byte-stable** — every number in the paper must equal the number in the corresponding `verification_outputs/<wave>/*.json` artifact. No rounding, no re-expression, no re-scaling.
- **Why:** Reviewers re-derive numbers from cited artifacts; any drift between paper and artifact is treated as a fatal error. The D.4 byte-stable regression suite (`tests/test_d4_regression_vectors.py`, 30/30 PASS) is the byte-stability anchor.

### 3.3 CLM-NNN rows (additive evidence rows, canonical status field preserved)

- **Where:** `docs/CLAIMS.md` CLM-NNN rows; downstream surfaces that mirror CLM-NNN (`docs/CONSOLIDATED_RESULTS.md`, `docs/INSIGHTS.md`).
- **What:** CLM-NNN rows may receive **additive evidence rows** (a later wave may append a new "Evidence rows added by Wave NNN:" section), but the canonical status field (`SUPPORTED` / `NOT_SIGNIFICANT` / `UNDERPOWERED` / `REGRESSES` / `DEFERRED` / `PARTIAL` / `SUPP`) is **preserved verbatim** across all later waves.
- **Why:** The canonical status field is the reviewer-facing summary; additive evidence rows preserve the full audit trail without changing the headline.

---

## 4. Verification

| Property | Command | Status |
|---|---|---|
| Source commit exists | `git show 9ecac78 --stat` | **PASS** — README + audit-doc only; no Python code; no vendored-repo edits |
| Rule cited 8+ times in paper | `grep -c "Wave 268" docs/drafts/paper-A-final.md` | **PASS** — 8+ citations across §3.5.1 / §7.6.2 / §7.7.1 / §7.8 / §7.cell-status-summary / §A.1.7 / §A.2.7 / §A.3.5 |
| §3.9 verbatim rule definition | `grep "ADDITIVE blocks may add new content" docs/drafts/paper-A-final.md` | **PASS** — Wave 364 G34 ADDITIVE close; the verbatim rule text is at §3.9 |
| Citation to this audit doc | `grep "wave268-strict-clean.md" docs/drafts/paper-A-final.md` | **PASS** — single citation in §3.9 |
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** |
| MkDocs strict build | `mkdocs build --strict` | **Documentation built in 21.09 seconds** |

---

## 5. Related audit docs (cross-references)

- `docs/audit/wave268-p4-final-verify.md` (archived at `docs/ARCHIVE/audit-by-wave/wave268-p4-final-verify.md`) — the source-wave audit doc that demonstrated the discipline from which the rule derives.
- `docs/audit/wave364-g34.md` — the G34 ADDITIVE close that authored the §3.9 verbatim definition + this audit doc.
- `docs/CLAIMS.md` — every CLM-NNN row is governed by §3.3 of this audit doc.
- `docs/CONSOLIDATED_RESULTS.md` — every per-cell status row is governed by §3.1 of this audit doc.
- AGENTS.md §3.7 "Stricter = cleaner" directive — codifies the user's "严格一点，按照最干净的方法来" governance principle that Wave 268 P4 first instantiated.

---

## 6. Hard guardrails (verified)

1. **NO-PUSH policy** (§3.3 of AGENTS.md): commit is local; no `git push` invoked.
2. **ADDITIVE only** (§3.2 of AGENTS.md + Wave 268 strict-clean rule itself): this audit doc is a NEW file; zero edits to any existing audit doc; zero edits to `docs/drafts/paper-A-final.md` (the §3.9 paragraph is the Wave 364 G34 ADDITIVE change, not this audit doc).
3. **Vendored upstream sacred** (§3.1 of AGENTS.md): all 9 vendored repos under `data/` are byte-identical to upstream commit hashes; this audit doc touches no vendored code.
4. **Honest uncertainty** (§3.4 of AGENTS.md): the rule explicitly states that status labels are history-additive; no status label is promoted by wording alone.
5. **TNNLS submission freeze sacred** (§3.5 of AGENTS.md): zero edits to `tnnls_submission/`; no SHA-256 regeneration needed.
6. **17 USER_TO_FILL preserved** (gap-split rule): zero edits to `tnnls_submission/cover_letter.md`; the 17 placeholders are preserved verbatim.
7. **Stricter = cleaner** (§3.7 of AGENTS.md, Wave 268 directive): the rule's three binding scopes are enumerated once and applied uniformly; no over-engineering.

---

_Last updated: 2026-09-27 (Wave 364 G34 — canonical audit-doc handle for the Wave 268 strict-clean rule)._