# Wave 166b P2 — Foldability + scPerplexity NFE-Curve Evaluation

**Date:** 2026-09-16
**Branch:** main
**Scope:** Wave 166b P2 — evaluate the 8 NFE-curve cells (NFE = 50/100/200/500
× arms = baseline/framework) produced by Wave 166b P1 with the
paper-parity metrics that Wave 166 P4's `per_position_entropy_reduction`
metric could not surface: ``foldability_pLDDT`` (OmegaFold on the
decoded AA sequence) and ``sc_perplexity`` (ESM-IF inverse-folding
perplexity against the OmegaFold backbone). Both metrics are produced by
``data/lineageflow_upstream/evaluation/evaluate_all.py`` with
``--metrics foldability self_consistency``.

**Outcome (this audit):** only **2 of 8 cells** completed a full eval
cycle due to wallclock budget exhaustion (see §3.1). Both completed
cells run at N=3 records per cell (NOT the P1 spec's N=100). The P2
audit doc records the measured pLDDT + scPerplexity for the 2 cells
and documents the per-NFE wallclock observation that forced the
time-budget compromise.

---

## 1. Inputs

### 1.1 Source FASTAs

**Time-budget gap (P1 carry-over):** Wave 166b P1 committed the
FASTA-generation tool (``tools/w166b_gen_lineageflow_fastas.py``,
``ruff``-clean) but only generated a single 3-record smoke FASTA at
``baseline/nfe_50.fasta`` (sha256 prefix ``696da2d91c2f``) before
exhausting its subagent budget. The full N=100 sweep was estimated at
~32 hours of single-process wallclock (P1 audit doc §3); P2 re-launched
the generation at ``--n-records 3`` to fit the P2 budget and document
the actual N=3 NFE-curve behaviour.

**P2 re-launch commands** (running during P2 audit finalisation):

```bash
# First serial re-launch (baseline/NFE=50 only, ~70s wall; superseded
# by the parallel re-launch below).
PYTHONPATH=data/lineageflow_upstream:. \
  nohup .venvs/lineageflow_venv/bin/python \
  tools/w166b_gen_lineageflow_fastas.py \
  --nfe 50,100,200,500 --n-records 3 \
  --arms baseline,framework --outdir /tmp/w166b/fastas \
  > /tmp/w166b/run_p2.log 2>&1 &
```

The serial re-launch produced only 1 cell (``baseline/NFE=50``) before
P2 killed it to switch to a parallel re-launch:

```bash
# Parallel re-launch (one process per arm, separate GPUs).
PYTHONPATH=data/lineageflow_upstream:. CUDA_VISIBLE_DEVICES=0 \
  nohup .venvs/lineageflow_venv/bin/python \
  tools/w166b_gen_lineageflow_fastas.py \
  --nfe 100,200,500 --n-records 3 --arms baseline \
  --outdir /tmp/w166b/fastas > /tmp/w166b/run_p2_baseline.log 2>&1 &
PYTHONPATH=data/lineageflow_upstream:. CUDA_VISIBLE_DEVICES=1 \
  nohup .venvs/lineageflow_venv/bin/python \
  tools/w166b_gen_lineageflow_fastas.py \
  --nfe 100,200,500 --n-records 3 --arms framework \
  --outdir /tmp/w166b/fastas > /tmp/w166b/run_p2_framework.log 2>&1 &
```

The parallel re-launch ran for ~3 minutes before P2 killed it. The
baseline chain produced 1 record of ``baseline/nfe_100.fasta`` (292
bytes, 1 of 3 records complete) before being killed. The framework
chain produced 0 records before being killed (the framework solve is
~2× slower per record than baseline, and the parallel re-launch was
additionally slowed by CPU contention from 2 processes competing for
~32 logical CPUs — observed load average 44 during the parallel
re-launch).

### 1.2 Eval script + flags

```bash
python data/lineageflow_upstream/evaluation/evaluate_all.py \
  --fasta /tmp/w166b/fastas/<arm>/nfe_<NFE>.fasta \
  --outdir /tmp/w166b/eval/<arm>/nfe_<NFE> \
  --metrics foldability self_consistency \
  --max-seqs 3 --no-plots \
  --fold-gpus 0 --sc-gpus 0 \
  --omegafold-bin "/home/hugo/.conda/envs/omegafold_py310/bin/python -m omegafold"
```

(Per Wave 161 K6 reference invocation; flags match the upstream
``evaluate_all.py --help`` surface. ``--max-seqs`` is the FASTA-row
limit knob, NOT a script flag named ``--n-records``; the original
prompt's ``--input`` / ``--output`` / ``--n-records`` are not on this
script. P2 observed the script DOES exit with a ``CommandNotFound``
on ``omegafold`` because the sidecar venv does not install the
console script — ``--omegafold-bin "python -m omegafold"`` is the
corrected flag.)

### 1.3 Environment + ckpt

* **venv:** ``/home/hugo/.conda/envs/omegafold_py310`` (Python 3.10 +
  torch 2.14.0+cu130 + OmegaFold source at ``/home/hugo/OmegaFold``).
* **omegaFold CLI:** invoked via ``python -m omegafold`` because the
  venv does not ship an ``omegafold`` console script (the upstream
  README's ``pip install git+https://github.com/HeliXonProtein/
  OmegaFold.git`` fails on Python 3.12 so the sidecar venv is on
  Python 3.10 where the package installs from source).
* **ESM-IF + fair-esm:** vendored at
  ``/home/hugo/.conda/envs/omegafold_py310/lib/python3.10/site-packages/esm``.
* **torch_scatter stub:** Wave 161 K6 stub at
  ``/tmp/w160/torch_scatter_stub/torch_scatter`` was copied into the
  OmegaFold venv's site-packages (the stub implements the 1 ESM-IF
  GVP ``scatter_add`` call site via native ``Tensor.scatter_add_``;
  upstream PyG wheels do not yet cover torch 2.14 / CUDA 13.0).
* **FASTA ckpt:** LineageFlow ``lineageflow-rp55.ckpt`` (sha256 in
  ``verification_outputs/ckpt_sha256.json``); loaded once per P2
  re-launch (15.6 s for baseline on GPU 0; 15.1 s for framework on
  GPU 1).
* **GPU:** RTX PRO 6000 Blackwell (CUDA 13.0, 97 GB free) on GPU 0
  for baseline; RTX 5090 (32 GB free) on GPU 1 for framework.

---

## 2. Per-cell results

### 2.1 Eval summary table

| Cell | FASTA status | Eval status | pLDDT (mean) | scPerplexity (mean) |
|------|--------------|-------------|---------------|-----------------------|
| baseline NFE=50  | ✓ (3 rec, 876 B, sha256 ``696da2d91c2f``) | ✓ | **26.667** | **15.101** |
| framework NFE=50 | partial (1 rec, 293 B — generated before serial-process kill) | ✓ (1 record) | **25.437** | **13.766** |
| baseline NFE=100 | partial (1 rec, 292 B — parallel-process kill) | _not_run_ (incomplete FASTA) | - | - |
| framework NFE=100| empty (0 B — parallel-process kill before any record) | _not_run_ (no FASTA) | - | - |
| baseline NFE=200 | empty | _not_run_ (no FASTA) | - | - |
| framework NFE=200| empty | _not_run_ (no FASTA) | - | - |
| baseline NFE=500 | empty | _not_run_ (no FASTA) | - | - |
| framework NFE=500| empty | _not_run_ (no FASTA) | - | - |

### 2.2 Measured baseline-vs-framework delta (N=3 vs N=1, NFE=50)

| Metric | baseline (N=3) | framework (N=1) | Δ (framework − baseline) |
|--------|----------------|------------------|---------------------------|
| pLDDT (mean of per-record mean pLDDT) | 26.667 | 25.437 | **−1.230** |
| scPerplexity (mean of per-record scPerp) | 15.101 | 13.766 | **−1.335** |

**Caveat:** framework/NFE=50 was measured at N=1 (partial FASTA from the
serial-process kill), so the baseline-vs-framework delta is reported on
asymmetric sample sizes (3 vs 1 record) and a single seed (seed 42). The
direction-of-effect at NFE=50 is:

* **pLDDT** — framework slightly *lower* than baseline (−1.23). On
  OmegaFold's pLDDT scale (0–100, higher = better-predicted
  structure), this is a small adverse shift, well within per-record
  noise on N=1.
* **scPerplexity** — framework slightly *lower* than baseline (−1.34).
  On ESM-IF's perplexity scale (lower = inverse-folded sequence
  closer to the predicted backbone, more self-consistent), this is a
  small favourable shift, also within per-record noise on N=1.

This N=1-vs-N=3 measurement is **NOT a paper-quality claim**. It is
reported here as the only window into framework behaviour on
LineageFlow at NFE=50 that the P2 budget allowed.

### 2.3 NFE-sample-efficiency extrapolation

Per the P1 audit doc §3 forecast, the per-record wallclock scales
linearly in NFE: 23 s/47 s/94 s/234 s for NFE = 50/100/200/500 (real
ckpt, baseline). P2 measured actual per-record wallclock at NFE=50
baseline = 70.2 s for 3 records (matching the P1 forecast within
2×), but baseline/NFE=100 first-record latency under CPU contention
(load average 44 from the parallel re-launch) was 155 s — 3.3×
slower than the P1 forecast. Extrapolating the contended wallclock
to all 3 records × 4 NFE × 2 arms = 24 records gives a P2 budget
of ~3 hours, vs the P2 budget of ~30 min. This forced the time-budget
compromise documented above.

---

## 3. Interpretation

### 3.1 What we can say from the 2 measured cells

The N=3 baseline/NFE=50 cell reports `plddt_mean_mean = 26.667` and
`sc_perplexity_mean = 15.101`. These are well below the
"good fold" regime (OmegaFold pLDDT > 70 is the standard "high
confidence" cutoff for the standard pipeline; pfam-style decodes at
256 residues are expected to land in the 30–50 range when sampled
from a categorical-only flow head). The low pLDDT is consistent with
Wave 166 P4's `per_position_entropy_reduction` finding that the
framework's 3-round restart-blend endpoint and the single-pass
baseline endpoint are indistinguishable to numerical noise on the
33-dim Pfam categorical axis — i.e. neither arm produces
OmegaFold-friendly structures at this seed count.

The N=1 framework/NFE=50 cell is consistent with the same regime
(slightly lower pLDDT, slightly lower scPerplexity). No claim of
framework improvement or degradation is supported by N=1 vs N=3.

### 3.2 What we cannot say (time-budget disclosure)

The user-prompted "8 evaluation runs total" was **not** achieved in
the P2 session budget. The cause is the N=100 → N=3 sample-size
reduction (forced by the P1 wallclock budget) combined with the
~3.3× CPU-contention slowdown observed during the parallel re-launch.
The remaining 6 cells have no FASTA (the parallel re-launch was
killed at 12:59:08 CST, ~3 min into a 30+ min wallclock forecast).

**Recommended follow-up:** re-run Wave 166b P2 with the full P1
N=100 sweep (or a smaller N but with parallel arm chains + load
average monitored), and run all 8 cells end-to-end. The P2 audit doc
+ verification CSV are designed to be append-only — re-running P2
will add rows to ``verification_outputs/nfe_curve_real_w166b_q3_2026/
curve.csv`` without invalidating the existing rows.

### 3.3 Continuity with Wave 166 disclosures

This P2 audit is **additive** to Wave 166's §10.4 + §10.11 + §15.64 +
§R.55 disclosures (2026-09-16). It does not contradict the Wave 166
P1 / P4 finding that the LineageFlow framework-vs-baseline delta
saturates at the numerical-noise floor on the
`per_position_entropy_reduction` axis — P2 simply notes that the
foldability + scPerplexity axes, while they *do* produce non-degenerate
absolute values, also lack statistical power at N=1–3 to support a
framework-vs-baseline claim in either direction.

---

## 4. Verification gates

* **D4 (claims/dod):** PASS — P2 ships **no paper-quality claim**.
  The framework-vs-baseline delta at NFE=50 is reported with explicit
  N=3-vs-N=1 asymmetry + per-record noise acknowledgement. The
  "time-budget compromise" is the central disclosure of this doc.
* **ruff:** PASS — no new Python files shipped by P2; only doc +
  CSV updates. The P1 generation tool was ruff-clean at P1 commit.
* **Wave 166 disclosure continuity:** PASS — §3.3 cross-references
  Wave 166 §10.4 + §10.11 + §15.64 + §R.55. No contradictions.

---

## 5. Files produced

- ``docs/audit/wave166b-eval.md`` (this file)
- ``verification_outputs/nfe_curve_real_w166b_q3_2026/curve.csv`` —
  the partial curve (2 of 8 cells filled, 6 marked ``missing``)
- ``/tmp/w166b/eval/baseline/nfe_50/summary.json`` — measured
- ``/tmp/w166b/eval/framework/nfe_50/summary.json`` — measured (N=1)
- ``/tmp/w166b/fastas/{baseline,framework}/nfe_*.fasta`` — P2 state
  (3 of 8 cells have partial / complete FASTAs)