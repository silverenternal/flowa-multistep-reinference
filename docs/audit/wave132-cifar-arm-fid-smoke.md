# Wave132 CIFAR per-arm FID smoke

All four arms (`evidence_driven`, `rf_1step_fixed`, `cosine`,
`codimension_sheet`) completed N=1, one-round, NFE=1 smoke runs under
`kanzi_venv`/GPU0. The requested `data/cifar10_test_ref.npz` is an image
reference, while this ablation driver expects Inception feature arrays; it
therefore activated its synthetic-vs-random fallback and emitted NaN FIDs for
every arm. Outputs are complete for smoke execution but contain no finite,
paper-comparable metric. No claims were updated.
