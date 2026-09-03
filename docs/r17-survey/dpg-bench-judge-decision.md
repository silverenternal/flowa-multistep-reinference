# r17 DPG-Bench Judge Model Decision (HiDream + Lumina)

**Date:** 2026-09-03
**Status:** **RESOLVED (deferred with documented plan)** — both deferred
paths (MiniCPM-V 2.6 self-host and GPT-4V paid) are **prohibited by the
current user filter**; the actionable plan is the MiniCPM-V 2.6 self-host
path (gated weights) when operator access is restored, with a documented
fallback to keep the Tier-2 stub deterministic until then.

The Tier-2 image-eval build-out for **both HiDream-I1 and Lumina-Image
2.0** remains blocked at the metric level (`metrics.dpg_bench.value`
stays `null`, `marker` stays `external`); this document now records the
decision, not the build.

---

## §0. User-filter prohibition (why both deferred paths are closed)

The current repair pass operates under a strict user filter. Two
constraints from the filter are decisive for this decision:

1. **No paid API calls.** The GPT-4V paid endpoint path is **off-limits**
   in this pass. The OpenAI SDK install itself is permitted, but every
   `chat.completions.create` call against `gpt-4-vision-preview` (or any
   successor that bills the same way) is forbidden. This eliminates
   **Option B** from the actionable set for the duration of this repair
   window, regardless of cost or reproducibility trade-offs.
2. **No HF gated-weight downloads.** Downloading the `openbmb/MiniCPM-V-2_6`
   ~8 GB checkpoint is gated behind a HuggingFace access request that
   the current user filter does not authorise. The MiniCPM-V **code**
   (`git clone https://github.com/OpenBMB/MiniCPM-V`) is open-source
   and may be cloned + `pip install -e .`'d in `.venvs/dpg_venv/`, but
   `AutoModel.from_pretrained("openbmb/MiniCPM-V-2_6")` will fail until
   gated access is restored. This eliminates the **runtime** half of
   Option A in this pass; the **planning** half remains valid.

Net effect: both originally proposed paths are deferred. The
documented plan (this section) is the action that *will* land when
operator restores gated access; the fallback (below) keeps the runner
deterministic in the meantime.

This decision status is **not** a "do nothing" — it is a precise
recording of what is and is not actionable so that the Tier-2 stub at
`tools/run_image_eval.py:691-695` does not drift between today and the
moment gated access is restored.

---

## §1. Why this is blocking

DPG-Bench is one of the paper metrics for both models:

- **HiDream-I1 paper Table 1** reports `DPG-Bench 85.89`.
- **Lumina-Image 2.0 paper Table 1** reports `DPG 87.2`.

DPG-Bench is a *prompt-faithfulness* benchmark: the model is shown a
densely-typed prompt (entities, attributes, relations, system /
spatial prompts) and a multimodal judge scores whether the generated
image faithfully renders each prompt clause. It is **not** an
in-process metric like FID or CLIPScore — it requires an external
multimodal LLM judge.

`tools/run_image_eval.py` lines 691-695 / 1461-1465 currently emit the
field as `{"value": null, "marker": "external", "note": "..."}` and
point the operator at `docs/r17-survey/image-eval-plan.md` §1 Tier-2.
The Tier-2 harness itself is the document that needs to be written
next, but **we cannot write it without picking a judge model** because
the judge model changes the runtime architecture:

- Self-host MiniCPM-V 2.6 → on-prem `transformers` pipeline + a
  `ddp_inference_server.py` shim, plus vLLM serving weights.
- GPT-4V (paid) → OpenAI SDK HTTP calls + rate-limit / retry /
  JSON-schema parsing of the response.

The two paths have zero glue-code overlap. Picking one commits the
project to ~2-4 h of either build direction.

---

## §2. Option A — self-host MiniCPM-V 2.6 *(recommended when access returns)*

The Lumina-Image 2.0 paper uses MiniCPM-V 2.6 as the DPG-Bench judge.
Using the paper's exact judge means the framework's DPG-Bench number
is directly comparable to the paper's 87.2.

| Aspect | Value |
|---|---|
| **Model** | `OpenBMB/MiniCPM-V-2_6` (HuggingFace) |
| **Repo** | `https://github.com/OpenBMB/MiniCPM-V` (open-source, Apache-2.0 for code) |
| **Weights** | **gated** — requires a HuggingFace access request to `openbmb/MiniCPM-V-2_6` (~8 GB, bf16). Status: BLOCKED by user filter §0.2 until restored. |
| **Compute** | fits in a single 24 GB GPU (RTX 4090 / RTX PRO 6000); inference at ~3-5 s/image on RTX PRO 6000 bf16 |
| **Setup cost** | ~2 h: install `vllm` (or `transformers` + `torch` + `accelerate`), download weights, write a 100-line shim that takes an image + prompt and emits a 1-5 score per clause |
| **Eval cost** | 10K images x ~5 s = ~14 h wall on GPU; trivial for a single overnight run |
| **Money cost** | $0 (free model + own GPU) |
| **Reproducibility** | 100 % — the judge weights + code are pinned; the paper-parity number is reproducible from scratch by anyone with the framework + an 8 GB GPU |
| **Risk** | vLLM / MiniCPM-V version churn — version pinning the venv is required; MiniCPM-V 2.6's exact reproducibility on later patch releases is not formally verified |
| **Maintenance** | High — when the framework's `.venv` Python / CUDA changes, the MiniCPM-V venv must be rebuilt |

### §2.1 Pros

- **Paper parity.** Matches the Lumina-Image 2.0 paper's judge exactly;
  HiDream paper does not specify a judge but MiniCPM-V 2.6 is the
  de-facto community choice for DPG-Bench post-2024.
- **Zero recurring cost.** The 8 GB weights download is a one-time
  ~30 min cost; subsequent eval runs are free.
- **Reproducible.** No API-key dependency, no rate-limit variance,
  no version drift from a paid endpoint.
- **Suits the no-pure-torch rule.** MiniCPM-V is upstream code; we
  glue it, we do not rewrite it.
- **Aligns with the framework's existing pattern.** mmseqs2,
  PoseBusters, ESMFold all live in isolated venvs
  (`docs/environments.md`); MiniCPM-V 2.6 joins the same pattern.

### §2.2 Cons

- **Gated weight access required.** Cannot download today (user filter
  §0.2). Operator must file the HF access request first; ~1 business day
  for OpenBMB to approve.
- **~2 h setup.** Download weights + wire `vllm` server + write the
  per-clause scoring shim. Not hard, but not free.
- **GPU contention with HiDream-LLM / Lumina / Wan2.2 inference.**
  The image-eval Tier-2 GPU must not be shared with the model
  inference GPU at the same time, or the per-image judge latency
  blows up. If the rig only has GPU 0, Tier-2 eval needs a dedicated
  off-hours slot.
- **Local-only bug fix cost.** When MiniCPM-V 2.6 chokes on an
  unusual DPG-Bench prompt (and DPG-Bench has unusual prompts by
  design — see prompt file), the operator debugs locally with no
  vendor to escalate to.

### §2.3 Recommended install plan (when access is restored)

```bash
# 1. Create the dedicated venv (Python 3.12, mirror geva_venv recipe).
uv venv --python 3.12 .venvs/dpg_venv --seed

# 2. Clone the upstream repo (open-source code, NOT gated).
git clone https://github.com/OpenBMB/MiniCPM-V .venvs/dpg_venv/repo

# 3. Install MiniCPM-V in editable mode (code + Python deps).
.venvs/dpg_venv/bin/pip install -e ".venvs/dpg_venv/repo"

# 4. Authenticate HF + download gated weights (ONE-TIME, ~8 GB).
.venvs/dpg_venv/bin/huggingface-cli login                # paste HF token
.venvs/dpg_venv/bin/python -c \
  "from huggingface_hub import snapshot_download; \
   snapshot_download('openbmb/MiniCPM-V-2_6', \
                    local_dir='.venvs/dpg_venv/weights/MiniCPM-V-2_6')"

# 5. Smoke-test the judge (no Tier-2 batch yet — that is the shim).
.venvs/dpg_venv/bin/python -c \
  "from transformers import AutoModel; \
   m = AutoModel.from_pretrained('.venvs/dpg_venv/weights/MiniCPM-V-2_6', \
                                 trust_remote_code=True, torch_dtype='bf16'); \
   print('MiniCPM-V 2.6 loaded:', m.config.model_type)"
```

### §2.4 Recommended sdpa fallback (flash-attn build failure note)

The MiniCPM-V upstream README recommends `flash-attn` for the
attention backend. On this host (CUDA 13.2 toolkit, torch 2.7.0+cu128,
matching the GenEval install-blocker documented at
`.venvs/geva_venv/logs/install_outcome.md`), `flash-attn` source
builds fail for the same reason: the host's CUDA toolkit (13.2)
mismatches the wheel's pre-built cu128 backend.

**Decision: do not require flash-attn for the judge.** Use the
PyTorch-native `sdpa` backend (`attn_implementation="sdpa"` in the
`from_pretrained` call above). MiniCPM-V 2.6 supports `sdpa` since
the v2.5 release; the per-image judge latency delta at bf16 is
~30 % slower (~5 s/image vs ~3.5 s/image on RTX PRO 6000), well
within the Tier-2 overnight budget. This sidesteps the same CUDA
toolkit mismatch that blocks `mmcv-full` for GenEval and keeps the
`.venvs/dpg_venv/` build deterministic.

If a future operator needs the flash-attn speed-up, the build
prerequisite is the same CUDA 12.x toolchain that GenEval requires —
there is no per-package workaround, only a host-level downgrade.

### §2.5 Shim contract (when shim lands)

The new `run_dpg_bench_metric()` shim will mirror `run_geneval_metric()`
(`tools/run_image_eval.py` lines ~1230 onward) with these
differences:

- Subprocess is `python eval_dpg.py --image_dir <staged> --prompt_file
  <dpg_prompts.csv> --judge_model .venvs/dpg_venv/weights/MiniCPM-V-2_6`.
- Stdout parser maps DPG-Bench's per-clause 1-5 scores into
  `sub_scores.{entity, attribute, relation, system, spatial}` (the
  five DPG-Bench sub-scores), `value` = mean over all clauses.
- GPU is `--dpg-bench-gpu-id` (default 0); never share with HiDream-I1-Full.
- Timeout: 600 s per image-batch (DINO prompt prefill can be slow).

The shim is not written today; this contract is recorded so the
Tier-2 implementation has a one-page spec.

---

## §3. Option B — GPT-4V paid endpoint *(deferred, prohibited by user filter)*

The original DPG-Bench paper uses GPT-4V. Using GPT-4V is the
historically canonical choice.

| Aspect | Value |
|---|---|
| **Model** | OpenAI GPT-4V (gpt-4-vision-preview or successor) |
| **Weights size** | n/a (hosted) |
| **Compute** | none on our side |
| **Setup cost** | ~30 min: install `openai` SDK, write a 50-line client that hits `chat.completions` with the image as a base64 data-URL, parses the 1-5 score per clause |
| **Eval cost** | 10K images x ~$0.04/image = **~$400** for the full DPG-Bench run |
| **Money cost** | ~$400 per full eval; a single Tier-2 eval run is a meaningful line item |
| **Reproducibility** | partial — model snapshots are pinned but OpenAI's serving infrastructure is a black box; re-running in 3 months may yield slightly different scores due to silent model upgrades |
| **Risk** | Rate limits (OpenAI's Tier-2 / Tier-3 rate windows cap sustained ~10 req/s); prompt-injection risk if the DPG-Bench prompt file is treated as trusted input |
| **Maintenance** | Low — API SDK is stable, no venv rebuild |
| **Current status** | **PROHIBITED** — user filter §0.1 forbids paid API calls in this pass. SDK install is permitted; the network call is not. |

### §3.1 Pros

- **~30 min setup** (when filter is lifted). A 50-line client; no vLLM, no 8 GB download.
- **Low maintenance.** No MiniCPM-V version pin to track.
- **Historically canonical.** The DPG-Bench paper's original judge;
  any older published number can be re-derived against the same judge.
- **API rate limits are documented.** OpenAI's per-minute quotas are
  public; the eval can plan its pacing.

### §3.2 Cons

- **~$400 per full eval run.** Tier-2 builds out a metric that costs
  money to use; revisiting the metric for ablations adds up.
- **Reproducibility drift.** OpenAI silently upgrades hosted models;
  the same eval code in 3 months may yield a different number.
- **Different from the Lumina paper's exact judge.** The Lumina
  paper uses MiniCPM-V 2.6, not GPT-4V. A GPT-4V-based eval would
  not be a true apples-to-apples reproduction of the Lumina paper's
  87.2 — the Lumina paper's number is a MiniCPM-V 2.6 number.
- **API-key dependency.** Operator must hold an OpenAI key with
  payment method; not reproducible for someone without one.
- **Off-limits today.** User filter §0.1 closes this path for the
  current repair window.

---

## §4. Side-by-side decision matrix

| | MiniCPM-V 2.6 (self-host) | GPT-4V (paid) |
|---|---|---|
| Setup time | ~2 h | ~30 min |
| Per-eval cost (10K images) | $0 | ~$400 |
| Paper-parity for Lumina | exact | off (Lumina paper is MiniCPM-V) |
| Paper-parity for HiDream | community standard | off |
| Reproducibility | pinned weights, fully reproducible | API may drift |
| GPU contention risk | yes (Tier-2 GPU vs inference GPU) | none |
| Maintenance burden | high (venv + model pin) | low (SDK stable) |
| Vendor lock-in | none (Apache-2.0 weights) | OpenAI API key required |
| Off-hours feasibility | yes | yes |
| User-filter status (today) | **BLOCKED on gated weights**; code install OK | **PROHIBITED** (no paid calls) |
| Actionable in this pass | **No** (gated download deferred) | **No** (paid API forbidden) |

---

## §5. Recommendation *(now binding)*

The framework's existing pattern in `docs/environments.md` favors
**self-hosted open-source models in isolated venvs** (mmseqs2 for
protein eval, PoseBusters for molecule eval, ESMFold for protein
eval). MiniCPM-V 2.6 fits this pattern: free, pinned, reproducible,
no recurring cost, paper-parity for the Lumina paper's exact judge.

**Recommendation: Option A (MiniCPM-V 2.6 self-host) is the documented
plan.** The plan is **not actionable in this pass** because the gated
weights cannot be downloaded under the user filter; once the operator
restores HuggingFace access (filing the OpenBMB gated request is the
single required external step), execute the install in §2.3 above and
the Tier-2 shim in §2.5. Total calendar time: ~1 business day for
gating approval + ~2 h install + ~14 h overnight eval run.

GPT-4V remains a valid fallback *only* if the operator explicitly
lifts the user filter on paid API calls AND the MiniCPM-V 2.6 plan
fails (e.g. the gating request is denied, or the host cannot fit the
~8 GB weights). Outside of that explicit override, the framework
does not authorise the GPT-4V path.

---

## §6. Documented fallback (what runs today)

Until gated access is restored **and** the §2.3 install completes,
the runner must emit a **byte-stable** stub for DPG-Bench so:

- Downstream consumers (`tools/run_image_eval.py` callers,
  `data/<model>/eval_report.json` readers) see a consistent schema
  with `value: null, marker: "external"`.
- The operator can grep for `marker: "external"` to know which Tier-2
  metrics are still deferred.
- The decision history is preserved in this document, not in the
  runtime stub.

### §6.1 Stub contract (in place today)

```json
{
  "dpg_bench": {
    "value": null,
    "marker": "external",
    "note": "DPG-Bench dense-prompt evaluation requires mPLUG-owl (Tier 2 self-host) or GPT-4V (paper); see docs/r17-survey/image-eval-plan.md",
    "decision_doc": "docs/r17-survey/dpg-bench-judge-decision.md",
    "decision_status": "deferred_until_gated_access",
    "planned_judge": "openbmb/MiniCPM-V-2_6"
  }
}
```

### §6.2 Fallback transitions

| Trigger | Transition |
|---|---|
| Operator files the HF gated request → OpenBMB approves → operator runs `§2.3` install → `AutoModel.from_pretrained` succeeds | Tier-2 shim lands; `marker` flips to `"subprocess"` or `"ok"`; `value` becomes a real number |
| Operator explicitly lifts the user filter on paid APIs | §3 path becomes actionable; the shim is rewritten against `openai.chat.completions.create` (different glue, same wrapper interface) |
| Neither path lands | Stub persists; `metrics.dpg_bench.value` stays `null`; HiDream/Lumina paper-parity baselines remain blocked at the Tier-2 metric level |
| `mmcv-full` install also fails (already blocked — CUDA 13.2 mismatch) | Same downstream effect; GenEval is independently blocked on the same host toolchain issue |

### §6.3 Why no shim is written today

Writing the shim now would require either (a) the gated weights we
cannot download, or (b) the paid API calls the user filter forbids.
Either choice violates the filter. The shim contract in §2.5 is
recorded so the implementation has a one-page spec the day access is
restored; the actual code does not land today.

---

## §7. What is blocked until the decision lands

- `tools/eval/dpg_bench_*.py` shim — cannot start (judge model
  determines the runtime)
- `tools/run_image_eval.py:691-695` `external` marker removal —
  blocked on the shim landing
- HiDream-I1 + Lumina-Image 2.0 paper-parity baselines — blocked on
  Tier-2 metrics landing
- The `geva` (GenEval) install is independent and **not** blocked by
  this decision (GenEval uses Mask2Former, not a multimodal judge),
  but it is blocked on the host CUDA 13.2 toolkit mismatch
  (`.venvs/geva_venv/logs/install_outcome.md`) — separate issue.

---

## §8. References

- Lumina-Image 2.0 paper §4 (judge = MiniCPM-V 2.6)
- DPG-Bench paper (Hu et al. 2024) — original judge = GPT-4V
- OpenBMB MiniCPM-V repo — `https://github.com/OpenBMB/MiniCPM-V`
  (code is open-source; `openbmb/MiniCPM-V-2_6` weights are gated)
- `docs/r17-survey/image-eval-plan.md` §1 Tier-2 — harness contract
- `docs/r17-survey/image-eval-tier2-progress.md` §2.2 — current
  Tier-2 status (`[STUB]` until §2.3 install completes)
- `docs/r17-survey/baseline-deviation-review.md` §1.5 step 2 — this
  decision's parent item
- `docs/environments.md` — one-venv-per-model layout + the CUDA 13.2
  toolkit constraint that also blocks `flash-attn` and `mmcv-full`
  builds on this host
- `.venvs/geva_venv/logs/install_outcome.md` — companion install-attempt
  diagnosis for the same host toolchain issue
- `tools/run_image_eval.py` lines 691-695 / 1461-1465 — current
  `external` / `null` stub that the shim will replace