# Wave 363 P1.R1 — R1 LineageFlow HMMER retro-validation reproducibility recipe

**Date:** 2026-09-27
**Author:** Wave 363 P1.R1 R1-recipe agent (USER AUTHORIZED, NO PUSH)
**Status:** ACTIVE — R1 LineageFlow HMMER retro-validation evidence chain (`verification_outputs/wave349-r1-3seed-gpu/`) is now documented at paper-citation convenience in `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` with SHA-256 anchors + bash/Python reproducibility recipes + honest status disclosure (PARTIAL / single-seed-disclosed preserved verbatim per Wave 268 strict-clean).
**Trigger:** Wave 363 P1.R1 task brief — author `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` for the R1_LineageFlow_HMMER cell using the Wave 349 P1 + P4 GPU retro-validation evidence + canonical SHA-256 ledger at `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS`.
**Scope:** ADDITIVE — (1) one new recipe doc (`paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md`); (2) one new audit doc (this file); (3) NO edits to existing paper-data files (the existing K4 recipe at `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` from Wave 363 P1.K4 is preserved verbatim, SHA `8c46e87`); (4) NO edits to `verification_outputs/wave349-r1-3seed-gpu/` evidence chain (byte-stable).
**Hard-rule compliance:** AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) — vendored upstream untouched (no edits to `data/<repo>/`); no destructive edits (additive-only — single new recipe doc, single new audit doc, no edits to existing paper-data files); NO-PUSH policy (commit-only; no `git push`); honest uncertainty preserved (R1 PARTIAL / single-seed-disclosed status preserved verbatim per Wave 308 P1 demotion + Wave 268 strict-clean; Wave 349 P1 + P4 retro-validation disclosed as falsification of Wave 280 P framework-fallback contamination, NOT as promotion of R1 verdict); TNNLS submission freeze preserved (no edits to `tnnls_submission/`); per-phase audit doc (this file); stricter-cleaner path chosen (new file `R1_REPRODUCIBILITY_RECIPE.md` rather than overwriting the existing K4 recipe at `REPRODUCIBILITY_RECIPE.md` — preserves both cells).

**Out of scope (deliberately):**
- No edits to `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` (Wave 363 P1.K4 deliverable, SHA `8c46e87`, byte-stable).
- No edits to `paper-data/K4_k5_lineageflow_hmmer/K4_k5_SOURCE.md` (the K4+K5 source provenance doc; preserved verbatim).
- No edits to `paper-data/K4_k5_lineageflow_hmmer/SHA256SUMS` (symlink to `verification_outputs/wave280-p-k4k5/SHA256SUMS`, byte-stable).
- No edits to `paper-data/K4_k5_lineageflow_hmmer/summary_n100.json` (symlink to `verification_outputs/wave280-p-k4k5/summary_n100.json`, byte-stable).
- No edits to `verification_outputs/wave349-r1-3seed-gpu/*` (3 byte-stable files: `seed42_manifest.json` SHA `0861e4b1...`, `seed44_manifest.json` SHA `cc4390bc...`, `SHA256SUMS` SHA `28aafe1c...`).
- No edits to `docs/CLAIMS.md` CLM-060 R1 row wording or status (Wave 308 P1 PARTIAL / single-seed-disclosed preserved verbatim).
- No edits to `docs/drafts/paper-A-final.md` §3.5.1 R1 3-seed ledger example (already anchors the SHA-256 chain at line 186-200).
- No edits to any vendored upstream repo (the 9 vendored repos in `data/` remain byte-identical to upstream pinned commits).
- No edits to `tnnls_submission/` (TNNLS submission freeze preserved per AGENTS.md §3 hard guardrail #5).
- No edits to the prior R1 audit trail (`docs/audit/wave349-r1-3seed-gpu.md`, `docs/audit/wave349-impl.md`, `docs/audit/wave349-gpu-acceleration.md`, `docs/audit/wave349-gap-audit.md`, `docs/audit/wave280-p-r1-sweep-result.md`).
- No live GPU re-verification (per Wave 349 P4 §3.3 caveat; the Wave 349 P1 + P4 evidence is already byte-stable).
- No `git push` (per Wave 325 NO-PUSH policy + AGENTS.md §3 guardrail #3).

---

## 1. Executive Summary

The R1 LineageFlow HMMER cell is **now documented at paper-citation convenience** in `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` (167 lines, SHA-256 `98a869c2a4af00eaf5b2fd89c02f66eb80974728322e425079346c0675a57088`) with **SHA-256-anchored evidence chain** + **bash/Python reproducibility recipes** + **honest status disclosure** (R1 PARTIAL / single-seed-disclosed preserved verbatim per Wave 268 strict-clean + Wave 308 P1 demotion).

| Headline | Value | Source |
|---|---|---|
| **R1 3-seed retro-validated zero-fallback (seed=42)** | `framework_fallback_per_family_count = {}` (N=1000, 4 × 250 records) | `verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json` (SHA `0861e4b1...`) |
| **R1 3-seed retro-validated zero-fallback (seed=44)** | `framework_fallback_per_family_count = {}` (N=1000, 4 × 250 records) | `verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json` (SHA `cc4390bc...`) |
| **R1 3-seed retro-validated zero-fallback (seed=43)** | `framework_fallback_per_family_count = {}` (N=1000, per Wave 349 gap-audit §2.3) | Wave 349 P1 synthetic-mode retro-validation (~23 min wallclock; manifest NOT collected at verification_outputs/, referenced in `wave349-r1-3seed-gpu/SHA256SUMS` text) |
| **Wave 280 P framework-fallback contamination claim** | **FALSIFIED** at the current toolchain (Wave 349 P1 + P2 + P4) | `docs/audit/wave349-gap-audit.md` §2.3 + `docs/audit/wave349-gpu-acceleration.md` §3.1 |
| **R1 paper R-level verdict** | **PARTIAL / single-seed-disclosed** (preserved verbatim) | `docs/CLAIMS.md` CLM-060 line 3032 (Wave 308 P1 demotion) |
| **R1 retro-validation methodology** | **GPU torch-mode + cuda:0 dispatch** (`force_mode="auto"`) | `tools/gen_lineageflow_n1000_fastas.py:419` (Wave 349 P4) |
| **R1 retro-validation wall-clock** | ~11 min per seed on contended GPU 0 (clean GPU 0 estimate: ~5 min) | `wave349-r1-3seed-gpu/SHA256SUMS` text |
| **Reproducibility standard** | **SHA-256-anchored + bash/Python recipes + PARTIAL status preserved** | `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` |

The R1 retro-validation is documented at the **highest reproducibility standard for a falsification-evidence paper cell**: every headline invariant (`framework_fallback_per_family_count = {}`) is traceable to a SHA-256-anchored artefact, reproducible by GPU torch-mode + cuda:0 dispatch (CPU fallback is byte-stable on CUDA-less hosts), with the Wave 280 P contamination-claim falsification disclosed verbatim and the R1 PARTIAL / single-seed-disclosed paper verdict preserved unchanged per Wave 268 strict-clean rule.

---

## 2. Observed Facts

### 2.1 SHA-256 inventory (recipe + 3 evidence files)

Per-file SHA-256, size, and status (verified at Wave 363 P1.R1 audit time):

| # | File | Size (bytes) | SHA-256 | Status |
|---|---|---|---|---|
| 1 | `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` | 9780 | `98a869c2a4af00eaf5b2fd89c02f66eb80974728322e425079346c0675a57088` | PRESENT (Wave 363 P1.R1 deliverable, NEW) |
| 2 | `verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json` | 805 | `0861e4b156c1e64078f56561c093dfe10e22542aa9740efbb8f4a61d76552ce7` | PRESENT (Wave 349 P4 evidence — matches §3.5.1 paper anchor) |
| 3 | `verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json` | 805 | `cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed` | PRESENT (Wave 349 P4 evidence — matches §3.5.1 paper anchor) |
| 4 | `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS` | 2642 | `28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2` | PRESENT (Wave 349 aggregator — matches §3.5.1 paper anchor at line 197) |

### 2.2 Bash verification (audit-time execution, 2026-09-27)

```bash
# Targeted SHA-256 verification of headline manifests (recipe §(b) command 1)
$ sha256sum -- verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json \
             verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json
0861e4b156c1e64078f56561c093dfe10e22542aa9740efbb8f4a61d76552ce7  verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json
cc4390bc4a02799dc2add0ad251e7e5ece08e29f1ec2322c8c6f28f813cf44ed  verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json

# Targeted SHA-256 verification of aggregator (recipe §(b) command 2)
$ sha256sum -- verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS
28aafe1c95195c0a2daa727150e4ea42651daa49cd5872443a81b88cfed15be2  verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS

# Cross-check the framework_fallback_per_family_count = {} invariant (recipe §(b) command 3)
$ python3 -c "
import json
for seed in [42, 44]:
    d = json.load(open(f'verification_outputs/wave349-r1-3seed-gpu/seed{seed}_manifest.json'))
    assert d['n'] == 1000, f'seed={seed} expected n=1000, got {d[\"n\"]}'
    assert d['framework_fallback_per_family_count'] == {}, f'seed={seed} expected empty fallback, got {d[\"framework_fallback_per_family_count\"]}'
    print(f'PASS: seed={seed} framework_fallback_per_family_count = {{}} at N={d[\"n\"]}')
"
PASS: seed=42 framework_fallback_per_family_count = {} at N=1000
PASS: seed=44 framework_fallback_per_family_count = {} at N=1000
```

All 3 verification commands executed cleanly at audit time. The headline invariant `framework_fallback_per_family_count = {}` for both seeds 42 and 44 is preserved across the SHA-256 chain.

### 2.3 Pre-submission gate status (audit-time execution, 2026-09-27)

| Gate | Expected | Actual |
|---|---|---|
| `python3 -m pytest tests/test_d4_regression_vectors.py -q` | 30/30 PASS | **30 passed** in 5.12s |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings | **All checks passed** |
| `python3 tools/check_claims_consistency.py` | No drift detected | **No drift detected.** |
| `mkdocs build --strict` | EXIT=0 | **Documentation built in 26.32 seconds** |

All 4 pre-submission gates PASS at audit time. The Wave 363 P1.R1 recipe doc does NOT touch any test/claims/markdown surface that the gates verify, so the audit-time gate state matches the prior commit state.

---

## 3. Interpretation

The R1 retro-validation recipe is **a falsification-evidence documentation deliverable**, not a verdict-promotion deliverable. Per Wave 308 P1 demotion + Wave 268 strict-clean "no number change" rule, the R1 paper R-level verdict remains **PARTIAL / single-seed-disclosed** (single-seed seed=42, d_z=+0.182, p_raw=1.25e-8, Bonferroni-significant at observed δ, single-seed granularity). The Wave 349 P1 + P4 retro-validation proves the Wave 280 P framework-fallback contamination claim is **not reproducible on the current toolchain** (`tools/gen_lineageflow_n1000_fastas.py` with `force_mode="auto"` + cuda:0 dispatch), but it does NOT prove the contamination never occurred on the Wave 280 P toolchain (which is not preserved). The 3-seed-pool aggregation `d_z` materialisation that would re-promote R1 to STRONG is **camera-ready scope** (next wave, 2-4h wall-clock with GPU dispatch).

The recipe is honest about its scope: §(d) Disclosure explicitly preserves the PARTIAL / single-seed-disclosed status verbatim, notes the tool-version-bounded falsification, and flags the seed=43 manifest as not-collected-at-verification-outputs (only referenced in `wave349-r1-3seed-gpu/SHA256SUMS` text). No promotion by wording, no fabrication of numbers, no destructive edits to existing paper-data files (the existing K4 recipe at `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` is preserved verbatim from commit `8c46e87`).

The R1 cell now has **the same reproducibility standard** as the R5a / R5b / R5c / R6 cells (Wave 363 P1.{R5a,R5b,R5c,R6} + Wave 362 P1.R6): SHA-256-anchored evidence chain + bash/Python reproducibility recipes + honest status disclosure per Wave 268 strict-clean. The recipe is safe to run in CI (CPU-only verification of the JSON manifests and the SHA-256 chain is sub-second; the GPU torch-mode path is documented for completeness and can be skipped in CI).

---

## 4. AGENTS.md hard guardrail compliance

1. **Vendored upstream is sacred** — no vendored file touched (recipe doc + audit doc only). ✓
2. **No destructive edits** — single new recipe doc + single new audit doc; no edits to existing paper-data files (the K4 recipe at `REPRODUCIBILITY_RECIPE.md` is preserved verbatim from commit `8c46e87`); no edits to `verification_outputs/wave349-r1-3seed-gpu/*` (byte-stable). ✓
3. **NO-PUSH policy** — local commit only; no `git push`. ✓
4. **Honest uncertainty** — R1 PARTIAL / single-seed-disclosed status preserved verbatim per Wave 308 P1 demotion + Wave 268 strict-clean; Wave 349 P1 + P4 retro-validation disclosed as falsification of Wave 280 P framework-fallback contamination, NOT as promotion of R1 verdict; tool-version-bounded caveat preserved. ✓
5. **TNNLS submission freeze** — no edits to `tnnls_submission/` files; the recipe + audit doc are paper-data + docs/audit additions only. ✓
6. **Per-phase audit doc** — this file follows the observed-facts / interpretation / gaps format from Wave 188-363 (12-decimal-CLAIMS-table pattern from Wave 121-273). ✓
7. **Stricter = cleaner** — chose the additive-only path (new file `R1_REPRODUCIBILITY_RECIPE.md`) over the destructive path (overwriting the existing K4 recipe at `REPRODUCIBILITY_RECIPE.md`); preserved the K4 cell's separate provenance; both cells now have distinct, byte-stable recipe docs. ✓

---

## 5. Cross-references

* `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` — NEW recipe doc (167 lines, SHA-256 `98a869c2a4af00eaf5b2fd89c02f66eb80974728322e425079346c0675a57088`).
* `paper-data/K4_k5_lineageflow_hmmer/REPRODUCIBILITY_RECIPE.md` — EXISTING K4 recipe (185 lines, preserved verbatim from commit `8c46e87`, Wave 363 P1.K4 deliverable).
* `verification_outputs/wave349-r1-3seed-gpu/SHA256SUMS` — canonical 3-file SHA-256 ledger (anchor: `28aafe1c...`).
* `verification_outputs/wave349-r1-3seed-gpu/seed42_manifest.json` — seed=42 N=1000 retro-validation manifest (SHA `0861e4b1...`).
* `verification_outputs/wave349-r1-3seed-gpu/seed44_manifest.json` — seed=44 N=1000 retro-validation manifest (SHA `cc4390bc...`).
* `docs/audit/wave349-r1-3seed-gpu.md` — Wave 349 P1 + P4 audit doc (canonical provenance).
* `docs/audit/wave349-gpu-acceleration.md` — Wave 349 P4 GPU dispatch audit doc (cuda:0 + force_mode="auto").
* `docs/audit/wave349-gap-audit.md` — Wave 349 gap audit §2.3 (R1 3-seed retro-validation: VERIFIED on current toolchain).
* `docs/audit/wave349-impl.md` — Wave 349 implementation audit doc (P1 + P3 + P4 governance).
* `docs/audit/wave280-p-r1-sweep-result.md` — Wave 280 P R1 3-seed sweep result (the original 3-seed sweep that the retro-validation falsifies).
* `docs/CLAIMS.md` CLM-060 line 3031 + line 3032 — Wave 280 P status addendum + Wave 308 P1 R1 demotion (preserved verbatim).
* `docs/drafts/paper-A-final.md` §3.5.1 (line 180-200) — Wave 349 R1 3-seed ledger example (byte-addressable SHA-256 chain at the paper surface).
* `tools/gen_lineageflow_n1000_fastas.py:419` — Wave 349 P4 `force_mode="auto"` CLI-default change.
* `adaptive_reflow/adapters/lineageflow.py:1393-1427` — Wave 349 P4 cuda:0 dispatch.
* `reproduce/01_R1_LineageFlow.sh` — existing R-level per-cell reproduction script (Wave 158 P2 +116% single-seed seed=42 baseline verifier).

---

## 6. Acceptance criteria

- New recipe doc `paper-data/K4_k5_lineageflow_hmmer/R1_REPRODUCIBILITY_RECIPE.md` authored (167 lines): ✓ (§2.1 row 1)
- New audit doc `docs/audit/wave363-r1-recipe.md` authored (this file): ✓
- SHA-256 chain verified for the 3 evidence files at audit time (recipe §(b) commands 1+2): ✓ (§2.2)
- Cross-check python command runs cleanly for both seeds 42 + 44 (recipe §(b) command 3): ✓ (§2.2)
- Pre-submission gates PASS at audit time (D.4 30/30 + claims PASS + ruff 0 + mkdocs strict EXIT=0): ✓ (§2.3)
- ADDITIVE only — no edits to existing paper-data files, no edits to verification_outputs/, no edits to vendored upstream: ✓ (§4 hard guardrails)
- NO-PUSH policy observed — local commit only, no `git push`: ✓ (§4 hard guardrail #3)
- Honest uncertainty preserved — R1 PARTIAL / single-seed-disclosed status verbatim, Wave 280 P falsification disclosed as falsification (not promotion): ✓ (§4 hard guardrail #4 + §3 interpretation)
- TNNLS submission freeze preserved — no edits to `tnnls_submission/`: ✓ (§4 hard guardrail #5)
- Per-phase audit doc — this file follows the observed-facts / interpretation / cross-references / acceptance-criteria pattern from Wave 188-363: ✓ (§§1-6)

---

_Last updated: 2026-09-27 (Wave 363 P1.R1 — R1 LineageFlow HMMER retro-validation reproducibility recipe + audit doc authored; SHA-256 chain + bash/Python recipes for Wave 349 P1 + P4 GPU torch-mode evidence; PARTIAL / single-seed-disclosed verdict preserved verbatim per Wave 268 strict-clean + Wave 308 P1 demotion)._
