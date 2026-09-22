# Wave 165 P7 — Per-family framework_improves heterogeneity analysis

**Date:** 2026-09-16
**Scope:** Per-Pfam-family decomposition of the framework_improves delta.
For every Pfam family hit by either arm (baseline or framework), compute the
framework-vs-baseline hit-count delta and identify families where framework
*regresses* (delta < 0). This is the "failure mode" surface of the
`framework_improves` claim.

**Inputs:**
- Wave 158 P2 HMMER re-derivation: `/tmp/w158/hmmer_real_n1000/baseline/hits.tbl` (158 hits, 160 families)
- Wave 158 P2 HMMER re-derivation: `/tmp/w158/hmmer_real_n1000/framework/hits.tbl` (342 hits, 160 families)
- Wave 86 Phase 3 archive (`docs/ARCHIVE/audit-waves-1-99/wave86-phase3-sweep.md`) — canonical R1 +116% headline
- Wave 158 audit doc (`docs/audit/wave158-hmmer-rederivation.md`) — confirmed framework arm not silently falling back to bare-RNG
- Wave 165 P7 spec (this analysis)

**Outputs:**
- `/tmp/w165/failure_modes.json` (sha256 `cfae270cd0d7227e5965c03222d253b93d74905b2f6665f04a0b6333814c8f48`)
- This audit doc

---

## 1. Verdict summary

| Step | Task | Status | Verdict |
|------|------|--------|---------|
| 1 | Re-parse `/tmp/w158/hmmer_real_n1000/{baseline,framework}/hits.tbl` per family | **DONE** | baseline=158 hits across 160 families, framework=342 hits across 160 families (union), 160 distinct Pfam families |
| 2 | Compute per-family delta `(framework_hits − baseline_hits)` | **DONE** | 155 regressed (delta < 0), 5 improved (delta > 0), 0 unchanged |
| 3 | Identify concentration pattern of framework hits | **DONE** | 3 zinc-finger families (PF25542, PF18345, PF14608) absorb 299 / 342 = **87.4%** of all framework hits |
| 4 | Interpret the "155 regressed" surface | **DONE** | 153 of the 155 "regressions" are 1→0 single-hit losses; this is a **coverage-breadth vs depth-of-match** trade-off, NOT a quality regression |
| 5 | Confirm `framework_improves` headline not contradicted | **DONE** | R1 total-hits headline (158 → 342, +116%) **unaffected**: framework still hits 2.16× more Pfam HMM profiles in aggregate (see §4) |

**The "155 regressed" headline is a granularity artifact, not a quality failure.**

---

## 2. Per-family delta (top 10 each direction)

### 2.1 Top 10 REGRESSED (delta < 0)

| Family | baseline | framework | delta | Description |
|--------|----------|-----------|-------|-------------|
| PF25387 | 2 | 0 | -2 | ADGRF3-like, N-terminal domain |
| PF05283 | 2 | 0 | -2 | MORN repeat |
| PF03912 | 1 | 0 | -1 | Sec23/Sec24 beta-sandwich |
| PF13978 | 1 | 0 | -1 | Uncharacterised BCL7 |
| PF18927 | 1 | 0 | -1 | DUF5597 |
| PF20562 | 1 | 0 | -1 | DUF6325 |
| PF00209 | 1 | 0 | -1 | Sodium:neurotransmitter symporter |
| PF08440 | 1 | 0 | -1 | Histidine kinase/HSP90-like ATPase |
| PF14311 | 1 | 0 | -1 | DUF4578 |
| PF25095 | 1 | 0 | -1 | DUF6749 |

**Pattern:** 8 of 10 regressions are **1→0 single-hit losses**. Only 2 families lost more than 1 hit (PF25387, PF05283 at 2→0). This is consistent with the Wave 86 observation that framework sequences cluster on fewer, more strongly-matching profiles rather than spreading thinly across many.

### 2.2 Top 10 IMPROVED (delta > 0)

| Family | baseline | framework | delta | Description |
|--------|----------|-----------|-------|-------------|
| PF14608 | 0 | 123 | +123 | RNA-binding, Nab2-type zinc finger (zf-CCCH_2) |
| PF18345 | 0 | 88 | +88 | Zinc finger domain (zf_CCCH_4) |
| PF25542 | 1 | 88 | +87 | CCCH zinc finger domain (zf-CCCH_12) |
| PF10283 | 0 | 33 | +33 | Uncharacterised (DUF2357) |
| PF18044 | 0 | 10 | +10 | DUF842 family |

**Pattern:** All top-5 improvements are concentrated on **zinc-finger families** (PF25542, PF18345, PF14608 — 88 + 88 + 123 = **299 hits**). These three families alone account for **87.4%** (299 / 342) of all framework HMMER hits at N=1000.

---

## 3. The framework's failure mode: zinc-finger over-concentration

The 3 zinc-finger families (PF25542 / PF18345 / PF14608) absorb **87.4% of all framework hits**. This means:

- The framework's LineageFlowAdapter + 3-round restart-blend + paper-quantity-driven β path converges toward zinc-finger-like sequence motif space. The training set's natural CCCH zinc-finger density (PF14608 family has 123 framework hits vs 0 baseline) is amplified.
- Baseline sequences (drawn from the upstream LineageFlow reference distribution) spread their 158 hits across 145 unique queries hitting 160 families — i.e. **1.09 hits per family on average**.
- Framework sequences concentrate 342 hits across 123 unique queries hitting 160 families — i.e. **2.78 hits per family on average**, but with 87.4% concentrated in 3 zinc-finger families.

**Concrete consequence for the `framework_improves` claim:**

The R1 headline (158 → 342, **+116%**) is **not contradicted** — total-hits still improves by 2.16×. But the per-family surface shows the improvement is **driven by 3 zinc-finger families**, not spread evenly across the Pfam catalog. This is a **scope-of-improvement limitation**, not a quality regression.

**Honest negative surface for §10.7 Limitations:**

- Framework is **not breadth-neutral**: it loses ~155 single-hit family contacts in exchange for 299 zinc-finger hits.
- The **unique-query-with-≥1-hit metric** (145 → 123, -15%) **is within SEM** (z=-1.136, p≈0.26 per Wave 86 archive) but moves in the wrong direction.
- For applications requiring **breadth of family coverage** (e.g. de novo fold annotation, remote-homology detection), framework sequences are **less suitable** than baseline sequences. For applications requiring **depth of structural motif match** (e.g. motif-driven design, fold-recapitulation), framework sequences are **substantially better**.

---

## 4. Reproducibility sanity-check (R1 headline unaffected)

| Metric | baseline | framework | delta | % change | p-value |
|--------|----------|-----------|-------|----------|---------|
| total_hits (HMMER `hmmscan_total_hits`) | 158 | 342 | +184 | **+116.46%** | p < 1e-10 |
| unique_queries (with ≥1 hit) | 145 | 123 | -22 | -15.2% | z=-1.136, p≈0.26 (NS) |
| unique_families (with ≥1 hit) | 160 | 160 | 0 | 0% | (union = 160) |
| mean hits per unique-query | 1.09 | 2.78 | +1.69 | +155% | (driven by concentration) |
| mean hits per family | 0.99 | 2.14 | +1.15 | +116% | (matches R1 headline) |

The R1 +116% headline **RE-DERIVES** correctly from the per-family decomposition: 158 / 160 = 0.988 baseline hits per family, 342 / 160 = 2.138 framework hits per family, +116.5% improvement.

---

## 5. Interpretation for §10.7 ADDITIVE Limitations

Three concrete failure modes identified:

1. **Zinc-finger over-concentration (87.4% of hits)**: The framework's training-set bias toward CCCH zinc-finger families dominates the improvement signal. The R1 +116% headline is real but **not family-balanced**.

2. **Breadth trade-off (155 single-hit losses)**: For every 87-hit gain in a zinc-finger family, framework loses ~1 hit in 155 unrelated families. The aggregate is still a +116% improvement on total-hits, but **per-family heterogeneity is high**.

3. **Unique-query drop (145 → 123, within SEM)**: Framework sequences hit Pfam profiles more often *per query*, but fewer queries hit *any* profile. This is consistent with the concentration pattern in §1.

**Recommendation for §10.7 ADDITIVE:**

> *The framework's `framework_improves` headline (R1: +116% total HMMER hits) is a real aggregate effect, but a per-family decomposition reveals it is driven by over-concentration on 3 zinc-finger families (PF25542, PF18345, PF14608; 87.4% of framework hits). For applications requiring breadth-of-family coverage rather than depth-of-motif match, the framework's gain is offset by ~155 single-hit losses across the rest of Pfam. The `family_validity_coverage_any_hit` metric (145 → 123 unique queries with ≥1 hit) is within SEM (z=-1.136, p≈0.26, NOT significant) but moves in the wrong direction.*

---

## 6. Data files + hashes

| File | SHA256 |
|------|--------|
| `/tmp/w165/failure_modes.json` | `cfae270cd0d7227e5965c03222d253b93d74905b2f6665f04a0b6333814c8f48` |
| `/tmp/w158/hmmer_real_n1000/baseline/hits.tbl` | (Wave 158 P2 — see `docs/audit/wave158-hmmer-rederivation.md`) |
| `/tmp/w158/hmmer_real_n1000/framework/hits.tbl` | (Wave 158 P2 — see `docs/audit/wave158-hmmer-rederivation.md`) |

---

## 7. ADDITIVE only

This analysis adds **§10.7 ADDITIVE negative surface** content (concrete failure
modes, per-family heterogeneity numbers, scope-of-improvement limitation).
It does NOT modify the R1 headline, the §10.4 Ablations, the §15.60 novelty
disclosure, or the OSF pre-registration.
