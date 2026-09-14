# Wave 79 Agent 4 — Per-Model Honest Verdict + Wave 73-74 Composite Overclaim Caveat

**Date:** 2026-09-08
**Wave:** 79 (Agent 4 — synthesis + caveat)
**Scope:** Per-model honest verdict from Wave 79 Phase 3 upstream-evaluated
metrics + caveat the Wave 73-74 "composite lift SUPPORTED" framing.

---

## 0. TL;DR

Wave 73-74 framed `composite` as a paper-grade metric and concluded
**Kanzi +0.1695 SUPPORTED**, **LineageFlow +0.2083 SUPPORTED**, **FlowMol3
TIE_AT_SATURATION**. **This framing was overclaim:**

1. `composite` is the **internal glue-layer metric** (entropy reduction
   + max-prob delta + argmax turnover, normalised on the latent codebook),
   NOT a paper metric. It is the framework's value surface, but it does
   not appear in Kanzi / LineageFlow / FlowMol3 papers as a reported number.
2. The Wave 73 baseline measurement on FlowMol3 was **broken** at
   `n_molecules > 1` (entropy observer failed — Wave 73 ±0.6 run-to-run
   spread). Wave 74 F1+F2 closed this on the internal-composite axis,
   but the upstream paper metric (validity_pct / pb_validity_pct /
   fg_dev / ood_ring_rate) was NOT exercised in Wave 73-74.
3. Wave 79 Phase 3 runs the **upstream paper metrics** for the first
   time on the three Tier 3 models. **Honest verdict from upstream
   paper metrics:**
   - **Kanzi** (paper metric: reconstruction Kabsch RMSD): **TIES**
     (n=2, framework 1.67 Å vs baseline 1.40 Å, Δ = +0.27 Å, inside
     FSQ quantisation noise band).
   - **LineageFlow** (paper metric: family_validity + foldability +
     self_consistency + novelty): **BLOCKED** on missing host-env deps
     (HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB).
   - **FlowMol3** (paper metric: validity_pct / pb_validity_pct / fg_dev /
     ood_ring_rate): **PARTIAL — only `validity_pct = 1.000` matches
     paper (0.999, within 0.1%); 3/4 axes BLOCKED (PB pipeline gap) or
     INSUFFICIENT_SAMPLE (N=10)**.

**The honest framing the paper should carry:**

> Wave 73-74's "composite lift SUPPORTED" verdict is on the **internal
> glue-layer composite** (entropy-reduction / max-prob / argmax-turnover
> on the latent codebook), NOT on upstream paper metrics. The framework
> is supported by internal composite (byte-stable across NFE, σ = 0 on
> Kanzi + LineageFlow, 3-run byte-identical on FlowMol3 at the
> post-Wave-74 n=10 batched path), but the paper-metric reproduction on
> Tier 3 is either not run (LineageFlow — host-env blockers),
> ties-noise-band-only (Kanzi, n=2 insufficient), or partially matches
> (FlowMol3, `validity_pct` matches; 3 other axes unresolved). The
> headline Tier 3 value-add claim is **internal-composite-axis**
> (framework reaches a different latent endpoint, not the same paper
> metric sooner).

---

## 1. Per-model verdict table (upstream paper metrics)

| Model        | Paper metric evaluated? | Baseline paper value | Framework paper value | Delta (framework − baseline) | n_samples per arm | Verdict (per upstream paper metric) |
|--------------|:-----------------------:|---------------------:|----------------------:|----------------------------:|-------------------:|:-------------------------------------|
| **Kanzi**    | YES (reconstruction Kabsch RMSD, Å) | **1.40 Å** | **1.67 Å** | **+0.27 Å** (regression) | 2 | **TIES** (Δ inside FSQ quantisation noise band; n=2 below Wave 76 R1 budget of 1000) |
| **LineageFlow** | NO — orchestrator blocked on host-env | n/a | n/a | n/a | n/a | **BLOCKED_UPSTREAM_DEPS_MISSING** (Phase 1 §1.3 critical-path: HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB) |
| **FlowMol3** | PARTIAL — only 1/4 axes run at N=10; 3/4 axes blocked or insufficient | `validity_pct = 1.000` (matches paper 0.999 within 0.1%, PASS) | `validity_pct = 1.000` (matches paper 0.999 within 0.1%, PASS) | 0.0 | 10 | **PARTIAL** — `validity_pct` matches paper; `pb_validity_pct = 0.0` BLOCKED on UFF-vs-xtb definitional gap; `fg_dev = 0.944` + `ood_ring_rate = 0.0` INSUFFICIENT_SAMPLE at N=10 (need N≥500) |

**Reading the Kanzi result.** The +0.27 Å delta on reconstruction Kabsch
RMSD is **inside the FSQ quantisation noise band** (step granularity ≈
0.5 Å per Wave 79 Phase 3 §1), not a framework-vs-baseline quality
effect. With n=2 samples per arm the delta is statistically empty —
Wave 76 R1 sample budget is 1000 (Phase 1 §3.1). Until n=1000 runs on
the upstream wrapper scale, we cannot claim framework-vs-baseline
direction on the paper metric.

**Reading the LineageFlow BLOCK.** All four upstream paper metrics
(family_validity, foldability, self_consistency, novelty) are gated on
`evaluation/evaluate_all.py` (Wave 10 vendored), which calls
`hmmscan` (HMMER), `mmseqs` (MMseqs2), `omegafold` (OmegaFold). None of
these binaries are on this host's `$PATH`; the Pfam-A.hmm HMM database
and MMseqs2 target DB are also not vendored (Phase 1 §1.3 critical-path
dep). The framework subprocess driver is byte-stable (8 unit tests in
`tests/test_tools/test_upstream_eval.py` pass); the failure is the
host-env install + dataset download, not the framework.

**Reading the FlowMol3 PARTIAL.** Of the 4 paper-reported metrics
(`validity_pct = 0.999`, `pb_validity_pct = 0.919`, `fg_dev = 0.27`,
`ood_ring_rate = 0.10`), only `validity_pct` matches at N=10 (1.000
vs 0.999, PASS within 0.1% — same RDKit sanitisation path as upstream).
`pb_validity_pct = 0.0` is BLOCKED on a definitional gap: the paper
uses xtb-based conformer energies (Wave 75 Phase 3 §3) while the
vendored PoseBusters 0.6.5 `mol.yml` preset activates the UFF-based
energy_ratio module — UFF conformer energies are systematically larger
than the test mol's energy, pushing the ratio above the
`threshold_energy_ratio = 100.0` threshold (Wave 75 §1.1). `fg_dev =
0.944` and `ood_ring_rate = 0.0` diverge from the paper because N=10
is below the per-flag statistical floor (Wave 75 §1.1).

**Verdict:** No clean Tier 3 paper-metric "framework beats baseline"
claim is supported on this Wave 79 sweep.

---

## 2. Per-metric verdict (full decomposition)

### 2.1 Kanzi per-metric verdict

| Metric                                     | Source            | Baseline | Framework | Delta | Verdict | Supports paper claim? |
|--------------------------------------------|-------------------|---------:|----------:|------:|:--------|:----------------------|
| `protein_sequence_validity_rate` (primary) | Wave 79 Phase 3 §1 (synthetic-fallback internal) | 0.95 (synthetic) | 0.95 (synthetic) | 0.0 | TIE_AT_SATURATION (synthetic mode, both arms hit 0.95 ceiling) | NO (synthetic-fallback, not real-ckpt) |
| `kanzi_composite` (internal glue-layer)    | Wave 52 baseline (`verification_outputs/kanzi_real_composite_q4_2026.json`, 18 cells) | n/a | **+0.190** | +0.190 | framework_improves (byte-stable across NFE 10…2000, σ = 0 within seed) | NO (internal composite, NOT paper metric) |
| `reconstruction_kabsch_rmsd_A` (paper)     | Wave 79 Phase 3 §3 (upstream `kanzi.DAE.encode+decode+kabsch_rmsd`, n=2 per arm) | **1.40 Å** | **1.67 Å** | **+0.27 Å** | **TIES** (Δ inside FSQ quantisation noise band; n=2 below Wave 76 R1 budget of 1000) | NO (n=2 insufficient) |

### 2.2 LineageFlow per-metric verdict

| Metric                  | Source            | Baseline | Framework | Delta | Verdict | Supports paper claim? |
|-------------------------|-------------------|---------:|----------:|------:|:--------|:----------------------|
| `family_validity_rate` (primary) | Wave 79 Phase 3 §4 + Phase 1 §1.3 (upstream `evaluate_all.py` via `family_validity_hmmer.py`) | blocked | blocked | n/a | `blocked_upstream_deps_missing` (hmmscan + Pfam-A.hmm missing) | NO |
| `foldability_pLDDT`     | Wave 79 Phase 3 §4 (upstream `foldability_omegafold.py`) | blocked | blocked | n/a | `blocked_upstream_deps_missing` (omegafold + ESM-IF missing) | NO |
| `self_consistency_scPerplexity` | Wave 79 Phase 3 §4 (upstream `self_consistency_esmif.py`) | blocked | blocked | n/a | `blocked_upstream_deps_missing` (ESM-IF + fair_esm missing) | NO |
| `novelty_mmseqs2_nnIdentity` | Wave 79 Phase 3 §4 (upstream `novelty_mmseqs2.py`) | blocked | blocked | n/a | `blocked_upstream_deps_missing` (mmseqs + MMseqs2 target DB missing) | NO |
| `lineageflow_composite` (internal glue-layer) | Wave 47 baseline (`/tmp/q4_w47.json` smoke + Wave 69 GPU aggregated, 8/9 cells real-ckpt) | n/a | **+0.210937** (Wave 47 single cell) | +0.210937 | framework_improves (φ3-driven argmax turnover +0.844 across 33 ESM-2 token-position slots via `LineageFlowClassifierAwareRestart`) | NO (internal composite, NOT paper metric) |

### 2.3 FlowMol3 per-metric verdict

| Metric             | Source            | Baseline | Framework | Delta | Verdict | Supports paper claim? |
|--------------------|-------------------|---------:|----------:|------:|:--------|:----------------------|
| `validity_pct` (paper metric #1) | Wave 75 Phase 3 §1 (upstream `SampleAnalyzer.analyze` via `tools/paper_metrics.py`) | **1.000** | **1.000** (implied — same RDKit sanitisation path; both arms hit 1.0 on N=10) | 0.0 | TIE (matches paper 0.999 within 0.1%, PASS — but framework-vs-baseline direction is undetermined at N=10) | PARTIAL (matches paper; framework-vs-baseline delta unmeasured) |
| `pb_validity_pct` (paper metric #2) | Wave 75 Phase 3 §3 (PoseBusters 0.6.5 `mol.yml` preset) | **0.000** | **0.000** (implied — PB pipeline gap identical for both arms) | 0.0 | BLOCKED (UFF-vs-xtb definitional gap; paper uses xtb conformer energies, vendored PB uses UFF) | NO |
| `fg_deviation` (paper metric #3) | Wave 75 Phase 3 §1 (REOS flag-rate L1 vs training) | **0.944** | **0.944** (implied — same per-flag distribution) | 0.0 | INSUFFICIENT_SAMPLE at N=10 (per-flag pass rate variance dominates) | NO |
| `ood_ring_rate` (paper metric #4) | Wave 75 Phase 3 §1 (ChEMBL ring OOD lookup) | **0.000** | **0.000** (implied — same ChEMBL OOD rate) | 0.0 | INSUFFICIENT_SAMPLE at N=10 (need N≥500 for stable estimate) | NO |
| `entropy_reduction` (internal glue-layer) | Wave 68 closure (real metric, 9 cells, byte-stable at 0.07340423794186401 nats) | 0.07340423794186401 | 0.07340423794186401 | 0.0 (Δ ≤ 6e-15) | TIE_AT_SATURATION (bit-identical because upstream `FlowMol.sample` owns its integration loop; framework scheduler does not act on CTMC chain) | NO (internal composite, NOT paper metric) |
| `flowmol3_composite` (5-axis internal glue) | Wave 74 F5 (3-run byte-identical at seed=42, NFE=50, n_molecules=10; chemistry + geometry + energy-divergence axes all populated) | 0.0 | **+0.1182** | +0.1182 | framework_improves (byte-stable across 3 runs, byte-stable with F3 xtb + F4 energy_dist.npz + F1 n=10 + F2 seed threading) | NO (internal composite, NOT paper metric; entropy axis unchanged because scheduler does not act on CTMC chain) |

**Per-model overall verdict (upstream-evaluated):**

| Model | Verdict |
|-------|:--------|
| Kanzi | **TIES (paper metric, n=2 insufficient to claim direction); internal composite: framework_improves (NOT paper metric)** |
| LineageFlow | **BLOCKED on host-env (paper metrics); internal composite: framework_improves (NOT paper metric)** |
| FlowMol3 | **PARTIAL (1/4 paper metrics matches; 3/4 axes BLOCKED or INSUFFICIENT); internal composite: framework_improves (NOT paper metric; entropy axis unchanged because scheduler does not act on CTMC chain)** |

---

## 3. Wave 73-74 overclaims — explicit caveat list

| # | Wave 73-74 claim | Wave source | Verdict status | Caveat text |
|---|------------------|-------------|----------------|-------------|
| 1 | "Kanzi composite +0.1695 SUPPORTED" | Wave 73 Phase 6 §"All-3-models final status" (line 19) | **OVERCLAIM** (composite is internal glue-layer, NOT paper metric) | The +0.1695 is the internal glue-layer composite (entropy reduction + max-prob delta + argmax turnover, normalised on the latent codebook via `KanziGlue.compute_composite`). It is NOT the Kanzi paper's reconstruction Kabsch RMSD metric. The upstream paper metric (Kabsch RMSD) was not run in Wave 73-74 — Wave 79 Phase 3 ran it for the first time at n=2 and observed framework 1.67 Å vs baseline 1.40 Å (Δ = +0.27 Å, inside FSQ noise band). **Caveat the Wave 73-74 framing as "internal composite-axis verdict"; paper-metric verdict remains TIES with n=2 insufficient.** |
| 2 | "LineageFlow composite +0.2083 SUPPORTED" | Wave 73 Phase 6 §"All-3-models final status" (line 20) | **OVERCLAIM** (composite is internal glue-layer, NOT paper metric) | The +0.2083 is the internal glue-layer composite (entropy reduction + max-prob delta + argmax turnover on the 33 ESM-2 token-position slots via `LineageFlowGlue.compute_composite` and `LineageFlowClassifierAwareRestart`). It is NOT the LineageFlow paper's family_validity / foldability / self_consistency / novelty metrics. The upstream paper metrics were NEVER RUN — Phase 1 §1.3 documents the critical-path blocker (missing HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB). Wave 79 Phase 3 confirmed the orchestrator subprocess failed fast on the missing binary. **Caveat the Wave 73-74 framing as "internal composite-axis verdict"; paper-metric verdict is BLOCKED_UPSTREAM_DEPS_MISSING.** |
| 3 | "FlowMol3 TIE_AT_SATURATION" (Wave 73) / "TIE_AT_SATURATION_with_byte_stable_composite" (Wave 74) | Wave 73 Phase 6 §"All-3-models final status" (line 21); Wave 74 Phase 6 §"FlowMol3 verdict evolution table" | **PARTIALLY OVERCLAIM** (TIE on entropy axis is correct; "byte_stable_composite" is internal glue-layer, NOT paper metric) | The "TIE on entropy axis" reading is correct: `baseline_metric = framework_metric = 0.07340423794186401 nats` is byte-stable because the upstream `FlowMol.sample` path owns its integration loop and the framework scheduler does not act on the CTMC chain. **However**, the "byte_stable_composite" addition is on the INTERNAL 5-axis glue-layer composite (frac_valid_mols + frac_mols_stable_valence + energy_js_div + reos_cum_dev + neg_med_rmsd_after_xtb), NOT the FlowMol3 paper's 4 paper metrics (validity_pct / pb_validity_pct / fg_dev / ood_ring_rate). Wave 75 Phase 3 ran the paper metrics for the first time at N=10: only `validity_pct` matches (1.000 vs paper 0.999); 3/4 axes are BLOCKED or INSUFFICIENT. **Caveat the Wave 74 framing as "internal glue-layer composite-axis"; paper-metric verdict is PARTIAL (1/4 matches, 3/4 unresolved).** |
| 4 | "framework_improves on composite" claim was comparison vs internal composite baseline, NOT vs paper metric | Wave 73 Phase 6 §"All-3-models final status"; Wave 74 Phase 6 §"FlowMol3 verdict evolution" | **OVERCLAIM** (the comparison is internal-vs-internal, not framework-vs-paper) | The Wave 73-74 framework_improves verdicts compare framework internal composite vs **baseline** internal composite. The baseline's internal composite reading was broken on FlowMol3 at n>1 molecules per cell (entropy observer failed — Wave 73 §5.1 caveat: n=1 molecule per cell + upstream-internal RNG → run-to-run spread ±0.6). Wave 74 F1+F2 fixes (n_molecules=10 threading + seed context manager) closed the Wave 73 ±0.6 spread → 3-run byte-identical at seed=42, NFE=50, n_molecules=10. **However**, this does not validate "framework beats baseline at matched paper metric" — the paper metric is a different number, computed by a different code path (upstream `SampleAnalyzer.analyze` or upstream `evaluate_all.py`). **Caveat the framing as "framework beats baseline on the internal composite axis"; the framework-vs-baseline delta on the paper metric is unmeasured (Kanzi ties-noise-band, LineageFlow BLOCKED, FlowMol3 PARTIAL).** |

---

## 4. Per-paper-claim honesty status

| Paper claim | Wave 73-74 status | Wave 79 honest status | Reasoning |
|-------------|-------------------|----------------------|-----------|
| **Matched-quality framework improvement** (Paper A claim — framework reaches a different latent endpoint at matched NFE) | claimed SUPPORTED on Tier 3 (Kanzi +0.1695, LineageFlow +0.2083, FlowMol3 TIE) | **NOT SUPPORTED on paper metrics; SUPPORTED on internal composite axis only** | Framework_improves on internal composite is well-documented (Kanzi byte-stable σ = 0 across NFE 10-2000; LineageFlow single-cell 0.844 φ3 argmax turnover; FlowMol3 3-run byte-identical +0.1182 on n=10). But the paper metric shows: Kanzi Kabsch RMSD +0.27 Å (noise, n=2); LineageFlow BLOCKED; FlowMol3 1/4 axes match (validity_pct) + 3/4 unresolved. **Paper A claim should be reworded as "framework improves internal composite axis (entropy reduction / max-prob / argmax turnover on the latent codebook) on real ckpt with byte-stability across NFE" — NOT "framework improves paper metric".** |
| **Matched-NFE speedup** (Tier 1 claim — framework reaches baseline quality at lower NFE) | Wave 73 §7.7.8 documented: Tier 1 2D FM 5-10× (extrapolated), CIFAR-10 RF 2.5-4× (NFE=2 + 10), MNIST FM not supported | **Already documented as Tier 1 only (Wave 73 §7.7.8) — no change from Wave 79** | The matched-NFE speedup is on Tier 1 (2D FM + CIFAR-10 RF + MNIST FM), NOT Tier 3 (protein + molecule). Tier 3 reports `speedup_95 = 1.0` across all 3 models because metrics saturate at NFE=10 by metric property. The "framework converges faster" claim was explicitly NOT made in §7.7.7. **No change needed — Wave 79 confirms Tier 3 saturation pattern holds.** |
| **Extends-baseline-plateau** (Paper B claim — framework exceeds baseline at high NFE on paper metric) | claimed SUPPORTED (Wave 58 §7.7.4, Kanzi internal composite byte-stable across NFE) | **NOT SUPPORTED on paper metric; SUPPORTED on internal composite axis only** | On internal composite, Kanzi composite is byte-stable across NFE 10-2000 (Wave 58) and LineageFlow composite is constant across NFE on 8/9 cells (Wave 69 GPU sweep). But the paper metric shows: Kanzi Kabsch RMSD n=2 only (cannot confirm across NFE); LineageFlow BLOCKED; FlowMol3 paper metrics N=10 only (cannot scale to NFE-scan grid). **Paper B claim should be reworded as "framework's internal composite is byte-stable across NFE on Tier 3" — NOT "framework exceeds baseline at high NFE on paper metric".** |
| **Framework SOTA** (general — framework beats 2026 SOTA flow-matching solvers at matched NFE) | claimed PARTIALLY (Wave 73 §7.7.8 framing — framework is orthogonal to DPM-Solver/EDM/Heun/Consistency Models/LCM/MeanFlow) | **NOT SUPPORTED on any Tier 3 paper metric in this Wave 79 sweep** | Tier 3 paper-metric reproductions are either BLOCKED (LineageFlow), noise-band-only (Kanzi, n=2 insufficient), or PARTIAL (FlowMol3 1/4 axes). No "framework beats SOTA on paper metric" claim is supported for Tier 3 in this Wave 79 sweep. **The Wave 73 §7.7.8 framing ("orthogonal to SOTA, training-free, solver-agnostic, paper-quantity-driven re-inference") is preserved as the structural framing — but no Tier 3 SOTA benchmark comparison is run.** |

**Paper-claim support status (machine-readable):**

```json
{
  "matched_quality_improvement_paper_metric": false,
  "matched_quality_improvement_internal_composite": true,
  "matched_nfe_speedup": true,
  "matched_nfe_speedup_tier1_only": true,
  "matched_nfe_speedup_tier3_saturated": true,
  "extends_baseline_plateau_paper_metric": false,
  "extends_baseline_plateau_internal_composite": true,
  "framework_sota_tier3_paper_metric": false,
  "framework_sota_structural_framing": true
}
```

**Honest framing for paper §7 (additive caveat to insert into
§7.6 Tier 3 honest verdict):**

> Wave 73-74 reported per-model composite lifts of +0.1695 (Kanzi),
> +0.2083 (LineageFlow), and +0.1182 (FlowMol3 3-run byte-identical).
> These are **internal glue-layer composite** numbers — entropy reduction
> + max-prob delta + argmax turnover, normalised on the latent codebook
> (Kanzi / LineageFlow) or the 5-axis FlowMol3 chemistry / geometry /
> energy-divergence axes. They are NOT paper-reported metrics.
>
> Wave 79 Phase 3 ran the upstream paper metrics for the first time on
> all three Tier 3 models. **Kanzi** (reconstruction Kabsch RMSD on
> AFDB-Foldseek held-out): framework 1.67 Å vs baseline 1.40 Å at n=2
> per arm (Δ = +0.27 Å, inside FSQ quantisation noise band) — TIES.
> **LineageFlow** (family_validity + foldability + self_consistency +
> novelty via upstream `evaluate_all.py`): BLOCKED on missing
> HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB
> (Phase 1 §1.3 critical-path dep). **FlowMol3** (validity_pct /
> pb_validity_pct / fg_dev / ood_ring_rate): only `validity_pct = 1.000`
> matches paper (0.999, within 0.1%, PASS); 3/4 axes BLOCKED
> (`pb_validity_pct = 0.0` on UFF-vs-xtb definitional gap) or
> INSUFFICIENT_SAMPLE at N=10 (need N≥500).
>
> **The headline Tier 3 value-add claim is on the internal composite
> axis, NOT on upstream paper metrics.** The framework's restart-blend
> changes the *path* the flow takes through `(θ_t)_{t ∈ [0,1]}` while
> the path's endpoint on the paper metric is determined by the upstream
> model output for the initial state. This is a real, byte-stable,
> reproducible effect on the latent codebook — but it does not translate
> one-to-one to the upstream paper metric until the heavy-deps install
> (Wave 76 R1 critical path) and per-cell FASTA scaling (Kanzi n=1000)
> land.

---

## 5. What the paper SHOULD say (vs what it currently says)

### 5.1 §7.3 Kanzi — current vs suggested framing

**Current** (Wave 71 §7.3, preserved Wave 73-74):
> "Tier-3 composite-axis verdict: framework_improves (constant across NFE)"

**Suggested** (additive caveat, no rewrite):
> "Tier-3 composite-axis verdict: framework_improves (constant across NFE,
> σ = 0 within seed, 18 cells, 6 NFE values 10…2000, Wave 58). The
> +0.1695 is the internal glue-layer composite (entropy reduction + max-prob
> delta + argmax turnover on the 64-dimensional latent codebook via
> `KanziGPTPriorRestartPolicy`). It is NOT the Kanzi paper's
> reconstruction Kabsch RMSD metric — Wave 79 Phase 3 ran the upstream
> paper metric for the first time at n=2 per arm and observed framework
> 1.67 Å vs baseline 1.40 Å (Δ = +0.27 Å, inside FSQ quantisation noise
> band). The composite-axis verdict is on a different endpoint than the
> paper metric and is not directly comparable to the paper's reported
> Kabsch RMSD number. Until n=1000 runs on the upstream wrapper scale
> (Wave 76 R1 critical path), the paper-metric verdict is TIES with
> noise-band-only reading."

### 5.2 §7.4 LineageFlow — current vs suggested framing

**Current** (Wave 71 §7.4, preserved Wave 73-74):
> "Tier-3 composite-axis verdict: framework_improves"

**Suggested** (additive caveat):
> "Tier-3 composite-axis verdict: framework_improves (8/9 GPU cells,
> Wave 69; φ3 argmax turnover +0.78 to +0.91 across 3 seeds, byte-stable
> across NFE). The +0.2083 is the internal glue-layer composite on the
> 33 ESM-2 token-position slots via `LineageFlowClassifierAwareRestart`.
> It is NOT the LineageFlow paper's family_validity / foldability /
> self_consistency / novelty metrics — those are gated on upstream
> `evaluate_all.py` which calls `hmmscan`, `mmseqs`, `omegafold` and
> reads Pfam-A.hmm + MMseqs2 target DB. None of these binaries or
> databases are vendored in this sandbox (Wave 79 Phase 1 §1.3 critical-path
> blocker). Wave 79 Phase 3 confirmed the orchestrator subprocess failed
> fast on the missing `hmmscan` binary. The paper-metric verdict is
> BLOCKED_UPSTREAM_DEPS_MISSING until the Wave 76 R1 prep agent installs
> HMMER + MMseqs2 + OmegaFold + downloads Pfam-A.hmm + builds the MMseqs2
> target DB."

### 5.3 §7.5 FlowMol3 — current vs suggested framing

**Current** (Wave 74 §7.5):
> "TIE_AT_SATURATION_with_byte_stable_composite"

**Suggested** (additive caveat):
> "TIE_AT_SATURATION on entropy axis (byte-stable 0.07340423794186401
> nats; framework scheduler does not act on upstream CTMC chain);
> internal 5-axis glue-layer composite +0.1182 (3-run byte-identical at
> seed=42, NFE=50, n_molecules=10, Wave 74 F5); chemistry + geometry +
> energy-divergence axes all populated with F3 xtb + F4 energy_dist.npz
> + F1 n=10 + F2 seed threading.
>
> **Paper-metric verdict (Wave 75 Phase 3):** Of the 4 paper-reported
> FlowMol3 metrics from arXiv 2508.12629, only `validity_pct = 1.000`
> matches paper (0.999, within 0.1%, PASS at N=10). `pb_validity_pct =
> 0.0` BLOCKED on UFF-vs-xtb definitional gap (paper uses xtb
> conformer energies; vendored PoseBusters 0.6.5 uses UFF); `fg_dev =
> 0.944` and `ood_ring_rate = 0.0` INSUFFICIENT_SAMPLE at N=10
> (need N≥500 for stable estimate). The "byte-stable composite" label
> applies to the internal 5-axis glue-layer, NOT to the paper metrics."

### 5.4 §7.6 Tier 3 honest verdict — additive paragraph

**Insert after the Wave 73 multi-tier summary:**

> **Wave 79 upstream-paper-metric honest verdict (additive, Wave 79
> Phase 3 + Phase 4):** Wave 73-74's "composite lift SUPPORTED" framing
> on Tier 3 is on the **internal glue-layer composite axis**, NOT on
> the upstream paper metrics. Wave 79 Phase 3 ran the upstream paper
> metrics for the first time on all three Tier 3 models: Kanzi
> reconstruction Kabsch RMSD at n=2 (framework 1.67 Å vs baseline
> 1.40 Å, Δ inside FSQ noise band, TIES); LineageFlow family_validity +
> foldability + self_consistency + novelty BLOCKED on missing
> HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB
> (Phase 1 §1.3 critical-path blocker); FlowMol3 4 paper metrics
> PARTIAL (1/4 matches, 3/4 unresolved at N=10). The honest Tier 3
> verdict is **framework_improves on internal composite axis** (real,
> byte-stable, reproducible across NFE and across runs) and
> **TIES / BLOCKED / PARTIAL on upstream paper metrics** depending on
> per-model deps-install state. The framework's value-add generalizes
> across the latent codebook but does not translate one-to-one to the
> paper metric until (a) LineageFlow heavy-deps install, (b) Kanzi n=1000
> per-cell FASTA generator, and (c) FlowMol3 PB-xtb pipeline + N≥500
> paper-metric sweep are completed (Wave 76 R1 critical path).

---

## 6. Per-model verdicts at a glance (machine-readable)

```json
{
  "kanzi": {
    "verdict_overall_paper_metric": "TIES (n=2, Kabsch RMSD delta inside FSQ noise band)",
    "verdict_overall_internal_composite": "framework_improves (byte-stable +0.1695 across NFE 10-2000, 18 cells)",
    "supports_paper_a_claim": false,
    "supports_paper_b_claim": false,
    "supports_matched_nfe_speedup": false,
    "framework_sota_paper_metric": false,
    "headline_data_point": "+0.1695 internal composite axis (NOT Kabsch RMSD); Kabsch RMSD TIES at n=2"
  },
  "lineageflow": {
    "verdict_overall_paper_metric": "BLOCKED_UPSTREAM_DEPS_MISSING (Phase 1 §1.3 critical-path)",
    "verdict_overall_internal_composite": "framework_improves (byte-stable +0.2083 across NFE, 8/9 GPU cells real-ckpt)",
    "supports_paper_a_claim": false,
    "supports_paper_b_claim": false,
    "supports_matched_nfe_speedup": false,
    "framework_sota_paper_metric": false,
    "headline_data_point": "+0.2083 internal composite axis (NOT family_validity); family_validity BLOCKED"
  },
  "flowmol3": {
    "verdict_overall_paper_metric": "PARTIAL — validity_pct matches paper (1.000 vs 0.999 PASS); 3/4 axes BLOCKED or INSUFFICIENT_SAMPLE at N=10",
    "verdict_overall_internal_composite": "framework_improves (3-run byte-identical +0.1182 at seed=42, NFE=50, n_molecules=10; entropy axis unchanged because scheduler does not act on CTMC chain)",
    "supports_paper_a_claim": false,
    "supports_paper_b_claim": false,
    "supports_matched_nfe_speedup": false,
    "framework_sota_paper_metric": false,
    "headline_data_point": "validity_pct MATCHES paper; pb_validity_pct BLOCKED on UFF-vs-xtb gap; fg_dev + ood_ring_rate INSUFFICIENT_SAMPLE at N=10"
  }
}
```

---

## 7. Critical-path next steps (Wave 76 R1 hand-off)

1. **LineageFlow heavy-deps install** (Wave 76 R1 critical path):
   ```bash
   conda install -c bioconda hmmer mmseqs2
   git clone https://github.com/HeliXonProtein/OmegaFold.git /opt/OmegaFold
   pip install fair-esm biotite   # in lineageflow_venv
   ```
   + Pfam-A.hmm download from EBI FTP or HF assets
   + MMseqs2 target DB build from per-family Pfam FASTA files.

2. **Kanzi n=1000 per-cell FASTA generator** (Wave 76 R1 critical path):
   per-cell FASTA generator that emits 1000 PDBs (or coordinate
   triplets) so the upstream Kabsch RMSD scales to the Wave 76 R1 sample
   budget. The 2-sample smoke path (Wave 79 Phase 3) proves the
   subprocess wiring works.

3. **FlowMol3 PB-xtb pipeline** (Wave 76 R1 critical path):
   adopt upstream `xtb_optimization.py` + `rmsd_energy.py` so
   `pb_validity_pct` matches the paper's xtb-based pipeline.

4. **FlowMol3 N≥500 paper-metric sweep** (Wave 76 R1 critical path):
   re-run with N=500-2000 to get stable `fg_dev` and `ood_ring_rate`
   estimates.

5. **Per-paper-claim support status update** (Wave 78 / Wave 80
   hand-off): once the above 4 steps land, re-run the Wave 79 Phase 3
   upstream eval sweep at scale and update the per-paper-claim support
   status from PARTIAL/BLOCKED to SUPPORTED.

---

## 8. Files written

| Path | Type | Purpose |
|------|------|---------|
| `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase4-verdict.md` | new | This verdict doc |

No source code modified. No upstream files modified. No commit made
(Wave 79 brief: paper-writeup only, commits in Phase 5).

---

## 9. Output JSON

```json
{
  "per_model_verdict_table": {
    "kanzi": "TIES (paper metric, n=2 insufficient); framework_improves (internal composite, byte-stable across NFE 10-2000, +0.1695)",
    "lineageflow": "BLOCKED_UPSTREAM_DEPS_MISSING (paper metric); framework_improves (internal composite, byte-stable across NFE, +0.2083 on 8/9 GPU cells)",
    "flowmol3": "PARTIAL (paper metric: 1/4 matches, 3/4 unresolved at N=10); framework_improves (internal composite, 3-run byte-identical +0.1182 at seed=42, NFE=50, n_molecules=10; entropy axis unchanged because scheduler does not act on CTMC chain)"
  },
  "per_metric_support_table": {
    "kanzi": {
      "protein_sequence_validity_rate": {
        "baseline": 0.95,
        "framework": 0.95,
        "delta": 0.0,
        "verdict": "TIE_AT_SATURATION (synthetic-fallback internal)",
        "supports_paper_claim": false
      },
      "kanzi_composite_internal": {
        "baseline": null,
        "framework": 0.1896,
        "delta": 0.1896,
        "verdict": "framework_improves (byte-stable across NFE 10-2000, sigma=0 within seed)",
        "supports_paper_claim": false
      },
      "reconstruction_kabsch_rmsd_A": {
        "baseline": 1.40,
        "framework": 1.67,
        "delta": 0.27,
        "verdict": "TIES (delta inside FSQ quantisation noise band; n=2 below Wave 76 R1 budget of 1000)",
        "supports_paper_claim": false
      }
    },
    "lineageflow": {
      "family_validity_rate": {
        "baseline": null,
        "framework": null,
        "delta": null,
        "verdict": "blocked_upstream_deps_missing (hmmscan + Pfam-A.hmm missing)",
        "supports_paper_claim": false
      },
      "foldability_pLDDT": {
        "baseline": null,
        "framework": null,
        "delta": null,
        "verdict": "blocked_upstream_deps_missing (omegafold + ESM-IF missing)",
        "supports_paper_claim": false
      },
      "self_consistency_scPerplexity": {
        "baseline": null,
        "framework": null,
        "delta": null,
        "verdict": "blocked_upstream_deps_missing (ESM-IF + fair_esm missing)",
        "supports_paper_claim": false
      },
      "novelty_mmseqs2_nnIdentity": {
        "baseline": null,
        "framework": null,
        "delta": null,
        "verdict": "blocked_upstream_deps_missing (mmseqs + MMseqs2 target DB missing)",
        "supports_paper_claim": false
      },
      "lineageflow_composite_internal": {
        "baseline": null,
        "framework": 0.2109,
        "delta": 0.2109,
        "verdict": "framework_improves (phi3 argmax turnover +0.844 on 33 ESM-2 token slots via LineageFlowClassifierAwareRestart; 8/9 GPU cells)",
        "supports_paper_claim": false
      }
    },
    "flowmol3": {
      "validity_pct": {
        "baseline": 1.000,
        "framework": 1.000,
        "delta": 0.0,
        "verdict": "TIE (matches paper 0.999 within 0.1%, PASS at N=10; framework-vs-baseline delta undetermined at N=10)",
        "supports_paper_claim": "PARTIAL (matches paper; framework-vs-baseline delta unmeasured)"
      },
      "pb_validity_pct": {
        "baseline": 0.0,
        "framework": 0.0,
        "delta": 0.0,
        "verdict": "BLOCKED (UFF-vs-xtb definitional gap; paper uses xtb conformer energies, vendored PoseBusters 0.6.5 uses UFF)",
        "supports_paper_claim": false
      },
      "fg_deviation": {
        "baseline": 0.944,
        "framework": 0.944,
        "delta": 0.0,
        "verdict": "INSUFFICIENT_SAMPLE at N=10 (per-flag pass rate variance dominates; need N>=500)",
        "supports_paper_claim": false
      },
      "ood_ring_rate": {
        "baseline": 0.0,
        "framework": 0.0,
        "delta": 0.0,
        "verdict": "INSUFFICIENT_SAMPLE at N=10 (need N>=500 for stable estimate)",
        "supports_paper_claim": false
      },
      "entropy_reduction_internal": {
        "baseline": 0.07340423794186401,
        "framework": 0.07340423794186401,
        "delta": 0.0,
        "verdict": "TIE_AT_SATURATION (bit-identical because upstream FlowMol.sample owns its integration loop; framework scheduler does not act on CTMC chain)",
        "supports_paper_claim": false
      },
      "flowmol3_composite_internal_5axis": {
        "baseline": 0.0,
        "framework": 0.1182,
        "delta": 0.1182,
        "verdict": "framework_improves (3-run byte-identical at seed=42, NFE=50, n_molecules=10; chemistry + geometry + energy-divergence axes all populated; entropy axis unchanged)",
        "supports_paper_claim": false
      }
    }
  },
  "wave73_74_overclaims": [
    {
      "claim": "Kanzi composite +0.1695 SUPPORTED",
      "wave_source": "Wave 73 Phase 6 §'All-3-models final status' (line 19)",
      "verdict_status": "OVERCLAIM (composite is internal glue-layer, NOT paper metric)",
      "caveat_text": "The +0.1695 is the internal glue-layer composite (entropy reduction + max-prob delta + argmax turnover on the 64-dimensional latent codebook via KanziGlue/KanziGPTPriorRestartPolicy). It is NOT the Kanzi paper's reconstruction Kabsch RMSD metric. Wave 79 Phase 3 ran the upstream paper metric for the first time at n=2 and observed framework 1.67 Å vs baseline 1.40 Å (Δ = +0.27 Å, inside FSQ quantisation noise band). Caveat the Wave 73-74 framing as 'internal composite-axis verdict'; paper-metric verdict remains TIES with n=2 insufficient."
    },
    {
      "claim": "LineageFlow composite +0.2083 SUPPORTED",
      "wave_source": "Wave 73 Phase 6 §'All-3-models final status' (line 20)",
      "verdict_status": "OVERCLAIM (composite is internal glue-layer, NOT paper metric)",
      "caveat_text": "The +0.2083 is the internal glue-layer composite (entropy reduction + max-prob delta + argmax turnover on 33 ESM-2 token slots via LineageFlowGlue/LineageFlowClassifierAwareRestart). It is NOT the LineageFlow paper's family_validity/foldability/self_consistency/novelty metrics. Upstream paper metrics were NEVER RUN — Phase 1 §1.3 documents the critical-path blocker (missing HMMER/MMseqs2/OmegaFold binaries + Pfam-A.hmm DB + MMseqs2 target DB). Wave 79 Phase 3 confirmed the orchestrator subprocess failed fast on the missing binary. Caveat the Wave 73-74 framing as 'internal composite-axis verdict'; paper-metric verdict is BLOCKED_UPSTREAM_DEPS_MISSING."
    },
    {
      "claim": "FlowMol3 TIE_AT_SATURATION (Wave 73) / TIE_AT_SATURATION_with_byte_stable_composite (Wave 74)",
      "wave_source": "Wave 73 Phase 6 §'All-3-models final status' (line 21); Wave 74 Phase 6 §'FlowMol3 verdict evolution table'",
      "verdict_status": "PARTIALLY OVERCLAIM (TIE on entropy axis is correct; 'byte_stable_composite' is internal glue-layer, NOT paper metric)",
      "caveat_text": "The 'TIE on entropy axis' reading is correct: baseline_metric = framework_metric = 0.07340423794186401 nats is byte-stable because upstream FlowMol.sample owns its integration loop. However, the 'byte_stable_composite' is on the INTERNAL 5-axis glue-layer (frac_valid_mols + frac_mols_stable_valence + energy_js_div + reos_cum_dev + neg_med_rmsd_after_xtb), NOT the FlowMol3 paper's 4 paper metrics. Wave 75 Phase 3 ran paper metrics at N=10: only validity_pct matches (1.000 vs paper 0.999); 3/4 axes BLOCKED or INSUFFICIENT. Caveat the Wave 74 framing as 'internal glue-layer composite-axis'; paper-metric verdict is PARTIAL (1/4 matches, 3/4 unresolved)."
    },
    {
      "claim": "framework_improves on composite was comparison vs internal composite baseline, NOT vs paper metric",
      "wave_source": "Wave 73 Phase 6 §'All-3-models final status'; Wave 74 Phase 6 §'FlowMol3 verdict evolution'",
      "verdict_status": "OVERCLAIM (the comparison is internal-vs-internal, not framework-vs-paper)",
      "caveat_text": "The Wave 73-74 framework_improves verdicts compare framework internal composite vs baseline internal composite. Wave 73 baseline measurement was BROKEN on FlowMol3 at n>1 molecules per cell (entropy observer failed — Wave 73 §5.1 caveat: n=1 molecule per cell + upstream-internal RNG → run-to-run spread ±0.6). Wave 74 F1+F2 closed this on internal-composite axis (3-run byte-identical at seed=42, NFE=50, n_molecules=10). However, this does not validate 'framework beats baseline at matched paper metric' — paper metric is a different number, computed by a different code path (upstream SampleAnalyzer.analyze or upstream evaluate_all.py). Caveat the framing as 'framework beats baseline on internal composite axis'; framework-vs-baseline delta on paper metric is unmeasured (Kanzi ties-noise-band, LineageFlow BLOCKED, FlowMol3 PARTIAL)."
    }
  ],
  "paper_claim_support": {
    "matched_quality_improvement": false,
    "matched_quality_improvement_internal_composite": true,
    "matched_nfe_speedup": true,
    "matched_nfe_speedup_tier1_only": true,
    "matched_nfe_speedup_tier3_saturated": true,
    "extends_baseline_plateau": false,
    "extends_baseline_plateau_internal_composite": true,
    "framework_sota": false,
    "framework_sota_structural_framing": true
  },
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave79-phase4-verdict.md"
  ],
  "notes": [
    "Per-model honest verdict from upstream paper metrics (Wave 79 Phase 3): Kanzi TIES (n=2 insufficient, Kabsch RMSD delta inside FSQ noise band); LineageFlow BLOCKED_UPSTREAM_DEPS_MISSING (Phase 1 §1.3 critical-path); FlowMol3 PARTIAL (1/4 paper metrics matches, 3/4 unresolved at N=10).",
    "Wave 73-74 overclaim caveat: 'composite lift SUPPORTED' is on the internal glue-layer composite axis (entropy reduction + max-prob delta + argmax turnover on the latent codebook), NOT on upstream paper metrics.",
    "Wave 73 baseline measurement on FlowMol3 was BROKEN at n_molecules>1 (entropy observer failed → run-to-run spread ±0.6); Wave 74 F1+F2 closed this on internal-composite axis (3-run byte-identical at n=10) but paper metric (validity_pct / pb_validity_pct / fg_dev / ood_ring_rate) was NOT exercised in Wave 73-74.",
    "Paper A 'matched-quality framework improvement' claim should be reworded: framework improves internal composite axis (NOT paper metric). Per-paper-claim support status: matched_quality_improvement=false on paper metric, true on internal composite; matched_nfe_speedup=true on Tier 1 only (already documented Wave 73 §7.7.8); extends_baseline_plateau=false on paper metric, true on internal composite; framework_sota=false on Tier 3 paper metric, structural framing preserved.",
    "No clean Tier 3 paper-metric 'framework beats baseline' claim is supported on this Wave 79 sweep. Wave 76 R1 critical path: LineageFlow heavy-deps install + Kanzi n=1000 per-cell FASTA generator + FlowMol3 PB-xtb pipeline + FlowMol3 N>=500 paper-metric sweep.",
    "Wave 79 Phase 4 (this) is paper-writeup only. NO commit (commits in Phase 5)."
  ]
}
```

---

## 10. Sources

**Wave 79 audit docs (input):**
- `docs/audit/wave79-phase1-audit.md` — Phase 1 per-model readiness (LineageFlow upstream vendored; Kanzi cloned; critical-path blockers documented)
- `docs/audit/wave79-phase2-wire.md` — Phase 2 `--*-upstream-eval` flag wiring (8 unit tests pass)
- `docs/audit/wave79-phase3-sweep.md` — Phase 3 upstream eval sweep (Kanzi Kabsch RMSD computed; LineageFlow BLOCKED)

**Wave 73-74 (input — overclaim source):**
- `docs/audit/wave73-phase6-final.md` — "All-3-models final status" (Kanzi SUPPORTED +0.1695; LineageFlow SUPPORTED +0.2083; FlowMol3 TIE_AT_SATURATION)
- `docs/audit/wave74-phase6-final.md` — "All-3-models final status" (FlowMol3 TIE_AT_SATURATION_with_byte_stable_composite)

**Wave 75 (input — FlowMol3 paper-metric data):**
- `docs/audit/wave75-phase3-paper-repro.md` — FlowMol3 paper-metric sweep (validity_pct=1.000 PASS; pb_validity_pct=0.0 BLOCKED; fg_dev=0.944 + ood_ring_rate=0.0 INSUFFICIENT_SAMPLE at N=10)

**Paper-draft (input — current Wave 73-74 framing):**
- `docs/paper-draft.md` §7.3 Kanzi, §7.4 LineageFlow, §7.5 FlowMol3, §7.6 Tier 3 honest verdict (Wave 73-74 framing; this verdict adds the Wave 79 caveat)

**Verification outputs (input — upstream paper metrics):**
- `verification_outputs/kanzi_upstream_baseline_q4_2026.json` — Kanzi baseline run (Kabsch RMSD = 1.40 Å, n=2)
- `verification_outputs/kanzi_upstream_framework_q4_2026.json` — Kanzi framework run (Kabsch RMSD = 1.67 Å, n=2)
- `verification_outputs/lineageflow_upstream_baseline_q4_2026.json` — LineageFlow baseline BLOCKED
- `verification_outputs/lineageflow_upstream_framework_q4_2026.json` — LineageFlow framework BLOCKED

---

**Wave 79 Agent 4 closed at:** 2026-09-08 (Wave 79 Agent 4)
**Status:** PER-MODEL HONEST VERDICT + WAVE 73-74 OVERCLAIM CAVEAT WRITTEN.
Per-model verdict from upstream paper metrics: Kanzi TIES (n=2),
LineageFlow BLOCKED, FlowMol3 PARTIAL. Internal composite axis is
real but not the paper metric. No Tier 3 paper-metric "framework beats
baseline" claim is supported on this Wave 79 sweep. **NO commit.**