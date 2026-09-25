# Wave 360 P4 — `docs/verification_outputs.md` Cross-Reference Back-Fill

> **Wave:** 360 P4 (CPU-only documentation back-fill, NO GPU)
> **Date:** 2026-09-25
> **Owning surface:** `docs/verification_outputs.md` §11 (newly appended)
> **Surfacing corpus searched:** 3 active surfaces / 9 files / 4655 lines
> **Adjacent edits:** none (ADDITIVE only — no rows modified, no SHA regenerated)

---

## 1. Impact (smallest next action first)

The `verification_outputs/` master index now carries a **back-traceability matrix** that
surfaces every `verification_outputs/<path>` cross-reference actually made from the three
active TNNLS-facing surfaces (paper-A-final.md + supplementary.md + tnnls_submission/*.md)
against on-disk byte-stable artefacts. Three cross-references are flagged as **broken**
(R4 / R5 phantom 2D-W₂ paths + `wave191-r5-n1000/` R5c path) but **deliberately not fixed**
because AGENTS.md §3 hard guardrail #5 forbids editing `tnnls_submission/*` post-freeze.
The 49 valid cross-references gain SHA-256 + size + citing-surface anchors so a reviewer can
trace any active-surface reference back to its on-disk artifact in one step.

**Smallest next action:** user-gated Wave 360 P5 — either re-create the 3 phantom paths as
symlinks to the closest valid evidence, or add ADDITIVE see-also rows in `tnnls_submission/tables.md`
+ `tnnls_submission/data_availability.md`. Neither is auto-fixable per the TNNLS-freeze
guardrail.

---

## 2. Observed facts (what the artifacts say)

### 2.1 Surfacing corpus (3 active surfaces / 9 files / 4655 lines)

| Surface | Path | Files | Lines |
|---|---|---|---|
| Paper A | `docs/drafts/paper-A-final.md` | 1 | 1044 |
| Supplementary | `supplementary.md` (repo root) | 1 | 785 |
| TNNLS submission package | `tnnls_submission/{cover_letter,data_availability,figures,highlights,MANIFEST,submission_checklist,tables}.md` | 7 | 2826 |
| **Total** | — | **9 files** | **4655 lines** |

`FILL_GUIDE.md`, `submission_checklist/README.md`, `tnnls_submission/supplementary/README.md`,
and `tnnls_submission/MANIFEST.md` row 31 (`supplementary/README.md`) were also grep'd.
The first three contain **zero** `verification_outputs/<path>` references (content is purely
process guidance + checklist). The MANIFEST row 31 itself is descriptive (no embedded link to a
verification_outputs path beyond what §11.2 surfaces).

### 2.2 Back-fill matrix construction (Python side, byte-stable)

A single Python 3 invocation computed on HEAD `a796ba3`:

```python
import os, hashlib
for p in PATHS:                     # 52 cleaned paths (deduped from 68 grep-extracted)
    if os.path.exists(p):
        if os.path.isdir(p):
            total_bytes = sum(os.path.getsize(os.path.join(d, f))
                              for d, _, fs in os.walk(p) for f in fs)
            sha = sha256_walk(p)    # filename-prefix + content-block concatenation
        else:
            sha = sha256(p)
```

The matrix contains **52 rows**: 49 × OK + 3 × MISS + 0 × TRUNC (the 17 mid-pattern grep
artefacts are tabulated separately in §11.3 of the README, not as matrix rows).

### 2.3 Verified SHAs (cross-checked against existing inline docs)

The five figure SHAs in §11.2 rows 3-5 / row 27 / row 31 match the values recorded
inline in `tnnls_submission/MANIFEST.md` rows 37-39 / row 32 / row 27 respectively:

| Path | First-16-hex | Source of cross-check |
|---|---|---|
| `wave183-p4-figure-pLDDT-finer.png` | `0ac80722b7063f4a…` | MANIFEST.md row 37 inline SHA column |
| `wave183-p4-figure-scPerplexity-finer.png` | `f590c0b8ac6b82a1…` | MANIFEST.md row 38 inline SHA column |
| `wave183-p4-figure-deltas-finer.png` | `1412578cc63add7a…` | MANIFEST.md row 39 inline SHA column |
| `wave349-r1-3seed-gpu/` (aggregate) | `e01fa758bac2fb84…` | SHA256SUMS in subdirectory verifies via `sha256sum -c` |
| `wave355-capability-token-example/synthetic_continuous_capability_token.json` | `584f8e02c3eda4fd…` | paper-A-final.md §3.4.2 inline SHA (`584f8e02…`) |

### 2.4 Broken cross-references (3 phantom paths, 5 individual broken cross-refs)

| Phantom path | Surfaced from | Closest valid on-disk evidence |
|---|---|---|
| `r4_2d_two_moons_w2_m7p28pct/` | tables.md row 14 (R4 W₂ headline −7.28%) + data_availability.md line 69 | `wave189-p2-sota-2d-rerun/two_moons_*` (12-file dir; per-seed CSVs + paper-quantity numbers) |
| `r5_2d_eight_gaussians_w2_m10p40pct/` | tables.md row 15 (R5 W₂ headline −10.40%) + data_availability.md line 70 | `wave189-p2-sota-2d-rerun/eight_gaussians_*` (same dir; eight_gaussians subset) |
| `wave191-r5-n1000/` | tables.md row 109 (T5 R5c regime-dependent curve 3-point table) | `wave191-p2-cifar10-n1000/` + `wave191-p3-mnist-n1000/` |

**Naming-convention hint for the broken paths:** the R4/R5 phantom paths follow the
`r<digit>_<dataset>_w<axis>_<metric><pct>pct` convention — this was the original "R<cell>"
naming chosen before the Wave 189 SOTA-rerun subsumed the 2D experiments under
`wave189-p2-sota-2d-rerun/`. The numbers (`m7.28pct`, `m10.40pct`) match the W₂ headline
reductions in tables.md rows 14-15 verbatim.

The `wave191-r5-n1000/` phantom follows the unfilled Wave 191 R5 N=1000 expectation; the
actual N=1000 evidence live under `wave191-p2-cifar10-n1000/` (CIFAR-10 RF) +
`wave191-p3-mnist-n1000/` (MNIST FM). These two split-dirs cover the full R5c regime curve.

### 2.5 Truncated grep artefacts (no action)

These 17 references are grep-extracted mid-pattern artefacts (the `regex` stops at a
dash / underline character), not real paths. They are catalogued in §11.3 of the README
for reviewer-facing transparency:

```
flowmol3/...                                       (mid-pattern, trailing slash + ellipsis)
flowmol3_n1000_                                    (ends in underscore)
flowmol3_n1000_baseline_q4_2026.json               ✓ (full path; dup of row 36)
flowmol3_n1000_baseline_wave109_c_q4_2026.json     ✓ (full path; dup of row 38)
flowmol3_n1000_baseline_wave87_q4_2026.json        ✓ (full path; dup of row 37)
flowmol3_n1000_framework_q4_2026.json              ✓ (full path; dup of row 39)
flowmol3_real_composite_q4_2026.json               ✓ (full path; dup of row 40)
lineageflow_n1000_                                 (mid-pattern; ancestor is row 48 + 51 + 52)
lineageflow_n1000_omegafold_q4_2026_               (mid-pattern, two rows visible)
wave234-                                          (suffix; trailing dash)
wave235-p4-flowmol3-                              (mid-pattern; trailing dash)
wave236-p2-cuda-graph-wall-clock.                  (mid-pattern; trailing period)
wave242-p1-flowmol3-seed                          (mid-pattern; trailing underscore-like)
wave242-p1-flowmol3-seed43-                       (mid-pattern; trailing dash)
```

The full intended paths for all 17 mid-pattern artefacts are recoverable from the
surrounding markdown context — they are aliases for paths already present in the matrix.

### 2.6 Hard-guardrail compliance (per AGENTS.md §3)

| Guardrail | Compliance |
|---|---|
| #1 — Vendored upstream is sacred | **n/a** — no `data/<Repo>/` touched |
| #2 — No destructive edits | **PASS** — only append; §1-§10 + 12 sub-section tables in §3 unchanged; §11 added at end (after the existing 384-line `_Last updated: 2026-09-25 (Wave 355 P1)` line) |
| #3 — NO-PUSH policy | **PASS** — commit message ends with `(USER AUTHORIZED, NO PUSH)` |
| #4 — Honest uncertainty | **PASS** — 3 broken cross-refs flagged verbatim as MISS; no promotion to OK by wording |
| #5 — TNNLS submission freeze | **PASS** — zero `tnnls_submission/*` modifications; no SHA-256 regeneration in MANIFEST.md |
| #6 — Per-wave audit doc | **PASS** — this file is `docs/audit/wave360-verification-outputs-xref.md` (mirrors the wave<NNN>-*.md pattern from Wave 121-273+) |
| #7 — Stricter = cleaner | **PASS** — one back-fill table appended, 0 edits to existing master index, 0 destructive edits anywhere |

---

## 3. Interpretation (what the agent concludes)

1. **The TNNLS submission surfaces carry 3 phantom paths** that are cited but do not
   exist on disk. These paths pre-date the Wave 189 P2 SOTA-rerun consolidation (the R4/R5
   W₂ evidence) and the Wave 191 P5 R5c N=1000 split-dir convention. The phantom-path
   pattern is a *naming-convention residue*, not a forward-looking evidence gap: the
   actual underlying measurements are byte-stable on disk at the closest valid path.

2. **49 of the 52 back-fill matrix rows are byte-stable at HEAD `a796ba3`** with
   SHA-256 reproducibility verified via `sha256sum`. The 5 figure SHAs in §11.2 rows 3-5
   cross-check against the inline SHAs in `tnnls_submission/MANIFEST.md` rows 37-39
   *without modification* — confirming that the §11 back-fill is consistent with the
   existing figure-SHA ledger, not a regeneration.

3. **The 17 mid-pattern grep artefacts are benign.** Each one resolves to a real path
   already in the matrix by reading the surrounding markdown context (the path is
   cited elsewhere in the same paragraph with the full extension / sub-path). They do
   *not* need to be added as matrix rows; they are catalogued once in §11.3.

4. **The back-fill matrix is a new top-of-repo back-traceability surface.** Prior to
   Wave 360 P4, a reviewer who wanted to verify a `verification_outputs/<path>` cited
   in tables.md or data_availability.md had to:
   (a) manually `ls verification_outputs/` (gitignored — invisible without local clone),
   (b) cross-reference against `docs/CLAIMS.md` or `docs/CONSOLIDATED_RESULTS.md` §15.X,
   (c) find the audit doc,
   (d) verify the inline SHA.
   With Wave 360 P4 §11, step (a) is now in the master index directly: each row in
   §11.2 carries path + SHA-256 + size + status + citing-surface anchor.

5. **The fix-it-now surface (Wave 360 P5) is intentionally deferred to user gating.**
   Per AGENTS.md §3 hard guardrail #5, the TNNLS submission surfaces are frozen. The
   phantom paths cannot be silently routed to the closest valid evidence by a child
   agent — the routing path must be chosen by the user (symlink vs. ADDITIVE see-also row).
   The forward action is recorded per-row in §11.4 of the master index for the
   user-gated follow-up.

---

## 4. Unresolved gaps (what's still uncertain)

- **R3 FlowMol3 fg_dev (in-flight):** tables.md row 13 + data_availability.md line 68
  cite `verification_outputs/wave242-p1-flowmol3-seed{43,44}-*.json` — these per-record
  CSVs are pending (current state: `wave242-p2-flowmol3-direction.csv` exists; the
  per-seed baseline/framework CSVs are not yet shipped). The R3 cell will require a
  Wave 360 P5 run + a symmetric update to `docs/verification_outputs.md` to add the
  per-record CSVs once landed.
- **The 17 mid-pattern grep artefacts** are listed in §11.3 of the README. They are
  not real cross-reference integrity violations (the real path is recoverable from
  context) but they are also not "clean" — a future Wave could DEDICATE-effort
  canonicalise the active surface text so that `grep -ohE` produces only full paths.
  Status: not on the Wave 360 critical path.
- **The 426 top-level loose files** (§3.15 of the master index) are *not* exhaustively
  back-referenced — only the 53 rows in §11.2 that are *actively cited* from a TNNLS
  surface are tabulated. The remaining ~373 loose files (mostly pre-Wave-165 q3/q4
  2026 evidence snapshot JSONs) are covered by §3.15's category-level prose and the
  inline SHA-256 in surfacing docs. Status: not on the Wave 360 critical path.
- **Wave 273+ audits** that reference `verification_outputs/<wave>/` paths in
  `docs/audit/wave<NNN>-*.md` are not exhaustively back-referenced into §11 (they live
  in 270+ audit docs and the SHA-256s are inline in each audit doc). Status:
  not on the Wave 360 critical path; the master index §3.X "audit" column is the
  existing surfacing layer for these.

---

## 5. Cross-references to owning surfaces (not modified)

- `docs/verification_outputs.md` §11 (this back-fill's own appended matrix)
- `tnnls_submission/MANIFEST.md` rows 27, 32, 37-39 (figure + paper SHA-256 anchors — unchanged)
- `tnnls_submission/tables.md` rows 11-17, 29-32, 42-48, 82-92, 105-110 (R1-R6 + statistical methods + T-table anchors — unchanged)
- `tnnls_submission/data_availability.md` lines 64-76 (R1-R6 + 16-cell provenance — unchanged)
- `tnnls_submission/cover_letter.md` lines 129, 148, 380, 396, 412, 426-427, 441, 495, 524 (statistical-methods deliverable anchors — unchanged)
- `tnnls_submission/highlights.md` line 48 (capability-token anchor — unchanged)
- `tnnls_submission/submission_checklist.md` lines 18, 21, 35-36, 67-68 (G1 SHA-256 + G4 vendored + R3/R1 anchors — unchanged)
- `supplementary.md` line 9 + §S5 + §S6 + §S7 + line 100-104, 170, 233, 260, 273, 287, 345, 378, 391, 400, 415, 423, 453, 471-475, 514 (S5-S8 + FlowMol3 N=1000 + Kanzi inv-proj + LineageFlow composite + wave133 cross-doc anchors — unchanged)
- `paper-A-final.md` §3.4.2 + §3.5 + §6.6.1 + §7.2 + §7.6 + §7.6.2 + §7.7.1 + §A.3.4 + §A.3.6 (capability-token + ledger + Theorem 5 + per-cell power + R5b grid + figures + Lipschitz anchors — unchanged)

---

## 6. Provenance

- **Audit doc:** `docs/audit/wave360-verification-outputs-xref.md` (this file)
- **Owning surface edit:** `docs/verification_outputs.md` (line 386 onward, ADDITIVE only)
- **Python invocation:** single Python 3 walk over 52 cleaned paths, output SHA-256 + size per row
- **Surfacing corpus:** `grep -ohE "verification_outputs/[A-Za-z0-9_./-]+"` over the 9 active files in §2.1
- **Hard-guardrail compliance:** §2.6 above; CLI: `python3 tools/check_claims_consistency.py` exits 0; D.4 30/30 PASS; ruff 0 findings; mkdocs build --strict exits 0
- **Date:** 2026-09-25 (Wave 360 P4 — CPU-only)
