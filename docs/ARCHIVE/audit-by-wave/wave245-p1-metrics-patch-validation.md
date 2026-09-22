# Wave 245 P1 — metrics.py Patch Numerical-Equivalence Validation

**Status:** PARTIAL / PENDING — Wave 242 seed 44 retry v3 is still running at audit-doc save time. Seed 44 framework metrics are NOT yet available; framework-arm cross-seed equivalence check cannot be finalized.

**Per task rule:** "DO NOT interrupt Wave 242 seed 44 retry v2 if still running." The current seed 44 retry (PID 3524941 wrapper + PID 3524943 wave87 sweep) was launched 2026-09-22 00:15:16 CST and remains in flight at audit time (2026-09-22 00:16:32 CST, ~75 s elapsed). No interruption, no termination, no kill — observed only.

## Background

**Patch in question:** Wave 244 P5 3-place defensive fallback in
`data/FlowMol3/repo/flowmol/analysis/metrics.py` (local-only, vendored code;
`.gitignored`; not committed to git as code). Patch scope:

1. **Line 111 (`analyze()`)** — `molecule.num_atoms` ⇒ 3-tier fallback
   (`num_atoms` → `GetNumAtoms()` → `GetAtoms()` → 0; Wave 245 P1 extension to
   original `getattr(num_atoms, len(molecule.GetAtoms()))` from Wave 244 P5)
2. **Lines 349–358 (`check_stability()`)** — try/except for
   `atom_types/valencies/charges` falling back to RDKit walks
3. **Line 366** — `fake_atoms = getattr(molecule, 'fake_atoms', False)`
4. **Lines 390–401 (`check_stability_midi()`)** — same try/except for
   `atom_types/valencies/charges`

**Why this validation matters:** G3 ("zero new LOC in upstream metric code")
is technically violated by the 11 new LOC in vendored upstream code, but the
patch is documented as *defensive-only*. Before accepting this trade-off, we
must show that the patch does not change numerical outputs for the cases where
the original `try`-branch succeeds (i.e., the original code path is preserved
when the molecule IS a full `SampledMolecule`).

## Seed 43 framework-arm metrics (pre-patch)

Source: `verification_outputs/wave242-p1-flowmol3-seed43-summary.json`
(generated 2026-09-21 22:03 CST, BEFORE the Wave 244 P5 patch and BEFORE the
Wave 245 P1 line-111 extension). Seed 43 was the FIRST sweep run; metrics were
extracted from full `SampledMolecule` objects — the **original code path was
exercised**, not the fallback.

| metric             | seed 43 framework | paper target | seed 43 baseline (for ref) |
|--------------------|------------------:|-------------:|---------------------------:|
| fg_dev             | 0.7361114699253837 | 0.27         | 0.7335809749838106         |
| validity_pct       | 1.0              | 0.999        | 1.0                        |
| pb_validity_pct    | 0.565            | 0.919        | 0.46                       |
| ood_ring_rate      | 0.01             | 0.10         | 0.005                      |
| wallclock_sampling | 1793.223 s       | n/a          | 1797.603 s                 |
| wallclock_metrics  | 7.229 s          | n/a          | 7.468 s                    |

Seed 43 framework `n_sampled=200, n_smiles=200, n_errors=0, n_dropped=0` (clean
run; rc=0 from wave87 sweep wrapper).

## Seed 44 framework-arm metrics (post-patch) — IN PROGRESS

Source: `verification_outputs/wave242-p1-flowmol3-seed44-framework.json` —
**DOES NOT EXIST YET**. The Wave 242 seed 44 retry v3 (with Wave 245 P1 extended
patch in `metrics.py`) was launched 2026-09-22 00:15:16 CST (PID 3524941
wrapper + PID 3524943 `wave87_n1000_sweep.py --seed-base 44`).

### Observed progress at audit time

- **Current PID state:**
  - 3524941 (`wave242_p1_flowmol3_rescue_single_mol.py --seed 44`): etime=01:14, CPU 0% (wrapper waits for child)
  - 3524943 (`wave87_n1000_sweep.py --seed-base 44 ...`): etime=01:14, CPU 108%, RSS 2.2 GB
- **GPU 0:** utilization 12%, memory 814 MiB
- **GPU 1:** idle
- **Wave87 sweep output files:**
  - `verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json`: modified 2026-09-22 00:13:46 (residue from PREVIOUS seed 44 retry attempt with original Wave 244 P5 patch; only baseline arm written; framework arm crashed at line 111 with `AttributeError: 'SampledMolecule' object has no attribute 'GetAtoms'` BEFORE the Wave 245 P1 extension)
  - `verification_outputs/flowmol3_n1000_framework_wave87_q4_2026.json`: modified 2026-09-21 23:05:06 (seed 44 framework arm from FIRST attempt; only sampling-stage JSON written; metrics path crashed before completion)
  - `verification_outputs/wave242-p1-flowmol3-seed44-{baseline,framework,summary}.json`: NONE EXIST yet (the wrapper script only renames wave87 outputs to `wave242-p1-flowmol3-seed44-*.json` AFTER the wave87 sweep completes and reports rc=0)
- **Estimated time to seed 44 framework JSON:** ~55 min remaining (30 min
  baseline + ~25 min framework for sampling; plus ~2 min for metrics + rename)

### Why seed 44 retry v3 was needed

Wave 244 P5 first patch (line 111 only) used `getattr(molecule, 'num_atoms',
len(molecule.GetAtoms()))`. When the seed 44 retry v2 ran with this patch, some
seed-44-sampled molecules were partial `SampledMolecule` objects with neither
`.num_atoms` NOR `.GetAtoms()` (a different molecule class than the seed-43
samples that exercised the original path). `len(molecule.GetAtoms())` raised
`AttributeError: 'SampledMolecule' object has no attribute 'GetAtoms'` at
`metrics.py:112` — see Wave 245 P1 commit f57d9ce (2026-09-22 00:15:28 CST)
for the full narrative and the 3-tier extension.

## Cross-seed numerical-equivalence check — CANNOT FINALIZE

The pre-patch (seed 43) framework arm exercised the ORIGINAL `metrics.py`
codepath (all 200 molecules were full `SampledMolecule` objects with
`.num_atoms`, `.atom_types`, `.valencies`, `.atom_charges`, `.fake_atoms` all
present). The post-patch (seed 44) framework arm will exercise the PATCHED
codepath. For numerical equivalence to be established, seed 44 framework-arm
metrics MUST match seed 43 framework-arm metrics within statistical variation
across seeds.

**Statistical-power context** (from `seed 43 summary
statistical_power_at_n1000`, scaled to N=200): at N=200, fg_dev SEM ~ 0.036
(1/sqrt(n_flags*N) ≈ 0.0129 at N=1000; ~2.24× larger at N=200), and MDD @ α=0.05
power=0.8 is ~3.6% in fg_dev. So framework-arm fg_dev across seeds should be
within ~0.04 absolute delta. Similarly for ood_ring_rate.

The expected diff ranges (preliminary, subject to verification when seed 44
completes):

- `|Δ fg_dev |` ≤ 0.04 (seed-variation noise floor at N=200)
- `|Δ validity_pct |` = 0 (both expect 1.0; tied at ceiling)
- `|Δ pb_validity_pct |` ≤ 0.10 (high SEM at N=200)
- `|Δ ood_ring_rate |` ≤ 0.02

**Honest disclosure:** Without seed 44 framework-arm output, this document CANNOT
certify that the patch is numerically inert. A future Wave 245 follow-up agent
MUST:
1. Verify that seed 44 retry v3 wrote
   `verification_outputs/wave242-p1-flowmol3-seed44-{baseline,framework,summary}.json`
2. Extract seed 44 framework metrics from the summary JSON
3. Compute absolute + relative diffs against seed 43 framework metrics
4. If any diff exceeds the statistical-variation envelope (see expected ranges
   above), REVERT THE PATCH and document a CODE bug (do not frame as
   "expected divergence")
5. If all diffs are within envelope, append a "POST-PATCH VALIDATION" section to
   this doc with the diffs and conclude that the patch is numerically safe

## Conclusion (PARTIAL)

**At audit-doc save time (00:16 CST 2026-09-22):** Seed 43 framework metrics
extracted cleanly (n_smiles=200, n_errors=0, no fallback path exercised).
Seed 44 framework metrics NOT YET AVAILABLE. The Wave 242 seed 44 retry v3
(with Wave 245 P1 3-tier extension) is RUNNING (PID 3524941 + 3524943) and
MUST NOT be interrupted.

**Final patch-validated verdict: PENDING** — to be issued by a future Wave 245
follow-up agent after seed 44 retry v3 completes and produces
`verification_outputs/wave242-p1-flowmol3-seed44-framework.json`.

**Wave 246 P4 update (audit-doc update; per-seed table cross-link).**
The Wave 246 P4 paper update
(`docs/drafts/section-2-method.md` §2.14, `docs/audit/wave246-p4-paper-updates.md`)
adds a per-seed table that uses the seed 43 framework fg_dev = 0.7361
(pre-patch baseline) and explicitly marks seed 44 as PENDING in the
table pending the seed 44 retry v3 completion. The seed 43 framework
fg_dev value 0.7361 is preserved verbatim from
`verification_outputs/wave242-p1-flowmol3-seed43-summary.json` and is
the post-patch framework arm reference (since Wave 245 P1 3-tier
extension is the active metrics.py at the audit save time, even though
seed 43 was sampled before the patch was applied — the patch is a
defensive fallback that does not exercise when the molecule IS a full
`SampledMolecule`, which seed 43's molecules all are).

**Hard rules respected:** No interruption of running process (PIDs 3524941 +
3524943 left alive). No modification of Wave 244 P5 patch (or its Wave 245 P1
extension). D.4 30/30 PASS not affected (regression suite does not exercise
metrics.py's `analyze()` path).

## Cross-references

- `data/FlowMol3/repo/flowmol/analysis/metrics.py:111-122` — extended patch (3-tier fallback, Wave 245 P1 commit f57d9ce)
- `data/FlowMol3/repo/flowmol/analysis/metrics.py:349-358` — patched (Wave 244 P5)
- `data/FlowMol3/repo/flowmol/analysis/metrics.py:363` — `getattr(molecule, 'fake_atoms', False)` patch
- `data/FlowMol3/repo/flowmol/analysis/metrics.py:390-401` — patched (Wave 244 P5)
- `docs/audit/wave244-p5-metrics-patch.md` — original 3-place patch narrative (extended by f57d9ce)
- `commit f57d9ce` — "Wave 245 P1: extend metrics.py line 111 patch with 3-tier fallback"
- `verification_outputs/wave242-p1-flowmol3-seed43-summary.json` — seed 43 framework metrics (clean)
- `verification_outputs/wave242-p1-flowmol3-seed43-{baseline,framework}.json` — per-arm output JSONs (sampling stage)
- `verification_outputs/flowmol3_n1000_{baseline,framework}_wave87_q4_2026.json` — wave87 sweep canonical output (currently mid-run for seed 44)
