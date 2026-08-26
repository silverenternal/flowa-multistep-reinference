# Contributing

`flowa-multistep-reinference` is a single-maintainer research project. The
contract layer *is* the product; empirical model behaviour is deliberately
out of scope. This file describes the four workflows the maintainer runs
on every change.

Read **[docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)** before
opening a PR. The test layer conventions, marker rules, and the
six-layer suite description live there. **[docs/adr/](docs/adr/)** is the
authoritative record for every architectural decision; if your change
touches a load-bearing boundary, write an ADR first.

## 1. How to add a hostile-case test

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

## 2. How to write an adapter

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

## 3. How to add a mutation test

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

## 4. How to update the docs scanner catalogue

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

## Local gate before pushing

```
PYTHONPATH=. ./.venv/Scripts/python.exe -m pytest tests/ --no-header -q
PYTHONPATH=. ./.venv/Scripts/python.exe tools/check_docs_against_code.py
.venv/Scripts/ruff.exe check adaptive_reflow/ tests/
```

All three must be green. The nightly mutation and weekly bench jobs do
not block the PR but their artifacts are expected to be triaged.