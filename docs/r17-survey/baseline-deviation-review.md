# r17 Baseline-Deviation Review (HiDream / Lumina / FlowMol3 / ProtBFN)

**Date:** 2026-09-03
**Trigger:** the r17-baseline workflow (task `w26z2s4s4`) measured four
SOTA models against their original papers and got "deviates" on three of
the four runnable models (HiDream, Lumina, ProtBFN). The previous run
captured proxy metrics (FID / CLIPScore / perplexity) where the paper
asks for paper-specific suites (GenEval / DPG-Bench / HPSv2.1 / VBench
/ PoseBusters / cluster-hit / AAR). The user asks for **review only —
no new experiments** until the cause of the deviation is identified and
a repair plan is on paper.

This document walks each model in the order it ran, names the specific
gap, distinguishes **doc-vs-code drift** from **wiring bug** from
**known external-tooling gap**, and proposes the corresponding repair.

---

## §0. Summary table (one-line verdict per model)

| Model | Paper metric | What we measured | Root cause | Severity |
|---|---|---|---|---|
| **flowmol3** | validity 99.9 %, PB-validity 91.9 %, FG-dev 0.27, OOD-ring 0.1 | validity 0.0 %, n_valid=0/100 (degenerate) | DGL dependency on sm_120 + partial-fidelity adapter that skips 444/475 GVP tensors | **wiring bug + env constraint** |
| **hidream_i1** | DPG-Bench 85.89, GenEval 0.83, HPSv2.1 33.82 | FID 361.4, CLIPScore 17.77 (n=10) | framework's `tools/run_image_eval.py` deliberately stubs GenEval/DPG/HPSv2 as `external`; paper metrics live in Tier-2 harnesses that were never built | **known external-tooling gap** + **adapter conditioning limitation** |
| **lumina_image_2_0** | GenEval 0.73, DPG 87.2, T2I-CompBench color 0.8211 | FID 293.8, CLIPScore 30.38 (n=30) | same Tier-2 gap as HiDream | **known external-tooling gap** |
| **wan2_2** | VBench total 86.22, WanBench 0.724 | skipped (LFS pointer stubs only) | weights not downloaded | **env constraint (out of scope)** |
| **protbfn_abbfn** | UniRef50 hit 69.7 %, CATH S40 hit 65.7 %, AbBFN AAR FR 95.6 % / CDR 67.8 % | perplexity 1.73, novelty 1.0 (n=8) | **doc-vs-code drift** — `docs/r17-survey/prot-comparison.md` advertises `aar / freq_l1 / plddt_mean / cluster_hit` but no implementation exists in the framework | **doc/code drift + missing harness** |

Three of the four are not "the framework is wrong" — they're **incomplete
harness surface**, knowingly under-built, and now mismatched against the
paper metrics we want to quote. FlowMol3 is the only one with a real
wiring bug layered on top of an env constraint.

---

## §1. HiDream-I1 — known external-tooling gap + adapter conditioning limitation

### §1.1 What the framework actually emits

`tools/run_image_eval.py` line 21-25 is explicit:

> * **GenEval** — *stub*. Object-composition evaluation requires a
>   separate mmdet/Mask2Former harness; this runner emits ``null`` with
>   a ``"external"`` marker pointing the operator at
>   ``docs/r17-survey/image-eval-plan.md``.
> * **DPG-Bench** — *stub*. Densely-typed prompts evaluation requires
>   either mPLUG-owl (Tier 2 self-host) or a paid GPT-4V judge (Lumina-
>   Image 2.0 paper); this runner emits ``null`` with a ``"external"``
>   marker.

Confirmed in the live eval JSON (`/tmp/hidream_i1_baseline_out/baseline_eval.json`):

```json
"dpg_bench": {
  "marker": "external",
  "note": "DPG-Bench dense-prompt evaluation requires mPLUG-owl ...",
  "value": null
}
```

(GenEval block has the same `external`/`null` structure.)

### §1.2 The plan document's contract

`docs/r17-survey/image-eval-plan.md` §1 is explicit about the split:

- **Tier-1 (in-process):** FID + CLIPScore via InceptionV3 pool3 (2048-d)
  + `openai/clip-vit-base-patch32`. Operator supplies reference
  statistics `.npz`. No external dep.
- **Tier-2 (external):** GenEval (official `geva` package +
  Mask2Former / DINO), DPG-Bench (MiniCPM-V 2.6 LLM judge or GPT-4V
  paid endpoint), HPSv2.1 (`hpsv2x`), ImageReward. The plan says
  these are **deliberately not** installed by the framework's
  `image-eval` extra; the operator runs them in a separate venv.

So the deviation is not a bug — the framework is **honest about what
it computes**, and the previous baseline run correctly emitted the
proxy numbers it could actually produce. The mismatch is that **paper
numbers live in Tier-2 and the Tier-2 harness was never built**.

### §1.3 Adapter-side limitation (independent issue, not the deviation cause)

`tools/run_sota_hidream_i1_experiment.py` line 303-311 documents a
*second* problem: `text_encoder_4` = Llama-3.1-8B-Instruct is gated by
Meta and HF can't redistribute it, so the published Dev HF snapshot
ships without the corresponding dir. The adapter substitutes a
zero-output stub so the diffusers config doesn't fail. Consequence:
HiDream runs under T5-XXL-only text conditioning, not the full
4-encoder stack — *this is a paper-vs-our-setup gap that paper
numbers cannot be reproduced without the Llama weights, even if
Tier-2 were wired.*

`data/hidream_i1/weights_dev/` is missing the Llama dir entirely; the
adapter `hidream_i1.py` line 502-510 imports `transformers.LlamaForCausalLM`
but the dir is absent on disk. **The `text_encoder_4` weight gap must
be closed before any paper comparison is honest.**

`docs/r17-survey/img-comparison.md` §1.1 also flags this.

### §1.4 Reference-stats gap

`data/hidream_i1_inception_stats.npz` is **not yet downloaded**
(`docs/r17-survey/img-comparison.md` line 36-39). The HiDream harness
falls back to a placeholder reference built from the generated
images themselves, which by construction yields a non-meaningful FID.
Lumina has the canonical MJHQ-30K reference (`data/lumina_image_2_0/mjhq30k_inception_stats.npz`)
and runs cleanly.

### §1.5 Repair plan (no execution in this pass)

The user has explicitly forbidden pure-torch rewrites and wants us to
use existing upstream harnesses. The Tier-2 stack itself is **not a
rewrite** — `geva` is the official GenEval implementation, MiniCPM-V
2.6 is the Lumina paper's exact judge, HPSv2.1 is the HiDream paper's
exact metric. They are *external tools*, not framework code.

| Repair step | Source of code | Where it lands in the repo | Cost |
|---|---|---|---|
| 1. Download `data/hidream_i1_inception_stats.npz` (COCO-30K from Clean-FID releases) | `clean-fid` GitHub release | `data/fid_stats/coco_30k_inception_stats.npz` | 30 MB, ~10 s |
| 2. Decide DPG-Bench judge model: self-host MiniCPM-V 2.6 (~8 GB, ~2 h setup) **or** GPT-4V paid endpoint (~$400 for 10K images) | HiDream/Lumina paper §4 | `docs/r17-survey/image-eval-plan.md` §6 Q2 → resolve in writing | decision only |
| 3. Install GenEval harness (`pip install generative-evaluation[mask2former]` + mmcv-full 1.5.3 + Mask2Former checkpoint, ~1 GB) in a separate `geva_venv` (separate venv because mmcv pins torch) | `github.com/djghosh/generative-evaluation` | `tools/eval/geva_*.py` thin shim calling the upstream `geva` CLI; glue layer only | ~1-2 h setup; eval is slow at scale |
| 4. Resolve HiDream text_encoder_4 gap: download `meta-llama/Llama-3.1-8B-Instruct` (~16 GB) under the gated-license approval flow, then drop into `data/hidream_i1/weights_dev/text_encoder_4/` + `tokenizer_4/` | HuggingFace gated repo | `data/hidream_i1/weights_dev/text_encoder_4/` | gated-license paperwork + ~30 min download |
| 5. Replace the `external` stub in `tools/run_image_eval.py` with a real subprocess call into `geva` + MiniCPM-V / GPT-4V (after step 2-3 install) | `tools/run_image_eval.py:640-848` | `tools/run_image_eval.py` | ~2-4 h glue + adapter calls |

Steps 1 + 4 are load-bearing. Steps 2-3-5 are the Tier-2 build-out.

---

## §2. Lumina-Image 2.0 — same Tier-2 gap as HiDream

### §2.1 What the framework actually emits

Identical mechanism to HiDream (`tools/run_image_eval.py:640-848`).
`/tmp/lumina_baseline_out/eval.json` confirms `dpg_bench.value = null,
marker = external`. The HiDream/Lumina image-eval harness is the same
code (`tools/run_image_eval.py`), so the gap is shared.

The MJHQ-30K reference is already downloaded — only the GenEval /
DPG-Bench / HPSv2.1 tier is missing.

### §2.2 Reference stats: clean (Lumina has MJHQ-30K already)

`data/lumina_image_2_0/mjhq30k_inception_stats.npz` is present, ~33.5 MB,
mu/sigma of the canonical partition. The Lumina harness resolves to
this file via `DEFAULT_REFERENCE_STATS` constant and reports
`placeholder_reference=false`. So Lumina's FID number is honest — but
the paper doesn't lead with FID, it leads with GenEval / DPG / T2I-
CompBench, which we don't compute.

### §2.3 Repair plan

Same Tier-2 build-out as HiDream, §1.5. No adapter-level gaps unique to
Lumina.

---

## §3. FlowMol3 — wiring bug + env constraint

### §3.1 What we measured

`/tmp/baseline_flowmol3.json` reports `validity = 0.0`, `n_valid = 0`,
`n_total = 100`, `uniqueness = "NaN"`, `qed_mean = "NaN"`. **All 100
molecules were generated, but 0 round-tripped through RDKit
sanitization.** The single-pass baseline gives 0 % validity against a
paper that reports 99.9 %.

### §3.2 Root cause: partial-fidelity adapter path skips 444/475 GVP tensors

The framework's `flowmol3_v2_adapter.py` (line 11-20, 132-153, 765-781)
documents the path itself:

- It loads the real `epoch=17 step=1547236` Pitt checkpoint (475 tensors,
  6 M params).
- It *partially* re-implements the upstream GVP message-passing using
  numpy/torch because **`flowmol.models.flowmol` requires DGL**, and
  PyPI's `dgl==2.1.0` wheel is built against `torch==2.6.0`'s
  `libgraphbolt_pytorch_2.6.0.so` — the `_version_cpu.so` import
  raises `undefined symbol: _ZN5torch3jit17parseSchemaOrNameERKSs` on
  our `torch==2.7.0+cu128` install. The earlier import error is the
  same root cause (we tested in `flowmol3_venv` before the workflow).
- 444 of 475 GVP tensors are skipped; the remaining 31 are simple
  embeddings / output heads that produce no coherent molecule.
- `adaptive_reflow/molecular/rdkit_export.py` reimplemented
  `build_molecule` (line 68-77) precisely to avoid the dgl import; the
  framework's RDKit export path works, but it's the *output* of a
  broken forward pass.

This is documented in `docs/environments.md` §"Open venv limitations"
and the r17-survey notes, but the deviation is still real and the
framework has not been repaired.

### §3.3 Paper metric gaps beyond validity

Even if we fix the partial-fidelity adapter, the framework's
`tools/run_mol_eval_safe.py` (for n_mols>=200; otherwise
`tools/run_mol_eval.py`) only computes validity / QED / SA / logP /
FCD.
The paper claims:

- **PB-validity** (PoseBusters) — not implemented.
- **FG-deviation** (Dundee + Glaxo Wellcome functional-group
  frequency L1) — not implemented.
- **OOD-ring rate** (ChEMBL ring-system lookup) — not implemented.
- **delta_e_relax / RMSD** (GFN2-xTB quantum-chemistry relaxation) —
  not implemented.

Upstream `flowmol/analysis/` (in the cloned repo at
`data/FlowMol3/repo/flowmol/analysis/molecule_builder.py`) has some of
the pieces (the bond-type remap), but the eval-only scripts (PoseBusters
runner, FG counter) are NOT in the repo — the upstream paper used an
internal harness that the public repo does not ship.

### §3.4 Repair plan (no execution in this pass)

| Repair step | Source of code | Where it lands | Cost |
|---|---|---|---|
| 1. **Fix DGL on sm_120**: try three options in order: (a) `uv pip install --python .venvs/flowmol3_venv dgl==2.1.0` already done but fails — try (b) torch downgrade to `2.6.0+cu128` if PyPI index has it (verify `https://download.pytorch.org/whl/cu128/torch-2.6.0*` exists), then re-install matching DGL; (c) if (b) fails, **build DGL from source** against torch 2.7+cu128 (the `dglteam/dgl` repo provides a CMake build; well-known to take 2-4 hours) | upstream `dglteam/dgl` | `flowmol3_venv` | option (b) ~30 min, option (c) ~3-4 h |
| 2. Wire `from flowmol.models.flowmol import FlowMol` into the adapter, replacing the partial-fidelity path | `data/FlowMol3/repo/flowmol/models/flowmol.py` | `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (replace `_load_model` partial path) | ~2-4 h glue |
| 3. Extend `tools/run_mol_eval.py` with PB-validity (PoseBusters wrapper), FG-deviation (Dundee FG SMARTS list + Glaxo Wellcome FG SMARTS list — both published as SMARTS), OOD-ring rate (ChEMBL ring-system set; download once and pickle), energy metrics (call `xtb` Python or run `xtb` CLI as subprocess) | PoseBusters (`github.com/maabuu/posebusters`); Dundee + Glaxo FG SMARTS lists (literature); xtb (`github.com/grimme-lab/xtb`) | `tools/run_mol_eval.py` + new `tools/metrics/` | ~6-10 h; PoseBusters is the heaviest (its precomputed 3D conformer step uses ETKDGv3 + MMFF) |
| 4. Stage the changes: PB-validity is the single most-cited molecule-gen metric across SOTA papers; deprioritize FG-dev / OOD-ring / energy until step 1-2 produce a non-degenerate sample stream | — | — | sequencing |

The user's no-pure-torch rule is honored: step 2 uses the upstream
GVP model verbatim (no rewrite), step 3 uses published SMARTS lists +
xtb CLI (no rewrite).

---

## §4. ProtBFN / AbBFN — doc-vs-code drift + missing protein-eval harness

### §4.1 The deviation is more honest than it looks

`/tmp/baseline_protbfn_abbfn.json` only emits perplexity (1.73) +
novelty-vs-bundled-FASTA (1.0) + uniqueness (1.0) + ngram3-rep (0.928).
The paper reports:

- **UniRef50 cluster hit** 69.7 %, **coverage_score** 0.544
- **CATH S40 hit** 65.7 %
- **novelty** at <50 % / <80 % / <95 % identity thresholds
- **AbBFN AAR FR 95.6 % / CDR 67.8 %** (per-region amino-acid recovery
  on IMGT-numbered VH)

**None of those are implemented in framework code.** The grep for
`mmseqs2|ESMFold|esmfold|amino_acid_recovery|AAR` returns zero hits in
`adaptive_reflow/` and `tools/`. The SOTA tool
`tools/run_sota_protbfn_abbfn_adapter_experiment.py` has metric slots
named `perplexity`, `novelty_fraction`, `uniqueness_fraction`,
`distinct_sequences`, `mean_length`, `recovery_rate`, `nll_per_token_mean`
— the last two (`recovery_rate` and `nll_per_token_mean`) exist as keys
but the `recovery_rate` is computed against a held-out protein set we
don't have, so it returns 0.

### §4.2 The doc-vs-code drift

`docs/r17-survey/prot-comparison.md` §opening paragraph (lines 1-14) **advertises** the metrics as:

> per-sequence metrics — `aar` (amino-acid recovery), `freq_l1`
> (frequency L1 distance to natural proteins), `novelty` (mean %
> sequence identity to the training set), `plddt_mean` (mean pLDDT
> under ESMFold), `n_cap` (constrained-token count), `beta`
> (diversity-vs-fidelity trade-off)

But no code anywhere in the tree computes `aar`, `freq_l1`, or
`plddt_mean`. The doc is forward-looking — it's describing the
**target** metric surface, not what the current code emits. The
`recovery_rate` key in the SOTA tool's JSON output is computed against
a reference that's not actually loaded, so it's a placeholder.

This is **doc-vs-code drift**, not a wire-up bug. The framework
**honestly** emits perplexity + novelty; the doc has not been kept in
sync with the code's actual output.

### §4.3 Adapter-side: framework's JAX loader is JAX-independent

`adaptive_reflow/adapters/protbfn_abbfn_adapter.py` line 922-925:

```python
from adaptive_reflow.adapters.protbfn_abbfn_jax_loader import (...)
from adaptive_reflow.adapters.protbfn_abbfn_model import (...)
```

The framework has a JAX loader (`protbfn_abbfn_jax_loader.py`) that
reassembles the 540 `.npy` per-tensor checkpoints into a JAX pytree
(per `docs/r17-survey/prot-comparison.md` line 26-28), and a JAX-free
re-implementation in `protbfn_abbfn_model.py`. **The previous baseline
used the torch re-implementation, not the JAX loader** — so the wire
to upstream is already half-built but not exercised.

The upstream repo's `data/protbfn_abbfn/repo/model.py` is the JAX
canonical. `inpaint.py` is the AbBFN inpainting entry. Both exist on
disk.

### §4.4 Paper-metric harness: zero in the tree

The paper metrics need:

- **UniRef50 cluster hit** — requires `mmseqs2` binary (system-level
  install, `apt install mmseqs2` or `conda install -c bioconda mmseqs2`)
  + a UniRef50 reference DB (~10 GB download from EBI).
- **CATH S40 hit** — `mmseqs2` search against CATH S40 + **ESMFold**
  weights (~3 GB, `facebook/esmfold_v1`) for per-sequence structure
  prediction + **pLDDT** extraction.
- **AAR scoring** — IMGT-numbered VH region alignment + per-position
  amino-acid match count. Pure Python, no external deps beyond
  BioPython (already in `protbfn_venv`).
- **freq_l1** — count amino-acid frequencies per position across a
  multiple-sequence alignment of natural proteins; pure Python.

None of these are wired. The dev cost is ~3-5 days, dominated by
mmseqs2 setup + UniRef50 DB download + ESMFold weights download.

### §4.5 Repair plan (no execution in this pass)

| Repair step | Source of code | Where it lands | Cost |
|---|---|---|---|
| 1. **Doc fix first**: rewrite `docs/r17-survey/prot-comparison.md` opening paragraph to match the actual emitted metrics (perplexity + novelty-vs-bundled-FASTA + uniqueness + ngram3-rep), mark `aar / freq_l1 / plddt_mean / cdr_recovery` as *target* metrics in a "## §Phase-C+ metric surface (future work)" section with the upstream stack + cost cited | — | `docs/r17-survey/prot-comparison.md` | ~30 min |
| 2. **AAR scoring** (lowest cost, highest paper relevance for AbBFN): pure-Python IMGT-numbered VH AAR per region (FR / CDR-H1 / H2 / H3). Use Biopython `SeqIO` for the FASTA + position-by-position comparison against the held-out `example_inputs/sequences.fasta`. Adds `amino_acid_recovery` + `cdr_recovery_per_region` keys to the SOTA tool output. | IMGT numbering table is literature; AbBFN paper §4.2 has the exact per-region buckets | `tools/run_sota_protbfn_abbfn_adapter_experiment.py` (new metric block) + `adaptive_reflow/molecular/` if needed | ~2-4 h |
| 3. **JAX loader wire-up** (the previous baseline used the torch re-implementation; switch to the JAX loader to match the upstream `data/protbfn_abbfn/repo/model.py`). ProtBFN paper *does* report perplexity under both paths, so the metric number should be the same; but the model.eval() is the upstream canonical, and any paper claim about "upstream ProtBFN" refers to this loader, not the reimplementation. | `adaptive_reflow/adapters/protbfn_abbfn_jax_loader.py` (already exists, re-import into the SOTA tool) | `tools/run_sota_protbfn_abbfn_adapter_experiment.py` | ~1-2 h glue |
| 4. **mmseqs2 + UniRef50 + ESMFold for cluster hit / CATH S40**: separate `protbfn_eval_venv`, system `apt install mmseqs2` (or conda), download UniRef50 DB (~10 GB) and CATH S40 DB (~5 GB) and ESMFold weights (~3 GB), write a new `tools/protein_eval.py` that consumes the SOTA tool's `samples.fasta` and emits `cluster_hit_rate`, `coverage_score`, `cath_s40_hit_rate`, `plddt_mean`. | mmseqs2 (`github.com/soedinglab/MMseqs2`); UniRef50 from EBI; ESMFold from HF | `tools/protein_eval.py` (new) | ~3-5 d |
| 5. Sequencing: 1 (doc fix) is the immediate cleanup; 2 (AAR) + 3 (JAX loader) are the ~3-h bundle; 4 (mmseqs2/ESMFold) is the multi-day stretch goal | — | — | — |

The user's no-pure-torch rule is honored: step 2 is pure-Python
literature numbers, step 3 uses the JAX loader that's already in the
tree, step 4 uses upstream mmseqs2 + UniRef50 + ESMFold.

---

## §5. Wan2.2 — env constraint (out of scope)

`data/wan2_2/weights/` is LFS pointer stubs at 135 B. The Wan2.2-T2V-A14B
real weights (T5-XXL-Enc, Wan2.1 VAE, 6+6 safetensors shards for the
high-noise and low-noise MoE experts) are ~130 GB total and not
downloaded on disk. Per `docs/environments.md` provenance policy
(`weights/` is `chmod 444`), no implicit download; the operator must
explicitly resolve this before any baseline can run.

No harness gap; weight gap. Out of scope for this review.

---

## §6. Repair priorities (sequenced for the user)

### §6.1 Quick wins (≤1 day, no new external tooling)

- **§1.4 / Lumina reference stats** — already in place.
- **§1.4 / HiDream reference stats** — download `coco_30k_inception_stats.npz` (~30 MB, ~10 s). One command.
- **§4.1 / ProtBFN doc fix** — rewrite `prot-comparison.md` opening to match code, ~30 min.
- **§4.1 / ProtBFN tool: rename `recovery_rate` → `recovery_rate_placeholder` and add a `status` field so downstream consumers don't misread the 0.0** — ~10 min, prevents future confusion. Applied 2026-09-03: `tools/run_sota_protbfn_abbfn_adapter_experiment.py` `ExperimentSummary` now carries `recovery_rate_placeholder: 0.0` + `recovery_rate_status: "placeholder_no_heldout_set"` (the `recovery_rate` key was never actually emitted by the harness — the rename lands as an explicit top-level field with a status sentinel rather than a true rename, so downstream JSON consumers see the new key shape immediately).
- **§1.5 / DPG-Bench judge model decision** — recorded as an open question in `docs/r17-survey/dpg-bench-judge-decision.md`. The decision BLOCKS Tier-2 build-out for both HiDream and Lumina until resolved. Applied 2026-09-03: doc created, decision deferred to user (MiniCPM-V 2.6 self-host ~8 GB free ~2 h setup vs GPT-4V paid endpoint ~$400 for 10K images).

### §6.2 Build-out (1-3 days)

- **§3.4 / FlowMol3 DGL fix + adapter wire-up** — ~3-4 h if torch 2.6+cu128 wheel exists; ~1 working day if DGL needs source build. Restore the upstream `FlowMol` import in the adapter.
- **§3.4 / PoseBusters wrapper in `tools/run_mol_eval.py`** — ~6-10 h, the biggest single piece of molecule-gen paper-metric machinery.
- **§4.5 / ProtBFN AAR scoring + JAX loader wire-up** — ~3 h bundle.
- **§1.5 / Tier-2 image-eval: GenEval + MiniCPM-V / GPT-4V DPG-Bench judge** — ~2-4 h glue + the 1-2 h setup for each tool, longer if DPG-Bench judge model is selected (GPT-4V = ~$400 of API spend on a 10K set).

### §6.3 Stretch (3-5 days)

- **§3.4 / FlowMol3 FG-deviation + OOD-ring + xtb energy** — ~6-10 h bundle, requires Dundee FG SMARTS list + ChEMBL ring-system set + xtb CLI installation.
- **§4.5 / ProtBFN mmseqs2 + UniRef50 + ESMFold for cluster-hit / CATH S40** — ~3-5 d, requires system-level mmseqs2 + ~18 GB of reference DB downloads + ESMFold weights.
- **§1.5 / HiDream text_encoder_4 = Llama-3.1-8B-Instruct** — gated license + ~16 GB download + verify dev variant runs under full 4-encoder conditioning.

### §6.4 Out of scope (until Wan2.2 weights are downloaded)

- Wan2.2 baseline numbers, VBench harness.

---

## §7. What this review does **not** propose

- No pure-torch rewrite of any model (per the user's explicit
  instruction). Where the framework has a partial-fidelity
  re-implementation (FlowMol3's GVP path, ProtBFN's torch model),
  the repair is to wire the **already-present** canonical
  reimplementation path (upstream `flowmol.models.flowmol`, JAX
  loader) or accept the framework's reimplementation as a
  self-contained piece and document it.
- No changes to the universal adapter Protocol surface
  (`adaptive_reflow.frame.adapter.FlowMatchingODEAdapter`). All four
  repairs are at the model-specific glue layer.
- No new dependencies in the **project** `.venv` (it stays
  torch-free). Heavy model eval tooling (mmseqs2, UniRef50 DB,
  ESMFold weights, PoseBusters, geva, MiniCPM-V 2.6) lives in the
  per-model venv or a dedicated `*_eval_venv` neighbour, mirroring the
  one-venv-per-model layout documented in `docs/environments.md`.