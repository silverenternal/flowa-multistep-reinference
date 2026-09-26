# Wave 367 P5 — §6 Theory De-Wave (Phase 5 of User Destructive Rewrite)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §6 Theory de-waved; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 367 P5)
**Scope:** §6 Framework Properties (paper draft, §6 preamble + §6.2 Sub-claim 1.4 + §6.6.1 numerical-validation footnote + §6.7 final paragraph)
**Hard guardrails:** NO-PUSH; USER-EXPLICIT destructive override under user spec; preserve all Theorem 4 / Theorem 5 / Lemma 1-3 equations + statement numbers verbatim

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Pre-edit SHA-256:** `c6ece5636e8895b9ce876594f966cbc6ceab7e3437f8fec2fc0797bce2193773`
- **Post-edit SHA-256:** `9945d23aec95c829ed808c065a65062b4f066f9369e71e182fb6ab3760c2632b`
- **Pre-edit line count:** 1160
- **Post-edit line count:** 1138
- **Net lines removed:** 22
- **`git diff --stat` for Phase 5:** 9 insertions, 31 deletions (40 line operations total)

### 1.2 Phase 5 edits by sub-step

| Sub-step | Location | Operation | Effect |
|---|---|---|---|
| (2) §6 preamble note | §6.1 last paragraph | DELETE standalone "Wave 364 PG20 preamble note" | Replaced with inline parenthetical preserving convention content; standalone block + "Wave 364 PG20" metadata removed |
| (3) §6.2 Sub-claim 1.4 note | §6.2 final Sub-claim 1.4 | DELETE standalone "Sub-claim 1.4 note (Wave 342 additive disposition)" block | Merge content into Sub-claim 1.4 prose; remove "Wave 342" metadata; preserve algorithm-layer blender set enumeration + adapter-layer molecule-domain replacement reference + RMS-precondition deferral |
| (4) §6.6.1 Wave 351 footnote | §6.6.1 numerical-validation footnote | CONVERT "Wave 351 ADDITIVE footnote" to plain academic footnote | Drop "Wave 351 ADDITIVE footnote, no number change." italic-prefixed metadata; preserve Lipschitz estimator + fitted parameters + transition-prediction + slope-scaling-disclosure + audit-doc references |
| (5) §6.6.1 Wave 364 PG3 addendum | §6.6.1 numerical-validation footnote | MERGE "Wave 364 PG3 ADDITIVE addendum" into main footnote | Collapse two Wave footers into one clean footnote; preserve loose-upper-bound terminology disambiguation + proven-claim/scope-of-applicability clarification |
| (6) §6 final paragraph | §6.7 last paragraph | DE-WAVE "Paper B companion note (Wave 367 ADDITIVE, post §2.2 deletion)" framing | Convert to plain one-sentence Paper B companion cross-reference; preserve "convergence-of-sampling-measures companion theorem lives in a separate companion document; the present paper does not depend on it" content |

### 1.3 Content preserved verbatim (the load-bearing invariants)

- **Theorem 4 (multi-round re-inference convergence rate bound)** statement + Eq. (4) τ_residual / τ_velocity definitions + proof sketch + connection to Lemma 1 + Sub-claim 4.1 regime-curve corollary — all unchanged.
- **Theorem 5 (R5b restart-blend attenuation formal bound)** statement + Eq. (5) / Eq. (6) + Sub-claims 5.1 / 5.2 / 5.3 / 5.4 — all unchanged.
- **Lemma 1 (protocol composition closure)** statement + Steps 1-4 proof + Sub-claims 1.1 / 1.2 / 1.3 / 1.4 (prose body, with Sub-claim 1.4 now incorporating the Wave 342 disposition inline) — all unchanged.
- **Lemma 2 (state-machine byte-determinism)** statement + Cases A-D proof — all unchanged.
- **Lemma 3 (ledger tamper-evidence)** statement + Cases 1-3 + edge-case SHA-256 collision proof — all unchanged.
- **§6.6.1 numerical validation** numerical quantities: `L_local ≈ 0.3810`, `eps_theta ≈ 0.0506`, `sigma_blend ∈ [0.0596, 0.2920]`, `(k=20 vs k=2)` predicted ratio `19 · sqrt(10) ≈ 60.08`, empirical ratio `0.3065 / 0.1662 ≈ 1.844`, ~33× asymptotic over-prediction factor — all unchanged.
- **§6.6.1 transition prediction** `matches_empirical` verdict + 4/4 schedulers WINS at `n_rounds = 1` + 4/4 schedulers REGRESSES at `n_rounds ≥ 2` — all unchanged.
- **§6.6.1 Sub-claim 5.1 proven-claim clarification** discrete `k = 1 → k ≥ 2` transition is proven; asymptotic `(k-1) · sqrt(k/L_local)` slope scaling is not — preserved (collapsed into main footnote with "Proven-claim clarification" header).
- **§6.6.1 loose-upper-bound terminology disambiguation** ~33× asymptotic over-prediction characterised as a loose upper bound (not "conservative", which is reserved for one-sided hypothesis-test bounds) — preserved (collapsed into main footnote).
- **Paper B companion cross-reference** "convergence-of-sampling-measures companion theorem lives in a separate companion document; the present paper does not depend on it" — preserved (Wave 367 ADDITIVE framing de-waved; substantive sentence retained).

### 1.4 Content removed (Wave metadata only)

- "**§6 preamble note (Wave 364 PG20, additive, lemma-numbering reconciliation).**" italic-prefixed paragraph header.
- "**Sub-claim 1.4 note (Wave 342 additive disposition).**" italic-prefixed paragraph header.
- "This sub-claim's wording above is the only line edited; Sub-claims 1.1–1.3 and §6.3–§6.5 are unchanged." closing sentence of the Sub-claim 1.4 note.
- "*Wave 351 ADDITIVE footnote, no number change.*" italic-prefixed footnote header.
- "*Wave 364 PG3 ADDITIVE addendum, no number change — gap G3 close-out (terminology + proven-claim clarification).*" italic-prefixed addendum header.
- "**No number change in §6.6** — Eq.(6), Sub-claims 5.1, 5.2, 5.3, 5.4 are preserved verbatim; this §6.6.1 footnote is ADDITIVE." closing meta-sentence of the Wave 351 footnote.
- "**No number change in §6.6 or §6.6.1** — Eq.(6), Sub-claims 5.1–5.4, the §6.6.1 numerical-validation footnote, and Theorem 5 statement are all preserved verbatim; this addendum is purely clarifying wording (terminology refinement + proven-claim/scope-of-applicability separation) and is preserved as additive per the Wave 268 strict-clean principle." closing meta-sentence of the Wave 364 PG3 addendum.
- "**Paper B companion note (Wave 367 ADDITIVE, post §2.2 deletion).**" italic-prefixed paragraph header at §6.7.

### 1.5 Verification gates (all PASS)

| Gate | Command | Status |
|---|---|---|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed** in 12.96s (target: 30/30 PASS) |
| Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | **All checks passed!** (0 findings) |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **No drift detected** (CLM-040 PROVISIONAL-by-Disputed is pre-existing state, unrelated to §6 edits) |
| mkdocs strict build | `mkdocs build --strict` | **Built in 21.59s** (mkdocs-material license warning is pre-existing infrastructure noise, unrelated to §6 edits) |

### 1.6 Hard guardrail compliance

| Guardrail | Status |
|---|---|
| NO-PUSH policy | Honoured — local commit only (no `git push`) |
| USER-EXPLICIT destructive override | Honoured — destructive operations performed under user spec ("USER-EXPLICIT DESTRUCTIVE REWRITE") |
| Preserve all Theorem 4 / Theorem 5 / Lemma 1-3 equations + statement numbers verbatim | Honoured — see §1.3 (verbatim preservation table) |
| Per-phase audit doc | Honoured — this file (`docs/audit/wave367-p5-theory-de-wave.md`) is the per-phase audit |
| NO-PUSH reaffirmation (AGENTS.md §3.3 + todo/PUSH-READY.md) | Honoured — local commit only; no push to remote |
| Vendored upstream sacred (AGENTS.md §3.1) | Honoured — `data/` vendored repos not touched; only `docs/drafts/paper-A-final.md` modified |

---

## 2. Interpretation

### 2.1 What the de-wave achieves

Phase 5 of the Wave 367 user-destructive rewrite removes **wave-number metadata** from the §6 Theory section while preserving every substantive content element. The four operations are:

1. **§6 preamble note → inline parenthetical.** The lemma-numbering convention note (Lemmas 1-3 = framework properties; Theorems 4-5 = convergence rate bounds; supplementary §S1 uses separate convention Lemmas 2-5) is reader-navigational content. Inlining it as a parenthetical at the end of the existing §6.1 final paragraph preserves the convention disambiguation without the standalone "Wave 364 PG20 preamble note" block structure. The "Wave 364 PG20" ADDITIVE framing is removed; the convention content remains accessible inline.

2. **§6.2 Sub-claim 1.4 note → merged into Sub-claim 1.4 prose.** The previously-enumerated fourth blender `RMSPreservingCoordinateMixer` (deprecated back-compat alias for the molecule-domain concrete impl `EqualRmsCoordinateMixer`) is now mentioned inline in Sub-claim 1.4 prose. The canonical molecule-domain replacement (exposed via universal `RestartMixer` Protocol at the adapter layer; referenced by R3 FlowMol3 + R2 Kanzi experimental cells) is preserved. The RMS-precondition deferral is preserved (still marked as deferred to separate work). The "Wave 342 additive disposition" framing is removed.

3. **§6.6.1 Wave 351 + Wave 364 PG3 → single clean academic footnote.** The two italic-prefixed Wave footnotes are collapsed into one footnote. The substantive content (Lipschitz estimator + fitted parameters + transition-prediction + slope-scaling-disclosure + loose-upper-bound terminology + proven-claim clarification + audit-doc references) is all preserved. The "(Wave 351 ADDITIVE)" and "(Wave 364 PG3 ADDITIVE)" framing is removed. The "No number change" meta-sentences are removed (the substantive claim of preservation is implicit in the footnote itself).

4. **§6 final paragraph Paper B companion cross-reference → plain one-sentence.** The existing "Paper B companion note (Wave 367 ADDITIVE, post §2.2 deletion)" italic-prefixed paragraph is de-waved to a plain one-sentence cross-reference: "The convergence-of-sampling-measures companion theorem lives in a separate companion document; the present paper does not depend on it." This is the §6-end cross-reference the user spec called for ("Paper B 引用移到 §6 末尾一句话").

### 2.2 Why destructive is acceptable here

Per AGENTS.md §3.2 ("No destructive edits. Additive is the rule"), destructive edits require (a) ADDITIVE paragraph first, (b) the destructive edit, (c) update the audit trail. In this Phase 5 work:

- The destructive operations remove only **Wave-number metadata** (italic-prefixed "Wave X ADDITIVE" / "Wave Y PG3" framing), NOT substantive content.
- The substantive content (lemma-numbering convention; blender enumeration + adapter-layer replacement + RMS-deferral; numerical-validation + loose-upper-bound + proven-claim clarification; Paper B companion cross-reference) is preserved — in some cases via inline merging into surrounding prose, in other cases via single-footnote collapse.
- The audit trail (this file) documents every line removed and every substantive content element preserved verbatim.

This is the user-authorised Phase 5 of the broader Wave 367 user-destructive rewrite (which spans multiple paper-text polish operations across §2 / §6 / §7 / §8 / abstract / cover letter). The §6 operations are the theory-section subset of that broader destructive rewrite.

### 2.3 What did NOT change

- **§6.5 Theorem 4** (Eq. (4), proof sketch, connection to Lemma 1, Sub-claim 4.1) — unchanged.
- **§6.6 Theorem 5** (Eq. (5), Eq. (6), proof sketch, Sub-claims 5.1-5.4, Sub-claim 5.4 Wave 350 ADDITIVE close-out header retained since Wave 350 is the originating-wave reference for the close-out status) — unchanged. The §6.6.1 footnote header for §6.6 itself was de-waved ("Wave 351 ADDITIVE" + "Wave 364 PG3 ADDITIVE" footnotes removed), but the inline "(Wave 350 ADDITIVE close-out)" header in Sub-claim 5.4 prose was retained per the task scope (only the §6 preamble + §6.2 Sub-claim 1.4 + §6.6.1 footnotes + §6.7 final were in-scope).
- **§6.3 / §6.4 Lemmas 2 / 3** — unchanged.
- **All numerical quantities** (`L_local`, `eps_theta`, `sigma_blend`, ratios, ~33× factor, `matches_empirical` verdict, 4/4 schedulers WINS/REGRESSES counts) — unchanged.
- **§6.6.1 audit-doc cross-references** (`wave351-thm5-numerical.md`, `wave350-thm5.md`, `wave350-r5b-figure.md`) — unchanged. These are file-pointer references, not wave-number metadata, and are the load-bearing pointer trail for the byte-stable numerical validation.

### 2.4 Risk assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Substantive content loss during Wave metadata removal | LOW | Every substantive content element enumerated in §1.3 (verbatim preservation table); cross-checked against original Wave 351 + Wave 364 PG3 footnotes and Wave 342 Sub-claim 1.4 note |
| Number drift during rephrasing | LOW | `tools/check_claims_consistency.py` exits 0 (No drift detected); the §6 edits are in a paper-draft file (`docs/drafts/paper-A-final.md`), not in `docs/CLAIMS.md`, so number consistency is not under the claims-consistency verifier's scope; the §6 numerical quantities (L_local, eps_theta, sigma_blend, ratios) are byte-preserved per the verbatim-preservation table |
| Theorem statement / equation drift | LOW | All five theorems/lemmas (Theorems 4-5, Lemmas 1-3) preserved verbatim per §1.3; Eq. (4) / Eq. (5) / Eq. (6) preserved verbatim (sub-claim 5.4 prose references them by number) |
| Audit-trail gap | LOW | This file documents every line removed and every substantive content element preserved (§1.3 + §1.4) |
| Mkdocs strict breakage | LOW | `mkdocs build --strict` exits 0 (built in 21.59s); the §6 edits are in a paper-draft file, not in mkdocs-served content (`docs/` is mkdocs source, but `docs/drafts/` is excluded from mkdocs build) |
| D.4 regression drift | LOW | D.4 30/30 PASS; the §6 edits are in a paper draft, not in `adaptive_reflow/` code |

### 2.5 Smallest next action

No further action required for Phase 5. The §6 Theory de-wave is complete:

- All four in-scope destructive operations performed (§6 preamble note → parenthetical; §6.2 Sub-claim 1.4 note → merged prose; §6.6.1 Wave 351 + Wave 364 PG3 → single footnote; §6.7 final → plain Paper B cross-reference).
- All four verification gates PASS (D.4 30/30, ruff 0, claims consistency no drift, mkdocs strict builds).
- All Theorem 4 / Theorem 5 / Lemma 1-3 equations + statement numbers preserved verbatim.
- Audit trail documented (this file).
- Local commit pending (NO-PUSH; commit only).

---

## 3. Provenance

- **Wave:** Wave 367 P5 (Phase 5 of user-destructive rewrite, §6 Theory de-wave)
- **Sub-steps:** (1) Read §6 current state; (2) DELETE §6 preamble note; (3) §6.2 merge Sub-claim 1.4 note into prose; (4) §6.6.1 convert Wave 351 footnote to plain academic footnote; (5) §6.6.1 merge Wave 364 PG3 addendum into main footnote; (6) §6 final paragraph ADD Paper B cross-reference; (7) verify D.4 30/30 PASS + claims PASS + ruff 0 + mkdocs strict PASS; (8) author this audit doc; (9) local commit (NO-PUSH)
- **Pre-edit SHA-256:** `c6ece5636e8895b9ce876594f966cbc6ceab7e3437f8fec2fc0797bce2193773`
- **Post-edit SHA-256:** `9945d23aec95c829ed808c065a65062b4f066f9369e71e182fb6ab3760c2632b`
- **Net lines removed:** 22 (9 insertions, 31 deletions across 40 line operations)
- **Verification:** D.4 30/30 PASS, ruff 0 findings, claims consistency no drift, mkdocs strict builds in 21.59s
- **Hard guardrails honoured:** NO-PUSH; USER-EXPLICIT destructive override (user spec); Theorem 4 / Theorem 5 / Lemma 1-3 verbatim preservation; per-phase audit doc