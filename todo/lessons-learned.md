# `todo/lessons-learned.md` — cross-cutting patterns (LL-001, ...)

**Purpose:** capture cross-cutting lessons that affect how we approach future
work. Each entry: title, evidence, mitigation. Append-only.

---

## LL-001 — `ckpt + upstream source` both required for "shippable model"

**Date:** 2026-09-05
**Evidence:** Wave 10 LineageFlow (see `todo/models/lineageflow.md`). The
public 9.788 GB ckpt was on disk and SHA-256 verified, but the upstream
LineageFlow GitHub repo (containing `core.sampler`, `core.flow_model`,
`data/`) was not surfaced in Wave 9 R3 research and is unreachable from
the sandbox (drive.google.com / huggingface.co / github.com partially
blocked). The ckpt is a PyTorch Lightning checkpoint with class references
to `core.sampler.SamplerConfig` that cannot be unpickled without the source.
**Wave 10 setup was BLOCKED; adapter ships on synthetic velocity shim;
comparison tied at family_validity=1.0 ceiling; claim verdict
partially_supported (real-ckpt OPEN).**

**Mitigation:**
1. When researching a candidate model, confirm BOTH (a) ckpt is publicly
   downloadable AND (b) source repo / inference API is public. A model
   without (b) is design-only, not shippable.
2. Add to `todo/models/<model>.md` §C: explicit "upstream source
   accessible?" question, checked before committing to a Wave.
3. If upstream source is missing, declare "design-only integration" upfront
   and skip the model (no adapter file).
4. Wave 9 R3's "sub-GB" estimate was 10× wrong — do not trust single-source
   research; cross-check the size against HF model card or repo docs.

**Reusable in:**
- Every Phase 2 per-model analysis (template: `todo/models/README.md` §C)
- Every Wave 2+ research agent (model selection criterion)

---

## LL-002 — `metric_saturation` invalidates comparison

**Date:** 2026-09-05
**Evidence:** Wave 10 LineageFlow comparison. family_validity was 1.0 in BOTH
baseline and framework arms, giving delta=0% (tie). The synthetic velocity
shim is a deterministic per-position-affine NumPy field that always
produces valid (well-formed) amino acid sequences, so family_validity
saturates at the ceiling regardless of framework value-add. The comparison
ran without error but produced no signal.

**Mitigation:**
1. Before any Phase 4 integration, define an "Acceptance metric table"
   per model (now in `PHASE-4-model-integration-iteration.md`).
2. Add a "Saturation check" column: if the metric saturates at the
   baseline, the comparison is **TIE (not supported)**, not supported.
3. Pick a metric that has headroom to move. E.g. for image models where
   FID < 5.0, prefer **inception_score** or **precision/recall** over FID
   (which is already SOTA at the baseline).

**Reusable in:**
- Every Phase 4 comparison
- Every `todo/models/<model>.md` §F (empirical record)

---

## LL-003 — "Research estimate" ≠ "shippable model" — always validate ckpt load

**Date:** 2026-09-05
**Evidence:** Wave 9 R3 research said LineageFlow was "sub-GB on disk" and
"easy 5090 fit". Actual ckpt is 9.788 GB. The error is likely a research
agent reading the HF model card's "small checkpoint" mention without
verifying the actual file size. Then a 5090 with 32 GB total cannot run
a 9.788 GB ckpt at full precision; bf16 reduces to 4.89 GB which fits but
still requires significant GPU memory for activations + optimizer state.

**Mitigation:**
1. Research agents must verify HF file sizes via actual `hf_hub_download`
   HEAD requests, not just by reading model cards.
2. `todo/models/<model>.md` §A must list the actual ckpt size (verified
   via `ls -lah` after download), not the paper-reported model size.
3. Compute "fit margin" = (32 GB - ckpt_size - activation_overhead_estimate)
   and reject any model with negative margin.
4. The "framework has theory, if integration doesn't improve, must be
   implementation wrong" hypothesis (user 2026-09-05) means: failed
   integration is **evidence of an implementation problem**, not evidence
   against the framework claim. Look for what broke in the integration
   first; the theory should hold if the implementation is right.

**Reusable in:**
- Every Phase 2 per-model analysis (template: `todo/models/README.md` §A)
- Every Wave 2+ research agent (verification step before commit)