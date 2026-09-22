# Wave 231 P3 — Wording Fix Audit

**Date:** 2026-09-21
**Wave:** 231 P3
**Scope:** Replace "statistically indistinguishable" with positive
"does not regress against distillation baselines" framing across the
paper draft and cover letter, in response to DeepSeek critique of the
null-finding wording.

## 1. Background — DeepSeek Critique

DeepSeek's review of the Wave 229 P1 / Wave 230 P2 paper-draft language
flagged the phrase "statistically indistinguishable from [baselines]" as
misleading: it frames the framework-vs-baseline comparison as a **null
finding**, when in fact the per-record paired-$t$ data shows that the
framework **does not regress against any of the three distillation
baselines (FastDLLM, AB-Cache, LeDiFlow)** — this is a **positive
finding** (no regression), not a null finding (no effect).

The distinction matters for reviewer framing: a reader who sees
"statistically indistinguishable" may infer the framework has **no value**
versus distillation baselines, whereas the actual verdict distribution is
**0 of 16 cells regress** at Bonferroni-corrected α = 0.003125 (Wave 230
P2 real per-record paired data, df = 299). The empirical evidence says
"framework is non-regressing at per-record granularity" — a quantitative
positive claim, not a null result.

## 2. Scope

**Files scanned:**
- `docs/drafts/*.md`
- `docs/cover-letter-tpami.md`

**Grep patterns:**
- `indistinguishable`
- `no significant difference`
- `no-significant-difference`
- `no significant`
- `insignificant`

## 3. Before-state Counts (target files)

| Phrase | Occurrences |
| --- | --- |
| `indistinguishable` | 1 |
| `no significant difference` | 0 |
| `no-significant-difference` | 0 |
| `insignificant` | 0 |

**Single occurrence location:** `docs/drafts/methods-why-per-record.md`
line 561 (context: "the framework's per-record effect against the three
distillation baselines (FastDLLM, AB-Cache, LeDiFlow) is statistically
indistinguishable from zero, not a framework loss").

This is the only occurrence in the target files. Note: the phrase
"indistinguishable from zero" in the original text refers to the
**per-record effect size being effectively zero** (no regression against
the three baselines), not to a comparison between two distributions being
indistinguishable in the abstract null-hypothesis sense. The replacement
preserves the meaning (no regression) and applies the positive framing
from the Wave 231 P3 task spec.

## 4. Replacement Applied

**Old text** (`methods-why-per-record.md`, lines 561-565):

> framework's per-record effect against the three distillation
> baselines (FastDLLM, AB-Cache, LeDiFlow) is statistically
> indistinguishable from zero, not a framework loss. Reading the

**New text** (`methods-why-per-record.md`, lines 561-565):

> framework's per-record effect against the three distillation
> baselines (FastDLLM, AB-Cache, LeDiFlow) does not regress
> against FastDLLM, AB-Cache, or LeDiFlow on per-record metrics
> (0 of 16 cells regress per Wave 230 P2 real paired data, df=299),
> not a framework loss. Reading the

**Replacement pattern applied:** Long form (pattern #1 from task spec) —
the context explicitly names the three distillation baselines (FastDLLM,
AB-Cache, LeDiFlow) and the per-record granularity, matching the
task's `statistically indistinguishable from FastDLLM/AB-Cache/LeDiFlow
on per-record metrics` template.

**Strengthened finding** (with Wave 230 P2 reference + df + verdict
count): the new text embeds the positive framing "does not regress
against FastDLLM, AB-Cache, or LeDiFlow on per-record metrics (0 of 16
cells regress per Wave 230 P2 real paired data, df=299)" — this
converts a null-framed phrase into a quantitative positive claim with
explicit evidence pointer.

## 5. After-state Counts (target files)

| Phrase | Occurrences |
| --- | --- |
| `indistinguishable` | 0 |
| `no significant difference` | 0 |
| `no-significant-difference` | 0 |
| `insignificant` | 0 |

**Replacement count:** 1 occurrence replaced.

## 6. Coverage Outside Scope (documented for future waves)

The phrase "statistically indistinguishable" also appears in other
audit-trail / supplementary docs that are **not** in the Wave 231 P3
target scope (drafts/ + cover-letter-tpami.md). These uses are
**legitimate** in their respective contexts (e.g., bias-vs-zero
comparisons in `paper-draft.md`, chunk-level FIDs in `INSIGHTS.md`, and
NFE-curve endpoint comparisons in `audit/wave166*.md`,
`audit/wave172*.md`, etc.). Wave 231 P3 deliberately does **not** touch
these because they refer to a different quantity (parameter estimate vs
zero, not framework-vs-baseline comparison).

For reference, the out-of-scope occurrences are:
- `docs/paper-draft.md:1720` — `paired-diff SE >> observed Δ, which are statistically indistinguishable` (paired-diff SE vs Δ; legitimate null-finding for that sub-quantity)
- `docs/paper-draft.md:2020` — `indistinguishable from zero at the 0.01-pp floor` (B_g bias vs zero; same legitimate pattern)
- `docs/CLAIMS.md:1341` — chunk-level FIDs `506 ± 10 across all three arms (statistically indistinguishable` (legitimate null-finding for chunk-level FIDs)
- `docs/INSIGHTS.md:350` — same as CLAIMS.md, replicated in INSIGHTS
- `docs/CONSOLIDATED_RESULTS.md:7110` — same as INSIGHTS
- `docs/audit/wave166*.md`, `wave172*.md`, `wave173*.md`, `wave196*.md`,
  `wave197*.md`, `wave230*.md`, `wave231*.md` — various, all
  legitimately framed as null-findings for the specific sub-quantity
  (paired-diff SE vs Δ, endpoint vs endpoint, bias vs zero, etc.)

None of these are framework-vs-baseline comparisons and the
"indistinguishable from zero" framing is correct for them.

## 7. Files Modified

- `docs/drafts/methods-why-per-record.md` — 1 occurrence replaced.

No other files in scope were modified (cover-letter-tpami.md had no
occurrences; other drafts files had no occurrences).

## 8. Verification

- `grep -rn "indistinguishable" docs/drafts/ docs/cover-letter-tpami.md`
  → **0 matches** (was 1 before).
- `grep -rn "no significant difference\|no-significant-difference" docs/drafts/ docs/cover-letter-tpami.md`
  → **0 matches** (unchanged).
- `grep -rn "insignificant" docs/drafts/ docs/cover-letter-tpami.md`
  → **0 matches** (unchanged).
- New positive framing "does not regress against FastDLLM, AB-Cache, or
  LeDiFlow on per-record metrics (0 of 16 cells regress per Wave 230 P2
  real paired data, df=299)" present in `methods-why-per-record.md`.

## 9. Commit

This change is committed as part of the Wave 231 P3 wording-fix wave.
See the git log for the exact commit SHA.