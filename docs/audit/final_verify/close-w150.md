# Wave 150 — Wave 149 follow-up (2026-09-14)

**Date:** 2026-09-14
**Agent:** Wave 150 Agent 6 (final close + audit doc + baseline R.38 + CONSOLIDATED 15.47 + final drift check)
**Wave:** 150 — Wave 149 follow-up

## Scope

Wave 150 closes the Wave 149 follow-up items (re-run the deferred Phase 3 sweep + close K1 RC4 ablation script hardcode + paper §10.4 K1 disclosure update + LineageFlow HMMER POC archival + continue paper.pdf warning reduction). 6 atomic Phases total (Phases 1-5 by prior agents + this Phase 6 final synthesis by Agent 6).

## 6 atomic phases

### Phase 1 (commit `706faf5`): P3 sweep closed
Re-ran Wave 124 N=1000 framework_inv_proj sweep on RTX PRO 6000 Blackwell. `n=1000, 0 skipped`. Sweep JSONs at `/tmp/w149/framework_inv_proj/`. Byte-stability delta=0.0 vs Wave 124 baseline — verifies that the Wave 121 bridge fix applied in Wave 149 P1 has zero regression at Kanzi N=1000.

### Phase 2 (commit `7b2df23`): K1 RC4 ablation fix
Closed K1 RC4 — ablation script `force_mode="synthetic"` hardcode replaced with proper argparse. `force_mode`/`metric_mode` argparse + `--limit/--model/--ckpt` flags + 50 LOC tests + backward-compat sanity sweep (~80 LOC total). Reduces the K1 Kanzi N=1000 5-arm ablation from a manual-edit-required run to a CLI-driven sweep.

### Phase 3 (commit `1fb3921`): paper section 10.4 K1 update
ADDITIVE reframe of `docs/paper-draft.md` §10.4 K1 disclosure — **4 of 5 K1 RCs RESOLVED** via Wave 149-150 (RC1 via Wave 149 P1; RC2+RC3 via Wave 149 P2; RC4 via Wave 150 P2); only RC5 (5-arm Kanzi N=1000 ablation 35h GPU) remains. Wave 146 + Wave 148 P3 wording preserved verbatim.

### Phase 4 (commit `183fc20`): LineageFlow HMMER POC
LineageFlow N=1000 HMMER raw JSON archival POC. FASTAs verified on-disk at `/tmp/w149/lineageflow_hmmer/baseline/{baseline,framework}.fasta` (126 939 + 127 374 bytes, 1000 sequences each, 4 families x 250 seq). `manifest.json` 717 bytes (seed 42, family IDs, nfe_per_record=10, n_rounds=3). Pfam DB checked at `data/lineageflow_upstream/databases/pfam35/Pfam-A.hmm` (2 246 909 846 bytes / ~2.1 GB; pre-pressed with `.h3f/.h3i/.h3m/.h3p`). POC N=10 scan executed end-to-end on both baseline + framework FASTAs (22 + 14 hits passed Viterbi filter; ~0.21s wall, ~866-1537 Mc/s). Full N=1000 HMMER scan **deferred to dedicated camera-ready compute window** (~30-50h CPU each).

### Phase 5 (commit `0bffbb0`): paper.pdf warnings 38 to 5
Continued paper.pdf warning reduction from 38 (Wave 149 P4 close) to **5** (Wave 150 P5 close) via non-tabular `\sloppypar` + `\path{}` fixes. PDF page count preserved at 115 ±2.

### Phase 6 (this commit): final close
Writes the audit doc `docs/audit/wave150-close.md` (this file) + inserts baseline §R.38 row + appends CONSOLIDATED §15.47 + final drift check (no remaining 33/33 occurrences to fix — Wave 149 Agent 6 standardization already converted 315 historical instances; remaining "33/33 PASS" occurrences are explicit historical-caveat footnotes documenting the Wave 38-39 first-batch subset). Single atomic Agent 6 commit.

## Acceptance gates

| Gate | Status |
|------|--------|
| ruff 0 | PRESERVED |
| D.4 72/72 PASS | PRESERVED |
| claims_consistency PASS | PRESERVED |
| mkdocs build --strict EXIT=0 | UNCHANGED from Wave 149 state (1 pre-existing nav-warning on `code-release-checklist.md`; Wave 150 introduces no new warnings) |
| Wave 150 P1 byte-stability delta | 0.0 (vs Wave 124 N=1000 baseline) |
| Wave 150 P5 paper.pdf warning reduction | 38 → 5 (87% reduction; pages preserved at 115 ±2) |
| Wave 150 P2 backward-compat sanity | PASS |
| Wave 150 P4 HMMER POC scan | PASS (22 + 14 Viterbi hits at N=10) |

## K1 status (after Wave 149 + Wave 150)

| State | K1 RCs remaining | Resolved |
|-------|-----------------:|----------|
| Before Wave 149 | BLOCKED on 5 RCs | 0 |
| After Wave 149 | BLOCKED on 2 RCs (RC4 + RC5) | 3 (RC1 + RC2 + RC3) |
| After Wave 150 | BLOCKED on 1 RC (RC5 only) | 4 (RC1 + RC2 + RC3 + RC4) |

- **RC1** (Wave 121 bridge bug) — RESOLVED via Wave 149 P1 (`4f5ecdf`) — adapter-layer inverse projection at `kanzi.py:_torch_velocity_field` + conditioning cache plumbing at `_resolve_conditioning` + 85 LOC unit test + 12 LOC regression test (~115 LOC total).
- **RC2** (CLI flag absence `--brai-eps-scale`) — RESOLVED via Wave 149 P2 (`6f700e2`) — 2-line argparse + 3-line consumer override + 80 LOC tests.
- **RC3** (CLI flag absence `--n-rounds`) — RESOLVED via Wave 149 P2 (`6f700e2`) — 2-line argparse + 3-line consumer override + 80 LOC tests + 6-cell sanity sweep.
- **RC4** (ablation script `force_mode="synthetic"` hardcode) — RESOLVED via Wave 150 P2 (`7b2df23`) — `force_mode`/`metric_mode` argparse + `--limit/--model/--ckpt` flags + 50 LOC tests + backward-compat sanity.
- **RC5** (5-arm Kanzi N=1000 ablation 35h GPU compute) — DEFERRED to camera-ready. Wave 150 P2 closes the script-side blockers; only the compute budget (35h GPU) remains.

## Camera-ready remaining (after Wave 150)

| Item | Scope | Estimated compute |
|------|-------|-------------------|
| K1 RC5 | 5-arm ablation at Kanzi N=1000 (5 conditions x N=1000 sweep) | 35h GPU |
| LineageFlow N=1000 full HMMER scan | 3 conditions (baseline + framework + framework_fallback) at full N=1000 | ~30-50h CPU each (POC suggests faster on warm DB cache) |
| paper.pdf warnings further reduction | Remaining 5 → 0 (non-tabular cosmetics only; mostly unused-`\xxx` definition warnings) | ~2h CPU + pdflatex build chain |
| Wave 121 bridge fix at scale | Re-run at N=5000-50000 (currently verified at Kanzi N=1000 only) | ~20h GPU |
| Wave 146 Item 1 Kanzi N=1000 algorithm-primitive ablation | Unblocked-once-RC4 (Wave 150 P2 ✓) + RC5 (pending) | ~5h GPU (after RC5) |
| Wave 146 Item 2 2D FM hp sweep full 15/15 cells | Unblocked via Wave 149 P2 (was PARTIAL with 3 BLOCKED hparams) | ~1h CPU |

## Final drift check (Wave 150 Agent 6 contribution)

Confirmed via `grep -rn "33/33 PASS" docs/` that all remaining "33/33 PASS" occurrences in `docs/` are explicitly annotated as the **Wave 149 D.4 drift fix footnote** (per `docs/GATES.md` §D.4 historical caveat + Wave 149 Agent 6 standardization extension to 73 non-archived docs/ files).

The Wave 149 drift fix already converted all 315 historical "33/33 PASS" instances to "72/72 PASS" across the non-archived docs/, leaving only the explicit historical-caveat paragraphs referencing the Wave 38-39 first-batch subset (which is the correct historical context for that figure). These remaining occurrences are intentional documentation, not drift bugs.

No additional drift correction is required for Wave 150.

## References

- `docs/baseline-audit-report.md` §R.38 (Wave 150 ledger row)
- `docs/CONSOLIDATED_RESULTS.md` §15.47 (Wave 150 close section)
- `docs/audit/wave150-rc4-ablation-fix.md` (Phase 2 — K1 RC4 ablation script fix)
- `docs/audit/wave150-lineageflow-hmmer-poc.md` (Phase 4 — LineageFlow HMMER POC)
- `docs/audit/wave150-pdf-warning-reduction.md` (Phase 5 — paper.pdf warning reduction)
- `docs/paper-draft.md` §10.4 (Phase 3 K1 RC1-RC4 RESOLVED disclosure)
- `docs/audit/wave149-close.md` (predecessor wave)
- `docs/baseline-audit-report.md` §R.37 (Wave 149 close row)
- `docs/GATES.md` §D.4 (D.4 72/72 PASS source-of-truth + historical "33/33 PASS" caveat)
- Wave 124 N=1000 framework_inv_proj sweep baseline (Wave 124 P1; sweep JSONs at `/tmp/w124/framework_inv_proj/`)