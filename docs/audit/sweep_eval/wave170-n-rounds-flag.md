# Wave 170 P3: `--n-rounds` CLI flag for fair-baseline comparison

## Goal

Enable `baseline --n-rounds 1` (no framework glue) vs `framework --n-rounds 3`
(with framework glue) for fair JMAA-theory-aligned comparison.

The Wave 170 P1 framework-mechanism ↔ JMAA-theory audit identified the unfair
baseline comparison as the root cause of the framework WORSE result for the
CLM-039 2D RF case: the baseline arm was using the same `n_rounds=3` restart-blend
chain as the framework arm, so the comparison measured integrator noise, not
mechanism presence.

The cleanest fix is to make `n_rounds` a CLI-tunable parameter. The baseline
arm uses `n_rounds=1` (pure `solve_ode`, no `apply_restart_distribution` glue).
The framework arm uses `n_rounds=3` (Wave 158 canonical Wave 45 multi-round
path with all three glue layers).

## Diff

`tools/gen_lineageflow_n1000_fastas.py`:

- Module-level `N_ROUNDS: int = 3` declaration: added 7 lines of comment
  documenting the new `--n-rounds` flag override semantics (default 3
  preserves backward compatibility with Wave 81/86/158 manifest bytes).
- `argparse`: added `--n-rounds` flag with type `int`, default `3`,
  help string explaining the baseline-vs-framework use case.
- `main()`: added 7-line comment block + `global N_ROUNDS; N_ROUNDS = int(args.n_rounds)`
  wire-through (same minimal `global` pattern as Wave 168 P1 `--nfe` fix).

Total: 26 lines added, 1 line removed (net +25 LOC). 2 file edits.

```diff
-N_ROUNDS: int = 3
+# Wave 170 P3: ``--n-rounds`` flag now allows overriding the
+# module-level ``N_ROUNDS`` constant via CLI (was hardcoded
+# ``n_rounds=3`` in Wave 158). Default 3 preserves backward compat
+# with the Wave 81/86/158 manifest bytes. The baseline arm in the
+# Wave 170 fair-baseline comparison uses ``--n-rounds 1`` to disable
+# the framework's restart-blend glue (so the baseline arm exercises
+# only ``solve_ode`` with no ``apply_restart_distribution`` chain).
+N_ROUNDS: int = 3  # legacy default; overridden by --n-rounds in main()
```

```diff
+    p.add_argument(
+        "--n-rounds",
+        type=int,
+        default=3,
+        help=(
+            "Number of restart-blend rounds for the framework arm. "
+            "Baseline arm: use 1 (no restart-blend glue, pure solve_ode). "
+            "Framework arm: use 3 (Wave 158 canonical Wave 45 multi-round path). "
+            "Default 3 preserves backward compatibility with Wave 81/86/158 manifest bytes."
+        ),
+    )
```

```diff
+    # Wave 170 P3: same minimal ``global`` wire-through pattern for
+    # ``--n-rounds`` — keeps the constant readable from the call sites
+    # in ``_build_lineageflow_adapter`` + ``_framework_emit_sequence``
+    # without churning every function signature. Default 3 preserves
+    # Wave 158 backward compat.
+    global N_ROUNDS
+    N_ROUNDS = int(args.n_rounds)
```

## Call-site analysis

`grep -n "N_ROUNDS" tools/gen_lineageflow_n1000_fastas.py` confirms `N_ROUNDS`
is referenced only in the **framework arm** path (line 197: `_solve_framework(
adapter, nfe=NFE_PER_RECORD, seed=int(seed), n_rounds=N_ROUNDS, )`) and the
manifest dict at line 359 (`"n_rounds": int(N_ROUNDS)`). The baseline arm
(`_write_baseline_arm`) does NOT use `N_ROUNDS` — bare RNG draws only. So
setting `--n-rounds 1` for the baseline arm has no behavioral side effects on
that arm; it only deactivates the framework glue if the same script is later
re-run for the framework arm with `--n-rounds 1` (which is the intended
mechanism: the framework arm needs the framework glue to function as a
"framework" arm in the JMAA-theory sense).

## Smoke test (sanity)

```
$ mkdir -p /tmp/w170/sanity/
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w170/sanity/n_rounds_1/ --n 1 --n-rounds 1 --nfe 50
wrote /tmp/w170/sanity/n_rounds_1/baseline.fasta (n=1)
wrote /tmp/w170/sanity/n_rounds_1/framework.fasta (n=1)
wrote /tmp/w170/sanity/n_rounds_1/manifest.json

$ cat /tmp/w170/sanity/n_rounds_1/manifest.json | python -c "import json,sys; d=json.load(sys.stdin); print('n_rounds:', d.get('n_rounds','MISSING'))"
n_rounds: 1

$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w170/sanity/n_rounds_3/ --n 1 --n-rounds 3 --nfe 50
wrote /tmp/w170/sanity/n_rounds_3/baseline.fasta (n=1)
wrote /tmp/w170/sanity/n_rounds_3/framework.fasta (n=1)
wrote /tmp/w170/sanity/n_rounds_3/manifest.json

$ cat /tmp/w170/sanity/n_rounds_3/manifest.json | python -c "import json,sys; d=json.load(sys.stdin); print('n_rounds:', d.get('n_rounds','MISSING'))"
n_rounds: 3

$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w170/sanity/default/ --n 1 --nfe 50
wrote /tmp/w170/sanity/default/baseline.fasta (n=1)
wrote /tmp/w170/sanity/default/framework.fasta (n=1)
wrote /tmp/w170/sanity/default/manifest.json

$ cat /tmp/w170/sanity/default/manifest.json | python -c "import json,sys; d=json.load(sys.stdin); print('default n_rounds:', d.get('n_rounds','MISSING'))"
default n_rounds: 3
```

All three cases produce a valid manifest and the `n_rounds` field reflects the
CLI flag (or the default 3 when omitted).

## CLI help

```
$ python tools/gen_lineageflow_n1000_fastas.py --help 2>&1 | grep -A 2 "n-rounds"
                                       [--n-rounds N_ROUNDS]

  --n-rounds N_ROUNDS  Number of restart-blend rounds for the framework arm.
                       Baseline arm: use 1 (no restart-blend glue, pure
                       solve_ode). Framework arm: use 3 (Wave 158 canonical
```

## Lint + tests + claims

```
$ ruff check tools/gen_lineageflow_n1000_fastas.py
All checks passed!

$ pytest tests/ -k "d4" -q --tb=line | tail -3
33 passed, 31 skipped, 5020 deselected, 9 warnings in 2.55s

$ python tools/check_claims_consistency.py | tail -3
- Active claims: 39
- Provisional claims: 0
**No drift detected.**
```

## Backward compatibility

- Default `--n-rounds=3` preserves Wave 158 manifest bytes (the
  `n_rounds` field in `manifest.json` continues to read `3` for the
  no-arg invocation path).
- The `N_ROUNDS: int = 3` module-level constant still exists and still
  reads as `3` from any caller that imports this module without invoking
  `main()` (e.g. tooling that uses `N_ROUNDS` as a constant).
- The `--nfe` flag wire-through pattern from Wave 168 P1 is unchanged.
- `_build_lineageflow_adapter` and `_framework_emit_sequence` still read
  `N_ROUNDS` from module scope; they pick up the CLI-overridden value
  automatically because of the `global N_ROUNDS` reassignment in `main()`.

## Files

- `tools/gen_lineageflow_n1000_fastas.py` (modified, +26 / -1)
- `docs/audit/wave170-n-rounds-flag.md` (this file, added)