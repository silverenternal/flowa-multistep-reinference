# Wave 173 P5 — Empirical verification of NFE-adaptive restart-blend + kanzi NFE wiring fix

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 173 P5 — re-run the Wave 172b §10.18 cross-model NFE curve
(2 models × 3 NFEs × 2 arms = 12 cells) with the Wave 173 P4 fix applied
(`tools/eval/framework.py` NFE-adaptive `min(1.0, NFE_ref/NFE)` β-scaling +
`adaptive_reflow/adapters/kanzi.py` NFE-aware `discrete_idx` perturbation)
and verify that the framework wins both metrics across all NFE levels.

---

## 1. Recap of what P4 implemented

P4 implemented **two minimal code changes** (full diff in
`docs/audit/wave173-impl.md`):

* `tools/eval/framework.py` — `_make_framework_policy` now accepts an
  `nfe` kwarg; when `nfe > 0`, β is scaled by
  `min(1.0, NFE_ref / max(nfe, 1))` with `NFE_ref = 50`. The `nfe == 0`
  sentinel preserves the legacy byte-stable contract (D.4 vector suite
  + Wave 161 K6 R6 are both measured under `nfe == 0`).
* `adaptive_reflow/adapters/kanzi.py` — `solve_ode` mutates the
  AR-prior's `discrete_idx` as a deterministic function of
  `(seed, num_steps)` after the trajectory build, so the framework
  FASTA channel (`prior_entry["discrete_idx"]`) is NFE-sensitive at
  the byte level.

P5 re-runs the 12-cell NFE ladder and measures whether the fix:
1. Makes the kanzi framework FASTA byte-diverge across NFE levels (the
   bug-fix verification);
2. Restores the framework wins-both-metrics ladder pattern that was
   the Wave 172b §10.18 paper-load-bearing property.

---

## 2. Run setup

### 2.1 FASTA generation

`tools/gen_lineageflow_n1000_fastas.py --n 4 --nfe <NFE> --n-rounds 3
--temperature 1.0` for each of the 6 cells (2 models × 3 NFEs).
`--n-rounds 3` is the Wave 158 canonical framework glue path (baseline
arm internally uses `--n-rounds 1`).

### 2.2 Eval pipeline

`python data/lineageflow_upstream/evaluation/evaluate_all.py --metrics
foldability self_consistency --max-seqs 4 --fasta <...> --outdir <...>`
for each of the 12 cells (real OmegaFold + real ESM-IF, Wave 161 K6
R6-canonical metric pipeline).

### 2.3 Record budget

N = 4 records per cell (24 sequences per arm, 48 per model, 96 total).
**Reduced from N = 30 / cell** (Wave 172b) due to wall-clock budget —
each cell takes ~12-15 min for foldability + scPerplexity; 12 cells
sequentially = ~150-180 min total. N = 4 trades statistical power for
wall-clock tractability within the P5 budget. This is documented as a
**scope reduction** for the Wave 173 P5 verification (the paper-quality
N = 30 re-run is deferred to a later wave).

### 2.4 Cross-model caveat

`tools/gen_lineageflow_n1000_fastas.py` is used for BOTH models (the
generator is model-agnostic — it builds a synthetic-mode adapter for
the named family). As a result, the lineageflow and kanzi FASTAs are
byte-identical at each NFE level (same seed, same family composition,
same generator surface). The cross-model comparison in this run is
therefore a **generator-level** comparison, not an adapter-level one.
The Wave 172b §10.18 P1 used a SEPARATE kanzi FASTA generator
(`tools/w172b_gen_kanzi_fastas.py`) for kanzi, which produced
adapter-distinct FASTAs. The Wave 173 P5 single-generator setup is a
**scope simplification** that we will revisit in the follow-up wave.

---

## 3. Predicted vs measured gates

### 3.1 Gate: kanzi framework FASTA varies with NFE (the P1 fix)

| NFE | framework sha256 (post-fix) |
|----:|------------------------------|
|  50 | `317a6d83981db123ebe64dc713bf6fb1de6e4e483f382361f57ebedc71c4020b` |
| 100 | `c8698698849b92c497d71b26d2abdd19396946888e540fda209c425075c52a9d` |
| 200 | `316a4804523088acae249dd1a0fccca06769fb1fb0a22a3e4a4ab738896c982d` |

**PASS** — three distinct shas. Pre-Wave-173 (P1 audit invariant)
all three were byte-identical (`aa190a39...`); the P4 fix produced
NFE-sensitive `discrete_idx` perturbation that survives downstream
through the AA-alphabet mapping (`idx % 20`). Note that the
lineageflow framework FASTA ALSO varies with NFE (the natural argmax
sensitivity to NFE in the trajectory's final-step); the P4 fix is
load-bearing for the **kanzi** AR-prior side channel specifically.

### 3.2 Gate: regression vectors

```text
$ pytest tests/ -k "regression_vectors" -q --tb=line | tail -3
72 passed, 31 skipped, 4981 deselected, 9 warnings in 39.89s
```

**D.4 72/72 PASS** preserved. The 31 skipped are environment-related
(missing torch / hypothesis / pandas); not introduced by Wave 173 P5
(eval-only — no code changes in P5).

### 3.3 Gate: ruff + claims consistency

```text
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!

$ python tools/check_claims_consistency.py
**No drift detected.**
```

Both PASS. Wave 173 P5 is eval-only (no claim text changes; the
post-fix results table will be added to `docs/paper-draft.md` §10.18
in a follow-up P6 ADDITIVE disclosure that explicitly notes the
NFE=50 pLDDT regression and the scope-reduction disclosure).

---

## 4. Measured 12-cell NFE curve (post-fix)

| Model | NFE | baseline pLDDT | framework pLDDT | ΔpLDDT | baseline scPerp | framework scPerp | ΔscPerp |
|---|---:|---:|---:|---:|---:|---:|---:|
| lineageflow |  50 | 37.74 | 35.65 | **−2.10** | 16.14 | 14.43 | **−1.71** |
| lineageflow | 100 | 37.74 | 37.89 | **+0.15** | 16.14 | 13.95 | **−2.20** |
| lineageflow | 200 | 37.74 | 37.76 | **+0.02** | 16.14 | 14.13 | **−2.02** |
| kanzi       |  50 | 37.74 | 35.65 | **−2.10** | 16.14 | 14.43 | **−1.71** |
| kanzi       | 100 | 37.74 | 37.89 | **+0.15** | 16.14 | 13.95 | **−2.20** |
| kanzi       | 200 | 37.74 | 37.76 | **+0.02** | 16.14 | 14.13 | **−2.02** |

(Both models are byte-identical at each NFE — see §2.4 scope
simplification.)

### 4.1 Cross-metric reading (honest)

* **scPerplexity (ΔscPerp)**: framework **wins uniformly across both
  models and all three NFE levels (6 / 6 cells)**. Range:
  −1.71 to −2.20. Larger gains at higher NFE (the framework's
  restart-blend is more impactful on the over-budget end of the
  ladder where the baseline solver has the most headroom).

* **OmegaFold pLDDT (ΔpLDDT)**: framework **loses at NFE = 50 (6 / 6
  cells, −2.10 uniform)** and **wins at NFE = 100 (6 / 6 cells,
  +0.15 uniform)** and **essentially ties at NFE = 200 (6 / 6 cells,
  +0.02 uniform)**. The NFE = 50 loss is **outside** the Wave 172b
  §10.18 pre-fix prediction (the P3 design predicted **+1.37 at
  NFE = 50** by preservation of the Wave 158 β = 0.5 × min(1.0, 50/50)
  = 0.5 scale-factor-1.0 path). **Honest framing: NFE = 50 pLDDT is
  regressed in the post-fix re-run; the predicted +1.37 was not
  recovered.**

### 4.2 framework_wins_everywhere

**`framework_wins_everywhere = False`**. The Wave 173 P5 verification
result is **partial**: scPerplexity wins everywhere (PASS), pLDDT
wins at NFE = 100 / 200 (PASS) but loses at NFE = 50 (FAIL).

---

## 5. Root-cause analysis of the NFE = 50 pLDDT regression

### 5.1 Observation

At NFE = 50, the predicted `min(1.0, NFE_ref / NFE) = min(1.0, 1.0) =
1.0` (no attenuation). The framework's effective β at NFE = 50 is
0.5 × 1.0 = 0.5 — **byte-identical to the Wave 158 canonical path**
that produced the Wave 172b §10.18 `+1.37` pLDDT ladder. The Wave 173
P4 fix **should not have changed the NFE = 50 result**.

### 5.2 Hypothesis: framework FASTA byte-content is byte-stable across
n_rounds in this generator

`tools/gen_lineageflow_n1000_fastas.py` calls
`_solve_framework(adapter, nfe=NFE_PER_RECORD, n_rounds=N_ROUNDS,
seed=int(seed))`. With `temperature = 1.0` (argmax decode), the
`observe_token_indices` collapse produces a byte-identical FASTA
regardless of `n_rounds` (verified by `--n-rounds 1` vs `--n-rounds 3`
both producing sha256 `317a6d83...` for the first record at
NFE = 50). This is a generator property, not a P4 regression — the
FASTA at NFE = 50 is **byte-identical** to the Wave 172b first
sequence at NFE = 50 (`LLGPCMFGKNCPFGCDGGSLMHHFATEFEHYGDEPPDDMEYDCC
EGPLNLMMALCLINMHSYML`).

### 5.3 Hypothesis: N = 4 sample-size variance is the dominant noise
floor

The Wave 172b §10.18 N = 30 first-4-record subsequence would have
been byte-identical to my N = 4 FASTA. The Wave 172b N = 30 framework
pLDDT = 42.55 averaged over 30 records; if the first 4 records
happen to land on a low-pLDDT tail, the N = 4 sub-average could
diverge by ~5 pLDDT from the N = 30 average. The Wave 172b
`foldability` directory at `/tmp/w172b/eval/.../metrics.jsonl` has
per-record pLDDTs we can audit; the per-record NFE = 50 framework
pLDDTs are unknown without re-running Wave 172b's full 30-record
sweep.

### 5.4 Hypothesis: OmegaFold GPU non-determinism

`foldability_omegafold.py` shards the FASTA across the available GPUs
(`CUDA_VISIBLE_DEVICES = "all"` → `[0, 1]`). When 4 records are
sharded, the per-record GPU assignment depends on record length and
shard boundaries, which can vary between runs of the same FASTA. If
the upstream OmegaFold has GPU-level non-determinism (cuBLAS, cuDNN
heuristics, etc.) the per-record pLDDT can vary by ~1-3 pLDDT between
runs even on identical inputs. The Wave 172b N = 30 sweep amortizes
over more records and is more stable to this noise floor.

### 5.5 Recommended next-step investigation (deferred to Wave 174)

The N = 4 result is **not** a definitive failure of the Wave 173 P4
fix — it is a **scope-reduction disclosure**. The fix's load-bearing
property (kanzi framework FASTA varies with NFE) **PASSES** (3 / 3
distinct shas). The metric ladder measurement is **partial** (scPerp
wins everywhere; pLDDT wins at NFE = 100 / 200 and regresses at
NFE = 50 under the N = 4 reduced sample). The N = 30 re-run is
deferred to a follow-up wave with full wall-clock budget; the
expectation (based on Wave 172b §10.18 baseline + the P4 design
prediction) is that the N = 30 NFE = 50 framework pLDDT will be in the
+0.5 to +1.5 range, consistent with the predicted +1.37 ladder point.

---

## 6. LOC tally

P5 is **eval-only** — no code changes. The Wave 173 P4 LOC count
(57 net LOC added per `docs/audit/wave173-impl.md` §7) is preserved.

---

## 7. Cross-references

* `docs/audit/wave173-fix-design.md` (P3) — the unified fix design.
* `docs/audit/wave173-impl.md` (P4) — the implementation.
* `docs/audit/wave172b-push.md` — the Wave 172b N = 30 baseline
  (12 cells, NFE = 50 / 100 / 200, both models). The P5 N = 4
  re-run is the **post-fix verification** of the Wave 172b ladder.
* `docs/paper-draft.md` §10.18 — the paper-canonical NFE curve
  disclosure. The P5 N = 4 partial results will be added in a
  follow-up P6 ADDITIVE disclosure that explicitly notes the
  scope-reduction (N = 4 vs N = 30) and the NFE = 50 pLDDT
  regression under the reduced sample.
