# Wave 357 P1 — ruff W292 trailing-newline fix in `tools/audit_thm5/`

**Date:** 2026-09-25
**Wave:** 357 P1
**Status:** READY_TO_COMMIT (subject to user authorization; NO-PUSH)
**Trigger:** Wave 356 P3 (`docs/audit/wave356-submission-checklist-review.md` §2.2 item 2 + §4 camera-ready fix #1) identified a 2-finding ruff W292 regression in `tools/audit_thm5/estimate_lipschitz.py:233` and `tools/audit_thm5/fit_thm5.py:371` — both files introduced by Wave 350/351 audit-tool additions. This wave discharges camera-ready fix #1.
**Scope:** strictly ADDITIVE — append exactly 1 trailing newline (`\n`) to each of the 2 target files (2 bytes total). NO code change, NO logic change, NO whitespace change beyond the single trailing newline, NO other ruff findings touched (out of scope per Wave 356 P3 submission_checklist).

---

## 1. Executive Summary

| Item | Value |
|---|---|
| ruff findings BEFORE fix | **2** (both `W292 No newline at end of file`) |
| ruff findings AFTER fix | **0** (`All checks passed!`) |
| Files fixed | **2** (`tools/audit_thm5/estimate_lipschitz.py` + `tools/audit_thm5/fit_thm5.py`) |
| Bytes added (net) | **+2** (1 newline byte per file) |
| Lines added (net) | **+2** (one trailing `\n` per file counts as one line break) |
| Camera-ready fix closed | **#1** of 8 (per `docs/audit/wave356-submission-checklist-review.md` §4) |
| Hard guardrails honored | NO-PUSH (commit-only); ADDITIVE only (1 byte per file); no other ruff findings touched; no vendored code touched; no claim numbers changed |
| Other gates verified | D.4 30/30 PASS, claims PASS (no drift), mkdocs build --strict PASS |

**Verdict:** Ruff W292 trailing-newline regression is closed; `ruff check adaptive_reflow/ tests/ scripts/ tools/` now reports 0 findings across all in-scope directories (matches the Wave 242 P4 baseline state preserved by the AGENTS.md §4.1 CI-mirror gate).

---

## 2. Observed Facts

### 2.1 Pre-fix ruff findings (regression vs Wave 242 P4 baseline)

Before this wave, `ruff check adaptive_reflow/ tests/ scripts/ tools/` reported:

```
Found 2 errors.
[*] 2 fixable with the `--fix` option.
```

The 2 findings were both `W292 No newline at end of file`:

| # | File | Line | Code | Description |
|---|------|------|------|-------------|
| 1 | `tools/audit_thm5/estimate_lipschitz.py` | 233 | W292 | `sys.exit(main())` is the last token; no trailing newline |
| 2 | `tools/audit_thm5/fit_thm5.py` | 371 | W292 | `sys.exit(main())` is the last token; no trailing newline |

Pre-fix byte-level confirmation (both files end without a trailing newline):

```
$ tail -c 20 tools/audit_thm5/estimate_lipschitz.py | od -c | tail -3
0000000                   s   y   s   .   e   x   i   t   (   m   a   i
0000020   n   (   )   )
0000024

$ tail -c 20 tools/audit_thm5/fit_thm5.py | od -c | tail -3
0000000                   s   y   s   .   e   x   i   t   (   m   a   i
0000020   n   (   )   )
0000024
```

Both files end with the literal bytes `n ( ) )` (no `\n`). The ruff W292 rule requires POSIX-compliant text files to end with exactly one `\n`.

### 2.2 Wave 356 P3 attribution

Per `docs/audit/wave356-submission-checklist-review.md` §2.2 item 2 + §4 camera-ready fix #1:

> "**ruff 0 findings (4-dir scope: `adaptive_reflow/`, `tests/`, `scripts/`, `tools/`)** | **PENDING (regression)** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` → 'Found 2 errors' — both are `W292 No newline at end of file` at `tools/audit_thm5/estimate_lipschitz.py:233` and `tools/audit_thm5/fit_thm5.py:371`; introduced by Wave 350/351 audit-tool additions (NOT in Wave 242 P4 0-finding baseline); exit code 1"

> "**ruff W292 trailing newlines** | Append `\n` to `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` | ~2 files × 1 byte | No (CI-gate only)"

Wave 350 P1 (audit-tool additions) created `tools/audit_thm5/estimate_lipschitz.py` and `tools/audit_thm5/fit_thm5.py` without trailing newlines on their `sys.exit(main())` final lines. This is a known-class regression (POSIX text-file convention violation) that ruff flags as W292.

### 2.3 Fix applied (Wave 357 P1)

The fix is the smallest possible intervention: append exactly 1 `\n` byte to the end of each of the 2 target files. No other bytes changed.

```bash
# 1 byte appended to estimate_lipschitz.py
printf '\n' >> tools/audit_thm5/estimate_lipschitz.py

# 1 byte appended to fit_thm5.py
printf '\n' >> tools/audit_thm5/fit_thm5.py
```

Post-fix byte-level confirmation (both files now end with exactly one trailing `\n`):

```
$ tail -c 20 tools/audit_thm5/estimate_lipschitz.py | od -c | tail -3
0000000               s   y   s   .   e   x   i   t   (   m   a   i   n
0000020   (   )   )  \n
0000024

$ tail -c 20 tools/audit_thm5/fit_thm5.py | od -c | tail -3
0000000               s   y   s   .   e   x   i   t   (   m   a   i   n
0000020   (   )   )  \n
0000024
```

Both files now end with the literal bytes `n ( ) ) \n` (exactly one trailing newline).

### 2.4 Post-fix ruff findings

After this wave, `ruff check adaptive_reflow/ tests/ scripts/ tools/` reports:

```
All checks passed!
```

Exit code 0. 0 findings. Matches the Wave 242 P4 0-finding baseline that the AGENTS.md §4.1 CI-mirror gate ("ruff check 0 findings in scope dirs") is supposed to preserve.

Per-file post-fix check:

```
$ ruff check tools/audit_thm5/estimate_lipschitz.py tools/audit_thm5/fit_thm5.py
All checks passed!
```

### 2.5 Post-fix line counts + SHA-256

| File | Pre-fix lines | Post-fix lines | Pre-fix SHA-256 | Post-fix SHA-256 |
|------|---------------|----------------|------------------|------------------|
| `tools/audit_thm5/estimate_lipschitz.py` | 232 | 233 | (not recorded; byte-stream ended at `n()`)`)`) | `657944744c2ea057d5f31abed16e132f7dcf092b4f942dc45d87385fd4fce2f9` |
| `tools/audit_thm5/fit_thm5.py` | 370 | 371 | (not recorded; byte-stream ended at `n()`)`)`) | `811c5e36315afd2c7a21d66aa2c2f260e79c4debb2efca18c00d11e41c6e5401` |

Per-file net delta: +1 line (one trailing `\n` counts as one line break in `wc -l`), +1 byte.

### 2.6 Other gates verified post-fix

| Gate | Command | Result |
|------|---------|--------|
| D.4 byte-stable regression | `python3 -m pytest tests/test_d4_regression_vectors.py -q` | **30 passed, 3 warnings** (the 3 warnings are pre-existing deprecation warnings for `RMSPreservingCoordinateMixer` + `RoundResultBundle` + `validate_round_result_bundle`; not test failures) |
| Claims consistency | `python3 tools/check_claims_consistency.py` | **PASS** ("No drift detected"; 61 active claims + 2 deprecated; CLM-040 forced to PROVISIONAL per `Disputed by` citation, unchanged) |
| mkdocs strict build | `mkdocs build --strict` | **PASS** ("Documentation built in 24.93 seconds"; exit code 0; the "currently unlicensed" line is a mkdocs-material future-deprecation banner, not a build error) |

All three gates PASS post-fix, matching the Wave 242 P4 baseline state.

### 2.7 Hard guardrails honored

1. **NO-PUSH policy** — this wave commits only; no `git push` invoked. The commit message carries the `(USER AUTHORIZED, NO PUSH)` suffix per `todo/PUSH-READY.md`.
2. **ADDITIVE only** — exactly 2 bytes appended (1 `\n` to each of 2 files). No byte removed, no byte modified. No code change, no whitespace change beyond the trailing newline.
3. **No other ruff findings touched** — per Wave 356 P3 §2.2 item 2 "do not fix any other ruff findings (out of scope per Wave 356 P3 submission_checklist)", this wave fixes ONLY the 2 W292 findings. The scope is exactly the 2 W292 lines.
4. **Vendored upstream untouched** — no edits to `data/FlowMol3/`, `data/LineageFlow/`, `data/Kanzi/`, `data/HiDream-I1/`, `data/GraphBFN/`, `data/Lumina-Image-2.0/`, `data/ProtBFN-AbBFN/`, `data/Wan2.2/`, `data/FreqFlow/`; all 9 vendored repos remain byte-identical to upstream commit hashes (FlowMol3 `77cae22`, LineageFlow `ccef84a`, Kanzi `cfed9cf`).
5. **TNNLS submission freeze preserved** — no edits to `tnnls_submission/*.md`. The MANIFEST row 23 SHA for `tnnls_submission/MANIFEST.md` does not change (these are tools/, not tnnls_submission/). The MANIFEST itself is unchanged.
6. **No claim wording change, no number promotion** — `docs/CLAIMS.md` and `docs/CONSOLIDATED_RESULTS.md` are unchanged. No UNDERPOWERED / DEFERRED / REGRESSES / NOT_SIGNIFICANT status was promoted to SUPPORTED by wording or number change.
7. **Per-phase audit doc** — this file (`docs/audit/wave357-ruff-w292-fix.md`) is the per-phase audit doc for Wave 357 P1, mirroring the 12-decimal-CLAIMS-table format pattern from Wave 121-273 and the Wave 356 P3 audit-doc structure.
8. **Wave 268 strict-clean rule honored** — "stricter = cleaner; pick the option with fewer files touched, fewer lines changed, more additive". Wave 357 P1 touched only 2 existing files (2 bytes total: 1 byte per file × 2 files) + 1 new audit doc; no other files modified.

---

## 3. Interpretation

### 3.1 Why the trailing-newline fix closes camera-ready fix #1

Per `docs/audit/wave356-submission-checklist-review.md` §3.1 item 1:

> "**ruff W292 (PENDING):** The 2 trailing-newline errors are in `tools/audit_thm5/` (Wave 350/351 audit-tool additions), NOT in `tnnls_submission/`. TNNLS does not require `ruff check` exit-0 on the submitted `tnnls_submission/` package; the ruff check is a CI-gate, not a ScholarOne upload-gate. Per Wave 268 strict-clean rule the fix is a 2-line trailing-newline append (~2 files × 1 byte) — strictly additive; camera-ready scope."

The fix is the minimum-impact intervention: 1 byte per file × 2 files = 2 bytes total. No content change, no logic change, no formatting change beyond the trailing newline. The AGENTS.md §4.1 CI-mirror gate ("ruff check 0 findings in scope dirs") now passes again, restoring the Wave 242 P4 0-finding baseline that Wave 350/351 inadvertently broke.

### 3.2 Why this is the only ruff finding to fix in this wave

Per Wave 356 P3 task hard-guardrail "do NOT fix any other ruff findings (out of scope per Wave 356 P3 submission_checklist)":

- The `ruff check adaptive_reflow/ tests/ scripts/ tools/` output BEFORE this wave contained EXACTLY 2 findings (both W292).
- After this wave's 2-byte append, the same command returns 0 findings.
- There are no other ruff findings to fix in this scope; the 2 W292 findings were the only blockers to the CI-mirror gate.

If any OTHER ruff finding existed at the start of this wave, this wave would NOT have closed it. The verification (`ruff check adaptive_reflow/ tests/ scripts/ tools/` → `All checks passed!`) is the proof that the W292 closure is complete and self-contained.

### 3.3 Reconciliation with Wave 350/351 audit-tool additions

The 2 W292 findings were introduced by Wave 350 P1 (audit-tool additions that created `tools/audit_thm5/estimate_lipschitz.py` + `tools/audit_thm5/fit_thm5.py`). The Wave 350/351 audit-doc authors did not catch the trailing-newline omission because the ruff check at Wave 350/351 was scoped to the audit-tool additions themselves (or to a subset of dirs that excluded `tools/audit_thm5/`); the W292 findings were detected later by the broader 4-dir ruff scope (`adaptive_reflow/ tests/ scripts/ tools/`) that the AGENTS.md §4.1 CI-mirror gate mandates.

The fix does NOT modify the Wave 350/351 audit-tool logic. The audit tools themselves (the `def main()` bodies, the `if __name__ == "__main__":` blocks, the imports) are unchanged. Only the trailing newline byte was added to the file end.

### 3.4 Relationship to camera-ready fix #3 (MANIFEST rehash)

Per Wave 356 P3 §4 camera-ready fix #3 ("MANIFEST.md SHA-256 final rehash") and Wave 356 P3 §3.1 item 2:

> "**MANIFEST rehash (PENDING):** Per MANIFEST self-reference note the displayed SHA staleness is **intentional**: 'the displayed SHA is the hash of the bytes BEFORE this very SHA-row was added'. The final rehash is the freeze-marker step (after USER fills 17 placeholders, then re-hash `tnnls_submission/*.md` + `supplementary/README.md`). The PENDING state is the documented design."

The MANIFEST rehash is **independent** of the ruff W292 fix and is **out of scope** for Wave 357 P1. The MANIFEST does NOT list any file under `tools/audit_thm5/` (the audit-tool scripts are NOT part of the TNNLS submission package; they are CPU-only analysis utilities that live in the repo but are not uploaded to ScholarOne). Therefore, appending a trailing newline to `tools/audit_thm5/estimate_lipschitz.py` or `tools/audit_thm5/fit_thm5.py` does NOT affect the MANIFEST SHA ledger. No MANIFEST refresh is required as part of this wave.

---

## 4. Camera-ready scope update

| # | Item | Camera-ready fix | State at Wave 357 P1 |
|---|------|------------------|-----------------------|
| 1 | ruff W292 trailing newlines | Append `\n` to `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` | **CLOSED** (this wave) |
| 2 | 17 USER_TO_FILL placeholders | User fills 17 fields in `tnnls_submission/cover_letter.md` per `tnnls_submission/FILL_GUIDE.md`; scaffold at `tnnls_submission/cover_letter_FILL_AUTOFILL.json` | OPEN (user-gated, no agent scope) |
| 3 | MANIFEST.md SHA-256 final rehash | After #2, run `cd tnnls_submission && sha256sum -- *.md supplementary/README.md` + `sha256sum tnnls_submission/MANIFEST.md` and update rows 22-31 + row 23 self-reference | OPEN (gated by #2 user fill-in) |
| 4 | Lean 4 build completion | Complete Mathlib v4.34.1 precompilation + discharge 15 sorry sites across `Theorem4Subclaim41.lean` (5) + `Theorem5Subclaim51.lean` (5) + `Theorem5Subclaim52.lean` (4) + `Theorem5Subclaim53.lean` (1); Wave 354 P6-P9 enumerated | OPEN (multi-week Lean 4 prover effort) |
| 5 | R3 FlowMol3 single_mol seed=44 | Run seed=44 framework arm on single_mol path NFE=250 N=200 (DGL 2.4.0 batched-path bug workaround); add to 3-seed direction-consistency table | OPEN (GPU-gated, honest-disclosure already accepted) |
| 6 | K4 Kanzi decision-metric saturation | Additional N=1000 sweep on Kanzi decision-metric boundary | OPEN (GPU-gated, honest-disclosure already accepted) |
| 7 | K5 FreqFlow + MM-FM integration | PHASE-4 model download + adapter integration + N=1000 sweep | OPEN (multi-step env + adapter + sweep) |
| 8 | K6 Wan2.2 N=1000 sweep | Wan2.2 N=1000 sweep + 4-arm H2H + statistical tests | OPEN (multi-step model + sweep + tests) |

Wave 357 P1 closes 1 of 8 camera-ready scope items (12.5%). The remaining 7 items are unchanged in status from the Wave 356 P3 enumeration.

---

## 5. ADDITIVE changes (Wave 357 P1)

### 5.1 Files modified

- `tools/audit_thm5/estimate_lipschitz.py` — appended 1 trailing newline (`\n`) byte. Net delta: +1 line (232 → 233), +1 byte. New SHA-256: `657944744c2ea057d5f31abed16e132f7dcf092b4f942dc45d87385fd4fce2f9`.
- `tools/audit_thm5/fit_thm5.py` — appended 1 trailing newline (`\n`) byte. Net delta: +1 line (370 → 371), +1 byte. New SHA-256: `811c5e36315afd2c7a21d66aa2c2f260e79c4debb2efca18c00d11e41c6e5401`.

### 5.2 File NOT modified (per Wave 268 strict-clean rule)

- All 9 vendored upstream repos under `data/` — UNCHANGED. The trailing-newline append is to `tools/audit_thm5/` audit utilities, NOT to vendored code.
- `docs/CLAIMS.md` — UNCHANGED. No claim wording or number change.
- `docs/CONSOLIDATED_RESULTS.md` — UNCHANGED. No result number change.
- `tnnls_submission/*.md` — UNCHANGED. The TNNLS submission freeze is preserved. No MANIFEST row changes (the modified files are not listed in MANIFEST).
- `tnnls_submission/MANIFEST.md` — UNCHANGED. The MANIFEST does not list `tools/audit_thm5/*.py`; no SHA refresh required.
- `docs/drafts/paper-A-final.md` + `paper-A-final.pdf` + `paper-A-final.tex` — UNCHANGED. The paper content is byte-stable.
- All other `tools/` files (excluding the 2 fixed) — UNCHANGED. The ruff fix is scoped to EXACTLY the 2 W292 finding files.
- `adaptive_reflow/`, `tests/`, `scripts/` — UNCHANGED. The ruff check on these 3 dirs reported 0 findings before AND after the fix.

### 5.3 New file

- `docs/audit/wave357-ruff-w292-fix.md` — NEW audit doc (this file).

---

## 6. Verification

```bash
# 1. Pre-fix ruff findings (baseline)
ruff check adaptive_reflow/ tests/ scripts/ tools/
# Found 2 errors. (W292 × 2 — captured at the start of this wave)

# 2. Apply 2-byte ADDITIVE fix
printf '\n' >> tools/audit_thm5/estimate_lipschitz.py
printf '\n' >> tools/audit_thm5/fit_thm5.py

# 3. Post-fix ruff findings
ruff check adaptive_reflow/ tests/ scripts/ tools/
# All checks passed!  (exit code 0)

# 4. Post-fix per-file ruff check
ruff check tools/audit_thm5/estimate_lipschitz.py tools/audit_thm5/fit_thm5.py
# All checks passed!  (exit code 0)

# 5. D.4 byte-stable regression (must remain 30/30 PASS)
python3 -m pytest tests/test_d4_regression_vectors.py -q
# 30 passed, 3 warnings in 1.25s  (PASS; warnings are pre-existing deprecations)

# 6. Claims consistency (must remain PASS)
python3 tools/check_claims_consistency.py
# **No drift detected.**  (PASS; 61 active claims + 2 deprecated)

# 7. mkdocs strict build (must remain PASS)
mkdocs build --strict
# Documentation built in 24.93 seconds  (PASS; exit code 0)

# 8. Post-fix line counts + SHA-256
wc -l tools/audit_thm5/estimate_lipschitz.py tools/audit_thm5/fit_thm5.py
# 233 tools/audit_thm5/estimate_lipschitz.py
# 371 tools/audit_thm5/fit_thm5.py

sha256sum tools/audit_thm5/estimate_lipschitz.py tools/audit_thm5/fit_thm5.py
# 657944744c2ea057d5f31abed16e132f7dcf092b4f942dc45d87385fd4fce2f9  tools/audit_thm5/estimate_lipschitz.py
# 811c5e36315afd2c7a21d66aa2c2f260e79c4debb2efca18c00d11e41c6e5401  tools/audit_thm5/fit_thm5.py
```

---

## 7. References

- **`tools/audit_thm5/estimate_lipschitz.py`** — 233 lines; SHA `657944744c2ea057d5f31abed16e132f7dcf092b4f942dc45d87385fd4fce2f9`; trailing newline restored.
- **`tools/audit_thm5/fit_thm5.py`** — 371 lines; SHA `811c5e36315afd2c7a21d66aa2c2f260e79c4debb2efca18c00d11e41c6e5401`; trailing newline restored.
- **`docs/audit/wave356-submission-checklist-review.md`** §2.2 item 2 + §3.1 item 1 + §4 camera-ready fix #1 — original enumeration of the W292 regression.
- **`docs/audit/wave354-p5-lean-subclaim-stubs.md`** §6.1 + §6.5 — Lean 4 PENDING_MATHLIB_CACHE documentation (camera-ready fix #4; out of scope for Wave 357 P1).
- **`tnnls_submission/FILL_GUIDE.md`** — 17 fillable field documentation (camera-ready fix #2; out of scope for Wave 357 P1, user-gated).
- **`AGENTS.md` §3 Hard guardrails** — NO-PUSH + ADDITIVE + vendored sacred + TNNLS freeze sacred.
- **`AGENTS.md` §4.1 CI-mirror gates** — ruff 0 findings (now restored), D.4 30/30 PASS, claims PASS, mkdocs strict PASS.

---

_Wave 357 P1 audit doc authored 2026-09-25 — ruff W292 trailing-newline fix in `tools/audit_thm5/estimate_lipschitz.py:233` + `tools/audit_thm5/fit_thm5.py:371` (closes Wave 356 P3 camera-ready scope item #1 of 8)._