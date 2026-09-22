# Wave 129 CIFAR small matched-NFE sweep

Run used `.venvs/kanzi_venv` on GPU0 with N=16, four rounds, and NFE=50.
Baseline and `CosineAnnealScheduler` sample artifacts plus per-round metrics
were produced. The process stalled while executing remaining scheduler arms
and was stopped within the bounded execution window; therefore the sweep is
**incomplete** and no comparison or paper claim is made.

Raw outputs and metadata are in `verification_outputs/wave129_cifar_small_sweep/`.
