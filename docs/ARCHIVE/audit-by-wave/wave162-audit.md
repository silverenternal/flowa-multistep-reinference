# Wave 162 P1 audit — §2 (JMAA) + §7 (14 innovations) + §10 (metrics) gap analysis

**Date**: 2026-09-15
**Branch**: main
**Wave scope**: READ-ONLY audit. No source edits to `docs/paper-draft.md`,
`docs/CONSOLIDATED_RESULTS.md`, `docs/CLAIMS.md`, or any code. The audit
output is **what the user feedback requires vs what is currently present
in each section**, with concrete file/line citations, and a precise
P2/P3/P4 scope recommendation for the upcoming ADDITIVE rewrite.

## 1. User feedback (preserved verbatim)

> 1. "JMAA那个论文还不能检索，你把具体的理论大概说一下"
>    => *JMAA paper is not retrievable; need concrete theory explanation
>    (not just cite).*
> 2. "而且我们创新点也没那么少吧"
>    => *we have more than a few innovation points; expand them.*
> 3. "指标你也没讲清楚"
>    => *metrics unclear; explain them clearly.*
> 4. "重新说"
>    => *rewrite / expand.*

The four feedback items point at three concrete sections of
`docs/paper-draft.md`: **§2 (framework + JMAA theory)**, **§7 (innovation
points)**, and **§10 (metrics / negative surface / R1-R6 disclosure)**.
This audit answers, for each section: *what is currently present, what is
gap, and what the P2/P3/P4 writers should add (ADDITIVE only).*

## 2. §2 JMAA theory — current state vs gap

### 2.1 Current state (file/line citations)

`docs/paper-draft.md` §2.8 (lines **257–358**) already carries a fully
self-contained concrete form of JMAA Theorem 1 — it does NOT say "see
Li 2026"; it states the bound, gives every quantity a closed-form one-
liner, and lists the four supporting lemmas + F-side regime:

| Element | Line | What is there |
|---|---|---|
| Theorem 1 (BL-convergence, concrete form) | 266–284 | Full bound `d_BL(μ, ν) ≤ A_g·ε + B_g·C_g·ε² + e_ρ·min(ρ⁴, (1-ρ)²η²)` with non-asymptotic qualifier |
| The four paper quantities (closed forms) | 286–295 | `A_g = (2π)^(-1/2) ∫ exp(-½x²)·g(x) dx`; `B_g = Σ_{z∈Z_g} exp(-z²/4)`; `C_g = e^{ρ²/2}/a`; `e_ρ = min(ρ⁴, (1-ρ)²η²)` |
| Lemma 2 (sheet-vs-cell) | 299–304 | `μ_{g,ε}(∪I_z) ≤ B_g·ε` |
| Lemma 3 (per-cell tail) | 305–309 | `∫_{I_z} p_ε dx ≤ C_g·e^{-z²/4}·ε²` |
| Lemma 4 (exterior-gap floor) | 310–314 | `⌊E(β)⌋ ≥ e_ρ/4` whenever `ε² < e_ρ/log 2` |
| Lemma 5 (BL-rate witness) | 315–319 | `selection_ratio → 1` at the Theorem 1 rate |
| F-side hypotheses (regime) | 321–340 | `d ∈ (0,∞)`, `c ∈ (0,1]`, `ρ ∈ (0, d/4)`, `η ∈ (0,∞)` with the role of each variable named |
| Concrete numerical witness (C4 closure) | 342–350 | `selection_ratio` 0.8061 → 0.9896 across rounds 0–6 |

§3.2 (lines 379–407) restates the theorem in compact four-quantity
form for the algorithm layer (one-liner per quantity + FlowA role +
algorithm consumer). §3.3 (lines 410–443) maps each lemma to a FlowA
algorithm: Lemma 2 + Lemma 3 → `CodimensionSheetScheduler`;
Theorem 1 → `EvidenceDrivenScheduler` (PID-lite); Lemma 4 →
`BoundedMergeOperator` floor.

### 2.2 Gap diagnosis

The **theorem itself is fully self-contained** — the math is there in
the §2.8 concrete-form block. What is **missing** for the user's
"JMAA paper not retrievable" feedback is an *executive-summary
explanation* that lets a reviewer who **never opens Li 2026** understand
the *intuition*:

1. **No intuition paragraph** for *why* the bound is `A_g·ε + B_g·C_g·ε²
   + e_ρ·min(ρ⁴, (1-ρ)²η²)`. The current text states the bound and the
   one-line closed forms but does not narrate what *each term* is
   measuring (sheet-evidence vs root-cell mass vs exterior-gap
   geometry) in plain English. A non-retrievable paper makes this gap
   acute.
2. **No worked numerical example** beyond the C4 closure 0.8061 →
   0.9896 ratio. The C4 paragraph (line 342) gives the ratio but does
   not **show the reader how to compute it from `(A_g, B_g, C_g, e_ρ)`**
   — a numerical worked example that plugs in toy values of
   `(ε, ρ, η, d, c)` would make the theory independently verifiable.
3. **No F-side hypothesis physical meaning**. The four quantities
   `d, c, ρ, η` are stated as a regime (line 326) but the *role* of each
   is named once and not unpacked in plain language.
4. **Abstract citation-only references** still exist in the paper
   (e.g. line 105 `JMAA Theorem 1 / Lemmas 2–5 derivation`), which the
   user feedback is pointing at when saying "JMAA paper not retrievable".

### 2.3 P2/P3 recommendation (ADDITIVE only)

P2 should ADD an **§2.9 "Plain-language theory summary"** subsection
immediately after §2.8 (after line 358). Scope (≤ 60 LOC, ADDITIVE — does
not delete any of §2.1–§2.8):

- 4-paragraph executive summary of Theorem 1 in reviewer-intuition
  language: (i) what `BL`-convergence means and why it is the right
  metric for inference-time re-inference; (ii) what each of the three
  terms (`A_g·ε`, `B_g·C_g·ε²`, `e_ρ·min(…)`) is measuring — sheet
  evidence, root-cell mass, exterior-gap geometry; (iii) one
  worked-numerical example with toy `(A_g=1, B_g=2, C_g=3, e_ρ=0.5, ε=0.01,
  ρ=0.3, η=1.0, d=2, c=1)` showing the bound evaluates to
  `0.01 + 6·10⁻⁴ + 0.5·min(0.0081, 0.49) ≈ 0.2550`; (iv) what `selection_ratio
  → 1` means as `ε ↓ 0` (the numerical witness FlowA measures).
- A 1-paragraph **physical-meaning unpacking** for `d, c, ρ, η`: fibre
  diameter (Gaussian-sheet decay), uniform-separation constant (root-
  family gap), cell-to-fibre ratio (Lemma 3 applicability),
  suppression exponent (root-suppression factor).

The P2 path preserves §2.8 verbatim (theorem statement + closed forms
+ lemmas + F-side regime unchanged) and only ADDS §2.9 as a
reviewer-facing intuition layer.

## 3. §7 innovation points — current state vs gap

### 3.1 Current state (file/line citations)

`docs/paper-draft.md` §7.11 "14 Innovation Points (4 tiers)" (lines
**5500–5546**) is already a reviewer-facing list of 14 concrete
innovation points across 4 tiers:

| Tier | Items | Innovation one-liner | Cross-ref |
|---|---|---|---|
| **A — Algorithm / Theory (4)** | A1 (DERIV-001 paper-quant-driven) | 23 hyperparameters, strict-DAG dispatcher | §2.6 |
| | A2 (Theorem 1 → executable) | `(A_g, B_g, C_g, e_ρ)` as algorithm params | §2.8, §3.3 |
| | A3 (Training-free inference) | Frozen θ; no distillation / LoRA / fine-tune | §3.1 |
| | A4 (3 byte-stable composite lifts) | Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 +0.1182 | §7.6 R1-R3 |
| **B — Architecture (3)** | B1 (4 Protocols × 17 state machines × 333 transitions) | PEP 695 generic state machines, byte-deterministic transition log | §3.5 |
| | B2 (8-method `FlowMatchingODEAdapter`) | Single canonical Protocol surface + `digest()` SHA-256; LCM-of-FM-family | §2.1, §2.7 |
| | B3 (Hexagonal port set — 8 named ports) | SchedulerPort, PolicyDriverPort, MergeOperatorPort, BlenderPort, AdapterPort, MixerPort, EvaluatorPort, EnvelopePort | §2.3 |
| **C — Methods / Algorithms (4)** | C1 (3 algorithms grounded in Lemmas 2–4) | `CodimensionSheetScheduler` (Lemma 2+3), `EvidenceDrivenScheduler` (Theorem 1), `BoundedMergeOperator` (Lemma 4) | §3.3 |
| | C2 (Solver-agnostic) | Euler / Heun / DPM-Solver++ / RK45 / CTMC / BFN | §3.3, §4.3 |
| | C3 (2.5–10× NFE speedup at matched sample quality) | CIFAR-10 Heun 2nd-order matched-NFE | §7.6.3, §7.7 |
| | C4 (Structural 4-way differentiation) | Isolation (36 tests) + interaction (53 cells) + cumulative (5×3 ablation matrix) + negative surface (K1–K8) | §3.4, §7.6, §10.4 |
| **D — Reproducibility / Integrity (3)** | D1 (D.4 72/72 byte-stable) | Materialization route + `OMP_NUM_THREADS=1` | §3.6, §10.4 |
| | D2 (Full SHA-256 ckpt-pinning chain) | 3 Tier 3 ckpts (Kanzi / LineageFlow / FlowMol3) SHA-256 verified on disk | §7.1, §12 |
| | D3 (K1–K8 honest negative surface) | 8-item `framework_ties / regresses / underpowered` disclosure, 4/5 RCs RESOLVED via Wave 149–150 | §10.4 |

Total: **4 + 3 + 4 + 3 = 14 innovation points**, grouped by what they
*contribute* (algorithm/math, system structure, novel methods,
reproducibility rigour).

### 3.2 Gap diagnosis

The 14 innovation points ARE there. The user's "我们创新点也没那么少吧"
(we have more than a few) feedback is consistent with this — the table
already enumerates 14 explicitly. The remaining gap is **organizational
+ comparative**:

1. **No §7.11 introduction that names the gap the innovations close**.
   The reader hits the 14-row table cold without a one-paragraph
   framing of *what existed in the literature before FlowA* (Consistency
   Models + iCT retrain; LCM LoRA distill; Rectified Flow Reflow
   distillation; DPM-Solver++ inner-solver acceleration; none with
   paper-quantity-driven inference-time re-inference). The §5.0 related-
   work section has the prose but §7.11 lacks a 1-paragraph lead-in.
2. **No "tier-rationale" paragraph** explaining why the 4 tiers (4+3+4+3
   = 14) are grouped this way. Currently the rationale is implied ("what
   they *contribute*"); a reviewer-facing 2-sentence rationale would
   make the §7.11 standalone.
3. **No cross-link from §1 Introduction paragraph (iv)** (the headline
   "14 innovation points" claim) to §7.11. Line 76 names "17 typed state
   machines with 333 typed transitions" and line 88 names "333 typed
   transitions" but §1 does not cross-link to §7.11.

### 3.3 P2/P3 recommendation (ADDITIVE only)

P2 should ADD a **§7.11 introduction paragraph** (≤ 12 LOC) immediately
before line 5502 (before the "This subsection enumerates…" sentence).
Scope:

- 1 paragraph framing: *what existing literature lacks* (training-free
  paper-quantity-driven inference-time re-inference; the gap between
  re-querying frameworks that retrain/distill vs solver-level
  acceleration that does not re-query) + the 4-tier rationale (algorithm
  / architecture / methods / reproducibility, mapped to *what each
  tier contributes to closing that gap*).
- 1 cross-link callout: "§1 paragraph (iv) headline '14 innovation
  points' expands to the §7.11 enumeration below; this subsection is
  the reviewer-facing summary, with each row's cross-reference
  resolving back to where the item is established."
- 1 sentence on the 4+3+4+3 count rationale (why 4 in tier A
  — algorithm/theory is the largest contributor; why 3 in tier D —
  reproducibility is the smallest but most-load-bearing for camera-
  ready acceptance).

The P2 path preserves §7.11 verbatim (all 14 rows + tier count footer
unchanged) and only ADDS the framing paragraph before the table.

## 4. §10 metrics — current state vs gap

### 4.1 Current state (file/line citations)

The user's "指标你也没讲清楚" (metrics unclear) feedback targets the
**R1–R6 metrics** (paper-metric framework_improves headline claims) and
the **negative-surface metrics** (K1–K8 known regressions/ties).

**R1–R6 framework_improves are listed 6 times across the paper**, in
descending specificity:

| Source | Line | Form | R-cells present | p-values | Bonferroni |
|---|---|---|---:|---|---|
| §1 Introduction headline table | 92–99 | Table with verdict column | 6 (R1–R6) | partial (only R1 has `Bonf p≈0`) | implicit only |
| §7.6 "Table A" | 3893–3902 | Per-row table with `Bonf-sig p` column | 6 (R1–R6) | yes (1 column `Bonf-sig p`) | **yes** (column header `Bonf-sig p`) |
| §7.6 "Table F" (Wave 93 12-row) | 3954–3969 | Per-cell table with `p (raw)` + `p (Bonf)` | 12 (3 Tier 3 models × 4 metrics) | yes (both columns) | **yes** (column `p (Bonf)`) |
| §10.4 K1–K8 + K8 R1 provenance | 6146–6256 | Per-item disclosure | 1 (R1 only, in K8) | yes (R1 +116% has `p < 1e-10`) | **yes** (explicit `Bonf-significant`) |
| §10.5.3 K2–K8 status table | 6328–6344 | Per-row status | 1 (R1 in K8) | n/a | n/a |
| §10.5.4 acceptance gates | 6346–6352 | Gates only | n/a | n/a | n/a |
| §12 R1-R6 cross-link expansion | 5973–6037 | Per-R with sha256 | 6 (R1–R6) | partial (R1 has `p < 1e-10`) | partial (only R1 explicit) |

**Concrete R1–R6 numbers** (from §7.6 Table A, lines 3895–3902):

| R | Tier | Model | Metric | N | Baseline | Framework | Δ | Bonf-sig p | Source on disk |
|---|---|---|---|---:|---:|---:|---:|---|---|
| R1 | Tier 3 | LineageFlow | `hmmscan_total_hits` | 1000 | 158 | 342 | **+184 (+116%)** | **< 1e-10** | `docs/audit/wave86-phase3-sweep.md` §2 + `verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/` (sha256-pinned) |
| R2 | Tier 3 | FlowMol3 | `fg_dev` | 1000 | 0.6381 | 0.6146 | **−0.0235** | **< 0.05 (4.05σ)** | `verification_outputs/flowmol3_n1000_sweep_q4_2026.json` |
| R3 | Tier 1 | CIFAR-10 RF v2 | FID | 250 | 218.87 (NFE=5) | 122.18 (NFE=2) | **−44.17%** | NFE-averaged (not Bonf) | `docs/CONSOLIDATED_RESULTS.md §4.3` |
| R4 | Tier 1 | 2D Two Moons | W₂ | 1000 | 0.5029 | 0.4663 | **−7.28%** | matched NFE 500, 3 seeds | `docs/r4-survey/10-sota-2d-experiment-results.md` |
| R5 | Tier 1 | 2D Eight Gaussians | W₂ | 1000 | 0.6606 | 0.5919 | **−10.40%** | matched NFE 500, 3 seeds | `docs/r4-survey/10-sota-2d-experiment-results.md` |
| R6 | Tier 2 | MNIST FM | FID | 1000 | 409.18 | 347.75 | **−15.01%** | n/a (CristianLazoQuispe ckpt) | `verification_outputs/baseline_comparison_q4_2026.json` |

**K1–K8 negative surface** (from §10.4 + §10.5.3, lines 6146–6344):

| Item | Verdict | Status (Wave 161) | Metric |
|---|---|---|---|
| K1 | FlowMol3 `pb_validity_pct` −9.95pp (UFF-vs-xtb) | RESOLVED-PARTIAL (RC5 35h GPU 5-arm ablation deferred) | Paper metric (PoseBusters) |
| K2 | Kanzi framework_inv_proj paper-metric TIES, Δ=−0.0222 Å | RESOLVED (byte-stable σ=0, dual-mode identity) | Paper metric (Kabsch RMSD Å) |
| K3 | CIFAR-10 RF v4 matched-NFE=50 REGRESS +221–226% | PROTOCOL_MISMATCH | Paper metric (FID) |
| K4 | LineageFlow `coverage_any_hit` UNDERPOWERED, z=−1.136, p=0.26 | UNDERPOWERED | Paper metric (binary) |
| K5 | LineageFlow `top1_family_type` TIES at zero | TIES_AT_ZERO | Paper metric (binary) |
| K6 | LineageFlow foldability + self_consistency N=5 only | RESOLVED (Wave 161 P1 N=1000 sweep COMPLETED; pLDDT +1.12 / scPerplexity −3.92) | Paper metric (Ω-fold + ESM-IF) |
| K7 | LineageFlow `novelty_mmseqs2` BLOCKED | RESOLVED-WITH-CANONICAL-HEADLINE-ON-DISK (Wave 158 P2) | Paper metric (MMseqs2 nearest-neighbour identity) |
| K8 | LineageFlow N=1000 HMMER + 8-cell NFE scan | RESOLVED + CANONICAL-HEADLINE-ON-DISK | Paper metric (`hmmscan_total_hits`) |

### 4.2 Gap diagnosis

The R1–R6 numbers ARE there, with concrete baseline + framework values
in §7.6 Table A. The user's "metrics unclear" feedback is best read as
pointing at three concrete sub-gaps:

1. **No §10 "Metrics explained" subsection** that walks the reader
   through each metric in plain language. Currently §10 is "Known
   negative surface & provenance discipline" (§10.4) — a disclosure
   surface, not a metrics primer. The user is asking *what is
   `hmmscan_total_hits` and how is it measured?* — that explanation is
   spread across §7.4 (LineageFlow subsection), §7.5 (FlowMol3
   subsection), and §S7.2 (supplementary), not consolidated.
2. **No unified R1–R6 table in §10**. §10.4 K8 (lines 6207–6219)
   mentions the R1 +116% headline in passing but does not enumerate
   R2–R6. The §7.6 Table A is the only place a reviewer sees all 6
   cells together with `p (Bonf)` + source path. A reader who skips
   directly from §1 to §10 misses R2–R6 entirely.
3. **No metric-definition glossary** — each of the 6 R-metrics uses a
   different paper's notion (`hmmscan_total_hits` is a count of HMMER
   domain hits against Pfam-A.hmm; `fg_dev` is the FlowMol3 paper's
   functional-group deviation from a reference molecule; W₂ is the
   2-Wasserstein distance; FID is Fréchet Inception Distance; v2 NFE-
   averaged means NFE=2 vs NFE=5, NOT matched-NFE). The definitions
   live in the source-paper citations but are not consolidated.

### 4.3 P2/P3 recommendation (ADDITIVE only)

P2 should ADD a **§10.6 "Metrics explained" subsection** (≤ 80 LOC,
ADDITIVE) at the end of §10 (after line 6356, before §11 Broader
Impact). Scope:

- **§10.6.1 Metric glossary (6 metrics, ~10 LOC)** — one short paragraph
  per R-cell metric with: (i) what it measures, (ii) what the paper
  reports as target, (iii) what FlowA measured (baseline / framework /
  Δ / p / Bonf-sig), (iv) on-disk source path + sha256.
- **§10.6.2 Unified R1–R6 table (~30 LOC)** — the same 6 rows from §7.6
  Table A, copied into §10.6.2 as a single reviewer-facing table with
  the same columns. ADDITIVE cross-reference (does not delete §7.6 Table
  A).
- **§10.6.3 K1–K8 metrics explained (~40 LOC)** — one paragraph per K
  cell with: (i) what metric it is, (ii) what the framework-vs-baseline
  reading is (baseline / framework / Δ), (iii) why this is *negative*
  (pipeline gap vs framework regression), (iv) current resolution
  status from §10.5.3. Cross-link back to §10.4 + §10.5.3.
- **§10.6.4 How to read a "p (Bonf) < α" verdict (~10 LOC)** — 1
  paragraph explaining the Bonferroni correction (the Wave 93 12-row
  power analysis uses α=0.05 / 12 tests = 0.0042 effective threshold;
  the R1 +116% headline hits p (Bonf) = 0.0; R2 fg_dev hits p (Bonf) <
  0.05 in the Wave 82 4.05σ test, which is the only Tier 3 paper-metric
  axis besides R1 with a statistically-significant framework_improves).

P3/P4 can extend this with worked numerical examples for each metric
(e.g. "for `hmmscan_total_hits`, the Wave 158 P2 measurement runs
`hmmscan --cpu 4 --noali` against `Pfam-A.hmm` and counts the
`!` flag in column 22 of the output `hits.tbl` file — 158 baseline
hits vs 342 framework hits is the R1 +116% number").

The P2 path preserves §10.1–§10.5 verbatim and only ADDS §10.6 as a
reviewer-facing metrics primer at the end of §10.

## 5. Cross-section interaction + Wave 151-161 provenance

| Feedback item | Section | Current line range | Wave that added it | Status |
|---|---|---|---|---|
| "JMAA theory concrete" | §2.8 (lines 257–358) | Wave 151 P2 (`§2.8 JMAA Theorem 1 — concrete form (math, lemmas, F-side hypotheses)`) | **4 paper quantities + 4 lemmas + F-side regime + C4 witness already there** |
| "14 innovation points" | §7.11 (lines 5500–5546) | Wave 151 P2 (`§7.11 14 Innovation Points (4 tiers)`) | **14 rows + 4+3+4+3 tier footer already there** |
| "Metrics R1–R6 explained" | §7.6 Table A (lines 3893–3902) + §10.4 K1–K8 (lines 6146–6256) | Wave 151 P2 + Wave 153 P2 + Wave 159 P1 + Wave 160 P2 + Wave 161 P2 (R1 +116% provenance + K1–K8 + K6 RESOLVED + R6 K6 numbers) | **6 R-cells in §7.6 Table A + 8 K-cells in §10.4 + 9 K-statuses in §10.5.3 already there** |
| "Bonferroni p-values" | §1 headline (line 99, R1 only) + §7.6 Table A (column `Bonf-sig p`, all 6 rows) + §7.6 Table F (column `p (Bonf)`, 12 rows) + §10.5.3 (K6 RESOLVED references R6 K6 in §15.58) | Wave 151 P2 + Wave 159 P1 + Wave 161 P2 (R1 +116% Bonf p=0 + R2 fg_dev 4.05σ + R6 K6 RESOLVED) | **§7.6 Table A has `Bonf-sig p` column header on all 6 R-rows + §7.6 Table F has `p (Bonf)` column on all 12 cells** |

## 6. P2/P3/P4 scope recommendation (ADDITIVE only)

| Wave | Section | LOC budget | What to add | What to preserve |
|---|---|---:|---|---|
| **P2** | §2.9 (new subsection after §2.8 line 358) | ≤ 60 LOC | 4-paragraph plain-language theory summary + worked-numerical example + F-side physical-meaning unpacking | §2.1–§2.8 verbatim |
| **P2** | §7.11 intro paragraph (before line 5502) | ≤ 12 LOC | 1-paragraph framing + 1 cross-link callout + 1 count-rationale sentence | §7.11 table (14 rows + footer) verbatim |
| **P2** | §10.6 (new subsection after line 6356) | ≤ 80 LOC | Metric glossary (6 metrics) + unified R1–R6 table + K1–K8 explained + Bonferroni primer | §10.1–§10.5 verbatim |
| **P3** | §2.10 (worked numerical examples) | ≤ 40 LOC | 2-3 worked examples with concrete (ε, ρ, η, d, c) values | §2.9 verbatim |
| **P3** | §10.6.5 (extended metric examples) | ≤ 50 LOC | Worked numerical examples per metric (e.g. how `hmmscan_total_hits` is counted from `hits.tbl`) | §10.6.1–§10.6.4 verbatim |
| **P4** | Final synthesis + drift check | n/a | Accept gates: pytest 72/72 + ruff 0 + claims consistency `No drift` | All P2/P3 paragraphs verbatim |

**Total P2 budget**: ≤ 152 LOC across 3 new subsections / paragraphs.
**Total P3 budget**: ≤ 90 LOC across 2 extended worked-examples.
**Total Wave 162 budget**: ≤ 242 LOC, all ADDITIVE.

## 7. Active claims count (39)

`docs/CLAIMS.md` carries **39 ACTIVE claims** (out of 43 total entries;
the other 4 are 2 ACTIVE-with-INVERTED-NOTE + 2 DEPRECATED). All 39
ACTIVE claims are referenced by `tools/check_claims_consistency.py`
which must report `No drift detected` at P4 close. The Wave 162 P2/P3
additions do not introduce any new claim (no CLM-NNN entry is added);
they only add *plain-language explanations* of the theorem, the
innovation points, and the metrics, all of which are already grounded
by the existing CLM-001 (sheet-evidence), CLM-002 (root-cell evidence),
CLM-003 (BoundedMergeOperator floor), CLM-004 (selection_ratio
witness), and downstream CLMs.

## 8. Acceptance gates (must pass at P4 close)

- `pytest tests/ -k "d4" -q --tb=line` → **72 passed**
- `ruff check adaptive_reflow/ tests/ scripts/ tools/` → **0 errors**
- `python tools/check_claims_consistency.py` → **"No drift detected"**
- No edits to §2.1–§2.8, §3, §4, §5, §6, §7.1–§7.10, §8, §9, §10.1–§10.5,
  §11, §12 (ADDITIVE only — §2.9, §7.11 intro paragraph, §10.6 are new)
- `docs/headline-evidence/` and `verification_outputs/` cross-links
  unchanged (the P2/P3 additions cite existing on-disk files)

## 9. Conclusion

The user's three feedback items are **partially addressed** by the
Wave 151 P2 + Wave 153 P2 + Wave 159 P1 + Wave 160 P2 + Wave 161 P2
additions to `docs/paper-draft.md`:

- §2.8 has the **math** (theorem + 4 quantities + 4 lemmas + F-side
  regime + C4 witness) — but lacks the **intuition layer** (plain-
  language explanation, worked numerical example, physical-meaning
  unpacking) that a reviewer with a non-retrievable JMAA paper would
  need.
- §7.11 has the **14 innovation points** across 4 tiers — but lacks
  the **framing paragraph + cross-link** from §1 to §7.11 and the
  tier-rationale explanation.
- §7.6 Table A has the **R1–R6 numbers + Bonf-sig p-values + source
  paths** — but §10 lacks a **metrics-explained subsection** that
  consolidates the 6 R-cells with metric definitions + a unified table
  + K1–K8 explained + Bonferroni primer.

Wave 162 P2/P3/P4 should ADD three reviewer-facing subsections (§2.9,
§7.11 intro paragraph, §10.6) — total ≤ 242 LOC, all ADDITIVE — to
fully close the user's feedback loop. No claim is added, no CLM
changes, no headline numbers change, no headline verdicts change.

**ADDITIVE only. Gates preserved. P4 close requires `No drift detected`.**

---

*End of Wave 162 P1 audit doc. P2/P3/P4 (ADDITIVE only) follows per
section 6 budget.*
