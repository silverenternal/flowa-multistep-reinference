# Wave 213 P8 — Signature ordering final confirmation

**Status.** Final confirmation that the DeepSeek F3 signature ordering
(`scPerplexity universal → hard-tier pLDDT selective → Theorem 1
load-bearing`) is consistently applied in the Abstract, Intro, and
Results drafts. No ordering violations found; no corrections applied.

**Scope.** This audit verifies the ordering of the three signature
findings established by Wave 209 P7 and preserved through Wave 211 P2:
the three empirical findings of the paper are the framework's universal
prior-fit improvement (scPerplexity, cluster-robust, cross-adapter), the
framework's selective hard-tier structural-quality improvement (pLDDT
with monotone `hard > medium > easy` Cohen's d_z pattern, cluster-robust,
cross-adapter), and the load-bearing role of the four Theorem 1 paper
quantities as a regulariser on the protein-axis scheduler (CLM-057 kanzi
synthetic, Cohen's d_z = −30.15 on the L2 axis). The DeepSeek F3 review
specified that these three findings are reported in the order scPerplexity
→ pLDDT → Theorem 1 in any location that enumerates them.

---

## Abstract — `docs/drafts/abstract-final.md`

The Abstract frames the paper across five sentences and does NOT enumerate
the three signature findings by name. The Abstract's content structure is:

| Sentence | Words | Function | Signature findings mentioned? |
|---|---:|---|---|
| Sentence 1 | 19 | Standard-ODEs framing (DeepSeek F3) | none |
| Sentence 2 | 31 | Problem framing (frozen-checkpoint gap) | none |
| Sentence 3 | 86 | Framework introduction (FlowA, four quantities, three scheduler/operator components) | Theorem 1 method only (not the Finding 3 empirical verification) |
| Sentence 4 | 64 | Validation (six R-cells, N = 1000, 2.5–10× NFE compression, byte-stable composite-axis lifts, K1–K8 boundary) | none enumerated; the byte-stable composite-axis lifts phrase is a single umbrella term that does not separate scPerplexity from pLDDT |
| Sentence 5 | 41 | Positioning (structural disjointness, SHA-256 + hash-chained + D.4) | none |

**Signature ordering verdict: CORRECT (not applicable).** The Abstract
does not enumerate the three signature findings in any order, so there is
no ordering to violate. The Abstract's only mentions of the Theorem 1
quantities appear in Sentence 3 as the framework's method (the four paper
quantities $(A_g, B_g, C_g, e_\rho)$ consumed as scheduler inputs), which
is the framework description rather than a finding. Sentence 4 uses the
umbrella phrase "byte-stable composite-axis lifts on all three Tier 3
real checkpoints" without separating scPerplexity universal from
hard-tier pLDDT selective, so no ordering between these two findings is
asserted in the Abstract. No correction is needed.

---

## Intro §1 — `docs/drafts/paper-flattened-draft.md` contribution list

The Intro's §1 contribution list (lines 21–28) has six bullets (i)–(vi):

- **(i)** FlowA framework proposal (training-free re-inference framework)
- **(ii)** CodimensionSheetScheduler introduction (per-record adaptive controller)
- **(iii)** Cross-budget NFE compression (2.5–10× across six R-level cells)
- **(iv)** Cluster-robust per-record testing on the protein foldability cell — **scPerplexity framework-WINS uniformly across all tiers** and **hard-tier pLDDT framework-WINS selectively**, with a monotone `hard > medium > easy` pattern in Cohen's d_z replicated on two protein adapters
- **(v)** Five-arm cumulative-add ablation (A0–A4) isolating the cosine ramp from the paper-quantity-driven schedulers
- **(vi)** K1–K8 boundary dimensions as structural scope statements

The Intro's framework paragraph (immediately preceding the contribution
list, line 17) states Theorem 1 inline as the bounded-Lipschitz
convergence bound that the framework's four paper quantities imply. This
is a method contribution (Theorem 1 statement + four closed-form
quantities + three scheduler/operator algorithms), not the Finding 3
empirical verification (the Theorem 1 quantities load-bearing as a
regulariser on the protein-axis scheduler). The Finding 3 empirical
verification is reported in §3.1 and is not separately bulleted in the
contribution list.

**Signature ordering verdict: CORRECT.** Within contribution (iv), the
two findings that are bulleted are listed in the DeepSeek F3 signature
order: scPerplexity universal ("scPerplexity framework-WINS uniformly
across all tiers") appears first, and hard-tier pLDDT selective
("hard-tier pLDDT framework-WINS selectively") appears second. The
Theorem 1 finding is not a separate contribution bullet (it is a method
contribution in the framework paragraph that precedes the list), so
there is no third ordering position to violate in the contribution list.
No correction is needed.

---

## Results §3.1 — `docs/drafts/results-final.md`

§3.1 of the Results draft explicitly enumerates the three signature
findings in two locations:

**§3.1 narrative paragraph (line 37+):**

> *"(i) the framework delivers a universal improvement on the
> prior-fit metric scPerplexity across tiers and across adapters
> (cluster-robust on all tiers of the protein foldability axis,
> replicated on two protein adapters); (ii) the framework delivers a
> selective pLDDT uplift on the hard tier of the protein foldability
> axis, with a monotone `hard > medium > easy` pattern in Cohen's d_z
> that is confirmed on two protein adapters; and (iii) the four paper
> quantities of Theorem 1 are load-bearing as a regulariser on the
> protein-axis scheduler, with Cohen's d_z = −30.15 on the Kanzi
> synthetic L2 axis (CLM-057)."*

**§3.1 finding headers:**

- **Finding 1 — scPerplexity universal improvement** (cluster-robust, cross-adapter)
- **Finding 2 — hard-tier pLDDT selective uplift** (cluster-robust, cross-adapter)
- **Finding 3 — Theorem 1 quantities load-bearing as a regulariser** (CLM-057 kanzi synthetic)

**§3.8 Headline summary (re-confirmation):**

> *"(i) the cluster-robust cross-adapter per-record finding
> (scPerplexity universal), (ii) the cluster-robust cross-adapter
> per-record finding (hard-tier pLDDT selective), and (iii) the
> Theorem 1 load-bearing regulariser (CLM-057 kanzi synthetic)."*

**Signature ordering verdict: CORRECT.** Both §3.1 (narrative paragraph
and finding headers) and §3.8 (headline summary) list the three findings
in the DeepSeek F3 signature order: scPerplexity universal first,
hard-tier pLDDT selective second, Theorem 1 load-bearing third. The
ordering is asserted explicitly in §3.1 ("The three findings are reported
in **signature ordering** — (1) cluster-robust cross-adapter per-record
(scPerplexity universal), (2) cluster-robust cross-adapter per-record
(hard-tier pLDDT selective), and (3) Theorem 1 load-bearing regulariser
(CLM-057 kanzi synthetic)") and re-confirmed in §3.8 ("The three findings
are reported in **signature ordering**: (i) the cluster-robust
cross-adapter per-record finding (scPerplexity universal), (ii) the
cluster-robust cross-adapter per-record finding (hard-tier pLDDT
selective), and (iii) the Theorem 1 load-bearing regulariser (CLM-057
kanzi synthetic)"). No correction is needed.

---

## Cross-cutting verification

The signature ordering is **consistently applied** across all three
locations:

1. **Abstract** — does not enumerate findings; no ordering to violate.
2. **Intro §1 contribution list** — enumerates two of the three findings
   (scPerplexity, pLDDT) in contribution (iv) in the correct signature
   order (scPerplexity first, pLDDT second); Theorem 1 is a method
   contribution in the framework paragraph, not a separate finding bullet.
3. **Results §3.1 + §3.8** — enumerates all three findings in the correct
   signature order (scPerplexity → pLDDT → Theorem 1), explicitly asserted
   in both §3.1 narrative paragraph and §3.8 headline summary.

No location places the Theorem 1 finding (Finding 3) before the scPerplexity
finding (Finding 1) or the hard-tier pLDDT finding (Finding 2). No location
places the hard-tier pLDDT finding (Finding 2) before the scPerplexity
finding (Finding 1). The signature ordering is preserved end-to-end.

---

## Conclusion

The DeepSeek F3 signature ordering (scPerplexity universal → hard-tier
pLDDT selective → Theorem 1 load-bearing) is consistently applied in
the Abstract, Intro, and Results drafts. No ordering violations found.
No corrections applied. The paper is ready for Wave 213 P9 downstream
work (final-checklist integration).

**Sign-off.**

- Abstract signature ordering: **CORRECT** (not applicable — does not enumerate findings)
- Intro contribution ordering: **CORRECT** (scPerplexity before pLDDT in contribution (iv); Theorem 1 is a method contribution in the framework paragraph)
- Results §3.1 signature ordering: **CORRECT** (all three findings listed in the DeepSeek F3 order in both §3.1 narrative paragraph and §3.8 headline summary)