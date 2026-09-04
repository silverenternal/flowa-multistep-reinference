# Releasing flowa-multistep-reinference

This document captures the full release process for the
`flowa-multistep-reinference` package on PyPI. The package is
intentionally research-stage (`Development Status :: 3 - Alpha` per
`pyproject.toml`) and ships a **dry-run release workflow**: builds
and metadata checks happen locally and on CI, but the actual
`twine upload` is gated on paper acceptance and executed manually.

The dry-run mode (build -> twine check, no upload) is the only path
this document endorses until the paper has been accepted.

## Audience

This document is for the project maintainer (and any future co-
maintainers). It assumes Python 3.12, the project virtualenv at
`.venv/`, and write access to the GitHub repository and the PyPI
project page.

## Pre-release checklist

All six gates must be green on the release commit. The gates are
the same six gates that run on every PR (`docs/CLAIMS.md`
CLM-019 / CLM-020 / CLM-021 / CLM-041 are the load-bearing ones
per the README "Six gates (load-bearing)" section):

1. **pytest** — `python -m pytest -q` reports 1235 passed, 7 skipped
   (torch-gated). The 7 skips are expected and documented in the
   PyTorch-gated test inventory in `tests/_utils/`.
2. **ruff** — `python -m ruff check .` reports 0 violations. The
   project policy is "0 violations, no warnings silenced to land a
   release"; if a gate violation is unjustified, fix the code; if
   justified, add an inline `noqa` + a comment referencing the
   fix-plan issue number.
3. **mypy (adaptive_reflow)** — `python -m mypy adaptive_reflow`
   reports 0 errors. The `legacy/` and `rdkit_oracle/` modules are
   excluded by configuration; see `pyproject.toml` `[tool.mypy]`
   `exclude` and `[[tool.mypy.overrides]]` for the rationale.
4. **docs scanner** — `python tools/check_docs_against_code.py`
   reports clean. The scanner walks every `Asserted by` reference
   in `docs/CLAIMS.md` and verifies it resolves to a real file:line.
5. **claims consistency** — `python tools/check_claims_consistency.py`
   reports clean (32 active / 0 provisional / 2 deprecated expected).
   The script auto-promotes `Disputed by` references to
   `PROVISIONAL` and exits 1 on drift.
6. **mkdocs `--strict`** — `python -m mkdocs build --strict` exits 0.
   `mkdocs.yml` `not_in_nav` and explicit nav must agree; the
   r4-survey/18-19 docs moved into the explicit nav as part of
   the Phase-4 audit (CHANGELOG entry dated `2026-08-31`).

After the six gates are green:

- [ ] `pyproject.toml` `version` field is bumped to the target
      release (this document assumes 0.1.0 for the first publish).
- [ ] `CHANGELOG.md` `[0.1.0]` (or higher) entry exists at the
      bottom of the file, above "How to read this changelog".
      The entry must list every user-visible surface, every
      optional-dependency extra, the gate impact at release time,
      and a link to the full git history.
- [ ] `LICENSE` file exists at the repo root. The shipped license
      is MIT (Copyright (c) 2026 silverenternal); SPDX expression
      in `pyproject.toml` is `"MIT"` and the
      `license-files = ["LICENSE", "LICENSE-*"]` glob includes
      the canonical file.
- [ ] `pyproject.toml` PEP 621 metadata is complete:
      `name`, `version`, `description`, `readme`, `requires-python`,
      `license`, `authors`, `keywords`, `classifiers`,
      `[project.urls]` (Homepage, Repository, Documentation, Issues,
      Changelog). All five URL fields must resolve to a live page.
- [ ] `dist/` is in `.gitignore` so wheel + sdist artifacts are
      never committed.
- [ ] Git working tree is clean on the release commit
      (`git status --porcelain` returns nothing).

## Build

```bash
# From the repo root. ``build`` and ``twine`` are pinned at the
# versions used for the dry-run; install them if missing.
uv pip install build hatchling twine

# Build sdist + wheel into ./dist. ``build`` will resolve the
# [build-system].requires from pyproject.toml and provision an
# isolated build venv with hatchling in it.
python -m build --outdir dist
```

The expected output is:

```
* Building sdist...
* Building wheel from sdist
* Building wheel...
Successfully built flowa_multistep_reinference-0.1.0.tar.gz and flowa_multistep_reinference-0.1.0-py3-none-any.whl
```

`dist/flowa_multistep_reinference-0.1.0-py3-none-any.whl` and
`dist/flowa_multistep_reinference-0.1.0.tar.gz` are the artifacts
to upload. Both must pass `twine check` (below).

## Twine check (dry-run gate)

```bash
python -m twine check dist/*
```

Expected output:

```
Checking dist/flowa_multistep_reinference-0.1.0-py3-none-any.whl: PASSED
Checking dist/flowa_multistep_reinference-0.1.0.tar.gz: PASSED
```

If either artifact fails, the README rendering or the metadata
schema is wrong. Common failures:

- `long_description_not_valid_rst` — the README has an RST/Sphinx
  construct (e.g. `.. code-block::`) that is not valid CommonMark;
  trim the offending block.
- `long_description_has_invalid_markdown` — a fenced code block has
  an unclosed ``` or an HTML tag is not balanced.
- `classifiers_deprecated` — a PyPI classifier in `classifiers = [...]`
  has been removed from the canonical list; remove it.
- `license_non SPDX` — the `license = "..."` value is not a valid
  SPDX expression; check against
  <https://spdx.org/licenses/>.

## Upload (gated on paper acceptance)

**DO NOT run this command until the paper has been accepted.** The
project ships research-stage code (`Development Status :: 3 - Alpha`)
and the 0.1.0 publish is intentionally held back from public PyPI
until the paper has been accepted at a peer-reviewed venue.

```bash
# Upload to PyPI. --repository pypi is the default; the
# TWINE_USERNAME and TWINE_PASSWORD env vars (or a keyring-backed
# token via ``keyring set https://upload.pypi.org/legacy/__token__``)
# are required.
python -m twine upload dist/*
```

For Test PyPI first-time validation (optional):

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ \
    flowa-multistep-reinference
```

## Post-release verification

After upload, verify the public surface matches the manifest in
`CHANGELOG.md` `[0.X.Y]`:

1. **PyPI landing page** — open
   <https://pypi.org/project/flowa-multistep-reinference/> and
   confirm the README renders correctly (the long description),
   the classifiers are shown, the project URLs are clickable, and
   the license is MIT.
2. **Wheel install** — in a fresh venv (Python 3.12 only):
   ```bash
   python -m pip install flowa-multistep-reinference
   python -c "from adaptive_reflow.contracts import RoundResultBundle; print(RoundResultBundle)"
   ```
   The import must succeed; the printed class identity confirms the
   wheel was assembled correctly.
3. **Optional-dependency extras** —
   ```bash
   python -m pip install 'flowa-multistep-reinference[flow_matching]'
   python -m pip install 'flowa-multistep-reinference[chemistry]'
   python -m pip install 'flowa-multistep-reinference[dev]'
   ```
   Each extra must install cleanly. The `[chemistry]` extra pulls
   in RDKit (~25 MB compiled wheel) — confirm the user opted in.
4. **CLI entry point** — `which claims-consistency` (POSIX) /
   `where claims-consistency` (Windows) returns a path under
   the virtualenv's `Scripts/` (Windows) or `bin/` (POSIX)
   directory.
5. **GitHub release tag** — push the release commit as
   `v0.1.0` (or matching version) and create a GitHub release
   linking to the `CHANGELOG.md` `[0.1.0]` entry.

## Rollback procedure

PyPI does not allow deletion of a published version, only
*yanking* (which hides the version from `pip install` but does
not remove already-downloaded wheels from caches).

If a critical bug is found post-publish:

1. **Yank the bad version** — this prevents new installs but does
   not affect existing users:
   ```bash
   python -m twine yank flowa-multistep-reinference==0.1.0
   ```
2. **Cut a fix release** — bump `pyproject.toml` to `0.1.1`,
   add a `[0.1.1] - YANKED-FIX` `CHANGELOG.md` entry describing
   the regression + the fix, re-run the six gates, and re-publish.
3. **If the bug is in the README / metadata only** (no code
   change required), yank + bump to `0.1.1` with an empty
   `[0.1.1] - rebuild` changelog entry and re-upload
   a fresh wheel.
4. **If the bug is paper-blocking** (e.g. an evaluator reports
   wrong numbers), yank + bump to `0.1.1` + revert the offending
   commit on a new branch + add a regression test that fails on
   the bad version + re-publish.
5. **Document the incident** — append a `### Yanked` subsection
   under the affected `CHANGELOG.md` version with the yank date,
   reason, and link to the fix commit.

## Dry-run verification (this release)

The 0.1.0 dry-run was executed on `2026-08-31` with the following
results (mirrored in the verification log):

| Step | Result |
|---|---|
| `python -m build --outdir dist` | sdist OK + wheel OK |
| `python -m twine check dist/*` | PASSED (both artifacts) |
| `python -m zipfile -l dist/*.whl` | `adaptive_reflow/` + `tools/` + `tests/` + `README.md` + `CHANGELOG.md` + `LICENSE` |
| `dist/` in `.gitignore` | YES |
| 6 gates | all green |
| `twine upload` | NOT EXECUTED (gated on paper acceptance) |

## Paper grounding (the release artefact carries an inventory)

The release ships the framework's paper-statement inventory
(`docs/theory/PAPER_INVENTORY.md`, A.0) and the per-equation citation
checker (`tools/check_doc_paper_refs.py`, E.2). Concretely:

* **Theorem 1** (BL-convergence of `mu_{g,eps}` to `nu_g`, `paper section 3.1`)
  is implemented in `adaptive_reflow/theory/rate_bound.py` and
  surface-tested by `tests/test_theory/test_rate_bound.py`.
* **Lemma 2**, **Lemma 4**, **Lemma 5** (sheet evidence `A_g`,
  physical-complement suppression, root-cell packing `B_g` + exterior
  gap `e_rho`) ground the per-round scheduler choices and are
  exhaustively enumerated in A.0.
* **Proposition 3** (selection-mechanism display, `paper section 4.2`)
  and **Proposition 6** (escaping-sharpness bound) are paired with
  must-fail fixtures under `tests/test_theory/negative/`.

The first release that follows paper acceptance must include a
`[0.X.Y]` CHANGELOG entry that names every A.0 statement shipped and
its mapping to a `tests/test_theory/` test (this is the A.1 / A.5
content of the release manifest, not just the version bump).

The package is **not** uploaded as of `2026-08-31`. The release is
held back until paper acceptance; the build artifacts in `dist/`
are valid and ready for upload on the maintainer's `twine upload`
command.