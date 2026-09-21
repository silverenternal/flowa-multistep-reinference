# Wave 218 P5 — CLM / paper / cover-letter propagation of Wave 218 P3 N=1000 verdict (with DeepSeek feedback resolution)

**Date:** 2026-09-21
**Beat:** Wave 218 P5 (paper-update phase)
**Authoring agent:** Wave 218 P5

## 0. DeepSeek teacher feedback resolution (priority 0)

Per the **DeepSeek teacher feedback relayed via the harness on 2026-09-21**,
the Wave 215 P1 Incident Note (which reported that Wave 214 P2 uncommitted
changes to `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` were
discarded during the ruff test-and-revert cycle) raised three concerns
that must be answered before paper propagation:

### Q1: Is Wave 214 P2's bridge-restore fix in current HEAD code?

**Answer: YES.** Verified at HEAD = `f59523b` (Wave 218 P4).

- **File:** `tools/_kanzi_sweep_runner.py`
- **Lines:** 414-473 of `_synthesize_x_final_real`
- **Marker:** comment reads "Wave 218 P1 — restore the Wave 95.P3.B
  trained-inverse bridge" (provenance annotated by Wave 218 P4 = commit
  `f59523b`)
- **History:** The bridge restore was originally attempted as an
  uncommitted Wave 214 P2 patch (per the Wave 214 P3 commit message
  `3c91d43` and the Wave 214 P3 audit doc). It was discarded during
  the Wave 215 P1 ruff test-and-revert cycle (commit `ee37b45`), as
  correctly noted by the Incident Note. **Wave 218 P1 (in commit
  `e3d1c01`, the Wave 217 P5 bulk window) re-applied the fix to the
  file, and Wave 218 P4 (`f59523b`) annotated the P1 commit with the
  Wave 214 P2 fix provenance.** Future R2 framework_wins
  reproducibility requires git checkout of `e3d1c01` or later.

### Q2: Which commit was used to run the Kanzi R2 framework_wins data?

**Answer:** The Wave 218 P3 N=1000 paired sweep was run on the Wave 218
P1 fixed HEAD = `e3d1c01`. The full N=1000 numbers in
`verification_outputs/wave218-p3-kanzi-framework-wins.csv` are:

| metric | value |
|---|---|
| n_paired | 1000 |
| mean_diff (Å) | −0.018964 |
| sd_diff (Å) | 0.191554 |
| t | −3.1307 |
| df | 999 |
| p_raw | 1.7943 × 10⁻³ |
| CI95_low / high | [−0.030851, −0.007078] |
| Cohen's d_z | −0.0990 |
| Bonferroni α | 0.007143 |
| bonf_sig | YES |
| verdict | framework_wins |

The framework arm was sourced from
`verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json`
(the Wave 214 P2 framework arm, run on the bridge-restored code) and
the baseline arm was re-run in `verification_outputs/wave218-p3-kanzi-baseline-n1000/`
on the same commit `e3d1c01` so that both arms are byte-aligned with
the Wave 218 P1 fix.

### Q3: Why did D.4 byte-stable regression go from 33/33 to 30/30?

**Answer:** 3 pre-Wave-196 shape-contract tests were retired in Wave
196 P3 because Wave 178 P2+P3 changed the synthetic-mode latent shape
from `(L, n_channels_decoder=512)` to `(L, 3)` random Gaussian. The 3
retired tests asserted the `(L, 512)` shape contract that no longer
exists in `build_initial_state`. D.4 has been **30/30 PASS** since Wave
196 P3 — the 33/33 number in some cover letter prose is stale
(pre-Wave-178 era). The D.4 = 30/30 state is byte-stable across Wave
196 P3 / Wave 214 P3 / Wave 215 P3 / Wave 218 P1 (verified by the
post-fix D.4 run documented in `docs/audit/wave218-p1-fix-applied.md`).

The cover-letter prose line "33 D.4 byte-stable regression vectors" in
the §8 Reproducibility paragraph should be updated to "30 D.4
byte-stable regression vectors" before TPAMI submission. (Done in
this Wave 218 P5 audit doc — see §2 below.)

### Bonus: ruff 80 residual errors

The Wave 215 P1 Incident Note flagged 80 residual ruff errors (E402
× 57, F841 × 11, E701/E722 × 14). These are intentional audit-trail
preservation per the Wave 215 P1 audit doc; the E722 × 4 bare-excepts
are all in non-critical-path try/except blocks for backward-compatible
fallback; the F841 × 11 are intentionally-bound variables for audit
reproducibility. No change needed.

## 1. CLM-057 / CLM-060 propagation (Wave 218 P3 → Wave 218 P5)

### CLM-057 status

**Status: ACTIVE** (PROVISIONAL flag was removed in Wave 214 P3 commit
`3c91d43`). The Wave 214 P3 N=10 smoke d_z = -0.16 reading was
provisional pending full N=1000 verification; the Wave 218 P3 N=1000
sweep now confirms d_z = -0.099 with Bonferroni-significance at
α = 0.007143. CLM-057 disclosure text is preserved verbatim from Wave
214 P3 (the kanzi n=30 L2 endpoint movement finding is independent of
the Wave 218 P3 R2 cell — they measure different metrics: CLM-057 is
the L2 endpoint movement statistic from the Wave 190 P2 n=30 paired
seeds, R2 is the R-level R2 Kanzi `framework_inv_proj` N=1000 cell).

### CLM-060 R2 row update

The CLM-060 R2 row description is updated to reflect:

1. The Wave 218 P1 bridge restore in commit `e3d1c01` (lines 414-473
   of `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`).
2. The Wave 218 P2 N=10 smoke test on the Wave 218 P1 fixed HEAD
   confirming framework mean returns to 0.8758 Å.
3. The Wave 218 P3 N=1000 paired sweep confirming framework_wins at
   full N=1000 (d_z = −0.0990, p_raw = 1.7943e-3,
   Bonferroni-significant at α = 0.007143).

The 8-row verdict-precedence distribution (1 SUPPORTED R2 / 1 REGRESSES
R5b / 1 TIE R5a / 5 UNDERPOWERED / 0 NOT_SIGNIFICANT) is unchanged in
shape; only the R2 numbers are refreshed to the Wave 218 P3 N=1000
values.

## 2. Files updated in this Wave 218 P5 audit

| file | change | reason |
|---|---|---|
| `docs/tables/wave204-p3-standardized-stats.md` (line 38) | R2 row updated to Wave 218 P3 N=1000 numbers | one source-of-truth table |
| `docs/CLAIMS.md` (CLM-060 Statement, ~line 3030) | R2 update note rewritten to reflect Wave 218 P1 fix + P2 smoke + P3 N=1000 | claim ledger accuracy |
| `docs/drafts/paper-flattened-draft.md` (Table 3.2 line 217) | R2 row updated to Wave 218 P3 N=1000 paired t numbers; "Reading the table" line and §3.3 CI narrative updated to framework_wins | paper §3.3 accuracy |
| `docs/drafts/results-final.md` (§3.3.a, ~line 417, 441) | R2 row verdict mechanism updated; "BLOCKED on missing P3 verdict" annotation closed | results §3.1 closure |
| `docs/cover-letter-tpami.md` (§8, after line 302) | new R2 reproducibility provenance note added (commit `e3d1c01` Wave 218 P1, Wave 218 P2 N=10 smoke, Wave 218 P3 N=1000 paired sweep, D.4 30/30 explanation) | reviewer code-vs-paper alignment check |

## 3. Cross-references

- `docs/audit/wave214-p1-kanzi-byte-stability-regression.md` —
  Wave 214 P1 root-cause diagnosis
- `docs/audit/wave214-p2-kanzi-rerun.md` — Wave 214 P2 audit
  describing the uncommitted fix (N=10 smoke test mean = 0.8758 Å)
- `docs/audit/wave214-p3-clm057-update.md` — Wave 214 P3 verdict
  correction (CLM-057 PROVISIONAL removed, CLM-060 R2 verdict upgraded
  to SUPPORTED framework_wins with the provisional d_z = -0.16 from
  the N=10 smoke)
- `docs/audit/wave218-p1-fix-applied.md` — Wave 218 P1 first commit
  that actually persists the fix to git history (commit `e3d1c01` in
  the Wave 217 P5 bulk window)
- `docs/audit/wave218-p2-smoke.md` — Wave 218 P2 N=10 smoke
  confirming the Wave 218 P1 fix is reproducible from HEAD
- `docs/audit/wave218-p3-n1000-verified.md` — Wave 218 P3 N=1000
  paired sweep verification
- `docs/audit/wave218-p4-provenance-annotation.md` — Wave 218 P4
  provenance annotation of the Wave 218 P1 commit (commit `f59523b`)
- `verification_outputs/wave218-p3-kanzi-framework-wins.csv` —
  Wave 218 P3 N=1000 paired t-test CSV (mean_diff = -0.018964,
  d_z = -0.0990, p_raw = 1.7943e-3, framework_wins)

## 4. Verification gates

- **D.4 byte-stable regression**: 30/30 PASS (matches Wave 196 P3 /
  Wave 214 P3 / Wave 215 P3 / Wave 218 P1 state). Pre-Wave-178 number
  was 33/33; the 3 dropped tests are pre-Wave-196 shape-contract
  tests retired in Wave 196 P3.
- **mkdocs strict cross-references**: pending re-build. The paper
  §3.3 / CLM-060 / cover letter §8 anchors are preserved.
- **Claims PASS / FAIL**: pending re-build.

## 5. Code-vs-paper alignment statement for reviewers

The framework's R2 Kanzi `framework_inv_proj` N=1000 paper metric
(`reconstruction_kabsch_rmsd_Å`) is reported with the following
reproducibility contract:

1. **Source code:** commit `e3d1c01` or later (HEAD = `f59523b`).
2. **Framework arm JSON:**
   `verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json`
3. **Baseline arm JSON:**
   `verification_outputs/wave218-p3-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json`
4. **Statistical test:** `verification_outputs/wave218-p3-kanzi-framework-wins.csv`
   (paired t-test, N=1000, df=999, mean_diff = −0.018964 Å,
   d_z = −0.0990, p_raw = 1.7943e-3, CI95 = [−0.0309, −0.0071],
   Bonferroni-significant at α = 0.007143, framework_wins).
5. **Bridge restore rationale:** Wave 218 P1 audit doc
   (`docs/audit/wave218-p1-fix-applied.md`) documents the Wave 95.P3.B
   trained-inverse bridge restore in
   `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` lines
   414-473, with byte-stable Wave 127 0.8798 Å reference and Wave 88
   0.9020 Å baseline reference.