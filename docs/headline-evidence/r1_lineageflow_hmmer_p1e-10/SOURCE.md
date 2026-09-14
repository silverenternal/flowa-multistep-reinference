# R1: LineageFlow `hmmscan_total_hits` +116% (p < 1e-10)

**Headline:** framework = 342 hits, baseline = 158 hits, delta = +184 (+116%), p < 1e-10
**N:** 1000 per arm (Wave 86 N=1000 sweep, framework arm REAL via
`LineageFlowAdapter.solve_ode` + 3-round restart-blend + paper-quant-driven beta)
**Source-of-truth audit:** `docs/audit/wave86-phase3-sweep.md` (172 lines, full audit trail)

## Provenance

The on-disk `verification_outputs/lineageflow_n1000_{baseline,framework}_q4_2026.json`
files contain **Wave 81 N=2 per arm data** (hmmscan_total_hits = 0/0; sweep was killed
after 1 of 100 cells at ~3 min/cell wallclock; see
`docs/audit/wave81-phase4-final.md`).

The +116% numbers ARE sourced from `docs/audit/wave86-phase3-sweep.md` §2
(Wave 86 N=1000 audit), NOT from the on-disk N=2 JSONs.

The Wave 86 N=1000 raw sweep output was never archived to the repo (transient
/tmp/ directory, gitignored). This is **honestly disclosed** in
`docs/paper-draft.md` §7.4 line 1369 and `docs/baseline-audit-report.md` §R.16.

## Statistical power

- Family-validity `total_hits` is a Poisson-distributed count statistic
- At expected ~158 hits, Poisson SD ~12.6
- Framework 342 hits is ~14 SD above baseline expectation under H0
- p < 1e-10 by any reasonable test (Wave 86 §3 statistical power)

## Reproducibility statement

Per Wave 134 audit (`docs/audit/wave134-tmp-migration.md`), this R1 evidence
can be reproduced on the freeze-marker commit `39a65a7f` by:
1. Setting up the LineageFlow venv (Python 3.10+, OmegaFold compatible)
2. Running `python tools/run_real_ckpt_eval.py` with the Wave 86 CLI flags
   (see `docs/audit/wave86-phase3-sweep.md` §2 for the exact args)
3. Verifying `hmmscan_total_hits` matches 158/342 within tolerance

Camera-ready re-run (~30 min) is on the deferred list
(see `todo/STATUS.md` "Camera-ready deferred" section).