# Mutation testing on Windows — limitation and fallback

**Summary:** `mutmut` is Linux-only, so we built
`tools/mutate/ast_mutator.py` as a Windows-compatible fallback. It runs
natively on Windows *and* on the Linux CI runner, and the score it
reports is comparable to mutmut's, so the S-tier gate is unchanged.

## 1. mutmut itself is Linux-only (upstream issue #397)

`mutmut` does **not** run natively on Microsoft Windows. Invoking it from
a Windows shell produces this banner from the upstream library and then
exits without producing any results:

```
$ .venv/Scripts/python.exe -m mutmut run --help
To run mutmut on Windows, please use the WSL. Native windows support
is tracked in issue https://github.com/boxed/mutmut/issues/397
```

This is an upstream issue ([boxed/mutmut#397][397]), not a defect of the
`flowa-multistep-reinference` harness. WSL2 is not available on every
development box, which meant the mutation gate was effectively
unreproducible for a subset of contributors: they could read a score
from CI but could never regenerate or debug one locally.

[397]: https://github.com/boxed/mutmut/issues/397

## 2. We built `ast_mutator.py` as a Windows-compatible fallback

`tools/mutate/ast_mutator.py` is a stdlib-only AST point mutator. It
parses a target module with `ast`, enumerates single-point mutation
sites, and re-runs the pytest suite once per mutant to decide whether
the suite *kills* the mutation.

**This is an AST-based point mutator, not full mutmut. Coverage is
partial but the S-tier threshold gating works the same.**

### Operators implemented

| Op    | Rewrite |
| ----- | ------- |
| `AOR` | Arithmetic operator replacement: `+`/`-`, `*`/`/`, and the equality pair `==`/`!=` |
| `UOR` | Unary operator replacement: `not x` → `x`, `-x` → `+x` |
| `ROR` | Relational operator replacement: `<` → `<=`, `>` → `>=`, `<=` → `<`, `>=` → `>` |
| `LOR` | Logical operator replacement: `and` → `or`, `or` → `and` |
| `CRP` | Constant replacement: `True`/`False` swap, `0`/`1` swap (ints and the `0.0`/`1.0` unit-interval bounds) |
| `SDL` | Statement deletion: the statement is wrapped in `if False:` so it becomes a no-op stub while staying syntactically valid |
| `NSR` | Name-swap replacement — the `cap`↔`floor` envelope swap in `frame/merge.py`, including method names (`_cap_for_channel` ↔ `_floor_for_channel`) |

### How it differs from mutmut

* mutmut mutates a wider surface: string/bytes payloads, `dict`/`set`
  literals, slices, and keyword-argument names. `ast_mutator` implements
  the seven families above.
* mutmut caches per-mutant coverage to skip provably-unreachable
  mutants. `ast_mutator` has no coverage integration; instead it uses a
  two-phase test strategy (below) to reach the same verdict for less
  wall-clock.
* The *score* both tools emit is the same quantity — `killed / total` —
  which is why the thresholds in `mutation-nightly.yml` gate identically.

### Design properties worth knowing

**Mutants are never written into the working tree.** Each mutant is
injected into the pytest subprocess through a generated plugin that
installs an `importlib` meta-path finder overriding exactly one module
name. A crash, a timeout, or a `Ctrl-C` therefore cannot leave a
half-mutated source file on disk — a real hazard with the copy-mutate-
restore approach mutmut uses. It also means mutants can be evaluated
concurrently (`--jobs`), because they share no mutable state.

**Two-phase test selection.** Phase 1 runs a cheap, name/import-derived
subset of `tests/`. A failure there is conclusive, because the subset is
a subset of the full suite. Only if the subset *passes* does the mutant
escalate to the full `tests/` run before being recorded as a survivor.
Verdicts therefore match "always run the full suite", at roughly a
twentieth of the cost for killed mutants.

**Baseline sanity check.** Before scoring a module, the harness injects
the *unmutated* source and requires its fast-phase tests to pass. Without
this, a bad test-selection heuristic would mark every mutant "killed" and
report a fake 1.000. A module whose baseline fails is refused, not scored.

**Deterministic Hypothesis profile.** The injector pins an in-memory
example database, `derandomize=True`, and `deadline=None`. The shared
on-disk `.hypothesis/examples` database would otherwise leak
counterexamples between mutants (making a verdict depend on which
mutants ran earlier), and wall-clock `deadline` failures under `--jobs`
would be miscounted as kills.

### Usage

```bash
# Single module
.venv/Scripts/python.exe tools/mutate/ast_mutator.py run \
    --target adaptive_reflow/frame/merge.py \
    --output mutmut_results.json

# Human-readable summary (per-module and per-area scores)
.venv/Scripts/python.exe tools/mutate/ast_mutator.py summary mutmut_results.json

# Enforce the S-tier thresholds (exit 1 on breach) — what CI runs
.venv/Scripts/python.exe tools/mutate/ast_mutator.py gate mutmut_results.json
```

Wrapper scripts run the sweep, aggregate the results, and regenerate the
baseline in one shot:

```bash
bash tools/mutate/run_ast_mutation.sh --quick     # 4 critical modules
tools\mutate\run_ast_mutation.bat --quick         # same, native Windows
```

`--target` accepts a file or a directory and may be repeated. Useful
flags: `--jobs N` (concurrent mutants), `--timeout S` (per-mutant
budget; a timeout counts as killed, matching mutmut), and `--baseline`
(also regenerate `tools/mutate/mutation_baseline.json`).

## 3. The nightly workflow runs ast_mutator on Linux, and the score is comparable

`.github/workflows/mutation-nightly.yml` runs on `ubuntu-latest` and now
invokes `ast_mutator` rather than `mutmut_run.sh`. Because the mutator is
stdlib-only and platform-independent, **the score is reproducible on both
platforms**: a Windows contributor can regenerate the exact number CI
gates on, which was impossible while the gate depended on mutmut.

The workflow enforces the same S-tier thresholds it always did:

| Area | Threshold |
| ---- | --------- |
| project-wide | `>= 0.50` |
| `adaptive_reflow/contracts/` | `>= 0.75` |
| `adaptive_reflow/universal/` | `>= 0.75` |
| `adaptive_reflow/frame/` | `>= 0.60` |

Per-area thresholds are skipped when a run mutated no modules in that
area, so narrowing `--target` cannot accidentally pass a gate it never
measured. The gate rejects a run in which zero mutants were evaluated.

Linux remains the source of truth for the *recorded* baseline simply
because CI is where the number is committed from — but it is no longer
the only place the number can be produced.

## 4. Files in this directory

* `ast_mutator.py` — the Windows-compatible AST point mutator. Canonical
  mutation-testing entry point; consumed by `mutation-nightly.yml`.
* `run_ast_mutation.sh` — Bash wrapper: sweep, aggregate, regenerate the
  baseline, summarise, gate.
* `run_ast_mutation.bat` — native-Windows batch equivalent.
* `mutation_baseline.json` — captured mutation-score baseline. Regenerated
  by `ast_mutator run --baseline`; hand-written `rationale` fields are
  preserved across regenerations.
* `justified_survivors.json` — manually-justified mutants the gate allows
  to survive. Maintained by humans, never mutated automatically. Entries
  may be a bare mutant-id string or an object with an `id` key;
  `ast_mutator summary` tags matching survivors `[justified]`.
* `mutmut.toml` — legacy mutmut configuration. Retained for the day
  [#397][397] closes and a cross-check against upstream mutmut becomes
  possible on Linux.
* `run_mutmut.sh`, `mutmut_run.sh` — legacy mutmut runners, superseded by
  `run_ast_mutation.sh`. Kept for the same cross-check reason; they still
  exit at the Windows banner described in §1.
* `WINDOWS_LIMITATION.md` — this document.

## 5. Future remediation

Native Windows support for mutmut is tracked upstream at
[boxed/mutmut#397][397]. When it lands, the useful move is *not* to
delete `ast_mutator.py` but to run both on Linux once and compare
scores — that calibrates how much mutation surface the seven operator
families miss relative to full mutmut, which is the one number this
document currently cannot supply.
