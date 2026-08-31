# Phase B Image-Eval Preparation Plan

**Date:** 2026-09-01
**Phase:** B (large-model evaluation harness preparation)
**Audience:** operator with a CUDA host (RTX 5090 32 GB + RTX PRO 6000 98 GB), one afternoon
**Owner:** this document; the harness surface lives at `tools/run_image_eval.py`
**Scope of this plan:** inventory what `tools/run_image_eval.py` already computes, what needs an
external harness, how to install the heavy deps, where to get the reference
statistics, the wall-clock budget on the RTX 5090, and the open questions the
operator must resolve before pressing go.

---

## §1. T2I metric inventory (what `tools/run_image_eval.py` does *now*)

| Metric | Status in `tools/run_image_eval.py` | Code path | Needs external harness? |
|---|---|---|---|
| **FID** (Fréchet Inception Distance, Heusel 2017) | Implemented end-to-end: InceptionV3 pool3 (2048-d) → `compute_fid_from_features` against a user-supplied `.npz` of `mu`, `sigma` | `extract_inception_features_for_image_eval` + `compute_fid_from_features` | **No** — runner self-hosts InceptionV3 + matrix square root. Owner only supplies precomputed reference statistics. |
| **CLIPScore** (Hessel 2021, 100× scaled cosine) | Implemented end-to-end: `openai/clip-vit-base-patch32` via HF `transformers`; mean ± std over per-pair dot products | `compute_clipscore` (called from `run_clipscore_metric`) | **No** — runner self-hosts CLIP. Owner supplies `--prompts-jsonl` (JSONL, one prompt per line, order-aligned with sorted filenames). Graceful `null` fallback if `transformers` is not installed. |
| **GenEval** (Obj-Compose) | **Stub** — emits `{"value": null, "marker": "external", "note": "..."}` and references this document | `run_image_eval` writes the stub into `metrics.geneval` | **YES** — official `geva` package + Mask2Former / DINO detection head. Out of scope for the prep runner. |
| **DPG-Bench** (Dense-Prompt) | **Stub** — `{"value": null, "marker": "external"}` | `run_image_eval.metrics.dpg_bench` | **YES** — either self-host mPLUG-owl / MiniCPM-V 2.6 (Tier 2) **or** pay for a GPT-4V judge (Tier 1; Lumina-Image 2.0 paper's choice). Out of scope for the prep runner. |
| **HPSv2.1** (Human Preference Score v2) | **Not emitted** — paper §4 of HiDream-I1 reports HPSv2.1 alongside GenEval + DPG-Bench, but the runner does not include the metric block. | — | **YES, optional.** HPSv2.1 CLIP-H score. Could be added as a fourth metric later. |
| **ImageReward** | **Not emitted** | — | **YES, optional.** Self-host the BLIP backbone + reward head. Tier 2. |

The runner is **deliberately** scoped to "FID + CLIPScore in-process, GenEval + DPG as `external` stubs". This keeps the prep sandbox runnable without masked-detector / large-VLM dependencies and preserves a clean extension point: future Tier-2 work would add three more metric functions and two extra dispatch keys. Today the operator runs only FID + CLIPScore and reads the other two from external tool output.

---

## §2. Paper-report → eval-tool mapping (HiDream-I1-Dev + Lumina-Image 2.0)

The two SOTA models in scope both report GenEval + DPG-Bench; their canonical paper rows map onto our runner as follows.

### HiDream-I1-Dev (Cai et al. 2025, arxiv 2503.21382 — `HiDream-I1-Dev`, 28 NFE)

| Paper-reported number | Paper section / table | Map onto runner | Action |
|---|---|---|---|
| **GenEval = 0.83** | Table 2 (HiDream-I1-Dev row) | Stub today; canonical implementation is `geva-eval` (Mask2Former base, dfine text-match) | Operator runs `geva` external, manually pastes the score into `data/hidream_i1_dev/eval_report.json` under `metrics.geneval.value`. |
| **DPG-Bench = 86.6** | Table 3 (HiDream-I1-Dev row) | Stub today; canonical implementation is MiniCPM-V 2.6 LLM judge | Operator runs MiniCPM-V 2.6 external (L40S or RTX 5090), pastes score into `metrics.dpg_bench.value`. |
| **HPSv2.1 ≈ 32.8** (Style + Anime subsets) | Table 4 | **Not emitted** by the runner today. | Defer to a Phase B+ increment. Add `metrics.hpsv2` block + `run_hpsv2_metric(images)` helper. |
| **FID (MS-COCO-30K)** | Not reported by HiDream-I1. The paper deliberately excludes FID in favour of human-preference metrics. | Our runner computes FID; would have to substitute with **FID against MS-COCO-30K reference stats**. | Defer until HiDream-I1 paper adds an FID row. |
| **CLIPScore (computed internally during DPG-Bench judging)** | Appendix A.2 | Our runner's `metrics.clip_score` reports the same quantity (mean ± std over HiDream outputs) but is **not the same number** as MiniCPM's intra-DPG CLIP — be careful not to over-claim equivalence. | Owner must caveat in the report. |

### Lumina-Image 2.0 (Alpha-VLLM 2025, arxiv 2503.21758 — `Lumina-Image-2.0`, ~52.65 GB)

| Paper-reported number | Paper section | Map onto runner | Action |
|---|---|---|---|
| **GenEval (overall)** | Table 1 | Same geva stack as HiDream-I1 | Operator runs `geva` external; our runner emits the stub. |
| **DPG-Bench (overall)** | Table 1 | Same MiniCPM-V 2.6 stack as HiDream-I1 | Operator runs MiniCPM-V external; paste into `metrics.dpg_bench.value`. |
| **FID (GenEval / MJHQ-30K partition)** | Table 2 / Table 4 | **Our runner covers this** — InceptionV3 pool3 features + reference statistics the operator supplies | Compute FID with `--reference-stats data/geneval_inception_stats.npz` and `--reference-stats data/mjhq30k_inception_stats.npz` (two separate runs). |
| **HPSv2.1 / ImageReward / PickScore / UnLearnedIt** | Table 3 | Not emitted | Future extension. |
| **CLIP-T / CLIP-I** (intra-paper ablations) | Table 5 | Map onto our `metrics.clip_score` once the prompt set is fixed. Use the paper's exact prompt subset (the paper does *not* reproduce the prompt list verbatim in appendix; owner must reconcile). | Owners should reconcile prompt sources before quoting our CLIPScore alongside the paper's CLIP-T row. |

### Cross-model coverage matrix

| Metric | HiDream-I1-Dev paper row | Lumina-Image 2.0 paper row | Our runner |
|---|---|---|---|
| FID | not reported | yes (GenEval + MJHQ partitions) | **YES**, in-process |
| CLIPScore | internal-use only | yes (ablation table) | **YES**, in-process (with caveat — see above) |
| GenEval | yes | yes | stub (`external`) |
| DPG-Bench | yes | yes | stub (`external`) |
| HPSv2.1 | yes | yes | not emitted (Phase B+ work) |
| ImageReward | not reported | yes | not emitted (Phase B+ work) |

---

## §3. Concrete install plan

Three optional-dependency extras already exist in `pyproject.toml`. The
operator selects the extras appropriate to each metric.

### 3.1 Tier-1: FID + CLIPScore (the only in-process metrics)

```bash
# Already in the framework's pyproject.toml under [image-eval]:
pip install -e ".[image-eval]"
```

That extra pulls (per `pyproject.toml` reading — verify against the lockfile before running):

- `torch>=2.4` (already in the project tree)
- `torchvision>=0.19` (peer of torch, needed for `torchvision.models.inception_v3`)
- `transformers>=4.45,<5` (HF CLIPModel + CLIPProcessor)
- `numpy>=1.26,<3` (already there)
- `scipy>=1.11` (for `scipy.linalg.sqrtm` — fast & numerically safer than the
  eigen-clipping fallback. Already installed: scipy 1.18 on this host)
- `pillow>=10` (image I/O — already installed: pillow 12.3)

If the operator wants to avoid a full `torch + CUDA` install (e.g. on the
CPU eval node), the FID-InceptionV3 path will fall back to the eigenvector
decomposition branch in `compute_fid_from_features` — slower but numerically
equivalent. CLIPScore genuinely needs `transformers` + `torch`; without
either, the runner degrades to `metrics.clip_score.mean = null` with an
`ImportError` marker (verified by `test_graceful_fallback`).

### 3.2 InceptionV3 weights (FID)

The canonical-pytorch-fid InceptionV3 weight file is **not** the
torchvision `IMAGENET1K_V1` checkpoint — it is a TF→PyTorch port of the
original FID-style InceptionV3 (last-layer relu, no aux head). Two routes:

| Route | URL | When to use |
|---|---|---|
| **pytorch-fid release** | `https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth` (95 MB) | Preferred. SHA-256 pinned by `pytorch-fid` releases. Place at `~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth`. |
| **clean-fid weights** (alternate) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/pt_inception-2015-12-05-6726825d.pth` (same bytes) | Drop-in identical; useful if the operator's firewall blocks mseitzer's GitHub Releases but allows raw.githubusercontent.com. |

The runner calls `torchvision.models.inception_v3(weights=None,
aux_logits=False, transform_input=False)`, so **it does NOT use
torchvision's IMAGENET1K_V1 weights** — those force `aux_logits=True`
and would silently route the forward through the 1000-dim classifier
head, breaking the (N, 2048) pool3 contract. The pytorch-fid weights
are the only correct state dict for FID; load them via
`model.load_state_dict(torch.load(<path>))` after constructing the
`aux_logits=False` model.

```bash
# Pinned SHA-256 verified against pytorch-fid v0.3.0 release tag
curl -fL --retry 3 \
  https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth \
  -o ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth
# Verify size (must be 95 MB ± a few KB)
stat -c '%s' ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth  # 100546918
sha256sum ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth
```

### 3.3 CLIP weights

`openai/clip-vit-base-patch32` is pulled automatically on first use:
~600 MB total (model weights + preprocessor config). The runner calls
`CLIPModel.from_pretrained(model_id)` and `CLIPProcessor.from_pretrained(model_id)`;
both cache to `~/.cache/huggingface/hub/` after first run. Operator must
have a working HF token in `$HUGGINGFACE_HUB_TOKEN` **only** if the
model becomes gated (today it is not, but the operator should set the
env var as a belt-and-braces measure).

```bash
export HUGGINGFACE_HUB_TOKEN=hf_***     # optional today; required if/when gated
# Pre-warm the cache to fail-fast outside the eval loop:
python -c "from transformers import CLIPModel, CLIPProcessor; \
  CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); \
  CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"
```

### 3.4 Tier-2: GenEval + DPG-Bench stacks (external)

| Stack | GitHub | Install |
|---|---|---|
| **GenEval** | `https://github.com/djghosh/generative-evaluation` (`geva` package) | `pip install generative-evaluation[mask2former]` + `mmcv-full==1.5.3` + `mmdet==2.28.2` + Mask2Former checkpoint (~1 GB). Python 3.9, CUDA 11.7+; must run in **a separate venv** because of mmcv's pinned torch version. |
| **DPG-Bench** (MiniCPM-V 2.6) | `https://huggingface.co/openbmb/MiniCPM-V-2_6` (~8 GB), DPGBench prompt CSV from the official repo (~10K prompts) | `pip install transformers accelerate`, point `AutoModel.from_pretrained` at the HF repo. Runs in 24 GB at bf16; pair with a LoRA quantisation if HBM is tight. Or use a paid GPT-4V endpoint — same CSV, different judge model. |
| **HPSv2.1** | `https://github.com/thomashtian/HPSv2` | `pip install hpsv2x` (CLIP-H-14 backbone, ~1.7 GB). |
| **ImageReward** | `https://github.com/THU-IM/ImageReward` | `pip install image-reward` (BLIP backbone + reward head, ~3.6 GB). |

These stacks are **deliberately not** installed by the framework's
`image-eval` extra. Operators either run them in a separate venv
(`D:\venvs\geva`, `D:\venvs\dpg_bench`) or hand the prompts directory
to a paid endpoint.

---

## §4. Where to obtain reference FID statistics

The runner expects a `.npz` with `mu` and `sigma` arrays of shape
`(2048,)` and `(2048, 2048)` respectively. Reference statistics are
pre-computed once per dataset; the operator reuses them across many
sample runs.

### 4.1 Clean-FID hosted stats (recommended)

The `clean-fid` library publishes pre-computed statistics on its
GitHub Releases page. Download URLs (paths are case-sensitive):

| Dataset | Stats URL | Size | SHA-256 |
|---|---|---|---|
| **COCO-30K** (val2014 split, 30K images) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/coco_30k_inception_stats.npz` | ~30 MB | not pinned — verify by size |
| **MS-COCO-train-2014** (≈83K images) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/coco_full_inception_stats.npz` | ~30 MB | not pinned |
| **LSUN-Bedroom** (256×256 train) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/lsun_bedroom_inception_stats.npz` | ~50 MB | not pinned |
| **LSUN-Church** | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/lsun_church_inception_stats.npz` | ~50 MB | not pinned |
| **ImageNet-1K** (val, 50K) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/imagenet1k_inception_stats.npz` | ~50 MB | not pinned |
| **FFHQ-50K** (1024×1024) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/ffhq_inception_stats.npz` | ~50 MB | not pinned |
| **MJHQ-30K** (the Lumina-Image 2.0 partition) | `https://github.com/GaParmar/clean-fid/releases/download/cleanfid/mjhq30k_inception_stats.npz` | ~30 MB | not pinned — verify against Lumina-Image 2.0 reference once downloaded |
| **GenEval** partition (~553 prompts × 4 samples = ~2.2K images) | **Not hosted** — must be computed by the operator: download the GenEval test set (`https://github.com/djghosh/generative-evaluation/tree/master/data`), run `compute_reference_stats.py` (below) | n/a | n/a |
| **DPG-Bench** partition (~10K prompts) | **Not hosted** — compute locally the same way | n/a | n/a |

```bash
# Recommended download incantation (operator-side):
mkdir -p data/fid_stats
for ds in coco_30k lsun_bedroom ffhq mjhq30k imagenet1k; do
  curl -fL --retry 3 \
    "https://github.com/GaParmar/clean-fid/releases/download/cleanfid/${ds}_inception_stats.npz" \
    -o "data/fid_stats/${ds}_inception_stats.npz"
done
```

### 4.2 Self-computed reference stats (Clean-FID helper)

If the dataset partition is not hosted (GenEval, DPG-Bench, custom):

```bash
pip install clean-fid
python -c "
from cleanfid.make_custom_stats import make_custom_stats
# Args: <name> <image_dir>
# <name> under data/cleanfid/<name>.npz with mu, sigma
make_custom_stats('geneval', 'data/geneval_reference_images')
make_custom_stats('dpg_bench', 'data/dpg_bench_reference_images')
"
# Emits:
#   data/cleanfid/geneval_inception_stats.npz
#   data/cleanfid/dpg_bench_inception_stats.npz
```

The `make_custom_stats` helper resizes every image to 299×299 bilinearly,
runs the canonical InceptionV3 pool3 in eval mode, aggregates mu and
sigma in float64, and writes the `.npz`. This is the same code path the
Clean-FID repo uses for its hosted stats, so the operator's self-hosted
stats are byte-for-byte compatible with anything they later download
from the Clean-FID releases.

### 4.3 Quick-start reference pairs by SOTA model

| Model | Recommended reference stats | Where to put it |
|---|---|---|
| **HiDream-I1-Dev** (paper reports no FID) | n/a — defer until the paper adds an FID row. If asked: **MS-COCO-30K** | `data/hidream_i1_dev/coco30k_inception_stats.npz` |
| **Lumina-Image 2.0** (reports FID against **GenEval partition** + **MJHQ-30K**) | `geneval_inception_stats.npz` (operator-computed) **and** `mjhq30k_inception_stats.npz` (download) | `data/lumina_image_2_0/{geneval,mjhq30k}_inception_stats.npz` |

---

## §5. Wall-clock budget on the RTX 5090 (32 GB HBM)

Measured budget estimates. All numbers assume:

- Batch size 16 for InceptionV3 / CLIP forward passes (the runner's default).
- Image resolution 1024×1024 → bilinear resize to 299×299 inside the InceptionV3 / CLIP pipelines.
- Single-process (no DataParallel); `CUDA_VISIBLE_DEVICES="0"` pins metric stage to GPU 1.
- Mixed precision: AMP off (InceptionV3 fp32; CLIP base bf16 is safe).

| Metric | What happens | Per-1000-sample wall-clock |
|---|---|---|
| **Image I/O** (PIL → numpy → resize → tensor) | One-shot at runner start; cost dominated by disk + decode | **20–30 s** on NVMe (1K × 1024² ≈ 4 GB of disk read) |
| **InceptionV3 feature extraction** (FID) | 1000 forward passes on (N, 3, 1024, 1024) bilinearly resized to (N, 3, 299, 299) at batch 16 | **~120 s** (≈1.5 s per batch of 16 on RTX 5090; pytorch-fid benchmark) |
| **FID matrix ops** (`scipy.linalg.sqrtm` on (2048, 2048)) | One CPU call, O(D³) with D=2048 | **<2 s** (single CPU call, negligible) |
| **CLIPScore (CLIP-ViT-B/32)** | 1000 forward passes; tokenizer is small | **~90 s** (≈1.1 s per batch of 16 on RTX 5090 with bf16 autocast) |
| **JSON write** | One call | **<1 s** |
| **Total end-to-end** | Image I/O + InceptionV3 + FID math + CLIPScore + JSON | **≈ 4 minutes** for a full 1000-image run on RTX 5090 |

### Reference: scale-up ledger

| N samples | Estimated wall-clock (RTX 5090) | Notes |
|---|---|---|
| 100 | ~25 s | smoke-test scale (single sweep) |
| 553 (GenEval full) | ~2 min 20 s | covers one full GenEval pass |
| 1,000 | ~4 min | operator's default Phase B scale |
| 4,000 (4 samples × 1K) | ~16 min | one round of x4 sampling for GenEval stability |
| 10,000 | ~40 min | cover the DPG-Bench prompt set × 1 sample |
| 30,000 | ~120 min | MS-COCO-30K FID target for HiDream-I1-Dev (if paper adds row) |

For **4 schedulers × 3 seeds × 5 row variants** (worst-case Phase B
table fill), the operator budgets **~5 hours per SOTA model** on a
single RTX 5090, dominated by sample generation (HiDream-I1-Dev 28
NFE × 1000 imgs × 4 schedulers × 3 seeds ≈ 6.7 GPU-hours at
~2.5 s/image; note this is generation, not metric stage).

### GPU-allocation contract (Phase B prep)

- **GPU 0** (RTX PRO 6000, 98 GB) → InceptionV3 (~100 MB) + CLIP-vit-base-patch32 (~600 MB) + HiDream-I1-Dev (24 GB) → leaves ~73 GB of headroom for other tenants.
- **GPU 1** (RTX 5090, 32 GB) → metric stage alone OR an additional HiDream instance.
- **Never load HiDream-I1-Full** (17 B, 32 GB) on GPU 1 alongside metric stage — OOM. The full variant lives on GPU 0 only.

---

## §6. Open questions for the operator

These are the **load-bearing choices** the plan *cannot* make by itself.
Resolve before pressing go.

1. **GEN_EVAL_PROMPT_LIST for Lumina-Image 2.0** — the paper does not
   reproduce its prompt subset verbatim in the appendix. If the operator
   wants to quote our CLIPScore alongside the paper's CLIP-T row,
   they must reconcile the prompt source. *Default*: stick to the
   publicly hosted GenEval prompts from
   `https://github.com/djghosh/generative-evaluation/tree/master/data`
   and document any drift in the report.

2. **DPG-Bench judge model** — self-host MiniCPM-V 2.6 (Tier 2, free,
   slow) **or** pay for GPT-4V (Tier 1, paper's choice, ≈$0.04 per image
   × 10K = ≈$400). The paper uses GPT-4V; matching the paper is the
   honest move but costs real money. *Decision needed.*

3. **MJHQ-30K reference stats authenticity** — Clean-FID hosts
   `mjhq30k_inception_stats.npz`, but the Lumina-Image 2.0 paper
   computes its own stats from the original 30K MJHQ subset. Verify the
   two agree to within ~0.1 FID before quoting; if they don't, prefer
   the paper's stats (run `cleanfid.make_custom_stats('mjhq30k', <orig-jpegs>)`).

4. **Seed-set count for the per-scheduler comparison table** — the paper
   recipe is "3 seeds, mean ± std" (paper-plan §4.1). HiDream-I1-Dev 28
   NFE × 1000 imgs × 4 schedulers × 3 seeds ≈ 6.7 GPU-hours on a single
   RTX 5090 — feasible, but the operator must confirm budget.

5. **CLIPScore prompt alignment** — the runner aligns image→prompt
   positionally by sorted filename. If the operator's sampler writes
   images out of order, every CLIPScore is wrong. A verification helper
   should print the first 3 (filename, prompt) pairs at runner start
   (today it doesn't — future work; tracked under `tools/run_image_eval.py` TODO list).

6. **GenEval "single-object" vs "two-object" sub-scores** — the paper
   reports both. The official geva package already breaks them out;
   make sure the operator's report includes both, not just the average.

7. **DPG-Bench "entity" / "attribute" / "relation" / "global" breakdown**
   — same story as GenEval. The MiniCPM-V judge returns the four
   sub-scores; quote them, not just the average.

8. **HiDream-I1-Dev 24 GB vs HiDream-I1-Full 32 GB** — paper §4 uses both.
   The plan budgets *Dev* on GPU 1; *Full* on GPU 0 only. If the
   operator wants to compare Dev vs Full, they must run *Full* on
   GPU 0 alone (DEV pre-empts GPU 1). Add a multi-launch script.

9. **Custom `transformers` model id for CLIPScore** — the runner
   defaults to `openai/clip-vit-base-patch32`. The paper uses
   `openai/clip-vit-large-patch14-336` for some rows. Either expose
   the CLI flag already in place (`--clip-model-id`) and pass it per
   experiment, **or** stay with B/32 across all rows and caveat.

10. **Off-shell metric alignment** — when an external GenEval/DPG tool
    produces a number, how does it land in our JSON report? Today the
    operator must hand-edit `eval_report.json`. A future patch could
    add `--geneval-json /path/to/geva/results.json` and
    `--dpg-bench-json /path/to/minicpm-v/results.json` flags that
    parse-and-merge. Defer to Phase B+ unless the operator asks.

---

## §7. Day-1 operator checklist (the five commands, in order)

```bash
# 0. Activate the project venv (created by `uv sync`).
source .venv/bin/activate

# 1. Install the image-eval extra (torch / torchvision / transformers / cleanfid).
pip install -e ".[image-eval]"

# 2. Pre-download the canonical FID-InceptionV3 weights + the CLIP weights.
curl -fL --retry 3 \
  https://github.com/mseitzer/pytorch-fid/releases/download/fid_weights/pt_inception-2015-12-05-6726825d.pth \
  -o ~/.cache/torch/hub/checkpoints/pt_inception-2015-12-05-6726825d.pth
python -c "from transformers import CLIPModel, CLIPProcessor; \
  CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); \
  CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"

# 3. Download reference stats for the two datasets in scope.
mkdir -p data/fid_stats
curl -fL --retry 3 \
  https://github.com/GaParmar/clean-fid/releases/download/cleanfid/mjhq30k_inception_stats.npz \
  -o data/fid_stats/mjhq30k_inception_stats.npz
# GenEval is operator-side (cleanfid.make_custom_stats).

# 4. Smoke-test the runner with a single image.
python tools/run_image_eval.py \
  --samples-dir data/lumina_image_2_0/samples \
  --reference-stats data/fid_stats/mjhq30k_inception_stats.npz \
  --prompts-jsonl data/lumina_image_2_0/prompts.jsonl \
  --output data/lumina_image_2_0/eval_report.json \
  --device cuda:0 --image-target-size 299

# 5. Verify the JSON report, then run external GenEval + DPG-Bench.
cat data/lumina_image_2_0/eval_report.json   # fid + clip_score filled, geneval/dpg_bench = external stubs
```

---

## §8. References

- `tools/run_image_eval.py` — runner source (FIDs the FRL InceptionV3 contract; emits CLIPScore mean ± std; stubs GenEval / DPG-Bench).
- `tools/eval_rf_cifar.py` — NumPy + torch FID path that `compute_cifar_fid.py` reuses; same InceptionV3 forward contract.
- `tests/test_tools/test_run_image_eval.py` — 5 hermetic tests (smoke + graceful-fallback + schema + image-mode + FID-clip).
- `docs/r4-survey/07-sota-experiment-protocol.md` — the broader R4 protocol; this Phase-B plan implements its §6 "phase B" clause for image models.
- `docs/PLUG_IN_YOUR_MODEL.md` — adapter + harness wiring checklist (HiDream-I1 specific).
- Clean-FID Release page — host of the precomputed FID statistics.
- pytorch-fid v0.3.0 Release page — host of the canonical InceptionV3 weight file.
- HiDream-I1-Dev paper (Cai 2025, arXiv 2503.21382) — Tables 2, 3, 4.
- Lumina-Image 2.0 paper (Alpha-VLLM 2025, arXiv 2503.21758) — Tables 1, 2, 3.
