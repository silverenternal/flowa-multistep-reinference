# The `reproduce/` one-click verifiers: one broken script, two green lights on the wrong number

**Date:** 2026-10-29 · **Scope:** `reproduce/0[1-8]_*.sh`,
`reproduce/verify_all_headlines.sh` · **Cost:** CPU only, ~0.2 s total ·
**Frozen surfaces touched:** none (`tnnls_submission/`, `docs/CLAIMS.md`,
`docs/drafts/` untouched)

## 1. Why this audit exists

`tnnls_submission/data_availability.md` tells reviewers to reproduce the
headline numbers by running `reproduce/0[1-7]_*.sh` and then
`reproduce/verify_all_headlines.sh`, expecting `OK: All 7/7`. Nothing in the
test suite ever executed those scripts, so a broken one could sit there
indefinitely. Running the master on 2026-10-29:

```
Summary: 8/9 R-level cells verified
FAILED cells:
  - 05_R5_2D_EightGaussians.sh
```

Two independent defects, plus two "green check, wrong quantity" defects.

## 2. `05_R5_2D_EightGaussians.sh` — failing since Wave 308

```
R5 FAIL: baseline=2.31 (expected 0.6606)
```

The script reads `analysis.per_cell_breakdown` in
`verification_outputs/g1_deep_dive_q3_2026.json` and looked up the key
`twodim_fm_2d_eight_gaussians`, which is the **2D FM ablation** row
(2.31 → 0.76, −67.10%). The expected values it asserts (0.6606 → 0.5919,
−10.40%) belong to a different row in the same file,
`rectified_flow_2d_sota_eight_gaussians` — the Liu 2022 rectified-flow SOTA
result that `docs/CLAIMS.md` CLM-039 calls the load-bearing number.

The Wave 308 "cosmetic fix" changed the expected numbers but not the row key.
Effect: the script failed for every wave since, and the −10.40% headline was
never actually verified by its own one-click script. Fixed by correcting the
key. No number changed.

## 3. `04_R4_2D_TwoMoons.sh` — passing, but not on the paper's number

The script asserted only `twodim_fm_2d_ablation` (2.85 → 0.62, −78.25%). That
is a real experiment, but `paper-A-final.md` §7.2 R5a explicitly separates it
from the cell: the ablation is "a distinct measurement", while the CLM-039
headline is `rectified_flow_2d_sota_two_moons` (0.5029 → 0.4663, −7.28%). The
canonical −7.28% had no verifier at all.

Fixed by asserting both rows, labelled. Both were already correct in the
artifact; nothing was re-derived.

## 4. `03_R3_FlowMol3.sh` — a green light for a retired reading

The script asserted the N=200 REOS Glaxo+Dundee proxy
(`wave216-p1-r3-per-record.json`, `d_z = −0.285`, `p = 8.03e-05`) and printed

```
OK R3 reproduced: framework per-record d_z = -0.285 (Bonf-sig < 1e-4, framework_WINS)
```

The manuscript retired that proxy. `paper-A-final.md` §7.2 R3 is the three-seed
`fg_dev` test — `mean_diff = −0.0377`, `t = −0.695`, `df = 2`, `p = 0.559`,
`d_z = −0.401` — and its status is **PARTIAL**, not a win: "The N=200 per-record
REOS Glaxo+Dundee flag-count proxy … is direction-consistent but does not track
`fg_dev` …, so it is reported as a retired proxy rather than a headline."

So the one-click verifier was certifying `framework_WINS, Bonf-sig < 1e-4` on a
number the paper explicitly does not claim, and not testing the number it does
claim. This is the worst of the four defects: a reviewer following the
reproduction instructions would have come away with a stronger impression than
the manuscript supports.

Fixed: the canonical three-seed test is asserted first (including
`bonf_sig == False`, so the script fails if the artifact ever starts claiming
significance), and the retired proxy is kept as a labelled audit-trail check.

## 5. `07_R6_MNIST_TierAware.sh` — wrong model label, superseded headline

Header said "MNIST FM (k6 tier-aware)". R6 is LineageFlow k6 foldability; MNIST
is R5c. The script also asserted only the Wave 235 P3 counterfactual grid cell
(`d_z = +0.6467`, uplift from `+0.2235`) and called it the headline.

The 2026-10-27 refresh replaced the R6 headline with the live tier-aware run.
`paper-A-final.md` §7.2 R6 now leads with scPerplexity `d_z = −0.8393`
(n = 3000), pooled pLDDT `d_z = +0.1466` (n = 3000, explicitly below the
+0.2235 bar) and hard-tier pLDDT `d_z = +1.1211` (n = 990), with the
counterfactual "retained as a design validation, not as the headline".

Fixed: the live numbers are asserted first, from
`verification_outputs/gap31-r6-live-uplift/gap31_summary.json` and
`verification_outputs/gap30-r6-fresh-tier/as-designed/sweep_summary.json`
(`pooled_per_tier.fresh.hard` — this is where `+1.1211` lives; it was previously
only in a markdown table), the "does not reach +0.2235" direction is asserted
too, and the counterfactual block is relabelled as the design validation.

## 6. `06_R5b_CIFAR_n_rounds1.sh` — half the story

The script verified the n_rounds=1 win (4/4 schedulers, −2.53% to −0.12%) and
stopped. R5b's paper label is **CONDITIONAL**, and the label rests entirely on
the reversal at n_rounds ≥ 2, which was not checked anywhere. The same JSON
holds it: `no_final_restart_n10.results.cosineanneal.delta_pct = +30.19%`.

Added as an assertion, so the script now reproduces both the win and the reason
it does not generalise.

## 7. `verify_all_headlines.sh` — counting the wrong scripts

The loop was `for script in reproduce/[0-9]*.sh`, which also matches
`09_verify_all_cell_recipes.sh` — a *different* master covering the 11 paper
cells. That is why the summary read `8/9`, and the progress prefix was
hardcoded `[%d/7]`. Fixed to an explicit `reproduce/0[1-8]_*.sh` array with a
computed denominator; the summary now reads `8/8` (7 R-level cells; R6 has a
second, recipe-level verifier in `08`).

## 8. What is now enforced

`tests/test_reproduce_scripts.py` (4 tests, 1.3 s) runs both masters and fails
if either goes non-zero, if `09` leaks back into the master's count, or if a
`reproduce/0[1-8]_*.sh` script exists that the master does not run. This is the
regression guard that was missing: `05` was broken across roughly a hundred
waves because nothing executed it.

## 9. Numbers that changed

None. Every corrected assertion was already satisfied by its artifact; the
defects were in *which* artifact row was read, or in the label attached to the
result. The paper's numbers were correct before and after.

## 10. Left for authorisation (frozen submission text)

`tnnls_submission/data_availability.md` §"Reproduction instructions":

- `bash reproduce/03_R3_FlowMol3.sh   # R3: FlowMol3 fg_dev N=200` — the script
  now verifies the N=1000 three-seed test; the comment describes the retired
  proxy.
- `bash reproduce/07_R6_MNIST_TierAware.sh  # R6: MNIST FM tier-aware` — R6 is
  LineageFlow k6, not MNIST.
- Step 3 lists seven scripts (01–07); `08_verify_R6_recipe.sh` and
  `09_verify_all_cell_recipes.sh` exist and are not listed.
- Step 4 says `# Expected: "OK: All 7/7 R-level headlines verified"`; the
  master now prints `8/8`.

These are one-line edits to a frozen file and were not made.
