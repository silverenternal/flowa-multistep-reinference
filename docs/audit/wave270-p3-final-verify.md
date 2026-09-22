# Wave 270 P3 — Final verification (CI-config + ruff-style wave, no source code changes)

**Date:** 2026-09-22
**Branch:** main
**Scope:** Verification of Wave 270 P1 (ruff code-only fixes, `adapters/profile_residual.py` + `adapters/rectified_flow_cifar.py`) + Wave 270 P2 (CI yml install fixes, `.github/workflows/cpu-tests.yml` + `.github/workflows/docs-deploy.yml`) + this audit doc.
**Trigger:** CI-watchdog install-line defects + a partial ruff clean-up in `adaptive_reflow/adapters/`. P1 fixed 3 ruff findings inside its explicit file scope, P2 fixed 2 CI install lines, this P3 confirms the four gates and documents the wave's residual ruff state.

---

## Summary

Wave 270 P1 and P2 are code-style + CI-config fixes that together touch four non-algorithm files. P3 confirms the four pre-existing gates (D.4 byte-stable, mkdocs strict, claims consistency, pytest smoke) remain green, and records the wave's residual ruff state honestly: the wave's three target ruff findings are all gone, but 12 pre-existing ruff findings outside the wave's file scope remain and have been explicitly deferred to a follow-up wave. This P3 introduces **no source code changes** — it writes the audit doc and commits.

| Wave | Verified |
|---|---|
| P1: ruff `profile_residual.py:430` W292 trailing newline | YES (file ends in `\n`) |
| P1: ruff `rectified_flow_cifar.py:370` SIM108 if-else → ternary | YES (line 370 is single-line ternary) |
| P1: ruff `rectified_flow_cifar.py:1449` SIM108 if-else → ternary | YES (line 1449 is single-line ternary) |
| P2: `cpu-tests.yml` install line `[test] → [test,dev]` + drop `\|\|` | YES |
| P2: `docs-deploy.yml` install line adds `mkdocs-material mkdocstrings` | YES |

| Gate | Status |
|---|---|
| D.4 byte-stable regression vectors | **PASS** (30/30) |
| mkdocs build --strict | **PASS** (0 warnings) |
| claims consistency (`tools/check_claims_consistency.py`) | **PASS** (no drift) |
| pytest smoke (focused subset) | **PASS** (274 tests, 0 failures) |
| ruff `adaptive_reflow/` full sweep | **12 findings remain** (all pre-existing, outside Wave 270's file scope) |

---

## Gate 1 — D.4 byte-stable regression vectors

```
$ timeout 30 .venvs/lineageflow_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py -q --no-header
30 passed, 3 warnings in 2.41s
```

- **30/30 PASS.** No regressions from Wave 270 P1 (W292 + 2× SIM108 in two
  non-algorithm adapter files) or Wave 270 P2 (CI yml install lines only).
- The 3 warnings are pre-existing `DeprecationWarning` from
  `adaptive_reflow/contracts/__init__.py` (re-export bridge to
  `adaptive_reflow.molecular.bundle`); they have been stable since
  Wave 28e3bf9 and are unrelated to this wave.

---

## Gate 2 — mkdocs build --strict

```
$ timeout 30 mkdocs build --strict
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/hugo/codes/flowa-multistep-reinference/site
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.
INFO    -  Documentation built in 24.67 seconds
```

- **0 warnings, 0 errors.** Build is strict-clean.
- The "Formatting signatures requires either Black or Ruff" line is an
  informational INFO (not a warning) emitted by mkdocstrings regardless
  of whether strict mode is on; it has been stable since Wave 33.
- No `.md` doc-source edits, no `mkdocs.yml` changes introduced by
  Wave 270 P1 / P2.

---

## Gate 3 — claims consistency (`tools/check_claims_consistency.py`)

```
$ python3 tools/check_claims_consistency.py
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, CLM-002, ... (60 IDs total)

**No drift detected.**
```

- **No drift.** Headline numerical claims (`+0.224`, `+0.647`, `+189%`,
  `−78.25%`, `−67.10%`, `−2.53% to −0.66%`, `+116.46%`) and one-line
  summaries are byte-identical to before.
- CLM-040's PROVISIONAL state (Sidecar/2D-RF framework 0/0 divergence
  investigated in Wave 29) is unchanged by this wave and is correctly
  acknowledged by the consistency check.
- Wave 270 P1's ruff style fixes are in non-algorithm adapter files and
  do not touch any code path that produces claims-bearing output; Wave
  270 P2's yml install lines run *before* the gate suite and emit no
  claims.

---

## Gate 4 — pytest quick smoke (focused subset)

```
$ PYTHONPATH=. timeout 120 python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_claims/ \
    tests/test_core/ \
    tests/test_engine/ \
    -q --no-header
274 passed, 22 warnings in 18.50s
```

- **274/274 PASS** in 18.5 seconds.
- Subset chosen to cover the four gate surfaces without the full
  `tests/` sweep (which exceeds the 30 s budget on CPU). The full
  slow/benchmark-filtered sweep that Wave 269 ran was not re-run here
  because no algorithm code was touched.
- 22 warnings are the pre-existing `DeprecationWarning` family from
  `default_cosine_scheduler()` (Wave 34 paper-quantity-driven default
  migration) — unrelated to this wave.

---

## Gate 5 — Ruff state on `adaptive_reflow/`

```
$ ruff check adaptive_reflow/ 2>&1 | tail -5
help: Add trailing newline

Found 12 errors.
[*] 7 fixable with the `--fix` option (5 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

- **12 findings remain**, all **pre-existing** (predate Wave 270) and
  all **outside Wave 270's explicit file scope**. The wave's three
  target findings are all gone:

| Pre-fix ruff state | Post-fix ruff state |
|---|---|
| `adapters/profile_residual.py:430 W292` | gone |
| `adapters/rectified_flow_cifar.py:370 SIM108` | gone |
| `adapters/rectified_flow_cifar.py:1449 SIM108` | gone |
| **Total in `adaptive_reflow/`** | **15 → 12** (12 outside this wave's scope) |

- Per the Wave 270 P1 commit message (`72637eba`), the 12 remaining
  findings are in:
  - `adaptive_reflow/algorithm/scheduler/tier_aware.py` (3 findings: I001, SIM108, W292)
  - `adaptive_reflow/frame/engine.py` (1 finding: I001)
  - `adaptive_reflow/framework/state_bundle_cache.py` (1 finding: W292)
  - `adaptive_reflow/stats/__init__.py` (1 finding: UP)
  - `adaptive_reflow/stats/equivalence.py` (6 findings: I001, SIM108, 3× W292, F841)
- **Honest disclosure:** the task's `ruff_clean_local` expectation was
  0 findings, and this P3 reports the gate as **fail** on the
  full-sweep criterion. The 12 remaining findings are NOT introduced
  by Wave 270; they predate P1 and were intentionally left for a
  follow-up wave per the P1 audit doc's "deferred to follow-up"
  statement. The verification JSON's `ruff_clean_local = false`
  reflects this honestly rather than papering over the gap.

---

## Wave 270 P1 fixes verified

### 5.1 W292 (`profile_residual.py`)

```
$ tail -c 5 adaptive_reflow/adapters/profile_residual.py | od -c | head -1
0000000   e   e   d   )  \n
0000005
```

- Last 5 bytes = `seed)\n`. Trailing newline present. PASS.

### 5.2 SIM108 ×2 (`rectified_flow_cifar.py`)

```
$ sed -n '368,372p' adaptive_reflow/adapters/rectified_flow_cifar.py
        captured_v = _captured_unet_forward(unet, x_t, t_t)
        v = captured_v if captured_v is not None else unet(x_t, t_t)
        return v
```

```
$ sed -n '1447,1451p' adaptive_reflow/adapters/rectified_flow_cifar.py
            captured_v = captured_velocity_field(unet, x_t, t_t)
            v_t = captured_v if captured_v is not None else unet(x_t, t_t)
            out[start:stop] = v_t
```

- Both refactors are single-line ternaries. Surrounding comments and
  indentation are preserved (the Wave 236 P2 CUDA-graph comment block
  above the line-370 refactor is verbatim, and 12-space inner-loop
  indentation is preserved around the line-1449 refactor). PASS.

---

## Wave 270 P2 fixes verified

### 5.3 `cpu-tests.yml` install line

```
$ grep -A 2 "Install dependencies" .github/workflows/cpu-tests.yml | head -4
      - name: Install dependencies
        run: |
          pip install -e ".[test,dev]" pytest hypothesis pytest-benchmark ruff mypy mutmut
```

- `[test] → [test,dev]`. The `\|\|` fallback is gone. PASS.

### 5.4 `docs-deploy.yml` install line

```
$ grep "pip install" .github/workflows/docs-deploy.yml
        run: pip install -e '.[dev]' mkdocs-material mkdocstrings
```

- `mkdocs-material mkdocstrings` appended. `mkdocs.yml` declares
  `theme: name: material`; this now resolves. PASS.

---

## Repo state at verification time

```
$ git status --short
 M docs/figures/noise_injection_two_moons_nfe_pareto.png
 M docs/figures/noise_injection_two_moons_pareto_front.png
 M docs/figures/noise_injection_two_moons_sigma_vs_w2.png
```

The three modified PNG files are pre-existing figure diffs unrelated
to this wave (they predate Wave 269 P1; they were already `M` at the
start of the conversation per the gitStatus snapshot). They are out of
scope for Wave 270 P3 and are not touched by this commit.

```
$ git log --oneline origin/main..HEAD | wc -l
2
```

2 unpushed commits on `main` (Wave 270 P1 + P2). This P3 commit will
be the 3rd. The unpushed history is Wave 270 only — both
code-style/yml-only, both preserving the four gates (modulo the
pre-existing ruff state disclosed in Gate 5). Push to `origin/main` is
the user's call (per the harness convention, this wave does not
auto-push).

---

## Hard-rule compliance

| Rule | Status |
|---|---|
| DO NOT modify framework source code | PASS — no source files touched |
| DO NOT touch vendored code | PASS — no files under `data/` modified |
| DO NOT touch background tasks | PASS — no background commands invoked |
| DO preserve D.4 30/30 PASS | PASS (Gate 1) |
| DO preserve mkdocs 0 warnings | PASS (Gate 2) |
| DO preserve claims consistency no drift | PASS (Gate 3) |
| DO NOT introduce any new internal IDs (Wave / CLM / USER ACTION) | PASS — this doc references only the pre-existing Wave 236 P2, Wave 28e3bf9, Wave 269, Wave 33, Wave 29, Wave 34, and Wave 270 identifiers, all already in audit context |
| DO NOT touch unrelated PNG figures | PASS — pre-existing figure diffs left alone |

---

## Files touched by this P3

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave270-p3-final-verify.md` — this audit doc.

No other files modified. No source code, no tests, no docs, no figures,
no config.

---

## Verification summary table (JSON-shaped)

| Key | Value | Provenance |
|---|---|---|
| `ruff_clean_local` | `false` | `ruff check adaptive_reflow/` reports 12 pre-existing findings (outside Wave 270's file scope) |
| `d4_pass` | `true` | 30/30 in `tests/test_d4_regression_vectors.py` |
| `d4_total` | `30` | full vector count |
| `mkdocs_warnings` | `0` | `mkdocs build --strict` emits only INFO lines |
| `claims_consistency` | `ok` | `python3 tools/check_claims_consistency.py` reports **No drift detected.** |
| `pytest_smoke_passed` | `true` | 274/274 in focused subset (D.4 + claims + core + engine) |
| `n_unpushed_commits` | `2` | `git log origin/main..HEAD` shows Wave 270 P1 + P2 |
| `audit_doc_path` | `docs/audit/wave270-p3-final-verify.md` | this file |
| `commit_sha` | (set by commit step below) | this audit doc's commit |
