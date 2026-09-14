# Wave 96 Status Reality Check — 2026-09-10

## Purpose

This audit doc was triggered by the Wave 96.E retry's GPU monitoring showing
"VRAM occupied but compute 0%". Investigation revealed a systemic issue:

**Most Kanzi "N=1000 sweep" claims across Waves 91-95 are actually N≤10
smoke tests, not N=1000 sweeps.**

This document enumerates every claim that needs correction.

## Reality Check Table — file system verification

I ran `find verification_outputs/ -name "kanzi_n1000*" -type d` to enumerate
what's actually on disk:

| Directory | Size | Files | Actual content | Claim status |
| --- | --- | --- | --- | --- |
| `kanzi_n1000_paper_metrics/` | 4.0 KB | 1 | 1 small summary | NO N=1000 sweep data |
| `kanzi_n1000_framework_paper_metrics/` | 20 KB | 2 | small summaries | NO N=1000 sweep data |
| `kanzi_n1000_framework_paper_metrics_real/` | 152 KB | 9 | `probe10*.json`, `smoke*.json` — all N≤10 probes | Wave 92c "N=1000 sweep" was actually N=10 |
| `kanzi_n1000_framework_paper_metrics_inv_proj/` | 7.5 MB | 2 | `per_metric.jsonl` (~7.5 MB) | Wave 95 Phase 3.C — likely N≤10 smoke that wrote ~750 KB/record with full per-metric detail |
| `kanzi_n1000_framework_paper_metrics_real_diverse/` | 0 B | 1 | empty `per_metric.jsonl` (placeholder) | Wave 96.E — currently in flight |

**Conclusion**: No directory contains the per-record JSONL output that a true
N=1000 sweep would produce. The typical sweep writes 50-200 bytes per record,
so a real N=1000 sweep would be 50-200 KB. The 7.5 MB file is consistent with
~50-100 N≥10 records with full per-metric detail, not N=1000.

## What commit messages claimed vs what was actually run

### Wave 91 (commit `dfe0f4e` etc.) — Kanzi bridge code

> tools/kanzi_latent_to_coord.py — Wave 91 Phase 2: Author tools/kanzi_latent_to_coord.py bridge

**Reality**: Authored the bridge code (true). Did NOT run any N=1000 sweep
through the bridge. No sweep output file dated Wave 91 exists.

### Wave 91 Phase 4 (commit `8c5eaaf` / `2a4c46e`) — Kanzi framework wire

> Wire kanzi_latent_to_coord into run_real_ckpt_eval.py

**Reality**: Wired the bridge (true). Did NOT run any N=1000 sweep through
the wired pipeline. Wave 91 Agent D RE-RUN task (#1277) is still marked
in_progress — was never completed.

### Wave 92b (commit `60dcbb7`) — Kanzi N-samples patch

> Patch tools/upstream_eval.py Kanzi branch to honor --upstream-n-samples

**Reality**: Patched the flag (true). Did NOT run any Kanzi N=1000 sweep to
verify the flag is honored end-to-end.

### Wave 92c (commit `27aa389`) — Kanzi N=1000 framework paper-metric sweep

> Run N=1000 Kanzi framework paper-metric eval

**Reality**: Output is `probe10c.json` (34 KB, N=10). The commit message said
"N=1000" but only N=10 records were actually processed. This is the smoke test
that yielded the +1.63 Å REGRESS that subsequently informed every downstream
decision.

### Wave 95 Phase 3.B (commit `378dc4a`) — project_out⁻¹ architectural fix

> Wire project_out⁻¹ into kanzi_latent_to_coord.py

**Reality**: Trained the inverse and wired the bridge (true). Did NOT run
N=1000 sweep. Wave 95 Phase 3.C retry produced `per_metric.jsonl` of ~7.5 MB
with framework RMSD = 3.1783 ± 0.0000 Å (zero variance, indicating N=10 smoke
where all records collapse to the same codebook index — see Wave 96.A
collapse-diagnosis).

### Wave 95 Phase 2.D (commit `f460444`) — FlowMol3 pb_validity xtb default

> Switch pb_validity default to xtb

**Reality**: Changed default (true). Did NOT re-run the Wave 86-89 FlowMol3
sweep to measure whether the -9.95pp REGRESS actually closes with xtb. The
12-cell table claim that F2 closes the REGRESS was is speculative until a
sweep is re-run.

### Wave 93 (commits `e69ffd8`, `51677d8`) — statistical power analysis

> 12-cell per-cell verdict table

**Reality**: Tool is correct. The numbers are sourced from upstream sweep
JSONs that themselves are N≤10 (per the above). At N≤10, MDD ≈ 31pp and
only effects ≥31pp are detectable. The verdict distribution (1 SUPPORTED,
1 REGRESS, 4 UNDERPOWERED, 8 TIE) reflects N=1000 sample variance masked
by N≤10 noise. The "Bonferroni p_bonf = 0" for the LineageFlow
`hmmscan_total_hits` cell is mathematically valid but conceptually meaningless
at N≤10 — the count scale of the metric means anything is "detected" if it
exists.

### Wave 96.D (no commit) — Kanzi framework endpoint collapse

Output: `/tmp/wave96d_dbg/per_metric.jsonl` — 3 records (RMSD 1.83, 1.90 Å,
unique idx_hash). This was a 3-record smoke test, not N=1000.

## Affected downstream artifacts

These downstream documents propagate the smoke-test numbers as if they were
N=1000 numbers:

1. `docs/audit/wave93-phase2-final.md:35-48` — 12-cell per-cell verdict table
2. `docs/audit/wave92c-n1000-sweep-real.md` — Wave 92c narrative
3. `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` — Phase 3.C narrative
4. `docs/paper-draft.md` §7.3 Kanzi — uses +1.63 Å REGRESS (from N=10)
5. `docs/paper-draft.md` §7.6 — uses the 12-cell verdict from above
6. `cover_letter.md` — cites "LineageFlow hmmscan_total_hits +116%, p<1e-10"
   and "FlowMol3 fg_dev 4.05σ" — both derived from N≤10 sources
7. `supplementary.md` §3.4 — Kanzi audit placeholder for Wave 92c numbers
8. `docs/CONSOLIDATED_RESULTS.md` §15.15 — 12-row verdict table
9. `docs/CONSOLIDATED_RESULTS.md` §19.9 — 4 一区 reviewer weaknesses (W2 row)

## What Wave 96.E is expected to deliver

Wave 96.E (task ID `wqqlmxg8w`, in flight as of 2026-09-10 15:21):

- New sweep script `tools/sweep_kanzi_n1000_diverse.py` with the 3-record
  debug limit REMOVED
- Real N=1000 sweep run via kanzi_venv
- Output to `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl`
  with **1000 records** (50-200 KB file)
- Mean / std / 95% CI for reconstruction_kabsch_rmsd_A
- Paper §7.3 update with the real N=1000 numbers

If the wave 96.E sweep succeeds and produces a 1000-record JSONL, all the
artifacts above need to be re-derived from the new numbers. If the wave
96.E sweep fails (or produces a 3-record file like Wave 96.D), this reality
check is the only honest record of what was actually measured.

## Action items for honesty

When Wave 96.E completes:

1. Verify the JSONL file size matches ~1000 records (50-200 KB). If it's
   smaller, the agent wrote another limited script.
2. Re-derive the 12-cell verdict table from the actual N=1000 numbers.
3. Update paper §7.3, §7.6, cover letter, supplementary, and
   CONSOLIDATED_RESULTS with the real numbers.
4. Add a §"N≤10 smoke provenance" caveat to each affected artifact.
5. Re-run the Wave 93 statistical power analysis on the new numbers — the
   MDD will tighten from ~31pp (N=10) to ~4.4pp (N=1000) for p=0.5 metrics.

## Temporary status (pending Wave 96.E)

**All paper-metric numbers cited from Wave 91-95 commits are preliminary
N≤10 smoke values, not N=1000 measurements. They are useful as
diagnostic signals but should not be cited as N=1000 statistical claims
in the paper.**

Co-Authored-By: Claude Code <noreply@anthropic.com>