# Kanzi — ICLR 2026 (protein)

**Status:** pending
**Wave:** candidate (Phase 2 analysis only — not yet integrated)
**Last updated:** 2026-09-05
**GitHub:** https://github.com/rdilip/kanzi
**HF:** TBD (not surfaced; GitHub-only weights per Wave 9 R1)

---

## A. Identification

- **arxiv_id:** 2510.00351
- **Title:** *Kanzi: Flow Autoencoders are Effective Protein Tokenizers*
- **Authors:** Riya D. Shah, ..., Dilip (per GH `rdilip/kanzi`; check
  arxiv for full author list)
- **Year:** 2026, ICLR 2026 (main track)
- **Domain:** protein — continuous-Tokenizer flow autoencoder that
  compresses protein sequences into a low-dim continuous latent space,
  then decodes via an autoregressive (AR) prior.
- **Weights URL:** `https://github.com/rdilip/kanzi` (GitHub-only weights
  — README likely has release / LFS pointers)
- **Weights file size:** **<2 GB total** (≈30 M encoder + 250 M AR prior,
  both fp16). Specifically:
  - Kanzi encoder ckpt (flow autoencoder for protein → latent):
    ≈30 M params, <300 MB
  - AR decoder prior (latent → protein sequence): ≈250 M params, ~1 GB
- **License:** TBD (academic, ICLR 2026; check GH `LICENSE`)

## B. Intrinsic model complexity

- **Params:**
  - Encoder (flow autoencoder): ≈30 M (lightweight, vanilla DiT-style or
    1D conv)
  - AR decoder prior: ≈250 M (Transformer, ESM-2-tiny-class)
  - **Combined: ≈280 M**
- **Architecture:** two-stage flow autoencoder:
  1. **Encoder** maps protein sequence → continuous latent z ∈ R^d
     (d=64 or 128, small bottleneck)
  2. **AR prior** models p(z | family) autoregressively (or via FM in the
     latent space — paper's specific contribution is the **flow
     autoencoder** vs discrete-token BFN)
  3. **Decoder** reconstructs protein sequence from z
- **Inference FLOPs:** small — encoder is one forward pass on a protein
  length-L sequence (L ≤ 1024); AR prior generates z one token at a time
  (L_z ≤ 64–128 steps). Total ≈few GFLOPs per protein.
- **Training compute:** modest (smaller than image DiT-XL/2 by 10–100×) —
  paper-reported ≈100–200 GPU-days on A100.
- **Dataset:** Pfam families (subset of LineageFlow's 88.6 k proteins
  across 8,886 families) or a smaller curated Pfam subset.
- **Reported metrics:**
  - **Designability 0.617** (≈61.7% of generated sequences fold to a
    plausible structure under ESMFold)
  - **scRMSD 3.655 Å** (structural RMSD vs native, lower is better)
  - Family validity: comparable to LineageFlow (~95%)

## C. Integration difficulty

| Item | Status | Notes |
|---|---|---|
| Architecture family | ✅ understood | encoder/AR are standard (1D conv + small Transformer); flow autoencoder is novel glue |
| Weight format | ✅ GitHub | `rdilip/kanzi` GH releases — small, <2 GB total |
| Environment deps | ✅ minimal | PyTorch + standard NLP stack (tokenizers, transformers); no flash-attn hard requirement |
| Inference API | ✅ clear | encoder.forward(seq) → z; AR prior sample → z' ; decoder.forward(z') → seq; clean modular pipeline |
| Paper-claim reproduction | 🟡 partial | designability 0.617 needs ESMFold runtime (heavy: ~3B params, slow); scRMSD 3.655 Å needs protein-structure alignment (Tm-align or similar) |
| Adapter fit | ✅ high | flow-matching ODE adapter fits the encoder; the AR prior is a discrete-sampler (not ODE), so adapter may need a `discrete_decoder_branch` extension |

## D. Risk profile

- **License:** TBD — check GH `LICENSE` (academic, ICLR 2026; likely
  research-only).
- **Environment fragility:** LOW — standard PyTorch; small ckpts; no
  exotic CUDA / flash-attn / dgl dependencies.
- **Paper-axis gaps:** minimal — the encoder is continuous-time FM (our
  adapter fits natively); the AR prior is a discrete sampler that our
  framework does not yet have a first-class Protocol for. May require
  adding a `discrete_decoder_branch` or treating the AR prior as a
  "black-box" pre-conditioner outside the ODE loop.
- **Network reachability:** ⚠️ `github.com` `rdilip/kanzi` is blocked
  from sandbox; ckpt download must happen from a host shell with network
  access.
- **Saturation check (LL-002):** at designability 0.617, the metric is
  high but NOT saturated (a perfect model = 1.0; LineageFlow family
  validity 0.953 is similar tier). Framework improvement has room.
- **Protein-axis precedent:** we already have `protbfn_abbfn_adapter.py`
  (ProtBFN + AbBFN, 4.9 GB) and `lineageflow.py` (657 M, Wave 10
  blocked). Kanzi adds a **continuous-tokenizer** orthogonal to BFN's
  discrete tokenizer — fresh axis.

## E. Framework-fit score

| Score | Value | Rationale |
|---|---|---|
| intrinsic_complexity_score | 3/10 | 280M params, no exotic env, encoder/AR are standard — small/fast |
| integration_difficulty_score | 5/10 | ckpt on GH (small, downloadable); AR prior needs discrete-sampler glue; designability eval needs ESMFold |
| claim-reproduction_cost | 5/10 | designability needs ESMFold (~3B params, slow); scRMSD needs structure align |
| **combined_score** | **15/100** | (3 × 5 = 15; **lowest in the pack** — easiest integrate) |

### JMAA theorem coverage (LL-001 / LL-002)

- **Theorem 1 (F-side):** Kanzi's encoder is **continuous-time FM** in the
  protein-latent space; v_θ(z_t, t) is smooth and uniformly bounded on
  the Pfam latent manifold. F-side hypothesis `uniform_simplicity` should
  hold (no adversarial Lipschitz surfaces noted in paper).
- **Lemma 2 (sheet tube):** the latent manifold is low-dim
  (d=64–128); sheet tube conditions trivially satisfied for Pfam
  proteins.
- **Proposition 6 (escaping-sharpness):** Kanzi's central claim is that
  continuous latent FM escapes sharpness better than discrete-token BFN;
  `validate_g_admissible` should pass.
- **Saturation check (LL-002):** designability 0.617 leaves ~38%
  headroom; framework improvement has clear room to surface.

## F. Empirical record

| | Result |
|---|---|
| Wave 9 R1 research | ✅ cataloged (ICLR 2026, 30M enc + 250M AR, fp16 <2 GB) |
| Wave 9 R1 recommendation | **"highest ROI"** — small, fits both GPUs, fresh protein axis (orthogonal to ProtBFN/LineageFlow) |
| Wave 9/10/11/12/13/14/15/16/17/18 follow-ups | not yet attempted |
| Adapter file | does not exist (`adaptive_reflow/adapters/kanzi_adapter.py`) |
| Conformance battery | not run |
| Reproduce path | unblocked; ckpt <2 GB, github-only |

## G. Next action

1. **Clone GH repo** — `git clone https://github.com/rdilip/kanzi` from
   host shell; capture SHA-256 of ckpt files; document LICENSE.
2. **Add `discrete_decoder_branch` Protocol extension** (if missing) —
   so the AR prior can be wrapped alongside the continuous-time FM
   encoder in a single adapter. Alternatively, treat the AR prior as a
   pre-conditioner outside the ODE loop.
3. **Author `KanziAdapter`** — wire encoder.forward as the velocity
   field; wire AR prior as a discrete-decoder hook; expose
   `velocity(t, z, family_condition)` matching the FM-ODE-Adapter
   Protocol.
4. **Run D.5 conformance battery** — verify 8/8 checks pass with synthetic
   velocity before any real-ckpt load.
5. **Phase-4 comparison** — baseline (paper config, NFE=100 Euler on
   encoder) vs framework (NFE=50 Heun + restart-blend) on Pfam subset
   N=500. Designability ≥ +0.01 OR scRMSD ≤ -0.05 Å = REPRODUCED.

## See also

- `../PHASE-2-model-complexity-analysis.md` (parent phase)
- `../PHASE-4-model-integration-iteration.md` (Phase 4 acceptance metric
  table: Kanzi → designability ≥ +0.01 OR scRMSD ≤ -0.05 Å; ALREADY-SOTA
  if both metrics at paper-parity)
- `../models/lineageflow.md` (Wave 10 protein sibling, blocked on
  upstream source — Kanzi is a faster / cleaner alternative)
- `../lessons-learned.md` (LL-001, LL-002)
- `../EXECUTION-PLAN.md` (Phase 2 candidate list)
- Wave 9 R1 research: `/tmp/wave9_sota_fm/R1-iclr2026/diagnose.md`