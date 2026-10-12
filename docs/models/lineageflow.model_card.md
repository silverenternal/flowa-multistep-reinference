# Model Card — lineageflow (LineageFlowAdapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter key:** `lineageflow`
**Card status:** COMPLETE (8/8 fields populated; production torch-mode
ckpt loading is **UNBLOCKED** via the Wave 39 5-LOC `_install_checkpoint_compat`
shim — mirrors upstream `_install_checkpoint_compat()` in
`inference/inference.py:39-59`). **The real forward pass now runs in the
adapter**: the upstream source tree is vendored at
`data/lineageflow_upstream/`, and the torch path builds the real
`models.model.LineageFlowClassifier` (657.6 M params) + the real
`inference.inference.compute_family_vector_field` (D-004 fix, 2026-10-12;
see `docs/audit/lineageflow-real-forward-fix.md`). The synthetic-mode
Protocol surface remains fully wired and tested. 25/25 hand-written tests
pass on CPU in ~18 s; 1 real-ckpt end-to-end test loads the 10.5 GB
published checkpoint with the shim installed and confirms the encoder
`word_embeddings` tensor shape = `(33, 1280)` matches the paper.
**Last updated:** 2026-10-12 (D-004 real-forward-pass fix).
**F.4 gate:** PASS (≥ 0.8 per-model target met).

---

## 1. Intended Use

- **Primary use.** Wire the published LineageFlow protein flow
  matching model (Lin et al. 2026, ICML 2026,
  `arXiv:2605.22252`) into the framework's
  `FlowMatchingODEAdapter` Protocol so the same algorithm-layer
  code that drives 2D FM, CIFAR-10 RF, Self-Flow image, and
  FlowMol3 molecules also drives a Pfam-family phylogeny-aware
  protein generator. Validates the "any FM model, when integrated
  into the framework, improves" claim as the **second** SOTA 2026
  model (protein axis, distinct from Self-Flow image axis).
- **Primary users.** Framework algorithm-layer developers; paper
  authors writing the `docs/paper-draft.md` §4 protein record;
  users running `tools/run_sota_lineageflow_experiment.py` once
  the upstream `core` source repo is reconstructed.
- **Out-of-scope uses.** Non-protein modalities, downstream
  structure prediction (use ESMFold / AlphaFold), production
  deployment.
- **Decision-support / safety.** Not a decision-support model.
  Generated sequences must **not** be deployed as drug candidates
  or therapeutic proteins without expert review.

## 2. Training Data — upstream `core` vendored; forward pass unblocked

- **Source.** Pfam families (El-Gebali et al. 2019) — 88 600
  proteins across 8 886 families per the paper.
- **Size.** ≈ 88 600 proteins; ≈ 8 886 Pfam families.
- **Train / val / test split.** Per-paper canonical split.
- **Provenance.** The adapter consumes the published
  `lineageflow-rp55.ckpt` checkpoint from
  `huggingface.co/jinxbye/LineageFlow` (9.788 GB on disk,
  SHA-256 verified: `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b`).
  The checkpoint stores `hyper_parameters["sampler_cfg"]` which
  carries the runtime knob-set for the per-family sampler.
- **Upstream `core` source repo — now VENDORED (D-004, 2026-10-12).** The
  ckpt pickle references `core.sampler.SamplerConfig` (shimmed by
  `_install_checkpoint_compat`) and the upstream `core` /
  `models.model` / `inference.inference` modules. Those are vendored at
  `data/lineageflow_upstream/` (upstream commit `ccef84ad`), so the real
  model now loads and runs: the adapter builds
  `models.model.LineageFlowClassifier(FlowTransformerConfig())` and loads
  the ckpt with **missing=0 / unexpected=0**. **This field is no longer
  blocked.** The training-data description above is still sourced from the
  paper + the ckpt `hyper_parameters` blob (the released checkpoint ships
  no dataset), but a real forward pass now runs end-to-end.

## 3. Evaluation Data — real forward pass runs; prior is synthetic

- **Held-out reference.** Per-paper Pfam held-out families.
- **Evaluator.** `family_validity` (the paper's headline metric,
  ≈ 95.3 %), `avg_log_likelihood`, `amino_acid_diversity`.
- **Sample budget.** n=32 at seed=42 (Wave 10 R2 protocol,
  synthetic mode); n≥256 for the real-ckpt headline.
- **Why this is the right eval.** `family_validity` is the
  paper's own metric; framework-vs-baseline comparison is
  the natural framework value-add claim.
- **Real-ckpt numbers (D-004, 2026-10-12).** The real forward pass now runs
  (see §2 / §8), but the adapter's `alpha_h` **family prior is synthetic**
  (upstream ships it as a separate JSON asset that is not vendored), so no
  family-specific `family_validity` claim follows yet. The Wave 10 R2 numbers
  below are on the synthetic velocity field and saturate at the validity
  ceiling (1.0 vs 1.0, delta 0 %). The real-ckpt basis is a **different**
  model from the canonical R1 headline (see
  `docs/audit/r1-3seed-real-ckpt-materialize.md`).

## 4. Quantitative Analyses

| Metric | Paper headline | Wave 10 R2 (synthetic, n=32) | Framework vs baseline (synthetic) | Source |
|---|---:|---:|---:|---|
| `family_validity` | 95.3 % | 1.0000 | 1.0000 (Δ = +0.0 %) | `docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow |
| `avg_log_likelihood` | n/a | (paper baseline) | **+0.23 %** | `docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow |
| `amino_acid_diversity` | n/a | (paper baseline) | **+0.09 %** | `docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow |

Honest framing (per `docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow + Wave
10 follow-up): the **synthetic velocity field gives
`family_validity = 1.0` in BOTH arms**, so the baseline-vs-framework
comparison is meaningless on the saturation ceiling (no signal).
The framework shows small positive uplifts on secondary metrics
(`avg_log_likelihood` +0.23 %, `amino_acid_diversity` +0.09 %),
but `family_validity` ties at the saturation ceiling. **Claim
verdict (Wave 10, protein axis): PARTIAL support** — framework
ties at saturation on the synthetic surface. The **real-ckpt verdict is
now obtainable** (D-004, 2026-10-12: the real forward pass runs in the
adapter); a real-ckpt re-run on the 3-seed basis is recorded additively in
`docs/audit/r1-3seed-real-ckpt-materialize.md` (direction-consistent
framework-WINS, pooled `d_z = +0.110`, below the 0.8 STRONG bar → R1 stays
PARTIAL). R3 (`docs/baseline-audit-report.md` §F.2) remains
`NOT_REPRODUCED`.

## 5. Ethical Considerations

- **Dataset ethics.** Pfam is a curated, publicly-released
  academic database of protein families (El-Gebali et al. 2019).
  No PII, no patient data. The dataset is a sequence library,
  not biological samples.
- **Dual-use risk.** Moderate-to-high. LineageFlow generates
  protein sequences with explicit Pfam-family conditioning.
  Downstream users must **not** deploy generated sequences as
  therapeutic proteins, vaccines, or gene-therapy candidates
  without expert review (biosafety + functional validation).
  The framework adapter does **not** provide structure
  prediction or functional annotation — those are out of scope.
- **Bias / fairness.** Not applicable — protein sequences have
  no demographically protected categories. The bias axis is
  biochemical (e.g. amino-acid composition skew toward Pfam
  family priors).
- **Environmental cost.** GPU-bound. The 657.6 M parameter
  ESM-2 backbone at bf16 ≈ 3.5 GB on-device, plus trajectory
  buffer. The real-ckpt forward pass now runs (D-004): ~2.5 s/record
  on a contended `cuda:0` (RTX PRO 6000), ~0.3 s/record on a clean GPU
  (`docs/audit/wave349-gpu-acceleration.md`).
- **Mitigations.** None required for the adapter itself.
  Downstream use must include biosafety review and disclosure.
  Generated sequences are not patentable / not licensable as
  biologics without the standard discovery pipeline.

## 6. Caveats

- **Production torch-mode: ckpt loading UNBLOCKED via 5-LOC shim (Wave 39).**
  Wave 39 Agent B added `_install_checkpoint_compat()` to
  `adaptive_reflow/adapters/lineageflow.py` (mirrors upstream's own
  `_install_checkpoint_compat()` in
  `inference/inference.py:39-59`). The shim installs an empty
  `class SamplerConfig: pass` plus a fabricated `core.sampler` /
  `core` module pair so `torch.load` can resolve the pickled
  class reference. The class is **never called at runtime** —
  it is a pickle-only placeholder, which is why the upstream's
  own shim is exactly an empty body. **Verified end-to-end** by
  `tests/test_adapters/test_lineageflow.py::test_shim_unblocks_torch_load_on_real_ckpt`
  which loads the 10.5 GB published ckpt and confirms the encoder
  `word_embeddings` tensor shape = `(33, 1280)` matches the paper.
  **The real forward pass now runs** (D-004, 2026-10-12): the upstream
  `core` / `models.model` / `inference.inference` tree is vendored at
  `data/lineageflow_upstream/`, and the torch path builds the real
  `LineageFlowClassifier` + `compute_family_vector_field` — the velocity
  field is non-zero (`docs/audit/lineageflow-real-forward-fix.md`).
- **Production torch-mode: upstream `core` runtime now available.**
  The ckpt references `core.sampler.SamplerConfig` (shimmed) and the
  upstream `core` / `models.model` / `inference.inference` modules, which
  are vendored. The adapter loads the ckpt with missing=0/unexpected=0 and
  runs the real vector field. Caveats that remain: the `alpha_h` family
  prior is **synthetic** (upstream ships it as a separate JSON asset that
  is not vendored), and the adapter uses the base-flow vector field rather
  than the upstream intervention/mutation sampler
  (`generate_with_intervention`).
- **HF ckpt is 10× larger than Wave 9 R3 estimate.** Wave 9 R3
  reported "sub-GB"; the actual ckpt is 9.788 GB on disk.
- **Synthetic-mode is not a baseline reproduction.** When
  `torch` is missing or `core` is unavailable, the adapter
  falls back to a deterministic NumPy per-position velocity
  field. The synthetic path produces a well-formed but
  **non-trained** FM model so the Protocol conformance tests
  can run without the heavy dependency. **Synthetic-mode
  results must NOT be cited as baseline reproductions of
  LineageFlow.**
- **D.5 auto-battery skips the 8 conformance checks** (per
  baseline-audit D.5 — `lineageflow` requires `core` module).
- **No new claims.** This card documents an existing adapter
  under the Mitchell/Gebru schema; it does not introduce new
  empirical results.

## 7. Paper-Equation Provenance

- **Primary paper:** Liang, L., Yang, M., Feng, Y., Li, J., Pan,
  S., Xu, Y., Ying, T., Zheng, Y., & Xu, Z. (2026). *LineageFlow:
  Flow Matching for High-Fidelity Family-Aware Protein Sequence
  Generation*. ICML 2026 (poster), `arXiv:2605.22252`. Integrated
  via `LineageFlowAdapter` in
  `adaptive_reflow/adapters/lineageflow.py`.
- **Equations used:**
  - Linear interpolation `X_t = (1 − t) X_0 + t X_1` (paper §3).
  - Flow matching on a per-token denoising head (paper §4).
  - MSE objective on the predicted velocity field over a
    33-token vocabulary (paper §4).
- **Architecture:** ESM-2-650M-style Transformer encoder
  (rotary positional embeddings, 33-token vocabulary
  approximating the Pfam amino-acid alphabet, hidden=1280,
  intermediate=5120, ~20 attention heads) augmented with a
  flow-matching denoising head (sinusoidal time embedding → 2
  dense layers → `norm_out` → `out_head` vocab projection).
  576 tensors, 657.6 M parameters.
- **Training:** PyTorch Lightning 2.6.1; `amp_dtype=bf16`;
  `lr=3e-4, betas=(0.9, 0.98), weight_decay=0.01, warmup=5000,
  label_smoothing=0.1`.
- **Framework theorems instantiated:**
  - **Theorem 1** (selection ratio) — `EvidenceScaleGapMetric`.
  - **Proposition 3** (selection mechanism) — `BoundedMergeOperator`.
  - **Theorem 1 rate bound** — `adaptive_reflow/theory/rate_bound.py`.
- **Cross-references:**
  `docs/paper-draft.md` §4 protein record,
  `docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow,
  `docs/audit/lineageflow-real-forward-fix.md` (D-004),
  `docs/baseline-audit-report.md` §F.2 R3,
  `docs/CONSOLIDATED_RESULTS.md` §7.3,
  `docs/CLAIMS.md` (LineageFlow claim ledger entry).

## 8. Known Failure Modes

- **Wave 39 (PHASE-4 unblock): ckpt loading is now UNBLOCKED.**
  The 5-LOC `_install_checkpoint_compat()` shim (added by Wave 39
  Agent B) mirrors the upstream's own shim and resolves the
  `core.sampler.SamplerConfig` pickle reference. **End-to-end
  verified** by
  `tests/test_adapters/test_lineageflow.py::test_shim_unblocks_torch_load_on_real_ckpt`
  (10.5 GB ckpt loads successfully, encoder `word_embeddings`
  tensor shape = `(33, 1280)` matches the paper). The full
  forward pass now runs end-to-end in the adapter (D-004, 2026-10-12).
- **Upstream `core` runtime — now vendored (D-004).** The ckpt
  pickle references `core.sampler.SamplerConfig` (shimmed, Wave 39) and
  the upstream `core` / `models.model` / `inference.inference` modules,
  which are vendored at `data/lineageflow_upstream/`. The real forward
  pass runs; the residual limitation is that the `alpha_h` family prior
  is synthetic (§3) and the adapter uses the base-flow vector field
  rather than the upstream intervention/mutation sampler.
- **BLOCKED on data pipeline.** The tokenizer + MSA context
  fetcher for Pfam family conditioning is **MISSING**. Without
  it, the `pfam_family_cond` channel cannot be populated.
- **Pfam-family-id + sampler_cfg blob.** The conditioning cache
  preserves the per-family sampler config across rounds so
  re-inference does not re-encode. A future change to the
  sampler knob-set would require a `LINEAGEFLOW_CONFIG_HASH`
  bump (`lineageflow:cfg:v1:sha256=f0b4b25e...`).
- **Single-channel architecture.** `state_shape=(256, 33)` is
  the only exposed channel pair (`amino_acid_categorical` +
  `pfam_family_cond`); other protein-FM models (ProtBFN, Kanzi)
  use different channel vocabularies and require separate
  adapters.
- **D.5 auto-battery skips.** All 8 conformance checks skip
  because `lineageflow` requires the `core` module
  (`baseline-audit-report.md` §D.5). 25/25 hand-written tests
  pass (`baseline-audit-report.md` §D.3 row `test_lineageflow`).
- **Synthetic-mode saturation.** `family_validity` ties at
  1.0 in both arms on the synthetic velocity field; the
  framework's value-add is invisible at the saturation
  ceiling. A real-ckpt re-run has since been materialised
  (`docs/audit/r1-3seed-real-ckpt-materialize.md`): direction-consistent
  framework-WINS on 3 zero-fallback seeds, pooled `d_z = +0.110`, below
  the 0.8 STRONG bar → R1 remains PARTIAL.

---

**See also:** `adaptive_reflow/adapters/lineageflow.py`,
`docs/audit/lineageflow-real-forward-fix.md` (D-004 real forward pass),
`docs/PLUG_IN_YOUR_MODEL.md` §LineageFlow,
`docs/baseline-audit-report.md` §F.2 R3,
`tests/test_adapters/test_lineageflow.py` (22/22 pass),
`docs/CLAIMS.md` (LineageFlow claim ledger entry).
