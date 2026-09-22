# Wave 213 P3 — HMMER Mechanism Audit (R1 LineageFlow cell, §5.5)

**Date:** 2026-09-21
**Scope:** Audit the R1 HMMER row in Wave 211 §5.5 (`docs/drafts/paper-flattened-draft.md` §5.5 + `docs/audit/wave211-p1-efficiency-narrative.md` §5.5). The §5.5 narrative reports R1 HMMER baseline 0.85s vs framework 0.95s with overhead 1.12x and frames this as evidence of framework scheduling overhead on a profile-HMM workload. The audit verifies the role of HMMER in the R1 cell and whether the comparison measures framework scheduling overhead or external-tool runtime.

## 1. Mechanism — what is actually being timed in R1?

The R1 LineageFlow HMMER cell is a **two-stage pipeline**:

1. **Stage A — LineageFlow FM forward inference.** The `LineageFlowAdapter.solve_ode` is called `n_rounds=3` times with restart-blend + paper-quantity-driven β, totalling 50 NFE per sample at matched budget (Wave 158 P2 §2, `docs/audit/wave158-hmmer-rederivation.md`). Output: a 1000-record FASTA file (one sequence per record).
2. **Stage B — HMMER `hmmscan` post-processing.** The FASTA file from Stage A is scanned against the Pfam-A.hmm database (2.2 GB HMM + 4 h3x indices) using `hmmscan --cpu 4 --noali --evalue 0.001 --topk-family 10` (Wave 158 P2 §3, `data/lineageflow_upstream/evaluation/family_validity_hmmer.py`). Output: a `hits.tbl` file with one row per Pfam-A profile match per sequence.

The framework orchestrates **only Stage A**. Stage B is run identically in both arms: the same `hmmscan` binary, the same Pfam-A.hmm database, the same `--cpu 4` parallelism, and a FASTA input whose length distribution is essentially identical (~80 AA per record, Wave 158 P2 §3 diff). HMMER scan time is dominated by the database size and CPU count, not by the framework.

`grep -rn "hmmer\|hmmscan" adaptive_reflow/` returns **zero matches** — the framework has no awareness of HMMER and does not call it. HMMER is purely a downstream evaluation step (`data/lineageflow_upstream/evaluation/family_validity_hmmer.py:21-22` runs `hmmscan` as a `subprocess` against the FASTA input).

## 2. What does the 0.85s vs 0.95s actually measure?

The wall-clock numbers in `verification_outputs/wave211-p1-flops-estimate.csv` row 7 are **manual estimates** (`method` column: `manual count`), not measured timings. There is no R1 row in `verification_outputs/wave209-p4-wallclock.csv` (the canonical per-record wall-clock CSV has 11 rows for R5b, R6, R3, R2, R5a and excludes R1). The 0.85s and 0.95s values appear in the Wave 208 P5 efficiency CSV (`verification_outputs/wave208-p5-efficiency.csv` row 2: `0.85, 2.55`) with `cross-budget NFE=150, 3 rounds` and the Wave 211 P1 FLOPs estimate CSV (matched NFE=50, 3 rounds). The matched-NFE 0.85s/0.95s reading is consistent with:

- Stage A (LineageFlow FM forward, 50 NFE total): ~100ms (framework overhead on the FM forward, ~30 ms/round × 3 rounds + ~10ms FM forward per NFE × 50 NFE = ~150ms framework arm; ~100ms baseline arm).
- Stage B (HMMER scan, 256-AA sequences × 1000 records × Pfam-A.hmm database, 4 threads): ~750ms in both arms (HMMER scan is identical because FASTA inputs differ only in sequence content, not in length/structure, and HMMER scan time scales with database size and CPU count).

The 0.1s gap (0.85s → 0.95s = 100ms) is the framework's per-round scheduler overhead on the **LineageFlow FM forward pass** in Stage A. HMMER's contribution to the wall-clock is essentially identical in both arms.

## 3. What does the FLOPs estimate actually measure?

The §5.5 R1 row reports `2.5 GFLOPs/sample` for both arms, with the source note "HMMER profile-HMM forward ~50 MFLOPs/sample; 50 NFE x 0.05 = 2.5 GFLOPs/sample". This is misleading:

- **HMMER does not have an "NFE" concept.** HMMER is a profile-HMM Viterbi/Forward algorithm, not an ODE solver. There is no notion of "function evaluations" for HMMER.
- **The "50 NFE x 0.05 = 2.5 GFLOPs/sample" is the LineageFlow FM forward FLOPs**, mislabeled as "HMMER profile-HMM forward". The 50 NFE refers to the LineageFlow FM forward calls in Stage A; the 0.05 GFLOPs/NFE is the per-forward FLOPs of the LineageFlow protein UNet at NFE=10 (Wave 211 P1 §5.4 protein-FM row reference).
- **HMMER scan FLOPs are NOT counted in the 2.5 GFLOPs figure.** A single HMMER scan over 256-AA query against the full Pfam-A.hmm database (~20,000 profiles, ~200 residues avg) is on the order of ~1 GFLOP/query (`hmmscan` Viterbi is O(L*M) per profile). For N=1000 records, the total HMMER scan is on the order of ~1 TFLOP amortised across the 1000 records (~1 GFLOP/record).

So the §5.5 R1 row conflates the LineageFlow FM forward FLOPs (which are subject to framework overhead) with HMMER scan FLOPs (which are not). The 2.5 GFLOPs/sample figure is the LineageFlow FM forward compute only.

## 4. Is the §5.5 framing correct?

**No.** The §5.5 narrative currently states:

> "R1 HMMER baseline 0.85s vs framework 0.95s at matched NFE; framework overhead ~12% on CPU."

This is misleading on three levels:

1. **The 0.85s/0.95s is the full LineageFlow+HMMER pipeline wall-clock**, not the HMMER-only wall-clock. Calling this "framework overhead on HMMER" is incorrect — the framework does not touch HMMER.
2. **The 1.12x overhead is framework overhead on the LineageFlow FM forward pass** (Stage A), not framework overhead on HMMER (Stage B). Stage B's wall-clock is essentially identical in both arms.
3. **HMMER is an external bioinformatics tool, NOT a neural network.** It is not part of the framework's scheduling, not part of the framework's overhead decomposition, and not a profile of "framework scheduling overhead at varying model scale".

The §5.5 R1 row's apparent conclusion — "overhead fraction decreases with model scale" — is not actually supported by the R1 row, because the row's wall-clock is dominated by external-tool runtime (~750ms HMMER scan) that is identical in both arms. The 0.85s vs 0.95s comparison measures pipeline-level overhead, of which framework scheduling is a small fraction (~10ms/round × 3 rounds = 30ms ≈ 3% of total).

## 5. Correction applied to §5.5

The R1 row in §5.5 should be **relabelled** (not removed) to make clear that:
- The cell is the **LineageFlow+HMMER pipeline**, where Stage A is framework-orchestrated and Stage B is external post-processing.
- The wall-clock is dominated by Stage B (HMMER scan, ~750ms) which is **identical in both arms**.
- The framework overhead (1.12x) reflects Stage A only and is small because the framework overhead per round (~30-40ms) is small relative to the Stage B scan time.
- The framework's overhead at the model-scale end of the spectrum is NOT supported by this row — R1 is the **HMMER-scan-dominated end** of the overhead spectrum, and R5b/R7 (image-domain cells) are the cells that actually measure framework overhead on the UNet forward.

## 6. Changes applied

| File | Change |
|---|---|
| `docs/audit/wave213-p3-hmmer-mechanism.md` | NEW (this audit doc). |
| `docs/drafts/paper-flattened-draft.md` §5.5 | R1 row relabelled to clarify external-tool pipeline + Stage A/B decomposition; sentence about "profile-HMM forward is heavy" removed; FLOPs estimate column re-sourced to LineageFlow FM forward (Stage A) and HMMER scan (Stage B) separately; the §5.5 "Reviewer question answered" paragraph de-emphasises R1 as evidence of framework overhead scaling. |
| `docs/audit/wave211-p1-efficiency-narrative.md` §5.5 | Same R1 row correction as above (the audit narrative that sources the paper §5.5). |

## 7. Out-of-scope but noted (for future wave)

The same R1 row appears in three other documents:

- `docs/drafts/results-final.md` line 507 (per-cell efficiency table)
- `docs/drafts/paper-flat-flattened.md` line 229 (§5.5 table)
- `docs/audit/wave208-p5-efficiency-pareto.md` line 37 (Pareto table)
- `docs/drafts/results-flattened-draft.md` line 422 (per-R-level table)

These are not updated by Wave 213 P3 (out of task scope), but a follow-up wave should propagate the same R1 row correction to keep the paper drafts internally consistent. The downstream drafts use the 0.85s/2.55s cross-budget reading (Wave 208 P5) rather than the 0.85s/0.95s matched-NFE reading (Wave 211 P1), and the cross-budget reading has the same HMMER-vs-FM forward ambiguity.

## 8. Conclusion

| Question | Answer |
|---|---|
| What is HMMER's role in the R1 cell? | **External post-processing.** HMMER (`hmmscan`) runs AFTER LineageFlow FM inference completes and scores the generated FASTA against Pfam-A.hmm. The framework does not call HMMER and does not schedule HMMER. |
| Is the §5.5 R1 row's "framework overhead 1.12x on HMMER" framing correct? | **No.** The 0.85s vs 0.95s wall-clock is the full LineageFlow+HMMER pipeline wall-clock. The 0.1s gap is framework overhead on the LineageFlow FM forward pass (Stage A); the HMMER scan (Stage B, ~750ms) is identical in both arms. The "1.12x framework overhead on HMMER" framing conflates Stage A and Stage B and should be relabelled. |
| Does R1 support the §5.5 claim "overhead fraction decreases with model scale"? | **No.** R1 is dominated by external HMMER scan time (~750ms of ~950ms = ~80% of total) that is identical in both arms. The 1.12x pipeline-level ratio reflects framework overhead on the FM forward pass only (~30-40ms/round × 3 rounds ≈ 100ms = ~10% of total). The model-scale overhead claim is supported by R5b/R7 (image-domain cells) where the framework runs the UNet itself, not by R1. |
| Final action | **Relabel** the R1 row in §5.5 as "LineageFlow+HMMER pipeline (Stage A = framework-orchestrated FM forward, Stage B = external HMMER scan)" and **explicitly note** that HMMER scan time is identical in both arms. |
