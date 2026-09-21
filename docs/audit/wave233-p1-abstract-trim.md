# Wave 233 P1 — Abstract Trim Verification

**Date:** 2026-09-21
**Scope:** Verify abstract paragraph is within TPAMI 250-word envelope;
apply trim only if over-envelope; preserve all key claims.

## TL;DR

The abstract paragraph in `docs/drafts/abstract-final.md` is **already at exactly 250 words** — at the TPAMI 250-word envelope. **No trim was applied.**

The task description's claim of "~264 words (wc -w output: 890 lines
including markdown formatting)" appears to be derived from a stale state
or a counting method that does not match TPAMI's whitespace-separated
word convention. The verification below uses the standard whitespace
split on the abstract paragraph only (the canonical TPAMI counting
target).

## Word count verification

### Method A: task-specified command (whole file)

```bash
python -c "import re; t=open('docs/drafts/abstract-final.md').read(); t=re.sub(r'[#*\n\r\t]',' ', t); print(len(t.split()))"
```

Output: **757 words**

(This counts everything in the file: status block, provenance block,
sentence-by-sentence table, section headers. Not the TPAMI target count.)

### Method B: abstract paragraph only (TPAMI canonical target)

```python
import re
with open('docs/drafts/abstract-final.md') as f:
    content = f.read()
lines = content.split('\n')
abs_text = ""
in_abs = False
for line in lines:
    if "## Abstract (final, paper-ready)" in line:
        in_abs = True
        continue
    if in_abs:
        if line.strip().startswith('---'):
            break
        if line.strip():
            abs_text += line.strip() + " "
print(len(abs_text.strip().split()))
```

Output: **250 words**

This is the abstract paragraph (line 20 of the file), 9 sentences,
matching the existing per-sentence table on lines 29–39 of the file.

### Method C: alphanumeric tokens of abstract paragraph

Output: **311 tokens**

(Counts symbol-bearing identifiers `A_g`, `L_emp`, `e^{A_g}`,
`∈ [0.68, 35.63]`, `|d_z|<0.07`, `g(x)=(1+0.25·tanh(x))·sin(x)`,
etc., as multiple tokens. Not the TPAMI canonical count.)

## Per-sentence word count (matches file table lines 29–39)

| Sentence | Words | Function |
|---|---:|---|
| Sentence 1 | 14 | **Standard-ODEs framing** (DeepSeek F3) |
| Sentence 2 | 18 | **Problem framing** (Wave 207 S1) |
| Sentence 3 | 53 | **Framework introduction** (Wave 207 S2) |
| Sentence 4 | 21 | **Scheduler architecture** |
| Sentence 5 | 28 | **Empirical anchors** (Wave 229 P1–P3) |
| Sentence 6 | 17 | **A_g vs L_emp** (Wave 231 P4) |
| Sentence 7 | 49 | **Validation** (Wave 207 S3) |
| Sentence 8 | 23 | **Granularity signature** (Wave 229 P1) |
| Sentence 9 | 27 | **Positioning** (Wave 207 S4) |
| **Total** | **250** | at TPAMI envelope — Wave 232 P2 trim |

## Key claims verification (all preserved)

| Claim | Location (sentence) | Status |
|---|---|---|
| FlowA training-free solver-agnostic re-inference | S3 | preserved |
| BL bound via 4 paper quantities (A_g, B_g, C_g, e_ρ) | S3 | preserved |
| scPerplexity universal (cluster-robust) | S8 (cluster-robust implicit in 14/16 + Bonferroni) | preserved |
| hard-tier pLDDT mixed-effects | S8 (per-record 4-arm, df=299) | preserved |
| 4-arm per-record (df=299, 0 REGRESSES out of 16 cells, vanilla scPerplexity SUPPORTED) | S8 (14/16 granularity-bounded, 3 Bonferroni-significant, framework-WINS) | preserved |
| 12 adapters empirical Lipschitz L_emp range | S5 (L_emp^max ∈ [0.68, 35.63], 52× range) | preserved |
| A_g is F-side family constant distinct from L_emp per-adapter Jacobian | S6 | preserved |

All key claims are preserved in the existing 250-word version.

## Trim decision

**No trim was applied.** The abstract is already at exactly 250 words,
the TPAMI envelope target. The status block on lines 3–9 of the file
already self-documents this count, and the Wave 232 P2 commit
(`9689604 Wave 232 P2: abstract trim to TPAMI 250-word envelope`)
established this as the Wave 232 P2 deliverable. Wave 233 P1 has nothing
to trim.

If a margin below 250 is desired for safety, that would be a Wave 233
P2 decision; Wave 233 P1 is verification only.

## Removed phrases list

**Empty.** No phrases were removed because no trim was required.

## Files

- Input: `docs/drafts/abstract-final.md` (line 20: abstract paragraph, 250 words)
- Output: `docs/audit/wave233-p1-abstract-trim.md` (this file)
- No modifications to `docs/drafts/abstract-final.md` made.

## Commits

- This audit doc will be added in the Wave 233 P1 commit.
- No changes to `docs/drafts/abstract-final.md` (already at 250 words).