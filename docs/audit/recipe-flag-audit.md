# Recipe commands that name flags their driver does not accept

**Date:** 2026-10-30
**Scope:** `reproduce/*.sh`, `scripts/*.sh`
**Status:** 7 commands repaired; `tools/check_recipe_flags.py` added as gate 19

---

## 1. Why this surfaced

The `--help` guard round (`docs/audit/cli-help-guard.md`) established that a
driver must treat `--help` as a dry run. Checking the same property across all
of `tools/*.py` turned up a second class of dead text: commands in the
reproduction recipes that name flags the target driver has never accepted.

The recipes are the reviewer-facing surface — "copy this line to re-run cell
R1". Their command blocks are commented out by default (the live sweeps cost
GPU-hours), so nothing executes them and nothing notices a rename.

## 2. Observed facts

A scanner that parses `python tools/X.py ...` lines out of `reproduce/*.sh` and
`scripts/*.sh`, follows backslash continuations, and diffs the flags against
the `add_argument("--…")` set of `X.py` reported **7 problems**:

| Location | Driver | Problem |
|---|---|---|
| `reproduce/01_R1_LineageFlow.sh:73` | `run_lineageflow_n1000_foldability_omegafold.py` | `--n-samples`, `--seed` do not exist (real: `--baseline-fasta`, `--framework-fasta`, `--output-dir`, …) — and the driver does not compute `hmmscan_total_hits` at all |
| `reproduce/01_R1_LineageFlow.sh:89` | `gen_lineageflow_n1000_fastas.py` | `--output-dir` → the flag is `--outdir` |
| `reproduce/06_R5b_CIFAR_n_rounds1.sh:129` | `run_sota_cifar_experiment.py` | `--n-seeds` does not exist; that driver threads its seed through `WAVE247_SEED` |
| `scripts/reproduce_r1_to_r6.sh:171` | `run_real_ckpt_eval.py` | 9 of 10 flags do not exist (real CLI: `--model`, `--seeds`, `--nfe-budgets`, `--n-rounds`, `--output`, `--metric-mode`, …) |
| `scripts/reproduce_r1_to_r6.sh:294` | `run_sota_2d_experiment.py` | **false positive** — `--output-dir` is registered by `add_sota_common_args` |
| `scripts/reproduce_r1_to_r6.sh:326` | `run_sota_2d_experiment.py` | **false positive** — same |
| `scripts/reproduce_r1_to_r6.sh:362` | `generate_mnist_samples.py` | `--ckpt`, `--seed`, `--arm`, `--output-dir` do not exist (real: `--weights`, `--n-samples`, `--out`) |

Two of the seven were artefacts of the scanner, not the recipe: the
`tools/run_sota_*.py` family registers `--output-dir` and `--seed` through
`tools/_sota_common.add_sota_common_args`, so a scan of literal
`add_argument` calls cannot see them. The committed checker resolves that call.

Beyond the flag names, two blocks were structurally wrong:

- **R1** named a driver that computes OmegaFold foldability, not
  `hmmscan_total_hits`. The headline metric comes from
  `gen_lineageflow_n1000_fastas.py` → external `hmmscan` →
  `tools/r1_d004_analysis.py`.
- **R6** named `generate_mnist_samples.py --arm baseline`, but that driver has
  no arm concept (it generates one single-pass arm) and writes `.npz`, while
  `tools/run_image_eval.py` consumes a directory of images. The two do not
  compose.

## 3. Repairs

- `reproduce/01_R1_LineageFlow.sh` — Step 5 is now the real three-step
  pipeline (5a generate both FASTA arms with `--nfe 150 --restart-min-nfe 5`,
  which is what opens the Wave 186 gate; 5b `hmmscan --tblout` both arms; 5c
  `tools/r1_d004_analysis.py`). The GAP-55 note is kept and now points at the
  same pair of flags instead of repeating a second, stale command.
- `reproduce/06_R5b_CIFAR_n_rounds1.sh` — the 3-seed sweep is a shell loop
  over `WAVE247_SEED`, which is the only seed control that driver has.
- `scripts/reproduce_r1_to_r6.sh` R1 — points at
  `reproduce/01_R1_LineageFlow.sh` instead of duplicating the pipeline; one
  copy of a command is one copy that can drift.
- `scripts/reproduce_r1_to_r6.sh` R6 — states the real composition
  (`generate_mnist_samples.py --weights … --out …`, then
  `run_image_eval.py --samples-dir …`) and records plainly that no committed
  end-to-end two-arm R6 driver exists; `SOURCE.md`'s reproducibility pointer is
  the Wave 28 canonical-extractor run of `run_image_eval.py`. This is not a new
  caveat — `docs/headline-evidence/r6_mnist_fm_fid_m15p01pct/SOURCE.md` already
  records it.

The expected headline numbers in every block are unchanged.

## 4. The gate

`tools/check_recipe_flags.py` scans `reproduce/*.sh` and `scripts/*.sh`, parses
each `python tools/X.py` invocation including backslash continuations and the
leading `#` of a commented block, resolves `X.py`'s flags from its AST (plus
`add_sota_common_args`), and exits 1 on an unknown flag or a missing driver.
Current output: `recipe-flag check: 0 problem(s)`.

`tests/test_tools/test_recipe_flags.py` pins: the repository is clean; an
unknown flag is reported; a known flag inside a commented recipe is accepted; a
missing driver is reported; `add_sota_common_args` flags are recognised; a
continuation line belongs to the same command; `-h`/`--help` exit 0.

Added to `todo.json["gate_chain"]` (18 → 19), `AGENTS.md` §4.1 (twelve →
thirteen checkers) and CI Gate 7.

## 5. Unresolved

- The scanner reads only `python … tools/*.py` lines. `hmmscan`, `bash`
  one-liners and inline `python -c` blocks are not checked.
- `tools/run_real_ckpt_eval.py` still has no `--ckpt`; the checkpoint is
  resolved by the model's config. The R1 block no longer calls it, so the
  question is moot for the recipes, but a reader looking for "evaluate a
  checkpoint" will land on `--model`.
