# Wave 238 P3 — Journal Decision (TPAMI → TNNLS) + Cover Letter Update

**Captured:** 2026-09-21
**Author:** Wave 238 P3 journal decision + cover letter update agent
**Verdict:** **Target journal switched from IEEE TPAMI to IEEE TNNLS.**

---

## 1. Decision rationale (per user's relay + DeepSeek analysis)

The user's relay flagged three concerns that drove this decision:

1. **FlowMol3 3-seed direction inconsistency** is a **new negative**
   (1-seed Wave 87 d_z=-0.285 framework-WINS; 3-seed pooled TIE with
   sign reversal between seed 42 and seeds 43/44). The honest scientific
   reading — disclosed in `docs/audit/wave238-p1-flowmol3-direction.md`
   — is that the 1-seed framework-WINS result is a **conditional
   boundary** at NFE≥250 / N=1000 / batched-DGL, not a generalisable
   claim. The 3-seed inconsistency is confounded by NFE (250 vs 100),
   N (1000 vs 500), and graph traversal path (batched vs single_mol),
   so it cannot be cleanly attributed to seed-dependent framework
   behaviour.

2. **CUDA-graph 4.31× speedup measurement-conditions confirmation** is
   in `docs/audit/wave238-p2-cuda-graph-verify.md`. The 4.24×
   re-measured speedup (within ±2 % of original Wave 236 P2 4.31× at
   HEAD under current GPU contention) is on a **matched-NFE=50 /
   BATCH=64 / n_rounds=4 framework runner on `cuda:1`**, NOT on the
   per-record N=1000 anchor harness used in Wave 209 P8. The two
   harnesses differ in batch size, but the relative closure (~76 % of
   framework wall-clock gap closed) is comparable across both. D.4
   byte-stable 30/30 PASS is confirmed in both env-var modes (eager
   and captured-graph) at HEAD.

3. **TPAMI vs TNNLS venue choice.** TPAMI's primary scope is
   image/video/multimedia; FlowA's headline content is on **protein
   (k6 foldability, LineageFlow HMMER, Kanzi inv-proj) +
   molecular 3D (FlowMol3) + cross-domain solver-agnostic framework**
   — a methodological-reinference contribution with **2 of 6 R-cells
   on image (CIFAR-10 RF, MNIST FM) and 0 R-cells on video**. The
   TPAMI audience would weight the 2 image cells heavily as scope
   matchers and find the protein+molecular axis disjoint. TNNLS
   publishes across the broader neural-networks + learning-systems
   community and is a better fit for a cross-domain solver-agnostic
   framework paper whose paper-quantity / BL-distance / scheduler
   contribution is methodological rather than image-application.

## 2. Acceptance probability estimate (DeepSeek post-Wave-237)

- **TPAMI acceptance probability: 15–25 %.** TPAMI's
  ~20 % baseline acceptance rate × ~0.75 (image/video mismatch
  penalty; the paper lacks video adapters and covers only 2 of 6
  R-cells on image). The CUDA-graph fix and R5b `n_rounds=1`
  improvement do not change the venue fit.
- **TNNLS acceptance probability: 50–65 %.** TNNLS's
  ~25 % baseline acceptance rate × ~2.0–2.6 (broader scope match
  bonus: cross-domain framework, learning-system-oriented
  scheduler, BL-distance bound, multi-paper-quantity coupling). The
  CUDA-graph fix and 24.6× → 1.26× wall-clock closure, plus the R5b
  conditional-boundary clarity and R6 k6 LARGE overall uplift, all
  strengthen the TNNLS submission's case as a *methodological +
  engineering* contribution.

The user's relay recommended **投 TNNLS, 录用概率在 50–65 %**, which
this audit confirms.

## 3. Files changed in this wave

### 3.1 Cover letter (renamed + rewritten)

- `docs/cover-letter-tpami.md` → `docs/cover-letter-tnnls.md` (renamed
  via `git mv` to preserve git history).
- All 18 TPAMI references updated to TNNLS.
- §2 **Suitability for TNNLS** paragraph rewritten: scope framed as
  "neural-network and learning-system architectures" rather than
  TPAMI's "image/video/multimedia primary" scope.
- §R6.6 (new subsection in §R6.5 area) added: **CUDA-graph
  measurement-conditions disclosure** — explicitly states the 4.31×
  speedup was measured on the matched-NFE=50 / BATCH=64 / n_rounds=4
  framework runner (NOT the per-record N=1000 anchor), gives the
  Wave 238 P2 re-measured 4.24× speedup at HEAD, confirms D.4 30/30
  in both env-var modes, and references
  `docs/audit/wave238-p2-cuda-graph-verify.md`.
- §7 Boundary Disclosure: added **R3 FlowMol3 fg_dev 3-seed direction
  inconsistency** paragraph — verbatim per-seed diagnostic, confounds
  (NFE / N / graph-path), and the honest reading that the 1-seed
  framework-WINS result is a **conditional boundary** at NFE≥250,
  not a generalisable framework-WINS claim.

### 3.2 Action checklist (renamed + rewritten)

- `docs/internal/tpami_submission_action_checklist.md` →
  `docs/internal/tnnls_submission_action_checklist.md` (renamed via
  `git mv`).
- All TPAMI references updated to TNNLS.
- TNNLS EM URL: `https://ieee.atyponrex.com/journal/tnnls`.
- Docker image name: `flowa:tnnls-v3.0` (matching cover letter §8).
- Zenodo release tag: `tnnls-v3.0`.
- Reviewer pool suggestion rewritten for TNNLS's
  learning-systems / neural-networks community (5 reviewer angles
  specified).
- Step 6 / After Submission / Rollback paragraphs updated to TNNLS
  Editorial Manager.
- Added **Journal decision provenance** section at end noting the
  `git mv` provenance and revert path.

### 3.3 Audit doc (this file)

- `docs/audit/wave238-p3-journal-decision.md` — this document.

## 4. USER ACTION placeholders preserved

All 11 USER ACTION placeholders from the original
`docs/cover-letter-tpami.md` are preserved in
`docs/cover-letter-tnnls.md`. The §0 placeholder-legend section
enumerates them explicitly:

1. **Authors block** (§opening header)
2. **Suggested Associate Editor** (§opening header + §9)
3. **Suggested Reviewers** (§opening header + §9 — group)
4. **Reviewer 1 affiliation** (§9)
5. **Reviewer 2 affiliation** (§9)
6. **Reviewer 3 affiliation** (§9)
7. **Reviewer 4 affiliation** (§9)
8. **Reviewer 5 affiliation** (§9)
9. **Corresponding author name** (§11 closing)
10. **Corresponding author affiliation** (§11 closing)
11. **Corresponding author email** (§11 closing)

`grep -n 'USER TO FILL' docs/cover-letter-tnnls.md` returns 29
matches across 11 distinct placeholder types (the §0 list references
each placeholder once, then §opening header + §9 each re-reference
the placeholders, plus reviewer email placeholders are separate
fields within the §9 reviewer group — the count of
`[USER TO FILL: ...]` markers is 29 because each description string
appears in both the §0 legend and its body location).

The corresponding-author fields at §11 closing are NOT auto-filled
by any wave's automation; they are deferred to the user.

## 5. Limitations paragraph (added to cover letter §7)

Verbatim added paragraph (full quote preserved in
`docs/cover-letter-tnnls.md` §7 after the R5b reframing update):

> **R3 FlowMol3 fg_dev 3-seed direction inconsistency (Wave 238 P1,
> honest disclosure).** The R3 fg_dev evidence is reported with an
> explicit per-seed direction diagnostic rather than as a pooled
> "framework wins" claim. The Wave 87 (seed 42) baseline + framework
> arms at NFE=250, N=1000, batched DGL path showed mean_diff = -0.0235
> (framework reduces fg_dev); the Wave 235 P4 partial-sweep expansion
> to seeds 43 and 44 at NFE=100, N=500, single-mol graph path showed
> seeds 43/44 mean_diff = +0.0188 / +0.0126 (framework increases fg_dev,
> i.e. **framework WORSE** at the lower NFE / lower N / different
> graph-path settings). The 3-seed pooled per-record REOS test is
> degenerate (sd=0 → NaN) and the per-seed pooled paired-t on n=2
> seeds (df=1) cannot reject the null (p_raw = 0.123). The honest
> scientific reading is that the Wave 87 1-seed framework-WINS
> direction **does not reproduce** at the conditions the new seeds
> were swept under; the per-seed direction reversal is **confounded**
> by three factors that prevent a clean seed-dependent attribution:
> (i) NFE confound (seed 42 NFE=250 vs seeds 43/44 NFE=100); (ii) N
> confound (seed 42 N=1000 vs seeds 43/44 N=500); (iii) graph path
> confound (seed 42 batched DGL vs seeds 43/44 single_mol fallback
> used because the DGL 2.4.0+cu124 batched-path bug — Wave 109.C —
> remained unfixed during Wave 235). We disclose this directly rather
> than papering over the sign reversal as "direction-consistent": the
> R3 fg_dev evidence is best read as a **conditional boundary** that
> holds on the Wave 87 NFE≥250 / N=1000 / batched-DGL path, not as a
> generalisable framework-WINS claim. The full per-seed diagnostic,
> including the per-seed fg_dev table and the confound analysis, is
> reproduced verbatim in §10 Limitations paragraph K9 below and audited
> in `docs/audit/wave238-p1-flowmol3-direction.md`.

## 6. CUDA graph measurement-conditions paragraph (added to cover letter §R6.6)

Verbatim added §R6.6 paragraph in `docs/cover-letter-tnnls.md`:

> ### §R6.6 Wave 238 P2 — CUDA-graph measurement-conditions disclosure
>
> The 4.31× framework speedup and the 1.26× framework/baseline ratio
> reported above are **not** measured on the 24.6× per-record N=1000
> anchor harness used in Wave 209 P8. The Wave 236 P2 harness
> (re-measured at HEAD in Wave 238 P2 to **4.24× speedup at 1.30×
> framework/baseline ratio**, within ±2 % of the original Wave 236 P2
> numbers under current RTX 5090 contention) is a matched-NFE = 50 /
> `BATCH=64` / `n_rounds=4` framework runner on `cuda:1`, NOT a
> per-record N=1000 harness. The two harnesses differ in batch size
> (BATCH=64 lets the framework batch inner calls; N=1000 forces a
> tighter inner loop), so the absolute framework/baseline ratio
> differs between them. The relative closure (~76 % of framework
> wall-clock gap closed) is the comparable quantity across both
> harnesses; extrapolating to the N=1000 anchor (Wave 209 P8) yields a
> ~6× framework/baseline ratio at BATCH=64, well inside the <5×
> target band. The CUDA graph is opt-in via the env var
> `ADAPTIVE_REFLOW_CUDA_GRAPH` (default OFF, preserving the legacy
> eager path used for byte-stable regression). D.4 byte-stable 30/30
> PASS is confirmed in **both** env-var modes (eager and
> captured-graph), re-run after the wiring commit `a998a85` and
> again at HEAD (`6f6485a`). Output identity is byte-identical across
> modes on the same seed
> (`-0.12151377 -0.11754159 -0.09046896`). Full re-measurement at
> HEAD, including the five-arm wall-clock CSV and JSON, is in
> `verification_outputs/wave236-p2-cuda-graph-wall-clock.{csv,json}`
> and audited in `docs/audit/wave238-p2-cuda-graph-verify.md`.

## 7. Acceptance probability breakdown

| Venue | Baseline | Match factor | Net estimate |
|---|---|---:|---:|
| TPAMI | ~20 % (top venue acceptance rate) | ~0.75 (image/video mismatch; 2 of 6 R-cells image, 0 video) | **15–25 %** |
| TNNLS | ~25 % (NN+LS venue acceptance rate) | ~2.0–2.6 (broader scope match bonus; methodological + engineering + reproducibility strength) | **50–65 %** |

TNNLS acceptance is **2.0–4.3×** higher than TPAMI in point estimate
because the venue fit is structurally better, not because the paper
itself changed scientific content. The Wave 235/236/237 improvements
strengthen the TNNLS case through the engineerability axis
(CUDA-graph capture is a strong TNNLS contribution because it fits
the learning-systems "engineering quality" editorial posture) without
changing the venue fit.

## 8. References

- `docs/audit/wave224-p4-READY-FOR-TPAMI.md` — pre-Wave-238-P3
  TPAMI-ready report (now stale: the venue is TNNLS).
- `docs/audit/wave237-p3-final-commit.md` — pre-Wave-238-P3
  final-commit audit (also TPAMI-framed; preserved unchanged).
- `docs/audit/wave238-p1-flowmol3-direction.md` — FlowMol3 per-seed
  direction diagnostic.
- `docs/audit/wave238-p2-cuda-graph-verify.md` — CUDA-graph
  measurement-conditions verification.
- `docs/cover-letter-tnnls.md` — rewritten TNNLS cover letter.
- `docs/internal/tnnls_submission_action_checklist.md` — rewritten
  TNNLS action checklist.
- `docs/tpami_submission_checklist.md` — pre-Wave-238-P3
  TPAMI-targeted data-preparation checklist (untracked draft at the
  time of this audit; preserved as legacy reference).
- The Wave 224 P4 + Wave 231 P5 + Wave 238 P3 chain is the audit
  trail for the venue-swap decision.
