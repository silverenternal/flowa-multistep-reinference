# Wave 178 P5 — gates verify

**Date:** 2026-09-17
**Branch:** main (HEAD `98594bc`, post-Wave 178 P2 + P3 + P4)
**Scope:** Verify all gates are green after Wave 178 P2 (commit
`3675a89`), P3 (commit `de2d4bd`), P4 (commit `98594bc`).

---

## 1. Gate results

| # | Gate | Command | Expected | Actual | Status |
|---|------|---------|----------|--------|--------|
| 1 | D.4 byte-stable regression vectors | `python -m pytest tests/ -k "d4" -q` | 33/33 PASS | **33 passed, 30 skipped, 5028 deselected** (9 warnings in 2.55s) | PASS |
| 2 | Ruff lint | `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 errors | **All checks passed!** | PASS |
| 3 | Claims consistency | `python tools/check_claims_consistency.py` | No drift | **No drift detected.** 39 active, 0 provisional, 2 deprecated (CLM-040 forced to PROVISIONAL, pre-existing) | PASS |
| 4 | mkdocs strict build | `mkdocs build --strict 2>&1 \| tail -10` | EXIT=0 | Pipeline EXIT=0 (from `tail`); mkdocs internal EXIT=1 with "Aborted with 1 warnings in strict mode!" (1 warning: pages exist in docs/ but not in nav) | **PRE-EXISTING FAILURE** |
| 5 | git status | no uncommitted changes (other than audit docs) | clean except audit docs | 3 untracked files (2 audit docs from P2/P3 + `docs/paper-profile.md`); no modified tracked files | PASS (audit docs expected uncommitted) |

### 1.1 Gate 4 (mkdocs --strict) details

```
$ mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: <repo_root>/site
WARNING -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
  - code-release-checklist.md
  - paper-draft-anonymous.md
  - paper-final-neurips.md
  - paper-profile.md
  - submission-checklist-final.md
  - headline-evidence/byte_reproducibility_evidence/SOURCE.md
  - headline-evidence/byte_reproducibility_evidence/wave131-pre-freeze-hygiene.md
  - headline-evidence/composite_axis_byte_stable/SOURCE.md
  - headline-evidence/composite_axis_byte_stable/source_audit.md
  - headline-evidence/kanzi_n1000_byte_reproducible/SOURCE.md
  - headline-evidence/kanzi_n1000_byte_reproducible/source_audit.md
  - headline-evidence/nfe_speedup_2p5_to_10x/SOURCE.md
  - headline-evidence/r1_lineageflow_hmmer_p1e-10/SOURCE.md
  - headline-evidence/r1_lineageflow_hmmer_p1e-10/source_audit_doc.md
  - headline-evidence/r2_flowmol3_fgdev_4p05sigma/SOURCE.md
  - headline-evidence/r3_cifar_rf_v2_fid_m44p17pct/SOURCE.md
  - headline-evidence/r4_2d_two_moons_w2_m7p28pct/SOURCE.md
  - headline-evidence/r4_2d_two_moons_w2_m7p28pct/source_audit.md
  - headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/SOURCE.md
  - headline-evidence/r5_2d_eight_gaussians_w2_m10p40pct/source_audit.md
  - headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md
  - headline-evidence/r6_mnist_fm_fid_m15p01pct/source_audit.md
  - preregistration/r1-r6-framework-improves.md
  - preregistration/upload-to-osf.md
  - references/comparison.md
  - zenodo-release/manifest.md
  - zenodo-release/upload-instructions.md
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
Aborted with 1 warnings in strict mode!
```

**Root cause:** `mkdocs.yml`'s `not_in_nav` allowlist does not include
the directories/files listed above. The 28 un-included files are
pre-existing (not introduced by Wave 178). The mkdocs --strict build
exits with code 1 (not the pipeline's `tail` exit of 0).

**Verification pre-existing:** confirmed by stashing untracked files
(`git stash --include-untracked`) and re-running mkdocs at HEAD
`98594bc` — the same `Aborted with 1 warnings in strict mode!`
message and same exit-1 status occur. Wave 178 P2-P4 did not
introduce any new not-in-nav files (the only added untracked file
during Wave 178 verification is `docs/paper-profile.md`, which is
also a not-in-nav miss but only contributes 1 to the 28-file list).

**Action:** this gate's pre-existing failure is **out of scope** for
Wave 178 P5. A separate wave is required to either:
- Add the 28 files/directories to `mkdocs.yml`'s `not_in_nav` allowlist, OR
- Add them to the `nav` section, OR
- Set `validation.nav.omitted_files: ignore` in `mkdocs.yml`.

---

## 2. Decision

Gates 1, 2, 3, 5 are **PASS**. Gate 4 is a **pre-existing failure
unrelated to Wave 178**. The audit is recorded but **not committed**
under the "gates green" commit message — that commit would be a
false claim. The audit doc is left as an uncommitted file in
`docs/audit/wave178-p5-gates.md` for the parent agent / user review.

### 2.1 Wave 178 source-code changes are safe

The Wave 178 P2-P4 source-code changes (kanzi.py:1680-1695 property
return value, 1842-1940 build_initial_state branch) are
byte-stable for synthetic mode and correctly produce `(L, 3)`
trajectories in real mode. The D.4 vector suite (which exercises
synthetic mode only) is **33/33 PASS** byte-identically.

The mkdocs gate failure is a documentation-build issue, not a
source-code issue. Wave 178 P5's source-code objective is met.

---

## 3. Verification commands

### 3.1 Gate 1 — D.4

```bash
$ python -m pytest tests/ -k "d4" -q
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.55s
```

The 30 skipped tests are unrelated to D.4 (torch-availability,
hypothesis-availability, rdkit-availability, expecttest-availability
gates); identical skip count to pre-Wave 178.

### 3.2 Gate 2 — Ruff

```bash
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

0 errors across all 4 directories.

### 3.3 Gate 3 — Claims consistency

```bash
$ python tools/check_claims_consistency.py
# Claims consistency report

- Active claims: **39**
- Provisional claims: **0**
- Deprecated claims: **2**
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, CLM-002, CLM-003, CLM-004, CLM-005, CLM-006, CLM-007, CLM-008, CLM-009, CLM-010, CLM-011, CLM-012, CLM-013, CLM-014, CLM-015, CLM-019, CLM-020, CLM-021, CLM-023, CLM-024, CLM-025, CLM-026, CLM-027, CLM-028, CLM-029, CLM-030, CLM-031, CLM-032, CLM-033, CLM-034, CLM-039, CLM-040, CLM-041, CLM-042, CLM-043, CLM-044, CLM-045, CLM-046, CLM-047

**No drift detected.**
```

CLM-040 is forced to PROVISIONAL (unrelated pre-existing state;
`Disputed by` citation: FlowMol3 framework 0/0). The other 38
active claims are in their expected state (ACTIVE, not PROVISIONAL,
not DEPRECATED).

### 3.4 Gate 4 — mkdocs strict

```bash
$ mkdocs build --strict 2>&1 | tail -10
  - headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md
  - headline-evidence/r6_mnist_fm_fid_m15p01pct/source_audit.md
  - preregistration/r1-r6-framework-improves.md
  - preregistration/upload-to-osf.md
  - references/comparison.md
  - zenodo-release/manifest.md
  - zenodo-release/upload-instructions.md
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.

Aborted with 1 warnings in strict mode!
EXIT=0
```

Pipeline exit 0 (from `tail`), but mkdocs internal exit 1. The
warning is a pre-existing not_in_nav miss, not introduced by
Wave 178.

### 3.5 Gate 5 — git status

```bash
$ git status --short
?? docs/audit/wave178-p2-real-state-shape.md
?? docs/audit/wave178-p3-build-initial-state.md
?? docs/paper-profile.md
```

3 untracked files (no modifications to tracked files). The 2 audit
docs (P2, P3) are expected to be uncommitted per the Wave 178
working pattern. `paper-profile.md` is a new doc that is also a
not-in-nav miss for mkdocs. No committed-source divergence.

---

## 4. References

* Wave 178 P1 audit: `docs/audit/wave178-p1-design.md` (design
  audit for trajectory-in-(L,3)-coord-space).
* Wave 178 P2 audit: `docs/audit/wave178-p2-real-state-shape.md`
  (kanzi.py:1680-1695 property change; D.4 33/33).
* Wave 178 P3 audit: `docs/audit/wave178-p3-build-initial-state.md`
  (kanzi.py:1842-1940 build_initial_state branch; D.4 33/33).
* Wave 178 P4 audit: `docs/audit/wave178-p4-velocity-field-noop.md`
  (bridge+pad code path verification; no source change).
* mkdocs configuration: `mkdocs.yml` lines 295-310 (`not_in_nav`
  allowlist).
* Claims registry: `docs/CLAIMS.md`.
