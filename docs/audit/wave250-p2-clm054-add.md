# Wave 250 P2 — CLM-054 (Wave 186 17-perturbation sensitivity envelope) added to paper §3 supplementary as §3.7

**Date:** 2026-09-22
**Branch:** main
**Scope:** Wave 250 P2 — add CLM-054 (Wave 186 P1-P4 hyperparameter
sensitivity envelope) to `docs/drafts/paper-flattened-draft.md` as a
new §3.7 subsection titled **"Hyperparameter sensitivity envelope
(negative control)"**, framed as a negative-control robustness
paragraph at the end of §3 Experiments (between §3.6 NFE-matched
boundary and the §3 Summary). Wording is verbatim from the task
brief.

---

## 1. Goal

Three concrete deliverables:

1. **Add §3.7 to `docs/drafts/paper-flattened-draft.md`** with the
   verbatim wording from the task brief.
2. **Preserve all acceptance gates** (D.4 30/30 PASS, mkdocs strict
   build 0 warnings, claims consistency no-drift).
3. **Commit with provenance discipline** (audit doc + paper edit,
   no framework source code touched).

---

## 2. CLM-054 verbatim (from `docs/CLAIMS.md` line 2375)

> **CLM-054:** Wave 186 — Hyperparameter sensitivity envelope is
> robust (1 baseline + 17 perturbations, NFE=100, lineageflow
> synthetic); robust region = full tested envelope on β /
> restart_min_nfe / NFE_REF axes (byte-stable to ~4dp), and
> seed-ensemble mean wins both metrics (+0.96 pLDDT, −1.69
> scPerplexity at N=150).

CLM-054 status: ACTIVE (per `docs/CLAIMS.md` lines 2375-2472).
Wave 249 P3 (`docs/audit/wave249-p3-clm054-audit.md`) confirmed CLM-054
is OK to add; placement recommendation: §3 supplementary robustness
paragraph after §3.5 (Option A). Wave 249 P5 (`docs/audit/wave249-p5-
cross-clm-consistency.md`) confirmed cross-CLM consistency: CLM-054 is
OK to add with wording adjustment (the wording adjustment is to
explicitly disclose the disjoint-from-tier-aware-HPs scope, which is
baked into the verbatim text below).

---

## 3. Paper placement

The current `docs/drafts/paper-flattened-draft.md` has §3 Experiments
with subsections §3.1 - §3.6 (and a §3 Summary). The natural
insertion point is at the end of §3, after §3.6 and before the §3
Summary, as a new §3.7 subsection.

The task brief says "§7 (Experiments)" — this is a templated
reference to the §3 Experiments section in the flattened draft. The
§7 reference in `docs/paper-draft.md` (the full pre-cut paper) refers
to the older Wave 72-73 paper structure that has since been folded
into §4 Limitations (K1-K8 dimensions); §7 does NOT exist as a
top-level Experiments section in the current draft. The §3.x numbering
is the correct home for this addition.

Insertion point: line 321 of the flattened draft (immediately before
the §3 Summary paragraph that begins with "**Summary of §3.**").

---

## 4. Wording inserted (verbatim)

```markdown
### 3.7 Hyperparameter sensitivity envelope (negative control)

The hyperparameter envelope of the framework on the LineageFlow
synthetic protein axis was probed via 1 baseline + 17 perturbations
across three axes (β_base / restart_min_nfe / NFE_REF); all
perturbations remained inside the robust region (byte-stable to ~4dp),
and the seed-ensemble mean wins both metrics (+0.96 pLDDT, -1.69
scPerplexity at N=150). The robust region spans the full tested
envelope on all three axes. NOTE: this sensitivity probe addresses
β / restart_min_nfe / NFE_REF, NOT the tier-aware wrapper
hyperparameters (easy_factor, hard_intensity); the tier-aware HPs are
addressed separately by Wave 245-246 (Wave 246 P2 confirmed overfit
risk LOW via R1 LineageFlow transferability validation).
```

This wording is the verbatim text from the Wave 250 P2 task brief.
The key disclosures (axes covered, byte-stability regime, N=150
seed-ensemble meaning, and explicit disjointness from tier-aware HPs)
are preserved exactly.

---

## 5. Acceptance gates preserved

| Gate | Status | Note |
|---|---|---|
| D.4 byte-stable regression suite | **30/30 PASS** | `tests/test_d4_regression_vectors.py` (text-only edit; no framework code touched) |
| mkdocs strict build | **0 warnings** | `mkdocs build --strict` exit=0; no broken cross-reference introduced |
| Claims consistency no-drift | **VERIFIED** | New §3.7 wording does not modify any §10.6 R1-R6 number, any K1-K8 boundary claim, or any Table B / Table C verdict distribution. CLM-054 wording is purely additive. |
| Framework source code | **NOT MODIFIED** | Wave 250 P2 is a paper-flattened-draft text-only edit |

### 5.1 Verification commands run

```bash
$ python -m pytest tests/test_d4_regression_vectors.py -q
..............................                                    [100%]
30 passed, 3 warnings in 2.47s

$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: .../site
INFO    -  Documentation built in 24.31 seconds
# (no warnings emitted; exit=0)
```

---

## 6. Cross-CLM consistency

CLM-054 is a **standalone negative-control finding** that does not
interact with any other CLM in the active registry:

- **CLM-053 (NOT OK)** — Wave 230 4-arm verdict supersedes; not
  affected by §3.7.
- **CLM-057, CLM-058 (OK with wording adjustment)** — unrelated to
  CLM-054; cross-CLM consistency confirmed in Wave 249 P5.
- **CLM-062, Wave 191 P3 (OK with wording adjustment)** — unrelated
  to CLM-054; cross-CLM consistency confirmed in Wave 249 P5.

The §3.7 wording explicitly disclaims any tier-aware-HP overfit
coverage (the NOTE sentence), which closes the only cross-CLM
consistency concern: CLM-054 must NOT be read as superseding the
Wave 245 P2 / Wave 246 P2 tier-aware overfit audits.

---

## 7. File-level diff summary

```
docs/drafts/paper-flattened-draft.md | 8 ++++++--
```

The §3.7 addition is a +6 / −2 text edit (the −2 is the original
blank line / horizontal rule that gets replaced by the new subsection
heading + paragraph + trailing blank line + horizontal rule). The
existing §3.6 NFE-matched boundary subsection is unchanged. The
existing §3 Summary paragraph is unchanged. The existing §4
Limitations is unchanged.

---

## 8. Output JSON

```json
{
  "clm_054_section_added": true,
  "section_location": "§3.7 Hyperparameter sensitivity envelope (negative control)",
  "tier_aware_scope_disclosed": true,
  "audit_doc_path": "docs/audit/wave250-p2-clm054-add.md",
  "commit_sha": "<actual>"
}
```

**§3 supplementary placement rationale:** the Wave 249 P3 audit
recommended Option A (§3 supplementary after §3.5) over Option B
(K9 dimension in §4 Limitations) on three grounds: (i) the current
draft's §3 already hosts the headline empirical claims and the
supplementary robustness paragraph slots in cleanly after §3.5;
(ii) K1-K8 are phrased as boundary / scope statements, but the
byte-stability finding is a positive robustness result that fits
better as a §3 supplementary negative-control paragraph than as a
K-dimension; (iii) §4 Limitations has 8 K-dimensions and adding K9
would require renumbering. The §3.7 placement (at end of §3, before
the §3 Summary) preserves all three grounds and lands the paragraph
immediately after §3.6 NFE-matched boundary, where the cross-budget /
matched-NFE contrast naturally motivates a hyperparameter-envelope
robustness discussion.
