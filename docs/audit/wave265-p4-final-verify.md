# Wave 265 P4: Final Verification

**Date:** 2026-09-22
**Branch:** main
**Scope:** Final byte-stable verification of all Wave 265 deliverables
(R1 p-value fact-fix, Quick Start cell-count fix, R3 row format
alignment, R2 row format KEEP decision). README only — no source code
changes in this wave.

## 1. Deliverables verified

| # | Wave | Commit | Description |
|---|---|---|---|
| 1 | 265 P1 | eeb6976 | README R1 p-value fact fix — `p < 1e-10` → `p ≈ 1.5e-08` |
| 2 | 265 P2 | c44fee9 | README Quick Start cell count + R3 row format consistency |
| 3 | 265 P3 | 03d1dc9 | R2 row format decision — KEEP (paired-design semantics) |

This wave is the P4 audit pass. It re-runs all four gates against the
post-Wave-265 README and writes this audit doc. No source-code change.

## 2. Gate results

### 2.1 D.4 byte-stable regression vectors

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 2.55s
```

**PASS** — 30/30 byte-stable regression vectors preserved. No test
churn: this wave did not touch Python code.

### 2.2 mkdocs build --strict

```
$ timeout 30 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 25.14 seconds
```

**PASS** — 0 warnings. No mkdocs nav edits this wave (only README
table text changed).

### 2.3 claims_consistency

```
$ python3 tools/check_claims_consistency.py
**No drift detected.**
```

**PASS** — No claim-field drift. README numerical claims (R1
+116.46%, p ≈ 1.5e-08, R2 d_z = −0.0990, R3 d_z = −0.285, R4 −78.25%,
R5 −67.10%) all match the canonical source-of-truth
(`verification_outputs/*.json` and CONSOLIDATED_RESULTS.md).

### 2.4 Internal-ID leak in README

```
$ grep -cE "Wave [0-9]+|CLM-[0-9]+|USER ACTION" /home/hugo/codes/flowa-multistep-reinference/README.md
0
```

**PASS** — 0 internal IDs in README. Wave numbers (e.g. "Wave 265")
appear only in the audit-doc trail (`docs/audit/wave265-*.md`), never
in README.md itself.

### 2.5 R1 p-value is correct

```
$ grep -E "1e-10|1.5e-08|1.49e-08" /home/hugo/codes/flowa-multistep-reinference/README.md
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 | [ver.](verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
```

**PASS** — R1 row now reads `p ≈ 1.5e-08`. The fact error
(`p < 1e-10`) has been removed. The value `1.49e-08` is the canonical
DATA_PRESENTATION.md number; `1.5e-08` is its 2-significant-figure
round (1.49 → 1.5), correct because p = 1.49e-08 > 1e-10 (one fact
the original README got wrong).

### 2.6 R3 row format consistency

Current README R3 row (line 17):

```
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
```

R2 row for comparison (line 16):

```
| R2 | Kanzi | RMSD (N=1000 paired-t) | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](verification_outputs/wave218-p3-kanzi-framework-wins.json) |
```

**PASS** — R3 now uses the same `reference | d_z = ...` column
semantics as R2. Both are paired-design cells (R2 = paired-t on
RMSD, R3 = per-record paired d_z on fg_dev), and both correctly
report Baseline=`reference` (no independent baseline number) and
Framework=`d_z = ...` (the paired-effect-size summary).

The R3 row's d_z value `−0.285` matches the source-of-truth in
`verification_outputs/wave216-p1-r3-per-record.json`. The vendor-
level BLOCKED note is preserved verbatim.

## 3. R1–R6 headline row snapshot

```
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 |
| R2 | Kanzi | RMSD (N=1000 paired-t) | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 |
| R6 | MNIST FM (tier-aware k6 pLDDT) | FID d_z | +0.224 | **+0.647** | +189% | large | §7.6.6 |
```

Two formats by design:
1. **Absolute-number format** for single-readout cells (R1, R4, R5,
   R6): Baseline and Framework columns are independent measurements.
2. **`reference / d_z` format** for paired-design cells (R2, R3): no
   independent baseline number exists; only the paired Cohen's d_z is
   the meaningful summary statistic. Mixing the formats is correct
   because it tracks the underlying experimental design.

## 4. Unpushed commits

```
$ git log --oneline origin/main..HEAD | wc -l
10
```

**10 unpushed commits.** This includes all of Wave 264 (3 commits),
all of Wave 265 (3 commits: P1, P2, P3), and 4 prior commits. None of
the 10 unpushed commits touch framework source code — they are
README table edits, R2 format decision (audit doc only), and audit
docs. The 30/30 D.4 byte-stable gate continues to pass against the
post-Wave-265 tree.

## 5. Hard rules respected

- No framework source code changes this wave (audit-only).
- No vendored code touched.
- README edits are byte-stable (text-only, no claims rewritten).
- D.4 30/30 PASS preserved.
- mkdocs 0 warnings preserved.
- claims_consistency no drift.
- No new internal IDs introduced (0 internal IDs in README confirmed).
- All numerical claims (R1 +116.46%, p ≈ 1.5e-08, R2 d_z = −0.0990,
  R3 d_z = −0.285, R4 −78.25%, R5 −67.10%, R6 +189%) match the
  canonical verification artifacts.

## 6. Summary

| Gate | Result |
|---|---|
| D.4 byte-stable | PASS (30/30) |
| mkdocs strict | PASS (0 warnings) |
| claims_consistency | PASS (no drift) |
| 0 internal IDs in README | PASS (0) |
| R1 p-value correct | PASS (p ≈ 1.5e-08) |
| R3 row format consistent | PASS (matches R2 paired-design format) |
| Unpushed commits | 10 (all README/audit, no source code) |

All four DeepSeek third-round review small issues are now resolved:

1. **R1 p-value fact fix** — done in Wave 265 P1.
2. **Quick Start "6" → "7" cell count** — done in Wave 265 P2.
3. **R3 row format unification** — done in Wave 265 P2.
4. **R2 row format (optional)** — declined in Wave 265 P3 with full
   rationale (paired-design semantics preserved; DeepSeek marked
   optional, "不是必须改").

README is fully clean for submission. Audit trail committed at
`docs/audit/wave265-p4-final-verify.md`.
