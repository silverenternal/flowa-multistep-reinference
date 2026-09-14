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

**Wave 139 follow-up (closes K8 honest-negative-surface item).** The full 8-cell
NFE scan paper-metric axis is now archived at
`verification_outputs/lineageflow_nfe_scan_paper_metric_q3_2026.json`
(8 cells: 3 seeds x ~3 NFE budgets [50/100/200]; real metric_mode; deterministic
per-record seed; full provenance to the v1.0.1-paper-final freeze-marker commit
0ef6465). Camera-ready re-run on the freeze-marker commit completed in ~30 min
on the LineageFlow venv (Python 3.10).

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

---

## Post-Wave-151 P5 audit reconciliation note (2026-09-14)

The prose-text audit-doc references in this SOURCE.md (lines 6, 16, 19, 40,
43) point to `docs/audit/wave86-phase3-sweep.md`, `docs/audit/wave81-phase4-final.md`,
and `docs/audit/wave86-phase1-audit.md`. **Wave 137 Phase 1 (commit `3f4a09e`)
archived all Wave 1-99 audit docs** from `docs/audit/` to
`docs/ARCHIVE/audit-waves-1-99/`. The canonical paths are now:

- `docs/ARCHIVE/audit-waves-1-99/wave86-phase3-sweep.md` (the R1 source-of-truth, N=1000 sweep audit)
- `docs/ARCHIVE/audit-waves-1-99/wave81-phase4-final.md` (the Wave 81 Phase 4 final)
- `docs/ARCHIVE/audit-waves-1-99/wave86-phase1-audit.md` (the Wave 86 Agent A audit)

The `source_audit_doc.md` symlink in this directory correctly points to
the canonical ARCHIVE path, so directory-level discovery works. This
note is **ADDITIVE only** — the existing prose references above are
preserved verbatim per the Wave 137 archive invariant (no destructive
edits to historical SOURCE.md text). The headline numbers (158 → 342,
+116%, p<1e-10) are byte-stable across Waves 135-151.

See `docs/audit/wave151-headline-evidence-audit.md` for the per-R
audit ledger and fix inventory.