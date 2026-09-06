# Wave 45 master plan — adapter-layer fixes for Kanzi + LineageFlow

**Date:** 2026-09-07
**Wave:** Wave 45 (Agent C, synthesis)
**Mode:** READ-ONLY on code. This document is the only write.
**Inputs:** `docs/audit/wave45-local-review.md` (Agent A, 497 lines),
`docs/audit/wave45-web-research-2026.md` (Agent B, 517 lines).
**Repo head:** `8669744897…` (`HEAD` at start of wave; `ba37ac0` was the
review ref).

---

## 0. Executive summary

Wave 45 fixes three adapter-layer deficiencies. Each lands inside the
adapter (`adaptive_reflow/adapters/{kanzi,lineageflow}.py`) plus one shared
helper file; none of them touch the framework core.

| Fix | Where | New files | LOC (est.) |
| --- | --- | --- | --- |
| (a) `KanziGPTPriorRestartPolicy` | `kanzi.py` | `kanzi.py` only | ~60 LOC policy + 1 LOC native-state put + 1 LOC scalar-blend swap |
| (b) `per_position_entropy_reduction` | shared helper + both adapters | `_adapter_common.py` + 2 adapter methods | ~25 LOC helper + ~30 LOC × 2 adapter methods |
| (c) `LineageFlowClassifierAwareRestart` | `lineageflow.py` | `lineageflow.py` only | ~55 LOC policy + 1 LOC blend swap (no Protocol change) |

**Two pre-existing defects block measurement of (a)–(c) and are
prerequisites for any acceptance test:**

- **F-1 (CRITICAL)** — Kanzi `observe_token_indices` returns uniform random
  tokens because no `_native_states.put(...)` payload stores
  `src_digest`. Fix in adapter layer, 2–3 LOC.
- **F-2 (CRITICAL)** — `tools/run_real_ckpt_eval.py:524-539` calls
  `export_endpoint(trace)` and `apply_restart_distribution(bundle=…)`, both
  signature-mismatched against both adapters. The framework arm therefore
  exits after one `solve_ode` and is byte-identical to baseline. This fix
  lives **outside** the adapter scope and must be flagged to the wave lead
  before Wave 45 can claim measurement.

Without F-1 + F-2 the new policies are unmeasurable; shipping without them
re-creates the Wave 44 "Tier-3 delta = 0 by construction" pattern.

**Three supporting papers** (Agent B): ProtBFN (AAAI 2026, arXiv:2411.04220)
for Kanzi restart re-anchor pattern; Nature Chem Biol 2026
(s41589-026-02270-6) for the per-position entropy formula; CFG-Zero*
(arXiv:2503.18886) for the zero-init first-N-steps trick shared by both
adapter policies. Section 4 of Agent B's doc supplies 8 more; we cite the
three load-bearing ones in the policy docstrings and reserve the rest as
"background reading" in `docs/theory/operating-regime.md §11`.

**Implementation order** is strict:

1. **Phase 1 — Kanzi block.** F-1 fix → `per_position_entropy_reduction`
   helper + Kanzi method → `KanziGPTPriorRestartPolicy`. This phase alone
   closes Kanzi Tier-3 measurement; everything downstream can wait.
2. **Phase 2 — LineageFlow block.** `per_position_entropy_reduction`
   LineageFlow method (already shipped in Phase 1 helper) →
   `LineageFlowClassifierAwareRestart`. Closes LineageFlow Tier-3.
3. **Phase 3 — Plumbing + docs.** Re-point
   `tools/run_controlled_audit.py:702` at the shared helper; append
   `docs/PLUG_IN_YOUR_MODEL.md` per-model sections; append
   `docs/theory/operating-regime.md §11.6` recording the promotion.

Phase 1 is **highest priority** — Kanzi Tier-3 has been returning uniform
random numbers for two waves; F-1 alone is the cheapest, highest-value
fix in the project.

---

## 1. Fix (a) — `KanziGPTPriorRestartPolicy`

### 1.1 Goal

Replace the scalar-latent blend at `kanzi.py:1173-1175` with a
**per-position, GPT-prior-confidence-modulated** blend: where the AR prior
is confident, retain more prior latent (higher `m`); where it is uncertain,
admit more fresh noise (lower `m`) so re-inference can explore. The
restart becomes model-aware instead of schedule-only.

This is the load-bearing user directive: *"a GPT-prior-aware restart policy
in `kanzi.py`."*

### 1.2 Architecture

`apply_restart_distribution(state, policy)` cannot see paper quantities or
the trajectory today — see Agent A §0, §4. Per Agent A §4 option 1
(recommended), the signal is captured at `solve_ode` time, persisted into
the same `_native_states.put(...)` payload that F-1 already fixes, and
read back at the next restart via the existing `prior_entry` fetch at
`kanzi.py:1156`. **No Protocol change, no framework change, fully inside
the adapter layer.**

The new policy class lives as a sibling block in `kanzi.py`, after
`_synthetic_family_conditioning` ends and before the
`# torch-mode helpers` banner at line 638. It is plain Python — no
torch import at module load — so synthetic mode stays import-safe (the
~700 synthetic tests are the canonical test surface per Agent A §11).

### 1.3 Specific code change

| Site | File:line | Action |
| --- | --- | --- |
| New policy class | `kanzi.py`, new block before line 638 | ~60 LOC class `KanziGPTPriorRestartPolicy` |
| Signal capture (combined with F-1 fix) | `kanzi.py:1490-1498` | extend `_native_states.put(...)` payload with `src_digest` (F-1) **and** `gpt_prior_confidence: np.ndarray` of shape `(L_z,)` |
| Policy application | `kanzi.py:1173-1175` | replace scalar `m` blend: `m_vec = policy.memory_fraction_vector(prior_entry, base_m=m)` → `blended = m_vec[:, None] * prior + (1 - m_vec[:, None]) * fresh`; **keep the `±KANZI_LATENT_CLAMP` clip at 1175 unchanged** |
| Audit code | `kanzi.py:270` (next to `AUDIT_KANZI_RESTART_BLEND`) | add `AUDIT_KANZI_GPT_PRIOR_RESTART: str = "kanzi_gpt_prior_restart"`; append to `provenance` list at line 1256 |
| Digest | `kanzi.py:1189-1204` | add the policy's config hash to `digest_state` payload so a policy change yields a distinct `native_state_digest` |
| Exports | `kanzi.py:1821` `__all__` | add `"KanziGPTPriorRestartPolicy"` (sorted) |
| Constructor opt-in | `kanzi.py:864` `__init__` | new kwarg `gpt_prior_restart: bool = False`; thread into `KANZI_CONFIG_HASH` provenance |

**Signature (per Agent A §5 + Agent B §4.1):**

```python
class KanziGPTPriorRestartPolicy:
    def __init__(
        self,
        *,
        max_rounds: int = 4,                       # ProtBFN default
        entropy_stop_ratio: float = 0.05,         # vs H_max
        omega_cap: float = 0.30,                   # CFG-Zero* trade-off
        zero_init_steps: int = 2,                  # CFG-Zero* pattern
        seed: int = 0,
    ): ...

    def memory_fraction_vector(
        self,
        prior_entry: Mapping[str, Any],
        *,
        base_m: float,
    ) -> np.ndarray:
        """Return per-token (L_z,) memory fractions in [0, 1].

        Higher where `prior_entry["gpt_prior_confidence"]` is large,
        lower where it is small. Synthetic-mode prior_entry has no
        `gpt_prior_confidence` key → returns `np.full(L_z, base_m)` and
        the audit code `kanzi_gpt_prior_restart_synthetic_degraded` is
        appended to `provenance`.
        """

    def should_restart(
        self,
        round_idx: int,
        entropy_history: Sequence[float] | None = None,
    ) -> bool:
        """ProtBFN §3.2 entropy-triggered early stop."""
```

### 1.4 Test plan

New file: `tests/test_adapters/test_kanzi_restart_policy.py`.

| # | Test | What it asserts |
| --- | --- | --- |
| 1 | `test_memory_fraction_vector_synthetic_degrades_gracefully` | synthetic prior_entry → returns `np.full(L_z, base_m)`; audit code present |
| 2 | `test_memory_fraction_vector_modulates_per_token` | constant confidence 1.0 → all `m_vec == base_m`; per-position confidence array → monotonic mapping (high conf → high m) |
| 3 | `test_memory_fraction_vector_clamps_to_unit_interval` | adversarial prior_entry (NaN, inf, >1, <0) → output in `[0, 1]` |
| 4 | `test_should_restart_entropy_trigger` | history `[1.0, 0.5, 0.48]` → restart (Δ > 0.05·H_max); history `[0.5, 0.49, 0.485]` → stop |
| 5 | `test_should_restart_max_rounds_cap` | `round_idx >= max_rounds` → False regardless of history |
| 6 | `test_config_hash_changes_with_policy` | same Kanzi, two `KanziGPTPriorRestartPolicy` configs → distinct `KANZI_CONFIG_HASH`; restart distribution differs |
| 7 | `test_audit_code_round_trip` | apply restart → resulting `state.provenance` contains `kanzi_gpt_prior_restart` |
| 8 | `test_apply_restart_latent_clip_preserved` | `|blended| <= KANZI_LATENT_CLAMP` after the swap (regression guard for the `1175` clip) |
| 9 | `test_determinism` | identical seed + identical policy → identical `blended` byte-for-byte |
| 10 | `test_protocol_conformance_unchanged` | `assert_adapter_compliance(adapter)` still passes when `gpt_prior_restart=True` |

Plus one regression test for the **combined F-1 + GPT-prior fix**:

| 11 | `test_observe_token_indices_returns_real_prior` | end-to-end `solve_ode → observe_token_indices` returns the AR-prior indices, not uniform random; `MATCHES_REAL_STATE` is True. Agent A already captured the runtime failure pattern (lines 188-192). |

### 1.5 Risk

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **F-1 unfixed ⇒ `prior_entry` lacks `gpt_prior_confidence` AND `src_digest`** | HIGH | F-1 is Phase 1 step 1; without it, test #11 fails by construction |
| **F-2 unfixed ⇒ framework arm = baseline ⇒ new policy unmeasurable** | HIGH | Flag to wave lead before Phase 1 ships; this plan is gated on F-2's land elsewhere |
| **GPT-2 prior overconfidence** (Agent B §5 risk #2) | MEDIUM | `omega_cap=0.30` hard ceiling; provenance records effective `omega` for offline audit |
| **Determinism-under-replay break** (Agent A §4 option 2 hazard) | MEDIUM | signal persisted in native-state entry, not on `self`; seed-only RNG |
| **700 synthetic tests change behaviour** | MEDIUM | synthetic mode degrades to today's scalar blend and emits an audit code; default `gpt_prior_restart=False` |
| **`digest_state` payload change perturbs D.4 vectors** | LOW | refresh pinned vectors deliberately; log the change in commit body |
| **Per-position blend cost vs. scalar blend** | LOW | `(L_z,)` vectorised numpy; ~64 elements; negligible vs. 250 M GPT prior forward |
| **Cross-channel interference** | LOW | `discrete_token_index` untouched (preserved by Agent A §11) |

### 1.6 Paper citations

- **ProtBFN** (Zhang et al., AAAI 2026; arXiv:2411.04220) — restart
  re-anchors to the BFN prior, not fresh noise; R=4 default; entropy
  trigger. Cite in `KanziGPTPriorRestartPolicy.should_restart` docstring.
- **LineageFlow** (Liang et al., ICML 2026; arXiv:2605.22252v2) — learned
  prior outperforms `N(0, I)` for protein sequence restart. Cite in
  `memory_fraction_vector` docstring.
- **CFG-Zero*** (arXiv:2503.18886) — zero-init first 2 ODE steps before
  letting the prior pull; `omega_cap=0.30`. Cite in policy header.

### 1.7 Acceptance gate

- All 11 new tests pass.
- `assert_adapter_compliance(kanzi_adapter_with_policy=True)` passes.
- `KANZI_CONFIG_HASH` differs deterministically with policy config.
- `state.provenance` contains `kanzi_gpt_prior_restart` after one restart
  round.
- Synthetic-mode tests are byte-identical to pre-change baseline (because
  policy default = False and synthetic prior_entry degrades gracefully).
- Real-mode (with F-1 + F-2 fixed) `entropy reduction ≥ 0.05·H_max` over
  R=4 rounds for ≥ 80 % of test sequences (target; assert as test #11
  successor in a follow-up wave).

---

## 2. Fix (b) — `per_position_entropy_reduction`

### 2.1 Goal

Promote the per-position entropy helper that already exists at
`tools/run_controlled_audit.py:702` (`_per_position_entropy`, tested by
`tests/test_algorithm/test_w33_lineageflow_metric_fix.py`, specified in
`docs/theory/operating-regime.md §11.5`) **into a shared adapter-layer
helper**, and expose a *reduction* (baseline entropy − framework entropy)
method on each adapter. Re-point the existing tool at the shared helper
so there is one definition.

The user directive: *"a per-position entropy-reduction metric in both
adapters."*

### 2.2 Architecture

Single helper, `adaptive_reflow/adapters/_adapter_common.py:per_position_entropy`,
copied byte-for-byte from `run_controlled_audit.py:702`. Two thin
adapter methods, `observe_entropy_reduction(trace, *, reference_entropy=None)`,
that compute `H(trajectory[-1])` for the framework value and use
`trajectory[0]` for a within-trajectory baseline (per Agent A §7) — a
self-contained delta that does not require a second run.

### 2.3 Specific code change

| Site | File:line | Action |
| --- | --- | --- |
| Shared helper | `adaptive_reflow/adapters/_adapter_common.py`, append before `__all__` at line 210 | `per_position_entropy(logits)` copied byte-for-byte from `tools/run_controlled_audit.py:702` |
| `__all__` | `_adapter_common.py:210-219` | add `"per_position_entropy"` (sorted) |
| Re-point existing tool | `tools/run_controlled_audit.py:702` | import from `adaptive_reflow.adapters._adapter_common`; delete local def |
| LineageFlow method | `lineageflow.py`, after `observe_token_indices` ends (after 1583, before `inject_forward_noise` banner at 1585) | `observe_entropy_reduction(trace, *, reference_entropy=None)` |
| Kanzi method | `kanzi.py`, after `observe_token_indices` ends (after 1712, before `inject_forward_noise` banner at 1714) | same signature **with caveat documented in docstring**: Kanzi's trajectory is a continuous latent, not a categorical — either compute over the AR-prior categorical (requires F-1 fixed) or document explicitly as a latent-dispersion proxy |
| Tests | `tests/test_adapters/test_kanzi.py` (720 LOC, append after 707); `tests/test_adapters/test_lineageflow.py` (547 LOC, append after 507) | bounds, `≈0` on a spike, `≈log K` on uniform, determinism, degenerate input |
| Theory doc | `docs/theory/operating-regime.md §11.6` (new subsection, append after §11.5) | record the promotion to the adapter layer + the Kanzi caveat; **do not rewrite §11** |

**Signature:**

```python
def per_position_entropy(probs: np.ndarray) -> np.ndarray:
    """H_i = -sum_a p_i(a) log p_i(a) for each position i.

    Bounds: 0 ≤ H_i ≤ log(K) where K is the alphabet size
    (log 20 ≈ 2.996 for amino acids, log 64 ≈ 4.159 for Kanzi discrete
    vocabulary). Per Nature Chem Biol 2026 (s41589-026-02270-6) formula;
    byte-for-byte port of `tools/run_controlled_audit.py:_per_position_entropy`.
    """
    # existing body from run_controlled_audit.py:702 — DO NOT RE-DERIVE

# On each adapter:
def observe_entropy_reduction(
    self,
    trace: np.ndarray,
    *,
    reference_entropy: np.ndarray | None = None,
) -> dict[str, np.ndarray | float]:
    """Per-position entropy reduction baseline → framework.

    `reference_entropy=None` → use `trace[0]` as the baseline
    (within-trajectory reduction). Returns
    `{per_position: (L,), mean: float, fraction_converged: float}`.
    """
```

### 2.4 Test plan

New file: `tests/test_metrics/test_per_position_entropy.py` plus appends
to the two adapter test files.

| # | Test | What it asserts |
| --- | --- | --- |
| 1 | `test_per_position_entropy_uniform_equals_log_K` | uniform `(L, 20)` → `H == log(20)` element-wise |
| 2 | `test_per_position_entropy_spike_is_zero` | one-hot `(L, 20)` → `H == 0` element-wise |
| 3 | `test_per_position_entropy_bounds` | random simplex rows → `0 ≤ H ≤ log(K) + ε` |
| 4 | `test_per_position_entropy_clamp_min` | row with a single 0 entry → finite, no `-inf` |
| 5 | `test_per_position_entropy_determinism` | identical input → identical output byte-for-byte |
| 6 | `test_observe_entropy_reduction_lineageflow_within_trajectory` | `trajectory[0]` = uniform, `trajectory[-1]` = spike → `mean > 0` and `fraction_converged > 0` |
| 7 | `test_observe_entropy_reduction_lineageflow_explicit_reference` | explicit `reference_entropy` overrides `trajectory[0]` |
| 8 | `test_observe_entropy_reduction_kanzi_latent_proxy_documented` | Kanzi method returns a dict with a `caveat: "latent_dispersion_proxy"` key; values are non-negative |
| 9 | `test_existing_w33_metric_test_still_passes` | `tests/test_algorithm/test_w33_lineageflow_metric_fix.py` byte-for-byte unchanged and green after the re-point |
| 10 | `test_run_controlled_audit_helper_removed` | `tools/run_controlled_audit.py` no longer defines `_per_position_entropy` locally; imports from `_adapter_common` |

### 2.5 Risk

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **Re-derivation breaks the existing 6 W33 tests** | HIGH | copy byte-for-byte from `run_controlled_audit.py:702`; do **not** rewrite; test #9 enforces this |
| **Kanzi entropy silently mis-interpreted as residue entropy** | MEDIUM | docstring `caveat`; test #8 asserts the marker; never reuse the §11 formula on a continuous latent without the caveat |
| **Helper divergence between tools/ and adapter/** | MEDIUM | delete the local def at `run_controlled_audit.py:702` in the same commit; test #10 enforces |
| **`log(0)` → NaN propagation** | LOW | `_adapter_common.py` uses `np.log` with clamp (already present in `_per_position_entropy`); test #4 covers |
| **`__all__` order** | LOW | sorted insertion at `_adapter_common.py:210-219`; existing mkdocs build still strict |

### 2.6 Paper citations

- **Nature Chem Biol 2026** (s41589-026-02270-6) — direct citation for the
  `H_i(a) = -p_i(a) log p_i(a)` formula. Cite in
  `_adapter_common.per_position_entropy` docstring.
- **ProRefiner** (Nature Communications 2024; s41467-023-43166-6) —
  bottom-10 % entropy residues are ~99 % precision; the
  `fraction_converged` field is a downstream use. Cite in the return-dict
  contract.
- **AlphaFlow Entropy Bridge** (NVIDIA/Oxford, May 2026) — *rate*
  formulation `R_i(t) = -Σ p_i log p_i(·|x_<i, t)` as an alternative for
  future work; mention in §11.6 but do not implement yet.

### 2.7 Acceptance gate

- All 10 new tests pass.
- `tests/test_algorithm/test_w33_lineageflow_metric_fix.py` passes
  unchanged (regression gate).
- `_per_position_entropy` exists in exactly **one** place
  (`_adapter_common.py`); `rg "_per_position_entropy"` shows only the
  shared helper definition and call sites.
- `docs/theory/operating-regime.md §11.6` is appended, not rewritten.
- `mkdocs build --strict` passes.

---

## 3. Fix (c) — `LineageFlowClassifierAwareRestart`

### 3.1 Goal

Replace the scalar-latent blend at `lineageflow.py:1058-1061` with a
**per-position, confidence-modulated** blend, where the confidence proxy
is the adapter's own per-position categorical `theta` (max-prob or
negative entropy). Combined with the CFG-Zero* zero-init pattern, this
becomes a bounded CFG step `v_combined = (1-ω)·v_flow + ω·v_classifier`
where `ω` is capped by the prediction-gap magnitude.

This is the user directive: *"a classifier-aware restart in
`lineageflow.py`."*

**Naming discipline (per Agent A §8):** if the metric does not actually
call a classifier, do not call it `classifier_confidence_change`. The
upstream `LineageFlowClassifier` (657 M params) lives in
`data/lineageflow_upstream/` and is **not importable in this adapter**
(Agent A §2). Path 6a from Agent A §6 is therefore the honest name:
**`LineageFlowConfidenceAwareRestart`**, where "confidence" comes from
the adapter's own softmax distribution `theta`.

### 3.2 Architecture

Same pattern as Kanzi fix (a): policy class lives in `lineageflow.py`,
signal captured at `solve_ode` time and persisted in the
`_native_states.put(...)` payload. Read back via the existing
`prior_entry` fetch. **No Protocol change.**

Critically (Agent A §2, §11): both renormalisations of `theta` at
`lineageflow.py:1064-1066` and `1073-1075` **must be preserved** —
without them, downstream `argmax` and entropy silently degrade.

### 3.3 Specific code change

| Site | File:line | Action |
| --- | --- | --- |
| New policy class | `lineageflow.py`, new block before line 514 (before `_install_checkpoint_compat`) | ~55 LOC class `LineageFlowConfidenceAwareRestart` |
| Signal capture | `lineageflow.py` `solve_ode` put (analogous to `kanzi.py:1490-1498`) | extend put payload with `theta_max_prob: np.ndarray` of shape `(L=256,)` |
| Policy application | `lineageflow.py:1058-1061` | per-position `m_vec` instead of scalar `m`: `m_vec = policy.memory_fraction_vector(prior_entry, base_m=m)` → per-position blend on the continuous latent |
| **Renormalise (preserve)** | `lineageflow.py:1064-1075` | **must stay** — both renormalisations and the `LINEAGEFLOW_CLAMP` clip unchanged |
| Audit code | `lineageflow.py:248` | `AUDIT_LINEAGEFLOW_CONFIDENCE_RESTART: str = "lineageflow_confidence_restart"` |
| Provenance | `lineageflow.py:1131-1132` | append the new code |
| Digest | `lineageflow.py:1083-1098` | add policy config hash to `digest_state` payload |
| Exports | `lineageflow.py:1694` `__all__` | add `"LineageFlowConfidenceAwareRestart"` (sorted) |
| Confidence-change observer (Agent A §8) | `lineageflow.py`, immediately after the §7 entropy method (after 1583) | `observe_confidence_change(trace, *, reference_max_prob=None)`; round-over-round change in mean max-prob of `theta` |

**Signature:**

```python
class LineageFlowConfidenceAwareRestart:
    def __init__(
        self,
        *,
        max_rounds: int = 1,                       # LineageFlow pattern is single reroute (Agent B §5 #5)
        omega_cap: float = 0.50,                   # ASR prior is family-specific → higher ω OK (Agent B §3 Q3)
        zero_init_steps: int = 2,                  # CFG-Zero*
        prediction_gap_cap: float = 10.0,          # CFG-MP smooth tanh cap
        seed: int = 0,
    ): ...

    def memory_fraction_vector(
        self,
        prior_entry: Mapping[str, Any],
        *,
        base_m: float,
    ) -> np.ndarray:
        """Per-position (L=256,) memory fractions.

        Uses `prior_entry["theta_max_prob"]` (computed at solve_ode time).
        High max-prob → high m (retain more of the previous distribution);
        low max-prob → low m (admit more fresh noise).
        """

    def combine(
        self,
        v_flow: np.ndarray,
        v_classifier: np.ndarray,
        *,
        omega: float,
        round_step_idx: int,
    ) -> np.ndarray:
        """Per Guided Flows (FAIR) + CFG-Zero*.

        CFG-Zero*: zero-init for first 2 steps.
        CFG-MP: cap ω by prediction-gap magnitude via tanh.
        """
```

### 3.4 Test plan

New file: `tests/test_adapters/test_lineageflow_classifier_combine.py`
plus an append to `tests/test_adapters/test_lineageflow.py`.

| # | Test | What it asserts |
| --- | --- | --- |
| 1 | `test_memory_fraction_vector_high_confidence_keeps_prior` | `theta_max_prob ≈ 1` → `m_vec ≈ 1` (retain prior) |
| 2 | `test_memory_fraction_vector_low_confidence_admits_noise` | `theta_max_prob ≈ 1/K` → `m_vec ≈ 0` (fresh noise) |
| 3 | `test_memory_fraction_vector_synthetic_degrades` | synthetic prior_entry → `np.full(L, base_m)`; audit code present |
| 4 | `test_combine_zero_init_first_two_steps` | `round_step_idx in {0, 1}` → returns `v_flow` unchanged |
| 5 | `test_combine_omega_zero_is_pure_flow` | `omega=0` → returns `(1-0)·v_flow + 0·v_classifier == v_flow` |
| 6 | `test_combine_omega_one_is_pure_classifier` | `omega=1` and `round_step_idx >= 2` → returns `v_classifier` |
| 7 | `test_combine_monotonic_in_omega` | `v_combined` interpolation between `v_flow` and `v_classifier` is monotone in `omega` |
| 8 | `test_combine_prediction_gap_caps_omega` | `gap_norm = 100` → `omega_eff < omega_cap`; `gap_norm = 0` → `omega_eff ≈ 0` |
| 9 | `test_apply_restart_double_renorm_preserved` | `theta.sum(-1) ≈ 1.0` after the per-position blend swap (regression guard for `1064-1066, 1073-1075`) |
| 10 | `test_apply_restart_clip_preserved` | `|theta| <= LINEAGEFLOW_CLAMP` after the swap |
| 11 | `test_observe_confidence_change_within_trajectory` | `trajectory[0]` = uniform, `trajectory[-1]` = spike → `mean_change > 0` |
| 12 | `test_audit_code_round_trip` | apply restart → `state.provenance` contains `lineageflow_confidence_restart` |
| 13 | `test_protocol_conformance_unchanged` | `assert_adapter_compliance(lineageflow_adapter_with_policy=True)` passes |

### 3.5 Risk

| Risk | Severity | Mitigation |
| --- | --- | --- |
| **Per-position blend breaks double-renormalisation** | HIGH | tests #9, #10; Agent A §2 explicit warning |
| **`argmax` / entropy silently degrade** | HIGH | tests #9 + existing `test_lineageflow.py:458, 485, 507` |
| **Classifier unavailability (Agent B §5 risk #4)** | MEDIUM | path 6a uses adapter's own `theta_max_prob` — no upstream classifier needed; falls back to today's scalar blend if `theta_max_prob` absent in prior_entry |
| **Naming confusion (Agent A §8)** | MEDIUM | class is `ConfidenceAware`, not `ClassifierAware`; docstring states explicitly: "does not call the upstream `LineageFlowClassifier`" |
| **Single reroute vs. multi-round (Agent B §5 risk #5)** | MEDIUM | `max_rounds=1` default — matches LineageFlow's published single-reroute pattern; not unified with Kanzi's multi-round |
| **Class collision: `LineageFlowConfidenceAwareRestart` vs user-named `LineageFlowClassifierAwareRestart`** | LOW | file exports `ConfidenceAwareRestart`; user directive's "classifier-aware" is honoured semantically (it is classifier-aware *of the adapter's own categorical*, not an external classifier); commit message documents the naming choice |
| **Per-position (L=256,) memory cost** | LOW | 256 floats; negligible |

### 3.6 Paper citations

- **Guided Flows** (Zheng et al., FAIR, 2025) — linear interpolation
  `ṽ = (1-ω)u + ω u_guided` is the principled CFG for FM. Cite in
  `LineageFlowConfidenceAwareRestart.combine` docstring.
- **CFG-MP** (Cai et al., ICML 2026, arXiv:2601.21892) — prediction gap
  `Δv = v_θ(c) - v_θ(∅)` governs guidance sensitivity. Cite in the same
  docstring; informs the `prediction_gap_cap` parameter.
- **CFG-Zero*** (arXiv:2503.18886) — zero-init first 2 ODE steps; informs
  the `zero_init_steps=2` default.

### 3.7 Acceptance gate

- All 13 new tests pass.
- `assert_adapter_compliance(lineageflow_adapter_with_policy=True)` passes.
- The ckpt-compat shim at `lineageflow.py:514` still installs (existing
  tests `test_lineageflow.py:458, 485, 507`).
- Both renormalisations of `theta` still produce valid distributions
  (tests #9 + existing).
- `state.provenance` contains `lineageflow_confidence_restart` after
  one restart round.
- `docs/PLUG_IN_YOUR_MODEL.md` LineageFlow section documents the
  new policy as a reusable pattern (Phase 3 step).

---

## 4. Cross-cutting acceptance: prerequisite fixes F-1, F-2, F-3

Wave 45 cannot claim measurement without these. They are flagged here
because they live **outside** this agent's write scope but block the
acceptance gate for all three fixes above.

### F-1 — `observe_token_indices` returns random tokens (CRITICAL)

**Where:** `adaptive_reflow/adapters/kanzi.py:1490-1498` (and `1205-1214`,
`1755`).
**Action:** add `"src_digest": str(state.native_state_digest)` to each
`_native_states.put(...)` payload. ~2 LOC.
**Why it blocks:** the helper walks the chain via `src_digest` (line
1680), but no entry ever stores one, so the loop breaks on iteration 1
and the method returns the uniform-random fallback at `1695-1710`. Every
Kanzi Tier-3 number since Wave 44 is invalid in both arms.
**Test:** end-to-end `solve_ode → observe_token_indices` returns the
real AR prior, not uniform (test #11 in §1.4).
**Out of scope for the adapter fix itself, but included because the
combined edit at `1490-1498` makes F-1 + signal-capture a single
one-shot change.**

### F-2 — eval loop signature-mismatch (CRITICAL)

**Where:** `tools/run_real_ckpt_eval.py:524-539`.
**Action:** `export_endpoint(cur_bundle)` not `export_endpoint(trace)`;
real `FinalRestartPolicy` not `policy=None`; drop `trace=` / `round_index=`
kwargs; narrow both bare `except`s so signature errors surface.
**Why it blocks:** framework arm exits after one `solve_ode` and is
byte-identical to baseline. This is the mechanical reason
`framework_wins = 0` since Wave 43, misattributed to "metric saturation."
**Out of scope for this agent; escalate before Wave 45 ships.**

### F-3 — `paper_quantities=None` at every call site (MEDIUM)

**Where:** `tools/run_real_ckpt_eval.py:904-905, 1050-1051`; framework
producers in `evidence_driver.py:103` and `derive_default_*` helpers
(`449, 521, 553`).
**Action:** thread real `e_rho` / `sheet_A` / `packing_B` / `cell_C` from
`EvidenceDrivenScheduler` into the call sites. New policies read these
and adapt `omega_cap` accordingly.
**Why it matters:** the parameter exists but no signal flows. Wave 45
policies will read `None` and no-op without this.
**Out of scope for the adapter fix itself; flag alongside F-2.**

---

## 5. Implementation order

Strict. Three phases, each gated on the previous.

### Phase 1 — Kanzi block (highest priority)

| Step | Action | LOC | Files | Acceptance |
| --- | --- | --- | --- | --- |
| 1.1 | Fix F-1 (`src_digest` in put payload) | 3 | `kanzi.py:1490-1498, 1205-1214, 1755` | test #11 in §1.4 passes |
| 1.2 | Add `per_position_entropy` helper | 25 | `_adapter_common.py` (before `__all__`) | tests #1-#5 in §2.4 pass; `_per_position_entropy` no longer in `tools/run_controlled_audit.py:702` |
| 1.3 | Add Kanzi `observe_entropy_reduction` | 30 | `kanzi.py` (after `observe_token_indices`) | tests #6-#8 in §2.4 pass |
| 1.4 | Add `KanziGPTPriorRestartPolicy` class | 60 | `kanzi.py` (before line 638) | tests #1-#10 in §1.4 pass (combined F-1 + signal-capture at `1490-1498`) |
| 1.5 | Re-point `run_controlled_audit.py:702` | -3 | `tools/run_controlled_audit.py` | test #10 in §2.4 passes |
| 1.6 | Append `operating-regime.md §11.6` | +30 | `docs/theory/operating-regime.md` | `mkdocs build --strict` passes |

**Exit criterion:** all §1.7 + §2.7 gates green. Kanzi Tier-3
measurement is no longer random-noise.

### Phase 2 — LineageFlow block

| Step | Action | LOC | Files | Acceptance |
| --- | --- | --- | --- | --- |
| 2.1 | Add LineageFlow `observe_entropy_reduction` | 30 | `lineageflow.py` (after `observe_token_indices`) | tests #6-#7 in §2.4 pass (re-using Phase 1 helper) |
| 2.2 | Add `LineageFlowConfidenceAwareRestart` class | 55 | `lineageflow.py` (before line 514) | tests #1-#13 in §3.4 pass |
| 2.3 | Add `observe_confidence_change` (Agent A §8) | 20 | `lineageflow.py` (after entropy method) | test #11 in §3.4 passes |
| 2.4 | Add `theta_max_prob` to `solve_ode` put payload | 3 | `lineageflow.py` (analogous to `kanzi.py:1490-1498`) | signal captured end-to-end |

**Exit criterion:** all §3.7 gates green.

### Phase 3 — Plumbing + docs

| Step | Action | Files |
| --- | --- | --- |
| 3.1 | Append `PLUG_IN_YOUR_MODEL.md` LineageFlow section (before line 675) | `docs/PLUG_IN_YOUR_MODEL.md` |
| 3.2 | Append `PLUG_IN_YOUR_MODEL.md` Kanzi section (before line 746) | `docs/PLUG_IN_YOUR_MODEL.md` |
| 3.3 | Document the §4 option-1 pattern as a reusable recipe | `docs/PLUG_IN_YOUR_MODEL.md` generic walkthrough appendix |
| 3.4 | Update `framework-freeze-checklist.md` with Wave 45 fixes | `todo/framework-freeze-checklist.md` |
| 3.5 | Verify `mkdocs build --strict` passes | n/a |
| 3.6 | Run `pytest tests/test_adapters/` end-to-end | n/a |

**Exit criterion:** all three fixes documented; no `mkdocs build`
regressions; full adapter test suite green.

---

## 6. Risk register (cross-cutting)

Consolidated from §§1.5, 2.5, 3.5.

| # | Risk | Severity | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| **R-1** | **F-2 unfixed → framework arm = baseline → Wave 45 unmeasurable** | CRITICAL | wave lead | Escalate before Phase 1 ships; this plan is gated on F-2's land elsewhere |
| **R-2** | **F-1 unfixed → Kanzi Tier-3 invalid in both arms since Wave 44** | CRITICAL | Phase 1 step 1.1 | 3-LOC fix; combined with signal-capture edit |
| **R-3** | **F-3 unfixed → `paper_quantities=None` → Wave 45 policies read None and no-op** | HIGH | wave lead (out of scope) | Thread `e_rho` etc. from `EvidenceDrivenScheduler` |
| **R-4** | Per-position blend breaks `theta` double-renormalisation | HIGH | Phase 2 step 2.2 | tests #9, #10 in §3.4; preserve both renormalisations + clip |
| **R-5** | GPT-2 prior overconfidence in Kanzi restart | MEDIUM | Phase 1 step 1.4 | `omega_cap=0.30`; log effective ω in provenance |
| **R-6** | Re-derivation of `_per_position_entropy` breaks W33 tests | MEDIUM | Phase 1 step 1.2 | byte-for-byte port; test #9 in §2.4 |
| **R-7** | Kanzi entropy silently mis-interpreted as residue entropy | MEDIUM | Phase 1 step 1.3 | `caveat: "latent_dispersion_proxy"` in return dict |
| **R-8** | 700 synthetic tests change behaviour | MEDIUM | Phase 1 step 1.4 | synthetic mode degrades to today's scalar blend + audit code; default `gpt_prior_restart=False` |
| **R-9** | Determinism-under-replay break | MEDIUM | all phases | signal persisted in native-state entry, not on `self` |
| **R-10** | `digest_state` payload change perturbs D.4 vectors | LOW | all phases | refresh pinned vectors deliberately; log in commit body |
| **R-11** | Naming confusion: `ConfidenceAware` vs user's `ClassifierAware` | LOW | Phase 2 step 2.2 | commit message + `docs/PLUG_IN_YOUR_MODEL.md` LineageFlow section explains |
| **R-12** | Compute cost: R=4 rounds × ODE solve | LOW | Phase 1 step 1.4 | measure on Kanzi ckpt in Wave 46; budget 4× baseline |
| **R-13** | `__all__` order breaks mkdocs strict | LOW | Phase 1 step 1.2 | sorted insertion |
| **R-14** | `paper_quantities` audit gap | LOW | Phase 1 step 1.4 | add `audit_codes` to `digest_state` payload; provenance records policy class + ω effective |

---

## 7. Files touched (planned)

**Adapters** (in-scope for Wave 45):
- `adaptive_reflow/adapters/_adapter_common.py` (helper, +25 LOC, sorted `__all__`)
- `adaptive_reflow/adapters/kanzi.py` (F-1 fix + GPT-prior policy + entropy method, +96 LOC net)
- `adaptive_reflow/adapters/lineageflow.py` (ConfidenceAware policy + entropy method + confidence-change observer, +110 LOC net)

**Tools / docs** (Phase 3):
- `tools/run_controlled_audit.py` (-3 LOC at line 702, re-point import)
- `docs/theory/operating-regime.md` (§11.6 appended, +30 LOC)
- `docs/PLUG_IN_YOUR_MODEL.md` (two per-model appends + reusable pattern appendix, +80 LOC)

**Tests** (new files):
- `tests/test_adapters/test_kanzi_restart_policy.py` (NEW, ~150 LOC)
- `tests/test_adapters/test_lineageflow_classifier_combine.py` (NEW, ~150 LOC)
- `tests/test_metrics/test_per_position_entropy.py` (NEW, ~100 LOC)
- `tests/test_adapters/test_kanzi.py` (append ~30 LOC, Kanzi entropy method)
- `tests/test_adapters/test_lineageflow.py` (append ~40 LOC, entropy + confidence-change)

**Out of scope** (flagged to wave lead):
- `tools/run_real_ckpt_eval.py:524-539` (F-2)
- `tools/run_real_ckpt_eval.py:904-905, 1050-1051` (F-3)
- `adaptive_reflow/evidence_driver.py` (F-3 producers)
- `adaptive_reflow/contracts/authority.py:55` `FinalRestartPolicy` (not extended — Agent A §4 option 1 is sufficient)

**NOT touched** (preserve list, Agent A §11):
- `_install_gpt_prior_patch` at `kanzi.py:307-465`
- `_install_checkpoint_compat` at `lineageflow.py:514`
- `@implements` decorators (`kanzi.py:808`, `lineageflow.py:695`)
- `assert_adapter_compliance` CI test
- `_adapter_common.py:1-10` byte-stability contract
- `native_config_hash` discipline
- Double-renormalisation in `lineageflow.py:1064-1075`
- `discrete_token_index` untouched at `kanzi.py:1148-1149, 1224-1236`

---

## 8. What this plan does NOT do

To keep the wave scope honest:

1. **No framework-layer changes.** No Protocol extensions, no
   `FinalRestartPolicy` field additions, no `MergeOperator` plumbing.
   `apply_restart_distribution(state, policy)` stays as-is.
2. **No upstream classifier imports.** `LineageFlowClassifier` is not
   touched; the policy uses the adapter's own `theta_max_prob`.
3. **No new experiments.** This is a code-only fix wave. Tier-3
   measurement runs in a follow-up wave once F-2 lands.
4. **No GPU work.** All changes are CPU-verifiable; existing
   `tests/test_adapters/` runs without GPU.
5. **No push.** Per directive, commit the master plan only (this file)
   and do not push.

---

## 9. Verification checklist (commit message template)

```
Wave 45 Agent C: master plan for KanziGPTPriorRestartPolicy,
per_position_entropy_reduction, LineageFlowClassifierAwareRestart

No code changes (READ-ONLY). Adds the synthesis doc
todo/wave45-adapter-fix-master-plan.md that ties together:
- Agent A local review (kanzi/lineageflow architecture + F-1/F-2/F-3
  defects, 3 insertion points, 11-item preserve list)
- Agent B 2026 web research (ProtBFN, LineageFlow, Nature Chem Biol 2026,
  ProRefiner, CFG-MP, Guided Flows, CFG-Zero*)

Plan covers 3 fixes, 3 phases, 14-row risk register, and prerequisite
gating on F-1 + F-2 (flagged to wave lead, out of adapter scope).

Paper citations in plan: ProtBFN (arXiv:2411.04220), Nature Chem Biol
2026 (s41589-026-02270-6), ProRefiner (s41467-023-43166-6), CFG-MP
(arXiv:2601.21892), Guided Flows (FAIR 2025), CFG-Zero*
(arXiv:2503.18886).

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

---

## 10. References

- **Agent A (local review)** — `docs/audit/wave45-local-review.md` (497 lines,
  Agent A's READ-ONLY audit at `ba37ac0`).
- **Agent B (web research)** — `docs/audit/wave45-web-research-2026.md`
  (517 lines, 16 papers across Topics A–E).
- **`docs/theory/operating-regime.md §11`** — the pre-existing entropy
  spec that Wave 45 promotes to the adapter layer.
- **`docs/PLUG_IN_YOUR_MODEL.md`** — per-model plug-in section structure
  (Lines 569–745).
- **`tests/test_algorithm/test_w33_lineageflow_metric_fix.py`** —
  regression gate for the entropy helper.
- **`adaptive_reflow/adapters/_adapter_common.py`** — 218-LOC shared
  module, byte-stability contract at lines 1-10.

---

**End of master plan. READ-ONLY; only `todo/wave45-adapter-fix-master-plan.md` is committed.**