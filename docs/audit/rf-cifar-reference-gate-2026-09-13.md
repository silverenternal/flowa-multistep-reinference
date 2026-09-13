# RF CIFAR reference evidence gate

Added opt-in `--require-reference` to `tools/run_rf_cifar_ablation.py`.
When enabled, the driver fails closed if the reference `.npz` is missing, lacks
`features`, is empty/non-2-D, or does not contain the canonical 2048-dimensional
Inception features. The error points operators to
`tools/eval_rf_cifar.py --extract-reference-features`. Default smoke behavior
and existing outputs remain unchanged.

Focused tests pass **6 tests** (2 torch-gated skips, 3 warnings).
