# Wave 187 P1 — Camera-ready consistency final review (12 sections)

**Date:** 2026-09-18
**Branch:** main
**Scope:** Final review of all 12 sections added/updated across Waves
174-185 for camera-ready consistency: §10.20 – §10.30 (11 sections)
plus §11.1 (1 section). Verify (1) the (a)–(f) standard structure is
present in each section, (2) each wave's claim in §10 / §11 references
the correct CLM ID from `docs/CLAIMS.md`, and (3) cross-references
across sections are internally consistent.

**No source changes — audit doc only.** Findings are documented for
the camera-ready copy-edit pass; no code or paper-text modifications
are proposed here.

---

## 1. (a)–(f) standard structure audit

The (a)–(f) standard structure is the camera-ready template adopted
by Wave 178 onward: each section opens with an introductory
motivation paragraph, then labels its body paragraphs
**(a) Background / setup**, **(b) Protocol**, **(c) Results**,
**(d) Verdict**, **(e) Honest disclosure**, **(f) Acceptance gates**.
Sections authored before Wave 178 (§10.20 – §10.23, Wave 174-177)
predate this template and use the **bold-paragraph structure** that
was the camera-ready convention at the time of their authoring.

| §         | Wave | Authored | (a)–(f) structure? | Notes |
|-----------|------|----------|---------------------|-------|
| §10.20    | 174  | 2026-09-13 | **No (different pattern)** | Inline (a)/(b)/(c) enumeration inside the motivation prose; structured "Wave 174 fixed all three issues: (a) ... (b) ... (c) ..."; tables + bold paragraphs for results, disclosure, gates. Pre-template. |
| §10.21    | 175  | 2026-09-13 | **Partial: (a)–(d) only** | Has (a) Per-adapter NFE_REF mechanism, (b) Root cause, (c) P4/P5 numbers, (d) Honest verdict. Missing (e) honest disclosure as a labelled paragraph and (f) acceptance gates table (gates are bulleted inline in §10.21). |
| §10.22    | 176  | 2026-09-13 | **No (different pattern)** | Uses `**Primary metric for kanzi:**`, `**Wave 176 results...**`, `**The structural finding:**`, `**Where the framework demonstrates value:**`, `**The principled reframing:**`, `**Honest disclosure.**`, `**Wave 176 acceptance gates**` as bold paragraph headers. Pre-template. |
| §10.23    | 177  | 2026-09-13 | **Partial: (a)–(d) only** | Has (a) Lineageflow synthetic composite fix, (b) Kanzi real ckpt shape fix, (c) Wave 177 P3 lineageflow real re-run, (d) Honest disclosure. Missing (e)/(f) labelled sections (gates are bulleted inline). |
| §10.24    | 178  | 2026-09-13 | **Yes (a)–(f) + (g) gates** | (a) Root cause, (b) `_real_state_shape`, (c) `build_initial_state`, (d) `velocity_field` bridge, (e) end-to-end eval, (f) Honest verdict, (g) Acceptance gates. |
| §10.25    | 179  | 2026-09-13 | **Yes (a)–(f) + (g) verdict + (h) gates** | (a) Wave 174-178 evidence limitation, (b) Wave 179 setup, (c) Multi-seed aggregation, (d) Paired t-test, (e) Critical verdict, (f) Error-bar figures, (g) Updated `framework_wins_both_metrics_everywhere`, (h) Acceptance gates. |
| §10.26    | 180  | 2026-09-13 | **Yes (a)–(f)** | (a) Fast-DLLM background, (b) Protocol, (c) Results table, (d) Verdict, (e) Honest disclosure, (f) Acceptance gates. |
| §10.27    | 181  | 2026-09-13 | **Yes (a)–(f)** | (a) AB-Cache background, (b) Protocol, (c) Results table, (d) Verdict, (e) Honest disclosure, (f) Acceptance gates. |
| §10.28    | 184  | 2026-09-14 | **Yes (a)–(f)** | (a) Motivation, (b) Test matrix, (c) Per-model ablation table, (d) Verdict, (e) Honest disclosure — framework gain source attribution, (f) Acceptance gates. |
| §10.29    | 183  | 2026-09-14 | **Yes (a)–(f) + (g) figures + (h) gates** | (a) Motivation, (b) Protocol, (c) Per-model saturation boundary, (d) kanzi NFE sweet spots, (e) Anti-resonance confirmation, (f) Framework wins across 9-point ladder, (g) Three figures, (h) Acceptance gates. |
| §10.30    | 182  | 2026-09-14 | **Yes (a)–(f)** | (a) LeDiFlow background, (b) Protocol, (c) Results table, (d) Verdict, (e) Honest disclosure, (f) Acceptance gates. |
| §11.1     | 185  | 2026-09-18 | **Yes (a)–(f)** | (a) Motivation, (b) Empirical BL measurement, (c) Per-model tightness ratio, (d) Honest disclosure, (e) Why the bound is too tight, (f) Conclusion. |

**Summary.** 8 of 12 sections follow the full (a)–(f) structure
(§10.24, §10.25, §10.26, §10.27, §10.28, §10.29, §10.30, §11.1). Two
sections (§10.21, §10.23) use a partial (a)–(d) variant (4 of 6
labelled subsections, with the missing (e)/(f) handled inline in
bold paragraphs). Two sections (§10.20, §10.22) predate the (a)–(f)
template and use a bold-paragraph convention that was the
camera-ready standard at the time of their authoring.

**Verdict on (a)–(f) standard.** The template is **fully adopted for
Waves 178-185** (the most recent 8 sections). The pre-template
sections (§10.20, §10.22) and partial-template sections
(§10.21, §10.23) are **structurally equivalent** — each contains the
load-bearing components (motivation, protocol, results, disclosure,
acceptance gates) under equivalent heading conventions. Renormalising
these four sections to the (a)–(f) template is a **copy-edit
optionality**, not a structural requirement: their current
presentation is consistent with the camera-ready style of their
authoring wave.

---

## 2. Cross-reference audit (CLM IDs)

Each section that introduces a new claim ledger entry (CLM) should
reference that CLM ID in either the body or the acceptance gates.
The following table maps each §10.xx / §11.x section to its
corresponding CLM ID per `docs/CLAIMS.md` and counts the references
in `docs/paper-draft.md`.

| §         | Wave | Expected CLM | CLM definition (verbatim from CLAIMS.md) | Refs in paper-draft.md |
|-----------|------|--------------|-------------------------------------------|------------------------|
| §10.20    | 174  | (none)       | —                                         | n/a (no claim added)  |
| §10.21    | 175  | (none)       | —                                         | n/a (no claim added)  |
| §10.22    | 176  | (none)       | —                                         | n/a (no claim added)  |
| §10.23    | 177  | (none)       | —                                         | n/a (no claim added)  |
| §10.24    | 178  | (none)       | —                                         | n/a (no claim added)  |
| §10.25    | 179  | (none)       | —                                         | n/a (no claim added)  |
| §10.26    | 180  | **CLM-048**  | "Wave 180 — FlowA wins on both metrics vs both baselines (vanilla + Fast-DLLM) at both NFE settings on the R6 task (LineageFlow protein re-inference)" | **0** ⚠ |
| §10.27    | 181  | **CLM-050**  | "Wave 181 — FlowA wins on both metrics vs all three baselines (vanilla + Fast-DLLM + AB-Cache) at both NFE settings on the R6 task (LineageFlow protein re-inference)" | 1 (acceptance gates row 3) ✓ |
| §10.28    | 184  | **CLM-049**  | "Wave 184 — n_rounds ablation isolates the kanzi NFE=100 pLDDT regression mechanism (both paper-quantity scheduler primary + multi-round averaging secondary, on kanzi; restart-blend glue path only, on lineageflow)" | **0** ⚠ |
| §10.29    | 183  | **CLM-051**  | "Wave 183 — Finer NFE curve resolves anti-resonance at kanzi NFE=100 (CONFIRMED) and saturation boundaries (lineageflow saturates at NFE=500, kanzi does not saturate in [10, 500]); framework wins both metrics at 10/18 (model,NFE) cells with both-models intersection at NFE=75 only" | 2 (headline framing + acceptance gates row 3) ✓ |
| §10.30    | 182  | **CLM-053**  | "Wave 182 — FlowA wins on both metrics vs all four baselines (vanilla + Fast-DLLM + AB-Cache + LeDiFlow) at both NFE settings on the R6 task (LineageFlow protein re-inference); FlowA exploits per-token paper quantities (selection_ratio / e_rho) while LeDiFlow exploits a learned per-family prior shift — paper-quantity-driven vs learned-distribution-guided" | 1 (acceptance gates row 3) ✓ |
| §11.1     | 185  | **CLM-052**  | "Wave 185 — Theorem 1's BL-convergence bound is tight on framework self-convergence but uniformly too tight (25×–7,522×) for framework-vs-baseline on protein; the bound's claim scope is relocated to framework self-distance (NOT framework-vs-baseline value-add)" | 1 (acceptance gates row 3) ✓ |

**Findings.**

1. **CLM-048 missing from §10.26** (Wave 180 Fast-DLLM). The
   claim is fully defined in `docs/CLAIMS.md` (line 1807) but the
   paper-draft.md body does not mention it. The acceptance gates
   row 3 mentions "39 active" (Wave 180 P3 state) without naming
   CLM-048 explicitly. This is a **minor cross-reference gap**.

2. **CLM-049 missing from §10.28** (Wave 184 n_rounds ablation).
   The claim is fully defined in `docs/CLAIMS.md` (line 1869) but
   the paper-draft.md body does not mention it. The acceptance
   gates row 3 mentions "41 active" (Wave 184 state) without
   naming CLM-049 explicitly. This is a **minor cross-reference
   gap**.

**Cross-reference verdict.** 4 of 6 expected CLM references are
present (CLM-050, CLM-051, CLM-052, CLM-053). The two gaps
(CLM-048 in §10.26, CLM-049 in §10.28) are **wording-level gaps**
— the underlying claim is in the ledger, the body of the section
makes the claim without naming the CLM ID. A 2-line copy-edit per
section closes both gaps (e.g., add "CLM-048" to §10.26 row 3 of
the acceptance gates, add "CLM-049" to §10.28 row 3 of the
acceptance gates).

---

## 3. Internal consistency checks

Beyond (a)–(f) and CLM references, the 12 sections are consistent
along the following axes:

### 3.1 ADDITIVE disclaimer (every section)

All 12 sections include the **ADDITIVE only — does not delete or
rewrite any §10.x–§10.y paragraph above** disclaimer at the end.
This is required for the §10.x additive-chaining convention (each
new wave is APPENDED, never replaces prior §10.x content).

| §         | ADDITIVE disclaimer present? | References preserved |
|-----------|------------------------------|----------------------|
| §10.20    | ✓ (§10.1–§10.19)            | ✓                    |
| §10.21    | ✓ (§10.1–§10.20)            | ✓                    |
| §10.22    | ✓ (§10.1–§10.21)            | ✓                    |
| §10.23    | ✓ (§10.1–§10.22)            | ✓                    |
| §10.24    | ✓ (§10.1–§10.23)            | ✓                    |
| §10.25    | ✓ (§10.1–§10.24)            | ✓                    |
| §10.26    | ✓ (§10.1–§10.25)            | ✓                    |
| §10.27    | ✓ (§10.1–§10.26)            | ✓                    |
| §10.28    | ✓ (§10.1–§10.27)            | ✓                    |
| §10.29    | ✓ (§10.1–§10.28)            | ✓                    |
| §10.30    | ✓ (§10.1–§10.29)            | ✓                    |
| §11.1     | ✓ (§2.8.1)                  | ✓ (Theorem 1 statement preserved verbatim) |

### 3.2 Acceptance gates table (every §10.x with new code/eval)

All 10 §10.x sections (excluding §11.1 which is theory only) include
an **Acceptance gates** table or bulleted list with the canonical
4-row format (D.4 byte-stable / Ruff lint / Claims consistency /
Wave N acceptance). The full format is uniformly applied for
§10.26-§10.30; §10.20-§10.25 use a slightly earlier 3-bullet
format (D.4 / Ruff / Claims) plus the wave-specific eval check.

| §         | Acceptance gates format            |
|-----------|------------------------------------|
| §10.20    | 3 bullets (D.4, Ruff, Claims) + Wave 174 acceptance note |
| §10.21    | 3 bullets (D.4, Ruff, Claims)      |
| §10.22    | 4 bullets (D.4, Ruff, Claims, push) |
| §10.23    | 4 bullets (D.4, Ruff, Claims, re-run) |
| §10.24    | Full table (4 rows)                |
| §10.25    | Full table (5 rows)                |
| §10.26    | Full table (4 rows)                |
| §10.27    | Full table (4 rows)                |
| §10.28    | Full table (5 rows)                |
| §10.29    | Full table (6 rows)                |
| §10.30    | Full table (5 rows)                |
| §11.1     | Full table (6 rows)                |

### 3.3 Cross-section consistency (model-asymmetric narrative)

The §10.20 (Wave 174) "model-asymmetric" framing — lineageflow
**uniform-win** + kanzi **scPerp uniform-win + pLDDT trade-off** — is
preserved verbatim through §10.21-§10.23 (no narrative drift). The
§10.24-§10.27 sections preserve the lineageflow wins, the
§10.28-§10.29 sections refine the kanzi NFE=100 anti-resonance, and
§10.30 (LeDiFlow) re-establishes the lineageflow-only headline on
the R6 task. **No model-asymmetric drift detected.**

### 3.4 Numeric consistency (claims ledger vs paper)

The §10.x headline numbers (pLDDT, scPerp, win margins) match the
numbers in `docs/CLAIMS.md` for each corresponding CLM entry to the
precision reported (typically 2-4 decimal places). Specifically:

- §10.26 / CLM-048: FlowA pLDDT 43.828 (NFE=100), 43.629 (NFE=200) ✓
- §10.27 / CLM-050: 4-arm headline ranking matches CLM-050 evidence ✓
- §10.28 / CLM-049: kanzi ΔpLDDT -1.63 at n_rounds=1 ✓
- §10.29 / CLM-051: lineageflow 9/9 wins, kanzi 1/9 wins ✓
- §10.30 / CLM-053: 5-arm headline ranking matches CLM-053 evidence ✓
- §11.1 / CLM-052: tightness ratio 25×-7,522× ✓

### 3.5 Section interdependencies (forward references)

The §10.26 (Wave 180) / §10.27 (Wave 181) / §10.30 (Wave 182)
sections cross-reference each other consistently in the closing
prose ("head-to-head with Fast-DLLM", "head-to-head with AB-Cache",
"head-to-head with LeDiFlow"). The §10.28 (Wave 184) / §10.29 (Wave
183) sections cross-reference the §10.20-§10.25 lineage correctly.
**No forward-reference gaps detected.**

---

## 4. Verdict

**Sections reviewed:** 12 (§10.20 – §10.30 + §11.1).

**Findings.**

1. **(a)–(f) structure.** 8 of 12 sections use the full template
   (§10.24 – §10.30 + §11.1). 2 use the partial (a)–(d) variant
   (§10.21, §10.23). 2 pre-date the template (§10.20, §10.22) and
   use a bold-paragraph convention that was camera-ready at the
   time of authoring. The 4 non-(a)–(f) sections are
   **structurally equivalent** — all required components
   (motivation, protocol, results, disclosure, gates) are present
   under equivalent heading conventions. Renormalisation to the
   full (a)–(f) template is a copy-edit optionality, not a
   structural gap.

2. **CLM cross-reference.** 4 of 6 expected CLM references are
   present. Two minor wording-level gaps:
   - CLM-048 not named in §10.26 body or acceptance gates
   - CLM-049 not named in §10.28 body or acceptance gates

3. **Internal consistency.** ADDITIVE disclaimer present in all 12
   sections. Acceptance gates table or bulleted list present in all
   12 sections. Cross-section narrative is internally consistent.
   Numeric values match the corresponding CLM evidence.

**Ready for compression:** **YES**, with **2 minor copy-edit items**
(CLM-048 reference in §10.26 row 3 of acceptance gates; CLM-049
reference in §10.28 row 3 of acceptance gates). These are
wording-level (one phrase per section) and do not affect the
technical content, the (a)–(f) structure, or any cross-reference.
The 12 sections are **camera-ready consistent** modulo these two
optional copy-edits.

---

## 5. Suggested copy-edit (optional, deferred to Wave 5+)

If a reviewer requests 100% CLM-claim-naming coverage:

- **§10.26 acceptance gates row 3.** Change
  "**No drift detected.** (39 active, 0 provisional, 2 deprecated)"
  → "**No drift detected.** (39 active after Wave 180 P3 + CLM-048,
  0 provisional, 2 deprecated)".
- **§10.28 acceptance gates row 3.** Change
  "**No drift detected.** (41 active, 0 provisional, 2 deprecated)"
  → "**No drift detected.** (41 active after Wave 184 P4 + CLM-049,
  0 provisional, 2 deprecated)".

These are 1-line additions to align the camera-ready copy with the
§10.27 / §10.29 / §10.30 / §11.1 convention. Out of scope for Wave
187 P1; flagged for a future copy-edit pass.

---

## 6. Acceptance gates (Wave 187 P1, audit-only)

| # | Gate | Result |
|---|------|--------|
| 1 | All 12 sections read end-to-end | ✓ (§10.20, §10.21, §10.22, §10.23, §10.24, §10.25, §10.26, §10.27, §10.28, §10.29, §10.30, §11.1) |
| 2 | (a)–(f) structure audit | 8/12 full template, 2/12 partial, 2/12 pre-template (structurally equivalent) |
| 3 | CLM cross-reference audit | 4/6 references present; 2 wording-level gaps (CLM-048, CLM-049) flagged |
| 4 | ADDITIVE disclaimer check | 12/12 present |
| 5 | Acceptance gates check | 12/12 present (table or bulleted) |
| 6 | Numeric consistency check | All §10.x headline numbers match CLM evidence to reported precision |
| 7 | D.4 / Ruff / Claims drift | D.4 33/33 PASS preserved (per §10.30 / §11.1 gate rows); no source changes in this audit |

**No source code changes. No paper-text changes. Audit doc only.**
