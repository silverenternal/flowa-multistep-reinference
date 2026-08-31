# r17 Phase-C: Protein-Sequence Model Comparison (ProtBFN + AbBFN)

Phase-C end-to-end smoke comparison between the **ProtBFN** (650M params,
general protein-sequence Bayesian Flow Network) and **AbBFN**
(antibody-VH ProtBFN fine-tune) adapters, each driven through the
FlowA re-inference scheduler harness
`tools/run_sota_protbfn_abbfn_adapter_experiment.py`. The Phase-C
target is to demonstrate that FlowA's per-step re-inference budget
maintains (or improves) per-sequence metrics — `aar` (amino-acid
recovery), `freq_l1` (frequency L1 distance to natural proteins),
`novelty` (mean % sequence identity to the training set), `plddt_mean`
(mean pLDDT under ESMFold), `n_cap` (constrained-token count), `beta`
(diversity-vs-fidelity trade-off) — relative to a fixed-NFE baseline
at matched compute.

The adapters and protocol are wired end-to-end (`adaptive_reflow/adapters/protbfn_abbfn_adapter.py`,
8-method surface, all protocol-conformance tests passing in
`tests/test_adapters/test_protbfn_abbfn_adapter.py`). The Phase-C
harness did **not** run real inference in this iteration because
**the on-disk weight trees are LFS pointers only**, not actual
numpy payloads, and the harness itself is currently a TODO stub.

> **Status: weights landed; harness implementation still TODO.** The
> weight blockers are closed: ProtBFN and AbBFN each have ~541
> `array_*.npy` payloads (~2.5 GB each, symmetric). The harness
> `tools/run_sota_protbfn_abbfn_adapter_experiment.py` is still a one-line
> STUB that prints `STUB. TODO: implement the protein-sequence BFN SOTA
> harness. See docs/r4-survey/07-sota-experiment-protocol.md.` and exits
> 0, regardless of the supplied `--weights` / `--n-samples` /
> `--output-dir` / `--seed`. No JSON, no `baseline_sequences.fasta`, no
> `framework_sequences.fasta` was written. Finishing the harness is a
> discrete SOTA-runbook item — see §2.3 for the captured exit code and
> §3.3 for what is left.

## 1. Weights-presence audit (this iteration)

The two model directories at `data/protbfn_abbfn/weights_real/` were
populated from `InstaDeepAI/protein-sequence-bfn` (correct repo, case-
sensitive `InstaDeepAI/`):

| Path | Expected files | On-disk reality (this iteration) | Loadable? |
|---|---|---|---|
| **`ProtBFN/`** | ~541 `array_*.npy` weight slices | **Present.** 541 `array_*.npy` files, ~2.5 GB total, real payloads (varied sizes: 5 KB metadata slices + 25 MB dense slices). | Yes — `numpy.load(array_113.npy)` yields a real weight tensor. **Harness stub does not consume it** (see §2). |
| **`AbBFN/`** | ~541 `array_*.npy` weight slices | **Present.** Same shape as ProtBFN, ~2.5 GB total. Symmetric to ProtBFN. | Yes — same. |
| `README.md` | Repo README | **Present** (2.7 KB). | n/a |

The on-disk LFS-pointer gap documented in the previous revision is
closed for both models. The remaining gap is the experiment-harness
implementation: `tools/run_sota_protbfn_abbfn_adapter_experiment.py` is
a one-line `print(STUB_MSG)` shell with no argparse, no weight load, no
sequence decode, no metric dispatch.

## 2. Harness invocation (ran, captured exit code)

```bash
PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights_real/ProtBFN \
    --n-samples 8 \
    --output-dir /tmp/exp_c_protbfn \
    --seed 0

PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights_real/AbBFN \
    --n-samples 8 \
    --output-dir /tmp/exp_c_abbfn \
    --seed 0
```

- **Exit code: 0** for both runs (clean stub message; the protein
  harness is a TODO stub that prints one line and returns).
- Behaviour: stub printed
  `"tools/run_sota_protbfn_abbfn_adapter_experiment.py: STUB. TODO:
  implement the protein-sequence BFN SOTA harness. See
  docs/r4-survey/07-sota-experiment-protocol.md."`
  no `summary.json`, no `baseline_sequences.fasta`, no
  `framework_sequences.fasta`.
- Note: `--seed` was passed; the current stub CLI has no `argparse`
  setup at all, so it is accepted silently and ignored. The harness
  does not even parse `--weights` / `--n-samples` / `--output-dir`.
- `/tmp/exp_c_protbfn/` and `/tmp/exp_c_abbfn/` were not created
  (only `run.log` was written).

## 3. Metrics table (placeholder rows)

When weights and harness implementation land, the populated rows will
look like:

### 3.1 ProtBFN (650M, unconditional protein-sequence BFN)

| Metric | Baseline (100 BFN steps) | Framework (2 x 50 BFN steps) | Paired delta | Direction | Paper row |
|---|---:|---:|---:|:---:|---|
| aar | -- | -- | -- | higher is better | not reported (intrinsic-metric) |
| freq_l1 | -- | -- | -- | lower is better | Table 2 (CATH-S40 partition) |
| novelty | -- | -- | -- | higher is better | Table 2 |
| plddt_mean | -- | -- | -- | higher is better | Table 3 (ESMFold) |
| n_cap | -- | -- | -- | neutral (raw) | app-specific |
| beta | -- | -- | -- | context-dep | Pareto front |

### 3.2 AbBFN (ProtBFN fine-tuned on antibody VH chains)

| Metric | Baseline (100 BFN steps) | Framework (2 x 50 BFN steps) | Paired delta | Direction | Paper row |
|---|---:|---:|---:|:---:|---|
| aar | -- | -- | -- | higher is better | not reported |
| freq_l1 | -- | -- | -- | lower is better | Table (OAS VH partition) |
| novelty | -- | -- | -- | higher is better | Table (OAS) |
| plddt_mean | -- | -- | -- | higher is better | ESMFold appendix |
| n_cap | -- | -- | -- | neutral | optional |

Until the harness implementation lands, **all cells remain `--`**.

### 3.3 What is left to implement (per harness stub)

| Harness | What's stubbed | What's needed to light it up |
|---|---|---|
| `tools/run_sota_protbfn_abbfn_adapter_experiment.py` | A one-line `print(STUB_MSG); sys.exit(0)`. No `argparse`, no weight load, no adapter construction, no metric dispatch. | Replace stub with: `argparse` for `--weights` / `--n-samples` / `--output-dir` / `--seed`; `default_protbfnabbfn_adapter(weights=..., mode="torch")`; baseline + framework arms with paired seed; BFN decode loop; metric dispatch (`aar`, `freq_l1`, `novelty`, `plddt_mean` via ESMFold, `n_cap`, `beta`); JSON+FASTA output (`summary.json`, `baseline_sequences.fasta`, `framework_sequences.fasta`). Per `docs/r4-survey/07-sota-experiment-protocol.md`. |

This stub is intentional in the r17 skeleton release; this iteration's
contribution is documenting the post-weights-blocker gap.

## 4. Per-arm comparison (the planned Phase-C runbook)

Each row in §3 will be the per-model, paired-delta summary that the
harness is supposed to produce. The protocol-conformance tests already
validate the adapter -> endpoint -> metric-JSON plumbing against the
synthetic BFN backend, so once the harness implementation lands the
only remaining work is:

1. Implement `tools/run_sota_protbfn_abbfn_adapter_experiment.py`
   (currently a one-line stub) per the seven-step runbook in
   `docs/r4-survey/07-sota-experiment-protocol.md`.
2. Wrap the adapter in the four canonical scheduler wrappers
   (`default_cosine_scheduler`, `CodimensionSheetScheduler`,
   `EvidenceDrivenScheduler`, `FreeTrajScheduler`).
3. Drive each wrapper for `--n-rounds` rounds, collecting per-round
   `{aar, freq_l1, novelty, plddt_mean, n_cap, beta}` metric dicts.
4. Compute paired-delta = framework - baseline (positive = framework
   wins, sign reversed for `lower-is-better` rows).
5. Emit `summary.json` + per-arm fasta + per-arm pkl metrics.
6. Render this `prot-comparison.md` with the real numbers.

## 5. Compute & packaging notes

- **Compute.** Phase-C is CPU-only by design: ProtBFN (650M params) and
  AbBFN (650M params, fine-tune) fit in <2 GB HBM at fp32 and the
  BFN update loop is not throughput-bound on the small batch sizes
  the protocol uses. No GPU required.
- **Dependencies.** ESMFold for `plddt_mean` is the heaviest external
  dep (~3 GB params, runs on CPU at ~5 s/sequence). pLDDT can be
  skipped (set `--skip-plddt`) for a faster smoke; the metric block
  becomes four instead of five columns.
- **Eval venv.** Same pattern as Phase-B image eval: ESMFold lives in
  an isolated venv (the framework venv does not host it). Pre-compute
  pLDDT for sequences cached in `data/protbfn_abbfn/runs/seqs.fasta`
  to amortise the cost across reruns.

## 6. Repro commands (the *intended* Phase-C runbook)

```bash
# Phase-C protein smoke (CPU; ProtBFN + AbBFN)
PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights_real/ProtBFN \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir data/protbfn_abbfn/runs/protbfn_smoke/seed_0 \
    --seed 0

PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights_real/AbBFN \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir data/protbfn_abbfn/runs/abbfn_smoke/seed_0 \
    --seed 0
```

Pre-flight checklist before pressing go:

- [ ] Real ProtBFN `array_*.npy` payloads in
      `data/protbfn_abbfn/weights/ProtBFN/` (~3 GB, fetched via
      `git lfs pull` inside the clone).
- [ ] Real AbBFN `array_*.npy` payloads in
      `data/protbfn_abbfn/weights/AbBFN/` (~3 GB, same).
- [ ] Seven-step runbook stub finished at
      `tools/run_sota_protbfn_abbfn_adapter_experiment.py` (replace
      the one-line `print(...) + return 0` body with the four-scheduler
      driver per `docs/r4-survey/07-sota-experiment-protocol.md`).
- [ ] (Optional) ESMFold installed in an isolated venv for the
      `plddt_mean` block.
- [ ] (Optional) CATH-S40 / OAS reference statistics for `freq_l1`
      reference distributions.

## 7. Summary

- **Phase C ran: NO.** Harness invocation captured; stub exited
  cleanly without writing outputs because (a) the on-disk
  `array_*.npy` files are LFS pointers, not real weights, and (b)
  the harness is itself a TODO stub pending the seven-step runbook
  implementation.
- **Phase C ready: PARTIAL.** The adapter, protocol, metric surface,
  and protocol-conformance tests are all in place; only the SOTA
  harness and the real weights are missing.
- **Capture location of the failed-run stderr:** `/tmp/protbfn.out`.

When real weights land and the seven-step runbook is finished, the
harness will populate §3 with paper-comparable numbers and this
document will be regenerated from the harness's own emitted
`comparison.md`.
