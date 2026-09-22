# Wave131 CIFAR arm filter

Added optional `--schedulers` (comma-separated) to
`tools/run_rf_cifar_ablation.py`; default empty value preserves all-arm
behavior and unknown names fail closed. Parser smoke passed. This enables
isolated diagnosis of slow arms without changing experiment semantics.

With kanzi_venv/GPU0, N=2, one round, NFE=4, the `evidence_driven` arm
completed and emitted JSON/Markdown. The `rf_1step_fixed` smoke exceeded the
short execution window and produced no summary; it is marked incomplete.
No paper claims were updated.
