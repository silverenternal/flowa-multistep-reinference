# CIFAR evaluation corrections

This review found substantive gaps in the earlier completion reports. A
parser test did not establish safe resume behavior, a reference generation
command did not exist, and successful adapter construction used non-EMA
weights when the published bundle contained EMA shadow parameters.

Changes:

- `eval_rf_cifar.py --extract-reference-features` now builds real pool3
  features from normalized CIFAR images using the canonical pretrained
  torchvision extractor. It validates input/output, writes atomically,
  records source SHA-256 and refuses to overwrite existing evidence.
- Ablation resume checks configuration, effective checkpoint content,
  reference content, implementation hashes, complete curves and finite
  results. Malformed caches are recomputed. Required references are
  checked before model construction; failed arms return a nonzero exit.
- CIFAR bundles use EMA shadow weights following the published conversion
  order, preserving `module.sigmas`. Malformed EMA no longer silently
  selects non-EMA model weights. Shape/count mismatches are rejected.
- The TF-port Inception path receives [0,1] pixels; its own normalization
  is no longer preceded by erroneous ImageNet normalization.

Validation: 27 tests for reference extraction and resume/reference behavior
passed in the lightweight environment. 18 EMA/preprocessing behavior tests
passed under `.venvs/kanzi_venv` with real torch. The existing ablation suite
also passed (7 passing, 2 dependency-gated skips in the lightweight environment).
These checks do not prove matched-NFE empirical improvements.

The real extraction command completed on GPU0:

```sh
CUDA_VISIBLE_DEVICES=0 .venvs/kanzi_venv/bin/python tools/eval_rf_cifar.py \
  --extract-reference-features --reference-samples data/cifar10_test_ref.npz \
  --reference-features data/cifar10_inception_features.npz \
  --feature-device cuda:0 --batch-size 32
```

Output: 10000 x 2048 finite float32 features, SHA-256
`a3736bb7ff369f5a5b31b112fbaeb139cb48949c0076b36e40ecf198ae61d617`.
Source image SHA-256:
`01b4857db8f8c3ea2e20fcdf962216a6fe7f8563969ba7d0370e75220616aaa7`.
The archive embeds source, preprocessing and extractor metadata.
These torchvision test-set features must not be mixed with TF-port features
or reported as reproduction of a published FID. `pytorch-fid==0.3.0` was
installed into the existing Kanzi sidecar and its pretrained TF-port weights
loaded successfully for the separate matched-NFE experiment.

The corrected loader was also checked against the pre-existing cleaned
`data/cifar10_rf.pth`: after removing the DataParallel `module.` prefix,
all 565 keys and all tensor values match exactly (zero mismatches). Thus
the shadow-parameter conversion preserves the existing published EMA
conversion, rather than merely producing a loadable model.

The six root TODO plans have been reopened where experiment acceptance is
missing; [open-requirements.md](open-requirements.md) records the remaining
conditions. Previous `DONE` labels based only on code commits were premature.
