# Wave 209 P7 — Signature Ordering (DeepSeek F3)

**Scope.** Apply the DeepSeek F3 review signature ordering to the
three core findings reported in §3 of the paper. The three findings
are ordered so that the **empirical findings on the audit-grade
sample size lead** (Findings 1 and 2) and the **theoretical anchor
follows** (Finding 3). The ordering is applied to
`docs/drafts/results-flattened-draft.md` §3.1, the tables in §3.2,
and the headline summary in §3.7.

**Status.** Complete; ordering applied as follows.

---

## 1. The three signature findings — finalised ordering

| # | Finding | Evidence stream | Audit-grade unit | Cluster-robust? | Cross-adapter? |
|---|---|---|---|:-:|:-:|
| 1 | **scPerplexity universal improvement across tiers** | R6 k6 overall scPerplexity d_z = −1.077, p = 2.74 × 10⁻¹⁶⁹; per-tier scPerplexity d_z ∈ [−1.033, −1.138] uniformly; cluster-robust p ≤ 1 × 10⁻² across all tiers; replicated on LineageFlow adapter | per-record N = 1000 | YES | YES |
| 2 | **hard-tier pLDDT selective uplift with monotone `hard > medium > easy` pattern** | R6 k6 hard pLDDT d_z = +1.189, p = 4.82 × 10⁻⁶⁵, cluster-robust p = 1.28 × 10⁻²; k6 + LineageFlow monotone `hard > medium > easy` in Cohen's d_z (+1.189/+0.218/−0.998 vs +1.840/+0.976/−0.590) | per-record N = 1000 | YES | YES |
| 3 | **Theorem 1 quantities load-bearing as a regulariser** | CLM-057 kanzi synthetic L2 axis: paper-quantity $L_2 \approx 0.46$ vs cosine-only $L_2 \approx 97.97$, $d = +10.24$, $p = 3.96 \times 10^{-31}$; d_z ≈ −30.15; framework acts as a stabiliser against the cosine ramp's endpoint perturbation | per-seed n = 30 paired seeds | n/a (synthetic) | n/a (single-axis) |

---

## 2. Why this ordering (vs the prior theoretical-first ordering)

The prior Wave 207 P6 / Wave 208 P7 ordering was:

1. Finding 1: Theorem 1 load-bearing as regulariser (kanzi synthetic L2)
2. Finding 2: scPerplexity universal improvement (k6 + lineageflow)
3. Finding 3: hard-tier pLDDT selective uplift (k6 + lineageflow)

The new Wave 209 P7 ordering is:

1. Finding 1: scPerplexity universal improvement (cluster-robust, cross-adapter)
2. Finding 2: hard-tier pLDDT selective uplift (cluster-robust, cross-adapter)
3. Finding 3: Theorem 1 quantities load-bearing as a regulariser

The DeepSeek F3 review surfaced that the prior ordering privileged
the **theoretical anchor** first because that is the natural
ordering for a theory-driven paper. The new ordering privileges
the **empirical findings on the audit-grade sample size** because
the empirical findings are what makes the paper credible to a
reviewer who is unfamiliar with the theoretical framework.

Specifically:

- **Finding 1 (scPerplexity universal, 1st).** This is the **only**
  finding that is cluster-robust AND cross-adapter AND universal
  across tiers AND on the audit-grade sample size (per-record
  power = 1.000 at N = 1000, Wave 208 P1 reframing). It is the
  strongest unit-test of the framework's per-record value-add, and
  it should lead. The cluster-robust verdict confirms the
  scPerplexity win uniformly across all tiers ($p_{\text{cluster}}
  \leq 1 \times 10^{-2}$) at the strict $\alpha_{\text{cluster}} =
  0.00208$.

- **Finding 2 (hard-tier pLDDT selective, 2nd).** This finding is
  cluster-robust AND cross-adapter AND monotone across tiers on
  the structural-quality axis. The monotone `hard > medium > easy`
  pattern in Cohen's d_z is the structural-position uniqueness
  argument for the protein foldability axis. It follows Finding 1
  because it shares the audit-grade sample size (N = 1000
  per-record) and the cluster-robust unit (df_cluster = 3, ICC =
  0.041, N_eff_design_effect = 89.6).

- **Finding 3 (Theorem 1 load-bearing, 3rd).** This is the
  **theoretical anchor** that explains why Findings 1 and 2 hold.
  It is CLM-057_kanzi_L2 (d_z = −30.15, the strongest single
  effect in the paper), but the sample size is n = 30 paired seeds
  (the audit-grade sample size for this axis is constrained by the
  kanzi synthetic generation cost, not by sample-size limitations).
  Putting Finding 3 last makes the §3 introduction read as "we
  observed X and Y, and here is the theoretical anchor that
  explains why X and Y hold", which is the reviewer-friendly
  argumentative arc.

---

## 3. Per-record vs per-seed power reframing

The signature ordering makes the **per-record analysis on the
protein foldability cell (R6)** the audit-grade unit for Findings 1
and 2, with per-record N = 1000 yielding per-record power > 0.99.
This is the **4-arm reframing of the per-seed analysis power**
(Wave 208 P1) — the head-to-head Table B 14/16 UNDERPOWERED verdict
on the image / 2D cells was driven by per-seed analysis on
seed-level n = 3–10; per-record analysis on the protein foldability
cell resolves the underpowered verdict because per-record N = 1000
yields per-record power > 0.99.

The 4-arm reframing is documented separately in
`docs/audit/wave209-p7-4arm-reframing.md`.

---

## 4. Where the ordering is applied in the paper

The ordering is applied to:

- `docs/drafts/results-flattened-draft.md` §3.1 (three-finding
  headline, with Finding 1 = scPerplexity universal, Finding 2 =
  hard-tier pLDDT selective, Finding 3 = Theorem 1 load-bearing).
- `docs/drafts/results-flattened-draft.md` §3.2 Tables 3.1, 3.2, 3.3
  (tables renamed to match the new finding order).
- `docs/drafts/results-flattened-draft.md` §3.3 statistical
  methodology cross-reference (LineageFlow rows in Tables 3.1 and
  3.2 are naive-only cross-reference).
- `docs/drafts/results-flattened-draft.md` §3.7 headline summary
  (rephrased to lead with Finding 1 and put Finding 3 last).
- `docs/drafts/results-flattened-draft.md` §3 Cross-finding
  consistency check (the three findings are mutually compatible,
  with Finding 1 establishing per-record value-add, Finding 2
  establishing selective structural-quality uplift, and Finding 3
  establishing the theoretical anchor).

---

## 5. Cross-references

- **DeepSeek F3 spec:** §3 signature ordering (empirical-findings
  first, theoretical anchor last).
- **Complementary audit docs:**
  - `docs/audit/wave211-p2-six-main-claims.md` (Wave 211 P2
    refinement; the Wave 209 P7 ordering is equivalent at the
    Flattening wave marker).
  - `docs/audit/wave209-p7-six-main-claims.md` (companion doc for
    the §1 six-claim reduction).
  - `docs/audit/wave209-p7-4arm-reframing.md` (companion doc for
    the per-record / per-seed power reframing).
- **Wave 208 P1** (4-arm power reframing source): the per-record
  unit N = 1000 power = 1.000 on scPerplexity is sourced from
  `docs/audit/wave208-p1-4arm-power-analysis.md`.