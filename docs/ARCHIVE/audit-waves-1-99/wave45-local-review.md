# Wave 45 Agent A — local review: kanzi + lineageflow adapter layer

**Date:** 2026-09-07
**Wave:** Wave 45 Agent A
**Mode:** READ-ONLY review. No code changed by this agent.
**Scope:** `adaptive_reflow/adapters/kanzi.py` (1861 LOC),
`adaptive_reflow/adapters/lineageflow.py` (1731 LOC), plus the
framework surfaces they consume.

**Directive being served (user, 2026-09-05):** framework abstraction is
done; all Kanzi / LineageFlow fixes belong in the **adapter layer**, not
the framework layer. Wave 45 wants (a) a GPT-prior-aware restart policy
in `kanzi.py`, (b) a per-position entropy-reduction metric in both
adapters, (c) a classifier-aware restart in `lineageflow.py`.

> **Read §3 before implementing anything.** This review found three
> defects that make the Wave 45 features unmeasurable if shipped on top
> of the current code. Two of them are the reason the Tier-3
> framework-vs-baseline delta has been stuck at zero. Ordering matters:
> §3 first, then §5–§8.

---

## 0. Corrections to the task premise

Four assumptions in the Wave 45 brief do not match the tree at `ba37ac0`.
Implementation agents will waste time if they take them at face value.

| Brief says | Reality |
| --- | --- |
| `framework/interfaces.py` holds the `FlowMatchingODEAdapter` Protocol | It does **not**. That Protocol lives in `adaptive_reflow/universal/adapter.py:272`. `framework/interfaces.py` holds 9 *algorithm-layer* Protocols (`ChannelwiseBlender`, `IntegratorProtocol`, `MergeOperatorProtocol`, …) and no adapter Protocol. |
| Wave 44 Agent A "will add" `observe_token_indices` | Already landed. Protocol `universal/adapter.py:328`; Kanzi impl `kanzi.py:1623`; LineageFlow impl `lineageflow.py:1504`; tests `tests/test_framework/test_adapter_observe_token_indices.py`. Wave 45 **extends** it, not adds it. |
| `RestartBlend` lives in `algorithm/merge_operator.py` | No such class anywhere. `merge_operator.py` has `BoundedMergeOperator` / `IdentityOperator` / `EMAOperator`. The restart-blend surface is `RestartBlenderProtocol` + `LinearBlender` in `algorithm/blender.py:421`. |
| kanzi.py is 1755 LOC | 1861 LOC at `ba37ac0` (Wave 44 Agent D's shrink + `observe_token_indices` landed after the brief was written). All line numbers below are against `ba37ac0`. |

One more, load-bearing: **neither adapter's `apply_restart_distribution`
receives paper quantities or the trace.** The signature is
`(self, state: StateBundle, policy: RestartPolicy) -> StateBundle`, and
`RestartPolicy` (= `contracts/authority.py:55 FinalRestartPolicy`) carries
only `beta_by_channel` / `alpha_by_channel` /
`fresh_noise_floor_by_channel` / `schedule_sample` / hashes — **no
`sheet_A`, `packing_B`, `cell_C`, or `e_rho` field**. See §4 for what this
forces.

---

## 1. Current `kanzi.py` architecture

**Model.** Kanzi (ICLR 2026, `arXiv:2510.00351`) is a two-stage
continuous-tokenizer flow autoencoder for proteins: a ~30 M encoder maps a
sequence to `L_z=64` latent tokens of dim `d=64`; a ~250 M autoregressive
GPT prior decodes latents back to residues.

**Channels (3).** `protein_latent` (continuous, `(64, 64)`),
`discrete_token_index` (discrete, `(64,)`, vocab 64), `pfam_family_cond`
(conditioning ref).

**The load-bearing asymmetry.** The ODE integrates the **continuous
latent only**. `discrete_token_index` is AR-prior sampler state that is
*carried across* the protocol boundary untouched — `apply_restart_distribution`
explicitly leaves it alone (`kanzi.py:1148-1149`, `1224-1236`), and so does
`observe_endpoint` (`1576-1586`). This is why Kanzi's discrete channel
cannot be recovered by an argmax over the trajectory the way
LineageFlow's can, and it is the root of finding **F-1**.

**Protocol methods, in file order:**

| # | Method | Line | Notes |
| --- | --- | --- | --- |
| 1 | `capabilities` | 969 | returns `KanziCapabilities` (766) |
| 0 | `_resolve_conditioning` | 984 | LRU conditioning cache keyed on `family_id` |
| 2 | `build_initial_state` | 1013 | stores `x0` + `discrete_idx` (put at 1058) |
| 3 | `export_endpoint` | 1108 | |
| 4 | `detach_and_validate_endpoint` | 1121 | |
| 5 | `apply_restart_distribution` | 1135 | latent-space blend; **the GPT-prior hook site** |
| 6 | `compose_condition` | 1264 | resolves `family_id` / `guidance_scale` / `num_steps` / `sampler_id` / `conditioning_cache_hash` into `delta_spec` |
| 7 | `_velocity_field` / `solve_ode` | 1342 / 1371 | Euler or Heun, `num_steps+1` grid, clamp `±KANZI_LATENT_CLAMP` |
| 8 | `observe_endpoint` | 1520 | |
| 9 | `export_trajectory` | 1609 | `(T, 64, 64)` |
| 9 | `observe_token_indices` | 1623 | Wave 44; **defective — see F-1** |
| 10 | `inject_forward_noise` | 1718 | optional, `hasattr`-detected by the runner |

**Framework hooks it actually consumes** (thin — this adapter is already
well-shrunk): `_adapter_common.memory_fraction_for` (1162),
`.digest_state`, `.make_ref`, `.NativeStateCache`,
`.make_adapter_capabilities`; `universal.state.validate_state_bundle`;
`universal.adapter.FlowMatchingODEAdapter` + `@implements`.
It does **not** consume `algorithm/blender.py`, `merge_operator.py`,
`scheduler/_core.py`, or `evidence_driver.py` — the restart blend math is
inlined at `1173-1175`.

**Restart math today** (`1162-1175`): `beta, m = memory_fraction_for(policy,
"protein_latent")` → seed from `sha256(policy_hash, next_round)` →
`fresh_x = _synthesize_latent_like_tensor(rng)` → `blended = m*prior +
(1-m)*fresh` → clip. Single channel, single blend, no model-side signal.

**GPT-prior monkey-patch (Wave 40 Agent B) — PRESERVE.** `kanzi.py:307-465`.
`_install_gpt_prior_patch()` (349) fixes upstream `kanzi.models.GPT.forward`
passing `block_mask` into the wrong `TransformerBlock.forward` slot, which
broke the `gpt_prior=True` loss branch in `DAE.forward`. The patch
introspects `TransformerBlock.forward` (395-397) to choose positional vs
kwarg, always forwards `score_mod=None` (404), is idempotent via the
`_kanzi_gpt_prior_patched` marker (385, 445), and is installed at import
time inside a bare `try/except` (459-465) so synthetic mode stays
import-safe. Four tests cover it (`test_kanzi.py:511, 533, 551, 608`).

---

## 2. Current `lineageflow.py` architecture

**Model.** LineageFlow (ICML 2026, `arXiv:2605.22252`), Pfam-phylogeny-aware
protein flow matching. Published ckpt = ESM-2-650M-style encoder (33-token
AA vocab, hidden 1280, ~657 M params) + time-conditioned flow head.

**Channels (2).** `amino_acid_categorical` (discrete, `(256, 33)` —
per-position categorical, `LINEAGEFLOW_STATE_SHAPE` at 190),
`pfam_family_cond`.

**The contrast with Kanzi.** Here the ODE state **is** the per-position
categorical `theta`. So the trajectory's last slice is already the
distribution over residues, and `observe_token_indices` is a plain
`argmax(trajectory[-1], axis=-1)` (`1582`) — correct, no cache-walk needed.
This same fact makes LineageFlow the natural home for the entropy metric
(§7): the softmax-entropy of `theta` is directly available.

**Protocol methods:** `capabilities` 857; `_put_native_state` 864 /
`_evict_native_state` 873 / `_put_conditioning` 876 /
`_resolve_conditioning` 885; `build_initial_state` 909;
`export_endpoint` 989; `detach_and_validate_endpoint` 1003;
**`apply_restart_distribution` 1017**; `compose_condition` 1140;
`_velocity_field` 1214 / `solve_ode` 1252; `observe_endpoint` 1408;
`export_trajectory` 1487; **`observe_token_indices` 1504**;
`inject_forward_noise` 1589.

**Restart math today** (`1043-1075`): same `memory_fraction_for` blend as
Kanzi, plus row-renormalisation to keep `theta` a valid distribution
(1064-1066), a defensive clip to `LINEAGEFLOW_CLAMP` (1071), and a second
renormalisation (1073-1075). Any classifier-aware change **must keep both
renormalisations** or downstream `argmax` / entropy silently degrades.

**Ckpt-compat shim — PRESERVE.** `_install_checkpoint_compat()` at 514
(the Wave 36 Agent C / Wave 39 5-LOC `SamplerConfig` shim that unblocks
`torch.load` on the real ckpt). Tests: `test_lineageflow.py:458, 485, 507`.

**`LineageFlowClassifier` is NOT in this file.** Verified: zero
occurrences of `classifier` in `lineageflow.py`. The 657 M-param
`LineageFlowClassifier` is an **upstream** class in
`data/lineageflow_upstream/models/model.py`, reachable only via
`sys.path.insert` from the sidecar tool `tools/run_lineageflow_real_ckpt.py`
(upstream ships no `setup.py`). This tightly constrains item (c) — see §6.

---

## 3. Three defects found — fix these first

### F-1 (CRITICAL) — Kanzi `observe_token_indices` always returns random tokens

`observe_token_indices` (1623) walks a native-state chain looking for
`discrete_idx`, hopping via `src_digest`:

```
1680:  src_digest = str(traj_entry.get("src_digest", ""))
1681:  for _ in range(int(KANZI_NATIVE_STATES_MAXSIZE)):
1682:      if not src_digest: break
```

**No stored native-state entry ever contains a `src_digest` key.** All five
`_native_states.put(...)` payloads in the file:

| put site | stored keys |
| --- | --- |
| 1058 `build_initial_state` | `x0, discrete_idx, source_round, mode, conditioning_hash` |
| 1205 `apply_restart_distribution` | `x0, discrete_idx, source_round, mode, conditioning_hash` |
| **1490 `solve_ode`** | `trajectory, t_grid, mode, conditioning_hash` |
| 1552 `observe_endpoint` | `x, t, mode, conditioning_hash` |
| 1755 `inject_forward_noise` | `x0, discrete_idx, source_round, mode, conditioning_hash` |

`src_digest` appears only inside the `digest_state({...})` payloads that are
*hashed* (1192, 1476, 1542) — never in the entry that is *stored*. So
line 1680 always yields `""`, line 1682 breaks on the first iteration,
`discrete_idx` stays `None`, and control always reaches the
"degenerate cache-miss fallback" at 1695-1710: a uniform random draw over
`[0, 64)`.

Runtime confirmation:

```
real AR prior  [:8]: [51, 24, 24, 18, 52, 45, 30, 47]
observed       [:8]: [42, 35, 3, 5, 9, 8, 34, 56]
MATCHES REAL STATE : False
IS RANDOM FALLBACK : True
```

**Consequence.** `tools/run_real_ckpt_eval.py:_real_protein_sequence_validity_rate`
(860-1010) consumes this and reports it as a *real* metric labelled
`"adapter.observe_token_indices + mod-20 AA proxy (Wave 44 Tier-3 close)"`.
It is measuring uniform noise. Any Kanzi Tier-3 number produced since
Wave 44 is invalid, in both arms.

**Fix (adapter layer, ~2 LOC).** Store the provenance you already hash:
add `"src_digest": str(state.native_state_digest)` to the `solve_ode` put
payload at **1490-1498** (and, for multi-round chains, to the puts at
1205-1214 and 1755). Then the existing walk works unchanged. Keep the
fallback, but have it append an audit code so a silent random return can
never again be mistaken for a real measurement.

*Note:* LineageFlow is unaffected — it reads the trajectory directly.

### F-2 (CRITICAL) — the framework arm never restarts, so Tier-3 delta is 0 by construction

`tools/run_real_ckpt_eval.py:524-539` (framework round loop):

```python
endpoint = adapter.export_endpoint(trace) if hasattr(...) else None   # 526
if endpoint is None:
    break                                                            # 531
cur_bundle = adapter.apply_restart_distribution(
    bundle=cur_bundle, trace=trace, policy=None, round_index=int(r), # 532-534
)
```

Both calls are signature-mismatched against both adapters:

- `export_endpoint(state: StateBundle)` is handed a **trace** → `AttributeError`,
  swallowed by the bare `except` at 527 → `endpoint = None` → **`break` at
  round 0**.
- `apply_restart_distribution(state, policy)` is called with
  `bundle=` / `trace=` / `round_index=` → `TypeError: got an unexpected
  keyword argument 'bundle'`. (Unreached, because the `break` fires first.)

Runtime confirmation:

```
export_endpoint(trace) RAISES -> AttributeError -> endpoint=None -> break
eval-style restart call RAISES TypeError -> unexpected keyword argument 'bundle'
```

**Consequence.** The "framework" arm executes exactly one `solve_ode` and
exits the loop — it is byte-identical to the baseline arm. This is the
mechanical explanation for the long-running `framework_wins = 0` /
`TIE_AT_SATURATION` observations that Waves 43/44 attributed to metric
saturation. It is not saturation; the restart blend never runs.

**Fix** is in `tools/run_real_ckpt_eval.py` (outside this agent's write
scope, and outside the "adapter layer" directive — flag it to the wave
lead): call `export_endpoint(cur_bundle)`, build a real `FinalRestartPolicy`
instead of `policy=None`, drop `trace=`/`round_index=`, and narrow both
bare `except`s so a signature error surfaces instead of degrading to
baseline. **Do not add a `**kwargs`-tolerant shim to the adapters to
paper over this** — that would hide the bug and violate the Protocol.

### F-3 (MEDIUM) — `paper_quantities` is `None` at every call site

Both `observe_token_indices` implementations document `paper_quantities` as
"a no-op consumer (Wave 44 surface only; Wave 45 may use `e_rho` /
`sheet_A` …)" (`kanzi.py:1651-1654`, `lineageflow.py:1533-1537`). Both eval
call sites hardcode `paper_quantities=None`
(`run_real_ckpt_eval.py:904-905, 1050-1051`), with a comment saying Wave 45
will thread it. Confirmed at runtime: varying the argument changes nothing.

So the *parameter exists but no signal flows through it.* Wave 45's
paper-quantity-aware behaviour needs the producer side wired too, or every
new policy will read `None` and no-op. `EvidenceDrivenScheduler`
(`evidence_driver.py:103`) and the `derive_default_*` helpers (449, 521,
553) are the framework-side producers of `e_rho`; `theory.paper_quantities`
has `sheet_evidence_A` / `root_cell_packing_B` / `per_cell_coefficient_C` /
`exterior_gap_e_rho`.

---

## 4. Where a model-specific restart policy can get its signal

`apply_restart_distribution(state, policy)` sees no trace and no paper
quantities (§0). Four options, ranked:

1. **`compose_condition` → `delta_spec` → native-state entry (RECOMMENDED).**
   `compose_condition` already writes derived values into `delta_spec`
   (`kanzi.py:1300-1330`) and `solve_ode` reads them back (1388-1418). Have
   `solve_ode` persist the policy-relevant signal into its native-state
   entry (the same put that F-1 fixes), then have
   `apply_restart_distribution` read it from `prior_entry` — which it
   already fetches at 1156. **No Protocol change, no framework change,
   fully inside the adapter layer.**
2. **Adapter-instance state**: stash last-round signal on `self` in
   `solve_ode`/`observe_endpoint`. Simple, but breaks determinism-under-
   replay and the LRU discipline. Avoid.
3. **Extend `FinalRestartPolicy`** with a paper-quantity field. Clean, but
   it is a *framework/contract* change — violates the directive, and
   perturbs `policy_hash`.
4. **Add a Protocol kwarg.** Breaks `@runtime_checkable` conformance for
   all 16 adapters. No.

Take option 1 for both (a) and (c).

---

## 5. Insertion point — `KanziGPTPriorRestartPolicy`

**Concept.** Today the restart blend uses one scalar `m` for the latent and
ignores the AR prior entirely. A GPT-prior-aware policy modulates `m`
per-position (or per-latent-token) using AR-prior confidence: where the GPT
prior is confident, retain more prior latent (higher `m`); where it is
uncertain, admit more fresh noise (lower `m`) so re-inference can explore.
This makes the restart *model-aware* rather than schedule-only.

| What | Where | Action |
| --- | --- | --- |
| Policy class `KanziGPTPriorRestartPolicy` | `kanzi.py`, new block after `_synthetic_family_conditioning` ends (**before line 638**, the `# torch-mode helpers` banner) | new ~60 LOC; stdlib+numpy only; must be import-safe without `torch` |
| Signal capture | `kanzi.py:1490-1498` (`solve_ode` put) | add `src_digest` (F-1) **and** the GPT-prior confidence vector — one edit, both fixes |
| Policy application | `kanzi.py:1173-1175` (replace scalar `m` blend) | `m_vec = policy_obj.memory_fraction_vector(prior_entry, base_m=m)`; blend per-token; **keep the clip at 1175** |
| Audit code | `kanzi.py:270` (next to `AUDIT_KANZI_RESTART_BLEND`) | add `AUDIT_KANZI_GPT_PRIOR_RESTART: str = "kanzi_gpt_prior_restart"`; append to `provenance` at **1256** |
| Digest | `kanzi.py:1189-1204` | add the policy's config hash to the `digest_state` payload so a policy change yields a distinct `native_state_digest` |
| Exports | `kanzi.py:1821` `__all__` | add both new names (sorted) |
| Constructor opt-in | `kanzi.py:864` `__init__` | `gpt_prior_restart: bool = False`, threaded into `KANZI_CONFIG_HASH` provenance |

**Constraints.** Synthetic mode has no GPT prior — the policy must degrade
to today's scalar blend and emit an audit code saying so, or the 700-odd
synthetic tests change behaviour. Default **off** until F-2 is fixed,
otherwise the policy is unmeasurable.

---

## 6. Insertion point — `LineageFlowClassifierAwareRestart`

**Blocker to resolve first.** The classifier is upstream-only (§2), not
importable in-process. Three honest paths:

- **6a (RECOMMENDED for Wave 45).** Use the adapter's *own* per-position
  categorical as the confidence proxy — max-prob or negative entropy of
  `theta`, which the adapter already holds. Needs no classifier, works in
  synthetic **and** torch mode, and composes directly with §7. Name it for
  what it measures (`LineageFlowConfidenceAwareRestart`) rather than
  claiming a classifier it does not call.
- **6b.** Accept externally-computed classifier logits through
  `compose_condition`'s `delta_spec` (per §4 option 1). Real classifier
  signal, but the caller must run the 657 M model in the sidecar and the
  adapter degrades whenever the key is absent.
- **6c.** Import the upstream classifier in-adapter. Rejected: `sys.path`
  hackery + a 657 M CPU forward per round; would make the adapter's test
  surface depend on the sidecar venv.

| What | Where | Action |
| --- | --- | --- |
| Policy class | `lineageflow.py`, new block before `_install_checkpoint_compat` (**before line 514**) | ~55 LOC |
| Application | `lineageflow.py:1058-1061` | per-position `m_vec` instead of scalar `m` |
| **Renormalise** | `lineageflow.py:1064-1075` | **must stay** — both renormalisations and the clip |
| Audit code | `lineageflow.py:248` | `AUDIT_LINEAGEFLOW_CONFIDENCE_RESTART` |
| Provenance | `lineageflow.py:1131-1132` | append the new code |
| Digest | `lineageflow.py:1083-1098` | add policy config hash |
| Exports | `lineageflow.py:1694` `__all__` | add new names |

---

## 7. Insertion point — `per_position_entropy_reduction`

**The math already exists and is already blessed.**
`docs/theory/operating-regime.md` **§11 (lines 667-759)** specifies this
metric — motivation, formula, bounds `[0, log K]`, why not ESM-2 NLL, and
6 tests. The helper is implemented at
**`tools/run_controlled_audit.py:702` `_per_position_entropy`** and tested
via `tests/test_algorithm/test_w33_lineageflow_metric_fix.py`.

It lives in a **tools script**, not the adapter layer. Wave 45's job is to
promote it to a shared adapter-layer helper and expose a *reduction*
(baseline entropy − framework entropy) per adapter. Do **not** re-derive
the formula; port it verbatim so the existing 6 tests keep passing.

| What | Where | Action |
| --- | --- | --- |
| Shared helper | `adaptive_reflow/adapters/_adapter_common.py` (218 LOC), append before `__all__` at **210** | `per_position_entropy(logits)` copied byte-for-byte from `run_controlled_audit.py:702`; then re-point that tool at the helper so there is one definition |
| `__all__` | `_adapter_common.py:210-219` | add `"per_position_entropy"` (sorted) |
| LineageFlow method | `lineageflow.py`, after `observe_token_indices` ends (**after 1583**, before the `inject_forward_noise` banner at 1585) | `observe_entropy_reduction(trace, *, reference_entropy=None)`; entropy of `trajectory[-1]`, and of `trajectory[0]` for a within-trajectory reduction — a self-contained delta that needs no second run |
| Kanzi method | `kanzi.py`, after `observe_token_indices` ends (**after 1712**, before the banner at 1714) | same signature. **Caveat:** Kanzi's trajectory is a *continuous latent*, not a categorical — softmax over a latent axis is not a residue distribution. Either compute entropy over the AR-prior categorical (needs F-1 fixed) or document explicitly that Kanzi's variant is a latent-dispersion proxy. Do not silently reuse the §11 formula on the latent and call it per-position entropy. |
| Tests | `tests/test_adapters/test_kanzi.py` (720 LOC, append after 707); `test_lineageflow.py` (547 LOC, append after 507) | bounds, `≈0` on a spike, `≈log K` on uniform, determinism, degenerate input |
| Theory doc | `operating-regime.md` §11 | **append** a Wave 45 subsection recording the promotion to the adapter layer + the Kanzi caveat. Do not rewrite §11. |

Note `docs/theory/operating-regime.md` §11.5 already flags that re-running
the comparison is a follow-up — **F-2 is why that re-run never showed
anything.**

---

## 8. Insertion point — `classifier_confidence_change` (lineageflow)

Same upstream constraint as §6. Under path 6a this metric is the
round-over-round change in mean max-probability of `theta` — an honest
adapter-side confidence signal. Under 6b it is the change in externally
supplied classifier confidence.

| What | Where |
| --- | --- |
| Method `observe_confidence_change(trace, ...)` | `lineageflow.py`, immediately after the §7 method (**after 1583**) |
| Constant | `lineageflow.py:248` block |
| `__all__` | `lineageflow.py:1694` |
| Tests | `tests/test_adapters/test_lineageflow.py` after 507 |
| Doc | `PLUG_IN_YOUR_MODEL.md` LineageFlow section (§9) |

**Naming discipline:** if the metric does not call a classifier, do not
call it `classifier_confidence_change`. Mis-naming it is how Wave 44's
"real metric" ended up measuring random noise (F-1).

---

## 9. Where to document the pattern

`docs/PLUG_IN_YOUR_MODEL.md` (817 LOC) is organised as a generic Step 1-5
walkthrough (lines 42-467) followed by per-model "Plug-in candidate"
sections. **Append to the two existing model sections; do not touch the
generic walkthrough** — a model-specific restart policy is exactly not the
minimum an integrator must implement.

- **LineageFlow** — section at **line 569**, ends at 674 (next heading
  `## Plug-in candidate: Kanzi` at 675). Insert before 675.
- **Kanzi** — section at **line 675**, ends at 745 (next heading
  `## Plug-in candidate: FreqFlow` at 746). Insert before 746.

Document as a reusable pattern: *"how to add a model-specific restart
policy without touching the framework"* — the §4 option-1 route
(`compose_condition` → `delta_spec` → native-state entry → restart), the
audit-code + digest discipline, and the synthetic-mode degradation rule.

`mkdocs.yml:194` lists `audit/*.md` under `not_in_nav`, so this review file
does not need a nav entry and will not break `mkdocs build --strict`.

## 10. What the framework guarantees (so the adapter need not re-derive it)

From `operating-regime.md` §1.4, §3, §10, §13:

- The framework does **not** guarantee improvement. §1.2 records the
  a-priori regime as **FALSIFIED on `twodim_fm`**. Adapters must not assume
  a positive delta.
- Default scheduler is paper-quantity-driven `codimension_sheet` (§10, §12).
- Per-channel `beta` floor lift `max(1-beta, e_rho/4)` is provided by
  `_adapter_common.memory_fraction_for(..., exterior_gap_e_rho=...)` —
  **already available and currently unused by both adapters** (they call
  the 2-arg form). Wave 45 policies should pass `e_rho` and the
  `audit_codes` list rather than re-implementing a floor.
- Lemma-4 floor `|F_g|² ≥ e_rho` belongs to `MergeOperatorProtocol`
  (`interfaces.py:204`) — algorithm layer, not adapter.

---

## 11. Preserve list (do not regress)

| Item | Location | Guard |
| --- | --- | --- |
| **GPT-prior monkey-patch (Wave 40 Agent B)** | `kanzi.py:307-465`; marker 346/450; import-time install 459-465 | `test_kanzi.py:511, 533, 551, 608` |
| Idempotency marker semantics | `kanzi.py:385, 445` | re-install must stay a no-op |
| Import-safety without `torch` | `kanzi.py:459-465`; `torch_is_available` 295 | synthetic mode is the canonical test surface |
| LineageFlow ckpt-compat shim | `lineageflow.py:514` | `test_lineageflow.py:458, 485, 507` |
| Double renormalisation of `theta` | `lineageflow.py:1064-1066, 1073-1075` | validity of `argmax` + entropy |
| `discrete_token_index` untouched by restart | `kanzi.py:1148-1149, 1224-1236` | AR state is not ODE state |
| Conditioning cache reuse across restart | `kanzi.py:1177-1181`; `lineageflow.py:1077-1081` | the optimisation that makes re-inference cheap |
| Digest determinism / D.4 vectors | all `digest_state` payloads | changing a payload changes `native_state_digest`; refresh pinned vectors deliberately |
| `@implements` + Protocol conformance | `kanzi.py:808`, `lineageflow.py:695` | `assert_adapter_compliance` CI test |
| `_adapter_common` byte-stability contract | `_adapter_common.py:1-10` | digests are load-bearing for `native_config_hash` |

---

## 12. Recommended sequencing

1. **F-1** — store `src_digest` in Kanzi's `solve_ode` put (2 LOC). Add a
   test asserting the returned indices equal the stored AR prior, so the
   random fallback can never silently return again.
2. **F-2** — fix the eval loop's two call sites. Until this lands, no Wave
   45 feature is measurable, because the framework arm is the baseline.
   Owner outside the adapter layer; escalate.
3. **§7 entropy helper** — promote from `tools/`, single definition, port
   verbatim. Lowest risk, highest immediate value.
4. **F-3 + §5/§6 restart policies** — thread paper quantities per §4
   option 1; ship default-off.
5. **§8 confidence metric**, then **§9 docs**.

Items 1-3 are cheap, verifiable, and unblock measurement. Items 4-5 are
only worth doing once 1-2 prove the harness can see a difference at all.

---

## 13. Verification performed by this agent

Read-only. Every claim above was checked against `ba37ac0`:

- Protocol location, `observe_token_indices` presence, `RestartBlend`
  absence, `LineageFlowClassifier` absence — `grep` over the tree.
- F-1 — static scan of all five `_native_states.put` payloads **plus** a
  runtime check showing the returned array equals the random fallback and
  differs from the stored AR prior.
- F-2 — `inspect.signature` on both adapters vs. the eval's kwargs, **plus**
  runtime reproduction of the `AttributeError` and the `TypeError`.
- F-3 — runtime check that varying `paper_quantities` changes nothing.
- Entropy helper provenance — located at `run_controlled_audit.py:702`,
  imported by `test_w33_lineageflow_metric_fix.py`, specified in
  `operating-regime.md` §11.
- `mkdocs.yml:194` `not_in_nav: audit/*.md`.
