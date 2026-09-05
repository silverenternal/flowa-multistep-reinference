# Model Card — freqflow (FreqFlowAdapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter key:** `freqflow`
**Card status:** COMPLETE (8/8 fields populated). Adapter Protocol
surface is fully wired and tested in `synthetic` mode; the production
`torch` mode is **BLOCKED** — upstream has not published a checkpoint.
**Last updated:** 2026-09-05 (Wave 36 Agent B, PHASE-4).
**F.4 gate:** PASS (≥ 0.8 per-model target met).
**PHASE-4 real-ckpt gate:** **BLOCKED — no public weights** (§6).

---

## 0. Real-checkpoint state (Wave 36 Agent B)

**Verdict: `nnet_ema.pth` does not exist publicly. No FID number is
claimed, reproduced, or estimated for FreqFlow.**

Probed 2026-09-05 from the GPU host (network reachable; `github.com`
returned HTTP 200, so this is a genuine absence, not a sandbox block —
contrast the Wave 19 analysis note in `todo/models/freqflow.md`, which
flagged GitHub as TCP-blocked from the sandbox):

| Probe | Result |
|---|---|
| `api.github.com/repos/OliverRensu/FreqFlow` | 200 — repo exists, public |
| `.../releases` | `[]` — no release assets |
| Recursive git tree of `main` | 23 files: code + `figs/img.png`. No `.pth`, no `.safetensors`, no LFS pointer |
| `huggingface.co/api/models?search=FreqFlow` | `[]` |
| `huggingface.co/api/models?search=Frequency-Aware Flow Matching` | `[]` |
| `huggingface.co/api/models?search=nnet_ema` | `[]` |
| `huggingface.co/api/models?author=OliverRensu` | `[]` — no HF account |

The upstream README's inference recipe reads
`--nnet_path=/path/to/nnet_ema.pth`. That is a **placeholder in the
authors' own command line**, not a download URL — which is why the
Wave 19 analysis recorded the weights URL as "conditional". Wave 36
resolves that condition to **negative**.

### What was downloaded

The upstream **source tree** is public and was fetched, satisfying the
upstream half of LL-001 (ckpt + upstream code both required):

| Artifact | SHA-256 | Size |
|---|---|---|
| `FreqFlow` `main` tarball | `e42d0eb1fac596ba5acf2dca36490fd67b0a7dbebea81485eafbe8e861c7d56e` | 521 464 B |
| Extracted tree (22 files, `figs/img.png` stripped) | see `data/freqflow_ckpt/SHA256SUMS` | 212 KB |
| `nnet_ema.pth` | — | **absent** |

Landing zone is `data/freqflow_ckpt/` (gitignored under the repo-wide
`data/` rule, so the bytes are not committed; `SHA256SUMS` and a README
with the probe transcript live alongside them). `sha256sum -c SHA256SUMS`
verifies clean.

The tarball digest is pinned in code as
`FREQ_FLOW_UPSTREAM_TARBALL_SHA256` so a later re-fetch detects an
upstream change that would invalidate the adapter's assumptions about
the two-branch architecture.

### Manual acquisition (when weights are released)

1. Watch <https://github.com/OliverRensu/FreqFlow> releases, or contact
   the corresponding author (`oliverrensu@gmail.com`, per the README).
2. Place the file at `data/freqflow_ckpt/nnet_ema.pth`, or export
   **`FREQFLOW_CKPT`** pointing at the file *or* its containing
   directory (both forms are accepted).
3. Append its digest to `data/freqflow_ckpt/SHA256SUMS` and re-verify.
4. Re-run `pytest tests/test_adapters/test_freqflow_real_ckpt.py -v`.
   The three `REQUIRES_CKPT` tests flip from skip to real assertions
   with no code edit.

No checkpoint is fabricated, and no synthetic-mode result is presented
as a FreqFlow measurement anywhere in this repository.

## 1. Intended Use

- **Primary use.** Wire the published FreqFlow model (Ren et al. 2026,
  CVPR 2026, `arXiv:2604.15521` — *Frequency-Aware Flow Matching for
  High-Quality Image Generation*) into the framework's
  `FlowMatchingODEAdapter` Protocol, so the same algorithm-layer code
  that drives 2D FM and CIFAR-10 RF also drives a two-branch
  frequency + spatial SiT-XL/2 backbone on ImageNet-256 latents.
- **Primary users.** Framework algorithm-layer developers; PHASE-4
  model-integration work validating the "any FM model, when integrated
  into the framework, improves" claim on the image axis.
- **Out-of-scope uses.** Other resolutions (ImageNet-512, CIFAR),
  non-image modalities, fine-tuning, or any production deployment.
  **Also out of scope today: any quantitative claim**, because no
  trained weights exist (§0).
- **Decision-support / safety.** Not a decision-support model.

## 2. Training Data

- **Source.** ImageNet-1k (Russakovsky et al. 2015, ILSVRC), 1.28 M
  training images, 1000 classes, encoded via the SiT SD-VAE (KL-reg,
  8× downsample) to a `(4, 32, 32)` float32 latent.
- **Size.** 1.28 M train / 50 000 val; 1000 classes + 1 unconditional
  token (1001-dim class embedding).
- **Pre-processing.** Standard ImageNet pipeline (resize +
  center-crop 256×256 → VAE encode → `(4, 32, 32)` latent).
- **Provenance.** The adapter does not train. It would consume the
  published `nnet_ema.pth`; upstream reports `accelerate launch` on
  32 GPUs × 4 nodes (≈2 000–3 000 GPU-days).
- **Caveat.** All of the above is **read from the paper and the
  upstream training script**, not verified against a checkpoint — no
  checkpoint exists to verify against.

## 3. Evaluation Data

- **Held-out reference.** ImageNet-256 validation set (50 000 images)
  for the paper's FID-50K protocol.
- **Evaluator.** FID-50K (Heusel et al. 2017).
- **Framework protocol.** Per LL-002 the comparison would need N ≥ 5 000
  with k = 5 subset CIs, because the paper's FID 1.38 sits near the
  saturation floor against the SiT-XL/2 baseline (FID ≈ 1.96): a
  framework delta below ≈0.05 FID is indistinguishable from noise and
  must be declared TIE, not a win.
- **Status.** **Not run.** Requires weights (§0).

## 4. Quantitative Analyses

| Quantity | Value | Source |
|---|---|---|
| Paper FID (ImageNet-256, 50 NFE Euler) | 1.38 | Ren et al. 2026, upstream README |
| Paper improvement over DiT / SiT | 0.79 / 0.58 FID | upstream README |
| Params | ≈675 M | Wave 19 analysis (two-branch SiT-XL/2) |
| Framework-reproduced FID | **not measured** | no checkpoint (§0) |
| Framework Δ vs baseline | **not measured** | no checkpoint (§0) |

Every figure in the first block is **paper-claimed and unverified by
this repository**. The measured rows are empty by design; they are not
filled with synthetic-mode output.

Test-suite state, `pytest tests/test_adapters/test_freqflow_real_ckpt.py`:
28 passed, 3 skipped (the `REQUIRES_CKPT` set), 0 failed. The skips are
the honest representation of §0.

## 5. Ethical Considerations

- **Generative image risk.** A class-conditional ImageNet generator can
  synthesise photorealistic imagery; ImageNet's own class taxonomy and
  collection process carry documented representational biases that a
  generator inherits and can amplify.
- **License.** Upstream ships **no `LICENSE` file** — the tree has 23
  files and none is a licence. Absent an explicit grant, the code is
  "all rights reserved" by default. The vendored source snapshot is
  kept locally, gitignored, and **not redistributed**; any future
  checkpoint must not be redistributed either.
- **Attribution.** Sucheng Ren, Qihang Yu, Ju He, Xiaohui Shen,
  Liang-Chieh Chen (ByteDance), Alan Yuille (JHU); CVPR 2026.

## 6. Caveats

- **C1 — no checkpoint (blocking).** The single caveat that dominates
  the card. FreqFlow cannot enter the PHASE-4 acceptance table until
  upstream publishes weights. Status: **BLOCKED**, not FAILED — nothing
  in the adapter is known to be wrong; it is untested against weights.
- **C2 — synthetic mode is not FreqFlow.** The `synthetic` backend is a
  two-branch NumPy shim (a 4096→256→4096 MLP plus a linear projection of
  the normalised FFT magnitude). It reproduces the adapter's *Protocol
  surface and mixing algebra*, not its learned velocity field. Numbers
  from it are meaningless as model results and are never reported as such.
- **C3 — `force_mode="torch"` degrades in-constructor.** Even with a
  checkpoint on disk, `FreqFlowAdapter.__init__` currently reassigns
  `self._mode = "synthetic"` after selecting `"torch"`, and
  `_velocity_field` asserts on the synthetic weights. Loading the real
  SiT-XL/2 + FFT graph is deliberately deferred until a checkpoint
  exists to load — writing an unexercisable loader against a state-dict
  layout nobody has seen would be guesswork. The checkpoint-resolution
  and failure-mode contracts around it *are* tested today.
- **C4 — saturation (LL-002).** Even with weights, FID 1.38 is close
  enough to the SiT baseline that a framework improvement may be
  unmeasurable. Plan for TIE as a likely honest outcome.
- **C5 — integrator drift.** The paper uses 50-NFE Euler; the
  framework's Heun/RK4/DPM-Solver defaults will not reproduce the
  paper's FID without a matched-NFE protocol.

## 7. Paper-Equation Provenance

- **Flow-matching path.** Linear interpolation
  `X_t = (1 − t)·X_0 + t·X_1`, MSE velocity regression — the standard
  latent FM objective the paper builds on.
- **Two-branch velocity.** The adapter models FreqFlow's central
  contribution as a convex combination
  `v_θ = (1 − m)·v_spatial + m·v_freq`, with `m = frequency_mix ∈ [0, 1]`
  and `v_freq` driven by the normalised `|FFT2(x)|` side-channel. The
  paper's own fusion is a *time-dependent adaptive weighting* with
  separate low- and high-frequency processing; the adapter's fixed
  scalar `m` is a **simplification**, exposed as a per-round knob via
  `condition.delta_spec["frequency_mix"]` so a future schedule can be
  threaded through without a Protocol change.
- **JMAA coverage.** Theorem 1 F-side: the velocity field is a
  continuous-time ODE, compatible with `uniform_simplicity`. Lemma 2:
  the two-branch fusion is piecewise-smooth. Proposition 6: the
  frequency branch is the paper's claimed escape-from-sharpness
  mechanism. None of these are *validated* against weights (§0).

## 8. Known Failure Modes

- **F1 — silent synthetic fallback.** `force_mode="auto"` degrades to
  synthetic when weights are absent, which is correct for tests but
  would be a reporting hazard. Mitigated by `force_mode="torch"`
  raising `FileNotFoundError` with `freqflow_weights_missing`, asserted
  in `test_force_torch_without_weights_raises_documented_error`.
- **F2 — stale `$FREQFLOW_CKPT`.** An env var left pointing at a deleted
  file falls through to the data-dir search rather than pinning a dead
  path (`test_env_var_pointing_at_a_missing_file_falls_through`).
- **F3 — truncated download.** A partial `nnet_ema.pth` would load as a
  corrupt state dict. `test_real_ckpt_file_is_nontrivial` rejects any
  candidate under 100 MB (a real checkpoint is ≈2.7 GB).
- **F4 — dead frequency branch.** A checkpoint whose FFT branch is
  missing or zeroed would make `frequency_mix` a no-op and silently
  reduce FreqFlow to SiT.
  `test_frequency_mix_changes_the_sample` and
  `test_frequency_mix_knob_with_real_ckpt` assert the extremes diverge.
- **F5 — latent clamp saturation.** The trajectory is clipped to
  `[−6, 6]`; a checkpoint with a wider latent scale would saturate.
  Re-tune `FREQ_FLOW_CLAMP` against the real VAE statistics once
  weights exist.
- **F6 — CFG range.** The adapter defaults to `guidance_scale = 1.5`,
  a mid-range choice; the paper sweeps `--cfg`/`--cfg_scale_pow`, so
  the paper's headline FID requires a sweep, not the default.

## See also

- Adapter: `adaptive_reflow/adapters/freqflow.py`
- Tests: `tests/test_adapters/test_freqflow.py` (synthetic surface),
  `tests/test_adapters/test_freqflow_real_ckpt.py` (checkpoint contract)
- Wave 19 analysis: `todo/models/freqflow.md`
- Landing zone + probe transcript: `data/freqflow_ckpt/README.md`
- Lessons: `todo/lessons-learned.md` (LL-001 ckpt + upstream both
  required; LL-002 saturation invalidates comparison)
