# Wave 88 Agent A — Kanzi framework-arm READ-ONLY audit

**Date:** 2026-09-09
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Scope:** Authoritative READ-ONLY audit of the **Kanzi framework-arm**:
(1) does the Wave 86 paper-quantity-driven β fix reach Kanzi today, and
(2) what minimal change is required to close Pitfall #5 (Kanzi framework-arm
N=1000 sweep) without re-doing the Wave 86 LineageFlow work.
**Status:** COMPLETE — fix plan authored (no code changes).

---

## 1. Audit findings (per the 4 read steps)

### 1.1 `tools/extract_ca_coords_for_kanzi.py` (Wave 80 N=1000 coord generator)

Read in full. **The extractor is NOT coupled to `KanziAdapter.solve_ode` — it
generates coords only.**

* Lines 70–96: stdlib-only PDB Cα extractor (regex over ATOM lines, no
  biotite/torch).
* Lines 104–128: deterministic `make_variants` adds Gaussian σ=0.10 Å noise
  to the reference backbone (variant 0 = unmodified, variants 1..n-1 =
  noise-perturbed).
* Lines 162–249: CLI emits one record per line as `>header\nflat_floats`
  (Kanzi-driver-compatible text format consumed by
  `tools/upstream_eval.py::run_kanzi_upstream_eval`).
* Determinism: seeded `numpy.random.default_rng(seed)` → byte-identical
  output for same seed (suitable for `--deterministic` / host_fingerprint).

**Verdict.** The extractor is a **pure data-prep** tool — it does NOT call
`KanziAdapter.solve_ode` and does NOT touch the framework solver path.
Re-use is safe for the framework-arm N=1000 sweep: the same coords file
feeds both arms (baseline DAE encode-decode vs framework multi-round
ODE solver), and the framework-arm just runs the framework's
`_solve_framework` over the same records.

### 1.2 `tools/run_real_ckpt_eval.py:_solve_framework` (Wave 86 paper-quantity-driven β fix)

Read lines 1139–1443 (the framework policy + `_solve_framework` body).

* `_make_framework_policy` (lines 1139–1286): Wave 86 Agent B Pitfall #1
  fix is **already wired**. When `paper_quantities` is supplied, the per-round
  β is driven by `PaperRatioAdaptiveScheduler` (Wave 31, paper Lemma 2/3/5).
  When `paper_quantities is None`, the legacy constant-`beta=0.5` path is
  preserved byte-identically (lines 1257–1264).
* `_compute_paper_quantities` (lines 1057–1136): Wave 86 Agent B helper.
  Looks up `profile_residual_fn` via TWO defensive paths:
  1. `caps = adapter.capabilities()` then
     `getattr(caps, "profile_residual_fn", None)`
  2. `getattr(adapter, "profile_residual_fn", None)`
* `_solve_framework` (lines 1289–1443): calls
  `pq = _compute_paper_quantities(adapter, trace, round_index=int(r))`
  then `_make_framework_policy(adapter, target_round=int(r), seed=int(seed),
  paper_quantities=pq)` then `apply_restart_distribution(endpoint, policy)`.
  This is the Wave 86 Pitfall #1 fix end-to-end.

**Verdict on the Wave 86 fix being "model-agnostic" (per Wave 86 audit plan
§3).** The fix is **structurally model-agnostic** in code shape
(generic over `adapter` / `trace`, dispatcher looks up `profile_residual_fn`
via two paths and falls back to `None` on failure). But the fix **fires the
paper-quantity-driven β path only when the adapter exposes
`profile_residual_fn`** — without that, `_compute_paper_quantities` returns
`None` and the legacy constant-β path runs (byte-stable but does NOT
exercise the Wave 86 paper-quantity-driven value-add).

### 1.3 Kanzi adapter `apply_restart_distribution` — Pitfall #1 Kanzi-specific check

Read lines 1432–1545 of `adaptive_reflow/adapters/kanzi.py`.

* Signature (line 1436): `apply_restart_distribution(self, state: StateBundle,
  policy: RestartPolicy) -> StateBundle` — matches the protocol expectation
  `(state, policy)` positional, NOT the legacy `(bundle=..., trace=...,
  policy=...)` keyword (which is exactly the bug Wave 45 Agent B / Wave 86
  Agent B closed).
* β consumption (line 1463): `beta, memory_fraction =
  memory_fraction_for(policy, ChannelName("protein_latent"))`. This reads
  the per-channel β from the Wave 86-fixed `FinalRestartPolicy.beta_by_channel`
  dict that `_make_framework_policy` constructs.
* Blend math (lines 1505–1529): `m_base = clamp(memory_fraction, 0, 1)` then
  `blended = m_base * prior_x + (1-m_base) * fresh_x` — **directly consumes
  the paper-quantity-driven β when the policy is paper-quantity-driven**;
  byte-stable under legacy β=0.5 otherwise.
* GPT-prior override (lines 1513–1529): when
  `KanziGPTPriorRestartPolicy` is wired, the per-position `m_vec` overrides
  `m_base` — this is the Wave 45 Agent F GPT-prior signal that takes
  precedence over the paper-quantity-driven β (correct: the
  `kanziGPTPrior` is a domain-specific Kanzi signal that knows the AR
  prior's confidence per-position).

**Verdict.** `apply_restart_distribution` is **paper-quantity-driven
compatible**: it consumes β from `policy.beta_by_channel["protein_latent"]`
(where the Wave 86 fix writes the paper-quantity-derived β). **No Kanzi
adapter code change required** for Pitfall #1 — only the upstream
`profile_residual_fn` signal needs to be plumbed.

### 1.4 Kanzi adapter — does it expose `profile_residual_fn`?

Grep over `adaptive_reflow/adapters/kanzi.py` and
`adaptive_reflow/universal/adapter.py`:

```
$ grep -n "profile_residual_fn" adaptive_reflow/adapters/kanzi.py
(no matches)

$ grep -n "profile_residual_fn" adaptive_reflow/universal/adapter.py
(no matches)

$ grep -rn "profile_residual_fn" adaptive_reflow/adapters/
(no matches in ANY adapter file)
```

`KanziCapabilities` (lines 1022–1056 of `kanzi.py`) extends
`AdapterCapabilities` with a fixed constructor signature — **no
`profile_residual_fn` field**. `AdapterCapabilities` itself (universal
dataclass, lines 130–260) does NOT declare `profile_residual_fn` either
(it only declares `channel_domains`, `state_shape`, `supported_channels`,
etc.).

**Verdict (load-bearing finding).** **The Kanzi adapter does NOT expose
`profile_residual_fn` via capabilities() OR as a direct attribute.**
Therefore:
* `_compute_paper_quantities(kanzi_adapter, trace, ...)` returns `None`.
* `_make_framework_policy` takes the legacy `beta=0.5` path
  byte-identically to pre-Wave 86.
* The Wave 86 paper-quantity-driven β fix is **inert for Kanzi** today.

This is the **actual gap** behind Pitfall #5 (Kanzi framework-arm N=1000
sweep "framework WORSE / TIES / noisy-band" reading). The sweep tool
  (Wave 83 Agent D) would run the framework arm with `β=0.5` for every
round — which is the legacy constant-β fallback the Wave 31 / Wave 34
paper-quantity-aware scheduler was meant to replace.

### 1.5 `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json`

Read in full. Key fields:

| Field | Value |
|---|---|
| `n_records_processed` | **200** (sweep was `--limit 200`, NOT N=1000) |
| `sweep_wallclock_s` | 492.094 (≈ 8 min on kanzi_venv CPU torch encoder) |
| `reconstruction_kabsch_rmsd_A.mean_rmsd_A` | 0.8235 Å |
| `codebook_entropy_bits` | 6.063 |
| `codebook_perplexity` | 66.85 |
| `codebook_js_distance` | 0.560 bits^0.5 |
| `codebook_utilization` | 0.131 |
| `verdict.arm` | **`"baseline_only"`** |
| `verdict.framework_arm_source` | "Wave 79 Phase 3: n=2 baseline=1.40 Å vs framework=1.67 Å (Δ=+0.27 Å inside FSQ quantisation noise band); not re-run at N=1000 here" |

**Verdict.** Confirmed: the committed N=1000 sweep file is **actually an
N=200 baseline-only sweep**. The framework-arm N=1000 sweep has **never
been run on the real Kanzi ckpt**. The Wave 79 n=2 proxy `TIES / NOISY-BAND`
reading is the only framework-arm evidence in the repo today.

### 1.6 Wave 83 phase4 final synthesis (`docs/audit/wave83-phase4-final.md`)

Read in full (357 lines). Per-paper-claim status (Wave 83 column, §3):

| Paper claim | Wave 83 status |
|---|---|
| `matched_quality_improvement` Tier 3 paper metric | **NOT SUPPORTED** — Kanzi baseline-arm N=1000 closed (5/6 metrics) but framework-arm still at n=2 proxy |
| `matched_quality_improvement` Tier 3 internal composite axis | **SUPPORTED — UNCHANGED** |
| `matched_nfe_speedup` Tier 1 | **SUPPORTED — UNCHANGED** |
| `matched_nfe_speedup` Tier 3 | **`speedup_95 = 1.0` — UNCHANGED** |
| `extends_baseline_plateau` Tier 3 paper metric | **PARTIALLY UNBLOCKED — Wave 83 closed Kanzi baseline-arm N=1000** |
| `extends_baseline_plateau` Tier 3 internal composite axis | **SUPPORTED — UNCHANGED** |
| `framework_sota` Tier 3 paper metric | **NOT SUPPORTED — UNCHANGED** |

Verdict summary (Wave 83 §10):
> "tier3_paper_metric_axis: NOT SUPPORTED overall — framework-vs-baseline
> TIES / NOISY-BAND on all 3 models at N=1000 (Kanzi n=2 proxy +
> FlowMol3 1/4 axes + LineageFlow adapter-bug closed but framework-arm
> deferred)"

**Verdict.** The Wave 83 final synthesis **explicitly acknowledges**
"framework-arm N=1000 still deferred" for Kanzi (lines 119, 122, 308, 342,
347). The Kanzi framework-arm N=1000 sweep is the only outstanding
Wave 76–78 reviewer-proof obligation in the Wave 79/80/81/82/83 Kanzi
chain.

---

## 2. Pitfall #5 (Kanzi part) — fix plan

### 2.1 Diagnosis

The Wave 86 paper-quantity-driven β fix in
`tools/run_real_ckpt_eval.py:_make_framework_policy` is **structurally
model-agnostic** but **only fires the paper-quantity-driven path when
the adapter exposes `profile_residual_fn`**. The Kanzi adapter does NOT
expose it today → the fix is **inert for Kanzi** → the framework-arm
N=1000 sweep would run with the legacy constant-β=0.5 path, producing
the same "TIES / NOISY-BAND" reading as Wave 79 n=2.

### 2.2 Fix (3 changes, ~30 LOC total — reuses Wave 86 infrastructure)

**Change 1 (Kanzi adapter, ~10 LOC)**: add a `profile_residual_fn`
property to `KanziCapabilities` (or as an instance attribute on
`KanziAdapter`). The callable must satisfy
`profile_residual_fn(x: float) -> float` so `_pq.sheet_evidence_A(...)`,
`_pq.root_cell_packing_B(...)`, and the existing Wave 86
`_compute_paper_quantities` helper can consume it.

Concretely, the Kanzi profile residual is the canonical Wave 86 example
(per `docs/audit/wave86-phase1-audit.md:399-403`):

```python
# In KanziCapabilities or KanziAdapter — additive, byte-safe
def profile_residual_fn(self, x: float) -> float:
    # Wave 86 convention: protein-latent flow is sheet-dominant at the
    # FSQ packing scale; use the same 0.5 * sin(x) profile that the
    # scheduler's _core.PaperRatioAdaptiveScheduler consumes for the
    # LineageFlow arm (per `_PAPER_QUANTITY_PROFILES["kanzi"]` in
    # tools/run_real_ckpt_eval.py:701 — already aligned).
    return 0.5 * math.sin(x)
```

This is **byte-stable** (deterministic, stdlib `math.sin`) and **matches
the per-model profile already wired in
`tools/run_real_ckpt_eval.py:_PAPER_QUANTITY_PROFILES["kanzi"]`** (line
701) — the eval tool's `for_profile(...)` materialisation already uses
this exact profile, so the fix aligns the framework-arm β with the
materialised paper-quantity snapshot (the Wave 86 invariant).

**Change 2 (Kanzi adapter tests, ~10 LOC)**: add a regression test in
`tests/test_adapters/test_kanzi.py` that:
1. Calls `kanzi_adapter.capabilities().profile_residual_fn(0.5)` and
   verifies it returns a `float`.
2. Calls `kanzi_adapter.profile_residual_fn(0.5)` (direct-attribute
   path) and verifies the same value.
3. Round-trips through `_compute_paper_quantities(kanzi_adapter,
   synthetic_trace, round_index=0)` and verifies a non-`None`
   `{"sheet_A", "packing_B", "exterior_gap"}` dict.

**Change 3 (D.4 regression vector, ~10 LOC)**: refresh the D.4 byte-stable
regression vector for `kanzi` so the **new** framework-arm trace digest
(with paper-quantity-driven β per round) is captured. The legacy
constant-β=0.5 path is preserved byte-identically when
`profile_residual_fn` is absent, so existing D.4 vectors for adapters
without the hook remain valid — only the Kanzi vector moves.

### 2.3 LOC estimate

**Total: ~30 LOC** (10 LOC Kanzi adapter + 10 LOC test + 10 LOC D.4
vector refresh). Reuses the existing Wave 86 `_compute_paper_quantities`
helper, `PaperRatioAdaptiveScheduler`, and
`_PAPER_QUANTITY_PROFILES["kanzi"]` materialisation — **no new
infrastructure**, just exposing the already-known signal on the Kanzi
adapter.

### 2.4 Why this is NOT a Wave 86 regression

The Wave 86 fix's design contract (per `docs/audit/wave86-phase1-audit.md`
§6 "MEDIUM" row, line 498): **"Adapter profile_residual_fn API — Wave 31
designs profile_residual_fn on the scheduler constructor, not on the
adapter. Adapters may not expose it yet."** with the Wave 86 mitigation:
"Step 1: check caps.profile_residual_fn AND adapter.profile_residual_fn
(defensive lookup). Step 2: if neither is present, return None and
fall back to constant β — preserves byte-stability." The fallback was
intentional for "adapters that don't expose it **yet**" (Kanzi is one
such adapter). Wave 88 closes this gap by exposing the signal — exactly
the Wave 86 plan's "Step 3: document the expected adapter surface in
docs/PLUG_IN_YOUR_MODEL.md" recommendation.

### 2.5 Pitfall #1 Kanzi-specific — verified

The Kanzi `apply_restart_distribution` (lines 1432–1545) consumes
`policy.beta_by_channel["protein_latent"]` via
`memory_fraction_for(policy, ChannelName("protein_latent"))`. The Wave 86
`_make_framework_policy` writes the paper-quantity-driven β into exactly
that dict slot. **No Kanzi adapter code change required for Pitfall #1.**
Pitfall #1 closes **automatically** once Change 1 above is in place (the
adapter exposes `profile_residual_fn` → Wave 86 `_compute_paper_quantities`
returns a non-`None` dict → Wave 86 `_make_framework_policy` produces a
`FinalRestartPolicy` with the paper-quantity-driven β → Kanzi
`apply_restart_distribution` consumes it via `memory_fraction_for(...)`).

---

## 3. Verification plan (N=1000 sweep with framework-arm REAL)

### 3.1 New sweep script

`tools/sweep_kanzi_n1000_paper_metrics.py` (Wave 83 Agent D, 165 LOC)
already runs the **baseline arm** over the N=200/1000 coords file. Add a
`--framework` flag that, when set, runs the framework arm:

* For each record (N=1000):
  1. Build initial state via
     `kanzi_adapter.build_initial_state(batch_id=rec_id, sample_id="s0")`.
  2. Call `_solve_framework(kanzi_adapter, nfe=50, seed=int(seed),
     n_rounds=3)` (the framework arm, paper-default NFE=50 per
     `DOWNSTREAM_METRICS["kanzi"]["nfe_paper_default"]`).
  3. Capture the integrated endpoint trace.
  4. Run `DAE.encode(trace.endpoint)` → `idx_BL` (or call the adapter's
     `observe_token_indices(trace)` per Wave 44 Agent B addition).
  5. Decode to AA string via `_decode_kanzi_idx_to_aa(idx_BL)` (same
     helper as Wave 83 baseline arm).
  6. Run Kabsch-aligned RMSD on the AA-reconstructed backbone.

### 3.2 Sweep invocation

```bash
# Baseline arm (Wave 83 baseline, 40 min on kanzi_venv CPU).
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/kanzi_n1000_paper_metrics \
    --limit 1000

# Framework arm (Wave 88 NEW, ~ 2× wallclock = 80 min).
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/kanzi_n1000_paper_metrics \
    --limit 1000 --framework
```

### 3.3 Output schema (additive to Wave 83 JSON)

Add a new JSON `verification_outputs/kanzi_n1000_paper_metrics_framework/kanzi_n1000_paper_metrics_framework.json`:

```json
{
  "tool": "tools.sweep_kanzi_n1000_paper_metrics",
  "model": "kanzi",
  "arm": "framework_real_ckpt",
  "n_records_processed": 1000,
  "wave88_paper_quantities_beta": "0.5 * math.sin(x) per kanzi adapter profile_residual_fn",
  "wave86_pitfall1_status": "closed (kanzi.apply_restart_distribution consumes paper-quantity-driven β)",
  "wave88_pitfall5_status": "closed (N=1000 framework-arm sweep run on real Kanzi ckpt)",
  "reconstruction_kabsch_rmsd_A": {
    "mean": <float>,
    "min": <float>,
    "max": <float>,
    "std": <float>
  },
  "codebook_entropy_bits": <float>,
  "codebook_perplexity": <float>,
  "codebook_js_distance": <float>,
  "codebook_utilization": <float>,
  "framework_vs_baseline_delta_angstrom": <float>,
  "verdict": "<TIED_AT_FSQ_STEP | FRAMEWORK_IMPROVES | FRAMEWORK_REGRESSES | TIES_NOISY_BAND>"
}
```

### 3.4 Per-paper-claim status (expected after Wave 88)

| Paper claim | Wave 83 status | Wave 88 expected status |
|---|---|---|
| Kanzi `matched_quality_improvement` Tier 3 paper metric | NOT SUPPORTED | **PARTIAL** — Wave 88 closes framework-arm N=1000; verdict = TIES / NOISY-BAND inside FSQ step ≈ 0.5 Å (consistent with Wave 79 n=2 proxy +1.40 vs +1.67 Å). Internal composite (Wave 52, +0.1695) remains SUPPORTED. |
| Kanzi `extends_baseline_plateau` Tier 3 paper metric | PARTIALLY UNBLOCKED | **UNBLOCKED — Wave 88 closes framework-arm N=1000** |
| Kanzi `framework_sota` Tier 3 paper metric | NOT SUPPORTED | **NOT SUPPORTED — UNCHANGED** (FSQ quantisation at 0.5 Å step is a structural SOTA ceiling, framework cannot improve past it on the Kanzi protein-axis) |

---

## 4. Risk + mitigation

| Risk | Mitigation |
|---|---|
| `profile_residual_fn` value mismatch with `_PAPER_QUANTITY_PROFILES["kanzi"]` → β diverges from eval-tool snapshot | Use the SAME `0.5 * math.sin(x)` profile in both places (already aligned in §2.2 Change 1) |
| D.4 byte-stable regression breaks when Kanzi vector moves | Refresh D.4 vector for Kanzi (Change 3); D.4 already covers adapter digests per round |
| N=1000 sweep wallclock = ~80 min for framework arm (vs 40 min baseline) | Wallclock acceptable for Wave 88 budget; parallelisable on the kanzi_venv CPU encoder |
| FSQ step ≈ 0.5 Å is a structural SOTA ceiling — framework cannot improve past it | Document explicitly in §3.4 verdict; framework's value-add lives on the **internal composite axis** (Wave 52, +0.1695), not the paper-metric axis |

---

## 5. JSON return

```json
{
  "wave": "Wave 88 Agent A",
  "scope": "Kanzi framework-arm READ-ONLY audit + fix plan",
  "findings": {
    "pitfall_1_kanzi_specific": "VERIFIED — apply_restart_distribution consumes policy.beta_by_channel[protein_latent] which the Wave 86 _make_framework_policy populates with paper-quantity-driven β. No Kanzi adapter code change required for Pitfall #1.",
    "pitfall_5_kanzi_part": "Wave 86 fix is structurally model-agnostic but INERT for Kanzi because Kanzi adapter does NOT expose profile_residual_fn. Kanzi falls back to legacy β=0.5 path byte-identically. Fix: ~30 LOC additive (10 LOC profile_residual_fn on Kanzi adapter + 10 LOC test + 10 LOC D.4 vector refresh).",
    "wave_83_n1000_actual_n": "CONFIRMED baseline-only N=200 (committed JSON says --limit 200); framework-arm N=1000 never run on real ckpt.",
    "wave_83_phase4_verdict": "Kanzi framework-arm N=1000 explicitly acknowledged as deferred (lines 119, 122, 308, 342, 347 of wave83-phase4-final.md)"
  },
  "fix_plan": {
    "loc_estimate": 30,
    "changes": [
      "Add profile_residual_fn (0.5 * sin(x)) to KanziCapabilities or KanziAdapter (10 LOC)",
      "Add regression test in tests/test_adapters/test_kanzi.py (10 LOC)",
      "Refresh D.4 byte-stable regression vector for kanzi (10 LOC)"
    ],
    "no_new_infrastructure": true,
    "reuses": [
      "Wave 86 _compute_paper_quantities helper (tools/run_real_ckpt_eval.py:1057-1136)",
      "Wave 86 _make_framework_policy paper-quantity-driven path (tools/run_real_ckpt_eval.py:1139-1286)",
      "Wave 31 PaperRatioAdaptiveScheduler (adaptive_reflow.algorithm.scheduler)",
      "_PAPER_QUANTITY_PROFILES[kanzi] = '0.5 * math.sin(x)' materialisation (tools/run_real_ckpt_eval.py:701)"
    ]
  },
  "verification_plan": {
    "sweep_script_change": "tools/sweep_kanzi_n1000_paper_metrics.py — add --framework flag (Wave 83 Agent D 165 LOC + ~30 LOC for framework-arm path)",
    "wallclock_estimate_minutes": 80,
    "output_json": "verification_outputs/kanzi_n1000_paper_metrics_framework/kanzi_n1000_paper_metrics_framework.json",
    "expected_paper_claim_status": {
      "matched_quality_improvement_t3_paper_metric": "NOT_SUPPORTED → PARTIAL (TIES / NOISY-BAND inside FSQ step)",
      "extends_baseline_plateau_t3_paper_metric": "PARTIALLY_UNBLOCKED → UNBLOCKED",
      "framework_sota_t3_paper_metric": "NOT_SUPPORTED → NOT_SUPPORTED (FSQ ceiling structural)"
    }
  },
  "no_code_changes": true,
  "audit_doc": "docs/audit/wave88-phase1-audit.md"
}
```

## 6. Files referenced

| Path | Lines | Purpose |
|---|---|---|
| `/home/hugo/codes/flowa-multistep-reinference/tools/extract_ca_coords_for_kanzi.py` | 263 | N=1000 coord extractor (Wave 80 Agent B) — pure data-prep, NOT coupled to adapter solver |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py` | 1057–1286 | `_compute_paper_quantities` + `_make_framework_policy` — Wave 86 paper-quantity-driven β fix |
| `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py` | 1289–1443 | `_solve_framework` — Wave 86 fix end-to-end |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py` | 1022–1056 | `KanziCapabilities` — NO `profile_residual_fn` field (gap) |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/kanzi.py` | 1432–1545 | `apply_restart_distribution` — consumes `policy.beta_by_channel["protein_latent"]` (Pitfall #1 verified) |
| `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | 47 | Wave 83 N=200 baseline-only sweep (verdict: baseline_only) |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave83-phase4-final.md` | 357 | Wave 83 final synthesis — explicitly defers Kanzi framework-arm N=1000 |
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave86-phase1-audit.md` | 509 | Wave 86 fix design + MEDIUM risk row for "adapters may not expose profile_residual_fn yet" |
| `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/universal/adapter.py` | 130–260 | `AdapterCapabilities` dataclass — no `profile_residual_fn` field |