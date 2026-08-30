# R5 Survey 09: Gate-Fix Execution Plan for FlowA

> Agent P deliverable — Detailed, executable fix plan for the four failing CI gates surfaced after R5 scaffolding (check_docs, mkdocs nav, pytest, mypy). Each step is concrete enough that a different agent can execute it end-to-end without further questions. Every recommendation cites `docs/r5-survey/08-gate-fix-research.md` for rationale.

**Date:** 2026-08-30
**Author:** Agent P
**Inputs:** Phase 1 research (`docs/r5-survey/08-gate-fix-research.md`); current gate failure inventory (see §1).
**Constraint:** Phase 2 is **read-only on this repo** — no source edits, no commits. This document is the work order for a follow-up agent with write access.

---

## §1. Decision matrix (one row per gate)

| Gate | Recommended action | Rationale (cite §X from research) | Effort |
|------|---------------------|------------------------------------|--------|
| **A. check_docs** (`paper-plan.md:88` `MySotaModelAdapter`) | **fix** — replace the inline-backtick reference with prose | Research §7 Gate A: "Backtick pairing in Markdown is binary (open/close); a missing or extra backtick is unambiguous. Fix it at the source (the .md file), not by suppressing the linter." | 5 min |
| **B. mkdocs nav** (4 pages not in `nav:`) | **fix by exclusion** — add the four paths to `not_in_nav:` (the existing escape hatch in `mkdocs.yml` lines 123–152) | Research §1: "Explicit `nav:` is curated; `not_in_nav:` is the documented escape hatch for files that are intentionally not primary landing surfaces." The four pages are research records, not primary docs. Mirrors the existing `r3-survey/*.md` and `r4-survey/*.md` lines (research §4: "Older rounds are kept (never deleted) so the audit trail is preserved"). | 10 min |
| **C. pytest** (11 new errors in `test_mnist_fm.py` + 3 pre-existing) | **importorskip** — add `pytest.importorskip("torch", reason="...")` at top of `test_mnist_fm.py` AND in a top-level `conftest.py` fixture so the skip happens at collection; for the 3 pre-existing fails, investigate first, then `xfail(strict=True, reason="issue #N")` if a known bug | Research §3 (scikit-learn, transformers, PyTorch): "`importorskip` for missing dependencies, `skipif` for environmental conditions, `xfail` for known bugs. The three are NOT interchangeable." Research §7 Gate C: "Do NOT use `xfail` to silence a torch-missing failure." | 30 min |
| **D. mypy** (41 errors in `rectified_flow_cifar.py`) | **exclude** — add a single regex entry to the existing `[tool.mypy] exclude` list AND add a `[[tool.mypy.overrides]]` block with `ignore_errors = true` mirroring the existing twodim_fm pattern | Research §2 (PyTorch Lightning two-tier + Django + mypy_self_check): regex `exclude` for directory-level skip + per-module override for fine-grained skip; the file is torch-required scaffolded experiment code that mirrors functionality already covered by the production `twodim_fm` adapter. Do NOT delete it (audit trail value per research §4). | 15 min |

---

## §2. Step-by-step fix plan

### Gate A — `check_docs: paper-plan.md:88`

**File:** `c:\Users\31472\codes\flowa-multistep-reinference\docs\paper-plan.md`

**Current state (line 88, exact text):**

```markdown
 - The experiment is plug-and-play: write `MySotaModelAdapter` implementing the Protocol, configure scheduler, run, compare.
```

**Diagnosis (tools/check_docs_against_code.py:561–617, `_scan_inline_backticks`):**

The scanner extracts every backtick token via `BACKTICK_RE = re.compile(r"`([^`\n]+)`")` (line 209). For each token it calls `_is_likely_python_symbol(name)` (line 220). `MySotaModelAdapter` matches the CamelCase pattern (starts with upper, contains lower), length 18 ≥ 4, not in `PROSE_SYMBOL_DENYLIST` (line 84 — the denylist has `MyAdapter` but **not** `MySotaModelAdapter`), so it is treated as a real Python symbol claim. The symbol index (`_build_symbol_index`, line 377) walks `adaptive_reflow/` only — there is no `MySotaModelAdapter` class anywhere in the production code. Result: `MISSING` claim at `paper-plan.md:88`, exit code 1.

**Fix (single Edit, lines 88 only):**

Replace the literal backticked identifier with a non-backticked prose phrase OR with the canonical existing adapter name. Two acceptable rewrites (pick one):

**Option A1 (preferred — illustrative placeholder phrasing, no symbol claim):**

```markdown
 - The experiment is plug-and-play: write a custom adapter implementing the Protocol, configure scheduler, run, compare.
```

**Option A2 (if a concrete reference is desired, point to an existing adapter):**

```markdown
 - The experiment is plug-and-play: write a custom adapter implementing the Protocol (see the shipped `TwoDimFMAdapter` for a worked example), configure scheduler, run, compare.
```

Option A1 is cleaner — `MySotaModelAdapter` is explicitly called out as an illustrative placeholder in the input prompt ("Pre-existing illustrative placeholder"). Option A2 keeps the teaching value of "see an existing adapter" while pointing at a real symbol.

**Why this fix (citation):** Research §7 Gate A: "Backtick pairing in Markdown is binary (open/close); a missing or extra backtick is unambiguous. Fix it at the source (the .md file), not by suppressing the linter."

---

### Gate B — `mkdocs nav: 4 pages missing`

**File:** `c:\Users\31472\codes\flowa-multistep-reinference\mkdocs.yml`

**Current state (lines 44–58 — the `nav:` block):**

```yaml
nav:
  - Home: api/index.md
  - API reference:
      - Contracts: api/adaptive_reflow.contracts.md
      - Universal: api/adaptive_reflow.universal.md
      - Frame: api/adaptive_reflow.frame.md
      - Molecular: api/adaptive_reflow.molecular.md
      - Eval: api/adaptive_reflow.eval.md
      - Adapters: api/adaptive_reflow.adapters.md
  - Architecture: ARCHITECTURE.md
  - Testing: TESTING_STRATEGY.md
```

The four flagged files (not present in `nav:` and not silenced in `not_in_nav:`):

1. `docs/paper-plan.md`
2. `docs/r5-survey/01-sota-fm-candidates.md`
3. `docs/r5-survey/02-baseline-fid.md`
4. `docs/r5-survey/02-sota-integration-plan.md`

**Diagnosis (`mkdocs.yml` lines 154–172 — `validation:` block):**

The `validation.nav.omitted_files: warn` setting (line 160) warns on any file not in `nav:`. The four flagged files match because:

- `paper-plan.md` is a planning document, not a primary landing surface — intentional omission, but not declared in `not_in_nav:`.
- The three `r5-survey/*.md` files are research records — `r3-survey/*.md` and `r4-survey/*.md` are already declared in `not_in_nav:` (lines 151–152) but `r5-survey/*.md` is missing.

**Fix (single Edit to `mkdocs.yml`, append two lines to the `not_in_nav:` block):**

Insert the following two lines just after the existing `r4-survey/*.md` line (line 152):

```yaml
  paper-plan.md
  r5-survey/*.md
```

The resulting `not_in_nav:` block should now end with:

```yaml
  r3-survey/*.md
  r4-survey/*.md
  paper-plan.md
  r5-survey/*.md
```

**Indentation note:** the existing entries use 2-space indentation; new lines must match exactly. The block is a YAML literal-block scalar (`|`), so each line must be indented by exactly 2 spaces relative to the parent `not_in_nav:` key.

**Verification command (run after the edit):**

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
PYTHONPATH=. python -m mkdocs build --strict 2>&1 | head -50
```

Expected: zero `WARNING - Documentation file ... is not included in the 'nav' configuration` lines.

**Why this fix (citation):** Research §1 (Flax/JAX, The Turing Way, mkdocs-awesome-pages-plugin) recommends explicit curated `nav:`; the `not_in_nav:` escape hatch is the canonical mkdocs pattern for files that are intentionally not primary landing surfaces. Research §4: "These are referenced from `nav:` under a 'Research Records' section. Older rounds are kept (never deleted) so the audit trail is preserved." The proposed fix uses `not_in_nav:` (not auto-generated nav, not deletion) — exactly the discipline described in research §4.

**Why NOT auto-gen via `mkdocs-awesome-pages-plugin` (research §1):** Adding a plugin adds a runtime dependency to the `dev` extra and changes the nav ordering for *all* files. Four files is below the threshold where plugin installation is justified; the simpler `not_in_nav:` declaration is the right tool for this scale.

---

### Gate C — `pytest: 11 new errors + 3 pre-existing`

**File(s):**

- `c:\Users\31472\codes\flowa-multistep-reinference\tests\test_adapters\test_mnist_fm.py` (11 errors — torch-missing collection)
- Three pre-existing failures (locations TBD by diagnostic step C1 below)

**Diagnosis:**

Per the gate inventory, the 11 new errors are caused by `torch` missing from the venv while the R4 EXP-1 MNIST tests require it (3-epoch MNIST training and inference). The 3 pre-existing failures are *separate* from the torch-missing ones and need a separate triage.

**Fix Step C1 — Triage the 3 pre-existing failures first (5 min):**

Run the full pytest suite excluding the torch-required file to see the pre-existing failures in isolation:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
python -m pytest tests/ --ignore=tests/test_adapters/test_mnist_fm.py --tb=short -q 2>&1 | tail -40
```

Expected: a list of 3 distinct failures with file:line and a short traceback. Record the three (file, test name, traceback) into a scratch note for the next step.

**Fix Step C2 — Decide xfail vs fix for each pre-existing failure (10 min):**

For each of the 3 pre-existing failures:

1. If the test is testing code that has changed since the test was written → **fix the test** (update the assertion to match the new API).
2. If the test exercises a known broken feature with a tracking issue → **mark `xfail(strict=True, reason="issue #N")`**.

Apply the decorator at the test-function level. The decorator syntax:

```python
@pytest.mark.xfail(strict=True, reason="issue #1234 — known broken until R6")
def test_something_that_fails():
    ...
```

Per research §3: "Use sparingly. With `strict=True`, an unexpected pass becomes a failure, preventing the 'xfail-rot' problem."

**Fix Step C3 — Add `importorskip` for torch in the test file (10 min):**

**File:** `c:\Users\31472\codes\flowa-multistep-reinference\tests\test_adapters\test_mnist_fm.py`

Insert the following line **after** the existing `import pytest` (line 57) and **before** the `# Helpers` section comment (line 59):

```python
# Skip the entire file when torch is not installed in the test env.
# The R4 EXP-1 MNIST adapter depends on torch for the velocity-field UNet;
# without it, no test in this module can run. Mirrors the scikit-learn and
# Hugging Face transformers convention for optional-dependency tests.
pytest.importorskip("torch", reason="torch is required for MNIST FM tests (R4 EXP-1)")
```

The placement matters: the import must be after `import pytest` (line 57) so `pytest` is in scope, and before any helper or test function that may transitively import torch. The `reason=` argument is mandatory per research §3 ("`importorskip` without a `reason=`: the skip message is opaque").

**Why `importorskip` and not `skipif` or `xfail` (citation):** Research §3 (scikit-learn conftest, transformers conftest, PyTorch test convention): "`importorskip` for optional dependencies, `skipif` for environmental conditions, `xfail` for known bugs." Torch-missing is a missing-dependency case, not a known bug and not an environmental condition. Research §7 Gate C: "Do NOT use `xfail` to silence a torch-missing failure. That masks a real production-build breakage." `importorskip` correctly preserves the test in the suite (collected but skipped) so a CI run with torch installed still exercises it.

**Why file-level and not fixture-level:** The conftest at `tests/test_adapters/conftest.py` is shared across all adapter tests; placing the skip there would also skip `test_rectified_flow_cifar.py` which has its own `torch_is_available()` shim (line 147 of `rectified_flow_cifar.py`) and runs in synthetic mode without torch. Per-module `importorskip` is the minimum-blast-radius placement.

**Verification command (after C1 + C2 + C3):**

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
python -m pytest tests/ --tb=short -q 2>&1 | tail -20
```

Expected: `12 skipped` (11 mnist tests + the module-level `importorskip` if pytest counts it as 1), `0 failed`. The 3 pre-existing failures should now either pass (if fixed) or be marked `xfail`.

---

### Gate D — `mypy: 41 errors in rectified_flow_cifar.py`

**File:**

- `c:\Users\31472\codes\flowa-multistep-reinference\adaptive_reflow\adapters\rectified_flow_cifar.py` (41 errors — torch-required scaffold)
- `c:\Users\31472\codes\flowa-multistep-reinference\pyproject.toml` (config edit)

**Diagnosis:**

`rectified_flow_cifar.py` is a 1158-line torch-required scaffold that mirrors the production 2D adapter (`adaptive_reflow/adapters/twodim_fm.py`) but for CIFAR-10 32×32 with a DDPM++ UNet. It uses `Any` extensively (line 54 `from typing import Any, Literal`) because torch tensors are typed as opaque `Any` in strict mode. The 41 errors are concentrated in the `_build_torch_unet_ddpmpp` (lines 310–433), `_torch_velocity_field` (lines 263–288), `_batched_torch_velocity_field` (lines 1088–1103), and the `nn.Module` class bodies.

This file is exactly the case research §7 Gate D describes: "If it must be kept for the audit trail ... add it to `[tool.mypy] exclude` with a comment explaining why."

**Fix Step D1 — Add the file to `[tool.mypy] exclude` regex list (5 min):**

**File:** `c:\Users\31472\codes\flowa-multistep-reinference\pyproject.toml`

**Current state (lines 238–250 — the `exclude:` list):**

```toml
exclude = [
    "venv/",
    "\\.venv/",
    "(^|/)rdkit-stubs/.*",
    "(^|/)site-packages/rdkit/.*",
    "(^|/)site-packages/numpy.*",
    "numpy",
    "site-packages.numpy.*",
    "(^|/)adaptive_reflow/eval/rdkit_oracle\.py",
    "(^|/)adaptive_reflow/adapters/twodim_fm.*",
    "(^|/)adaptive_reflow/adapters/twodim_fm_train\.py",
    "(^|/)adaptive_reflow/eval/twodim_fm_evaluator\.py",
]
```

Insert one new line after the `twodim_fm_train\.py` line:

```toml
    "(^|/)adaptive_reflow/adapters/rectified_flow_cifar\.py",
```

The list should now end with:

```toml
    "(^|/)adaptive_reflow/adapters/twodim_fm_train\.py",
    "(^|/)adaptive_reflow/eval/twodim_fm_evaluator\.py",
    "(^|/)adaptive_reflow/adapters/rectified_flow_cifar\.py",
```

The escape `\.py` is required to avoid `.py` matching `pytorch`, etc. (mypy's regex flavor is documented in the config-file reference at https://mypy.readthedocs.io/en/stable/config_file.html#import-discovery — cited in research §2).

**Fix Step D2 — Add a matching `[[tool.mypy.overrides]]` block (5 min):**

**Current state (lines 312–318 — the twodim_fm override block):**

```toml
[[tool.mypy.overrides]]
module = [
    "adaptive_reflow.adapters.twodim_fm",
    "adaptive_reflow.adapters.twodim_fm_train",
    "adaptive_reflow.eval.twodim_fm_evaluator",
]
ignore_errors = true
```

Insert one new entry in the `module` list:

```toml
[[tool.mypy.overrides]]
module = [
    "adaptive_reflow.adapters.twodim_fm",
    "adaptive_reflow.adapters.twodim_fm_train",
    "adaptive_reflow.adapters.rectified_flow_cifar",
    "adaptive_reflow.eval.twodim_fm_evaluator",
]
ignore_errors = true
```

**Why both regex `exclude` AND per-module override (citation):** Research §2 (PyTorch Lightning, Django, mypy_self_check): two-tier pattern. The regex `exclude` removes the file from mypy's input entirely (the cheap skip); the per-module override is a defensive belt-and-suspenders that also fires if anyone passes the file explicitly via `mypy path/to/file.py`. Per research §2: "Use `warn_unused_ignores = true` and `warn_redundant_casts = true` (mirroring Lightning's config) to catch dead `# type: ignore` comments. Never use a blanket `exclude = '.*'` — that's the failure mode."

**Fix Step D3 — Do NOT delete the file (alternative considered and rejected):**

Per research §7 Gate D: "If `rectified_flow_cifar.py` is a scaffolded experiment that mirrors functionality already covered by the production `adaptive_reflow/` package: **delete it**. Dead scaffolds rot; mypy errors are a symptom." — BUT this file is NOT dead. It is the load-bearing adapter for CLM-040 (CIFAR-10 SOTA FM reproduction, see `docs/paper-plan.md:88` and `rectified_flow_cifar.py:42-44`). The audit trail value (research §4) outweighs the maintenance cost. The regex-exclude + per-module-override pair achieves the same CI-green outcome without losing the audit record.

**Verification command (after D1 + D2):**

```bash
cd c:/Users\31472/codes/flowa-multistep-reinference
python -m mypy adaptive_reflow/ 2>&1 | tail -20
```

Expected: zero error lines referencing `rectified_flow_cifar.py`; no new errors in other files; overall error count reduced by ≥ 41.

**Optional polish (NOT required for the gate fix):**

If a future cleanup agent wants to remove the file from the production tree entirely while preserving the audit trail:

1. Move the file to `docs/r5-survey/code/rectified_flow_cifar.py` (read-only reference).
2. Add `docs/r5-survey/code/` to `[tool.mypy] exclude` (the directory pattern would catch any future files dropped in there).
3. Add `docs/r5-survey/code/` to `pyproject.toml [tool.ruff] extend-exclude`.

This is research §4's discipline ("`scratch/`, `playground/`, `experiments/` — gitignored throwaway code") applied to research artefacts: keep the record, remove the runtime surface. **Do not do this in the Phase 2 fix — it is out of scope.**

---

## §3. Commit order

**Recommendation: TWO commits, one for the doc/code-with-no-runtime-effect fixes (A+B+D) and one for the test fix (C).** Reasoning:

- **Commit 1 — "fix(r5): resolve 3 of 4 CI gate failures (docs/nav/mypy)"** covers Gates A, B, D. These three are doc-config / type-config changes with zero runtime behaviour impact. If the commit breaks anything, the blast radius is limited to "docs site broken" or "mypy too permissive" — both reversible by reverting a single commit.
- **Commit 2 — "fix(r5): skip torch-required MNIST tests in stdlib-only env"** covers Gate C. This one changes runtime test-collection behaviour (11 tests go from error → skip), which is a behaviour change reviewers will want to scrutinise separately.

**Why not all four in one commit:** Research §6 (synthesis) and the cited patterns (Lightning, transformers, Cookiecutter Data Science) all favour atomic commits per concern. The bigger concern is reviewer ergonomics: a single 4-gate commit makes a reviewer re-validate four unrelated decisions; splitting lets each gate's justification stand alone.

**Why not four commits:** Gates A and B are both doc-site concerns (the linter that flags Gate A and the linter that flags Gate B both consume the `docs/` tree). Grouping them keeps the docs-tree concerns reviewable in one pass. Gate D is config-only with no doc overlap — it slots in naturally with A+B because it is also "non-runtime gate fix." Group A+B+D = "make the linters green"; group C = "make the runtime green."

**Citation for commit granularity:** Research §6 synthesis explicitly cites Hugging Face transformers (atomic, per-concern commits) and Lightning (config split per concern). Cookiecutter Data Science §4 ("the smallest unit of a project is not code, but an experiment") implies the same — one round of fixes is one experiment-shaped unit.

**Commit message templates:**

```
fix(r5): resolve check_docs, mkdocs nav, and mypy gate failures

Three non-runtime gate fixes:

* paper-plan.md:88 — replace `MySotaModelAdapter` inline-backtick
  placeholder with prose ("write a custom adapter implementing the
  Protocol") so the check_docs_against_code inline-symbol scanner no
  longer flags a non-existent symbol.
* mkdocs.yml not_in_nav — add paper-plan.md and r5-survey/*.md so the
  four research-record pages are explicitly omitted from the primary
  nav (mirrors the existing r3-survey/*.md / r4-survey/*.md entries).
* pyproject.toml [tool.mypy] — exclude
  adaptive_reflow/adapters/rectified_flow_cifar.py (regex + per-module
  override) to silence the 41 mypy errors in the torch-required R5
  scaffolded CIFAR adapter. Mirrors the existing twodim_fm exclusion
  pattern.

Refs: docs/r5-survey/08-gate-fix-research.md §1 §2 §7.
```

```
fix(r5): skip torch-required MNIST adapter tests in stdlib-only env

The R4 EXP-1 MNIST tests in tests/test_adapters/test_mnist_fm.py
require torch (UNet inference for the 3-epoch trained MNIST FM
adapter); the stdlib-only CI env does not have torch installed. Add
a module-level pytest.importorskip("torch", reason=...) so the suite
is collected but each test is reported as skipped, not errored.

Mirrors the scikit-learn conftest and Hugging Face transformers
conftest convention for optional-dependency tests. Does NOT use
xfail — torch-missing is a missing dependency, not a known bug.

The 3 pre-existing failures (unrelated to torch) are individually
triaged and either fixed or marked @pytest.mark.xfail(strict=True,
reason="issue #N").

Refs: docs/r5-survey/08-gate-fix-research.md §3 §7.
```

---

## §4. Verification plan

After each gate's fix, run the gate-specific check + a no-regression sweep:

### After Gate A fix:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
PYTHONPATH=. python tools/check_docs_against_code.py --quiet
```

Expected: `All N claims verified across M source file(s).` (N was M+1 before the fix; M+1 after.)

Then run the full docs-check sweep:

```bash
PYTHONPATH=. python tools/check_docs_against_code.py --scan-docstrings --quiet
```

Expected: zero missing docstring-identifier claims (gate A's fix does not introduce new docstring issues).

### After Gate B fix:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
python -m mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR" || echo "OK: mkdocs strict build clean"
```

Expected: no `WARNING - Documentation file ... is not included in the 'nav' configuration` lines.

### After Gate C fix:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
python -m pytest tests/test_adapters/test_mnist_fm.py -v 2>&1 | tail -15
```

Expected: `11 skipped` (one line per test, each `SKIPPED [1] torch is required for MNIST FM tests (R4 EXP-1)`).

Then full suite:

```bash
python -m pytest tests/ --tb=short -q 2>&1 | tail -10
```

Expected: `0 failed`, `12 skipped` (11 mnist + any other module-level skips), `X passed` (X = the original passing count minus 11).

### After Gate D fix:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
python -m mypy adaptive_reflow/ 2>&1 | tail -10
```

Expected: error count reduced by ≥ 41; no new errors in other files.

### After all four gates:

```bash
cd c:/Users/31472/codes/flowa-multistep-reinference
PYTHONPATH=. python tools/check_docs_against_code.py --quiet
python -m mkdocs build --strict 2>&1 | grep -E "WARNING|ERROR" || echo "OK"
python -m pytest tests/ --tb=short -q 2>&1 | tail -5
python -m mypy adaptive_reflow/ 2>&1 | tail -5
python -m ruff check adaptive_reflow/ 2>&1 | tail -5
```

All five lines must end with `OK` or `0 errors` or equivalent. This is the "6 gates green" done-criterion (the 6th gate is `ruff`, which is assumed-passing in the R5 inventory — included here as a regression sentinel).

---

## §5. Risks

### Gate A risk — editing the doc might break other doc-checks

**What could go wrong:** The rewrite "write a custom adapter implementing the Protocol (see the shipped `TwoDimFMAdapter` for a worked example)" introduces `TwoDimFMAdapter` as a new backticked symbol. This token *does* exist in the codebase (in `adaptive_reflow/adapters/twodim_fm.py`), so `_build_symbol_index` (line 377 of `tools/check_docs_against_code.py`) will find it. Risk level: **low** — the scanner resolves it as `OK`. If the scanner still flags it (e.g. because the module is conditionally excluded), revert to Option A1 (no backticks).

**Mitigation:** Use Option A1 (no concrete symbol in backticks) unless Option A2 is desired for teaching value. If using Option A2, re-run `check_docs_against_code.py --quiet` immediately after the edit.

### Gate B risk — adding to `not_in_nav:` might cause mkdocs build warnings

**What could go wrong:** The YAML literal-block scalar (`not_in_nav: |`) has strict indentation rules. A single-character indent mistake will produce a YAML parse error and the entire mkdocs build will fail (not just warn).

**Mitigation:** Edit only by matching the existing 2-space indent exactly. Verify with `python -c "import yaml; yaml.safe_load(open('mkdocs.yml'))"` (catches YAML syntax errors before mkdocs runs).

### Gate C risk — marking tests as xfail might hide real bugs

**What could go wrong:** The 3 pre-existing failures may be real regressions masked by `xfail(strict=True)`. If a test that previously passed starts failing post-refactor, marking it `xfail` and moving on silently is exactly the "xfail-rot" failure mode research §5 warns about.

**Mitigation:**

1. Run the full pytest suite (per Step C1) and read each of the 3 failures carefully.
2. For each one, ask: "is this a test that was previously green?" → check `git log -- tests/path/to/test_xxx.py` for the most recent commit touching the test.
3. If the test was modified or the underlying code was modified recently, the failure is likely a regression → **fix the test**, do not mark xfail.
4. Only mark xfail when there is a clear known-bug trail (issue link, TODO comment in the code, etc.).

### Gate C risk — `importorskip` at module level might mask downstream torch-dependent code that should be importable

**What could go wrong:** If `test_mnist_fm.py` happens to import other torch-dependent modules *for their side effects* (e.g. registering a pytest fixture, warming up a cache), then `importorskip` at the top of the file silently skips all those side effects.

**Mitigation:** Read the file from line 1 to line 100 (already done in this analysis — only `numpy as np` and `pytest` are imported at the top, no side-effect imports). The `_make_phase_state`, `_make_final_policy`, `_make_condition_delta` helpers defer their framework imports to inside the function body (lines 102, 124, 161). The conftest fixture `mnist_fm_weights_path` is referenced but not defined in the conftest — this is itself a separate latent bug that the importorskip will not surface. **Flag this as a separate issue for a follow-up round** (see §7).

### Gate D risk — mypy exclude might hide future regressions

**What could go wrong:** If a future contributor adds real (non-torch) type errors to `rectified_flow_cifar.py` while refactoring, the regex `exclude` will silently hide them. Per research §5 ("Risk: blanket `exclude = '.*'` ... hides real bugs"), the worst-case failure mode is a broad exclude swallowing a real production bug.

**Mitigation:**

1. The regex is **file-scoped** (matches a single file path) — not directory-scoped — so new files in `adaptive_reflow/adapters/` are still checked.
2. The companion per-module `[[tool.mypy.overrides]]` block is the visible-in-config companion — anyone running `cat pyproject.toml` can see exactly which modules are silenced and why.
3. **Add a code comment** in `pyproject.toml` above the new exclude line:

```toml
# R5 scaffolded CIFAR adapter — torch-required UNet constructor and
# torch.no_grad() inference path. Production analogue is twodim_fm.py
# (also excluded). Both files are intentionally not mypy-strict-clean
# until the [rf-cifar] extra is wired into the type-checking CI matrix.
"(^|/)adaptive_reflow/adapters/rectified_flow_cifar\.py",
```

The comment + the parallel twodim_fm pattern means the exclusion is self-documenting.

### Commit-order risk — grouping Gate A+B+D could combine unrelated fixes

**What could go wrong:** A reviewer asking "why is this commit touching docs AND mypy config?" would be confused if the three gates are unrelated.

**Mitigation:** The commit message (in §3) explicitly enumerates the three gates and gives each a one-line rationale. The "fix(r5):" prefix signals that all three are part of the same R5-survey workflow round.

---

## §6. Estimated total effort and timeline

| Gate | Effort | Steps | Sequential / Parallel |
|------|--------|-------|----------------------|
| A. check_docs | 5 min | 1 edit + 1 verify | parallel with B and D |
| B. mkdocs nav | 10 min | 1 edit + 1 verify | parallel with A and D |
| C. pytest | 30 min | 3 steps (triage + xfail + importorskip) + 2 verifies | sequential after A+B+D so the doc fixes don't accidentally fail pytest collection; but can also run in parallel since pytest doesn't read pyproject.toml [tool.mypy] config |
| D. mypy | 15 min | 2 edits + 1 verify | parallel with A and B |
| **Total** | **~60 min** | 4 gates × ~15 min avg | **A, B, D can run in parallel; C runs sequentially** |

**Sequencing rationale:** Gates A, B, D are all config / doc-only — they have no interaction with each other and can be done by three sub-agents in parallel (or sequentially by one agent in ~30 min). Gate C requires running pytest, which depends on the rest of the repo being in a stable state; running C in parallel with A/B/D is fine but the **final verification** (the "all 6 gates green" sweep) must be sequential after all four.

**Wall-clock for a single agent doing all four:** ~60 min (mostly the test triage in Step C1).

**Wall-clock for three agents in parallel (one per A+B, C, D):** ~30 min.

---

## §7. Done criteria

**Hard done criteria (binary, all must hold):**

1. `PYTHONPATH=. python tools/check_docs_against_code.py --quiet` exits 0.
2. `python -m mkdocs build --strict` produces no WARNING/ERROR lines.
3. `python -m pytest tests/ -q` exits 0 with `0 failed`.
4. `python -m mypy adaptive_reflow/` reports 0 errors in `rectified_flow_cifar.py` and no NEW errors elsewhere (count reduced by ≥ 41 vs. pre-fix baseline).
5. `python -m ruff check adaptive_reflow/` still exits 0 (regression sentinel).
6. The 6-gate CI run on the post-fix commit is fully green (the canonical bar per `docs/STATUS.md` and `docs/CLAIMS.md`).
7. Both commits (§3) land on `main` and the audit-trail round R5's `docs/r5-survey/` contains this document (`09-gate-fix-plan.md`) and the upstream research (`08-gate-fix-research.md`).

**Soft done criteria (qualitative, encouraged but not blocking):**

- All four fixes have code comments referencing `docs/r5-survey/08-gate-fix-research.md` §X so a future maintainer can trace the rationale.
- The 3 pre-existing pytest failures each have either a fix commit OR an `xfail` decorator with a linked issue number — no silently-xfailed tests.
- The `not_in_nav:` entry is alphabetically ordered (paper-plan.md sits between `lean_issue_re_inference_provenance.md` and `r3-survey/*.md`).

**Out of scope for "done" (flagged but not blocking):**

- The `mnist_fm_weights_path` fixture referenced by `test_mnist_fm.py` is not defined in `tests/test_adapters/conftest.py`. With `importorskip` applied, this latent bug is masked (the tests skip before fixture resolution). **A follow-up round should add a `_materialize_mnist_fm_weights` fixture** mirroring the existing `_materialize_twodim_fm_weights` pattern (conftest.py:22–33) so the test suite works when torch IS installed.
- The `MySotaModelAdapter` illustrative placeholder is preserved in the prose of `docs/paper-plan.md` §4.3 (just no longer backticked). If the user later writes the actual `MySotaModelAdapter` class, they should re-introduce the backticks and re-add it to the denylist if they want it to remain "illustrative."

---

## §8. References

- Phase 1 research: `docs/r5-survey/08-gate-fix-research.md` (cited per-section above).
- check_docs scanner: `tools/check_docs_against_code.py` lines 220–254 (`_is_likely_python_symbol`), 561–617 (`_scan_inline_backticks`).
- mkdocs config: `mkdocs.yml` lines 44–58 (nav:), 123–152 (not_in_nav:), 154–172 (validation:).
- mypy config: `pyproject.toml` lines 229–250 ([tool.mypy]), 252–318 (per-module overrides).
- pytest config: `pyproject.toml` lines 68–83 ([tool.pytest.ini_options]).
- Cited real-world examples (from research): Flax/JAX mkdocs, The Turing Way `--strict`, mkdocs-awesome-pages-plugin, PyTorch Lightning two-tier mypy exclusion, mypy self-check `exclude`, Django mypy exclude pattern, scikit-learn conftest `importorskip`, Hugging Face transformers conftest, PyTorch test convention, Cookiecutter Data Science layout, Reproducible-ML-Experiments Template.
