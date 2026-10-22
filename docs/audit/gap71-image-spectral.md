# GAP-71 — Image spectral restart (R5b CIFAR): is the regression a band-structure mismatch?

**Date:** 2026-10-23
**Author:** GAP-71 agent (USER AUTHORIZED, NO PUSH)
**Scope:** `todo.json` `GAP-71-ADAPTER-IMAGE-SPECTRAL` (P1). Absorbs the
`GAP-66-R5B-EQUAL-BUDGET` and `GAP-63-R5B-N1000` before-arm.
**Status:** code landed, **no run yet** — the user's standing instruction is to
finish every code-type task in `execution_order` before spending GPU time.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched.

---

## 0. Pre-registration (written BEFORE the before-arm run and BEFORE the spectral arm exists)

### 0.1 What is actually on record, and what is not

The only CIFAR R5b number in the ledger is Wave 280's `+52.33 %` ΔFID
(`docs/audit/wave280-p-cifar-sweep-result.md`). Read at face value it is a
three-seed result. It is not:

| defect | what the audit says |
|---|---|
| **n = 1 draw, not 3** | `framework FID is byte-identical across seeds 42 and 43` (466.8138 both, `np.array_equal` True, md5 `dded5996…` × 2). The framework arm's seed never reaches the samples. |
| **unmatched NFE** | `--baseline-num-steps 2 --n-rounds 2 --match-nfe budget` → `framework_total_nfe = 3` vs `baseline_nfe = 2`. The framework arm is **50 % over budget**, not at matched compute. |
| **N = 100** | Two orders below the R5c N=1000 table, and below the N=1000 floor that `gap75` established for quoting a delta. |
| **1 of 4 schedulers, 2 of 3 seeds** | CosineAnneal only; seed 44 started and produced no `summary.json`. |

So `+52.33 %` is a **single-draw, over-budget, N=100** measurement. The
`+18…+23 %` figures from `gap46` are worse: baseline NFE=200 vs framework
NFE=50, i.e. a 4× *under*-budget. Both were opened as retraction candidates
before this gap; `GAP-71` step (1) is the re-measurement that decides.

### 0.2 The hypothesis

The R5b/R5c regression is partly a **band-structure mismatch**. The current
restart blend is per-pixel:

```
x_restart = m · x_prior + (1 − m) · ε,        ε ~ N(0, I)
```

White noise carries equal power at every radial frequency, so at any `m < 1` the
blend destroys the prior's **low-frequency** content — the part that encodes
object layout and class identity — at exactly the same rate as it re-randomises
the **high-frequency** detail, which is the part a restart is supposed to
refresh. A radial-frequency selective blend,

```
X = FFT(x);   W(f) = 1 for f ≤ cut, 0 for f > cut   (raised-cosine edge)
x_restart = IFFT(W·X_prior + (1 − W)·X_fresh)
```

keeps the prior's low bands and injects fresh noise only in the high bands.
Because the cutoff is the memory fraction itself (`cut = m`), the operator has
**no new hyperparameter**: `m = 0` is exactly the current pure-fresh draw and
`m = 1` is exactly the current pure-prior draw, so the endpoints agree with the
existing operator and only the interior differs.

### 0.3 The arms

All arms: `N = 1000`, three seeds (`42/43/44`), four schedulers, Euler solver,
`WAVE247_SEED` = seed, CIFAR-10 reference = the 10 000-image test set.

| arm | operator | NFE budget |
|---|---|---|
| **BEFORE** | current per-pixel blend | **matched**: `framework_total_nfe == baseline_nfe` enforced |
| **AFTER** | spectral band blend, `cut = m` | same, enforced |
| *reference* | Wave 280's published number | unmatched (NFE 3 vs 2), N=100, n=1 |

The BEFORE arm is run **once**, here, and is the retraction baseline that
GAP-66 and GAP-63 were opened for. It is not re-run per scheduler-seed cell
later.

### 0.4 Decision rules (fixed before the run)

1. **Retraction.** If the matched-budget N=1000 BEFORE delta is below **+5 %**,
   the `+18…+23 %` (`gap46`) and `+52.33 %` (`wave280`) figures are **retracted**
   in every non-frozen surface. Sign is not retracted — only magnitude.
2. **Spectral rule.** The AFTER arm must cut the regression by **at least half**
   relative to BEFORE, i.e. `Δ_after ≤ 0.5 · Δ_before` on the same cells and
   seeds. If it does not, band structure is **not** the missing variable and the
   boundary is stated without it.
3. **Seed invariance.** A cell whose framework samples are byte-identical across
   seeds is reported as **n = 1** regardless of how many seeds were launched.
   This is checked mechanically (md5 of the `*_samples.npz`) before any FID is
   averaged.
4. **No seed shopping.** Seeds are a diagnostic axis. If the matched-budget
   BEFORE arm is null at 3 seeds, the run stops there.
5. **Verdicts.**
   * `BAND_STRUCTURE_CONFIRMED` — rule 1 and rule 2 both hold.
   * `BAND_STRUCTURE_NOT_THE_LEVER` — rule 1 holds, rule 2 fails.
   * `RETRACTION_ONLY` — rule 1 fires, so the published magnitude dies, and rule
     2 is untestable or fails.
   * `REGRESSION_REPLICATES` — matched-budget delta is still ≥ +5 %, so the
     published direction *and* magnitude survive the two defects.

### 0.5 Limitations, declared before the numbers

* **L1 — radial cutoff is not a semantic band.** A radial FFT cutoff does not
  separate "layout" from "texture" the way a wavelet or a learned basis would.
  It is the cheapest operator that is genuinely frequency-selective and has no
  free parameter. If it fails, the honest conclusion is "this radial operator
  does not help", not "band structure is irrelevant".
* **L2 — periodic boundary.** FFT on a 32×32 image imposes circular
  periodicity; the raised-cosine edge suppresses but does not remove ringing.
  A DCT would avoid this and is the natural follow-up if the arm is close.
* **L3 — the before-arm is a re-measurement, not a replication.** The Wave 280
  artifacts are in `/tmp/wf280-cifar/` and were never committed; the numbers
  cannot be recomputed from the repo, only re-measured.
* **L4 — the framework seed defect may persist.** Wave 280's framework FID was
  seed-invariant. If that is structural (the framework arm's RNG is derived from
  the scheduler, not the seed), the BEFORE arm will again be n = 1 and rule 1
  will be evaluated on one draw. §0.4 rule 3 forces this to be reported, not
  averaged away.

---

## 1. Code landed for this gap (no run)

### 1.1 `--require-matched-nfe` (the GAP-66 constraint, CIFAR side)

`tools/run_sota_cifar_experiment.py` already had `--match-nfe {budget,sample}`,
but `budget` (the default) does **not** constrain the framework total to the
baseline's. The new guard:

* `summary.json` gains `nfe_matched: bool` and `nfe_mismatch: {baseline, framework}`
  **always** — so an unmatched run is visible without anyone remembering to look;
* `--require-matched-nfe` turns a mismatch into a non-zero exit **before** FID
  is computed, so an unmatched number cannot be produced by accident.

The default stays permissive because every historical `reproduce/*.sh` for this
driver was written against the permissive behaviour; changing the default would
silently break them. The GAP-71 sweep script passes the flag explicitly.

### 1.2 `spectral_band_fraction` (the AFTER operator)

`adaptive_reflow/adapters/rectified_flow_cifar.py`:

* `RectifiedFlowCIFARAdapter(..., spectral_band_fraction: float | None = None)`;
* `None` (default) keeps the per-pixel blend **byte-identical**;
* a value in `(0, 1)` switches `apply_restart_distribution` to the radial blend
  of §0.2, with `cut = m` and a raised-cosine transition.

### 1.3 What is NOT done here

The BEFORE arm and the AFTER arm are both GPU runs and are **not** part of this
commit. This note exists so that the decision rules are on record before either
number exists.

---

## 2. Status

| item | state |
|---|---|
| §0 pre-registration | this file, committed before any run |
| `--require-matched-nfe` | landed |
| `spectral_band_fraction` | landed, default off |
| BEFORE arm (matched NFE, N=1000, 3 seeds) | **not run** (GPU deferred by user directive) |
| AFTER arm | **not run** |
| verdict | none |
