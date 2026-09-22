# Wave 170 P4 — Fair-baseline FASTA generation (10 cells, NFE=10/50/100/200/500)

**Status:** COMPLETE. 10/10 cells generated. N=100 records per cell (4 Pfam
families × 25 records/family). `n_rounds=1` and `n_rounds=3` arms exercised
across the full NFE sweep; SHA256 collected for every FASTA.

**Auditor:** Wave 170 P4 (paper-quality follow-up to Wave 170 P1 / P2 / P3
and Wave 169 P4).

**Goal:** Generate the fair-baseline comparison FASTAs mandated by the
Wave 170 P1 audit + Wave 170 P2 fix design:

| Arm | Mechanism (per Wave 170 P1) | `--n-rounds` |
|-----|------------------------------|--------------|
| `baseline_n1` | `solve_ode` × 1 round, no restart-blend (pure framework target `P_target(NFE)`) | 1 |
| `framework` | `solve_ode` × 3 rounds + `apply_restart_distribution` per round (Wave 158 canonical multi-round glue) | 3 |

**Cell matrix:** 5 NFE levels × 2 arms = 10 cells.

---

## 1. CRITICAL correction to the P4 task description

The P4 task description (`STEP 2`..`STEP 11`) references CLI flags
(`--output-dir`, `--n-records-per-family`) that **do not exist** in the
actual CLI. The `--n-rounds` flag is the only Wave 170 P3 addition; the
remaining CLI surface is unchanged from Wave 168 P1. The actual flags
used here are `--outdir`, `--n`, `--nfe`, `--n-rounds`.

### 1a. Actual CLI surface used in P4

| Flag | Value | Meaning |
|------|-------|---------|
| `--outdir` | `/tmp/w170/fastas/nfe_{10,50,100,200,500}_{baseline_n1,framework}/` | Single output dir for both `baseline.fasta` + `framework.fasta` + `manifest.json` |
| `--n` | 100 | Total records = 4 families × 25 records/family |
| `--nfe` | 10 / 50 / 100 / 200 / 500 | Per-record NFE budget for the framework arm |
| `--n-rounds` | 1 (baseline_n1) / 3 (framework) | Number of restart-blend rounds (Wave 170 P3 CLI flag) |

Each invocation writes **both** `baseline.fasta` (bare RNG, identical
across `--n-rounds`) and `framework.fasta` (drives the framework glue at
the configured `--n-rounds`), plus `manifest.json` recording the
`n_rounds` value. The fair-baseline comparison therefore uses:

* `baseline_n1/framework.fasta` — solve_ode at `n_rounds=1` (no
  restart-blend) — this is the Wave 170 P1 §1 fair baseline reference.
* `framework/framework.fasta` — solve_ode at `n_rounds=3` with the
  Wave 45 multi-round restart-blend glue.

### 1b. Why two directories per NFE level (rather than one)

The gen script's manifest field `n_rounds` is a single integer, so a
single directory cannot hold both arms with their respective `n_rounds`
in the manifest. Splitting into two directories preserves the
`n_rounds` provenance for every cell without resorting to a sidecar
metadata file. The bare-RNG `baseline.fasta` is identical in both
directories at the same NFE level (bare RNG is unchanged by
`--n-rounds`), so the duplication is byte-free.

---

## 2. Cell matrix and verification

### 2.1 Per-cell record count + manifest `n_rounds`

```
NFE=10  baseline_n1: 100 records, n_rounds=1
NFE=10  framework:   100 records, n_rounds=3
NFE=50  baseline_n1: 100 records, n_rounds=1
NFE=50  framework:   100 records, n_rounds=3
NFE=100 baseline_n1: 100 records, n_rounds=1
NFE=100 framework:   100 records, n_rounds=3
NFE=200 baseline_n1: 100 records, n_rounds=1
NFE=200 framework:   100 records, n_rounds=3
NFE=500 baseline_n1: 100 records, n_rounds=1
NFE=500 framework:   100 records, n_rounds=3
```

10/10 cells pass. 100/100 records per cell (4 families × 25).

### 2.2 SHA256 inventory

#### baseline.fasta (bare RNG, identical across `--n-rounds`)

| NFE | baseline_n1/baseline.fasta | framework/baseline.fasta | byte-equal? |
|-----|-----------------------------|---------------------------|--------------|
| 10  | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | YES |
| 50  | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | YES |
| 100 | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | YES |
| 200 | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | YES |
| 500 | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | `8fa313004239d7bdbaaa3fdfe80dfa67c2d27ac0e54810051bad54b9cba2b137` | YES |

The bare-RNG baseline is byte-identical across NFE × `--n-rounds` —
expected: bare RNG is purely a function of `seed + i + family_id + length`
and is independent of the framework-side `--nfe` / `--n-rounds` flags.

#### framework.fasta (framework arm, varies with `--n-rounds`)

| NFE | baseline_n1/framework.fasta | framework/framework.fasta | byte-equal? |
|-----|--------------------------------|-----------------------------|--------------|
| 10  | `74d96a76a58b45a8a6b3c270e8548539c91b7db13e135e48168d8a6468cb3d45` | `74d96a76a58b45a8a6b3c270e8548539c91b7db13e135e48168d8a6468cb3d45` | YES |
| 50  | `4147a6b4a09178066a1ea47c2a1c743f57c2c3ea9c35d88a1807e820592b0c43` | `4147a6b4a09178066a1ea47c2a1c743f57c2c3ea9c35d88a1807e820592b0c43` | YES |
| 100 | `9a75eee04969575e510ed0fa27740c9dea4a9f68111b320d0c11c195bdbd5f1f` | `9a75eee04969575e510ed0fa27740c9dea4a9f68111b320d0c11c195bdbd5f1f` | YES |
| 200 | `2075710ce923654eb20ec6e3eb1017bc681e7faf514c5a03d2b73fa397c3c804` | `2075710ce923654eb20ec6e3eb1017bc681e7faf514c5a03d2b73fa397c3c804` | YES |
| 500 | `0c050127203bf74266a65833132ac0e0c1d5860318f78a9af9a4f07d1f8de3c4` | `0c050127203bf74266a65833132ac0e0c1d5860318f78a9af9a4f07d1f8de3c4` | YES |

`n_rounds=1` and `n_rounds=3` produce **byte-identical framework.fastas**
at every NFE level (10, 50, 100, 200, 500).

This is the **expected** Wave 169 P4 finding:

> "byte-identical fastas at every measured NFE level" — Wave 169 P4 §1

> "synthetic mode collapses to one dominant token per position
> regardless of `memory_fraction`" — Wave 170 P1 §3 conclusion

The synthetic velocity field's attractor collapses to a single
dominant token per position regardless of how many `apply_restart_
distribution` rounds run, so the per-position argmax (which is what
`framework.fasta` writes) is byte-stable across `n_rounds`. This is a
**test-surface limitation**, not a code defect:

* The framework glue code is exercised correctly (`_solve_framework`
  splits NFE across rounds, calls `apply_restart_distribution` between
  rounds).
* The synthetic-mode velocity field returns identical per-position
  logits regardless of the restart-blend input, so the argmax
  observable is unchanged.

**Implication for the Wave 170 paper-quality comparison:** the
`baseline_n1` vs `framework` comparison is **byte-identical** at every
NFE level under synthetic mode, so any `ΔpLDDT` or `ΔscPerplexity`
measurement is deterministically 0.00. This matches the Wave 169 P4
finding and the Wave 170 P1 audit's prediction. The fair-comparison
artifacts are correctly generated; the empirical disambiguation of the
restart-blend value-add **requires a real torch-mode LineageFlow
checkpoint** (out of scope for this CPU-only wave).

### 2.3 Cross-NFE framework.fasta diversity (sanity check)

Despite being byte-stable across `--n-rounds`, the framework fastas DO
vary across NFE — confirming the `--nfe` flag is wired correctly
through `NFE_PER_RECORD` (Wave 168 P1 fix):

```
NFE=10  framework.fasta: 74d96a76a58b45a8a6b3c270e8548539c91b7db13e135e48168d8a6468cb3d45
NFE=50  framework.fasta: 4147a6b4a09178066a1ea47c2a1c743f57c2c3ea9c35d88a1807e820592b0c43
NFE=100 framework.fasta: 9a75eee04969575e510ed0fa27740c9dea4a9f68111b320d0c11c195bdbd5f1f
NFE=200 framework.fasta: 2075710ce923654eb20ec6e3eb1017bc681e7faf514c5a03d2b73fa397c3c804
NFE=500 framework.fasta: 0c050127203bf74266a65833132ac0e0c1d5860318f78a9af9a4f07d1f8de3c4
```

5/5 SHA256 are distinct — `--nfe` propagates correctly.

---

## 3. Reproduction

```bash
mkdir -p /tmp/w170/fastas/

# baseline_n1 cells (--n-rounds 1)
for nfe in 10 50 100 200 500; do
  python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w170/fastas/nfe_${nfe}_baseline_n1/ \
    --n 100 --nfe ${nfe} --n-rounds 1
done

# framework cells (--n-rounds 3, Wave 158 canonical)
for nfe in 10 50 100 200 500; do
  python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w170/fastas/nfe_${nfe}_framework/ \
    --n 100 --nfe ${nfe} --n-rounds 3
done
```

Total wall-clock: ~2 min on cold clone (CPU-only, synthetic mode).

---

## 4. Connection to Wave 168 / 169 / 170 prior work

* **Wave 168 P1** added `--nfe` CLI flag — wired into `NFE_PER_RECORD`
  via global reassignment. Validated by cross-NFE framework.fasta
  diversity (§2.3 above).
* **Wave 169 P4** first validated `n_rounds=1` vs `n_rounds=3`
  byte-identity at NFE=50/100/200/500 — the validation experiment
  reverted the `--n-rounds` CLI flag at the end (Wave 169 P3
  precedent). NFE=10 was not measured in Wave 169 P4.
* **Wave 170 P1** documented the framework mechanism ↔ JMAA theory
  mismatch: bare-RNG baseline ≠ ODE target distribution. Proposed
  `n_rounds=1` as the fair baseline reference.
* **Wave 170 P2** designed the `--baseline-mode {rng,ode}` flag for
  future expansion (not used here; current `--n-rounds 1` is the
  per-call knob that already implements the "ODE baseline" semantics).
* **Wave 170 P3** re-added the `--n-rounds` CLI flag (default 3, the
  Wave 158 canonical Wave 45 multi-round path). This wave (P4) is
  the first to consume it across a 5-cell NFE sweep.

**P5 (this audit + commit) closes the Wave 170 P4 task:** fair-baseline
FASTAs generated for 5 NFE levels × 2 arms = 10 cells, all SHA256
collected, byte-identity-across-`n_rounds` confirmed and documented.

---

## 5. Open follow-ups (for Wave 171+)

1. **Torch-mode LineageFlow adapter** — required to empirically
   disambiguate the restart-blend value-add. Synthetic mode collapses
   to one dominant token per position, so the per-position argmax is
   `--n-rounds`-invariant. A real torch-mode adapter would expose the
   restart-blend effect through `apply_restart_distribution`'s actual
   state-space semantics.
2. **Sub-modal-sensitive decoding** — replace argmax with
   temperature-sampling or top-k at high NFE so the per-position
   categorical entropy is preserved end-to-end (the Wave 169 P1
   recommendation).
3. **OmegaFold pLDDT evaluation** — even with byte-identical
   framework.fastas under synthetic mode, the bare-RNG baseline.fasta
   evaluation IS informative for the Wave 167 finding
   (`pLDDT_improvement_Ω`); the framework arm simply cannot
   disambiguate in synthetic mode and should be marked as
   "framework-arm pLDDT untestable under synthetic test surface" in
   the paper.
