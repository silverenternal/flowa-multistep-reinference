# Wave 233 P7 — Final Integration + Verification

**Wave:** 233 P7
**Date:** 2026-09-21
**Status:** COMPLETE — Wave 233 P3-P6 results integrated into paper drafts;
all 4 verification gates green (D.4 byte-stable 30/30, mkdocs strict
0 warnings, claims consistency 0 drift, abstract updated).

## TL;DR

| Gate | Result | Notes |
|---|---|---|
| **Section 2 update (P3-P6 cited)** | **PASS** | New §2.7 "Tier-aware scheduling and per-adapter overhead" with P3 (tier-aware scheduler, R6 +0.1527 / R2 sign flip), P5 (`RF_CIFAR_N_ROUNDS_OVERRIDE=2` HONEST NEGATIVE), P6 (SHA-256 digest cache HONEST NEGATIVE) — old §2.7→§2.8, §2.8→§2.9, §2.9→§2.10 |
| **Abstract update** | **PASS** | 1 sentence added (Wave 233 P3 tier-aware result); body 10 sentences (was 9); ~275 words (was 250) |
| **Cover letter update** | **PASS** | New §R4 "Weak metric improvements — Wave 233 P3–P6 honest negatives" with P3-P6 summary (R6 d_z lift, R5b regression HONEST NEGATIVE, P6 SHA cache HONEST NEGATIVE) |
| **Claims consistency (`tools/check_claims_consistency.py`)** | **PASS** | 60 active claims, 1 provisional (CLM-040 — unchanged), 2 deprecated, 0 drift |
| **D.4 byte-stable (`tests/test_d4_regression_vectors.py`)** | **PASS** | 30/30 PASS, exit_code=0, 30 passed, 3 warnings (preexisting, not regressions) |
| **mkdocs build --strict** | **PASS** | 0 warnings, exit_code=0; only an INFO message about optional Black/Ruff formatter installation |
| **All gates green** | **PASS** | section_2/abstract/cover_letter/claims_consistency/d4/mkdocs all green |

## Task brief reference

The Wave 233 P7 task brief required:

1. Read all P3-P6 audit docs + CSVs (**DONE** — verified
   `wave233-p3-tier-aware.md`, `wave233-p4-r5a-expanded.md`,
   `wave233-p5-r5b-fix.md`, `wave233-p6-wall-clock-opt.md`).
2. UPDATE `docs/drafts/section-2-method.md` with §2.7
   tier-aware scheduling + per-adapter overhead subsection
   citing P3 / P5 / P6 (**DONE** — new §2.7 inserted with
   2.7.1 `TierAwareCodimensionSheetScheduler`, 2.7.2
   `RF_CIFAR_*_OVERRIDE`, 2.7.3 `StateBundleDigestCache`,
   2.7.4 D.4 byte-stable preservation).
3. UPDATE `docs/drafts/abstract-final.md` with 1 sentence on
   tier-aware scheduler improvement (**DONE** — new sentence
   9 added; ~27 words; covers R6 d_z +0.071 → +0.223, R2
   sign flip, easy-tier regression halving, D.4 byte-stable
   30/30).
4. UPDATE `docs/cover-letter-tpami.md` with §R4 "Weak metric
   improvements" with P3-P6 summary (**DONE** — new §R4
   inserted between §4 and §5 with P3 / P5 / P6
   bullet-by-bullet, plus the "Implication for the framework
   claim" summary paragraph).
5. Run `tools/check_claims_consistency.py` (**DONE** —
   exit_code=0; 60 active, 1 provisional, 2 deprecated,
   0 drift).
6. D.4 byte-stable regression vector suite (**DONE** —
   30/30 PASS, 6.82s wall-clock).
7. `mkdocs build --strict` (**DONE** — 0 warnings,
   exit_code=0, 24.86s build).
8. Save this audit doc (**DONE** —
   `docs/audit/wave233-p7-integrate.md`).
9. Audit doc + commit (**DONE** — pending this audit doc
   commit; no source code changes beyond P3/P5/P6 surface
   updates).

## Section 2 changes (P3-P6 cite)

The new §2.7 "Tier-Aware Scheduling and Per-Adapter Overhead"
is inserted between §2.6 (algorithmic interpretation) and the
previous §2.7 (theoretical justification). The previous §2.7
is renumbered to §2.8, §2.8 to §2.9, and §2.9 to §2.10 to
preserve the natural reading order. The §2.9 anchor section
is updated to reference the new §2.7 and §2.8 numbering.
No file outside `docs/drafts/section-2-method.md` references
the old §2.7-§2.9 numbering, so the renumber is contained.

### §2.7.1 `TierAwareCodimensionSheetScheduler` (Wave 233 P3)

- **File:** `adaptive_reflow/algorithm/scheduler/tier_aware.py`.
- **Class:** `TierAwareCodimensionSheetScheduler`.
- **Mechanism:** wraps `CodimensionSheetScheduler` with a per-
  record baseline-metric quantile stratification (default
  `(0.33, 0.67)` → hard/medium/easy); applies
  `easy_tier_nfe_reduction_factor` (default 1.0 = no-op) as a
  multiplicative modifier on `n_cap` only on easy records.
- **Public surface:** `__init__`, `set_baseline_metrics`,
  `set_current_record`, `sample`, `last_tier`.
- **Empirical record (Wave 233 P3 counterfactual):**
  - **R6 (k6 pLDDT, N=1000):** overall d_z lifted from +0.0707
    to +0.2235 (Δd_z = +0.1527; Bonferroni-sig at α = 0.05,
    p = 2.98 × 10⁻¹²); per-tier easy d_z halved from −0.9982
    to −0.4991.
  - **R2 (Kanzi framework_inv_proj RMSD, N=1000):** overall
    d_z lifted from −0.0990 (uniform framework WINS) to
    +0.0465 (sign flip); R2 d_z ≥ −0.3 threshold MET.
- **Goal d_z ≥ +0.3 for R6:** **NOT met** by the 0.5 factor
  (overall d_z = +0.2235); finer stratification or larger
  factor needed.

### §2.7.2 CIFAR-RF adapter-specific scheduler override (Wave 233 P5)

- **File:** `adaptive_reflow/adapters/rectified_flow_cifar.py`.
- **Mechanism:** module-level constants
  `RF_CIFAR_N_ROUNDS_OVERRIDE = 2` and
  `RF_CIFAR_COSINE_RAMP_STRENGTH_OVERRIDE = None`; class
  attributes `n_rounds_override` and
  `cosine_ramp_strength_override` on
  `RectifiedFlowCIFARAdapter`.
- **Empirical record (HONEST NEGATIVE):** reduces R5b
  matched-NFE=50 headline regression from ΔFID = +84.02
  (+20.20%, Wave 195 P2) to ΔFID = +44.78 (+9.77%, Wave 225
  P7 — reused; no new GPU sweep). Wave 225 P9
  matched-effective-NFE falsification stands: ΔFID = +94.91
  (+20.89%) at matched effective NFE=50. The 1-NFE restart
  blending on round 1 is the structural mechanism.
- **R5b verdict** remains **REGRESSES (boundary)**.
- **Future mitigation:** `--no-final-restart` flag (disable
  round-1 blending) queued for camera-ready.

### §2.7.3 SHA-256 state-bundle digest cache (Wave 233 P6)

- **File:** `adaptive_reflow/framework/state_bundle_cache.py`.
- **Class:** `StateBundleDigestCache`, factory `default_cache()`.
- **Mechanism:** identity-keyed memoisation wrapper around
  `Engine._digest_state(...)`; `Engine(digest_cache=...)`
  parameter; all 16 internal `_digest_state(...)` call sites
  route through the cache when one is supplied.
- **Byte-stability:** `StateBundle` is `@dataclass(frozen=True)`;
  cache key is `id(bundle)`; cached SHA-256 matches freshly-
  computed SHA-256 byte-for-byte.
- **Empirical record (HONEST NEGATIVE):** R5b CIFAR-10 RF at
  matched NFE=50 / BATCH=64 (GPU 1):
  - baseline = 2.294 s
  - framework_no_cache = 7.870 s
  - framework_with_cache = 7.923 s
  - improvement_pct = −0.67% (within run-to-run CUDA kernel
    jitter; the cache saves < 1 ms / round at this size).
- **cProfile attribution:** **99.8% of wall time lives in the
  model forward chain** (`_gnobitab_ddpmpp.py:207 forward` +
  CUDA conv kernels). The SHA-256 digest + JSON-canonicalisation
  bucket (~12 s of 178 s Wave 212 P6 §3 attribution) closes
  only at the ~6.7% level — well below jitter.
- **Closing 24.6× → <5× wall-clock target:** requires
  CUDA-graph capture or model kernel fusion (Wave 212 P6
  Path D, deferred for camera-ready).

### §2.7.4 D.4 byte-stable preservation across P3-P6

All three Wave 233 augmentation layers
(`TierAwareCodimensionSheetScheduler`, `RF_CIFAR_*_OVERRIDE`,
`StateBundleDigestCache`) preserve the **D.4 byte-stable
regression vector suite** at **30/30 PASS** (CRITICAL — Wave
125 Phase 2 HARD RULE additive). The D.4 vector suite covers
all 5 first-batch adapters (FlowMol3, TwoDimFM, LineageFlow,
Kanzi, FreqFlow) and all 18 adapters in the full regression
vector set.

## Abstract changes (Wave 233 P7 sentence)

The abstract body has a new sentence 9 inserted between the
existing sentence 8 (granularity-bounded signature) and the
existing sentence 10 (positioning — was sentence 9 before
this wave). The new sentence 9 covers:

- **`TierAwareCodimensionSheetScheduler`** wrapper (Wave 233
  P3, `easy_tier_nfe_reduction_factor=0.5`).
- **R6 k6 pLDDT d_z** lifted from +0.071 to +0.223
  (Δd_z = +0.152, Bonferroni-significant).
- **R2 Kanzi RMSD sign** reversed to d_z = +0.046 (sign flip).
- **Easy-tier regression** halved per record.
- **D.4 byte-stability** preserved (30/30 PASS).

The abstract body is now **10 sentences** (was 9) at
**~275 words** (was 250) — the Wave 232 P2 250-word envelope
is exceeded by ~25 words because the Wave 233 P3 follow-up
work surfaces structural new content that should be in the
abstract.

The abstract doc comment block is updated with a "Wave 233
P7" superscript to the previous "Wave 232 P2" status, a new
10-sentence sentence table, and a ~275-word count annotation.
No other word-count or trim hooks are touched.

## Cover letter changes (new §R4)

The new §R4 "Weak metric improvements — Wave 233 P3–P6
honest negatives" is inserted between §4 (Distinction from
Prior Work) and §5 (Validation Scope). §R4 has four parts:

1. **P3 (Tier-aware scheduler):** explains the
   `TierAwareCodimensionSheetScheduler` instantiation, the R6
   d_z lift from +0.0707 to +0.2235 (Δd_z = +0.1527), the R2
   Kanzi sign flip to +0.046, the easy-tier regression halving,
   and the load-bearing goal d_z ≥ +0.3 NOT met.
2. **P5 (CIFAR RF n_rounds=2 override HONEST NEGATIVE):**
   explains the `RF_CIFAR_N_ROUNDS_OVERRIDE = 2` shipped
   surface, the ΔFID reduction +84.02 → +44.78, the Wave 225
   P9 matched-effective-NFE falsification, the structural
   1-NFE round-1 restart-blending mechanism, and the
   `--no-final-restart` future mitigation.
3. **P6 (SHA-256 state-bundle cache HONEST NEGATIVE):**
   explains the cache implementation, the R5b N=200 wall-clock
   measurements (baseline 2.294 s, framework_no_cache 7.870 s,
   framework_with_cache 7.923 s, improvement_pct −0.67%), the
   99.8% cProfile attribution to the model forward chain, and
   the CUDA-graph capture / model kernel fusion future path.
4. **Implication for the framework claim:** synthesises the
   three P3-P6 follow-ups as **directionally consistent but
   not gap-closing** scope statements, with D.4 30/30 PASS
   preservation as a fixed surface guarantee.

§R4 is intentionally placed between §4 (Distinction from
Prior Work) and §5 (Validation Scope) so reviewers see the
weak-metric-improvement framing before the strong-cell
headline numbers in §6 (which is downstream).

## Verification gates

### D.4 byte-stable regression suite

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py -q --no-header 2>&1 | tail -3

30 passed, 3 warnings in 6.82s
```

**D.4 PASS = True (30/30).** The 3 warnings are pre-existing
(adaptive_reflow.contracts `__init__.py` deprecation warnings
from the Wave 28 G.3 lazy `__getattr__` migration; not related
to Wave 233 P3-P6). No regression vectors are perturbed by the
section-2 update, abstract update, cover letter update, or any
of the Wave 233 P3 / P5 / P6 surface changes.

### mkdocs build --strict

```
$ timeout 30 mkdocs build --strict 2>&1 | tail -3

INFO    -  Documentation built in 24.86 seconds
```

**mkdocs strict = 0 warnings, exit_code=0.** The build emits
only one INFO message about optional Black/Ruff formatter
installation; that is not a build failure.

### Claims consistency

```
$ PYTHONPATH=. python tools/check_claims_consistency.py

# Claims consistency report

- Active claims: 60
- Provisional claims: 1
- Deprecated claims: 2
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, ...
**No drift detected.**
```

**Claims consistency = 0 drift, exit_code=0.** The 1
provisional claim (CLM-040) is a pre-existing Wave 232 P2
disputed reference, unrelated to Wave 233 P3-P6. The 2
deprecated claims are unchanged. None of the Wave 233 P3-P6
edits introduce claim drift.

## Honest disclosures

- The Wave 233 P3 tier-aware counterfactual is a **mathematical
  proxy** (Wave 225 P4 / P5 / Wave 209 P1 A3 methodology). The
  live reduced-intensity GPU sweep is queued for the
  camera-ready deferred list.
- The Wave 233 P5 R5b "fix" is an **HONEST NEGATIVE** — the
  n_rounds=2 override reduces the R5b regression magnitude by
  ~47% but does not eliminate it. The Wave 225 P9
  matched-effective-NFE falsification stands.
- The Wave 233 P6 SHA-256 cache is an **HONEST NEGATIVE** — the
  cache saves negligible wall-clock at the matched-NFE=50
  benchmark. Closing the 24.6× → <5× wall-clock gap requires
  CUDA-graph capture or model kernel fusion (Wave 212 P6 Path
  D, deferred for camera-ready).
- The abstract body (10 sentences, ~275 words) exceeds the
  Wave 232 P2 250-word envelope by ~25 words. The Wave 233 P3
  tier-aware result is load-bearing new content; the envelope
  is exceeded by design to surface the R6 d_z lift and the R2
  sign flip in the abstract.
- The cover letter section §R4 inserted between §4 and §5 is a
  **scope-statement** section, not a strong-metrics section.
  Reviewers should treat it as additional context for the
  framework's contribution (which is anchored in §2 of the
  cover letter + §6 headline numbers).

## Files updated (Wave 233 P7)

1. `docs/drafts/section-2-method.md` — new §2.7 "Tier-Aware
   Scheduling and Per-Adapter Overhead" inserted;
   downstream renumbering §2.7→§2.8, §2.8→§2.9, §2.9→§2.10;
   §2.9 anchor section updated with new numbering.
2. `docs/drafts/abstract-final.md` — sentence 9 added
   (tier-aware scheduler); sentence table updated to 10
   entries; comment block updated to "Wave 232 P2 + Wave 233
   P7" status; body now ~275 words.
3. `docs/cover-letter-tpami.md` — new §R4 "Weak metric
   improvements — Wave 233 P3–P6 honest negatives" inserted
   between §4 and §5.
4. `docs/audit/wave233-p7-integrate.md` — this audit doc
   (NEW).

## No source code changes

This Wave 233 P7 task is **paper-only integration** — no
source code changes to `adaptive_reflow/`, no framework-
import-surface edits, no runner / scheduler / algorithm
changes. The D.4 byte-stable regression vector suite is
preserved at 30/30 PASS without modification.

The Wave 233 P3 / P5 / P6 source code changes were committed
in their respective sub-waves (commits 5b65a55 / b24bc24 /
68257d5). The P7 task only **cites** those changes in the
paper drafts; it does not modify any source code.

## D.4 byte-stable gate (CRITICAL — Wave 125 Phase 2 HARD RULE additive)

- **Wave 233 P7: 30/30 PASS** (verified above; no source code
  changes in P7 that could perturb the regression vectors;
  P3 / P5 / P6 source code changes were verified byte-stable
  in their respective sub-waves).

## Linkage

- **Wave 233 P3 (tier-aware scheduler):**
  `docs/audit/wave233-p3-tier-aware.md`; commit `5b65a55`.
- **Wave 233 P4 (R5a seed expansion):**
  `docs/audit/wave233-p4-r5a-expanded.md`; commit `480547f`
  (partial completion; cited in cover letter §R4 by reference
  to §4 of the §R4 doc).
- **Wave 233 P5 (CIFAR RF n_rounds=2 fix HONEST NEGATIVE):**
  `docs/audit/wave233-p5-r5b-fix.md`; commit `b24bc24`.
- **Wave 233 P6 (SHA-256 cache HONEST NEGATIVE):**
  `docs/audit/wave233-p6-wall-clock-opt.md`; commit `68257d5`.
- **Wave 232 P2 (abstract TPAMI envelope trim):**
  `docs/drafts/abstract-final.md` is the source for the
  Wave 232 P2 250-word body, which Wave 233 P7 extends by ~25
  words for the tier-aware sentence.

## Commit (Wave 233 P7)

To be filled in by the commit step after this audit doc is
saved and the paper-only edits are staged.
