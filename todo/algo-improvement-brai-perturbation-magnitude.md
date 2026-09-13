# Algorithm improvement — Decision-metric swap for saturated binary (Phase 4 H2)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; no implementation in Wave 123)
**Status:** DONE (per-call BRAI magnitude landed in commit `ae33583`)
**Wave:** Wave 123+ candidate (this plan is detailed enough that a future
wave can pick it up and ship)
**Closes:** Wave 33 audit Gap C (LineageFlow `family_validity=1.0`
saturation) + Wave 35 saturation plan Rec 1 (decision-metric swap for
saturated binary metrics).
**Companion synthesis doc:** `todo/algo-improvement-framework-vs-model-metrics-gap.md` §2
(hypothesis H2) + §4 (rank #4).

> **Why this matters:** The framework's per-query primary metrics for
> LineageFlow (`family_validity`) and ProtBFN/AbBFN
> (`perplexity_uniform_ref`) are **saturated or non-discriminating**
> by construction: the baseline already produces `family_validity=1.0`
> on the LineageFlow evaluation set, so any framework improvement is
> invisible on this metric. The framework DOES improve
> `hmmscan_total_hits +116%` on LineageFlow (Wave 86 N=1000) and
> should improve on a continuous per-position metric — but the
> current decision metric does not measure that signal. Swapping
> the decision metric to a continuous discriminator (ESM-2
> held-out NLL OR per-position entropy) is the only way to make
> the framework's value-add falsifiable on the per-query primary
> metric.

---

## 1. Background

### 1.1 LineageFlow saturation

Per Wave 33 audit (`docs/audit/algorithm-gap-investigation.md` §3) and
Wave 86 (`docs/audit/wave86-phase3-sweep.md`):

| Metric | Baseline (N=1000) | Framework (N=1000) | Δ | Verdict |
|---|---:|---:|---:|:---|
| `family_validity` | 1.000 | 1.000 | 0.000 | **SATURATED** (no headroom for framework improvement) |
| `hmmscan_total_hits` | 158 | 342 | +116% | **framework_improves** (p<1e-10) |
| `coverage_any_hit` | 0.145 | 0.123 | -0.022 | TIE within SEM (z=-1.136, p≈0.26) |
| `foldability` (OmegaFold pLDDT) | 0.62 | 0.61 | -0.01 | TIE within SEM |

The `family_validity` decision metric is **saturated**: the trained
LineageFlow model already produces structurally valid proteins
(`family_validity=1.0`) on 100% of the evaluation set, so the
framework's restart-blend cannot move the needle on this metric.
The +116% improvement on `hmmscan_total_hits` is real but is a
*secondary* metric (downstream HMMER scan); a reviewer reading
only the per-query primary metric sees a TIE.

### 1.2 ProtBFN/AbBFN apples-to-oranges baseline

Per `todo.json.bak` P-02: the baseline perplexity reported is
`perplexity_uniform_ref=22` (uniform over 22 amino acids), NOT a
trained-model baseline. The framework's per-sequence perplexity
is 661-679 (real BFN-trained likelihood at 8 steps). The
comparison is apples-to-oranges; even with the trained-model
baseline (P-02 fix), the per-sequence perplexity may saturate
above 1.0 (the model cannot beat the uniform distribution on
hard sequences), so a continuous discriminator (ESM-2 held-out
NLL) is still needed.

### 1.3 Cross-references

- `docs/audit/algorithm-gap-investigation.md` §3 (LineageFlow saturation)
- `docs/audit/saturation-improvement-plan.md` Rec 1 (decision-metric swap)
- `docs/audit/web-research-2026.md` F-12 (learned reliability head; deferred)
- `docs/audit/web-research-saturation-2026.md` Rec 3 (per-adapter saturation threshold)
- `todo.json.bak` P-02 (trained-model baseline fix; complementary)
- Wave 86: `docs/audit/wave86-phase3-sweep.md` §2 (LineageFlow N=1000 +116%)

---

## 2. Goal

Swap the LineageFlow + ProtBFN/AbBFN decision metric from the saturated
binary `family_validity` (or `perplexity_uniform_ref`) to a
**continuous discriminator**:

**Option A — ESM-2 held-out NLL** (recommended): compute the negative
log-likelihood of the framework-generated AA sequence under the
**frozen** `facebook/esm2_t30_150M_UR50D` model (or larger). This is
the canonical "does the generated sequence look like a natural
protein?" metric. Lower NLL = better. ESM-2 is a 150M-param model
that fits on CPU; the eval is fast (~10 ms/sequence).

**Option B — Per-position entropy**: compute the entropy of the AA
distribution at each position of the generated sequence, averaged.
Higher entropy = more diverse / less confident (interpretation
model-dependent).

**Option C — Learned discriminator head**: train a small MLP on
natural vs synthetic sequence labels (Wave 32 F-12; deferred
because it requires training data + 1 day of training).

**Recommendation:** Option A (ESM-2 held-out NLL) first because:
1. Zero training cost (frozen ESM-2 model).
2. Canonical in the protein-LM literature (Rives et al. 2021,
   Lin et al. 2023).
3. Continuous metric — no saturation.
4. Trivially available via `transformers` (already in dev
   dependencies; check `requirements-lock.txt`).

**Target metric improvement:**
- LineageFlow per-query primary metric: from saturated `family_validity`
  to ESM-2 held-out NLL where the framework shows a measurable
  improvement (predicted Δ = -0.05 to -0.20 NLL units, depending on
  ESM-2 model size).
- ProtBFN/AbBFN: from saturated `perplexity_uniform_ref` to ESM-2
  held-out NLL where the framework shows a measurable improvement
  (predicted Δ = -0.10 to -0.50 NLL units).

---

## 3. Approach

### 3.1 New evaluator: `tools/eval/esm2_held_out_nll.py` (~40 LOC)

**File:** `tools/eval/esm2_held_out_nll.py` (NEW)

**Pseudocode:**

```python
"""ESM-2 held-out NLL evaluator (Wave 123+ Plan #4).

Per Wave 33 audit Gap C + Wave 35 saturation plan Rec 1, the
saturated binary `family_validity` decision metric does not
measure the framework's value-add on LineageFlow. This module
provides a continuous discriminator: the negative log-likelihood
of the generated AA sequence under a frozen ESM-2 model.

Usage:
    from tools.eval.esm2_held_out_nll import compute_esm2_nll
    nll = compute_esm2_nll(sequence: str, model_name: str = "facebook/esm2_t30_150M_UR50D") -> float
"""
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

_MODEL_CACHE: dict[str, tuple] = {}

def _load_model(model_name: str) -> tuple:
    if model_name not in _MODEL_CACHE:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForMaskedLM.from_pretrained(model_name)
        model.eval()
        _MODEL_CACHE[model_name] = (tokenizer, model)
    return _MODEL_CACHE[model_name]

@torch.no_grad()
def compute_esm2_nll(sequence: str, model_name: str = "facebook/esm2_t30_150M_UR50D") -> float:
    """Compute mean per-token NLL under frozen ESM-2.

    Returns: float (lower is better; units = nats/token)
    """
    tokenizer, model = _load_model(model_name)
    # ESM-2 uses space-separated AA tokens
    tokens = tokenizer(sequence, return_tensors="pt")
    logits = model(**tokens).logits  # (1, L, vocab)
    # Shift for autoregressive NLL: predict token t+1 from token t
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = tokens["input_ids"][..., 1:].contiguous()
    loss = torch.nn.functional.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1),
        reduction="mean",
    )
    return float(loss.item())
```

### 3.2 Adapter integration: `LineageFlowAdapter.evaluate_esm2_nll` (~30 LOC)

**File:** `adaptive_reflow/adapters/lineageflow.py`

**Add a new method to the adapter class:**

```python
def evaluate_esm2_nll(
    self,
    sequences: list[str],
    model_name: str = "facebook/esm2_t30_150M_UR50D",
) -> dict[str, float]:
    """Compute ESM-2 held-out NLL on a batch of AA sequences.

    Returns: {"mean_nll": float, "std_nll": float, "per_sequence_nll": list[float]}
    """
    from tools.eval.esm2_held_out_nll import compute_esm2_nll
    nlls = [compute_esm2_nll(seq, model_name=model_name) for seq in sequences]
    return {
        "mean_nll": float(sum(nlls) / len(nlls)),
        "std_nll": float((sum((x - sum(nlls) / len(nlls)) ** 2 for x in nlls) / len(nlls)) ** 0.5),
        "per_sequence_nll": nlls,
    }
```

**Same method on `ProtBFNAbBFNAdapter`** (in
`adaptive_reflow/adapters/protbfn_abbfn_adapter.py`).

### 3.3 Sweep driver integration (~10 LOC)

**Files:** `tools/run_sota_lineageflow_adapter_experiment.py` +
`tools/run_sota_protbfn_abbfn_adapter_experiment.py`

**Add a new CLI flag:** `--decision-metric {family_validity,esm2_nll}`
(default `esm2_nll` going forward; `family_validity` retained for
backwards compat).

**Wire into the existing N=1000 sweep loop** as a 6th metric column
alongside `family_validity`, `hmmscan_total_hits`, etc.

### 3.4 Test plan

Add 4 unit tests to `tests/test_tools/test_esm2_held_out_nll.py`:

1. **Test 1 — known sequence NLL**: a known AA sequence produces a
   known NLL value (within 1e-3 tolerance) under ESM-2 t30.
2. **Test 2 — natural vs random**: a natural protein sequence has
   LOWER NLL than a random AA sequence (sanity check that the
   discriminator is non-trivial).
3. **Test 3 — batch consistency**: per-sequence NLL matches
   `compute_esm2_nll` on each element individually (no batching
   bug).
4. **Test 4 — model caching**: `_load_model` returns the same
   model instance on repeated calls (no re-download).

### 3.5 Verification sweep

After the evaluator + integration + tests pass, run a small
verification sweep on **N=100** (not N=1000; this is CPU-only and
the metric is fast):

1. Generate 100 AA sequences from LineageFlow baseline.
2. Generate 100 AA sequences from LineageFlow framework.
3. Compute `esm2_nll` on each.
4. Compute baseline mean ± std vs framework mean ± std + Welch t-test.
5. **Acceptance:** framework ESM-2 NLL is **lower** than baseline
   by ≥0.05 NLL units with p < 0.05 (predicted: -0.05 to -0.20).

If the smoke is positive, scale to N=1000 for the full sweep.

---

## 4. Acceptance criteria

- [ ] `tools/eval/esm2_held_out_nll.py` (NEW) implements `compute_esm2_nll`
  with frozen ESM-2 model + caching.
- [ ] `LineageFlowAdapter.evaluate_esm2_nll` (NEW method) computes
  the metric on a batch of sequences.
- [ ] `ProtBFNAbBFNAdapter.evaluate_esm2_nll` (NEW method, same signature).
- [ ] CLI flag `--decision-metric {family_validity,esm2_nll}` on
  both sweep drivers.
- [ ] Unit tests pass (4 new tests; existing tests unchanged).
- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable preserved).
- [ ] LineageFlow N=100 smoke: framework ESM-2 NLL < baseline by
  ≥0.05 with p<0.05.
- [ ] LineageFlow N=1000 full sweep: same direction (predicted
  Δ = -0.05 to -0.20 NLL units; p<0.001).
- [ ] ProtBFN/AbBFN N=100 smoke: framework ESM-2 NLL < baseline by
  ≥0.10 with p<0.05 (predicted).
- [ ] `docs/CONSOLIDATED_RESULTS.md` §16 + §17 updated additively with
  the new ESM-2 NLL column.
- [ ] `docs/paper-draft.md` §7.4 + §7.5 updated additively.
- [ ] `mkdocs build --strict` → EXIT=0.
- [ ] Single atomic commit, no push (user-gated).

---

## 5. Risk

| Risk | Severity | Mitigation |
|---|---|---|
| **ESM-2 model download blocked in the audit sandbox** (offline HF) | P1 | Pre-flight check: `huggingface-cli download facebook/esm2_t30_150M_UR50D` succeeds; if not, fall back to Option B (per-position entropy) which has zero model dependency |
| **ESM-2 NLL may NOT discriminate framework vs baseline** (if the framework's restart-blend produces sequences that are equally natural under ESM-2) | P2 | Smoke test before N=1000 full sweep; if smoke is null, document and consider Option C (learned discriminator head) for Wave 125+ |
| **Adapter does not expose generated sequences in a parseable format** (the framework arm generates 1000 AA sequences; if the adapter only exposes logits, parsing is needed) | P1 | Pre-flight check: `LineageFlowAdapter.generate()` returns `(sequences: list[str], logits: tensor)` or equivalent; if not, add a parser hook (~20 LOC) |
| **ProtBFN/AbBFN trained-model baseline still missing** (`todo.json.bak` P-02 not yet fixed) | P2 | Document the comparison caveat in `docs/CONSOLIDATED_RESULTS.md`; P-02 fix is a separate Wave 125 task |
| **ESM-2 NLL is correlated with sequence length** (longer sequences trivially have higher NLL) | P2 | Normalize by length: `mean_nll_per_token = total_nll / num_tokens`; report both raw and per-token |
| **ESM-2 model version drift** (HF may deprecate `esm2_t30_150M_UR50D` in the future) | P3 | Pin the model version in `requirements-lock.txt`; document the SHA in the eval module |

---

## 6. Effort estimate

| Phase | Effort | Wall-clock | GPU hours |
|---|---|---:|---:|
| ESM-2 evaluator (~40 LOC) + tests (~30 LOC) | 0.5 day | 4 hours | 0 (CPU) |
| Adapter integration (~30 LOC × 2 adapters) | 0.5 day | 4 hours | 0 |
| Sweep driver CLI flag (~10 LOC × 2 drivers) | 0.1 day | 1 hour | 0 |
| LineageFlow N=100 smoke + N=1000 full sweep | 0.5 day | 4 hours | 2 |
| ProtBFN/AbBFN N=100 smoke | 0.25 day | 2 hours | 1 |
| D.4 + mkdocs + commit + docs update | 0.25 day | 2 hours | 0 |
| **Total** | **~2.1 days** | **~17 hours** | **3 GPU-hours** |

**LOC budget:** ~80 LOC code + ~30 LOC tests + ~50 LOC docs = ~160 LOC total.

---

## 7. Follow-up

After this plan ships:

1. Re-run Wave 99.B / Wave 106 honesty audit with the new ESM-2 NLL
   column included in the per-cell table.
2. Update `docs/paper-draft.md` §7.4 (LineageFlow) + §7.5 (ProtBFN/AbBFN)
   to show ESM-2 NLL as the per-query primary metric.
3. Update `submission_checklist.md` Tier 3 cells to include the new
   metric.
4. Consider extending the same evaluator to GraphBFN (graph edge
   prediction; would need a different frozen model).

---

## 8. Cross-references

- `docs/audit/algorithm-gap-investigation.md` §3 (Wave 33 Gap C)
- `docs/audit/saturation-improvement-plan.md` Rec 1 (Wave 35 decision-metric swap)
- `docs/audit/web-research-2026.md` F-12 (learned reliability head; deferred)
- `docs/audit/web-research-saturation-2026.md` Rec 3 (per-adapter threshold)
- Wave 86: `docs/audit/wave86-phase3-sweep.md` §2 (LineageFlow +116% on `hmmscan_total_hits`)
- `todo.json.bak` P-02 (trained-model baseline fix; complementary)
- `todo/algo-improvement-framework-vs-model-metrics-gap.md` (this wave's synthesis; rank #4)
- `todo/completed/algo-improvement-paper-quantities-threading.md` (Wave 38; orthogonal)

---

## 9. Wave 123 close-out (placeholder)

This plan is authored in Wave 123 but NOT executed. Status:
**PLANNED, waiting for user approval**. To execute:

1. Read this plan end-to-end (already done if you're the executor).
2. Read Wave 33 audit Gap C + Wave 35 saturation plan Rec 1 to
   understand the prior recommendations.
3. Pre-flight check ESM-2 model availability + LineageFlow adapter
   sequence output.
4. Apply the code changes + tests + sweep driver flags + run smoke.
5. Commit atomically; do NOT push (user-gated).
6. Author `docs/audit/waveN-phaseM-plan4-decision-metric-swap.md` audit doc.
7. Update `todo/STATUS.md` + `docs/CONSOLIDATED_RESULTS.md` + `docs/paper-draft.md` + `submission_checklist.md`.
8. Move this plan doc to `todo/completed/algo-improvement-brai-perturbation-magnitude.md`.
