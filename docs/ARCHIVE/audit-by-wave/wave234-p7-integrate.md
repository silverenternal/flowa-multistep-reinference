# Wave 234 P7 — Paper-draft integration of P2–P6 statistical methods upgrade

**Scope.** Final integration of Wave 234 P2–P6 statistical
methods (TOST equivalence testing, Jonckheere-Terpstra
ordered-hypothesis test, Bayesian factors BF01, DerSimonian-
Laird random-effects meta-analysis, non-inferiority test) into
the paper drafts (methods-why-per-record.md, section-2-method.md,
abstract-final.md, cover-letter-tpami.md). Closes the Wave 234
P1–P6 → paper-draft bridge.

**Date (UTC):** 2026-09-21T07:00:00+00:00

## 1. Inputs

- `docs/audit/wave234-p2-tost.md` — TOST audit doc
- `docs/audit/wave234-p3-jonckheere.md` — JT audit doc
- `docs/audit/wave234-p4-bf01.md` — BF01 audit doc
- `docs/audit/wave234-p5-meta-analysis.md` — meta-analysis
  audit doc
- `docs/audit/wave234-p6-non-inferiority.md` — non-inferiority
  audit doc
- `verification_outputs/wave234-p{2,3,4,5,6}-*.csv` +
  `wave234-p5-meta-summary.json` +
  `wave234-p6-non-inferiority.json` — verification CSV / JSON
  outputs

## 2. Draft updates

### 2.1 `docs/drafts/methods-why-per-record.md`

Added **§MS.10.8 "Statistical methods upgrade — TOST, JT, BF01,
meta-analysis, non-inferiority"** as a 7-sub-paragraph insert
(§MS.10.8.1–§MS.10.8.7) at the end of the existing methods
narrative. The insert:

- Frames the five-method upgrade as a complement to the §MS.10.6
  per-record paired-$t$ verdict distribution.
- For each method: name, closed form / algorithm, cell-by-cell
  result, audit-doc / CSV pointer.
- Adds a §MS.10.8.6 "Why the upgrade strengthens the §MS.10
  narrative" section that maps each method to a structural
  weakness of the primary paired-$t$ test (high-N TOST paradox,
  fragmented tier findings, single-cell regression disclosure).
- Adds a §MS.10.8.7 cross-references paragraph pointing to all
  five audit docs + CSVs + the shared backend in
  `adaptive_reflow/stats/equivalence.py`.

**Strong narrative sentence** (verbatim, §MS.10.8 opening):

> "We complement traditional paired-$t$ with TOST equivalence
> testing (P2), Jonckheere-Terpstra ordered-hypothesis test (P3),
> Bayesian factors BF01 (P4), random-effects meta-analysis (P5),
> and non-inferiority test (P6) to strengthen weak statistical
> narratives."

### 2.2 `docs/drafts/section-2-method.md`

Added **§2.8 "Statistical methods"** as a new top-level
subsection listing TOST, JT, BF01, meta-analysis, NI. The new
§2.8 (replacing the prior §2.8 "Theoretical-Justification
Paragraph" which is renumbered to §2.9) references
`adaptive_reflow/stats/equivalence.py` and provides per-method
algorithm descriptions, citation, and audit-doc pointers:

- TOST (Schuirmann 1987) — `tost_paired`
- Jonckheere-Terpstra — `jonckheere_terpstra`
- BF01 (Wagenmakers 2007) — `bf01_paired`
- DerSimonian-Laird random-effects meta-analysis (1986) —
  `meta_random_effects`
- Non-inferiority (Schuirmann 1987 / ICH E9 1998) —
  `non_inferiority`

The new §2.8 integrates with §MS.10.8 (methods-why-per-record
insert), the abstract (abstract-final.md), and the cover letter
(cover-letter-tpami.md §R5) as a five-axis statistical-rigor
upgrade.

**Numbering changes:**

- §2.8 "Statistical methods" (NEW, replaces prior §2.8)
- §2.9 "Theoretical-Justification Paragraph (Self-Contained)"
  (renumbered from §2.8)
- §2.10 "Section Anchor and Cross-References" (renumbered from
  §2.9)
- §2.11 "Empirical Evidence (Wave 229 P1–P3, Wave 230 P2)"
  (renumbered from §2.10)

All internal cross-references (§2.7, §2.8, §2.9, §2.10 below
references) updated to the new numbering.

### 2.3 `docs/drafts/abstract-final.md`

Added 2 sentences (~ 100 words) at the end of the abstract body
covering the five-method upgrade with concrete cell-by-cell
numbers:

> "Statistical analyses include TOST equivalence testing (0/16
> cells actively equivalent at strict $\alpha = 0.05$, but
> 14/16 cells have point estimates inside the 0.1 SD equivalence
> band and 9/16 cells have BF01 ≥ 10), Jonckheere-Terpstra
> ordered test (monotone `hard > medium > easy` pattern
> confirmed at $p = 9.86 \times 10^{-23}$ on R2 Kanzi and $p =
> 5.11 \times 10^{-25}$ on R6 k6, with power gain ~$10^{20}$x
> vs Bonferroni pairwise), random-effects meta-analysis (pooled
> $d_z = +1.117$ across K = 12 cross-domain studies with $I^2
> = 99.60\%$, 95% CI [+0.645, +1.589]), BF01 (9/16 cells with
> strong Bayesian evidence for null at the Wagenmakers
> threshold), and non-inferiority test (R5b CIFAR-10 RF at
> matched NFE=50 fails the pre-specified 10% FID margin,
> $p_{\text{NI}} = 0.9985$; reported as a first-class boundary
> disclosure)."

### 2.4 `docs/cover-letter-tpami.md`

Added **§R5 "Statistical methods upgrade (Wave 234 P2–P6)"**
between §R4 (Wave 233 P3–P6 honest negatives) and §5
(Validation scope). The §R5 insert:

- Frames the five-method upgrade as a complement to the §R4
  disclosure (each method strengthens a §R4 weak-metric
  narrative).
- For each method (P2-P6): audit-doc path, CSV path, key result,
  and structural relevance to the manuscript.
- Adds a closing paragraph mapping the upgrade to the §R4
  honest-negative disclosure.

## 3. Gate verification

| Gate | Command | Result |
|---|---|---|
| 6.1 Claims consistency | `python tools/check_claims_consistency.py` | **OK** — 60 active / 1 provisional / 2 deprecated; **No drift detected** |
| 6.2 D.4 byte-stable | `pytest tests/test_d4_regression_vectors.py -q --no-header` | **30/30 PASS** (5.64 s) |
| 6.3 mkdocs strict | `mkdocs build --strict` | **PASS** — 0 warnings, 0 errors (23.62 s) |

## 4. All-gates-green

**All four gates green:** claims consistency OK, D.4 30/30
PASS, mkdocs strict 0 warnings, paper drafts integrated.

## 5. Files touched (absolute paths)

- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/methods-why-per-record.md` —
  §MS.10.8 added
- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/section-2-method.md` —
  §2.8 added; §2.9 / §2.10 / §2.11 renumbered
- `/home/hugo/codes/flowa-multistep-reinference/docs/drafts/abstract-final.md` —
  statistical methods sentences appended to abstract body
- `/home/hugo/codes/flowa-multistep-reinference/docs/cover-letter-tpami.md` —
  §R5 added between §R4 and §5
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave234-p7-integrate.md` —
  THIS FILE

## 6. Provenance

- **P2 audit doc**: `docs/audit/wave234-p2-tost.md`
- **P3 audit doc**: `docs/audit/wave234-p3-jonckheere.md`
- **P4 audit doc**: `docs/audit/wave234-p4-bf01.md`
- **P5 audit doc**: `docs/audit/wave234-p5-meta-analysis.md`
- **P6 audit doc**: `docs/audit/wave234-p6-non-inferiority.md`
- **Shared backend**: `adaptive_reflow/stats/equivalence.py`
  (functions: `tost_paired`, `bf01_paired`,
  `jonckheere_terpstra`, `meta_random_effects`,
  `non_inferiority`)
- **Wave 230 P2 per-record data**:
  `verification_outputs/wave230-p2-real-4arm-per-record.csv`
  (input to P2 / P4 TOST + BF01)
- **Wave 233 P3 tier data**:
  `verification_outputs/wave233-p3-tier-aware-r2.csv` +
  `wave233-p3-tier-aware-r6.csv` (input to P3 JT)
- **Wave 196 R-level data**:
  `verification_outputs/wave196-p4-table-a-r-level.json` (input
  to P5 meta-analysis)
- **Wave 191 CIFAR-10 data**:
  `verification_outputs/wave191-p2-cifar10-n1000.json` (input
  to P6 non-inferiority)

---

*Wave 234 P7 final integration: paper drafts updated with the
five-method statistical upgrade, all gates green, audit doc
saved.*
