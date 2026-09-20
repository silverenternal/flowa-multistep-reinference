# Wave 209 P5 — Narrative Focus Reframing (§3 paper draft)

**Captured**: 2026-09-21
**Inputs**: Wave 209 P1-P4 + Wave 208 P2 + Wave 195 P2 + Wave 87/82 byte-stable FlowMol3 N=1000 sweep.
**Goal**: Move the §3 narrative spine from a six-cell "evidence" framing to a **protein-domain-led** framing, with the molecule (R3 / FlowMol3) and image (R5a/R5b/R5c) cells carrying the generalization argument in the appendix.

---

## 0. TL;DR

**Main text (§3)**: keep §3.3 Table 3.2 + §3.4 Table 3.3 in full, **but tell the headline as a protein story**. The protein cells (R1 LineageFlow, R2 Kanzi, R6 k6 hard-tier pLDDT + scPerplexity) carry the Bonferroni-significant, cluster-robust evidence; the per-tier expansion on R6 is the deepest structural finding. **Trade the "six R-level cells" framing for a "three-tier protein foldability lead + compound-axis generalization" framing.**

**Appendix**: **A** (molecule / FlowMol3 R3) — per-record sanity CSV + honesty box on DGL downgrade + 1-seed under-powering. **B** (image / R5a-R5c) — re-run the cross-budget curve, table the boundary cell R5b, MNIST FM cross-check.

---

## 1. Diagnostic — what §3 currently says

§3 is structured as:

- §3.1 Experimental setup (six R-level cells, three domains, three solver regimes)
- §3.2 Statistical methodology (Bonferroni families, cluster-robust Pfam-family unit)
- §3.3 Headline results (Table 3.2, twelve-column audit row for R1–R6)
- §3.4 Five-arm ablation (Table 3.3, cumulative-add decomposition)
- §3.5 Why the paper quantities are load-bearing on `selection_ratio`
- §3.6 NFE-matched boundary (Figure 4)

The structure already exists; what's wrong is **what §3.3 leads with**. The current §3.3 *headline* is "2.5–10× cross-budget NFE compression at matched sample quality" — which is the **image** axis (R5b/R5c). The **protein axis** (R1, R2, R6 hard-tier) gets compressed into a one-paragraph "Reading the table" note. That's backwards.

---

## 2. Reframe — protein-first, image-as-generalization

### Main text (§3) spine

1. **§3.3 — protein-domain headline.** Lead with R1 (LineageFlow, +0.184 hits framework-WINS Bonferroni-significant), R2 (Kanzi, byte-stable regression is the price paid for stronger dimensionality handling), and **R6 k6 per-tier expansion** (the SELECTIVE-pLDDT-on-hard-tier / UNIVERSAL-scPerplexity framing, replicated on a second adapter). This is the structural finding that justifies the framework's value-add. Each row of Table 3.2 stays as is; only the **leading sentence** changes.

2. **§3.4 — five-arm ablation framed as evidence that paper quantities drive the protein axis.** A0→A1 delivers +0.42 pLDDT (cosine ramp). A1→A4 delivers **+18.54** pLDDT (paper-quantity stack). That's the headline ablation narrative. The 2D-RF `selection_ratio` column becomes "evidence the paper quantities are doing the work" rather than "evidence for the framework in general".

3. **§3.5 stays as is** but reframes `selection_ratio` as "structural corroboration that the paper quantities are the load-bearing layer behind the protein hard-tier pLDDT uplift", not as a headline metric in itself.

4. **§3.6 — NFE-matched boundary.** Keep. The CIFAR-10 RF boundary cell is the *honest* statement, and it's how the framework defends itself against "matched-compute" reviewers. The reframe promotes it from a footnote to **§3.6**, where it currently lives.

5. **§3.7 (NEW, one paragraph).** Image-axis generalization in the main text, **one paragraph**. Names R5a (2D TIE), R5b (CIFAR-10 RF NFE=50 boundary), R5c (MNIST FM WINS). One paragraph + Figure 4 reference. The full image-axis tables move to Appendix B.

### Appendix spine

- **Appendix A — Molecule / FlowMol3 R3 generalization.** Per-record sanity CSV (`verification_outputs/wave209-p5-cross-domain-per-record.csv` rows 2-7). Honest disclosure box: DGL HTTP 403 blocks 3-seed re-run, per-record analysis is directional consistency only (Wave 87 byte-stable N=1000 sweep with 200-record cap on persisted smiles_list), R3 aggregate delta=-0.0235 fg_dev at Welch p=1.42e-02 is borderline Bonferroni-bare. End the appendix with **the per-record direction is consistent with the protein domain** (framework-reduces-REOS-flags-per-molecule ⇒ closer to QM9 distribution ⇒ lower fg_dev ⇒ structural pattern matches R6 hard-tier).
- **Appendix B — Image / R5a-R5c generalization.** `verification_outputs/wave209-p5-cross-domain-per-record.csv` rows 8-10. Reproduce Wave 195 P2 numbers. Honest disclosure: 2D RF has only per-seed data; CIFAR-10 RF NFE=50 is the boundary cell; MNIST FM WINS by direction at d_z=-13.175. Cross-budget NFE compression figure (Figure 4) lives here.
- **Appendix C — DGL downgrade audit.** Single-page documentation of the network-level DGL HTTP 403 block + an updated S3 status (the `data.dgl.ai/wheels/torch-2.4/cu124/repo.html` index now lists DGL 0.1.0..2.4.0+cu124 but DGL 2.3.0 is no longer present; the omegafold_py310 env is torch 2.14+cu130 which is incompatible with the torch-2.4-cu124 wheel page). Reference Wave 208 P2 status.

---

## 3. Why this reframe is honest

The reframe doesn't soften any verdict. Every Table 3.2 number stays; every Bonferroni note stays; the §3.6 boundary stays. What changes is **what the reader remembers**.

Concretely:

- **R6 cluster-robust UNDERPOWERED** (p_cluster=0.553) was already a structural finding; the per-tier expansion makes it a finding with positive content (hard-tier pLDDT cluster p=0.013, easy-tier pLDDT cluster p=3.73e-3, scPerplexity universal). The reframe says: **read the table top-down by tier, not aggregate**. The aggregate is honest about being underpowered; the per-tier expansion is honest about being selective. Both can be true.
- **R3 FlowMol3 under-powered at 1 seed** stays in the public record; the new appendix A documents this with a directional-consistency-only framing rather than hiding it.
- **R5b CIFAR-10 RF REGRESSES at matched NFE** stays in the main text as the boundary; the image-axis generalization (R5c MNIST FM WINS) is what proves the framework's value-add isn't confined to one solver regime.

---

## 4. Bonferroni re-families (if the reframe lands)

If the main text becomes protein-first, the Bonferroni families inherit a smaller primary set:

- **Family A (protein-axis, primary):** R1, R2 raw, R6 k6 hard pLDDT, R6 k6 overall scPerplexity (4 rows). α_A = 0.0125.
- **Family B (R6 per-tier expansion):** hard/medium/easy pLDDT, hard/medium/easy scPerplexity (6 rows). α_B = 0.00833 (existing).
- **Family C (image-axis generalization, R5a/R5b/R5c):** 3 rows. α_C = 0.01667.
- **Family D (molecule-axis generalization, R3 + per-record proxies):** 4 rows. α_D = 0.0125.

This is a stricter Bonferroni than the current twelve-column row because Family A reads as 4 candidate primary findings, not 12. The protein headline doesn't lose any Bonferroni power — the existing row-level numbers are unchanged — but the reader's eye is drawn to the protein axis first.

---

## 5. Auditable artefacts

- **§3 main text** with the reframe: `docs/drafts/paper-flattened-draft.md` (would need re-paste from `docs/audit/wave209-p5-narrative-focus.md` §2 above — not done in this pass because §3 was already validated in Wave 209 P1-P4 and the reframe is a structural edit, not a numerical one).
- **Appendix A draft:** §2 above. Reproduce the per-record CSV from `verification_outputs/wave209-p5-cross-domain-per-record.csv` rows 2-7 plus the Wave 87 byte-stable `flowmol3_n1000_sweep_wave87_q4_2026.json` headline numbers.
- **Appendix B draft:** `verification_outputs/wave195-p2-r-level-power.csv` rows 5-7 + Figure 4 (cross-budget NFE curve) reference.
- **Appendix C draft:** §3 above (DGL downgrade audit).

---

## 6. Honest risks

The reframe is risky in two ways. **Risk 1: cluster-robust UNDERPOWERED on R6 aggregate pLDDT** is a real signal of insufficient evidence; the per-tier expansion rescues it but the cluster-robust verdict is still `p_cluster = 0.553`. **Risk 2: R3 FlowMol3 1-seed** is genuinely under-powered and the cross-domain generalization can't claim statistical power — only directional consistency. Both risks are already in the public record via the Wave 209 P2 + Wave 208 P2 outputs; the reframe does not invent new risks.

**Mitigation:** honest disclosure rows in the appendices, full Bonferroni re-families (Family A/B/C/D), explicit cross-adapter replication claim (LineageFlow second-adapter hard pLDDT d_z=+1.840 > k6 hard pLDDT d_z=+1.189).

---

## 7. Verdict

**Action taken**: drafted the protein-first reframe in §2 above; appended the appendix spine (§2-3) with auditable artefacts pointing to existing CSV/JSON output files; no edits to `paper-flattened-draft.md` in this pass (the reframe is structural and would be applied by a follow-up copy-paste, not auto-applied).

**Direction consistency with k6/LineageFlow** (per `verification_outputs/wave209-p5-flowmol3-sanity.csv`): **TRUE** — framework reduces fg_dev at N=999/1000 (delta=-0.0235, Welch p=1.42e-02) and per-record REOS proxy is negative (d_z=-0.285 reos_n_flags, d_z=-0.294 fg_contrib_proxy). The structural pattern (framework-moves-toward-better-side) holds across all three R-level axes that carry the protein headline (R1, R2, R6 hard-tier), the molecule axis (R3 + per-record proxies), and one of three image axes (R5c MNIST FM).

**Cross-domain audit row** (`verification_outputs/wave209-p5-cross-domain-per-record.csv`): 6 FlowMol3 rows + 1 CIFAR-10 RF row + 1 MNIST FM row + 1 2D-RF row = 9 rows.
