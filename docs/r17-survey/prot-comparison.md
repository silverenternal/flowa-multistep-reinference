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

> **Status: awaiting weights + harness implementation.** Both blockers
> are concrete and small: drop real `array_*.npy` files in place
> (~3 GB each for ProtBFN/AbBFN) and finish the seven-step SOTA
> runbook stub at `tools/run_sota_protbfn_abbfn_adapter_experiment.py`
> per `docs/r4-survey/07-sota-experiment-protocol.md`.

## 1. Weights-presence audit (the blocker)

The two model directories at `data/protbfn_abbfn/weights/` were cloned
from the canonical HF repo `InstaDeepAI/protein-sequence-bfn`
(repos `instadeepai/protbfn-650m` and `instadeepai/AbBFN` returned
`{"error": "Invalid username or password."}` from the HF API and do
not exist; the correct repo is case-sensitive `InstaDeepAI/`). The
metadata is sound, but the `array_*.npy` payloads are LFS pointers:

| Path | Expected files | On-disk reality |
|---|---|---|
| **`ProtBFN/`** | ~541 `array_*.npy` weight slices (~3 GB total) | **LFS pointers only.** `file array_0.npy` reports `ASCII text`; first bytes are `version https://git-lfs.github.com/spec/v1\noid sha256:...`. Each file is 129-133 bytes. `du -sh` = 2.2 MB (just metadata). |
| **`AbBFN/`** | ~541 `array_*.npy` weight slices (3 GB antibody-VH fine-tune) | **LFS pointers only.** Same shape as `ProtBFN/`; 2.2 MB total. |
| `README.md`, `BFN_overview.png`, `cath_s40_proteins.png` | Repo-level assets | **Present.** |

A direct `numpy.load(array_0.npy)` call against the on-disk file would
**not** raise (numpy would happily parse the ASCII text as a 0-d string
array of length 130), but loading would yield *not-a-weight-array* and
any subsequent `torch.from_numpy(...)` or `np.dot(...)` would either
crash or return garbage. We deliberately did not exercise the load
path because that would be misleading; the clean signal is that LFS
payloads were never fetched (`weights_metadata.json` is honest about
this: `"status": "downloaded"` reports 6.4 MB total, which is
metadata-only).

## 2. Harness invocation (ran, captured exit code)

```bash
PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights/ProtBFN \
    --n-samples 8 \
    --output-dir /tmp/phase_c_smoke/protbfn \
    --seed 0
```

- **Exit code: 0** (clean stub message; the protein harness is a TODO
  stub that prints one line and returns).
- Behaviour: stub printed
  `"tools/run_sota_protbfn_abbfn_adapter_experiment.py: STUB. TODO:
  implement the protein-sequence BFN SOTA harness. See
  docs/r4-survey/07-sota-experiment-protocol.md."`
  no `summary.json`, no `baseline_sequences.fasta`, no
  `framework_sequences.fasta`.
- Note: `--seed` was passed; the current stub CLI ignores it (no
  `argparse` setup at all). Adding `--seed` to the stub arg-parser is
  one of the Phase-C harness TODO items.
- `/tmp/phase_c_smoke/protbfn/` was not created.

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

Until the weights land, **all cells remain `--`**.

## 4. Per-arm comparison (the planned Phase-C runbook)

Each row in §3 will be the per-model, paired-delta summary that the
harness is supposed to produce. The protocol-conformance tests already
validate the adapter -> endpoint -> metric-JSON plumbing against the
synthetic BFN backend, so once real weights land the only remaining
work is:

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
    --weights data/protbfn_abbfn/weights/ProtBFN \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir data/protbfn_abbfn/runs/protbfn_smoke/seed_0 \
    --seed 0

PYTHONPATH=. python tools/run_sota_protbfn_abbfn_adapter_experiment.py \
    --weights data/protbfn_abbfn/weights/AbBFN \
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
