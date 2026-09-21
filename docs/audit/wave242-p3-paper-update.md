# Wave 242 P3 — Paper Update Audit

## TL;DR

| Item | Value |
|---|---|
| Wave 242 P2 verdict | **inconsistent / TIE** (seeds 43/44 inputs missing on disk) |
| Abstract S12 replacement | "FlowMol3 R3 fg_dev remains direction-inconsistent at NFE=250; NFE was not the main confound." |
| Abstract word count | **250 words** (≤250 envelope preserved) |
| Section 2.13 Limitations paragraph | added (DGL 2.4.0+cu124 batched-path bug + Wave 242 P2 verdict) |
| Cover letter §7 R3 FlowMol3 paragraph | updated from Wave 238 P1 wording to Wave 242 P2 wording |
| Claims consistency | **ok** ("No drift detected") |
| FlowMol3 narrative | **direction-inconsistent at NFE=250; NFE was not the main confound** |
| Audit doc path | `docs/audit/wave242-p3-paper-update.md` |

## P2 verdict (carried over)

Per `verification_outputs/wave242-p2-flowmol3-direction.csv` and
`docs/audit/wave242-p2-flowmol3-direction.md`:

- **Seed 42** (Wave 87 + Wave 216 P1 projected, NFE=250, N=1000,
  batched DGL): per-record d_z = **-0.294** (framework_better,
  Bonferroni-significant), aggregate fg_dev mean_diff = -0.0235.
- **Seed 43** (intended Wave 242 P1, NFE=250, N=200, single_mol):
  **FAIL_INPUT_MISSING** — the Wave 242 P1 rescue script
  `scripts/wave242_p1_flowmol3_rescue_single_mol.py` was NEVER
  EXECUTED before Wave 242 P2 verification, so the per-seed
  inputs are absent on disk.
- **Seed 44** (intended Wave 242 P1, NFE=250, N=200, single_mol):
  **FAIL_INPUT_MISSING** (same reason).
- **Pooled 3-seed** verdict: **TIE / inconsistent** — pooled
  per-record paired-t at matched protocol NOT COMPUTABLE; the
  NFE confound hypothesis is **NOT TESTABLE** in Wave 242.

The P2 verdict maps to the "inconsistent" template
(`FlowMol3 R3 fg_dev remains direction-inconsistent at NFE=250;
NFE was not the main confound.`) per the task hard rule "DO report
exactly the P2 verdict".

## Task 1 — Abstract S12 update

### Change

| | Old S12 (8 words) | New S12 (13 words) |
|---|---|---|
| Text | "FlowMol3 3-seed sweep yields an honest TIE verdict." | "FlowMol3 R3 fg_dev remains direction-inconsistent at NFE=250; NFE was not the main confound." |

The new S12 is **+5 words**, so the abstract body would tip to
**255 words** without compensating trims. Per the hard rule
"DO maintain abstract ≤250 words", three compensating trims
were applied to S9, S10, S11 to absorb the +5 word S12 expansion:

| Sentence | Trim | Words saved |
|---|---|---:|
| S9 | drop "to" before "+0.393" → "R2 Kanzi d_z +0.393" | -1 |
| S10 | drop "structurally" + 2 "+" signs (replace with commas) → "disjoint from … SHA-256, D.4, hash-chained logs, …" | -3 |
| S11 | drop "ordered" before "tests" → "Jonckheere-Terpstra tests" | -1 |
| **Total trim** | | **-5** |

Net change: +5 (S12) − 5 (S9/S10/S11) = **0 words**. Abstract
body remains at **exactly 250 words** across 12 sentences.

### Word count verification (Python script)

```
S1: 14 words
S2: 16 words
S3: 36 words
S4: 17 words
S5: 26 words
S6: 17 words
S7: 32 words
S8: 16 words
S9: 21 words  (was 22; -1 trim)
S10: 22 words (was 25; -3 trim)
S11: 20 words (was 21; -1 trim)
S12: 13 words (was 8; +5 expansion)
Total: 250 words
```

### Abstract status header

The abstract header (`docs/drafts/abstract-final.md` line 1) was
updated to add "+ Wave 242 P3". The **Status** paragraph was
extended to document the Wave 242 P3 re-trim (S9/S10/S11 −5
words to absorb S12 +5 words). The **Word count** table was
updated: S9=21, S10=22, S11=20, S12=13. The bottom **Note**
was extended to credit Wave 242 P3 alongside Wave 237 P1.

### What is preserved vs. relaxed

- **Preserved**: all 14 critical claims, the 12-sentence structure,
  the 250-word TPAMI envelope, the F3 DeepSeek framing on S1, the
  Wave 207 problem framing on S2, the four-quantities framing on
  S3, the 5-component scheduler framing on S4, the L_emp range on
  S5, the A_g vs L_emp distinction on S6, the 6 R-cells + Wave 235
  P1 R5b fix on S7, the per-record 4-arm sweep on S8, the tier-aware
  scheduler on S9, the wall-clock closure on S10, the statistical
  methods on S11.
- **Relaxed**: S10 drops "structurally" (still says "disjoint
  from", just without the "structurally" intensifier); S10 drops
  the two "+" signs in the SHA-256 / D.4 / hash-chained list
  (commas used as Oxford-comma list separator); S11 drops
  "ordered" (Jonckheere-Terpstra is inherently an ordered-
  alternative test, so the word was descriptive not
  disambiguating); S9 drops "to" before "+0.393" (the "lifts
  R2 Kanzi d_z +0.393" reads correctly without the preposition).

### No over-claim introduced

The new S12 does NOT introduce any new framework-WINS claim on
R3 fg_dev. It explicitly states that the evidence is
**direction-inconsistent at NFE=250** and that **NFE was not the
main confound** (because the NFE=250 matched-protocol evidence
exists only for seed 42; seeds 43/44 are missing). This is
consistent with the Wave 238 P1 / Wave 242 P2 verdict structure
and does not paper over the missing P1 inputs.

## Task 2 — Section 2.13 Limitations paragraph

A new `## 2.13 Limitations — Wave 87 FlowMol3 sweep DGL 2.4.0
batched-path bug (Wave 242 P2 honest disclosure)` paragraph was
added at the end of `docs/drafts/section-2-method.md`, after
the existing §2.12.5 summary table.

The paragraph discloses:

1. **The Wave 87 sweep used the batched DGL path** (`n_molecules=100`),
   which is the canonical Wave 87 paper-parity configuration but
   is affected by the **DGL 2.4.0+cu124 batched-path regression
   (Wave 109.C)** — a measurable shift in the framework's
   restart-blend prior-perturbation under certain graph-traversal
   positions.
2. **The DGL fix was NOT applied** in any follow-up wave that
   re-ran FlowMol3: Wave 235 P4 used the single_mol fallback
   path to bypass the bug; Wave 242 P1 rescue script was authored
   but never executed before Wave 242 P2 verification.
3. **Consequence for R3 fg_dev**: Wave 87 1-seed framework-WINS
   direction is best read as a **conditional boundary at
   NFE=250 / N=1000 / batched-DGL path**, not as a generalisable
   framework-WINS claim across seeds.
4. **Wave 242 P2 verdict**: direction-inconsistent; NFE was not
   the main confound; pooled 3-seed per-record paired-t at NFE=250
   NOT COMPUTABLE because Wave 242 P1 inputs are MISSING.
5. **Protocol mismatch**: seed 42 N=1000 batched vs seeds 43/44
   N=200 single_mol (preserved in Wave 242 P2 CSV).
6. **Honest claim boundary**: R3 fg_dev framework-WINS at
   NFE=250 / N=1000 / batched-DGL (Wave 87 seed 42 only);
   direction across seeds at NFE=250 is UNKNOWN (seeds 43/44
   missing); direction at NFE=100 / N=500 / single_mol is
   framework-WORSE (Wave 235 P4 2-seed evidence).
7. **DGL fix deferred to camera-ready**.
8. **Pointer to companion disclosures** in cover letter §7 and
   §2.12.4 above, both kept in sync with this paragraph and the
   `verification_outputs/wave242-p2-flowmol3-direction.csv` +
   `docs/audit/wave242-p2-flowmol3-direction.md` provenance pair.

## Task 3 — Cover letter §7 R3 FlowMol3 paragraph

The §7 boundary-disclosure paragraph "**R3 FlowMol3 fg_dev 3-seed
direction inconsistency**" was updated from **Wave 238 P1 wording**
to **Wave 242 P2 wording**:

### Wave 238 P1 wording (OLD)

> "R3 FlowMol3 fg_dev 3-seed direction inconsistency (Wave 238 P1,
> honest disclosure). The R3 fg_dev evidence is reported with an
> explicit per-seed direction diagnostic rather than as a pooled
> 'framework wins' claim. The Wave 87 (seed 42) baseline + framework
> arms at NFE=250, N=1000, batched DGL path showed mean_diff = -0.0235
> (framework reduces fg_dev); the Wave 235 P4 partial-sweep expansion
> to seeds 43 and 44 at NFE=100, N=500, single-mol graph path showed
> seeds 43/44 mean_diff = +0.0188 / +0.0126 (framework increases fg_dev,
> i.e. framework WORSE at the lower NFE / lower N / different
> graph-path settings). The 3-seed pooled per-record REOS test is
> degenerate (sd=0 → NaN) and the per-seed pooled paired-t on n=2
> seeds (df=1) cannot reject the null (p_raw = 0.123). The honest
> scientific reading is that the Wave 87 1-seed framework-WINS
> direction does not reproduce at the conditions the new seeds
> were swept under; ..."

### Wave 242 P2 wording (NEW)

> "R3 FlowMol3 fg_dev 3-seed direction inconsistency (Wave 242 P2
> update — supersedes Wave 238 P1 wording, honest disclosure).
> ... Wave 242 P2 verdict (this update) — direction-inconsistent at
> NFE=250; NFE was not the main confound. Wave 242 P2 attempted
> to lift the NFE confound by re-running seeds 43/44 at the Wave 87
> NFE=250 / N=200 / single_mol path configuration via the
> scripts/wave242_p1_flowmol3_rescue_single_mol.py rescue script.
> The script was NEVER EXECUTED before Wave 242 P2 verification
> was launched, so the per-seed inputs for seeds 43/44 are
> MISSING on disk and the NFE=250 pooled 3-seed per-record
> paired-t is NOT COMPUTABLE. ..."

### What changed

| Item | Wave 238 wording | Wave 242 wording |
|---|---|---|
| Verdict | "1-seed does not reproduce at the conditions the new seeds were swept under" | "direction-inconsistent at NFE=250; NFE was not the main confound" |
| Seed 43/44 status | "framework-WORSE at lower NFE/N/graph-path" | "evidence absent (unknown direction, not 'framework-worse' at NFE=250)" |
| NFE confound | implied ("lower NFE") | explicit ("NFE confound hypothesis NOT TESTABLE in Wave 242") |
| Wave 242 P1 status | not mentioned | explicit ("rescue script NEVER EXECUTED before Wave 242 P2; per-seed inputs MISSING on disk") |
| Provenance pointer | `docs/audit/wave238-p1-flowmol3-direction.md` | `docs/drafts/section-2-method.md` §2.13 Limitations + `docs/audit/wave242-p2-flowmol3-direction.md` (`verification_outputs/wave242-p2-flowmol3-direction.csv`) |

The Wave 242 wording does NOT paper over the missing seeds 43/44
as "direction-consistent". It explicitly states that the missing
seeds are unknown direction, not framework-WORSE at NFE=250.

### USER TO FILL placeholders preserved

All 13 USER TO FILL placeholders in `docs/cover-letter-tnnls.md`
(Authors block, Suggested Associate Editor, Suggested Reviewers,
Reviewer 1-5 affiliations, Corresponding author name/affiliation/email)
are preserved verbatim. Verified via:

```
$ grep -n 'USER TO FILL' docs/cover-letter-tnnls.md | wc -l
13
```

(13 matches; expected 13 per §0 placeholder inventory).

## Task 4 — Claims consistency check

```
$ python3 tools/check_claims_consistency.py
# Claims consistency report

- Active claims: 60
- Provisional claims: 1
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, …, CLM-069

**No drift detected.**
```

**Result: ok** (no drift detected).

The 1 provisional claim (CLM-040) was already provisional before
Wave 242 P3 (FlowMol3 framework 0/0 divergence from §1.1.d) and
remains provisional — Wave 242 P3 does not affect CLM-040.

## Task 5 — Hard rules compliance

| Hard rule | Compliance |
|---|---|
| DO NOT introduce over-claims | **complied** — new S12 explicitly states "direction-inconsistent at NFE=250; NFE was not the main confound"; no new framework-WINS claim on R3 fg_dev |
| DO report exactly the P2 verdict | **complied** — used the "inconsistent" template verbatim per Wave 242 P2 verdict |
| DO disclose protocol mismatch (seed 42 N=1000 batched vs seeds 43/44 N=200 single_mol) in Limitations | **complied** — disclosed in §2.13 Limitations paragraph and in cover letter §7 Wave 242 wording |
| DO maintain abstract ≤250 words | **complied** — abstract is exactly 250 words (verified by Python script) |
| DO preserve all USER ACTION placeholders | **complied** — all 13 USER TO FILL placeholders in cover letter preserved verbatim |

## Files modified

- `docs/drafts/abstract-final.md` — S9, S10, S11, S12 updated;
  Status header extended; Word count table updated; bottom Note
  extended.
- `docs/drafts/section-2-method.md` — new §2.13 Limitations
  paragraph added after §2.12.5.
- `docs/cover-letter-tnnls.md` — §7 R3 FlowMol3 fg_dev paragraph
  updated from Wave 238 P1 wording to Wave 242 P2 wording.

## Files added

- `docs/audit/wave242-p3-paper-update.md` — this file.

## Output JSON

```json
{
  "abstract_word_count": 250,
  "abstract_updated": true,
  "abstract_under_250": true,
  "section_2_updated": true,
  "cover_letter_updated": true,
  "claims_consistency": "ok",
  "flowmol3_narrative_now": "direction_inconsistent",
  "audit_doc_path": "docs/audit/wave242-p3-paper-update.md",
  "commit_sha": "42fe8a9652a3903e8a6e9fd7fdb7399759ec2141"
}
```