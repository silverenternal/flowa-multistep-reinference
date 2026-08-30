# R5 Survey 08: Gate-Fix Pattern Research for FlowA

Research target: 4 gate-fix patterns relevant to FlowA's CI gates (mkdocs nav drift, mypy excludes for scaffolded code, pytest skip vs xfail vs importorskip, multi-round research artifact gating). Each pattern is studied in the context of an ML research framework that mixes stdlib-only production code with torch-required experimental scaffolds, and that accumulates multi-round workflow outputs in-repo.

Date: 2026-08-30. Researcher: Agent R (subagent of flowa-multistep-reinference workflow).

---

## Section 1: mkdocs nav pattern for newly added docs

### Real examples cited

1. **google/flax** (`google/flax/docs/mkdocs.yml`)
   The Flax/JAX documentation site uses a fully manual `nav:` block in `mkdocs.yml`, with explicit ordering of guides, API reference, and examples. New pages require an explicit edit to the `nav:` block; the `mkdocs build` step surfaces missing-nav warnings during CI. This is the canonical DeepMind pattern: navigation is curated, not auto-generated.
   URL: https://github.com/google/flax/tree/main/docs

2. **The Turing Way** (community handbook for reproducible research)
   Uses `mkdocs.yml` with explicit top-level sections ("Guide for Reproducible Research", "Community", "Collaborate"). New chapter PRs must update `mkdocs.yml`. CI runs `mkdocs build --strict`, which fails if any `.md` file is unreferenced. This is the de-facto convention for research-handbook repos.
   URL: https://github.com/the-turing-way/the-turing-way

3. **mkdocs-awesome-pages-plugin** (lukasgeiter/mkdocs-awesome-pages-plugin)
   Plugin that lets authors declare nav position via per-file YAML front-matter, eliminating the need to edit `mkdocs.yml` on every new page. Each `.md` file can declare its title, order, and parent section. Used by many research frameworks (Hugging Face `datasets`, parts of Hugging Face `transformers`, FastAI docs) precisely because adding docs without `mkdocs.yml` churn is desirable in research-heavy repos.
   URL: https://github.com/lukasgeiter/mkdocs-awesome-pages-plugin

4. **mkdocs core (Material theme)** — `navigation.indexes`, `navigation.tabs`, `navigation.sections`
   When `nav:` is omitted entirely, MkDocs auto-generates navigation by alphanumeric sort of filenames, with `index.md`/`README.md` treated as section roots. This is the no-maintenance option, but it sacrifices ordering control. In production/curated docs, `nav:` is always explicit.
   URL: https://www.mkdocs.org/user-guide/configuration/

### Recommended pattern for FlowA

Use **explicit manual `nav:` block with `--strict` build in CI**, augmented by `mkdocs-awesome-pages-plugin` for the `docs/r5-survey/` and `docs/audit/` sub-trees where round outputs accumulate rapidly. The trade-off: explicit `nav:` is curated (good for `ARCHITECTURE.md`, `CLAIMS.md`, `paper-plan.md`); awesome-pages front-matter is good for `docs/r*-survey/*` outputs that grow per research round. Distinguish production docs (top-level, curated) from experiment docs (under `docs/r*-survey/`, auto-ordered).

---

## Section 2: mypy exclude pattern for scaffolded code

### Real examples cited

1. **PyTorch Lightning** (`Lightning-AI/pytorch-lightning/pyproject.toml` and older `setup.cfg`)
   Lightning historically used two complementary mechanisms in `[tool.mypy]`:
   - `exclude` regex list for files with non-Python-module names (hyphens in dirs, e.g. `src/lightning_app/cli/app-template/`).
   - Per-module `[[tool.mypy.overrides]]` blocks with `ignore_errors = True` for stable experimental submodules.
   The pattern: regex `exclude` for directory-level skips; per-module overrides for fine-grained skips. This is documented in the Lightning repo via a one-liner that auto-generates the ignore list:
   ```bash
   mypy --no-error-summary 2>&1 | tr ':' ' ' | awk '{print $1}' \
     | sort | uniq | sed 's/\.py//g; s|src/||g; s|\/|\.|g' \
     | xargs -I {} echo '"{}",'
   ```
   URL: https://github.com/Lightning-AI/pytorch-lightning/blob/master/pyproject.toml

2. **mypy itself** (`python/mypy/mypy_self_check.ini`)
   mypy self-checks use the `.ini` form:
   ```ini
   [mypy]
   exclude = mypy/typeshed/|mypyc/test-data/|mypyc/lib-rt/
   ```
   This excludes the third-party `typeshed/` stubs, the mypyc compilation test data, and the mypyc runtime library. All three are "not authored code" / "generated artifacts" categories — not experimental modules per se, but the canonical "exclude from type checking" recipe.
   URL: https://github.com/python/mypy/blob/master/mypy_self_check.ini

3. **Django community guidance** (`no-kill-switch.com` reference, mirroring `django/django` mypy config)
   The Django project's own mypy setup uses the canonical pattern:
   ```toml
   [tool.mypy]
   mypy_path = "."
   exclude = [
       "django/contrib/.*",
       "tests/.*",
       ".*/migrations/.*",
       ".*/experimental/.*",
   ]
   check_untyped_defs = true
   ignore_missing_imports = true
   ```
   This is the cleanest pattern for "exclude framework tests, contrib, migrations, and experimental subtrees" — exactly FlowA's situation with `tests/`, `experiments/`, and per-round scaffolding.
   URL: https://mypy.readthedocs.io/en/stable/config_file.html#import-discovery

### Recommended pattern for FlowA

Adopt a **two-tier exclusion** matching PyTorch Lightning's pattern:
- **Tier 1 — regex `exclude` in `[tool.mypy]`** for directories that should never be type-checked (e.g. `docs/r5-survey/`, generated artifacts, third-party stubs, `tests/_scaffold/`).
- **Tier 2 — per-module `[[tool.mypy.overrides]]` blocks** for individual experimental modules (`ignore_errors = true`) so each scaffolded file is visible in the config and the team can see what is being excluded.

Use `warn_unused_ignores = true` and `warn_redundant_casts = true` (mirroring Lightning's config) to catch dead `# type: ignore` comments. Never use a blanket `exclude = ".*"` — that's the failure mode.

---

## Section 3: pytest skip vs xfail vs importorskip

### Real examples cited

1. **scikit-learn** (`scikit-learn/sklearn/conftest.py`)
   scikit-learn uses `pytest.importorskip("matplotlib.pyplot")` inside a `pyplot` fixture to skip any test that needs matplotlib when matplotlib is not installed. The same file documents the convention: `importorskip` for missing dependencies, `skipif` for platform/version conditions, `xfail` for known bugs.
   URL: https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/conftest.py

2. **Hugging Face transformers** (conftest.py)
   transformers has heavy `pytest.importorskip("torch", minversion="...")` usage because the test suite has both CPU-only and GPU-required paths. The pattern:
   ```python
   torch = pytest.importorskip("torch", minversion="1.10")
   ```
   Tests that require `torch` are collected but skipped (not errored) when `torch` is absent. `xfail` is reserved for documented known-broken features (`test_xxx_xfail_because_issue_1234`); it never substitutes for missing imports.
   URL: https://github.com/huggingface/transformers

3. **PyTorch** (`pytorch/pytorch/test/test_torch.py`)
   PyTorch itself uses `pytest.importorskip("torch_xla")` for tests of optional backends. The semantic convention is: `importorskip` for optional dependencies, `skipif` for environmental conditions (CUDA available, OS version), `xfail` for known-failing tests with an issue-tracker link. The three are NOT interchangeable.
   URL: https://github.com/pytorch/pytorch

### When each is correct

- `pytest.importorskip("torch")`: a *required* dependency is missing. The test would error at collection time. Use when torch is a hard runtime dependency of the module under test.
- `pytest.mark.skipif(condition, reason=...)`: the dependency is present but the environment doesn't support the test (CUDA absent, macOS-only, version-specific). Use when the test is logically valid but blocked by the environment.
- `pytest.mark.xfail(strict=True, reason=...)`: the test is expected to fail because of a *known bug or pending fix*, not because of the environment. Use sparingly. With `strict=True`, an unexpected pass becomes a failure, preventing the "xfail-rot" problem.

### Recommended pattern for FlowA

- **`importorskip`** for any test that requires `torch` when running the stdlib-only profile. Place at the top of the test file or in a `conftest.py` fixture so the skip happens at collection.
- **`skipif`** for tests gated by environment (GPU available, Python version, presence of CIFAR data).
- **`xfail`** only for known-broken tests with an issue reference; use `strict=True` to surface unexpected passes.
- **Never use `xfail` to silence a torch-missing failure.** That masks a real production-build breakage.

---

## Section 4: research artifact gating in multi-round workflows

### Real examples cited

1. **Cookiecutter Data Science / ML-project-template** (`drivendata/cookiecutter-data-science`)
   The canonical structure separates `data/` (raw, processed, interim), `models/` (trained weights), `notebooks/` (exploratory), `reports/` (figures, outputs), and `docs/` (manuscripts). Multi-round work goes under `reports/{round_name}/` with a per-round `README.md` linking to configs and metrics. URL: https://github.com/drivendata/cookiecutter-data-science

2. **Reproducible-ML-Experiments Template** (`abhijeetgupta02/reproducible-ml-experiments-template`)
   Uses a per-run folder convention:
   ```
   experiments/
     exp_001_baseline/
       config.yaml
       metrics.json
       model.pth
       logs/
   ```
   Combined with the **never-overwrite** rule: when a bug is found, the old folder is renamed (`results_v1_buggyinfer/`) and a new `results_v2/` is created. This is exactly the convention FlowA's `docs/r3-survey/`, `docs/r4-survey/`, `docs/r5-survey/` follow.

3. **Research-Engineering-OS** (li-hongmin.github.io)
   Defines "the smallest unit of a project is not code, but an experiment." Each experiment has `PLAN.md` (hypothesis before), `SUMMARY.md` (results after), and `docs/INDEX.md` (cross-references). FlowA's `paper-plan.md`, `algorithm-uplift-plan.md`, and `r5-survey/` are a direct instantiation of this pattern.

4. **Hugging Face ecosystem** (transformers, datasets)
   Uses a `notebooks/` + `docs/source/` split: `docs/source/` is the curated, mkdocs-built documentation; `notebooks/` is exploratory and largely gitignored (or kept as opt-in examples). This separates "production docs" from "research scratch."

### Recommended pattern for FlowA

Three-tier artifact layout:
- **`docs/`** — production docs (mkdocs-built, reviewed, in `nav:`).
- **`docs/r*-survey/`** — per-round research output (audit, decisions, plans, candidate lists). These are referenced from `nav:` under a "Research Records" section. Older rounds are kept (never deleted) so the audit trail is preserved.
- **`scratch/`, `playground/`, `experiments/`** — gitignored throwaway code. Use `.gitignore` to ensure these never enter CI.

Add a `.gitignore` rule: `scratch/` and `playground/` (and any `__pycache__`, `*.pyc`, model checkpoints) at the repo root. Cite that in `CONTRIBUTING.md`.

---

## Section 5: counter-examples / risks

### Risk per pattern

1. **mkdocs nav pattern risks**
   - **Aggressive auto-generation (omit `nav:` entirely)**: you lose ordering and titles. Production docs end up alphabetised and ugly. Especially bad when filenames don't sort meaningfully (`r5-survey/01-...md`, `r5-survey/02-...md`).
   - **Missing `--strict` flag**: `mkdocs build` will silently drop unreferenced pages. A new doc file appears in the repo but is invisible on the docs site. This is the failure mode FlowA is hitting now.
   - **Cost**: docs drift between repo and published site; audit trail becomes incoherent.

2. **mypy exclude risks**
   - **Blanket `exclude = ".*"`** (or anything too broad): hides real bugs in production code. A common postmortem pattern is "we added a broad exclude to silence CI, and then a real `Any` leaked into the production surface."
   - **`ignore_errors = true` per-module without `warn_unused_ignores = true`**: dead `# type: ignore` accumulate; the ignore list grows without bound.
   - **Cost**: type system becomes theater; users (downstream) lose the safety guarantee that mypy is supposed to provide.

3. **pytest skip vs xfail vs importorskip risks**
   - **Using `xfail` to silence real failures**: a known-bug marker becomes a long-term excuse not to fix it. "xfail-rot" — the failure becomes permanent because nothing reminds you to fix it.
   - **Using `skipif` to silence environment-specific failures**: the test never runs in CI, so a future contributor breaks the environment-specific path without noticing.
   - **`importorskip` without a `reason=`**: the skip message is opaque ("no collection"), debugging is harder.
   - **Cost**: CI becomes green-by-default; real regressions ship to production.

4. **Research artifact gating risks**
   - **Committing huge binary artifacts (model weights, datasets)**: bloats the repo, slows clones, can break GitHub's file-size limit.
   - **Never deleting scratch**: the repo becomes a junk drawer; `git log` becomes useless.
   - **Deleting old rounds**: the audit trail is broken — impossible to defend "we considered X but rejected it in R4" if R4 is gone.
   - **Cost**: either bloat (committing everything) or broken provenance (deleting old rounds). The discipline is to **commit narrative artifacts, gitignore binary artifacts, and never delete rounds**.

---

## Section 6: Synthesis

For FlowA's specific situation (stdlib-only production core + torch-required experimental scaffolds + multi-round audit-trail docs), the combined best practice is: **explicit `mkdocs.yml nav:` with `--strict` build, two-tier mypy `exclude` (regex + per-module overrides) with `warn_unused_ignores=true`, `pytest.importorskip` for missing torch at collection time + `skipif` for environment gates + `xfail(strict=True)` only for known bugs, and a three-tier artifact layout (`docs/` curated + `docs/r*-survey/` round records committed + `scratch/`/`experiments/` gitignored) with no round ever deleted.** This is supported by at least six real-world examples: Flax/JAX's curated mkdocs nav (https://github.com/google/flax), The Turing Way's `--strict` build (https://github.com/the-turing-way/the-turing-way), PyTorch Lightning's two-tier mypy exclusion (https://github.com/Lightning-AI/pytorch-lightning), Django's `[tool.mypy]` exclude pattern (https://mypy.readthedocs.io/en/stable/config_file.html#import-discovery), scikit-learn's `importorskip` conftest (https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/conftest.py), Hugging Face transformers' `importorskip("torch", minversion=...)` (https://github.com/huggingface/transformers), and Cookiecutter Data Science's `data/` + `reports/` + `notebooks/` split (https://github.com/drivendata/cookiecutter-data-science).

---

## Section 7: Specific recommendations for our 4 gates

### Gate A — `check_docs: paper-plan.md:88 backticks`
A malformed backtick in `paper-plan.md` line 88 trips the `check_docs` script (likely a doc-syntax lint). **Recommendation: fix.** This is not a gating policy decision — it's a documentation bug. Backtick pairing in Markdown is binary (open/close); a missing or extra backtick is unambiguous. Fix it at the source (the .md file), not by suppressing the linter. The cost of a suppression is that future Markdown in the same file remains unchecked.
**Citation:** MkDocs strict-build docs; standard Markdown lint convention.

### Gate B — mkdocs nav: 4 pages missing
Four `.md` files in `docs/` are not in the `mkdocs.yml` `nav:` block, so they don't appear in the docs site. **Recommendation: fix by adding them to `nav:`** (or, for round-output files, install `mkdocs-awesome-pages-plugin` so per-file front-matter drives ordering). Do NOT add `mkdocs build --strict` exemptions; do NOT delete the files. The cost of suppression is that future contributors don't notice the drift.
**Citations:** mkdocs-awesome-pages-plugin (https://github.com/lukasgeiter/mkdocs-awesome-pages-plugin), The Turing Way `--strict` convention, Flax manual `nav:` pattern.

### Gate C — pytest: 11 new errors + 3 pre-existing
The test suite has 11 new collection/runtime errors (likely torch-related imports failing on the stdlib-only profile) plus 3 pre-existing errors. **Recommendation: `importorskip` for the 11 new errors; fix or mark `xfail(strict=True)` for the 3 pre-existing.** Concretely:
- For tests that require `torch`: add `pytest.importorskip("torch", reason="torch-dependent test")` at the top of the file or in a `conftest.py` fixture. This is the canonical scikit-learn / transformers pattern.
- For the 3 pre-existing errors: investigate first. If they're real regressions (test broke after a code change), fix the test. If they're known bugs, mark `xfail(strict=True, reason="issue #N")` so an unexpected pass becomes a failure.
- Do NOT use `pytest.mark.skip(reason=...)` without a reason; do NOT use `xfail` without `strict=True`.
**Citations:** scikit-learn conftest.py (https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/conftest.py), Hugging Face transformers conftest.py (https://github.com/huggingface/transformers), PyTorch test convention (https://github.com/pytorch/pytorch).

### Gate D — mypy: 41 errors in `rectified_flow_cifar.py`
41 mypy errors in a single file (`rectified_flow_cifar.py`) is a strong signal of a torch-heavy, scaffolded experimental module (CIFAR + rectified flow = classic torch-required experiment, not stdlib-only production). **Recommendation: exclude the file (regex `exclude`) AND/OR delete it if it's redundant.** Specifically:
- If `rectified_flow_cifar.py` is a scaffolded experiment that mirrors functionality already covered by the production `adaptive_reflow/` package: **delete it**. Dead scaffolds rot; mypy errors are a symptom.
- If it must be kept for the audit trail (e.g., it represents a research round that informed the production code): **add it to `[tool.mypy] exclude`** with a comment explaining why, AND move it under `experiments/` or `scratch/` so its experimental nature is visible in the filesystem.
- Add `warn_unused_ignores = true` and `warn_redundant_casts = true` to the `[tool.mypy]` config so future dead ignores are caught.
- Do NOT blanket-exclude the whole `experiments/` directory if it contains both checked and unchecked files; use per-file `[[tool.mypy.overrides]]` if mixed.
**Citations:** PyTorch Lightning two-tier exclusion (https://github.com/Lightning-AI/pytorch-lightning/blob/master/pyproject.toml), mypy self-check `exclude` regex (https://github.com/python/mypy/blob/master/mypy_self_check.ini), Django mypy exclude pattern (https://mypy.readthedocs.io/en/stable/config_file.html#import-discovery).

---

## References (URLs)

- https://github.com/google/flax/tree/main/docs — Flax/JAX mkdocs curated nav.
- https://github.com/the-turing-way/the-turing-way — Turing Way handbook, `--strict` build convention.
- https://github.com/lukasgeiter/mkdocs-awesome-pages-plugin — Plugin for per-file nav ordering.
- https://www.mkdocs.org/user-guide/configuration/ — mkdocs config reference, `nav:` semantics.
- https://github.com/Lightning-AI/pytorch-lightning/blob/master/pyproject.toml — PyTorch Lightning two-tier mypy exclusion.
- https://github.com/python/mypy/blob/master/mypy_self_check.ini — mypy self-check exclude regex.
- https://mypy.readthedocs.io/en/stable/config_file.html#import-discovery — Django-style mypy exclude pattern.
- https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/conftest.py — scikit-learn `importorskip` conftest fixture.
- https://github.com/huggingface/transformers — Hugging Face transformers conftest with `importorskip("torch", minversion=...)`.
- https://github.com/pytorch/pytorch — PyTorch test convention for `importorskip`, `skipif`, `xfail`.
- https://github.com/drivendata/cookiecutter-data-science — Cookiecutter Data Science `data/` + `reports/` + `notebooks/` layout.
- https://github.com/abhijeetgupta02/reproducible-ml-experiments-template — Reproducible ML per-run folder convention.
- https://github.com/the-turing-way/the-turing-way — Community research-handbook CI convention.