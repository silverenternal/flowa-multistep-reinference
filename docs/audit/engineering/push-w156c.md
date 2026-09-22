# Wave 156c — Push Audit

**Date:** 2026-09-15
**Operator:** Wave 156c Agent 5 (paper §10.4 + §Ablations ADDITIVE update + push executor)
**Branch:** main
**Push target:** origin/main
**User approval:** User explicitly approved push of Wave 156 + Wave 156c commits (4 unpushed + 1 new paper-update commit = 5 total).

## Pre-push State

| Metric | Value |
| --- | --- |
| Working tree | clean (after staging `docs/paper-draft.md`) |
| Unpushed commits (Wave 156 + 156c batch) | **4** (Wave 156 P1 + P2 + P3 + Wave 156c P4) |
| Pre-push commit additions from Wave 156c P5 (paper-update) | **1** (this commit, sha `6e9035e`) |
| Total commits pushed in this Wave 156c push | **5** |
| Local HEAD SHA (pre-commit) | `326ef64` (Wave 156c P4: HMMER real-seq outputs collected) |
| Local HEAD SHA (post-commit, pre-push) | `6e9035e` (Wave 156c P5: paper §10.4 + §Ablations ADDITIVE update) |
| origin/main HEAD SHA (pre-push) | `3a4f876b4afcd7dab33b93975e382cad3548a0f7` (Wave 155 P3 README refresh) |

### Pre-push commit range overview

| Wave | Commit | Description |
| --- | --- | --- |
| Wave 156 P1 | `72af942` | ruff cleanup of scripts/run_ablation_sweep.py (7 → 0 errors; SIM105/I001/SIM118/SIM108/UP017) |
| Wave 156 P2 | `aaf0f9b` | K1 RC5 N=1000 5-arm real-ckpt ablation sweep launched (RTX PRO 6000 Blackwell; --force-mode real wired) |
| Wave 156 P3 | `8b38c86` | LineageFlow N=1000 HMMER with REAL sampled sequences launched (FASTAs via tools/gen_lineageflow_n1000_fastas.py) |
| Wave 156c P4 | `326ef64` | HMMER real-seq outputs collected (baseline + framework hits.tbl + sha256; gates preserved) |
| Wave 156c P5 | `6e9035e` | paper §10.4 + §Ablations ADDITIVE Wave 156 K1 sweep disclosure (this commit) |

## Pre-push Gate Verification

```
$ python tools/verify_submission_readiness.py
[ OK ] d4_72          : 72 passed, 0 failed (D.4 pinned regression vectors)
[ OK ] ruff_0         : All checks passed!
[SKIP] mypy_0         : mypy not on PATH (sandbox without mypy); preserved from Wave 149 P5 audit
[ OK ] claims_pass    : No drift detected (39 active claims)
[ OK ] paper_warns    : 1 warning (≤10 budget; 0 overfull + 1 LaTeX Warning)
[ OK ] r1_r6_sha      : 10/10 R1-R6 files present + sha256 matches
[ OK ] k1_rc5         : K1 §10.4 wording confirms "only RC5" + "REMAINING" status
[ OK ] drift_33       : 0 unintended 33/33 occurrences outside Wave 149 audit trail (73 intentional historical docs verified)
[ OK ] framework_n1000 : 2/2 Kanzi N=1000 sweep JSONs present (framework_inv_proj + framework_synth)
READY_WITH_SKIPS: mypy_0
```

**Status:** READY_WITH_SKIPS — only skip is `mypy_0` (sandbox lacks mypy; preserved from Wave 149 P5 audit, not a regression). All 8 other gates pass.

## Paper-draft.md changes (Wave 156c P5)

Two ADDITIVE paragraphs added; zero existing content removed or rewritten:

1. **§10.4 Wave 156 paragraph** (inserted after the Wave 154b POC validation paragraph at line 6194, before §10.5): documents the **10/15 OK + 5/15 RUN_ERROR** real-ckpt result, the kanzi 5/5 shape-mismatch traceback at `kanzi.py:1209` / upstream `models.py:351`, the recommended 3-line camera-ready-deferred patch, the lineageflow 5/5 real-ckpt OK value-add, the sha256 of the JSON, and the cross-link to the audit doc. Preserves K1 §10.4 wording verbatim per the ADDITIVE reframe of Wave 150 P3.

2. **§Ablations.9 Wave 156 real-ckpt per-component contribution matrix (10/15 OK)** (inserted after §Ablations.8 closing, before §5 Discussion): renders the 5-arm × 3-model matrix with status badges (OK / RUN_ERROR), per-cell `signed_delta` values, and the interpretation (twodim_fm 5/5 + lineageflow 5/5 OK; kanzi 0/5 OK on shape mismatch). Cross-links §10.4 Wave 156 paragraph + the audit doc. ADDITIVE only — does not modify any §Ablations.1-8 cell.

LOC added: **+26 insertions** (per `git show --stat 6e9035e`).

## Push Execution

```
$ git push origin main
To https://github.com/silverenternal/flowa-multistep-reinference.git
   3a4f876..6e9035e  main -> main
```

**Result:** SUCCESS. origin/main advanced from `3a4f876` to `6e9035e` (5 commits transferred cleanly; no rejections, no non-fast-forward warnings).

## Post-push State

| Metric | Value |
| --- | --- |
| Unpushed commits | **0** |
| origin/main HEAD SHA | `6e9035e954d12ca1450eb00c5b80883d8e77728c` |
| Local HEAD SHA | `6e9035e954d12ca1450eb00c5b80883d8e77728c` |
| Divergence | None — local and origin/main are at the same SHA |

### Post-push origin/main top commits

```
6e9035e Wave 156c P5: paper section 10.4 + Ablations ADDITIVE Wave 156 K1 sweep disclosure
326ef64 Wave 156c P4: HMMER real-seq outputs collected (baseline + framework hits.tbl + sha256)
8b38c86 Wave 156 P3: LineageFlow N=1000 HMMER with REAL sampled sequences launched
aaf0f9b Wave 156 P2: K1 RC5 full N=1000 5-arm real-ckpt ablation sweep launched
72af942 Wave 156 P1: ruff cleanup of scripts/run_ablation_sweep.py
```

## Final Acceptance Gates (post-push)

| Gate | Status | Detail |
| --- | --- | --- |
| `verify_submission_readiness.py` | READY_WITH_SKIPS: mypy_0 | All 8 hard gates PASS; mypy skip is preserved from Wave 149 P5 audit (sandbox without mypy) |
| D.4 pinned regression vectors | **72/72 PASS** | unchanged from Wave 154b push |
| ruff | **0 errors** | unchanged from Wave 156 P1 ruff cleanup |
| claims consistency | **No drift detected** | 39 active claims |
| paper_warns | **1 warning** (≤10 budget) | unchanged from Wave 156c P4 |
| r1_r6_sha | **10/10 files present + sha256 matches** | unchanged |
| k1_rc5 | K1 §10.4 wording preserves "only RC5" + "REMAINING" | ADDITIVE Wave 156 paragraph does not modify the K1 disclosure |
| drift_33 | 0 unintended 33/33 occurrences outside Wave 149 audit trail | 73 intentional historical docs verified |
| framework_n1000 | 2/2 Kanzi N=1000 sweep JSONs present | framework_inv_proj + framework_synth |

## Rollback Instructions (if push needed to be reverted)

```bash
# Revert this push (5 commits) without touching history:
git revert --no-commit 6e9035e 326ef64 8b38c86 aaf0f9b 72af942
git commit -m "Revert Wave 156 + 156c push (5 commits)"
git push origin main

# Or, for a hard reset to the previous origin/main SHA (DANGEROUS — rewrites history):
# git reset --hard 3a4f876
# git push --force-with-lease origin main
```

## Cross-references

- Wave 156 + 156c sweep JSON: `/tmp/w156/k1_rc5_5arm_real_n1000/ablation_q4_2026.json` (sha256 `8583a49eb385ab0a4d3b95da1eb8b1a05198ccc62411b20e9ead70321e93ac21`)
- Wave 156 HMMER real-seq outputs: `/tmp/w156/hmmer_real_n1000/{baseline,framework}/hits.tbl`
- K1 sweep launch audit: `docs/audit/wave156-k1-rc5-launch.md`
- HMMER real-seq collect audit: `docs/audit/wave156c-hmmer-collect.md`
- ruff cleanup audit: `docs/audit/wave156-ruff-cleanup.md`
- Paper-draft.md Wave 156c P5 diff: `git show 6e9035e` (26 insertions across §10.4 + §Ablations.9)
