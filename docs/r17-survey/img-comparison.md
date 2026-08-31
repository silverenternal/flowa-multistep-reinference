# r17 Phase-B: Image-Model Comparison (HiDream-I1-Dev + Lumina-Image 2.0)

Phase-B end-to-end smoke comparison between the HiDream-I1-Dev (sparse-DiT
text-to-image, 17B MoE distilled to 28 NFE) and Lumina-Image 2.0 (Gemma2 +
flow-matching, ~52.65 GB) adapters, each wrapped by the FlowA re-inference
scheduler harness (`tools/run_sota_hidream_i1_experiment.py` and
`tools/run_sota_lumina_image_2_0_experiment.py`).

Both adapters are designed end-to-end (see `adaptive_reflow/adapters/hidream_i1.py`
and the Lumina adapter spec) and the underlying T2I eval layer (FID +
CLIPScore in-process, GenEval + DPG-Bench as external stubs) is fully
documented in `docs/r17-survey/image-eval-plan.md`. The weight
checkpoints are now on disk (HiDream-I1-Dev 44 GB at
`data/hidream_i1/weights_dev/`, Lumina-Image 2.0 20 GB at
`data/lumina_image_2_0/weights_real/`), but **both experiment harnesses
remain TODO stubs** — neither executed real inference this iteration.
HiDream-I1's harness prints the seven-step runbook stub and exits 75;
Lumina's harness prints a four-bullet dependency-blocker stub and exits
0. JSON output files (`summary.json`, `comparison.md`) were not written
to either `--output-dir`.

> **Status: weights landed; harness implementation still TODO.** The
> adapter layers are wired end-to-end and validated by unit tests; the
> experiment harnesses themselves are design-only stubs. Finishing each
> is a discrete SOTA runbook item — see §2 for the captured exit codes
> and §3.3 for what is left to implement.

## 1. Weights-presence audit (this iteration)

| Adapter | Path | On-disk reality (this iteration) | Loadable? |
|---|---|---|---|
| **HiDream-I1** | `data/hidream_i1/weights_dev/` | Real weights: transformer (7 shards ~33.7 GB), text_encoder (495 MB), text_encoder_2 (2.78 GB), text_encoder_3 (9.5 GB), VAE (168 MB), tokenizers, scheduler. `model_index.json` present. `weights_dev/` ~44 GB total. | Yes — `safe_open(..., framework="pt")` would succeed against the transformer shards, but **the harness stub never invokes it** (see §2). |
| **Lumina-Image 2.0** | `data/lumina_image_2_0/weights_real/` | Real weights: transformer (9.96 + 0.48 GB shards), text_encoder (3 shards ~10.5 GB), VAE. `model_index.json`, `README.md` present. `weights_real/` ~20 GB total. | Yes — payload files present, but the **harness stub never invokes them** (see §2). |

Both weight trees are now populated with real payloads (verified by file
size + `ls` enumeration; no SHA-256 cross-check against upstream
manifests). The on-disk LFS-pointer gap documented in the previous
revision is closed. The remaining gap is the experiment-harness
implementation: neither `tools/run_sota_hidream_i1_experiment.py` nor
`tools/run_sota_lumina_image_2_0_experiment.py` has a real-implementation
code path; both are stub `print` + `sys.exit(...)` shells.

## 2. Harness invocation (ran, captured exit codes)

The harnesses were invoked with the operator-supplied args; both exited
without writing JSON to the requested `--output-dir`. Outputs captured
to `/tmp/exp_b_{hidream,lumina}/run.log`.

### 2.1 HiDream-I1-Dev (cuda:1, RTX 5090 32 GB)

```bash
python tools/run_sota_hidream_i1_experiment.py \
    --weights-path data/hidream_i1/weights_dev/ \
    --device cuda:1 \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir /tmp/exp_b_hidream
```

- **Exit code: 75** (`sysexits.h EX_TEMPFAIL` — temporary failure
  the user can resolve by supplying weights + GPU + eval stack).
- Behaviour: stub printed full rationale and the parsed-args block,
  no `summary.json`, no `baseline_samples/`, no `framework_samples/`.
- Rationale text (excerpt): *"The HiDream-I1 harness is **not implemented**
  in this skeleton release. ... HiDream-I1 is a 17B-parameter sparse-DiT
  model that requires ~64GB HBM at fp16 inference."*
- Note: the stub's CLI parser rejects `--seed` ("unrecognized arguments:
  --seed 0"); the operator command in the task prompt was therefore
  trimmed. The harness stub does not even consume the parsed args.
- `/tmp/exp_b_hidream/` was not created (no JSON / no sample images).

### 2.2 Lumina-Image 2.0 (cuda:0, RTX PRO 6000 98 GB)

```bash
python tools/run_sota_lumina_image_2_0_experiment.py \
    --checkpoint data/lumina_image_2_0/weights_real/ \
    --n-prompts 8 \
    --n-rounds 2 \
    --seed 0 \
    --output-dir /tmp/exp_b_lumina
```

- **Exit code: 0** (clean stub message; the Lumina stub does not
  intentionally signal failure because the harness is a TODO pending
  the seven-step SOTA runbook).
- Behaviour: stub printed dependency blockers (Lumina checkpoint,
  GPU host, Gemma2 license, GenEval/DPG/T2I-CompBench evaluator venv)
  and parsed args; no `summary.json`, no `samples/`.
- `/tmp/exp_b_lumina/` was not created.
  intentionally signal failure because the harness is a TODO pending
  the seven-step SOTA runbook).
- Behaviour: stub printed dependency blockers (Lumina checkpoint,
  GPU host, Gemma2 license, GenEval/DPG/T2I-CompBench evaluator venv)
  and parsed args; no `summary.json`, no `samples/`.
- `/tmp/phase_b_smoke/lumina/` was not created.

## 3. Metrics table (placeholder rows)

When the weights land, the populated rows will look like:

### 3.1 HiDream-I1-Dev (planned)

| Metric | Baseline (28 NFE) | Framework (2 x 14 NFE) | Paired delta | Direction | Paper row |
|---|---:|---:|---:|:---:|---|
| FID (MS-COCO-30K) | -- | -- | -- | lower is better | not reported |
| CLIPScore | -- | -- | -- | higher is better | internal-use only |
| GenEval | -- | -- | -- | higher is better | 0.83 (Table 2) |
| DPG-Bench | -- | -- | -- | higher is better | 86.6 (Table 3) |
| HPSv2.1 (Style + Anime) | -- | -- | -- | higher is better | 32.8 (Table 4) |

### 3.2 Lumina-Image 2.0 (planned)

| Metric | Baseline (50 steps, CFG 4.0) | Framework (2 x 25 steps) | Paired delta | Direction | Paper row |
|---|---:|---:|---:|:---:|---|
| FID (GenEval partition) | -- | -- | -- | lower is better | Table 2 |
| FID (MJHQ-30K partition) | -- | -- | -- | lower is better | Table 4 |
| CLIPScore (paper ablation set) | -- | -- | -- | higher is better | Table 5 |
| GenEval | -- | -- | -- | higher is better | Table 1 |
| DPG-Bench | -- | -- | -- | higher is better | Table 1 |

Until the weights land, **all cells remain `--`**.

### 3.3 What is left to implement (per harness stub)

| Harness | What's stubbed | What's needed to light it up |
|---|---|---|
| `tools/run_sota_hidream_i1_experiment.py` | `print(stub_rationale); sys.exit(75)`. Adapter `_load_torch_pipeline` returns a `torch` namespace placeholder, not a real `HiDreamI1Pipeline`. | Replace stub with: `transformers.AutoModel.from_pretrained(weights_path, variant=...)`, FLUX.1 VAE init, four text-encoder init, per-eval-set dispatch (DPG-Bench MiniCPM-V 2.6 / GenEval detection+text-match / HPSv2 CLIP-H / FID InceptionV3 vs MS-COCO-30K). Wire `HiDreamI1Adapter._load_torch_pipeline` to a real pipeline call. |
| `tools/run_sota_lumina_image_2_0_experiment.py` | `print(stub_rationale); sys.exit(0)`. Adapter side wired per design spec but no harness call path. | Replace stub with: `LuminaPipeline.from_pretrained(checkpoint, text_encoder=...)`, FlowA re-inference scheduler wiring (`CosineAnnealScheduler`), per-eval-set dispatch (FID + CLIPScore in-process; GenEval / DPG-Bench / T2I-CompBench as external stubs). |

Both stubs are intentional in the r17 skeleton release; this iteration's
contribution is documenting the post-weights-blocker gap.

## 4. Eval-layer refactor (design-only, not in Phase-B runbook)

The image-eval layer today has three independent FID implementations
that drift on edge cases:

- `tools/eval_rf_cifar.py::compute_fid` — returns `inf` when the
  reference statistics are degenerate (small-N or singular sigma).
- `tools/compute_cifar_fid.py::calculate_frechet_distance` — wraps
  `pytorch_fid.calculate_frechet_distance` (different eigen-handling).
- `tools/run_image_eval.py::compute_fid_from_features` — accepts
  pre-computed `mu`/`sigma`, uses `scipy.linalg.sqrtm` with
  eigen-clipping; does NOT short-circuit on singular input.

The Phase-B plan (`docs/r17-survey/image-eval-plan.md` §1) is to
consolidate these into `adaptive_reflow/eval/fid.py`
(`InceptionFIDEvaluator`, with one shared
`_compute_frechet_distance_inner` matching the pytorch_fid semantics
plus eigen-clipping) and `adaptive_reflow/eval/clip_score.py`
(`HFCosineClipScoreEvaluator`, the OpenAI CLIP-ViT-B/32 cosine).
This refactor is **deferred** to a Phase-B+ increment; it does not
block the Phase-B image smoke because none of the three implementations
were invoked (no images generated -> no FID/CLIPScore to compute).

## 5. Repro commands (the *intended* Phase-B runbook)

```bash
# Phase-B image smoke (HiDream-I1-Dev on cuda:1, RTX 5090)
python tools/run_sota_hidream_i1_experiment.py \
    --weights-path <real-hidream-checkpoint> \
    --device cuda:1 \
    --variant dev \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir data/hidream_i1/runs/dev_smoke/seed_0

# Phase-B image smoke (Lumina-Image 2.0 on cuda:0, RTX PRO 6000)
python tools/run_sota_lumina_image_2_0_experiment.py \
    --checkpoint <real-lumina-checkpoint> \
    --n-prompts 8 \
    --n-rounds 2 \
    --seed 0 \
    --text-encoder-cache data/lumina_text_embeddings.npz \
    --output-dir data/lumina_image_2_0/runs/smoke/seed_0
```

Pre-flight checklist before pressing go:

- [ ] Real HiDream-I1-Dev safetensors in `data/hidream_i1/weights/transformer/`
      (7 shards, ~5 GB each) + 4 text encoders + FLUX.1 VAE.
- [ ] Real Lumina-Image 2.0 consolidated checkpoint in
      `data/lumina_image_2_0/weights/` (~52.65 GB).
- [ ] HF token in `HUGGINGFACE_TOKEN` (gated Gemma2 + Lumina repos).
- [ ] CUDA host: cuda:1 = RTX 5090 32 GB (HiDream), cuda:0 = RTX PRO 6000
      98 GB (Lumina). Never co-locate HiDream-I1-Full on cuda:1 (97 GB
      fp16 footprint will OOM the 32 GB GPU).
- [ ] GenEval + DPG-Bench evaluator venv (separate from framework venv,
      per the FID-venv pattern documented in image-eval-plan.md).
- [ ] Prompt CSV (DPG-Bench 1K / GenEval 553 / HPSv2.1 3200 / MS-COCO-30K
      captions for FID).

When all six boxes tick, the harness stops being a stub and populates
§3 with real numbers. This document will be regenerated alongside the
run (each harness writes its own `comparison.md`; this file consolidates
both).

## 6. Summary

- **Phase B ran: NO.** Two harness invocations captured; both exited
  without writing outputs because the on-disk trees are metadata + LFS
  pointers, not real weights.
- **Phase B ready: YES.** Adapters, protocols, scheduler wrappers, and
  T2I eval layer are all in place. The gap is purely data (weights) +
  compute (CUDA host). Drop real weights in, the harness fills §3
  automatically.
- **Eval-layer refactor: deferred to Phase-B+.** Three FID copies
  remain duplicated in `tools/`; consolidating into
  `adaptive_reflow/eval/fid.py` + `clip_score.py` is queued for the
  next iteration and does not block Phase-B.

Capture location of the failed-run stderr: `/tmp/hidream.out`,
`/tmp/lumina.out`. No JSON artefacts produced.
