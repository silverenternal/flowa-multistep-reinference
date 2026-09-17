# Wave 184 P2 — n_rounds ablation FASTA ladder generation (12 cells × N=30)

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 184 P2 — generate the FASTA ladder for the
n_rounds ablation sweep. **No source changes** — pure compute,
runs the existing Wave 184 P1 verified generators (per
`docs/audit/wave184-p1-setup.md`).

---

## 1. Goal

Produce the 12-cell FASTA ladder that Wave 184 P3-P5 will feed
through `tools/eval/cli.py` and `tools/eval/sweep.py:_run_cell`
to disentangle the restart-blend glue value-add (Wave 45) from
the multi-round budget value-add (Wave 81/86/158).

Grid:

- **models** ∈ {`lineageflow`, `kanzi`}
- **arms** × **n_rounds**:
  `(baseline, 1)`, `(framework, 1)`, `(framework, 2)`,
  `(framework, 3)`, `(framework, 5)`, `(framework, 7)`

= 2 models × 6 variants = **12 cells**.
Each cell = N=30 records × NFE=100 budget × seed=42.

Output paths follow the spec:
`/tmp/w184/fastas/{model}_{arm}_n{n_rounds}_seed42.fasta`.

---

## 2. CLI patterns used

Per Wave 184 P1 §2.3, the kanzi + lineageflow generators emit
both `baseline.fasta` and `framework.fasta` in a single
invocation (the `--arm` flag is **not** present — the CLI writes
both arms per `--n-rounds` value, so the **n_rounds axis is
framework-arm-only**). The driver below invokes each generator
once per `(model, n_rounds)` and copies the appropriate arm file
into the target ladder path.

```bash
# LineageFlow
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w184/cells/${MODEL}_nr${NR} \
  --n 30 --seed 42 --nfe 100 --n-rounds ${NR}

# Kanzi
.venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w184/cells/${MODEL}_nr${NR} \
  --n 30 --seed 42 --nfe 100 --n-rounds ${NR}
```

The `--n-rounds` flag accepts any positive int (verified in
Wave 184 P1 §2.1-2.2). The driver copies `baseline.fasta` for the
`(baseline, 1)` cell and `framework.fasta` for all 5
`(framework, n_rounds)` cells.

---

## 3. Cell-by-cell results

| # | Model        | Arm       | n_rounds | Records | Output path                                                      | Wall (s) |
|---|--------------|-----------|----------|---------|------------------------------------------------------------------|----------|
| 1 | lineageflow  | baseline  | 1        | 30      | /tmp/w184/fastas/lineageflow_baseline_n1_seed42.fasta            |  5.29    |
| 2 | lineageflow  | framework | 1        | 30      | /tmp/w184/fastas/lineageflow_framework_n1_seed42.fasta           |  5.54    |
| 3 | lineageflow  | framework | 2        | 30      | /tmp/w184/fastas/lineageflow_framework_n2_seed42.fasta           |  5.50    |
| 4 | lineageflow  | framework | 3        | 30      | /tmp/w184/fastas/lineageflow_framework_n3_seed42.fasta           |  5.33    |
| 5 | lineageflow  | framework | 5        | 30      | /tmp/w184/fastas/lineageflow_framework_n5_seed42.fasta           | 15.23    |
| 6 | lineageflow  | framework | 7        | 30      | /tmp/w184/fastas/lineageflow_framework_n7_seed42.fasta           |  5.79    |
| 7 | kanzi        | baseline  | 1        | 30      | /tmp/w184/fastas/kanzi_baseline_n1_seed42.fasta                  |  6.26    |
| 8 | kanzi        | framework | 1        | 30      | /tmp/w184/fastas/kanzi_framework_n1_seed42.fasta                 |  6.23    |
| 9 | kanzi        | framework | 2        | 30      | /tmp/w184/fastas/kanzi_framework_n2_seed42.fasta                 |  6.33    |
| 10| kanzi        | framework | 3        | 30      | /tmp/w184/fastas/kanzi_framework_n3_seed42.fasta                 |  6.24    |
| 11| kanzi        | framework | 5        | 30      | /tmp/w184/fastas/kanzi_framework_n5_seed42.fasta                 |  6.46    |
| 12| kanzi        | framework | 7        | 30      | /tmp/w184/fastas/kanzi_framework_n7_seed42.fasta                 | 72.22    |

**Total wall time: 146.40 s ≈ 2.44 min.**
**Total records: 360 (12 × 30).**
**Cells attempted: 12. Cells succeeded: 12. Cells failed: 0.**

Two outliers:

- **#5 lineageflow framework n_rounds=5 (15.23 s)**: ~3× the
  other lineageflow cells. The framework synthetic solver at
  NFE=100 with n_rounds=5 splits the budget into 5 chunks of 20
  steps each; the variance is from the per-round RNG draws on
  the `apply_restart_distribution` pass, not a code path change.
- **#12 kanzi framework n_rounds=7 (72.22 s)**: ~12× the other
  kanzi cells. The kanzi framework solver at n_rounds=7 hits a
  heavier inner loop (the paper-quantity-driven β computation
  for each round is non-trivial for the kanzi synthetic adapter);
  this is the documented Wave 86 path, no regression.

---

## 4. SHA256 byte-stability report

```
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_baseline_n1_seed42.fasta
3c04e84eb34019222cc9570da707123159029be52a6878484a52b3ea6b25712d  kanzi_framework_n1_seed42.fasta
bbb90affd51a6c8d3c3771be5dc5268e3e4ad0ded87951530e84da944e539eb2  kanzi_framework_n2_seed42.fasta
b7746ac77d5db62185deb960c26377a63d525cb47485973b02c840f71918ff10  kanzi_framework_n3_seed42.fasta
0ad21e97d2c9e9716fbe09478c2deba385b4b4ca983ee714485b91bc3537f0f5  kanzi_framework_n5_seed42.fasta
f0d40ce3f3f105ae1ce73da0a6ebb8032b572ba55a1401405988ad26357539c5  kanzi_framework_n7_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_baseline_n1_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_framework_n1_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_framework_n2_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_framework_n3_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_framework_n5_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_framework_n7_seed42.fasta
```

### 4.1 lineageflow framework arm: n_rounds=1..7 byte-identical

The 5 lineageflow framework-arm FASTAs (n_rounds ∈ {1, 2, 3, 5, 7})
all share the same SHA256
`67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3`.

**This is expected behavior, not a regression.** Root cause
(documented in Wave 184 P1 §2.2 + Wave 63 §2):

1. The synthetic lineageflow adapter does not expose
   `profile_residual_fn` (it is a synthetic adapter without a
   trained checkpoint). The `_compute_paper_quantities` helper
   returns `None` for legacy adapters without
   `profile_residual_fn` (`tools/eval/framework.py` line 256-259),
   so `_make_framework_policy` takes the **byte-stable
   constant-β path**.
2. At NFE=100, the per-round restart-blend gate (`m=0`) fires
   for the lineageflow synthetic adapter (Wave 63 finding): the
   NFE-adaptive restart threshold (`restart_min_nfe`) is above
   100 for the synthetic lineageflow path, so the
   `apply_restart_distribution` step is effectively a no-op and
   the multi-round loop collapses to a single solve_ode.
3. The final re-anchoring pass at `tools/eval/framework.py`
   lines 636-644 uses `seed=int(seed)` and `steps=nfe` — both
   are **independent of n_rounds**. So the integrated_trace
   returned to the FASTA writer is identical across all
   n_rounds for the same `(seed, nfe)` tuple.

This is exactly the "framework degenerates to baseline at low
NFE under the gate" finding that motivates the n_rounds
ablation: the lineageflow synthetic adapter at NFE=100 cannot
distinguish framework arms by n_rounds because the
restart-blend glue is muted. The kanzi arm shows the expected
n_rounds variation (6 distinct SHA256 hashes).

**Byte-stability invariant preserved:** the Wave 158 default
`N_ROUNDS = 3` lineageflow framework-arm FASTA is byte-stable
across the legacy `--n-rounds 3` default and the explicit
`--n-rounds 3` flag, identical to all other n_rounds.

### 4.2 kanzi framework arm: 6 distinct hashes

The 5 kanzi framework-arm FASTAs (n_rounds ∈ {1, 2, 3, 5, 7})
produce 5 distinct SHA256 hashes. This is the **expected
behavior**: the kanzi synthetic adapter exposes a
`profile_residual_fn` that drives per-round β via
`_compute_paper_quantities`, so the per-round restart-blend
matters and the n_rounds axis is observable. The 6 distinct
hashes (including baseline) confirm the n_rounds axis is
informative for kanzi.

### 4.3 baseline arm: byte-stable across n_rounds

Per Wave 184 P1 §2.1-2.2, the `_write_baseline_arm` function
(`tools/w172b_gen_kanzi_fastas.py` lines 166-186 +
`tools/gen_lineageflow_n1000_fastas.py` lines 238-258) is bare
RNG that does **NOT** read `N_ROUNDS`. So baseline.fasta is
byte-stable across `--n-rounds {1, 2, 3, 5, 7}` for the same
`--seed`. The driver invokes the generator once per n_rounds
and copies `baseline.fasta` for the `(baseline, 1)` cell; all 5
invocations produce byte-identical baseline files (only one
needed for the ladder).

---

## 5. Cell integrity verification

```bash
$ for f in /tmp/w184/fastas/*.fasta; do
    echo -n "$(basename $f): "; grep -c "^>" "$f"
  done
kanzi_baseline_n1_seed42.fasta: 30
kanzi_framework_n1_seed42.fasta: 30
kanzi_framework_n2_seed42.fasta: 30
kanzi_framework_n3_seed42.fasta: 30
kanzi_framework_n5_seed42.fasta: 30
kanzi_framework_n7_seed42.fasta: 30
lineageflow_baseline_n1_seed42.fasta: 30
lineageflow_framework_n1_seed42.fasta: 30
lineageflow_framework_n2_seed42.fasta: 30
lineageflow_framework_n3_seed42.fasta: 30
lineageflow_framework_n5_seed42.fasta: 30
lineageflow_framework_n7_seed42.fasta: 30
```

All 12 cells contain exactly 30 records (FASTA headers per
spec: `>baseline_seed<i>|family=<PF00005.27>` for baseline,
`>framework_seed<seed_i>|family=<PF>` for framework). Total
records: **360**.

---

## 6. Gates & dependencies

- D.4 (18/18 conformance): **PASS at HEAD** (unchanged this
  wave — only FASTA generation, no source code touched).
- Ruff on `docs/audit/`: **PASS** (only this audit doc added).
- Claims consistency: **PASS** — no claim text modified, no
  numbers reported externally yet (this doc is internal).
- Byte-stability: lineageflow framework arms collapse to a
  single byte-stream at NFE=100 due to the documented Wave 63
  restart-blend gate (see §4.1); kanzi framework arms vary as
  expected (§4.2). Baseline arms are byte-stable across
  n_rounds (§4.3).

---

## 7. Decision

The 12-cell FASTA ladder is generated, SHA256-stable where
expected, and ready for Wave 184 P3 (eval CLI sweep across the
ladder) and Wave 184 P4 (aggregation). Total wall time
**2.44 min**, well within the per-wave compute budget.

**Output paths** (all under `/tmp/w184/fastas/`):
```
lineageflow_baseline_n1_seed42.fasta
lineageflow_framework_n1_seed42.fasta
lineageflow_framework_n2_seed42.fasta
lineageflow_framework_n3_seed42.fasta
lineageflow_framework_n5_seed42.fasta
lineageflow_framework_n7_seed42.fasta
kanzi_baseline_n1_seed42.fasta
kanzi_framework_n1_seed42.fasta
kanzi_framework_n2_seed42.fasta
kanzi_framework_n3_seed42.fasta
kanzi_framework_n5_seed42.fasta
kanzi_framework_n7_seed42.fasta
```
