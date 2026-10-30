# The reproduction commands a reviewer would copy did not exist

**Date:** 2026-10-30
**Scope:** `docs/audit/reproducibility/p5-experiment-setup.md`,
`docs/audit/reproducibility/p8-experiment-setup.md`,
`tools/check_recipe_flags.py`
**Trigger:** verification of the 44-driver flag rejection committed in
`452cd760`. That change made a driver exit 2 on any argument instead of
ignoring it, so every documented invocation had to be re-read — and five of
the six did not survive the reading.

## 1. Observed

Both records carry the same section:

> ## 6. Reproducibility commands
> Reviewers can re-run the headline cells with the following commands:

| § | Command as written | What exists |
|---|---|---|
| 6.1 | `tools/run_lineageflow_n1000_foldability_omegafold.py --nfe-baseline 50 --nfe-framework 150 --n-rounds 3 --n-paired 1000 --seeds 42 …` | driver exists; **none of the five flags does** (`--output-dir`, `--fasta`/`--baseline-fasta`/`--framework-fasta`, `--gpus`, `--max-seqs`, `--skip-fold`/`--skip-sc`) |
| 6.2 | `tools/run_cifar10_rf.py --nfe 50 --n-rounds 4 --n-samples 1000 --chunk-size 100` | **no such file**; the driver is `tools/run_sota_cifar_experiment.py`, and it threads one seed per process through `WAVE247_SEED` |
| 6.3 | `tools/flowmol3_n1000_sweep.py --seed 42 --nfe 250 --n-samples 1000` | **no such file**; the driver is `tools/wave87_n1000_sweep.py`, whose sample flag is `--n-total` |
| 6.4 | `tools/run_sota_2d_experiment.py --target two_moons --n-seeds 7 --n-samples 1000 --n-rounds 5` | driver and all four flags exist — the one command that was real |
| 6.5 | `tools/run_kanzi_inv_proj.py --nfe 50 --n-rounds 3 --n-paired 1000 --seeds 42 43 44` | **no such file**; the two arms are `sweep_kanzi_n1000_framework_paper_metrics.py` and `sweep_kanzi_n1000_paper_metrics.py` |
| 6.6 | `tools/run_lineageflow_real_ckpt.py --nfe 50 --n-rounds 3 --n-paired 1000 --seeds 42 …` | driver exists, takes no arguments at all; it is a CPU smoke of the forward pass, not the HMMER sweep |

Five of six, in a section whose stated purpose is that a reviewer can re-run
the headline cells.

The same class then turned up one directory over, in the per-cell recipe that
ships with the paper data — `paper-data/R5b_cifar10_rf/REPRODUCIBILITY_RECIPE.md`,
"GPU path — regenerate the 12-cell evidence":

| Script | Flags as written | Flags it accepts |
|---|---|---|
| `scripts/wave235_p1_r5b_fix_sweep.py` | `--config rounds1 --n-records 200 --seed 42 --output-dir …` | `--device`, `--skip-runs` |
| `scripts/wave225_p7_r5b_reduced_rounds.py` | `--n-records 200 --seed 42 --output-dir …` | none — the script parses no arguments |
| `scripts/wave206_p6_cifar_rf_v4_honest_negative_curve.py` | `--full --nfe-list … --n-records-per-nfe 500 --output-dir …` | `--full`, `--pilot`, `--device`, `--n-records` |

Only `--full` was real. The other nine per-cell recipe files are clean.

## 2. Why it was invisible

Three separate reasons, and all three had to hold:

1. **Nothing executed the blocks.** They are prose in a record, not a script.
   `tools/check_recipe_flags.py` reads `reproduce/*.sh` and `scripts/*.sh`;
   its `_INVOCATION` regex would have matched `python tools/run_cifar10_rf.py`
   and reported "no such driver", but the file was never in its source set.
2. **The wrong commands still "worked".** Until 2026-10-30 a driver that
   ignored `sys.argv` ran its default configuration when handed flags. A
   reviewer who copied §6.6 got output, from a different configuration than
   the one the command asked for. The failure was silent in the direction
   that matters least visibly.
3. **The records were written from a template.** §6.2, §6.3, §6.5 and §6.6
   are §6.4's command with the script name and a few flags changed. The
   template was never validated against the drivers, and §6.4 is the one that
   happens to be correct.

## 3. What changed

**The records.** §6 is now a table of the six one-click recipes
(`reproduce/01_R1_LineageFlow.sh` … `07_R6_MNIST_TierAware.sh`) plus
`09_verify_all_cell_recipes.sh` for the whole set. Each subsection gives the
recipe and then the live re-run, taken verbatim from that recipe's Step 5 —
the block that `check_recipe_flags.py` already validates. §6.6 additionally
spells out the three-step R1 pipeline (generate FASTA → `hmmscan` against
`Pfam-A.hmm` → `r1_d004_analysis.py`) because the headline metric is a HMMER
hit count, not a sampler statistic.

Every driver and flag named in the new §6 was checked to exist before the
commit: `run_lineageflow_n1000_foldability_omegafold.py`,
`run_sota_cifar_experiment.py`, `wave87_n1000_sweep.py`,
`run_sota_2d_experiment.py`, `materialize_twodim_fm.py`,
`sweep_kanzi_n1000_{framework_,}paper_metrics.py`,
`gen_lineageflow_n1000_fastas.py`, `r1_d004_analysis.py`,
`scripts/wave216_p1_r3_per_record.py`, `scripts/wave218_p3_paired_ttest.py`.

Each record keeps a `> Corrected 2026-10-30` note naming what the block used
to say, so the historical text is not erased — the record still shows what
was claimed, and now also shows that it was wrong.

**The checker.** `check_recipe_flags.py` gained `DOC_GLOBS` —
`docs/audit/reproducibility/*.md` and `paper-data/*/*REPRODUCIBILITY_RECIPE.md`
— plus a second pass over `bash reproduce/x.sh` citations, so a renamed
recipe is caught the same way as a renamed flag. The source set is now 34
shell recipes plus 14 markdown files, 48 in total; `--verbose` lists all of
them. This is the change that would have caught the defect on the day it was
introduced.

**Tests.** `tests/test_tools/test_recipe_flags.py` grew from 8 to 12 cases:
a record naming a missing driver, a record naming a flag the driver lacks, a
record naming a missing recipe, and a record naming a real command that must
stay quiet.

**The per-cell recipe.** The three R5b commands were rewritten to the flags
those scripts actually take, with a `> Corrected 2026-10-30` note naming the
old text. The wall-clock figures and output filenames were left alone — they
were never wrong.

## 4. Interpretation

The commands were wrong in a way that resembles the defect this repository
has fixed repeatedly — a surface that claims a verification it never
performed. The pattern is consistent enough to name: **a claim whose
verification command is itself unverified**. The gate chain covers
`reproduce/*.sh` against the drivers, `docs/` against the code, and the
submission package against its hashes; it did not cover the prose that tells
a reader how to reproduce a number. It does now, for the two files where
that prose is reviewer-facing.

## 5. Unresolved

- The same class may exist in older records that cite commands —
  `docs/audit/wave*/`, the `docs/ARCHIVE/` tree, and the remaining
  `docs/audit/reproducibility/` siblings (`item4-tex-rewrite.md`,
  `p3-comparison.md`, which are scanned and clean, but are not the whole
  audit tree). Those are not in the checker's source set: a scan that
  reports 200 problems across historical records teaches nothing, and the
  records are supposed to describe what was run at the time. The two
  surfaces that a reviewer is told to follow are covered; the rest is
  history.
- §6.1's live re-run is described but not exercised: the OmegaFold foldability
  sweep needs GPU and a fold server. The recipe verifies the stored records
  by SHA-256, which is the part that runs on CPU.
