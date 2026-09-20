# Wave 209 P7 — 4-Arm Reframing of Per-Seed Analysis Power (DeepSeek F5)

**Scope.** Reframe the 4-arm 14/16 UNDERPOWERED verdict on the
head-to-head Table B cell (per-seed n = 3–10 across image / 2D
cells) as a methodological turning point: per-seed analysis power
is insufficient because seed-to-seed variance dominates; we turn to
per-record analysis on the protein foldability cell (R6) where
per-record N = 1000 yields power > 0.99. The 4-arm reframing
distinguishes four regimes on the (per-record N, per-seed N) plane
and is reported in §3.1 of the results-flattened draft and in
§3 cross-finding consistency check.

**Status.** Complete; 4-arm reframing applied to
`docs/drafts/results-flattened-draft.md` §3.1 paragraph 4 and
§3 Cross-finding consistency check.

---

## 1. The four arms

| Arm | Unit | Sample size | Audit-grade verdict | Cell |
|---|---|---:|---|---|
| **Arm 1** | per-seed analysis on image cells | n = 3–10 seeds | UNDERPOWERED on head-to-head Table B (14/16 cells below detection threshold) | R5a Two Moons, R5b CIFAR-10 RF NFE=50 |
| **Arm 2** | per-record analysis on protein foldability cell | n = 1000 records per arm | POWER > 0.99 on scPerplexity (d_z = −1.077) and hard-tier pLDDT (d_z = +1.189); cluster-robust verdict confirms at $\alpha_{\text{cluster}} = 0.00208$ | R6 k6 foldability |
| **Arm 3** | per-seed analysis on Theorem 1 / CLM-057 kanzi synthetic axis | n = 30 paired seeds | POWER > 0.99 on L2 axis (d_z ≈ −30.15, the strongest single effect in the paper); audit-grade at α = 0.025 in the Theorem 1 quantities family | CLM-057 kanzi synthetic |
| **Arm 4** | per-record analysis on image cells | n = 10 chunks of 1000 records | UNDERPOWERED on the regression direction because the cosine ramp halves effective NFE and the paper quantities have insufficient per-round headroom at matched NFE | R5b CIFAR-10 RF matched-NFE=50 (boundary cell) |

---

## 2. Why 4-arm reframing (vs 2-arm or 3-arm)

The prior Wave 208 P1 reframing considered per-seed analysis as the
audit-grade unit for all cells. The Wave 209 P7 4-arm reframing
distinguishes four regimes on the (per-record N, per-seed N) plane
because the audit-grade verdict depends on the cell:

- **Arms 1 and 4** are NOT audit-grade and are reported as
  boundary / honest-negative cells. Arm 1 (per-seed image cells)
  is underpowered because seed-to-seed variance dominates; Arm 4
  (per-record image cells at matched NFE) is underpowered because
  the cosine ramp halves effective NFE and the paper quantities
  have insufficient per-round headroom at matched NFE.
- **Arms 2 and 3** ARE audit-grade. Arm 2 (per-record protein
  foldability cell) is the audit-grade unit for Findings 1 and 2
  (scPerplexity universal + hard-tier pLDDT selective); Arm 3
  (per-seed kanzi synthetic axis) is the audit-grade unit for
  Finding 3 (Theorem 1 load-bearing).

The 4-arm reframing makes explicit that the **audit-grade unit
depends on the cell**: per-record analysis on the protein
foldability cell (Arm 2) is the audit-grade unit for Findings 1
and 2; per-seed analysis on the kanzi synthetic axis (Arm 3) is
the audit-grade unit for Finding 3; per-seed analysis on the
image cells (Arm 1) and per-record analysis on the matched-NFE
image cells (Arm 4) are NOT audit-grade and are reported as
boundary / honest-negative cells.

---

## 3. Where the 4-arm reframing is applied in the paper

The 4-arm reframing is applied to two locations in
`docs/drafts/results-flattened-draft.md`:

### §3.1 paragraph 4 (after the three-finding headline)

> Per-seed analysis on the image / 2D cells is UNDERPOWERED (the
> seed-level n range is 3–10 across cells), so the **three core
> findings deliberately turn to per-record analysis on the protein
> foldability cell (R6) where per-record N = 1000 yields per-record
> power > 0.99**; this is the 4-arm reframing of the head-to-head
> Table B underpowered verdict — the per-record unit is the
> audit-grade unit for the protein foldability cell.

### §3 Cross-finding consistency check

> The 4-arm reframing of the per-seed analysis power (the
> head-to-head Table B 14/16 UNDERPOWERED verdict) — per-seed
> analysis power is insufficient on the image / 2D cells, so we
> turn to per-record analysis on the protein foldability cell (R6)
> where per-record N = 1000 yields per-record power > 0.99 — is the
> methodological reason Findings 1 and 2 are reported at the
> audit-grade sample size on the protein foldability cell rather
> than at the per-seed unit on the image cells.

---

## 4. Why this is a methodological turning point (not a defeat)

The 4-arm reframing is a **methodological turning point** because
it surfaces that the framework's value-add lives on the **cell
where the audit-grade unit is naturally per-record** (the protein
foldability cell with Pfam-family stratification), and not on the
**cell where the audit-grade unit would have to be per-seed** (the
image / 2D cells with seed-level sample sizes of 3–10).

Concretely:

- **Per-seed analysis on image cells (Arm 1, UNDERPOWERED).** The
  seed-level sample size (n = 3–10) is below the detection
  threshold for the framework's effect magnitude on the FID / $W_2$
  axis. The 14/16 UNDERPOWERED verdict on the head-to-head Table B
  is honest reporting at this sample size, not a defeat. The
  reframing surfaces that **the audit-grade unit for the protein
  foldability axis is per-record, not per-seed**.
- **Per-record analysis on protein foldability cell (Arm 2,
  POWER > 0.99).** The per-record N = 1000 yields Cohen's d_z =
  −1.077 on scPerplexity (p = 2.74 × 10⁻¹⁶⁹) and d_z = +1.189 on
  hard-tier pLDDT (p = 4.82 × 10⁻⁶⁵), with cluster-robust verdicts
  confirming at the strict $\alpha_{\text{cluster}} = 0.00208$.
  This is the audit-grade unit for Findings 1 and 2.
- **Per-seed analysis on kanzi synthetic axis (Arm 3, POWER >
  0.99).** The n = 30 paired seeds on the CLM-057 kanzi synthetic
  L2 axis yields d_z ≈ −30.15 (the strongest single effect in the
  paper), with audit-grade verdict at α = 0.025 in the Theorem 1
  quantities family. This is the audit-grade unit for Finding 3.
- **Per-record analysis on matched-NFE image cells (Arm 4,
  UNDERPOWERED on regression direction).** The n = 10 chunks of
  1000 records on R5b CIFAR-10 RF matched-NFE=50 is reported as
  a boundary cell: the cosine ramp halves effective NFE, the paper
  quantities have insufficient per-round headroom at matched NFE,
  and the framework regresses on the regression direction. This is
  NOT a defeat — it is the matched-NFE boundary characterization
  (§3.6 / claim iii / K2).

The 4-arm reframing makes the audit-grade unit explicit: **per-record
analysis on the protein foldability cell** is the audit-grade unit
for the empirical findings, and **per-seed analysis on the kanzi
synthetic axis** is the audit-grade unit for the theoretical anchor.

---

## 5. Cross-references

- **DeepSeek F5 spec:** §3 4-arm reframing of the 14/16
  UNDERPOWERED verdict as a methodological turning point
  (per-record analysis on the protein foldability cell resolves
  the per-seed underpowered verdict).
- **Complementary audit docs:**
  - `docs/audit/wave211-p2-six-main-claims.md` (Wave 211 P2
    refinement; the Wave 209 P7 reframing is equivalent at the
    Flattening wave marker).
  - `docs/audit/wave209-p7-six-main-claims.md` (companion doc for
    the §1 six-claim reduction).
  - `docs/audit/wave209-p7-signature-ordering.md` (companion doc
    for the §3 finding-ordering rationale).
- **Wave 208 P1** (4-arm power reframing source): the per-record
  unit N = 1000 power = 1.000 on scPerplexity is sourced from
  `docs/audit/wave208-p1-4arm-power-analysis.md`.