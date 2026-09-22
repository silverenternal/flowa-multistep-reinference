# Wave 128 CIFAR GPU retry

Date: 2026-09-13. Retry used `.venvs/kanzi_venv` per `docs/environments.md`;
torch 2.14.0+cu130 reported CUDA available on GPU0 (RTX PRO 6000 Blackwell).

The bounded quick matched-NFE command reached adapter construction but failed
to load `data/rectified_flow_cifar10.pth`: the file is an optimizer bundle
with keys `optimizer`, `model`, `ema`, and `step`, while
`RectifiedFlowCIFARAdapter` expects a raw DDPMppUNet state dict. No samples or
metrics were produced. Exact request, environment, and failure are recorded
in `verification_outputs/wave128_cifar_gpu_retry/run_metadata.json`.

This is a checkpoint-format mismatch, not evidence about the algorithm; no
paper or claims surface was updated. A valid raw checkpoint (or explicit
bundle extraction procedure) is required before the N=200 audit can run.
