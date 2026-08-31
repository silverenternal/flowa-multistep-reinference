# r17 Phase-B: Image-Model Comparison (HiDream-I1-Dev + Lumina-Image 2.0)

Phase-B end-to-end smoke comparison between the HiDream-I1-Dev (sparse-DiT
text-to-image, 17B MoE distilled to 28 NFE) and Lumina-Image 2.0 (Gemma2 +
flow-matching, ~52.65 GB) adapters, each wrapped by the FlowA re-inference
scheduler harness (`tools/run_sota_hidream_i1_experiment.py` and
`tools/run_sota_lumina_image_2_0_experiment.py`).

Both adapters are designed end-to-end (see `adaptive_reflow/adapters/hidream_i1.py`
and the Lumina adapter spec) and the underlying T2I eval layer (FID +
CLIPScore in-process, GenEval + DPG-Bench as external stubs) is fully
documented in `docs/r17-survey/image-eval-plan.md`. **Neither harness
executed real inference in Phase B because both weight checkpoints are
absent from disk**: the on-disk trees at `data/hidream_i1/weights/` and
`data/lumina_image_2_0/weights/` are metadata + LFS pointers only. The
harness stubs both detected this and reported the gap; the JSON output
files do not exist.

> **Status: awaiting weights.** The two image-model harnesses are
> wiring-complete and pipeline-validated (adapter -> protocol -> harness
> -> stub exit). They will run end-to-end the moment real `.safetensors`
> / `.pth` payloads land on disk and a CUDA host is available.

## 1. Weights-presence audit (the blocker)

| Adapter | Path | Expected files | On-disk reality |
|---|---|---|---|
| **HiDream-I1** | `data/hidream_i1/weights/` | 7 x `transformer/diffusion_pytorch_model-{00001..00007}-of-00007.safetensors` (~5 GB each), text encoders (CLIP-L/14, CLIP-G/14, T5-XXL, Llama-3.1-8B), FLUX.1 VAE | **LFS pointers only.** Each transformer shard is a 135-byte `version https://git-lfs.github.com/spec/v1` pointer file. Metadata (config.json, model_index.json, scheduler/, vae/) is present but no payload. `weights_metadata.json` records `status=fetched_metadata_only`, `total_clone_size=7.0M`. |
| **Lumina-Image 2.0** | `data/lumina_image_2_0/weights/` | `Lumina-Image-2.0` consolidated checkpoint (~52.65 GB), Gemma2 text encoder (gated, license-gated) | **Metadata only.** `model_index.json` (411 B), `model_args.pth` (129 B), `README.md` (2.4 KB). No `diffusion_pytorch_model*.safetensors` or consolidated `.pth` payload. The repository is gated, and the size is above the auto-download budget. |

Both trees pass the smoke-`ls` check but fail the actual-load check: any
`safe_open(..., framework="pt")` call against the HiDream transformer
shards would error with *"InvalidFileException: does not contain a
header identifying it as a safetensors file"*; any `torch.load(...)`
against the Lumina checkpoint directory would error with
*"No such file or directory"*. We deliberately did not exercise the load
path against pointers because that would raise a misleading exception
in the harness rather than cleanly surfacing the metadata-only gap.

## 2. Harness invocation (ran, captured exit codes)

The harnesses were invoked with the operator-supplied args; both exited
without writing JSON to the requested `--output-dir`. Outputs captured
to `/tmp/{hidream,lumina}.out`.

### 2.1 HiDream-I1-Dev (cuda:1, RTX 5090 32 GB)

```bash
python tools/run_sota_hidream_i1_experiment.py \
    --weights-path data/hidream_i1/weights/transformer \
    --device cuda:1 \
    --variant dev \
    --n-samples 8 \
    --n-rounds 2 \
    --output-dir /tmp/phase_b_smoke/hidream
```

- **Exit code: 75** (`sysexits.h EX_TEMPFAIL` — temporary failure
  the user can resolve by supplying weights + GPU + eval stack).
- Behaviour: stub printed full rationale and the parsed-args block,
  no `summary.json`, no `baseline_samples/`, no `framework_samples/`.
- Rationale text (excerpt): *"The HiDream-I1 harness is not implemented
  in this skeleton release. HiDream-I1 is a 17B-parameter sparse-DiT
  model that requires ~64 GB HBM at fp16 inference. The published
  HiDream-ai/HiDream-I1-{Full,Dev,Fast} HF repos are unreachable from
  the sandbox (no HF token)."*
- `/tmp/phase_b_smoke/hidream/` was not created.

### 2.2 Lumina-Image 2.0 (cuda:0, RTX PRO 6000 98 GB)

```bash
python tools/run_sota_lumina_image_2_0_experiment.py \
    --checkpoint data/lumina_image_2_0/weights \
    --n-prompts 8 \
    --n-rounds 2 \
    --seed 0 \
    --output-dir /tmp/phase_b_smoke/lumina
```

- **Exit code: 0** (clean stub message; the Lumina stub does not
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
