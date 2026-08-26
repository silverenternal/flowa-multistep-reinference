# Mutation testing on Windows — known limitation

`mutmut` does **not** run natively on Microsoft Windows. Attempting to
launch it from a Windows shell produces the following banner from the
upstream library:

```
To run mutmut on Windows, please use the WSL. Native windows support
is tracked in issue https://github.com/boxed/mutmut/issues/397
```

This is an upstream issue (boxed/mutmut#397), not a defect of the
`flowa-multistep-reinference` harness. The repo's
`.github/workflows/mutation-nightly.yml` job runs on
`ubuntu-latest` for exactly this reason: **Linux is the source of
truth for mutation score**, and the gate enforced in that workflow
operates on the artifact (`mutmut_results.json`,
`mutmut_results.txt`) that mutmut writes when invoked on Linux.

## What this means locally on Windows

Running the harness on Windows will fail at the first invocation:

```bash
$ .venv/Scripts/python.exe -m mutmut run --help
To run mutmut on Windows, please use the WSL. Native windows support
is tracked in issue https://github.com/boxed/mutmut/issues/397
```

The `tools/mutate/run_mutmut.sh` (and the Linux-targeted
`tools/mutate/mutmut_run.sh` wrapper that delegates to it) script
exits cleanly at the same banner with no mutation results produced,
so no `mutmut_results.json` is written. This is expected.

## What to do instead

The mutation-nightly GitHub Actions workflow
(`.github/workflows/mutation-nightly.yml`) exercises the harness on
`ubuntu-latest`, parses the produced `mutmut_results.json`, enforces
the S-tier thresholds (`project >= 0.50`, `contracts/universal >=
0.75`), and uploads `mutmut_report.html` as a build artifact. To
inspect mutation results on a Windows machine:

1. Open the latest successful run of `mutation-nightly` in GitHub
   Actions.
2. Download the `mutmut-report` artifact — it contains
   `mutmut_results.json`, `mutmut_results.txt`, and
   `mutmut_report.html`.

Locally on Windows you can also reproduce the parsing logic without
running mutmut itself:

```bash
.venv/Scripts/python.exe -c "import json; print(json.dumps(
    json.load(open('mutmut_results.json')), indent=2))"
```

## Future remediation

Native Windows support is tracked upstream at
[boxed/mutmut#397](https://github.com/boxed/mutmut/issues/397). When
that issue is closed and `mutmut` ships a Windows entry-point, this
document will be deleted and the harness will be runnable on both
platforms. Until then, treat any "mutation score" reported on Windows
as **invalid**; the Linux workflow is the authoritative measurement.

## Files in this directory

* `mutmut.toml` — mutmut configuration (paths under test, runner
  command). Platform-agnostic; consumed by mutmut on Linux.
* `run_mutmut.sh` — canonical mutation-testing runner (Bash). Used by
  the `mutation-nightly.yml` workflow.
* `mutmut_run.sh` — Linux-targeted alias that delegates to
  `run_mutmut.sh`. Kept so a fresh `git clone` on Linux still has a
  runner with the conventional name.
* `mutation_baseline.json` — captured mutation score baseline (Linux).
  Updated by the workflow and committed back when the score changes
  by more than the S-tier delta.
* `justified_survivors.json` — manually-justified mutants that the
  gate allows to survive. Maintained by humans, never mutated
  automatically.
* `WINDOWS_LIMITATION.md` — this document.
