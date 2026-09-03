# Image-Eval Tier-2 Harness Progress (HiDream / Lumina §6.2 build-out)

**Date:** 2026-09-03
**Owner:** this document; the harness surface lives at `tools/run_image_eval.py`
**Audience:** operator with a CUDA host (RTX 5090 32 GB + RTX PRO 6000 98 GB)
**Status convention:** [WIRED] means the runner emits a real number under
`metrics.<name>`; [STUB] means it emits a `marker: "external"` (or
`"not_installed"`) placeholder; [BLOCKED] means the harness needs an
upstream dependency that is not installable on this host today.

---

## §1. Tier-1 (in-process, runs in `hidream_venv` / `lumina_venv`)

| Metric | Status | Code path | Action |
|---|---|---|---|
| **FID** | [WIRED] | `tools/run_image_eval.py::run_fid_metric` (InceptionV3 pool3 + scipy sqrtm) | none — `--reference-stats data/fid_stats/mjhq30k_inception_stats.npz` |
| **CLIPScore** | [WIRED] | `run_clipscore_metric` (`openai/clip-vit-base-patch32` via HF transformers, 100× paper scale) | none — `--prompts-jsonl <prompts.jsonl>` |

The Tier-1 stack is unchanged from Phase B. `--reference-stats` resolves
to the Lumina canonical `mjhq30k_inception_stats.npz` (~33 MB); HiDream
has no canonical reference yet (paper does not lead with FID — see
`docs/r17-survey/baseline-deviation-review.md` §1.4).

## §2. Tier-2 (external subprocess wrappers, each in its own venv)

The runner emits the byte-stable `{"value": null, "marker": "external",
"sub_scores": {...}}` stub for every Tier-2 metric by default. Passing
the metric-specific `--<name>-binary` opt-in to the subprocess wrapper
swaps the stub for a real run. Below is the checklist of each Tier-2
metric, what the wrapper does, what the upstream CLI is, and the
install status today.

### §2.1 GenEval (HiDream-I1 / Lumina-Image 2.0 paper Table 2)

| | |
|---|---|
| **Upstream** | `github.com/djghosh13/geneval` (djghosh13, MIT) |
| **Upstream CLI** | `python evaluation/evaluate_images.py <image_dir> --outfile <results.jsonl> --model-path <detector_dir>` then `python evaluation/summary_scores.py <results.jsonl>` |
| **Expected output shape** | one stdout line per sub-task (`single_object   = 92.50% (37 / 40)` etc.) plus `Overall score (avg. over tasks): 0.78300` |
| **Wrapper function** | `tools/run_image_eval.py::run_geneval_metric` |
| **Wrapper status** | **[WIRED]** — invoked when `--geneval-binary` is set. Stages the flat SOTA samples into GenEval's numbered-subfolder layout (`<idx>/samples/<idx>.png` + `<idx>/metadata.jsonl`), shells out to `evaluate_images.py` with a 600 s timeout, parses `summary_scores.py` stdout into `sub_scores` + `value`. Heuristic `_infer_geneval_tag()` maps flat prompt strings to one of the six sub-tasks when the operator only has a `[prompt, ...]` JSONL; supplying the upstream `evaluation_metadata.jsonl` (with `tag`/`include`/`exclude`) bypasses the heuristic. |
| **External venv** | `.venvs/geva_venv` (created 2026-09-03, Python 3.12.13, `uv venv --python 3.12 --seed`) |
| **Install status** | **[CPU-ONLY STACK LIVE]** — `mmcv-full 1.7.2` (CPU-only ops path, `compiling_cuda_version='not available'`) + `mmdet 2.28.2` + the upstream `djghosh13/geneval` scripts import cleanly in `.venvs/geva_venv`. The wrapper can shell out to `evaluate_images.py`. Note: this is **CPU inference** — correct but slow. For paper-fidelity numbers, build against a CUDA 12.x host. |
| **Build recipe** | `bash .venvs/geva_venv/logs/install_geva_v3_cpu_only.sh` (sibling to the v2 script; the v2 build was blocked at the CUDA step). The v3 patch (`mmcv_setup_patch.py`) is idempotent and survives re-runs. The compiled wheel is archived at `.venvs/geva_venv/logs/mmcv_full-1.7.2-cp312-cp312-linux_x86_64-cpu_only.whl` (~28 MB) — if someone wipes `.venvs/geva_venv`, `pip install --no-deps --no-build-isolation <that-wheel>` reinstalls the built `_ext.cpython-312-x86_64-linux-gnu.so` (74 MB) without re-running the source build. |
| **Why the GPU build is still blocked** | The v2 CUDA build dies with `RuntimeError: The detected CUDA version (13.2) mismatches the version that was used to compile PyTorch (12.8)`. The v3 CPU build sidesteps this by overriding `torch.cuda.is_available() -> False` inside `setup.py` so mmcv 1.7.2 takes the `Compiling mmcv._ext only with CPU` branch (which uses `CppExtension`, not `CUDAExtension`, and never hits `_check_cuda_version`). The prebuilt-mmseg wheel that downstream mmdet needs is also missing on PyTorch 2.7+cu128 + Python 3.12 for this host's CUDA 13.2 toolkit, so a *GPU* build would need a CUDA 12.x host or a future `+cu132` torch wheel + matching mmcv prebuilt wheel. Demoting the host CUDA toolkit would break the other tenants (`docs/environments.md`). |

When the wrapper is invoked today (--geneval-binary set, .venvs/geva_venv
not fully provisioned) it returns:

```json
{
  "metric": "geneval",
  "value": null,
  "marker": "not_installed",
  "missing": ["--geneval-binary=...", "--geneval-repo=...", "--geneval-detector-path=..."],
  "install_hint": "Provision a separate geva_venv ... §B to install mmcv-full 1.7.2 + mmdet 2.28.2 + clone github.com/djghosh13/geneval + download the Mask2Former Swin-S weights (~1 GB).",
  "sub_scores": {"single_object": null, "two_object": null, "counting": null, "colors": null, "position": null, "color_attr": null}
}
```

When the wrapper is invoked **without** `--geneval-binary` it returns
the legacy byte-stable stub:

```json
{
  "value": null,
  "marker": "external",
  "note": "GenEval object-composition evaluation requires an mmdet/Mask2Former harness; see docs/r17-survey/image-eval-plan.md",
  "sub_scores": {"single_object": null, "two_object": null, "counting": null, "colors": null, "position": null, "color_attr": null}
}
```

### §2.2 DPG-Bench (HiDream-I1 / Lumina-Image 2.0 paper Table 3)

| | |
|---|---|
| **Upstream** | `github.com/MLL-Hub/DPG-Bench` (paper §A.2 judge prompt list + ~10K prompts CSV) |
| **Upstream CLI** | `python eval_dpg.py --image_dir <samples> --prompt_file <prompts.csv> --judge_model <hf_repo>` |
| **Judge model decision** | BLOCKED — MiniCPM-V 2.6 self-host vs GPT-4V paid endpoint. See `docs/r17-survey/dpg-bench-judge-decision.md` (decision deferred to operator). |
| **Wrapper function** | not yet implemented — currently the byte-stable `{"value": null, "marker": "external"}` stub. |
| **External venv** | `.venvs/dpg_venv` (not yet created; install attempts paused pending the judge-model decision). |
| **Install status** | [STUB] — wrapper not built; metric block is the external placeholder. |
| **Operator next steps** | resolve `docs/r17-survey/dpg-bench-judge-decision.md` Q1 first. Once decided, create `.venvs/dpg_venv`, install `transformers accelerate` + the judge model weights, and add `run_dpg_bench_metric()` mirroring `run_geneval_metric()`. |

### §2.3 HPSv2.1 (HiDream-I1 paper Table 4)

| | |
|---|---|
| **Upstream** | `github.com/tgxs002/HPSv2` (Apache-2.0; PyPI `hpsv2==1.2.0` by same author). Note: the earlier docs cited the `thomashtian/HPSv2` HPSv2x fork — that fork is not on PyPI; the canonical PyPI package is `hpsv2` from `tgxs002` and it supports both v2.0 and v2.1 checkpoints via `hpsv2.score(..., hps_version=...)`. |
| **Upstream API** | `hpsv2.score(image_path, prompt, hps_version="v2.1") -> list[float]` (CLIP-H-14 backbone + custom HPSv2 head). The v2.1 checkpoint auto-downloads from the `xswu/HPSv2` HF repo on first call (~3.3 GB). |
| **Wrapper function** | `tools/run_image_eval.py::run_hpsv2_metric` (subprocess wrapper) + `tools/run_image_eval.py::_resolve_hpsv2_metric` (dispatch) + `tools/run_image_eval.py::_hpsv2_external_legacy_stub` (byte-stable stub) + `tools/run_image_eval.py::_hpsv2_not_installed_marker` (operator-friendly fallback). |
| **External venv** | `.venvs/hpsv2_venv` (created 2026-09-03, Python 3.12.13, `uv venv --python 3.12 --seed`). |
| **Driver script** | `.venvs/hpsv2_venv/scripts/hpsv2_score.py` (shipped in the runner checkout; auto-fetches the missing `bpe_simple_vocab_16e6.txt.gz` from `mlfoundations/open_clip` on first run — known packaging bug in `hpsv2==1.2.0`). |
| **Wrapper status** | **[WIRED]** — invoked when `--hpsv2-binary` is set. Calls the driver as a subprocess with a 1800 s timeout; the driver sorts samples lexicographically, aligns them with the JSONL prompts, calls `hpsv2.score(...)` per (image, prompt) pair, aggregates mean + std + per-image scores into a JSON block, and the wrapper reads that block back. The JSON output is structured under `metrics.hpsv2` with the keys `value` (mean), `std` (sample stddev), `n_pairs`, `hps_version`, `per_image` (capped at 256), `elapsed_seconds`, and `marker` (one of `ok` / `not_installed` / `external_error` / `external`). |
| **Install status** | [WIRED] — venv created, `hpsv2==1.2.0` installed, driver script present. BPE vocab auto-fetched (one-time, 1.3 MB). HPSv2 v2.1 checkpoint (3.3 GB) downloads from HF on the first real eval run. |
| **Known quirks** | (a) `hpsv2==1.2.0` is missing `bpe_simple_vocab_16e6.txt.gz` (handled by the driver); (b) the upstream `hpsv2.score` re-loads the checkpoint on the FIRST call only, so the first image of a 5K batch is slow; (c) `v2.0` and `v2.1` scores are NOT directly comparable per the upstream README — operators must pick one and stick with it. |
| **Operator next steps** | Run the operator checklist in §7 with `--hpsv2-binary .venvs/hpsv2_venv/bin/python --hpsv2-version v2.1` to produce the first HiDream HPSv2.1 paper-comparable number. |

### §2.4 T2I-CompBench (Lumina-Image 2.0 paper Table 1)

| | |
|---|---|
| **Upstream** | `github.com/m-Hossam/T2I-CompBench` (paper, BLIP-VQA judge) |
| **Upstream CLI** | `python evaluation/evaluate_blip.py --image_dir <samples> --out_dir <results>` then aggregate `python evaluation/aggregate_score.py` |
| **Wrapper function** | `_t2i_compbench_external_stub()` — emits the byte-stable `{"value": null, "marker": "external", "sub_scores": {"color": null, "shape": null, "texture": null}, ...}` block. |
| **External venv** | `.venvs/t2icompbench_venv` (not yet created). |
| **Install status** | [STUB] — wrapper stub already reserves the `sub_scores` block so downstream consumers can key off `metrics.t2i_compbench.sub_scores.color` etc. before the real wrapper lands. |
| **Operator next steps** | create `.venvs/t2icompbench_venv`, `pip install t2i-compbench-tool clip-benchmark`, add `run_t2i_compbench_metric()` mirroring the GenEval pattern. |

### §2.5 ImageReward (Lumina-Image 2.0 paper Table 3, optional)

| | |
|---|---|
| **Upstream** | `github.com/THUDM/ImageReward` (THUDM, Apache-2.0) |
| **Upstream CLI** | `python .venvs/image_reward_venv/scripts/image_reward_score.py --samples-dir <flat_dir> --prompts-jsonl <prompts.jsonl> --output-json <out.json> [--model ImageReward-v1.0]` |
| **Backbone** | BLIP visual encoder (ViT-large, 224px) + MLP scoring head + AestheticScore module (uses OpenAI CLIP) — all open-source, all bundled in `image-reward==1.5` PyPI package |
| **Wrapper function** | `tools/run_image_eval.py::run_image_reward_metric` (subprocess wrapper). Stages a flat samples dir + JSONL prompts, shells out to the driver with an 1800 s timeout, parses the driver's JSON output. Graceful NaN / `not_installed` / `external_error` fallbacks mirroring the GenEval + HPSv2 patterns. |
| **External venv** | `.venvs/image_reward_venv` (created 2026-09-03, Python 3.12.13, `uv venv --python 3.12 --seed`) |
| **Install status** | [WIRED] — wrapper code lands in `tools/run_image_eval.py::run_image_reward_metric`. CLI surface: `--image-reward-binary`, `--image-reward-driver`, `--image-reward-prompts`, `--image-reward-model`, `--image-reward-timeout`, `--image-reward-gpu-id`. Driver script lands at `.venvs/image_reward_venv/scripts/image_reward_score.py` (mirrors the HPSv2 driver shape). Legacy stub (`{"metric": "image_reward", "value": null, "marker": "external"}`) is emitted by default so downstream consumers see a stable JSON contract before the venv is provisioned. |
| **Driver install** | `uv pip install --python .venvs/image_reward_venv/bin/python image-reward && uv pip install --python .venvs/image_reward_venv/bin/python 'clip @ git+https://github.com/openai/CLIP.git' && uv pip install --python .venvs/image_reward_venv/bin/python 'transformers>=4.27.4,<4.40' 'diffusers>=0.16.0,<0.30' 'accelerate>=0.16.0,<0.30'`. Three pins are required because (a) `setup.py`'s `dependency_links` for OpenAI CLIP is a pre-PEP-517 legacy mechanism that uv ignores, (b) the bundled BLIP vendored BERT imports `apply_chunking_to_forward` (removed in transformers ≥ 5.x), (c) diffusers ≥ 0.30 needs newer transformers for Dinov2 compat. See `.venvs/image_reward_venv/logs/install_outcome.md` for the full diagnosis. |
| **Operator next steps** | (a) one-time model pre-download: `HF_HUB_OFFLINE=0 .venvs/image_reward_venv/bin/python -c "import ImageReward as RM; RM.load('ImageReward-v1.0')"` (~3.6 GB from `huggingface.co/THUDM/ImageReward`); (b) run the wrapper with `--image-reward-binary .venvs/image_reward_venv/bin/python`. If `HF_HUB_OFFLINE=1` is set in the calling shell and the model is not pre-cached, the wrapper emits `{"marker": "external_error", "error": "LocalEntryNotFoundError: ... offline mode is enabled ..."}` (graceful, never raises). |

## §3. Summary table (operator view)

| Metric | Wrapper | Today | Paper | Cost to wire |
|---|---|---|---|---|
| FID | yes | [WIRED] | HiDream does not lead, Lumina yes | done |
| CLIPScore | yes | [WIRED] | yes | done |
| GenEval | yes (subprocess) | [WIRED — CPU-only build live; GPU build still env-blocked] | HiDream 0.83, Lumina 0.73 | CPU build: 30 min on this host (already done — `bash .venvs/geva_venv/logs/install_geva_v3_cpu_only.sh`); GPU build: 1-2 h on a CUDA 12.x host |
| DPG-Bench | stub | [STUB] — judge model decision pending | HiDream 86.6, Lumina 87.2 | depends on MiniCPM-V vs GPT-4V decision |
| HPSv2.1 | yes (subprocess) | [WIRED] | HiDream 32.8 (Style + Anime) | done — driver + wrapper shipped in this pass |
| T2I-CompBench | stub | [STUB] | Lumina color 0.8211 | ~2-4 h glue + venv |
| ImageReward | yes (subprocess) | [WIRED] | Lumina table 3 (optional HiDream) | done — install recipe at `.venvs/image_reward_venv/logs/install_outcome.md` |

## §4. Where to obtain reference FID statistics

| Dataset | URL | Local path |
|---|---|---|
| MJHQ-30K (Lumina canonical) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/mjhq30k_inception_stats.npz` (~33 MB) | `data/fid_stats/mjhq30k_inception_stats.npz` (already present, mirrored at `data/lumina_image_2_0/mjhq30k_inception_stats.npz`) |
| COCO-30K (HiDream fallback) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/coco_30k_inception_stats.npz` (~30 MB) | `data/fid_stats/coco_30k_inception_stats.npz` (NOT YET DOWNLOADED — repair §1.4 of baseline-deviation-review.md) |
| GenEval partition | operator-computed via `cleanfid.make_custom_stats('geneval', <refs>)` | n/a |
| DPG-Bench partition | operator-computed | n/a |

## §5. Where to obtain GenEval prompts + detector weights

GenEval canonical prompt file: `https://github.com/djghosh13/geneval/blob/main/prompts/evaluation_metadata.jsonl` (553 prompts, JSONL with `tag` / `include` / `exclude` / `prompt` fields).

Mask2Former detector weights: download via
`.venvs/geva_venv/repo/evaluation/download_models.sh <out_dir>` (the
script pulls `mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth` from
the official mmdetection model zoo, ~1 GB).

When the operator has both, set:

```bash
--geneval-binary      .venvs/geva_venv/bin/python
--geneval-repo        .venvs/geva_venv/repo
--geneval-prompts     data/geneval_evaluation_metadata.jsonl
--geneval-detector-path data/geva_models/mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth
--geneval-gpu-id      0
--geneval-timeout     600
```

## §6. GPU-allocation contract (Phase B prep)

- **GPU 0** (RTX PRO 6000, 98 GB) → InceptionV3 + CLIP-vit-base-patch32 + GenEval detector + DPG-Bench judge + HiDream-I1-Dev (24 GB). Leaves ~73 GB of headroom.
- **GPU 1** (RTX 5090, 32 GB) → metric stage alone OR an additional HiDream instance.
- **Never** load HiDream-I1-Full (17 B, 32 GB) on GPU 1 alongside metric stage — OOM. Full variant lives on GPU 0 only.

GenEval runs the Mask2Former Swin-S detector (~1024-d backbone, ~250 MB) and the CLIP ViT-L/14 openai backbone (~900MB) on the same GPU as the caller. The wrapper passes through `CUDA_VISIBLE_DEVICES` from `--geneval-gpu-id`.

## §7. Day-1 operator checklist

```bash
# 1. Install Tier-2 venv (only GenEval attempted today; DPG/HPSv2 follow the same shape).
uv venv --python 3.12 .venvs/geva_venv --seed
bash .venvs/geva_venv/logs/install_geva_v3_cpu_only.sh        # CPU-only build (works today, see logs/install_outcome.md for v2/GPU diagnosis)

# 2. Download reference stats for the dataset partition you evaluate against.
mkdir -p data/fid_stats
curl -fL --retry 3 \
  https://github.com/GaParmar/clean-fid/releases/download/cleanfid/coco_30k_inception_stats.npz \
  -o data/fid_stats/coco_30k_inception_stats.npz

# 3. Run the runner with the GenEval subprocess wrapper enabled.
python tools/run_image_eval.py \
  --samples-dir data/lumina_image_2_0/samples \
  --reference-stats data/fid_stats/mjhq30k_inception_stats.npz \
  --prompts-jsonl data/lumina_image_2_0/prompts.jsonl \
  --output data/lumina_image_2_0/eval_report.json \
  --device cuda:0 --image-target-size 299 \
  --geneval-binary .venvs/geva_venv/bin/python \
  --geneval-repo   .venvs/geva_venv/repo \
  --geneval-prompts data/geneval_evaluation_metadata.jsonl \
  --geneval-detector-path data/geva_models/mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth \
  --geneval-gpu-id 0

# 4. Inspect metrics.geneval:
python -c "import json; r=json.load(open('data/lumina_image_2_0/eval_report.json')); print(json.dumps(r['metrics']['geneval'], indent=2))"
```

### §7.1 HPSv2.1 checklist (HiDream-I1 paper Table 4)

```bash
# 1. Install the HPSv2 venv (sibling of geva_venv; no CUDA build step).
uv venv --python 3.12 .venvs/hpsv2_venv --seed
uv pip install --python .venvs/hpsv2_venv/bin/python hpsv2

# 2. The driver script is already shipped under
#    .venvs/hpsv2_venv/scripts/hpsv2_score.py — no separate clone step.

# 3. First run auto-downloads:
#    - HPSv2 v2.1 checkpoint from the xswu/HPSv2 HF repo (~3.3 GB)
#    - The bpe_simple_vocab_16e6.txt.gz from mlfoundations/open_clip
#      (~1.3 MB; one-time, known packaging bug in hpsv2==1.2.0)

# 4. Run the runner with the HPSv2 subprocess wrapper enabled.
python tools/run_image_eval.py \
  --samples-dir data/hidream_i1/samples \
  --prompts-jsonl data/hidream_i1/prompts.jsonl \
  --output data/hidream_i1/eval_report.json \
  --hpsv2-binary .venvs/hpsv2_venv/bin/python \
  --hpsv2-prompts data/hidream_i1/prompts.jsonl \
  --hpsv2-version v2.1 \
  --hpsv2-gpu-id 0

# 5. Inspect metrics.hpsv2:
python -c "import json; r=json.load(open('data/hidream_i1/eval_report.json')); print(json.dumps(r['metrics']['hpsv2'], indent=2))"
```

### §7.2 ImageReward checklist (Lumina-Image 2.0 paper Table 3, HiDream optional)

```bash
# 1. Install the ImageReward venv (full recipe at .venvs/image_reward_venv/logs/install_outcome.md).
uv venv --python 3.12 .venvs/image_reward_venv --seed
uv pip install --python .venvs/image_reward_venv/bin/python image-reward
# The setup.py ``dependency_links`` for OpenAI CLIP is a pre-PEP-517 legacy
# mechanism that uv ignores; install it explicitly:
uv pip install --python .venvs/image_reward_venv/bin/python \
  "clip @ git+https://github.com/openai/CLIP.git"
# Pin transformers / diffusers / accelerate to ranges compatible with the
# 2023-era vendored BLIP / AestheticScore modules (the BLIP vendored BERT
# imports ``apply_chunking_to_forward`` which was removed in transformers 5.x):
uv pip install --python .venvs/image_reward_venv/bin/python \
  "transformers>=4.27.4,<4.40" \
  "diffusers>=0.16.0,<0.30" \
  "accelerate>=0.16.0,<0.30"

# 2. The driver script is already shipped under
#    .venvs/image_reward_venv/scripts/image_reward_score.py — no separate
#    clone step.

# 3. One-time model pre-download (3.6 GB from huggingface.co/THUDM/ImageReward):
HF_HUB_OFFLINE=0 .venvs/image_reward_venv/bin/python -c \
  "import ImageReward as RM; m = RM.load('ImageReward-v1.0'); print('loaded')"

# 4. Run the runner with the ImageReward subprocess wrapper enabled.
python tools/run_image_eval.py \
  --samples-dir data/lumina_image_2_0/samples \
  --prompts-jsonl data/lumina_image_2_0/prompts.jsonl \
  --output data/lumina_image_2_0/eval_report.json \
  --image-reward-binary .venvs/image_reward_venv/bin/python \
  --image-reward-prompts data/lumina_image_2_0/prompts.jsonl \
  --image-reward-model ImageReward-v1.0 \
  --image-reward-gpu-id 0

# 5. Inspect metrics.image_reward:
python -c "import json; r=json.load(open('data/lumina_image_2_0/eval_report.json')); print(json.dumps(r['metrics']['image_reward'], indent=2))"
```

## §8. References

- `tools/run_image_eval.py` — runner source. `_resolve_geneval_metric` (Tier-2 dispatch), `run_geneval_metric` (subprocess wrapper), `_stage_geneval_inputs` + `_infer_geneval_tag` (SOTA → upstream layout bridge), `_parse_geneval_summary` (stdout → JSON). Same shape repeated for HPSv2 (`_resolve_hpsv2_metric` / `run_hpsv2_metric`) and ImageReward (`_resolve_image_reward_metric` / `run_image_reward_metric`).
- `.venvs/geva_venv/logs/install_outcome.md` — install-attempt diagnosis for GenEval (v2/GPU build, blocked at `mmcv-full` source build by `RuntimeError: The detected CUDA version (13.2) mismatches the version that was used to compile PyTorch (12.8)`).
- `.venvs/geva_venv/logs/install_geva_v3_cpu_only.sh` — CPU-only build recipe for this host (works today, ~30 min from a clean `.venvs/geva_venv`).
- `.venvs/geva_venv/logs/mmcv_setup_patch.py` — idempotent `setup.py` patch that monkey-patches `torch.cuda.is_available() -> False` so mmcv 1.7.2 takes the `Compiling mmcv._ext only with CPU` branch (sidesteps `_check_cuda_version`).
- `.venvs/geva_venv/logs/mmcv_full-1.7.2-cp312-cp312-linux_x86_64-cpu_only.whl` — prebuilt CPU-only wheel (reinstall via `pip install --no-deps --no-build-isolation <this>`; no source re-build needed if the venv is wiped).
- `.venvs/image_reward_venv/logs/install_outcome.md` — install diagnosis for ImageReward (three pins: `clip @ git+openai/CLIP`, `transformers<4.40`, `diffusers<0.30`).
- `docs/r17-survey/baseline-deviation-review.md` §1.5 + §6.2 — the source repair plan that this checklist operationalises.
- `docs/r17-survey/image-eval-plan.md` — Phase B prep plan (Tier-1 + Tier-2 stack inventory).
- `docs/r17-survey/dpg-bench-judge-decision.md` — DPG-Bench judge model decision (BLOCKED).
- `docs/environments.md` — one-venv-per-model layout + the CUDA 13.2 toolkit constraint that explains why mmcv-full cannot build on this host.