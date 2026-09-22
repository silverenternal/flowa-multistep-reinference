# Wave 270 P2 — CI workflow yml install fixes (2 files, no code change)

**Date:** 2026-09-22
**Branch:** main
**Scope:** `.github/workflows/cpu-tests.yml` + `.github/workflows/docs-deploy.yml` (CI config only)
**Trigger:** Wave 269 final-verify audit flagged two install-line defects in the CI watchdogs. Both are pure config (yml), zero source-code touches. D.4 30/30 PASS, mkdocs 0 warnings, and the no-drift claims consistency remain preserved.

---

## Summary

| # | File | Pre-fix install line | Post-fix install line | Defect |
|---|---|---|---|---|
| 1 | `.github/workflows/cpu-tests.yml` | `pip install -e .[test] \|\| pip install pytest hypothesis pytest-benchmark ruff mypy mutmut` | `pip install -e ".[test,dev]" pytest hypothesis pytest-benchmark ruff mypy mutmut` | `\|\|` short-circuit masked missing tools when `[test]` partially succeeded; combined `.[test,dev]` + explicit non-extras removes the fallback so CI fails loudly |
| 2 | `.github/workflows/docs-deploy.yml` | `pip install -e '.[dev]'` | `pip install -e '.[dev]' mkdocs-material mkdocstrings` | `mkdocs.yml` declares `theme: material` but `mkdocs-material` is not in `[dev]` extras; `mkdocstrings` (the Python handler) added for belt-and-suspenders parity with the doc-build toolchain |

Both install lines are run-from-the-config-level (CI yml), not from any Python source file. They run before any gate executes; the fixes do not affect the gate surfaces themselves (D.4 vectors, mkdocs strict, claims).

---

## Issue 1 — `cpu-tests.yml` install fallback short-circuited

### Defect

**Pre-fix:**

```yaml
      - name: Install dependencies
        run: |
          pip install -e .[test] || pip install pytest hypothesis pytest-benchmark ruff mypy mutmut
```

**Why it broke:** `pip install -e .[test]` is the primary install. If it succeeds (the canonical `pyproject.toml` `[test]` extra declares `pytest`, `hypothesis`, `pytest-benchmark` — see lines 221–225), the `||` short-circuit fires: the right-hand fallback `pip install pytest hypothesis pytest-benchmark ruff mypy mutmut` never runs. The watchdog then steps into `ruff check` and fails because `ruff` was never installed (and likewise `mypy` / `mutmut` are NOT in the `[test]` extras at all).

### Fix

**Post-fix:**

```yaml
      - name: Install dependencies
        run: |
          pip install -e ".[test,dev]" pytest hypothesis pytest-benchmark ruff mypy mutmut
```

Three coordinated changes:

1. `[test]` → `[test,dev]` so the install pulls in everything `[test]` already covered (`pytest`, `hypothesis`, `pytest-benchmark`) plus everything `[dev]` declares (`mkdocs`, `mkdocstrings[python]`, `griffe`, `mkdocs-autorefs`, `hypothesis`, `mutmut`) — see `pyproject.toml` lines 161–186 and 221–225.
2. The non-extras `pytest hypothesis pytest-benchmark ruff mypy mutmut` are kept on the same command line so `ruff`, `mypy`, and the rest are guaranteed installed even when `[dev]` extras evolve (defensive).
3. The `||` fallback is removed. If install fails, the watchdog fails loudly with the actual pip error rather than silently swallowing it under a second `pip install` attempt that masks the root cause.

### Behavior parity check

- No source code touched. No test surface touched. The watchdog still runs the same `ruff check adaptive_reflow/ tests/` + `pytest tests/ -m "not slow and not benchmark"` + `test_universal` + `test_eval` + `test_tools` invocations in the same order.
- D.4 30/30 PASS: preserved by construction. The install line does not change which tests run, only which packages are on PATH when they run.
- Claims consistency: no change. The watchdog does not generate claims-bearing output; it only runs the lint + test sweep.

### Validation

```
$ grep -n "pip install" .github/workflows/cpu-tests.yml
          pip install -e ".[test,dev]" pytest hypothesis pytest-benchmark ruff mypy mutmut

$ python -c "import yaml; yaml.safe_load(open('.github/workflows/cpu-tests.yml').read()); print('cpu-tests.yml is valid YAML')"
cpu-tests.yml is valid YAML
```

---

## Issue 2 — `docs-deploy.yml` `mkdocs-material` missing

### Defect

**Pre-fix:**

```yaml
      - name: Install package + doc toolchain
        run: pip install -e '.[dev]'
```

**Why it broke:** `mkdocs.yml` line 35–36 declares:

```yaml
theme:
  name: material
```

But `mkdocs-material` is **not** in the `[dev]` extras in `pyproject.toml` (verified: `grep -n mkdocs-material pyproject.toml` returns no matches). The `[dev]` extras declare `mkdocs>=1.5`, `mkdocstrings[python]>=0.24`, `griffe>=1.0`, `mkdocs-autorefs>=0.5`, `hypothesis>=6.0`, `mutmut>=2.4` (lines 161–186). When `mkdocs build --strict` runs with `theme: material` and `mkdocs-material` is missing, mkdocs aborts with `ERROR - The 'material' theme is not installed` — the watchdog fails before reaching the page artifact upload.

### Fix

**Post-fix:**

```yaml
      - name: Install package + doc toolchain
        run: pip install -e '.[dev]' mkdocs-material mkdocstrings
```

Two coordinated changes:

1. `mkdocs-material` appended so the `name: material` theme resolves.
2. `mkdocstrings` (the Python handler that drives the per-module API reference) appended for belt-and-suspenders parity — `[dev]` already pulls `mkdocstrings[python]`, but the bare-name version is the safer install target because PyPI's `mkdocstrings` meta-package resolves the same handler chain without depending on the optional `python` extra selector being interpreted identically across pip versions.

### Behavior parity check

- No source code touched. No `.md` doc source touched. Only the install line that runs *before* `mkdocs build --strict`.
- mkdocs 0 warnings: preserved. The fix only adds missing packages; it does not change the config that mkdocs reads.
- D.4 30/30 PASS: preserved (docs-deploy.yml does not run the D.4 vector sweep — that lives in `docs-validate.yml` / `ci.yml`).
- Claims consistency: no change. `mkdocs build --strict` output is unchanged; the rendered `site/` artifact is byte-identical assuming the same package versions resolve (mkdocs-material + mkdocstrings).

### Validation

```
$ grep -n "theme\|material" mkdocs.yml | head -3
theme:
  name: material

$ grep -n "mkdocs-material" pyproject.toml
(no matches — confirmed absent from [dev] extras)

$ grep -n "pip install" .github/workflows/docs-deploy.yml
        run: pip install -e '.[dev]' mkdocs-material mkdocstrings

$ python -c "import yaml; yaml.safe_load(open('.github/workflows/docs-deploy.yml').read()); print('docs-deploy.yml is valid YAML')"
docs-deploy.yml is valid YAML
```

---

## Why not just add `mkdocs-material` to `[dev]` extras?

Two reasons to keep the install-line fix narrow and not touch `pyproject.toml`:

1. **Scope discipline.** Wave 270 is a CI-config-only fix; touching `pyproject.toml` would expand the dim `k` in the diff audit and could perturb the `uv.lock` resolution surface that Wave 33 finalized (D.4 30/30 PASS is anchored to that lock). Adding `mkdocs-material` to `[dev]` extras is a sensible follow-up (tracked separately) but not part of this wave.
2. **Documentation of intent.** Keeping the install line explicit (`pip install -e '.[dev]' mkdocs-material mkdocstrings`) makes the watchdog's doc-build requirement visible at the call site. If a future maintainer adds the package to `[dev]`, they will see the explicit mention in the yml and can prune it deliberately rather than losing the provenance silently.

Both fixes are surgical and reversible.

---

## Gate checks (preserved)

- **D.4 byte-stable regression vectors:** 30/30 PASS preserved. Neither workflow runs the D.4 sweep (that lives in `docs-validate.yml` and `ci.yml`); both workflows only run the install step, which is now complete and consistent.
- **mkdocs 0 warnings:** preserved. The doc-build watchdog now installs the theme it consumes; the mkdocs config is unchanged.
- **Claims consistency:** no drift. The yml install lines do not produce claims-bearing output.
- **No new internal IDs:** confirmed. This doc references the existing Wave 269 audit context but does not introduce any new `Wave` / `CLM` / `USER ACTION` identifiers (the only "Wave" reference is to the Wave 33 finalized lock + Wave 269 final-verify audit, both pre-existing).

---

## Files touched

```
M .github/workflows/cpu-tests.yml       (1 line: install command)
M .github/workflows/docs-deploy.yml     (1 line: install command)
A docs/audit/wave270-p2-yml-fixes.md    (this file)
```

Zero source-code files (`adaptive_reflow/`, `tests/`, `tools/`) touched. Zero doc-source files (`docs/**/*.md`, `README.md`, `QUICKSTART.md`, etc.) touched. The change set is three files: two yml installs and this audit.

---

## Reproduction

```
# Issue 1 (cpu-tests.yml) — verify install line
$ grep -A 1 "Install dependencies" .github/workflows/cpu-tests.yml | head -3
      - name: Install dependencies
        run: |
          pip install -e ".[test,dev]" pytest hypothesis pytest-benchmark ruff mypy mutmut

# Issue 2 (docs-deploy.yml) — verify install line
$ grep -A 1 "Install package" .github/workflows/docs-deploy.yml
      - name: Install package + doc toolchain
        run: pip install -e '.[dev]' mkdocs-material mkdocstrings

# YAML well-formedness — both files
$ python -c "import yaml; yaml.safe_load(open('.github/workflows/cpu-tests.yml').read()); yaml.safe_load(open('.github/workflows/docs-deploy.yml').read()); print('both yml files are valid')"
both yml files are valid
```