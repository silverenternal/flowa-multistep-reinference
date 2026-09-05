# LineageFlow — ICML 2026 (protein)

**Status:** **DEFERRED_unblock_5LOC_shim** (PHASE-4 active; pickle loading PASSED; numerical forward deferred on upstream `core` source clone)
**Wave:** 10 (PHASE-3 adapter) + 36 (5-LOC shim option discovered) + 39 (shim applied + 10.5 GB ckpt loads in 20s) + 40 (upstream clone + numerical forward in-flight)
**Last updated:** 2026-09-05 (Wave 40 launch)
**GitHub:** https://github.com/Jinx-byebye/LineageFlow (capital J + '-byebye' suffix; case-mismatch with HF 'jinxbye' is the Wave 9 R3 misread)
**HF:** https://huggingface.co/jinxbye/LineageFlow

---

## A. Identification

- **arxiv_id:** 2605.22252
- **Title:** *LineageFlow: Flow Matching for High-Fidelity Family-Aware Protein
  Sequence Generation*
- **Authors:** Langzhang Liang, Ming Yang, Yi Feng, Junfan Li, Shirui Pan, Yinghui
  Xu, Tianlei Ying, Yizhen Zheng, Zenglin Xu
- **Year:** 2026, ICML 2026 (poster)
- **Domain:** protein sequence generation (Pfam families)
- **Weights URL:** https://huggingface.co/jinxbye/LineageFlow
- **Weights file:** `lineageflow-rp55.ckpt` — **9.788 GB on disk**
  (NOT "sub-GB" as Wave 9 R3 reported)
- **License:** TBD (not in Wave 9 R3; check HF metadata)

## B. Intrinsic model complexity

- **Params:** 657.6 M (state_dict total: 657,627,337)
- **Architecture:** ESM-2-650M-style Transformer (rotary embeddings, 33-token vocab
  ≈ Pfam amino acid alphabet, hidden=1280, intermediate=5120, ~20 attention
  heads) + flow-matching head (time_emb + norm_out + out_head)
- **State dict:** 576 tensors, 33-token vocab, ESM-2 architecture
- **Training:** PyTorch Lightning 2.6.1; amp_dtype=bf16; lr=3e-4, betas=(0.9, 0.98),
  weight_decay=0.01, warmup=5000, label_smoothing=0.1
- **Dataset:** Pfam families (88.6 k proteins across 8,886 families per paper)
- **Reported metric:** 95.3% family validity

## C. Integration difficulty (the FAILURES)

| Item | Status | Notes |
|---|---|---|
| HF Hub reachable | ✅ yes (download succeeded) | `hf download` worked via GET |
| ckpt SHA-256 verified | ✅ matches HF metadata | f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b |
| ckpt file size | 🟡 9.788 GB | 10× larger than Wave 9 R3's "sub-GB" estimate |
| Upstream `core` source repo | 🔴 **UNREACHABLE** | GitHub not surfaced; sandbox network blocks drive.google.com, huggingface.co HEAD requests, github.com sometimes blocked |
| LineageFlow `core.sampler.SamplerConfig` class | 🔴 **MISSING** | ckpt pickle references this class; only stubbed for introspection |
| `core.sampler.*` runtime (FlowMatchingSampler / PhylogenySampler) | 🔴 **MISSING** | needed for inference |
| `core.flow_model.*` forward / flow_step | 🔴 **MISSING** | needed for forward pass |
| Data pipeline (tokenizer + MSA context fetcher) | 🔴 **MISSING** | needed for Pfam family conditioning |
| ckpt storage shape | ✅ understood | encoder (568 tensors) + time_emb (4) + norm_out (2) + out_head (2) = 576 |

## D. Risk profile

- **License:** TBD — must check HF model card
- **Environment fragility:** **HIGH** — the ckpt is a PyTorch Lightning checkpoint
  with class references that need a complete `core` package. The HF Hub README
  does not include a "how to load" example. Without the source repo, the ckpt
  is useless.
- **Paper-axis gaps:** none known (no institutional claims), but cannot verify
  without running the real model
- **Network reachability:** ⚠️ HF Hub `hf download` works, but `WebFetch` HEAD
  requests time out. GitHub not reachable from sandbox. Drive.google.com blocked.

## E. Framework-fit score

| Score | Value | Rationale |
|---|---|---|
| intrinsic_complexity_score | 6/10 | 657M params, ~3.5 GB bf16, ESM-2 backbone — middleweight |
| integration_difficulty_score | 9/10 | upstream `core` source missing → adapter cannot run real model |
| claim-reproduction_cost | 9/10 | paper baseline 95.3% family validity needs real forward pass |
| **combined_score** | **54/100** | easy model BUT hard integration = blocked |

## F. Empirical record (Wave 10)

| | Result |
|---|---|
| Wave 10 setup | **BLOCKED** (upstream `core` source unreachable) |
| Wave 10 adapter | **OK** (22/22 tests pass on CPU in 0.70s) |
| Wave 10 comparison | **TIE** (family_validity 1.0 vs 1.0, delta=0%, but synthetic shim — not real model) |
| Claim verdict | **partially_supported** (real-ckpt verdict open) |
| Commit | `1cda977` (7 files, +3026 lines) |
| Reproduce path | unblocked; needs GitHub access to `core` source |

### What worked
- Framework adapter (8-method FlowMatchingODEAdapter Protocol surface) ships
  and runs on CPU synthetic velocity field
- 22/22 tests pass in 0.70s
- LineageFlowAdapter registered in `ADAPTER_REGISTRY` under `'lineageflow'`
- Public ckpt loads and SHA-256 verifies

### What didn't work
- Cannot run a real forward pass without the upstream `core.sampler` source
- Synthetic velocity field gives family_validity=1.0 in BOTH arms, so the
  baseline-vs-framework comparison is meaningless (no signal)
- Wave 9 R3's "sub-GB" estimate was 10× wrong

## G. Next action

To unblock Wave 10 follow-up:
1. **Find LineageFlow GitHub source repo** — try `arxiv.org/abs/2605.22252` for
   code link, or contact authors, or search `github.com/LineageFlow` directly
2. **Clone source + `pip install -e .`** — get `core.sampler.SamplerConfig`
3. **Re-run Wave 10** with real forward pass; family_validity will differentiate
   baseline vs framework
4. **OR**: declare LineageFlow "design-only integration" and remove the
   adapter file (similar to Wan2.2)

## See also

- `../PHASE-2-model-complexity-analysis.md` (parent phase)
- `../lessons-learned.md` (LL-001 — ckpt+upstream source both required)
- `../STATUS.md` (current state)
- Wave 10 output: `/tmp/wave10_lineageflow/`
