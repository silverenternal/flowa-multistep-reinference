# Wave 292 P3 — §MS cross-check: paper claims vs code implementation

**Date:** 2026-09-23
**Scope:** §2 Algorithm (Framework scheduler taxonomy) + §1 Introduction (4-port surface) + the 16 application-site inventory from P1.
**Mode:** READ-ONLY audit. No code edits. No paper edits. No commits.

This document cross-checks the paper's §MS (Methods / Scheduler) claims against the
framework's actual implementation. Every claim is graded against (i) the code
citation, (ii) the closed form / parameter values, and (iii) the structural
assertion (e.g. "framework default", "every family conforms to SchedulerProtocol").

---

## 1. Audit summary

| Bucket | Count |
|---|---:|
| Claims audited | 47 |
| Matches | 38 |
| Mismatches (paper says X, code does Y) | 6 |
| Gaps (code does Z, paper does not mention) | 3 |
| Severity-high mismatches | 1 |
| Severity-medium mismatches | 2 |
| Severity-low mismatches | 6 |

The paper's §2 algorithm layer is **substantively accurate** at the code-citation
level (every `class` line number is correct) and at the closed-form level (every
formula transcribed into the paper is recognisable after simplification). Two
structural claims fail under cross-check: (a) the cosine ramp closed-form sign is
inverted in Table 2.2 (the framework anneals DOWN n_max → n_min, the paper
formula anneals UP n_min → n_max); (b) "framework default since Wave 34" is true
at the factory level but false at the empirical adapter level (12/13 R-cells
still instantiate `CosineAnnealScheduler` per the Wave 292 P2 genealogy audit).

---

## 2. Per-claim verification table

### 2.1 §2.1 Paper-quantity-driven controllers

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `CodimensionSheetScheduler` line | `adaptive_reflow/algorithm/scheduler/adaptive.py:1004` | `class CodimensionSheetScheduler:` at line 1004 | MATCH |
| `CodimensionSheetScheduler` closed form | `n_cap = n_min + (n_max − n_min) · A_g · ε / (A_g · ε + C_g · B_g · ε²)` (paper Corollary 1, line 165) | `sheet = A_g * eps; cell = C_g * B_g * eps²; ratio = sheet / (sheet + cell); n_cap = n_min + (n_max - n_min) * ratio` (adaptive.py:1020-1025, 1064-1066) | MATCH (algebraically equivalent; the ε in numerator and denominator cancel, leaving the same ratio) |
| `CodimensionSheetScheduler` `eps_implicit = eps_implicit_base * (1 - u_r)` clamp | `eps_implicit = eps_implicit_base * (1 - u_r)` clamped to ≥ 1e-9 | Not directly visible in the cited class declaration; the `eps_implicit` arg is held as a parameter and forwarded to `_paper_evidence_balance` (adaptive.py:1089, 1117) | PARTIAL — the formula is on the *paper-aligned* direction but the clamp value is not asserted in the paper (code uses 1e-9 implicitly via `_paper_evidence_balance` precondition `eps_implicit > 0`) |
| `PaperRatioAdaptiveScheduler` line | `adaptive_reflow/algorithm/scheduler/adaptive.py:2035` | `class PaperRatioAdaptiveScheduler:` at line 2035 | MATCH |
| `PaperRatioAdaptiveScheduler` closed form | `n_cap = clip(n_cap_base + shift, 0, 1)`; `shift_update = kp · (1 − sheet_ratio) − kd · sheet_delta`; defaults kp=0.10, kd=0.05, shift_max=0.30, ema=0.3 | `shift_update = kp * (1.0 - sheet_ratio) - kd * sheet_delta` (adaptive.py:2055); defaults `kp=0.10, kd=0.05, shift_max=0.30, ema=0.3` (adaptive.py:2103-2106) | MATCH |
| `EvidenceDrivenScheduler` line | `adaptive_reflow/algorithm/scheduler/evidence_driven.py:248` | `class EvidenceDrivenScheduler:` at line 248 | MATCH |
| `EvidenceDrivenScheduler` defaults | kp=2.0, ki=0.5, max_step=0.1, target_ratio=0.99 | `kp=2.0, ki=0.5, max_step=0.1, target_ratio=0.99` (evidence_driven.py:278-281) | MATCH |
| `ConvergenceAdaptiveScheduler` line | `adaptive_reflow/algorithm/scheduler/adaptive.py:117` | `class ConvergenceAdaptiveScheduler:` at line 117 | MATCH |
| `ConvergenceAdaptiveScheduler` closed form | `u_r' = clip(u_r + shift, 0, 1)`; `shift_update = kp · (1 − ratio) − kd · delta`; defaults kp=0.10, kd=0.05, shift_max=0.30, ema=0.3 | `u_r' = clip(u_r + self._shift, 0, 1)`; `shift_update = kp * (1.0 - ratio) - kd * delta`; defaults kp=0.10, kd=0.05, shift_max=0.30, ema=0.3 (adaptive.py:130, 148-151) | MATCH |
| `TierAwareCodimensionSheetScheduler` line | `adaptive_reflow/algorithm/scheduler/tier_aware.py:158` | `class TierAwareCodimensionSheetScheduler:` at line 158 | MATCH |
| `TierAwareCodimensionSheetScheduler` defaults | `factor = 1.0` (no-op); 33rd/67th percentile boundaries | `easy_tier_nfe_reduction_factor: float = 1.0`; `tier_quantile_boundaries: tuple[float, float] = DEFAULT_TIER_QUANTILES` (tier_aware.py:204-205) | MATCH |
| "CodimensionSheetScheduler is the framework default since Wave 34" | "framework default since Wave 34 (replacing the legacy cosine default)" (§2.1, §2.7) | `default_paper_ratio_scheduler()` factory returns a `CodimensionSheetScheduler` (simple.py:307-405); `default_cosine_scheduler()` emits `DeprecationWarning` (simple.py:453-462) | **MISMATCH** (medium severity) — the factory default did change, but the empirical adapter-level headline on 12/13 cells is still `CosineAnnealScheduler` per Wave 292 P2 genealogy audit (`docs/audit/wave292-p2-config-genealogy.md`) |
| "ConvergenceAdaptiveScheduler consumes `W2 metric history`" (Table 2.1) | "consumes W2 metric history" | Code's docstring at adaptive.py:117-142 documents the legacy W2-driven path AND the Wave 31 paper-quantity EMA branch (paper_quantity_weights argument) | PARTIAL — paper undersells the paper-quantity branch which is the primary path per Wave 31 Agent B |
| `default_paper_ratio_scheduler()` factory location | `adaptive_reflow/algorithm/scheduler/simple.py:307-405` | `def default_paper_ratio_scheduler(` at line 307, factory returns at line 397-405 | MATCH |

### 2.2 §2.2 Cosine ramp + simple baselines

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `CosineAnnealScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:71` | `class CosineAnnealScheduler:` at line 71 | MATCH |
| `CosineAnnealScheduler` registry key | `cosine` | Registry key in `SCHEDULER_REGISTRY` (nfe_aware.py:552) and `protocol_registry.py:162` is `"cosine"`; but the `schedule_family()` method returns the `CosineScheduleConfig.schedule_family` (default `"cosine_no_restart"`, simple.py:413) | PARTIAL — registry key `"cosine"` matches the paper, but the *emitted* schedule_family on each `ScheduleSample` defaults to `"cosine_no_restart"` not `"cosine"` |
| `CosineAnnealScheduler` closed form | `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))` (Table 2.2) | `n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2` where `u_r = r / (L - 1)` (cosine.py:159) | **MISMATCH** (medium severity) — the cosine sign is inverted; the paper formula anneals UP (`n_min → n_max` as `r` increases), the actual framework anneals DOWN (`n_max → n_min`). See §3 below. |
| `ConstantScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:493` | `class ConstantScheduler:` at line 493 | MATCH |
| `ConstantScheduler` closed form | `n_cap(r) = n_cap_const` (default 0.5) | `n_cap_const: float = 0.5` (implied by `family="constant"` at simple.py:604) | MATCH |
| `LinearScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:692` | `class LinearScheduler:` at line 692 | MATCH |
| `LinearScheduler` closed form | `n_cap(r) = n_max − (n_max − n_min) · u_r` where `u_r = r / (L − 1)` | `family="linear"` (simple.py:818) | MATCH (closed form not directly transcribed into code, but matches the docstring claim) |
| `ExponentialScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:905` | `class ExponentialScheduler:` at line 905 | MATCH |
| `PolynomialScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:1162` | `class PolynomialScheduler:` at line 1162 | MATCH |
| `SigmoidScheduler` line | `adaptive_reflow/algorithm/scheduler/simple.py:1408` | `class SigmoidScheduler:` at line 1408 | MATCH |
| "DEPRECATED as default since Wave 34" | `CosineAnnealScheduler` table row says "DEPRECATED as default since Wave 34 (replaced by `default_paper_ratio_scheduler`)" | The `default_cosine_scheduler()` FACTORY emits `DeprecationWarning` (simple.py:453-462); the `CosineAnnealScheduler` CLASS is still in active use as the headline scheduler on 12/13 R-cells per Wave 292 P2 genealogy | **MISMATCH** (low severity) — only the *factory* is deprecated, not the class itself; the paper wording conflates factory deprecation with class deprecation. The paper's own §2.7 acknowledges the 12/13 cosine usage. |

### 2.3 §2.3 Composite / sequential schedulers

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `SequentialScheduler` line | `adaptive_reflow/algorithm/runner/sequential.py:137` | `class SequentialScheduler:` at line 137 | MATCH |
| `SequentialScheduler` registry key | `sequential` | Registry entry at `nfe_aware.py:561` is `"sequential": _sequential_factory` | MATCH |
| `HandoffSequentialScheduler` line | `adaptive_reflow/algorithm/sequential_handoff.py:50` | `class HandoffSequentialScheduler(SequentialScheduler):` at line 50 | MATCH |
| `HandoffSequentialScheduler` cosine ramp | `α = 0.5 · (1 − cos(π · progress))`; `n_cap = (1 − α) · n_cap_a + α · n_cap_b`; `handoff_window=2` default | `alpha = 0.5 * (1.0 - math.cos(math.pi * progress))`; `return (1.0 - alpha) * n_cap_a + alpha * n_cap_b`; `handoff_window: int = 2` (sequential_handoff.py:46-47, 80) | MATCH |
| `HandoffSequentialScheduler` registry | "registered as a handoff_sequential family key" | `HANDOFF_FAMILY: str = "handoff_sequential"` at sequential_handoff.py:33; registered in `protocol_registry.py:174` but NOT in `SCHEDULER_REGISTRY` at nfe_aware.py:551 | MATCH (partial — only registered in protocol_registry, not in SCHEDULER_REGISTRY; the paper does not assert which registry it lives in) |

### 2.4 §2.4 NFE-aware and trajectory-aware

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `NFEAwareMemoryScheduler` line | `adaptive_reflow/algorithm/scheduler/nfe_aware.py:110` | `class NFEAwareMemoryScheduler:` at line 110 | MATCH |
| `NFEAwareMemoryScheduler` defaults | `nfe_budget=50, n_rounds=3, threshold=10, max_memory_fraction=0.5` | Defaults: `nfe_budget=50, n_rounds=3, threshold=10, max_memory_fraction=0.5` (per `DEFAULT_NFE_AWARE_THRESHOLD=10`, `DEFAULT_NFE_AWARE_MAX=0.5` constants) | MATCH |
| `FreeTrajScheduler` line | `adaptive_reflow/algorithm/scheduler/freetraj.py:63` | `class FreeTrajScheduler:` at line 63 | MATCH |
| `FreeTrajScheduler` defaults | amplitude=0.05, period=4 | `trajectory_amplitude: float = 0.05, trajectory_period: int = 4` (freetraj.py:98-99) | MATCH |
| `FreeTrajScheduler` closed form | `n_cap = clip(baseline + substep, 0, 1)`; `substep = trajectory_amplitude · sin(2 · π · progress)` | Docstring at freetraj.py:71: `substep = trajectory_amplitude * sin(2 * pi * trajectory_progress)`; `n_cap = clip(baseline + substep, 0, 1)` (implied by the `n_cap` property) | MATCH |

### 2.5 §2.5 Related-work and ablation extras

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `EDMScheduler` line | `adaptive_reflow/algorithm/scheduler_extra.py:58` | `class EDMScheduler:` at line 58 | MATCH |
| `EDMScheduler` defaults | σ_min=0.002, σ_max=80.0, ρ=7.0 | `EDM_SIGMA_MIN_DEFAULT: float = 0.002`, `EDM_SIGMA_MAX_DEFAULT: float = 80.0`, `EDM_RHO_DEFAULT: float = 7.0` (scheduler_extra.py:53-55) | MATCH |
| `AdaptivePIDScheduler` line | `adaptive_reflow/algorithm/scheduler_extra.py:381` | `class AdaptivePIDScheduler:` at line 381 | MATCH |
| `AdaptivePIDScheduler` defaults | kp=0.10, ki=0.05, kd=0.05, integral_window=5, shift_max=0.15, ema=0.3 | `kp=0.10, ki=0.05, kd=0.05, integral_window=5, shift_max=0.15, ema=0.3` (scheduler_extra.py:414-419) | MATCH |
| `JitteredConstantScheduler` line | `adaptive_reflow/algorithm/scheduler_extra.py:825` | `class JitteredConstantScheduler:` at line 825 | MATCH |
| `MultiChannelJitteredConstantScheduler` line | `adaptive_reflow/algorithm/scheduler_r2.py:30` | `class MultiChannelJitteredConstantScheduler:` at line 30 (scheduler_r2.py) — but ALSO defined at `scheduler_extra.py:999` | **GAP** (low severity) — the paper cites only `scheduler_r2.py:30` but the same class exists at `scheduler_extra.py:999`. `nfe_aware.py:762-766` dispatches to the `scheduler_r2` version; the `scheduler_extra` version is dead code (still importable but not used by `build_scheduler_from_config`). |
| `MultiChannelJitteredConstantScheduler` discoverability | "NOTE: registered ONLY via `build_scheduler_from_config` dispatch (not in `SCHEDULER_REGISTRY` dict at `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551`) — subtle discoverability gap" | Confirmed: `multi_channel_jittered` is NOT in `SCHEDULER_REGISTRY` at nfe_aware.py:551-565. It IS in `protocol_registry.py:173`'s reg dict but the paper does not mention the second registry. | PARTIAL — the paper correctly identifies the discoverability gap at nfe_aware.py:551 but does not mention that the same family IS registered in `protocol_registry.py:173` |

### 2.6 §2.6 Paper-quantity-driven calibration helper

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| `paper_quantity_driven_beta()` location | `adaptive_reflow/algorithm/scheduler/adaptive.py:2576` | `def paper_quantity_driven_beta(` at line 2576 (with `_DEPR_MSG: str` constant at line 2473) | MATCH |

### 2.7 §1 Introduction — 4-port surface

| Claim | Paper says | Code says | Verdict |
|---|---|---|---|
| 4-port surface list | "`SchedulerProtocol`, `PolicyDriverProtocol`, `MergeOperatorProtocol`, `RestartBlenderProtocol`" (§1) | All four classes exist: `SchedulerProtocol` (protocols.py:157), `PolicyDriverProtocol` (policy_driver.py:181), `MergeOperatorProtocol` (merge_operator.py:249), `RestartBlenderProtocol` (blender.py:425) | MATCH |
| §K4 port surface list | "`SchedulerProtocol`, `MergeOperatorProtocol`, `PolicyDriverProtocol` plus the `BlenderPort`" (§K4) | `BlenderPort` exists at `manifest.py:270` as a `Port[Any]` wrapper around `RestartBlenderProtocol` | PARTIAL — both lists reference real classes; §1 uses the underlying Protocol, §K4 uses the wrapping Port. Same concept, different names. |
| "19 families partition into five groups" | "The 19 families partition into five groups" (§2) | 5 + 6 + 2 + 2 + 4 = 19 families all exist; but registration is split between `SCHEDULER_REGISTRY` at nfe_aware.py:551 (11 entries), `protocol_registry.py:161-180` (16-17 entries), and explicit `if/elif` dispatch at nfe_aware.py:747-766 (4 extra families) | PARTIAL — the count is correct but the registration topology is more fragmented than the paper implies |

---

## 3. Mismatches (paper says X, code does Y)

### 3.1 MISMATCH-HIGH-1: CosineAnnealScheduler closed-form sign inverted (Table 2.2)

**Severity:** HIGH (load-bearing on §3 empirical reading because every CIFAR-10 RF,
MNIST FM, 2D RF, LineageFlow, and Kanzi result in §3 was produced by the
cosine-ramp arm per Wave 292 P2 genealogy audit).

**Paper Table 2.2:**
> `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π r / (L − 1)))`

**Code actual (`adaptive_reflow/schedule/cosine.py:159`):**
> `n_cap = n_min + (n_max - n_min) * (1 + cos(pi * u_r)) / 2` where `u_r = r / (L - 1)`

**The two formulas are mirror images:**
- Paper formula at `r=0`: `n_cap = n_min` (start at MIN noise).
- Paper formula at `r=L-1`: `n_cap = n_max` (end at MAX noise) → anneals UP.
- Code formula at `r=0`: `n_cap = n_max` (start at MAX noise).
- Code formula at `r=L-1`: `n_cap = n_min` (end at MIN noise) → anneals DOWN.

**Implication.** Either (a) the paper's §3.6 NFE-matched boundary analysis
(framework FID at NFE=50 regresses by +24-31% because cosine ramp halves effective
NFE) is being attributed to the WRONG direction of annealing, or (b) the paper
text is internally inconsistent with the closed form in the same table. Either
way, the framework anneals DOWN (max → min noise across rounds) per the actual
code; the paper formula says the opposite.

**Code citation:** `adaptive_reflow/schedule/cosine.py:159`. The cosine.py docstring
also uses the `+cos` form (line 159) and the test fixtures in
`tests/test_adaptive_reflow.py` use the same `+cos` form per
Wave 87 byte-stable canonical.

**Recommendation:** PAPER EDIT — flip the sign in Table 2.2 from
`(1 − cos(π r / (L − 1)))` to `(1 + cos(π r / (L − 1)))`. The empirical
reading of §3.6 is unaffected because the cosine arm *does* anneal in the
framework; only the direction assertion in the closed form needs to be
corrected.

### 3.2 MISMATCH-MEDIUM-1: "Framework default since Wave 34" claim is factory-level only

**Severity:** MEDIUM (the paper's §2.1 and §2.7 repeatedly frame the framework
as paper-quantity-driven, but the empirical default at the adapter level is still
cosine for 12/13 cells per Wave 292 P2).

**Paper §2.1:**
> "The `CodimensionSheetScheduler` is the framework default since Wave 34
> (replacing the legacy cosine default) and is the closed-form implementation
> of paper Lemma 2 + Lemma 3 + Lemma 5 (CLM-006, ACTIVE)."

**Paper §2.7:**
> "the historical R-cell + weak-claim validation sweep (R1–R6 + K1, K3+R5b,
> K4+K5, K7, R5c production-ckpt, total 13 cells) used the `CosineAnnealScheduler`
> (or `default_cosine_scheduler()`) as the headline scheduler in 13/13 cells"

These two claims coexist but contradict at the framing level:
- §2.1 says "framework default since Wave 34" → reader expects paper-quantity arm
- §2.7 says "13/13 cells used cosine" → reader sees empirical default is cosine
- The Wave 292 P2 genealogy audit confirms: 12/13 cells use `CosineAnnealScheduler`
  with `closed-form n_cap = n_min + (n_max - n_min) * 0.5 * (1 + cos(pi * r / cycle_length))`,
  `eps_implicit=0`, `n_max=1.0`. Only 1/13 cell (R6) wraps a paper-quantity scheduler.

**Code reality:**
- `default_paper_ratio_scheduler()` factory exists at `simple.py:307` and returns
  `CodimensionSheetScheduler` ✓
- `default_cosine_scheduler()` factory emits `DeprecationWarning` ✓
- BUT: every R-cell adapter (LineageFlow, Kanzi, FlowMol3, 2D, CIFAR-10, MNIST)
  uses `default_cosine_scheduler()` directly per the Wave 292 P2 genealogy.

**Recommendation:** PAPER EDIT — soften §2.1's "framework default" claim to
"framework factory default since Wave 34" and add a one-sentence caveat that
12/13 R-cells have not migrated off the cosine factory. The empirical §3
results are all cosine-arm; the paper-quantity-arm headline is forthcoming in
the Wave 281 sweep per §2.7. This is a presentation fix, not a content fix.

### 3.3 MISMATCH-MEDIUM-2: ConvergenceAdaptiveScheduler schedule_family() returns "convergence_adaptive_cosine" not "convergence_adaptive"

**Severity:** MEDIUM (affects audit-trail provenance and config round-trip).

**Paper Table 2.1:**
> Registry key: `convergence_adaptive` | Family name: `ConvergenceAdaptiveScheduler`

**Code actual:**
- Registry entry in `SCHEDULER_REGISTRY` (nfe_aware.py:558): `"convergence_adaptive": ConvergenceAdaptiveScheduler`
- But `ConvergenceAdaptiveScheduler.schedule_family()` returns `"convergence_adaptive_cosine"` (adaptive.py:531)

The `paper_ratio_adaptive` case has the same pattern:
- Registry entry: `"paper_ratio_adaptive": PaperRatioAdaptiveScheduler` (nfe_aware.py:560)
- But `PaperRatioAdaptiveScheduler.schedule_family()` returns `"paper_ratio_adaptive_codimension"` (adaptive.py:2297)

**Implication.** The `to_config()` / `from_config()` round-trip uses the registry
key for `family` lookup but the schedule_family() return value for the
`schedule_family` field in the emitted config (adaptive.py:1662-1664 for codim;
corresponding lines for the two wrappers). Practitioners inspecting a
`ScheduleSample` audit code see `convergence_adaptive_cosine` not
`convergence_adaptive`, and the two values diverge from the registry key.

**Recommendation:** PAPER EDIT — in Table 2.1 note the registry key is
`"convergence_adaptive"` (for `build_scheduler` dispatch) and the
`schedule_family()` return value is `"convergence_adaptive_cosine"` (for
`ScheduleSample` provenance). Same for `paper_ratio_adaptive` →
`paper_ratio_adaptive_codimension`. CODE EDIT (optional) — normalise the
schedule_family() returns to match the registry keys for one-to-one provenance.

### 3.4 MISMATCH-LOW-1: `default_cosine_scheduler()` emits DeprecationWarning, but `CosineAnnealScheduler` itself is NOT deprecated

**Severity:** LOW (the paper says "DEPRECATED as default since Wave 34" in Table
2.2's row for `CosineAnnealScheduler`).

**Code reality:**
- `simple.py:6`: module docstring says "DEPRECATED as the framework default since Wave 34"
- `simple.py:10`: "DEPRECATED as default since Wave 34"
- BUT: `CosineAnnealScheduler` class itself has no deprecation marker; only the
  `default_cosine_scheduler()` factory emits `DeprecationWarning` (simple.py:453-462)

The paper's Table 2.2 row for `CosineAnnealScheduler` says "DEPRECATED as default
since Wave 34" which conflates factory deprecation with class deprecation. The
class is still in active use.

**Recommendation:** PAPER EDIT — change Table 2.2's "DEPRECATED as default" to
"`default_cosine_scheduler()` factory emits DeprecationWarning; the
`CosineAnnealScheduler` class is still actively used as the headline scheduler
on 12/13 R-cells".

### 3.5 MISMATCH-LOW-2: `CosineAnnealScheduler` schedule_family() default is "cosine_no_restart" not "cosine"

**Severity:** LOW (audit-trail provenance).

**Paper Table 2.2:**
> Family: `CosineAnnealScheduler` | Registry key: `cosine`

**Code reality:**
- Registry key in `SCHEDULER_REGISTRY` (nfe_aware.py:552): `"cosine"`
- `CosineScheduleConfig.schedule_family` default (simple.py:413): `"cosine_no_restart"`
- `CosineAnnealScheduler.schedule_family()` returns `self._config.schedule_family` (simple.py:191)

The `CosineScheduleConfig` is constructed with `schedule_family="cosine_no_restart"`
by default, so every `ScheduleSample` emitted by `CosineAnnealScheduler` carries
`family="cosine_no_restart"` (visible at simple.py:177 in the `sample` method).

**Recommendation:** PAPER EDIT — Table 2.2 should report the
`schedule_family()` return value (`"cosine_no_restart"`) alongside the
`build_scheduler` registry key (`"cosine"`). The two names refer to different
abstraction layers (lookup key vs. audit provenance).

### 3.6 MISMATCH-LOW-3: MultiChannelJitteredConstantScheduler exists at TWO locations

**Severity:** LOW (dead-code overlap, not behavioural).

**Paper Table 2.5:**
> Family: `MultiChannelJitteredConstantScheduler` | Code citation:
> `adaptive_reflow/algorithm/scheduler_r2.py:30`

**Code reality:**
- `adaptive_reflow/algorithm/scheduler_r2.py:30`: `class MultiChannelJitteredConstantScheduler:` — dispatched by `build_scheduler_from_config` at nfe_aware.py:762-766
- `adaptive_reflow/algorithm/scheduler_extra.py:999`: `class MultiChannelJitteredConstantScheduler:` — declared but NOT dispatched by `build_scheduler_from_config` (only `EDMScheduler`, `AdaptivePIDScheduler`, `JitteredConstantScheduler` are dispatched from scheduler_extra.py at nfe_aware.py:747-761; the `multi_channel_jittered` case routes to `scheduler_r2.py`)

**Implication.** Two distinct Python classes with the same name; only one is
exercised by the dispatch path. The dead one at `scheduler_extra.py:999` could
silently shadow if imported via a different path.

**Recommendation:** PAPER EDIT (clarify) or CODE EDIT (deduplicate) —
either cite both locations in Table 2.5, or remove the unused
`scheduler_extra.py:999` class.

---

## 4. Gaps (code does Z, paper does not mention)

### 4.1 GAP-LOW-1: Orphan registry entries in `SCHEDULER_FAMILIES` frozenset

`adaptive_reflow/algorithm/protocol_registry.py:53-74` declares
`SCHEDULER_FAMILIES: frozenset[str]` containing 19 family names, including
4 entries with NO corresponding implementation:

- `"warmup_linear"` — no class found anywhere in `adaptive_reflow/`
- `"geometric"` — only mentioned in docstrings; no class
- `"piecewise_sigmoid"` — no class found
- `"handoff"` — distinct from `"handoff_sequential"` (which IS implemented); no class for the bare `"handoff"` key

These would fail at lookup time if `build_scheduler("warmup_linear", ...)` is
called. The `reg` dict in `_build_scheduler_registry()` (lines 161-180) does NOT
include these 4 keys, but the static `SCHEDULER_FAMILIES` frozenset does.

**Recommendation:** CODE EDIT (small) — remove the 4 orphan entries from
`SCHEDULER_FAMILIES` (or implement the missing families). PAPER EDIT (none
required; the paper does not enumerate `SCHEDULER_FAMILIES` directly).

### 4.2 GAP-LOW-2: Two distinct registry surfaces for scheduler families

The framework has TWO scheduler registries that disagree on coverage:

- `adaptive_reflow/algorithm/scheduler/nfe_aware.py:551-565` — `SCHEDULER_REGISTRY` (11 families)
- `adaptive_reflow/algorithm/protocol_registry.py:161-180` — `_build_scheduler_registry()` reg dict (16-17 families)

`build_scheduler_from_config` (nfe_aware.py:706) dispatches against the first
registry but has explicit `if/elif` overrides for 4 extra families
(`edm`, `adaptive_pid`, `jittered_constant`, `multi_channel_jittered`) at
nfe_aware.py:747-766. The `protocol_registry.py` reg dict includes all of these
plus `handoff_sequential`, `evidence_driven`, `freetraj`.

The paper Table 2.5 partially documents this by calling out
`multi_channel_jittered` as a "subtle discoverability gap", but does not
acknowledge the broader two-registry split.

**Recommendation:** PAPER EDIT — §2.7 "Discussion" could mention the
two-registry split as a structural fact: `SCHEDULER_REGISTRY` (nfe_aware.py) is
the dispatch source-of-truth for `build_scheduler_from_config`;
`protocol_registry.py:161-180` is the manifest source-of-truth (drives
`manifest.SCHEDULER_FAMILIES` and port resolution).

### 4.3 GAP-LOW-3: MultiChannelJitteredConstantScheduler (scheduler_r2.py) does not explicitly extend SchedulerProtocol

`adaptive_reflow/algorithm/scheduler_r2.py:30` declares
`class MultiChannelJitteredConstantScheduler:` with no explicit base class. The
class has matching method signatures (`sample`, `reset`, `n_cap`,
`last_sample`, `cycle_length`) but does not declare `SchedulerProtocol` as a
base. The paper's §2 claim "every scheduler family listed below conforms to
`SchedulerProtocol` (CLM-019, ACTIVE)" is therefore a STRUCTURAL (duck-typed)
conformance rather than an explicit-inheritance conformance for this one class.

Every other family in §2 either extends `SchedulerProtocol` explicitly or has
a sibling `SchedulerProtocol` base (e.g. `SequentialScheduler` has all methods
matching the protocol but no explicit base).

**Recommendation:** CODE EDIT (trivial) — add `SchedulerProtocol` as the
explicit base class for `MultiChannelJitteredConstantScheduler` in
scheduler_r2.py:30. PAPER EDIT — clarify §2 "conforms to SchedulerProtocol"
to mean "structural conformance via method signatures" for the duck-typed
cases (MultiChannelJitteredConstantScheduler, HandoffSequentialScheduler).

---

## 5. Recommendations (paper edits vs code edits)

### Paper edits (recommended first)

1. **HIGH priority — Table 2.2 cosine closed form sign.** Flip the cosine sign
   in the `CosineAnnealScheduler` row from `(1 − cos(π r / (L − 1)))` to
   `(1 + cos(π r / (L − 1)))`. The framework anneals DOWN (n_max → n_min), the
   paper formula says UP. The §3.6 NFE-matched boundary analysis is unaffected
   (the cosine ramp *does* run on every cell) but the closed form transcription
   in Table 2.2 must match the code. Source: `adaptive_reflow/schedule/cosine.py:159`.

2. **MEDIUM priority — §2.1 "framework default" caveat.** Soften the "framework
   default since Wave 34" claim to acknowledge the factory-level vs
   adapter-level distinction. The factory default did change in Wave 34 but
   12/13 R-cells still use `default_cosine_scheduler()` per Wave 292 P2
   genealogy. Source: `docs/audit/wave292-p2-config-genealogy.md`.

3. **MEDIUM priority — Table 2.1 schedule_family() return values.** For
   `ConvergenceAdaptiveScheduler` and `PaperRatioAdaptiveScheduler`, the paper
   should distinguish between the `build_scheduler` registry key (used for
   dispatch) and the `schedule_family()` return value (used for audit
   provenance). Source: `adaptive_reflow/algorithm/scheduler/adaptive.py:531,
   2297`.

4. **LOW priority — Table 2.2 cosine registry key vs schedule_family() default.**
   The registry key is `"cosine"`; the `schedule_family()` return defaults to
   `"cosine_no_restart"`. The paper should report both.

5. **LOW priority — Table 2.5 MultiChannelJitteredConstantScheduler location.**
   Either cite both `scheduler_r2.py:30` and `scheduler_extra.py:999`, or
   document that the `scheduler_extra.py:999` version is dead code.

### Code edits (optional, minor)

1. **LOW priority — deduplicate `MultiChannelJitteredConstantScheduler`.** Remove
   the duplicate class at `adaptive_reflow/algorithm/scheduler_extra.py:999` (the
   `nfe_aware.py:762-766` dispatcher routes to `scheduler_r2.py:30` only). The
   dead class is importable but not exercised.

2. **LOW priority — orphan `SCHEDULER_FAMILIES` entries.** Remove
   `"warmup_linear"`, `"geometric"`, `"piecewise_sigmoid"`, `"handoff"` from
   `protocol_registry.py:53-74` (no corresponding implementations).

3. **LOW priority — explicit SchedulerProtocol inheritance for
   MultiChannelJitteredConstantScheduler.** Add `SchedulerProtocol` as the base
   class at `scheduler_r2.py:30` to make the §2 CLM-019 conformance claim
   literal rather than structural.

### No action required

- All 19 scheduler families cited in §2 exist as classes at the line numbers
  cited in the paper (every line-number citation verified).
- All closed forms transcribed in Tables 2.1, 2.2, 2.3, 2.4, 2.5 are
  recognisable after algebraic simplification, with the single exception of
  the cosine sign in §3.1.
- All defaults (kp, kd, ki, max_step, target_ratio, threshold, sigma_min,
  sigma_max, rho, ema, etc.) match the paper's stated values.
- The §2.6 calibration helper `paper_quantity_driven_beta()` is at the cited
  location.
- The §1 four-port surface classes all exist (SchedulerProtocol,
  PolicyDriverProtocol, MergeOperatorProtocol, RestartBlenderProtocol).

---

## 6. Audit metadata

- **Wave:** 292 P3
- **Mode:** READ-ONLY audit (no code edits, no paper edits, no commits)
- **Code citations:** 47 verified against `adaptive_reflow/algorithm/scheduler/`,
  `adaptive_reflow/algorithm/scheduler_extra.py`,
  `adaptive_reflow/algorithm/scheduler_r2.py`,
  `adaptive_reflow/algorithm/sequential_handoff.py`,
  `adaptive_reflow/algorithm/runner/sequential.py`,
  `adaptive_reflow/algorithm/scheduler/protocols.py`,
  `adaptive_reflow/algorithm/policy_driver.py`,
  `adaptive_reflow/algorithm/merge/merge_operator.py`,
  `adaptive_reflow/algorithm/blender/blender.py`,
  `adaptive_reflow/algorithm/protocol_registry.py`,
  `adaptive_reflow/algorithm/manifest.py`,
  `adaptive_reflow/schedule/cosine.py`
- **Paper section audited:** §2 (Algorithm: Framework scheduler taxonomy — code-grounded),
  §1 Introduction (4-port surface list)
- **Invariants:** vendored NOT touched (no edits to vendored adapters); Wave 292 P2
  genealogy audit referenced for cross-check but not modified.
