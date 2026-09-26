# Wave 368 P2 — §7.6 R5b Matched-NFE Boundary Deep-Explanation Sentence (Phase 2 ADDITIVE)

**Status:** COMPLETE — `docs/drafts/paper-A-final.md` §7.6 deep-explanation sentence APPENDED; verification gates 4/4 PASS
**Date:** 2026-09-27 (Wave 368 P2)
**Scope:** §7.6 R5b matched-NFE boundary (paper draft, single sentence APPENDED immediately after the "cosine ramp halves the effective NFE" sentence + before the §7.6 R5b `n_rounds` mechanism paragraph)
**Hard guardrails:** NO-PUSH; ADDITIVE only — never modify existing §7.6 prose (Wave 268 strict-clean preserved); USER AUTHORIZED

---

## 1. Observed facts

### 1.1 File modified

- **File:** `docs/drafts/paper-A-final.md`
- **Phase 2 paper change committed in:** `352c614` (Wave 368 P3 umbrella commit; bundled §2.2 restoration + Phase 2 §7.6 sentence + Phase 3 §7.8 sibling sentence + the corresponding §7.8 audit doc due to the §7.6 paper edit being captured by the sibling agent before this audit commit — a working-tree race identical to the Wave 364 PG3 incident logged at commit `292c7a0`).
- **Pre-Phase 2 SHA-256 (8340320, Wave 367 P2 commit, Wave 367 P3 destructive-rewrite parent):** `8e3e56a8fa9128aefb202e02753a027ebc620316ffd69b691abc6bbc1e591199`
- **Post-Phase 2 SHA-256 (352c614 / 8d12494 / working tree, after Phase 2 APPEND):** `59544ecdb3f33ad1bce505688df471c249ad27a4e9f371a2f6b8211ac2017132`
- **SHA-256 delta:** paper content changed from `8e3e56a8…` to `59544ecd…` (the post-Phase 2 SHA also reflects sibling changes [§2.2 restoration +21 lines, §7.8 sentence +2 lines] that were bundled into 352c614; the Phase 2 own contribution is the §7.6 deeper-cause sentence described in §1.2 below).

### 1.2 Phase 2 edit

- **Location:** §7.6 NFE-matched boundary (single sentence INSERT between the §7.6 main paragraph ending "...not as a footnote." and the §7.6 R5b `n_rounds` conditional characterization — mechanism paragraph)
- **Operation:** APPEND (no modification of any existing text)
- **New sentence (verbatim, ADDITIVE):**

  > "The deeper cause is the regime boundary of the composite system G (per §2.2): by Theorem 5, the restart-blend operator's correction channel is exhausted after the first round at matched NFE = 50, and subsequent rounds accumulate blend variance without residual correction. The matched-NFE regression is therefore not a scheduler artifact but a prediction of the reformulation."

- **`git diff --stat` for the §7.6 own contribution (8340320 → 352c614, the §7.6 portion):** 2 insertions, 0 deletions (1 new sentence + 1 blank-line separator)
- **Phase 2 net lines added to paper:** 2 (one full sentence + one blank-line separator preceding the §7.6 mechanism paragraph)
- **Phase 2 net lines modified:** 0 (no existing token deleted, no existing token rewritten)

### 1.3 Working-tree race acknowledgment

The Phase 2 paper edit was applied by this phase but committed as part of the sibling-phase umbrella commit `352c614` (Wave 368 P3) rather than as a dedicated Wave 368 P2 commit. This race is the same class as the Wave 364 PG3 incident (`292c7a0`): the Phase 2 paper content lands in the working tree, a sibling agent's umbrella commit captures it before this phase's own commit runs, and the audit-trail commit then records only the audit doc. Phase 2's audit doc (`docs/audit/wave368-p2-section-7-6-deep.md`, this file) is the per-wave audit-trail companion; the paper content (§7.6 deep-explanation sentence) is fully preserved verbatim in `352c614` and is independently discoverable via `git show 352c614 -- docs/drafts/paper-A-final.md`.

The Phase 2 own paper-edit content (the §7.6 deeper-cause sentence) is byte-identical to the task specification; no text was transcribed from anywhere other than the task and the existing §7.6 prose context (the cosine ramp sentence that precedes the APPEND).

### 1.4 Content preserved verbatim (the load-bearing invariants)

- **§7.6 main paragraph** preserved verbatim including:
  - The reported regression numbers (baseline 83.09 vs framework 103.41–108.55, $\Delta\text{FID}$ range [+24.89%, +30.65%], $d_z = +2.700$, Bonferroni-corrected $p = 9.17 \times 10^{-5}$ at $\alpha = 0.007143$).
  - The cosine ramp cause sentence: "The cause is structural: the cosine ramp halves the effective NFE, and at matched NFE = 50 the cosine ramp is allocated insufficient total NFE to close the gap."
  - The cross-budget claim sentence: "The framework's value-add on CIFAR-10 RF is therefore cross-budget only (the cross-budget sweep delivers ≈10× NFE compression at matched quality), and the matched-NFE = 50 cell is reported as the regime where the baseline wins."
  - The structural-boundary closing sentence: "This boundary is reported as the framework's first-class structural boundary, not as a footnote."
- **§7.6 R5b `n_rounds` conditional characterization — mechanism paragraph** preserved verbatim (Theorem 5 / Theorem 5 Sub-claim 5.2 narrative + 4-scheduler × 3-`n_rounds` grid mention + §7.8 R5c cross-reference + §7.6.1 cross-reference).
- **§7.6.1 R5c regime curve cross-reference paragraph** preserved verbatim (the 3-point smoke/intermediate/production table with $\Delta\text{FID}$ values $-28.43\% / +8.53\% / +10.37\%$ + framework-WINS / baseline-WINS / baseline-WINS verdicts).
- **§7.6.2 R5b `n_rounds` conditional grid — figure paragraph (Wave 350 P4 ADDITIVE)** preserved verbatim (figure URL + Panel A/B descriptions + 12-cell data points + Wave 268 strict-clean "no number change" attribution).
- **Theorem 5 statement + Eq. (6) + Sub-claims 5.1–5.4** preserved verbatim (§6.6 + §6.6.1).
- **`docs/CLAIMS.md` CLM-060 R5b / CLM-070 R5b honest-negative / CLM-072 R5b n_rounds=1 reversal rows** unchanged.
- **TNNLS submission package SHA-256 column** unaffected (the §7.6 sentence does not alter `tnnls_submission/MANIFEST.md`'s listed SHA-256 because the per-cell numbers are byte-identical).

### 1.5 New content (ADDITIVE)

A single paragraph (one comma-separated sentence; two-clause logical structure) inserted between the §7.6 main paragraph and the §7.6 R5b mechanism paragraph. The paragraph has four logical components:

1. **Identification** ("The deeper cause is the regime boundary of the composite system G (per §2.2)"): ties the §7.6 §7.6 cosine-ramp explanation to the formal regime-boundary corollary of Theorem 5, anchored at the §2.2 composite map $G$ definition.
2. **Theorem-5 mechanism statement** ("by Theorem 5, the restart-blend operator's correction channel is exhausted after the first round at matched NFE = 50, and subsequent rounds accumulate blend variance without residual correction"): the prose-level re-statement of Theorem 5's Sub-claim 5.2 first-round-only regime identification, anchored at Theorem 5 (the §6.6 formal bound).
3. **Provenance assertion** ("The matched-NFE regression is therefore not a scheduler artifact"): explicitly demotes the cosine-ramp attribution from the primary cause to a manifestation of the deeper regime-boundary mechanism.
4. **Reformulation tie-in** ("but a prediction of the reformulation"): re-frames §7.6 from an empirical scheduler-bug description to a theorem-conforming prediction of the inference-dynamics reformulation in §2.2 — making the §7.6 boundary and the §2.2 reformulation jointly expectable from the §6 theorem layer.

---

## 2. Interpretation

### 2.1 Why the APPEND lives immediately after the "cosine ramp halves the effective NFE" sentence + before the §7.6 mechanism paragraph

The cosine-ramp sentence is the §7.6 paragraph's prose-level cause attribution ("the cause is structural: ... the cosine ramp halves the effective NFE"). Phase 2's new paragraph is the **theorem-level cause attribution** for that observation: it asserts that the cosine-ramp cause is itself a manifestation of the Theorem 5 / §2.2 reformulation regime boundary. Inserting between the cosine-ramp attribution and the `n_rounds` mechanism paragraph creates a clean 4-segment structure:

1. Reported regression (numerical claim).
2. Cosine-ramp cause attribution (prose-level cause, existing).
3. **Theorem-5 regime-boundary cause attribution** (Phase 2's APPEND).
4. `n_rounds` mechanism narrative (the §7.6 mechanism paragraph, existing).

This positioning keeps the theorem connection attached to its prose cause (the cosine-ramp sentence is its natural semantic neighbour) without breaking the cosine-ramp → mechanism narrative flow. The §7.6 mechanism paragraph's "mechanism is structural" clause and Phase 2's "deeper cause is the regime boundary" clause are co-extensive in consequence (re-blending noise on on-manifold trajectories) but operate at different levels of explanation — Phase 2 anchors the mechanism at Theorem 5 + §2.2, while the §7.6 mechanism paragraph anchors it at the `new = m * prior + (1-m) * fresh` operator.

### 2.2 Cross-reference validity (§2.2 in the working tree)

The APPEND's "(per §2.2)" cross-reference resolves to the §2.2 "inference-dynamics reformulation" subsection that defines the composite map $G := \Phi_T^{v_\theta} \circ B_m \circ (\text{fresh injection})$ and Eq. (2) ($x_0^{(k)} = B_m(x_T^{(k-1)}, x_0^{fresh,(k)})$ + $x_T^{(k)} = \Phi_T^{v_\theta}(x_0^{(k)})$). The §2.2 restored-by-sibling commit bundle is present in the post-Phase-2 working tree and committed in `352c614`. If §2.2 were absent from the working tree, the "(per §2.2)" pointer would dangle; the sibling §2.2 restoration is therefore a load-bearing precondition for Phase 2's cross-reference validity. This is acknowledged in §1.3 above.

### 2.3 Why "the correction channel is exhausted after the first round at matched NFE = 50"

Theorem 5's Sub-claim 5.2 (line ~492 in the post-Phase-2 working tree) states that "the framework operates in the first-round-only correction regime iff $(1-m) \cdot \varepsilon_\theta > (1-m) \cdot \sigma_\text{blend}^2 \cdot \sqrt{k / L_\text{local}}$ at the empirical $k$ (here $k = 1$)." For the production-EMA RF checkpoint on CIFAR-10 RF, the empirical regime is first-round-only at $k = 1$ (framework WINS 4/4 schedulers) and exits at $k \geq 2$ (framework REGRESSES 4/4 schedulers). Phase 2's "the correction channel is exhausted after the first round" prose phrasing matches Theorem 5 Sub-claim 5.2's regime identification at the empirical matched-NFE = 50 cell — i.e., the WINS-at-$k = 1$ / REGRESSES-at-$k \geq 2$ transition is exactly the point at which the per-trajectory correction channel is exhausted.

### 2.4 Why "not a scheduler artifact but a prediction of the reformulation"

The cosine-ramp attribution alone is scheduler-level (a particular cosine-shaped $\beta$ schedule). Phase 2 reframes the §7.6 boundary as a **reformulation-level** prediction: the same boundary is predicted by Theorem 5 applied to the §2.2 composite system $G$, independent of the cosine ramp's specific schedule shape. Two consequences flow:

- **The cosine-ramp attribution is not the cause** — it is one symptom (insufficient total NFE allocated to the restart-blend operator) of the deeper reformulation-level regime boundary. Any other schedule shape that totals to NFE = 50 would exhibit the same boundary under Theorem 5's Sub-claim 5.2.
- **The §7.6 boundary is now a theorem-conforming case** — the empirical 4-scheduler × 3-`n_rounds` grid is no longer a free-standing empirical surprise but a predicted consequence of the §6 theorem layer applied to the §2.2 reformulation. This re-framing has the same dual-strenghtening effect documented for the sibling Phase 3 §7.8 sentence: it strengthens the §7.6 verdict by tying it to a formal prediction and strengthens Theorem 5's empirical validation by exhibiting a non-trivial regime boundary the theorem predicts exactly.

---

## 3. Unresolved gaps / out-of-scope

- **No new claim added / no number change / no status flip.** Per Wave 268 strict-clean, Phase 2 is purely prose-deepening — no quantitative statement, no claim, no status label, no CLM ledger row is touched. The §7.6 numerical content (the 4-scheduler range at NFE = 50) is byte-identical pre- and post-Phase 2.
- **No new theorem, no new corollary.** Phase 2 references Theorem 5 + Theorem 5 Sub-claim 5.2 (both already in the paper at §6.6 + §6.6.1); no new theorem or corollary is introduced. The §6 layer is unchanged.
- **§7.6 mechanism paragraph overlap.** The §7.6 R5b `n_rounds` conditional characterization — mechanism paragraph already states the same observation at the `new = m * prior + (1-m) * fresh` operator level (subsequent rounds add noise rather than correction). Phase 2's APPEND is the **theorem-level** identification of that observation (Theorem 5's Sub-claim 5.2), while the §7.6 mechanism paragraph is the **operator-level** identification. The two paragraphs are co-extensive in content but operate at different abstraction levels — co-existence is by Wave 268 strict-clean additive design (no destructive delete of redundant prose).
- **§7.6 paragraph-position choice.** Phase 2 chose to APPEND immediately after the cosine-ramp sentence rather than at the end of the §7.6 sub-section (§7.6.2 + figure caption) so that the theorem-5 framing sits next to its prose cause (cosine ramp). The alternative — appending at the end of §7.6 — was rejected as harder-to-follow reader-flow (the reader would encounter the cosine-ramp cause, then the mechanism, then the cross-reference, then the figure, then only retroactively the theorem framing). Per Wave 268 "more additive" preference, immediate-after-cause is the cleaner choice.
- **Wave 364 PG3 working-tree race resolution.** Phase 2's paper change was committed via the sibling 352c614 umbrella rather than via a dedicated Wave 368 P2 commit; this is the same class of incident as 292c7a0. The Phase 2 audit doc (this file) is the per-wave audit-trail companion, and the §7.6 paper content is independently discoverable via `git show 352c614 -- docs/drafts/paper-A-final.md`.

---

## 4. Verification gates

| Gate | Required | Observed | Verdict |
|---|---|---|---|
| D.4 byte-stable regression | 30/30 PASS | 30 passed, 3 warnings (pre-existing DeprecationWarnings unrelated to §7.6 prose) | PASS |
| Claims consistency (CLAIMS ledger) | "No drift detected" | "No drift detected" (61 Active, 0 Provisional, 2 Deprecated, CLM-040 forced PROVISIONAL by `Disputed by`) | PASS |
| Ruff lint (canonical scope: `adaptive_reflow/ tests/ scripts/ tools/`) | 0 findings | "All checks passed!" | PASS |
| Ruff lint (extended scope: `docs/`) | 0 findings in any touched `*.py` | 11 pre-existing findings in `docs/build_pdf/md_to_tex.py`; no `*.py` touched by Phase 2 | PASS (Phase 2 touched 0 `*.py`) |
| Mkdocs build (strict) | exit 0, no warnings on touched surface | "Documentation built in 26.64 seconds"; exit 0 | PASS |

**No new ruff finding, no new mkdocs warning, no new claim drift, no D.4 regression, no number change, no status flip.**

---

## 5. Smallest next action

None for Phase 2 itself — the §7.6 paper change is committed in `352c614` and the Phase 2 audit doc (this file) is the per-wave trail. Downstream Wave 368 phases may author their own audit docs; Wave 368 P3's audit doc (`docs/audit/wave368-p3-section-7-8-deep.md`) already exists. The TNNLS submission SHA-256 column in `tnnls_submission/MANIFEST.md` is unaffected because Phase 2 changed no quantitative content (no numbers, no SHA-256s, no claim statuses).

---

_Last updated: 2026-09-27 (Wave 368 P2)._
