# Contributing

`flowa-multistep-reinference` is a single-maintainer research project. The
contract layer *is* the product; empirical model behaviour is deliberately
out of scope. This file describes the development workflow, the six pre-merge
gates, and the per-change recipes the maintainer runs on every PR.

Read **[docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)** before
opening a PR. The test layer conventions, marker rules, and the
six-layer suite description live there. **[docs/adr/](docs/adr/)** is the
authoritative record for every architectural decision; if your change
touches a load-bearing boundary, write an ADR first.

---

## 1. Dev environment setup

```bash
# Python 3.12 is the project pin (see pyproject.toml requires-python).
python3.12 -m venv .venv
source .venv/bin/activate           # bash / zsh
# .venv\Scripts\Activate.ps1        # PowerShell on Windows

# ``.[dev]`` brings in mkdocs + mkdocstrings + griffe (the docs-build
# toolchain). pytest, hypothesis, pytest-benchmark, ruff, and mypy are
# pinned transitively by the project metadata and resolve alongside
# the install. PYTHONPATH=. is required at runtime because the project
# is imported by path rather than via a site-packages install.
pip install --upgrade pip
pip install -e '.[dev]'
```

The full suite is **CPU-only and stdlib-first** (see
`docs/TESTING_STRATEGY.md` §1): no GPU runner is needed, no native tensor
library is required for the typed-contracts core. The optional
`[chemistry]` (RDKit) and `[flow_matching]` (NumPy / SciPy) extras are
opt-in model-family adapters; install them only when you actually touch
those modules.

## 2. The six pre-merge gates

Every push to `main` and every PR runs the six gates below via
`.github/workflows/ci.yml`. They must all be green before a change merges.

| # | Gate                            | Local command                                                                                              | What it checks                                                                  |
|---|---------------------------------|------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| 1 | `pytest`                        | `PYTHONPATH=. python -m pytest tests/ -m "not slow and not benchmark" --no-header -q`                      | Full unit + property + adversarial + golden suite; torch-gated files skip cleanly via `pytest.importorskip("torch")`. |
| 2 | `ruff`                          | `ruff check adaptive_reflow/ tests/`                                                                       | E/W/F/I/B/UP/SIM over package + tests; per-file-ignores in `pyproject.toml` cover intentional re-exports and the quarantined `legacy/` tree. |
| 3 | `mypy`                          | `python -m mypy adaptive_reflow`                                                                           | Strict mode over the full `adaptive_reflow` tree; per-module overrides silence upstream rdkit / numpy stub noise. |
| 4 | `check_docs_against_code`       | `PYTHONPATH=. python tools/check_docs_against_code.py`                                                     | Every inline-symbol / code-block / path claim in the governance docs resolves to a real public symbol. |
| 5 | `check_claims_consistency`      | `python tools/check_claims_consistency.py`                                                                 | Every `Asserted by` / `Disputed by` reference in `docs/CLAIMS.md` resolves; ACTIVE claims cross-referenced from at least one governance surface. |
| 6 | `mkdocs build --strict`         | `mkdocs build --strict`                                                                                    | Auto-generated API reference renders cleanly; no broken internal links or unresolved mkdocstrings directives. |

The slow / benchmark / stress markers are intentionally excluded from
the PR-loop pytest gate so the wall-clock stays bounded; they are covered
by the dedicated nightly / weekly jobs (see §5).

## 3. PR process

1. **Branch off `main`.** One logical change per PR; refactors land
   separately from feature work.
2. **Run the six gates locally** (§2). A CI run that fails a gate
   locally-passing change is a CI bug; file it in the PR description.
3. **Push and open the PR.** GitHub Actions runs `ci.yml` automatically;
   the badge in `README.md` reports the status. Branch protection
   requires the `ci` workflow to be green before merge.
4. **Address review comments in the same branch.** Force-push after
   review fixes is fine; squash-merge at the end keeps `main` linear.
5. **Update governance docs in the same commit** as any public-symbol
   addition. The docs scanner (§2 gate 4) refuses to merge a new
   public symbol that is not mentioned in `ARCHITECTURE.md` §4 / §7
   inside a python fenced code block.

## 4. Per-change recipes

### 4.1 How to add a hostile-case test

The six fail-closed hostile cases live in
**[DESIGN_BOUNDARY.md §3](DESIGN_BOUNDARY.md)** and are mirrored as
fixtures in `tests/test_adversarial/`. To add a new one:

1. Add the case to `DESIGN_BOUNDARY.md` §3 with its expected audit code.
2. Add a `tests/test_adversarial/test_<case>.py` file with the fixture
   and the expected fail-closed outcome.
3. Mirror the case in `docs/TESTING_STRATEGY.md` §2.3 so the catalogue
   and the test stay in sync.
4. Run `pytest tests/test_adversarial/ -v` and confirm the new test
   passes (a passing test means the gate stays closed).
5. Update `ROADMAP.md` if the closure is scheduled.

### 4.2 How to write an adapter

The protocol surface is `FlowMatchingODEAdapter` in
`adaptive_reflow.universal.adapter`. The full recipe is in
**[ARCHITECTURE.md §5](ARCHITECTURE.md)** and the worked example is
`ToyLinearAdapter` under `adaptive_reflow/adapters/`. The short form:

1. Subclass `FlowMatchingODEAdapter` and implement the eight-method
   Protocol surface (capabilities handshake + 8 calls + `mechanism_id`).
2. Declare your `supported_channels` and `channel_domains`; the engine
   will fail closed on a domain mismatch.
3. Re-export the new class from `adaptive_reflow/adapters/__init__.py`.
4. Add tests under `tests/test_adapters/test_<your_adapter>.py` covering
   capability handshake, `source_round<0` rejection, and a hostile-case
   test for every capability you do *not* advertise.
5. Run `pytest tests/test_adapters/ -v` and `ruff check adaptive_reflow/`.

Adapters are not allowed to `import torch` or any native tensor library
inside `adaptive_reflow/adapters/`. If your model needs a tensor
library, wrap it behind an opaque `TensorRef` boundary.

### 4.3 How to add a mutation test

Mutation testing is gated by `tools/mutate/mutmut.toml` and runs on the
nightly Linux job (see `docs/TESTING_STRATEGY.md` §2.6). To add a new
mutation target:

1. Add the module path to the `targets = [...]` list in
   `tools/mutate/mutmut.toml`.
2. Bump the target score in `docs/TESTING_STRATEGY.md` §7 only if the
   architectural intent has shifted.
3. Re-run `bash tools/mutate/run_mutmut.sh` locally; surviving mutants
   are filed as follow-ups in `ROADMAP.md`.
4. A surviving mutant in `contracts/` or `universal/` is, by definition,
   a missing test (see ADR-0005) and blocks the PR that introduced it.

### 4.4 How to update the docs scanner catalogue

The scanner at `tools/check_docs_against_code.py` walks every `*.md`
file under the repo root plus `docs/`, extracts CamelCase /
SCREAMING_SNAKE_CASE identifiers and `adaptive_reflow/...` path claims,
and verifies each one resolves to a real public symbol. To keep the
catalogue current:

1. When you add a new public symbol, mention it in `ARCHITECTURE.md`
   §4 or §7 (or the relevant subsection) inside a python fenced code
   block — that's how the scanner picks it up.
2. When you rename or remove a symbol, run
   `PYTHONPATH=. python tools/check_docs_against_code.py` and chase
   the unresolved claims to their source.
3. Never add an inline-backtick reference to a symbol that does not
   exist; the scanner will fail CI on drift.

## 5. Nightly / weekly jobs

These do not block PRs but their artifacts are expected to be triaged:

| Workflow                | Cadence                       | What it does                                            |
|-------------------------|-------------------------------|---------------------------------------------------------|
| `bench-regression.yml`  | Weekly Mon 04:00 UTC + manual | `pytest --benchmark-only` + `tools/bench/check_budgets.py` |
| `mutation-nightly.yml`  | Nightly 03:00 UTC + manual    | `tools/mutate/ast_mutator.py run --target ...` + score gate |
| `stress-nightly.yml`    | Weekly Mon 03:00 UTC + manual | `pytest -m stress` with `HYPOTHESIS_PROFILE=stress`     |
| `docs-deploy.yml`       | push to main (paths-filtered) | `mkdocs build --strict` + GitHub Pages publish          |

A failing mutation report is a follow-up ticket; a failing
bench-regression is a same-day fix.

## 6. Where to ask questions

- **Bugs / design questions**: open a GitHub issue with the
  `discussion` label.
- **Security**: see [`SECURITY.md`](SECURITY.md) for the responsible
  disclosure process; do not file public issues for security-sensitive
  reports.
- **Maintainer contact**: see [`CODEOWNERS`](CODEOWNERS) for the
  per-path review routing.

The maintainer triages issues weekly. PRs that fail any of the six
gates (§2) will not be reviewed until the gate is green; please
run the local equivalents before pushing.
