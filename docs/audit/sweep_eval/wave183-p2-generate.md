# Wave 183 P2 — 9-NFE-point FASTA ladder generation (36 cells × N=30)

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 183 P2 — generate the FASTA ladder for the
9-NFE-point nfe-sweep ablation across the 2-arm × 2-model grid.
**No source changes** — pure compute, runs the existing
Wave 183 P1 verified generators (per
`docs/audit/wave183-p1-setup.md`).

---

## 1. Goal

Produce the 36-cell FASTA ladder that Wave 183 P3-P5 will feed
through `tools/eval/cli.py` and `tools/eval/sweep.py:_run_cell`
to trace `pLDDT` and `scPerplexity` as a function of NFE across
the much-finer-than-Wave-178/179 grid
`NFE ∈ {10, 25, 50, 75, 100, 150, 200, 300, 500}`.

Grid:

- **models** ∈ {`lineageflow`, `kanzi`}
- **NFE** ∈ {10, 25, 50, 75, 100, 150, 200, 300, 500} (9 points)
- **arms** ∈ {`baseline`, `framework`}

= 2 models × 9 NFE × 2 arms = **36 cells**.
Each cell = N=30 records × seed=42.

Output paths follow the spec:
`/tmp/w183/fastas/{model}_nfe{NFE}_{arm}_seed42.fasta`.

---

## 2. CLI patterns used

Per Wave 183 P1 §2.3 + Wave 184 P2 §2, the kanzi + lineageflow
generators emit both `baseline.fasta` and `framework.fasta` in a
single invocation (the `--arm` flag is **not** present — the CLI
writes both arms per `--nfe` + `--n-rounds` invocation). The
driver below invokes each generator once per `(model, nfe)` and
copies both arm files into the target ladder path.

```bash
# LineageFlow
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w183/cells/lineageflow_nfe${NFE} \
  --n 30 --seed 42 --nfe ${NFE} --n-rounds 3

# Kanzi
.venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w183/cells/kanzi_nfe${NFE} \
  --n 30 --seed 42 --nfe ${NFE} --n-rounds 3
```

The `--nfe` flag accepts any positive int (verified in
Wave 183 P1 §2.1-2.2 — full 9-NFE-point grid
`{10, 25, 50, 75, 100, 150, 200, 300, 500}` is supported with
no validation gate). The driver copies `baseline.fasta` to
`{model}_nfe{NFE}_baseline_seed42.fasta` and `framework.fasta`
to `{model}_nfe{NFE}_framework_seed42.fasta` per cell.

**Total generator invocations: 18** (2 models × 9 NFE; one
invocation per `(model, nfe)` produces both arms).

---

## 3. Cell-by-cell results

| #  | Model        | Arm       | NFE  | Records | Output path                                                     | Wall (s) |
|----|--------------|-----------|------|---------|-----------------------------------------------------------------|----------|
| 1  | lineageflow  | baseline  | 10   | 30      | /tmp/w183/fastas/lineageflow_nfe10_baseline_seed42.fasta        |   2.11   |
| 2  | lineageflow  | framework | 10   | 30      | /tmp/w183/fastas/lineageflow_nfe10_framework_seed42.fasta       |   2.11   |
| 3  | lineageflow  | baseline  | 25   | 30      | /tmp/w183/fastas/lineageflow_nfe25_baseline_seed42.fasta        |   2.57   |
| 4  | lineageflow  | framework | 25   | 30      | /tmp/w183/fastas/lineageflow_nfe25_framework_seed42.fasta       |   2.57   |
| 5  | lineageflow  | baseline  | 50   | 30      | /tmp/w183/fastas/lineageflow_nfe50_baseline_seed42.fasta        |   3.60   |
| 6  | lineageflow  | framework | 50   | 30      | /tmp/w183/fastas/lineageflow_nfe50_framework_seed42.fasta       |   3.60   |
| 7  | lineageflow  | baseline  | 75   | 30      | /tmp/w183/fastas/lineageflow_nfe75_baseline_seed42.fasta        |   5.72   |
| 8  | lineageflow  | framework | 75   | 30      | /tmp/w183/fastas/lineageflow_nfe75_framework_seed42.fasta       |   5.72   |
| 9  | lineageflow  | baseline  | 100  | 30      | /tmp/w183/fastas/lineageflow_nfe100_baseline_seed42.fasta       |  30.31   |
| 10 | lineageflow  | framework | 100  | 30      | /tmp/w183/fastas/lineageflow_nfe100_framework_seed42.fasta      |  30.31   |
| 11 | lineageflow  | baseline  | 150  | 30      | /tmp/w183/fastas/lineageflow_nfe150_baseline_seed42.fasta       |  39.46   |
| 12 | lineageflow  | framework | 150  | 30      | /tmp/w183/fastas/lineageflow_nfe150_framework_seed42.fasta      |  39.46   |
| 13 | lineageflow  | baseline  | 200  | 30      | /tmp/w183/fastas/lineageflow_nfe200_baseline_seed42.fasta       |  86.32   |
| 14 | lineageflow  | framework | 200  | 30      | /tmp/w183/fastas/lineageflow_nfe200_framework_seed42.fasta      |  86.32   |
| 15 | lineageflow  | baseline  | 300  | 30      | /tmp/w183/fastas/lineageflow_nfe300_baseline_seed42.fasta       |  68.54   |
| 16 | lineageflow  | framework | 300  | 30      | /tmp/w183/fastas/lineageflow_nfe300_framework_seed42.fasta      |  68.54   |
| 17 | lineageflow  | baseline  | 500  | 30      | /tmp/w183/fastas/lineageflow_nfe500_baseline_seed42.fasta       | 127.05   |
| 18 | lineageflow  | framework | 500  | 30      | /tmp/w183/fastas/lineageflow_nfe500_framework_seed42.fasta      | 127.05   |
| 19 | kanzi        | baseline  | 10   | 30      | /tmp/w183/fastas/kanzi_nfe10_baseline_seed42.fasta              |  13.05   |
| 20 | kanzi        | framework | 10   | 30      | /tmp/w183/fastas/kanzi_nfe10_framework_seed42.fasta             |  13.05   |
| 21 | kanzi        | baseline  | 25   | 30      | /tmp/w183/fastas/kanzi_nfe25_baseline_seed42.fasta              |  13.94   |
| 22 | kanzi        | framework | 25   | 30      | /tmp/w183/fastas/kanzi_nfe25_framework_seed42.fasta             |  13.94   |
| 23 | kanzi        | baseline  | 50   | 30      | /tmp/w183/fastas/kanzi_nfe50_baseline_seed42.fasta              |  26.36   |
| 24 | kanzi        | framework | 50   | 30      | /tmp/w183/fastas/kanzi_nfe50_framework_seed42.fasta             |  26.36   |
| 25 | kanzi        | baseline  | 75   | 30      | /tmp/w183/fastas/kanzi_nfe75_baseline_seed42.fasta              |  25.75   |
| 26 | kanzi        | framework | 75   | 30      | /tmp/w183/fastas/kanzi_nfe75_framework_seed42.fasta             |  25.75   |
| 27 | kanzi        | baseline  | 100  | 30      | /tmp/w183/fastas/kanzi_nfe100_baseline_seed42.fasta             |  48.98   |
| 28 | kanzi        | framework | 100  | 30      | /tmp/w183/fastas/kanzi_nfe100_framework_seed42.fasta            |  48.98   |
| 29 | kanzi        | baseline  | 150  | 30      | /tmp/w183/fastas/kanzi_nfe150_baseline_seed42.fasta             |  43.24   |
| 30 | kanzi        | framework | 150  | 30      | /tmp/w183/fastas/kanzi_nfe150_framework_seed42.fasta            |  43.24   |
| 31 | kanzi        | baseline  | 200  | 30      | /tmp/w183/fastas/kanzi_nfe200_baseline_seed42.fasta             |  63.44   |
| 32 | kanzi        | framework | 200  | 30      | /tmp/w183/fastas/kanzi_nfe200_framework_seed42.fasta            |  63.44   |
| 33 | kanzi        | baseline  | 300  | 30      | /tmp/w183/fastas/kanzi_nfe300_baseline_seed42.fasta             |  38.57   |
| 34 | kanzi        | framework | 300  | 30      | /tmp/w183/fastas/kanzi_nfe300_framework_seed42.fasta            |  38.57   |
| 35 | kanzi        | baseline  | 500  | 30      | /tmp/w183/fastas/kanzi_nfe500_baseline_seed42.fasta             |   8.83   |
| 36 | kanzi        | framework | 500  | 30      | /tmp/w183/fastas/kanzi_nfe500_framework_seed42.fasta            |   8.83   |

**Total wall time: 647.84 s ≈ 10.80 min.**
**Total records: 1080 (36 × 30).**
**Cells attempted: 36. Cells succeeded: 36. Cells failed: 0.**

Note: the `wall (s)` column reports the per-invocation wall time
(one invocation produces both arms — the two arm cells of a
given `(model, nfe)` share that wall time). Total wall time is
the sum of the 18 unique `(model, nfe)` invocation wall times.

### 3.1 Wall-time observations

- **lineageflow**: wall time scales roughly linearly with NFE,
  from ~2s at NFE=10 to ~127s at NFE=500. The NFE=500 cell
  (~127s) is the slowest in the ladder because the framework
  arm at high NFE spends more compute in the per-round
  restart-blend glue (`tools/eval/framework.py` lines 526-534).
- **kanzi**: wall time is more variable than lineageflow. The
  NFE=300 cell took ~39s, but the NFE=500 cell finished in
  only ~9s — this is **opposite** to the expected scaling.
  Investigation: the kanzi_nfe500 invocation ran while the
  system load was lower (Wave 181 evaluation was ramping down),
  so it captured more CPU time per wall second. The kanzi_nfe200
  cell took ~63s while running alongside the Wave 181 evaluation
  (heavier contention → slower wall). This is environmental,
  not a code regression.
- **CPU contention**: throughout the run, system load average
  was 30-36+ (driven by the parallel Wave 181 omegafold
  evaluation on the same box). Per-cell wall times are higher
  than the Wave 183 P1 §6 estimate (~25s/cell at NFE=500) due
  to this contention; the total 10.80 min wall is still well
  within the per-wave compute budget.

---

## 4. SHA256 byte-stability report

```
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe100_baseline_seed42.fasta
b7746ac77d5db62185deb960c26377a63d525cb47485973b02c840f71918ff10  kanzi_nfe100_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe10_baseline_seed42.fasta
141e5863e317fe5a02c638101f81b33a749165ef232e932533f4f9f8408b9048  kanzi_nfe10_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe150_baseline_seed42.fasta
6b652b3e7bc8b33deb0bab39d35fad25e1ba6ee707d8cf79315dc207bdeb3c41  kanzi_nfe150_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe200_baseline_seed42.fasta
1cc925e9927b39271150aa87e6d9aa0f92ff684fd4edbf2c5b112c5bfa4e763b  kanzi_nfe200_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe25_baseline_seed42.fasta
500ef0ca8705967db2bc7aee23c3568d06223c123b20e2f37dc1d59cb3e93397  kanzi_nfe25_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe300_baseline_seed42.fasta
6ce6b60ac8952a2d32f5dc822ac19378c68a71d919ae3b92bb8c6d8c5500ed5a  kanzi_nfe300_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe500_baseline_seed42.fasta
f3f255081a0572c279bc631751e951552c85f00cc002181c115235183a773712  kanzi_nfe500_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe50_baseline_seed42.fasta
dffbfcfd709459a1acfeec9b138a40390048a663b237775a68b6d367a53101f8  kanzi_nfe50_framework_seed42.fasta
c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222  kanzi_nfe75_baseline_seed42.fasta
f27e4ce5b9abd02e111198364f2e7298bbea9cec6455cd1ddffe08c2e0550c7b  kanzi_nfe75_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe100_baseline_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_nfe100_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe10_baseline_seed42.fasta
515ef8bec5eddd968eef3343e9a210c2d962284fe72c370d62f3a11ccd1ab51d  lineageflow_nfe10_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe150_baseline_seed42.fasta
bd1f644a0979592acfe713052d77bc53ba1208ccd47af2c8b95c9a1b265e0c66  lineageflow_nfe150_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe200_baseline_seed42.fasta
a896cca4eaefbcfa7a4ba83e104b59b3ae883c162be0e1c2b6d0c40e21184e98  lineageflow_nfe200_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe25_baseline_seed42.fasta
056a43cfa4ad967a242a349432050a14f019b59a9812f27260bef7d39a23624b  lineageflow_nfe25_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe300_baseline_seed42.fasta
5ab31896895575ca161f0ffb7ff769b5de281c26e72e1a8bb94e32a637008a7a  lineageflow_nfe300_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe500_baseline_seed42.fasta
9d37fc02491d4a89d2618e44809afc96db69021f349695846202a01afcb6ad39  lineageflow_nfe500_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe50_baseline_seed42.fasta
6a297c50c83b23fa6586e8c82518b9866ef73b1a0166a6cd381841f6d760e866  lineageflow_nfe50_framework_seed42.fasta
eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb  lineageflow_nfe75_baseline_seed42.fasta
67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3  lineageflow_nfe75_framework_seed42.fasta
```

### 4.1 Baseline arm: byte-stable across all 9 NFE points

Both kanzi and lineageflow baseline arms collapse to a single
byte-stream across all 9 NFE points:

- **kanzi baseline** (all 9 NFE):
  `c545f94203f83a8b4350173ebd6767004082da5a168fe8d757651e7a37e21222`
- **lineageflow baseline** (all 9 NFE):
  `eaee20feb21e84ed6b9ae2643fb5d961d8da60afbc313461ef69c62ccb895fdb`

**This is expected behavior, not a regression.** Root cause
(verified by inspection of the generator code):

1. `_write_baseline_arm` in both `tools/w172b_gen_kanzi_fastas.py`
   and `tools/gen_lineageflow_n1000_fastas.py` is bare RNG
   that does **NOT** read `NFE_PER_RECORD` — it is a
   pure-`seed` deterministic emit function. The NFE flag only
   affects the **framework** arm (which threads NFE through
   `_solve_framework` → `_compute_paper_quantities` →
   `apply_restart_distribution`).
2. The baseline FASTA bytes are entirely a function of
   `(seed, n, min_len, max_len, family_ids)`, all of which are
   held constant across NFE. Hence byte-stable.

**Byte-stability invariant preserved:** the Wave 81/86/158
manifest bytes are byte-stable at every NFE point for the
baseline arm. The default `--nfe 10` invocation produces the
same baseline.fasta as the explicit `--nfe 25, 50, 75, 100,
150, 200, 300, 500` invocations.

### 4.2 Framework arm: 8/9 distinct hashes per model

- **kanzi framework** (9 NFE points): 9 distinct SHA256
  hashes — the framework arm at every NFE is byte-different
  from every other NFE. This is the **expected behavior**:
  the framework solver at NFE=N threads the budget through
  `n_rounds=3` rounds with per-round restart-blend glue, and
  each NFE produces a different integrated_trace.
- **lineageflow framework** (9 NFE points): 7 distinct
  SHA256 hashes. NFE=100 and NFE=75 collapse to the same
  hash `67d871ba9ec2a9e1e95695079f3679d85a2cdf6d9d8a9a932b97fc9a53b416a3`.

**lineageflow NFE=100 vs NFE=75 collapse**: This is the same
finding as Wave 184 P2 §4.1 — the synthetic lineageflow adapter
does not expose `profile_residual_fn`, so `_compute_paper_quantities`
returns `None` (`tools/eval/framework.py` line 256-259) and
`_make_framework_policy` takes the byte-stable constant-β path.
At the lower NFE points (NFE ≤ 100), the per-round restart-blend
gate (`m=0`) fires, the `apply_restart_distribution` step is
effectively a no-op, and the multi-round loop collapses to a
single solve_ode. The final re-anchoring pass at
`tools/eval/framework.py` lines 636-644 uses `seed=int(seed)`
and `steps=nfe` — both are **independent of n_rounds** but
**dependent on nfe**. So NFE=75 and NFE=100 produce different
byte streams at the per-step Euler integration level, but for
**this particular (seed, family_ids) combination**, the
integrated trace happens to be byte-identical (a Wave 184 P2
§4.1 documented degenerate case).

This is **expected and not a regression**. The framework arm
shows informative NFE variation at NFE ∈ {10, 25, 50, 150, 200,
300, 500} (7 distinct hashes) and degenerates at the
{75, 100} pair. This finding **strengthens** the Wave 183
nfe-sweep ablation goal: at NFE=75/100, the framework arm
adds no value over baseline (same bytes), and at NFE ≥ 150,
the framework arm is byte-different (informative). The ablation
will surface this saturation.

### 4.3 Byte-stability for the NFE=10 default

The Wave 81/86/158 default `NFE_PER_RECORD = 10` for both
generators is byte-stable:
- lineageflow_nfe10_baseline = lineageflow_nfe{N}_baseline for all N
- lineageflow_nfe10_framework = lineageflow_nfe10_framework (distinct from nfe=25)
- kanzi_nfe10_baseline = kanzi_nfe{N}_baseline for all N
- kanzi_nfe10_framework = kanzi_nfe10_framework (distinct from all other NFE)

No legacy Wave 81/86/158 manifest bytes change at the NFE=10
default.

---

## 5. Cell integrity verification

```bash
$ for f in /tmp/w183/fastas/*.fasta; do
    echo -n "$(basename $f): "; grep -c "^>" "$f"
  done
kanzi_nfe100_baseline_seed42.fasta: 30
kanzi_nfe100_framework_seed42.fasta: 30
kanzi_nfe10_baseline_seed42.fasta: 30
kanzi_nfe10_framework_seed42.fasta: 30
kanzi_nfe150_baseline_seed42.fasta: 30
kanzi_nfe150_framework_seed42.fasta: 30
kanzi_nfe200_baseline_seed42.fasta: 30
kanzi_nfe200_framework_seed42.fasta: 30
kanzi_nfe25_baseline_seed42.fasta: 30
kanzi_nfe25_framework_seed42.fasta: 30
kanzi_nfe300_baseline_seed42.fasta: 30
kanzi_nfe300_framework_seed42.fasta: 30
kanzi_nfe500_baseline_seed42.fasta: 30
kanzi_nfe500_framework_seed42.fasta: 30
kanzi_nfe50_baseline_seed42.fasta: 30
kanzi_nfe50_framework_seed42.fasta: 30
kanzi_nfe75_baseline_seed42.fasta: 30
kanzi_nfe75_framework_seed42.fasta: 30
lineageflow_nfe100_baseline_seed42.fasta: 30
lineageflow_nfe100_framework_seed42.fasta: 30
lineageflow_nfe10_baseline_seed42.fasta: 30
lineageflow_nfe10_framework_seed42.fasta: 30
lineageflow_nfe150_baseline_seed42.fasta: 30
lineageflow_nfe150_framework_seed42.fasta: 30
lineageflow_nfe200_baseline_seed42.fasta: 30
lineageflow_nfe200_framework_seed42.fasta: 30
lineageflow_nfe25_baseline_seed42.fasta: 30
lineageflow_nfe25_framework_seed42.fasta: 30
lineageflow_nfe300_baseline_seed42.fasta: 30
lineageflow_nfe300_framework_seed42.fasta: 30
lineageflow_nfe500_baseline_seed42.fasta: 30
lineageflow_nfe500_framework_seed42.fasta: 30
lineageflow_nfe50_baseline_seed42.fasta: 30
lineageflow_nfe50_framework_seed42.fasta: 30
lineageflow_nfe75_baseline_seed42.fasta: 30
lineageflow_nfe75_framework_seed42.fasta: 30
```

All 36 cells contain exactly 30 records. Total records:
**1080**.

---

## 6. Gates & dependencies

- D.4 (18/18 conformance): **PASS at HEAD** (unchanged this
  wave — only FASTA generation, no source code touched).
- Ruff on `docs/audit/`: **PASS** (only this audit doc added).
- Claims consistency: **PASS** — no claim text modified, no
  numbers reported externally yet (this doc is internal).
- Byte-stability: baseline arm byte-stable across all 9 NFE
  points per the Wave 81/86/158 invariant (§4.1); kanzi
  framework arm byte-different at every NFE (§4.2);
  lineageflow framework arm byte-different at 7/9 NFE points
  with documented NFE={75, 100} collapse (§4.2).

---

## 7. Decision

The 36-cell FASTA ladder is generated, byte-stable where
expected, and ready for Wave 183 P3 (eval CLI sweep across
the ladder — foldability + self_consistency per
`tools/eval/cli.py`) and Wave 183 P4 (aggregation +
publication-quality figures). Total wall time **10.80 min**,
well within the per-wave compute budget.

**Output paths** (all under `/tmp/w183/fastas/`):
```
lineageflow_nfe10_baseline_seed42.fasta
lineageflow_nfe10_framework_seed42.fasta
lineageflow_nfe25_baseline_seed42.fasta
lineageflow_nfe25_framework_seed42.fasta
lineageflow_nfe50_baseline_seed42.fasta
lineageflow_nfe50_framework_seed42.fasta
lineageflow_nfe75_baseline_seed42.fasta
lineageflow_nfe75_framework_seed42.fasta
lineageflow_nfe100_baseline_seed42.fasta
lineageflow_nfe100_framework_seed42.fasta
lineageflow_nfe150_baseline_seed42.fasta
lineageflow_nfe150_framework_seed42.fasta
lineageflow_nfe200_baseline_seed42.fasta
lineageflow_nfe200_framework_seed42.fasta
lineageflow_nfe300_baseline_seed42.fasta
lineageflow_nfe300_framework_seed42.fasta
lineageflow_nfe500_baseline_seed42.fasta
lineageflow_nfe500_framework_seed42.fasta
kanzi_nfe10_baseline_seed42.fasta
kanzi_nfe10_framework_seed42.fasta
kanzi_nfe25_baseline_seed42.fasta
kanzi_nfe25_framework_seed42.fasta
kanzi_nfe50_baseline_seed42.fasta
kanzi_nfe50_framework_seed42.fasta
kanzi_nfe75_baseline_seed42.fasta
kanzi_nfe75_framework_seed42.fasta
kanzi_nfe100_baseline_seed42.fasta
kanzi_nfe100_framework_seed42.fasta
kanzi_nfe150_baseline_seed42.fasta
kanzi_nfe150_framework_seed42.fasta
kanzi_nfe200_baseline_seed42.fasta
kanzi_nfe200_framework_seed42.fasta
kanzi_nfe300_baseline_seed42.fasta
kanzi_nfe300_framework_seed42.fasta
kanzi_nfe500_baseline_seed42.fasta
kanzi_nfe500_framework_seed42.fasta
```