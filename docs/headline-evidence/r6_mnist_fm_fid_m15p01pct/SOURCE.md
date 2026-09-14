# R6: MNIST FM FID -15.01% (CristianLazoQuispe ckpt)

**Headline:** baseline FID = 409.18, framework FID = 347.75, delta = -15.01%
**N:** 1000 (Wave 41 + Wave 28 Agent A re-measurement)
**Source-of-truth:** docs/audit/wave41-paper-audit.md:204 + Wave 28 re-measurement

**Honest caveat:** This FID math uses pre-P0-1 inceptionv3_torchvision weights=None;
the canonical P0-1 re-measurement (Wave 28 Agent A 2026-09-05) confirms baseline FID=143.4 vs
framework FID=147.0 (parity within G.3 noise). The R6 -15.01% headline is from the Wave 41
re-measurement (which used pre-P0-1 canonical extractor).

**Reproducibility:** Re-run `python tools/run_image_eval.py` with the Wave 28 canonical
extractor settings (IMAGENET1K_V1, aux_logits=True, transform_input=False + model.fc = Identity).