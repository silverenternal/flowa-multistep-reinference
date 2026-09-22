# Wave 128 CIFAR matched-NFE GPU audit

Date: 2026-09-13. Output directory:
`verification_outputs/wave128_cifar_gpu/`.

Preflight captured GPU0 as NVIDIA RTX PRO 6000 Blackwell, 2 MiB / 97887 MiB
used, 0% utilization. The bounded command requested a quick matched-NFE
run with checkpoint `data/rectified_flow_cifar10.pth`, 4 rounds, baseline and
framework max 50 steps, and independent sample limits. The runner exited
before inference with `RuntimeError: cuda experiment requires torch and a
valid checkpoint`; the active environment lacks the required torch runtime.

No result artifact or paper claim was produced. The exact request and block
reason are recorded in `verification_outputs/wave128_cifar_gpu/run_metadata.json`;
GPU postflight is in `gpu_after.csv`. Re-run under the documented model
sidecar environment after installing torch.
