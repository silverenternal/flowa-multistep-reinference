# Wave 45 Agent E — `per_position_entropy_reduction` on the LineageFlow adapter

**Status:** landed (commit below), not pushed.
**Scope:** `adaptive_reflow/adapters/lineageflow.py`,
`tests/test_adapters/test_lineageflow.py`, this doc.
**Depends on:** Wave 45 Agent D, who promoted the P2-W33-C formula into
`adaptive_reflow/adapters/_adapter_common.py` as
`per_position_entropy_reduction`.

---

## 1. What was added

`LineageFlowAdapter.observe_entropy_reduction(trace, paper_quantities=None,
*, reference_theta=None) -> dict[str, float]`, returning
`{"per_position_entropy_reduction": <float>}` under the new exported
constant `PER_POSITION_ENTROPY_REDUCTION`.

The method **re-derives no math**. It selects two `theta` arrays out of
the cached ODE trajectory, converts them to logits, and delegates to
Agent D's shared helper — which stays the single definition of the
formula specified in `docs/theory/operating-regime.md` §11.

Two modes:

| `reference_theta` | Computes | Meaning |
| --- | --- | --- |
| `None` (default) | `H(trajectory[0]) - H(trajectory[-1])` | **Within-trajectory.** Self-contained; needs no second run. Positive = integrating the ODE sharpened the per-position posterior. |
| an array | `H(reference_theta) - H(trajectory[-1])` | **Framework-vs-baseline.** Caller supplies the baseline arm's endpoint. Positive = this run sharpened relative to baseline. |

Signature parity with `observe_token_indices` (`trace` first,
`paper_quantities` second) is deliberate: `tools/run_real_ckpt_eval.py`
discovers metric surfaces by `hasattr` duck-typing, so a future wave can
call both the same way. `paper_quantities` is accepted and ignored — the
entropy reduction is a property of the trajectory alone, and a test pins
that passing one does not change the value.

## 2. Why this is a *plain* computation for LineageFlow

LineageFlow's ODE trajectory state **is** the per-position categorical.
`trajectory` has shape `(N+1, L, K)` with `L = 256` and
`K = LINEAGEFLOW_VOCAB_SIZE = 33` (the Pfam amino-acid alphabet), and
`observe_token_indices` decodes a residue with a plain
`argmax(trajectory[-1], axis=-1)` (`lineageflow.py:1582`). Softmaxing
along the trailing axis therefore yields a genuine residue distribution,
and its Shannon entropy is a residue-level quantity bounded by `log K`.

That is exactly the precondition §11 assumes, so no new justification is
needed — only the promotion from the tools layer to the adapter layer.

## 3. Bug found and fixed en route: probabilities are not logits

This is the substantive finding of the task, and it would have shipped a
near-degenerate metric.

`per_position_entropy_reduction` documents its inputs as **logits** and
applies a numerically-stable softmax along the trailing axis. But
LineageFlow's `theta` is **already row-normalised**: `solve_ode` divides
by `x.sum(axis=-1, keepdims=True)` after every integration step
(`lineageflow.py:1340-1362`), and `test_solve_ode_returns_finite_trace`
pins `traj.sum(axis=-1) == 1`.

Feeding a probability vector into a softmax double-normalises it and
crushes the distribution toward uniform. Measured on a delta-spike:

| Input handed to the helper | uniform → one-hot reduction | Expected (`log 33`) |
| --- | --- | --- |
| raw `theta` (probabilities) | **0.0275** | 3.4965 |
| `log(theta + eps)` | **3.4965** | 3.4965 |

A **127x understatement**. On the real synthetic trajectory the metric
read `0.00107` nats before the fix and `0.987` nats after — i.e. the
broken form was numerically indistinguishable from "no signal", which is
precisely the failure the Wave 45 local review warns about in its
naming-discipline note on F-1 ("how Wave 44's 'real metric' ended up
measuring random noise").

**Fix:** a module-private `_theta_to_logits(theta, eps=1e-12)` that
returns `log(theta + eps)`. This inverts the helper's softmax exactly —
`softmax(log theta) == theta` whenever `theta` sums to 1 (verified
residual `6.3e-12`) — so the helper computes the genuine Shannon entropy
of the residue distribution. The `eps` floor keeps `log(0)` finite for
clamped-to-zero residues and matches the helper's own `eps` convention.

The conversion lives in the **adapter**, not the helper: the helper's
logits contract is correct and shared, and it is each adapter's job to
present its native state in that form. Agent D's file was not touched.

## 4. Tests

Ten tests appended to `tests/test_adapters/test_lineageflow.py`, covering
the five cases the review asked for (bounds, `≈0` on a spike, `≈log K` on
uniform, determinism, degenerate input) plus the delegation and export
checks:

| Test | Pins |
| --- | --- |
| `..._uniform_to_spike_equals_log_k` | the calibration anchor **and** the §3 regression |
| `..._spike_to_uniform_is_negative_log_k` | the metric is signed |
| `..._identical_endpoints_is_zero` | no change → no reduction |
| `..._on_real_trajectory_is_bounded_and_nondegenerate` | finite, in `[-log K, log K]`, and *strictly inside* both bounds — a value pinned at 0 or saturated carries no signal |
| `..._reference_theta_mode` | the two modes differ as documented |
| `..._is_deterministic` | repeat calls and a second adapter agree exactly |
| `..._ignores_paper_quantities` | the ignored argument really is ignored |
| `..._missing_native_state_raises` | `CapabilityMissingError`, not a bogus number |
| `..._matches_shared_helper` | the adapter delegates rather than re-deriving |
| `..._constant_is_exported` | the metric key is importable and in `__all__` |

Tests that need an exact analytic answer pin the cached trajectory to a
controlled `(2, L, K)` uniform/one-hot pair rather than depending on
whatever the synthetic velocity field produces.

**Mutation check.** Removing the `_theta_to_logits` call fails 4 of the
10 tests, so the §3 bug cannot silently regress.

### Result

```
$ python3 -m pytest tests/test_adapters/test_lineageflow.py -q --tb=line
34 passed, 1 skipped, 3 warnings in 3.85s
```

The 1 skip is pre-existing and unrelated (`torch not installed in this
environment`, the real-ckpt shim test).

Broader adapter suite: **989 passed, 66 skipped, 1 failed** in 165s. The
single failure is `test_protocol_deep_audit.py::test_j_audit_inventory_smoke`
and is **pre-existing and unrelated** — verified by `git stash`, it fails
identically without this agent's changes:

```
audit covers Protocol methods {...} but the Protocol declares additional
methods {'observe_token_indices'}; update PROTOCOL_METHOD_SHAPE
```

Wave 44 added `observe_token_indices` to the `FlowMatchingODEAdapter`
Protocol without updating that test's `PROTOCOL_METHOD_SHAPE` table. It
is a one-line fix in `tests/test_adapters/test_protocol_deep_audit.py`,
which is outside this agent's disjoint file scope — flagged for the wave
owner rather than fixed here. Note `observe_entropy_reduction` is **not**
added to the Protocol (it is a concrete-adapter method only), so it does
not extend this failure.

**Note on the runner.** The task specified
`.venvs/lineageflow_venv/bin/python -m pytest`, but that interpreter has
no `pytest` installed (`No module named pytest`); of the 11 sidecar
venvs only `flowmol3`, `kanzi`, `hpsv2` and `wan2_2` carry one. The suite
was run with the system interpreter's pytest 9.1.1 instead. The new code
is stdlib + numpy only, so the sidecar buys nothing here — but the venv
gap is worth closing if lineageflow tests are meant to gate in CI.

## 5. Kanzi deferred

Not implemented for Kanzi, and deliberately so.

Kanzi's trajectory is a **continuous latent**, not a per-position
categorical. A softmax along its trailing axis does not produce a residue
distribution, so the §11 formula would return a number with no
residue-level meaning — a latent-dispersion proxy wearing the name of an
entropy over amino acids. Per the review's naming discipline, that number
must not be called `per_position_entropy_reduction`.

Two honest routes for Phase 3, both out of scope here:

1. Compute the entropy over Kanzi's **AR-prior categorical** (requires
   F-1, fixed by Wave 45 Agent A) — a genuine residue distribution, and
   the direct analogue of what LineageFlow does.
2. Keep the latent computation but name and document it as a
   latent-dispersion proxy, with its own bounds argument.

## 6. Files changed

| File | Change |
| --- | --- |
| `adaptive_reflow/adapters/lineageflow.py` | `+~150` — `observe_entropy_reduction`, `_theta_to_logits`, `PER_POSITION_ENTROPY_REDUCTION`, helper import, `__all__` entry |
| `tests/test_adapters/test_lineageflow.py` | `+~180` — 10 tests + 4 fixtures + 2 imports |
| `docs/audit/wave45-lineageflow-entropy-metric.md` | new (this file) |

Untouched, as scoped: `framework/`, `scheduler/`, `paper_quantities`,
regression vectors, `test_claims`, other adapters, `_adapter_common.py`
(Agent D), `tools/run_real_ckpt_eval.py`.

## 7. Follow-ups for the wave owner

1. **Wire the metric into the eval pipeline.** `run_real_ckpt_eval.py`
   does not call `observe_entropy_reduction` yet — out of scope here
   (Agent B/C own that file). Until it is wired, the metric is available
   but unconsumed, and the Tier-3 sweep will not report it.
2. **Kanzi**, per §5.
3. **Append to `operating-regime.md` §11** recording the promotion to the
   adapter layer plus the §3 probabilities-vs-logits caveat. The review
   asked for this; `docs/theory/` was outside this agent's file scope, so
   it is left for whoever owns that file this wave. The caveat matters
   for any future adapter whose native state is already normalised.
4. **Fix `PROTOCOL_METHOD_SHAPE`** in
   `tests/test_adapters/test_protocol_deep_audit.py` to include
   `observe_token_indices` (pre-existing Wave 44 breakage, see §4).
5. **Install `pytest` in `.venvs/lineageflow_venv`** if lineageflow tests
   are meant to gate in CI under that interpreter.
