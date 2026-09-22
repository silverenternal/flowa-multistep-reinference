# Wave131 rf_1step_fixed smoke

The isolated arm completed on kanzi_venv/GPU0 with N=1, one round, NFE=1 in
about 7 seconds. It wrote `ablation.json` and `ablation.md`. Feature extraction
used the script's synthetic-vs-random fallback because
`data/cifar10_inception_features.npz` is absent; the resulting FID is not
paper-comparable. No quick-path code change was needed and no claims were
updated.
