# `--help` was not a dry run

**Date:** 2026-10-30
**Scope:** every `tools/*.py` with a `__main__` block; 39 drivers.
**Status:** closed. Each driver now prints its docstring and exits before doing
any work. No metric, claim, status label, or verdict moved. No GPU was used.

---

## 1. What happened

While smoke-testing the checkers, every `tools/*.py` was run with `--help` to
confirm it did not crash. Sixteen files under `verification_outputs/` and
`verification_outputs/MANIFEST.md` came back modified: several drivers
(`wave195_p2_r_level_power`, `wave196_*`, `wave208_p1_*`, `wave230_p2_*`,
`build_verification_manifest`) execute their analysis from the `__main__`
block and read no arguments at all, so `--help` was treated as "no arguments"
and the analysis ran.

Everything was restored with `git checkout --` and `check_data_integrity`
re-verified 15 directories / 703 files / 0 mismatches. The hazard was written
into `doc-anchor-audit.md` section 6 and left unfixed, because adding an
argument parser to each driver looked like a separate change. It is not: a
three-line guard is enough, and the risk is a silent evidence rewrite.

## 2. The size of the class

| | count |
|---|---:|
| `tools/*.py` | 212 |
| with a module-level `__main__` block | — |
| ... that read `sys.argv` or call `parse_args` | the rest |
| ... that read no arguments at all | **39** |
| of those, that write files | 30 |
| of those, read-only analysis that still runs | 9 |

`tools/flowmol3_xtb_bridge.py` is deliberately not in the set. Its docstring
says *"The module is import-only; there is no `__main__`"*, and a grep for
`__main__` finds that sentence. A first draft of the fix inserted `import sys`
into it — inside the docstring, where `ast.parse` does not complain. The
static test now matches the AST node, not the string.

## 3. The guard

```python
if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    ...
```

39 drivers, 135 added lines: one guard each, plus `import sys` in the 18 that
did not already import it. `ruff check tools/` is clean; `compile()` — not
`ast.parse()`, which tolerates a misplaced `from __future__` — is what the
insertion script verified per file, because the first draft put `import sys`
above `from __future__ import annotations`.

## 4. The test

`tests/test_tools/test_cli_help_guard.py` (6 cases):

* every `tools/*.py` with a `__main__` block either parses arguments or opens
  the block with the guard — the guard must be the block's **first** statement,
  so a guard placed after the work does not count;
* at least 30 drivers rely on the guard, so the invariant cannot pass by
  covering nothing;
* a synthetic driver that ignores argv is reported;
* a *copy* of `render_r5c_regime_curve.py` run inside `tmp_path` prints its
  docstring, exits 0, and creates no `docs/` directory — the dynamic half runs
  on a copy precisely so a regression fails the test instead of rewriting
  `docs/figures/fig5_r5c_regime_curve.png`;
* both `-h` and `--help` are honoured.

Suite: 5610 passed / 180 skipped / 0 failed in 546 s (was 5603; the 6 guard
tests plus the seventh reviewer-pointer case). `ruff check` clean, all 15
gate-chain entries green, `mkdocs build --strict` exit 0.

## 5. What this does not fix
The drivers still take no real arguments. `--help` is now honest; every other
flag is still ignored, so `python3 tools/wave195_p2_r_level_power.py --seed 7`
silently runs the default configuration. Making each driver configurable is a
different change, and the audit records that produced them already document
the parameters they ran with. The guard exists to stop the silent-write
failure mode, not to pretend the drivers have a CLI.
