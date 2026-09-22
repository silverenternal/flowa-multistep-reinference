# CIFAR reference availability check

The runner expects `data/cifar10_test_ref.npz`; it is absent in this checkout.
The documented generator is `tools/run_sota_cifar_experiment.py --build-ref`
using torchvision and writes roughly 120 MB for 10,000 test images. This audit
only checked availability and CLI help; no download was attempted and no
paper conclusion changed.
