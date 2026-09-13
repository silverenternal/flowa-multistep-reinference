# Wave128 CIFAR retry3 smoke

Using `.venvs/kanzi_venv` on GPU0, `RectifiedFlowCIFARAdapter` loaded the
training bundle via its `model` state dict fallback and completed
`batched_inference(n_samples=2, num_steps=4, seed=7)`. Output shape/dtype and
summary are recorded in `verification_outputs/wave128_cifar_gpu_retry3/smoke.txt`.
This validates forward sampling only; no statistical conclusion or paper
claim is made.
