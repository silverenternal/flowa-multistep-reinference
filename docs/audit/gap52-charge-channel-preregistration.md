# GAP-52 — Pre-registration: channel-faithful restart blend for FlowMol3 R3

**Date:** 2026-10-19
**Status:** FROZEN BEFORE THE RUN. No arm, seed, threshold, or metric may change
after the dev screen starts.
**Parent:** `docs/audit/gap43-blend-positive-run.md` (as-wired verdict:
`INCONCLUSIVE` on `fg_dev`, `d_z = +2.97` on `pb_validity`).
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 1. Motivation (observed, not inferred)

GAP-43 tested the **as-wired** all-channel restart blend at 50 seeds. On the
primary `fg_dev` endpoint it was `INCONCLUSIVE` (mean Δ = −0.01921, p = 0.1301),
and the tuned-baseline gate failed (3/10). On `pb_validity` it won 50/50 seeds
(`d_z = +2.97`).

Reading the blend code found two representation-level choices that were never
validated against the upstream model:

1. **Charge is a categorical channel upstream, but a continuous one in the
   blend.** `_solve_ode_upstream` converts `c` to a 6-class one-hot via
   `clip(round(c) + 2, 0, 5)`. `_channel_aware_blend` instead computes
   `m·c_prior + (1−m)·c_fresh` and only then is the result rounded. For two
   independent `N(0,1)` draws the blended variance is `m² + (1−m)²`:
   at `m = 0.5` the std falls from 1.000 to 0.707, and the probability of the
   neutral class rises from **38.3 % to 52.0 %**. The as-wired arm therefore
   injects a systematic neutral-charge bias that the baseline does not have.
2. **One scalar memory fraction for all channels.** `FinalRestartPolicy`
   already supports per-channel `beta_by_channel`, but the canonical driver
   passes a single scalar, so coordinate, charge, and pair share `m = 0.5`.
   There is no mechanistic reason a continuous coordinate prior and a
   categorical bond prior should have the same restart memory.

## 2. Hypotheses

- **H1 (charge fix).** Making the charge channel categorical
  (keep-or-resample, matching the upstream representation) removes the
  neutral-charge bias and improves `fg_dev` relative to the as-wired blend.
- **H2 (per-channel m).** Giving the coordinate channel lower memory
  (more exploration) and the discrete channels higher memory (more
  conservation) improves `fg_dev` relative to a flat `m = 0.5`.
- **H3 (interaction).** The two changes are not additive; the charge fix
  matters more once the discrete memory is high.

Both are *mechanism* hypotheses. Neither is a metric-specific reweighting;
the metrics are computed exactly as in GAP-43.

## 3. Arms (2 × 2 factorial)

| arm | charge mode | memory fractions `(m_x, m_c, m_pair)` |
|---|---|---|
| **C0** (reference = GAP-43 as-wired) | continuous | (0.5, 0.5, 0.5) |
| **C1** (H1 only) | categorical | (0.5, 0.5, 0.5) |
| **C2** (H1 + H2) | categorical | (0.25, 0.75, 0.75) |
| **C3** (H2 only) | continuous | (0.25, 0.75, 0.75) |

`m_pair` also controls the atom-type channel `a`, which is folded into
`raw_pair` in the current adapter (documented limitation, unchanged).

## 4. Dev screen

- **Seeds:** `1000, 1010, …, 1090` (10 seeds). Disjoint from every seed used
  in GAP-43 (`55…545`) and from the confirmatory block.
- **Protocol:** `--n-total 200`, `--nfe 250`, `--nfe-batch 100`,
  `--shared-prior --real-restart-blend`, `cuda:0`.
- **Why N=200:** screening only. GAP-39 showed the *level* of `fg_dev` is
  N-dependent; the paired Δ is the quantity carried forward, and the
  confirmatory run uses N=1000.
- **Selection rule (fixed now):**
  1. Compute the paired mean Δ (`fg_dev`, framework − baseline) for each arm.
  2. Drop any arm whose mean Δ is not below C0's mean Δ.
  3. Among the survivors, pick the lowest mean Δ.
  4. If no arm beats C0, **stop** and record a null; do not run the
     confirmatory block.
- **No early stopping on individual seeds.** All 10 dev seeds are run for all
  four arms before the rule is applied.

## 5. Confirmatory block

- **Winner** from §4 plus **C0** (the as-wired reference).
- **Seeds:** `2000, 2010, …, 2490` (50 seeds), fresh.
- **Protocol:** `--n-total 1000`, `--nfe 250`, `--nfe-batch 100`,
  `--shared-prior --real-restart-blend`, `cuda:0`.
- **Primary endpoint:** `fg_dev`, paired Δ = framework − baseline.
- **Secondary (reported, not gated):** `pb_validity_pct`, `ood_ring_rate`,
  `validity_pct`.

## 6. Decision rule (frozen)

Let `Δ` be the 50-seed paired difference of the winner vs the **baseline arm**,
and `Δ_C0` the same for the reference arm.

**`POSITIVE`** iff all of:

1. `mean(Δ) < 0`;
2. one-sample t-test `p < 0.05` (single confirmatory arm, no multiplicity
   correction);
3. `|d_z| ≥ 0.5`;
4. the **tuned-baseline gate** passes: on seeds `2000…2090` (10 seeds),
   `mean(Δ_tuned) < 0`, where `Δ_tuned = fg_dev(framework, NFE=250) −
   min(fg_dev(baseline, NFE=250), fg_dev(baseline, NFE=1000))`;
5. `mean(Δ) < mean(Δ_C0)` — the fix must also beat the as-wired arm, not just
   the baseline.

**`BOUNDED NEGATIVE`** iff the 95 % bootstrap CI of `d_z` has upper bound
`< −0.5`.

Otherwise **`INCONCLUSIVE`**.

The secondary endpoints cannot change the verdict. `pb_validity` is reported
as an exploratory consistency check; if the winner's `pb_validity` advantage
disappears, that is a mechanism warning and must be stated even if `fg_dev`
is `POSITIVE`.

## 7. Implementation (additive, default off)

- `FlowMol3V2Adapter(..., charge_blend_mode="continuous"|"categorical")`;
  default `"continuous"` keeps every existing digest byte-identical.
- `_channel_aware_blend(..., charge_mode=...)`; categorical mode uses the
  same keep-or-resample rule as `a`/`e`, with the same per-channel memory.
- `scripts/wave338_p5_r3_n1000_paired.py` gains
  `--charge-blend-mode` and `--restart-memory-fraction-{coordinate,charge,pair}`.
  Defaults reproduce the current CLI exactly.
- D.4 regression vectors must remain 30/30 (72/72 with the adapter suite).

## 8. What would falsify the programme

If neither C1 nor C2 beats C0 on the dev block, the charge-channel defect is
not load-bearing for `fg_dev`, and the as-wired `INCONCLUSIVE` stands. That is
a publishable negative and will be recorded as such; no further arm may be
added to this pre-registration.

## 9. Cost

| Stage | Runs | Estimate |
|---|---|---|
| Dev screen | 4 arms × 10 seeds × N=200 (both arms each) | ~1.1 h |
| Confirm | 2 arms × 50 seeds × N=1000 (both arms each) | ~13 h |
| Tuned gate | 10 seeds × baseline NFE=1000 | ~2.7 h |

The confirm stage runs the winner and C0; both include a baseline arm, so the
baseline is measured twice per seed. This is deliberate: each arm's evidence
file is self-contained.
