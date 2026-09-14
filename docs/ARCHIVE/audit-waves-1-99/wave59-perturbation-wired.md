# Wave 59 Agent 4 — `PerturbationPolicy` wired into Kanzi + LineageFlow

Status: DONE (2026-09-07)

Scope: wire the Phase-3 `PerturbationPolicy` protocol
(`adaptive_reflow/algorithm/perturbation.py`, Wave 59 Agent 3, READ-ONLY
here) into the two primary Tier 3 adapters — `KanziAdapter` and
`LineageFlowAdapter` — **without changing any default behaviour**.

## 1. User constraint honoured

> Default = `UniformFreshPerturbation` (old path). The new path
> (`PaperQuantityAttractorInversion` / BRAI) is **opt-in only**.

Both adapters now take an optional constructor kwarg:

```python
KanziAdapter(..., perturbation: PerturbationPolicy | None = None)
LineageFlowAdapter(..., perturbation: PerturbationPolicy | None = None)
```

`None` instantiates `UniformFreshPerturbation()`. Every existing
`apply_restart_distribution` caller — the eval pipeline, the schedulers,
`tools/run_real_ckpt_eval.py`, the D.4 pinned regression vectors —
therefore keeps the legacy path with no call-site change.

## 2. Byte-stability mechanism (why the default is provably preserved)

The protocol's `UniformFreshPerturbation.propose` seeds from
`(x.shape, t)`. The adapters' legacy restart noise seeds from
`(policy_hash, source_round)` — a **different** seed key, and one the
protocol does not expose (it is an adapter-level concern; documented as
such in the perturbation module docstring).

So rather than routing the default through `propose` (which would rotate
the noise stream and invalidate Wave 47 / 52 / 58 data), the adapters
**dispatch on the policy type**:

| policy | path | noise source |
|---|---|---|
| `UniformFreshPerturbation` (default, or explicit) | PRESERVED inline | `default_rng(sha256(policy_hash, source_round))` — unchanged from Wave 0 |
| any other `PerturbationPolicy` | opt-in | `policy.propose(prior_state, paper_quantities, t)` |

`UniformFreshPerturbation(seed_offset=k)` with `k != 0` adds `k` to the
legacy seed (mod 2^32), so the configurable knob still works without
touching the `k = 0` default.

## 3. Changes per file

### `adaptive_reflow/adapters/kanzi.py`

* New import of `PerturbationPolicy` / `UniformFreshPerturbation`.
* New audit constant `AUDIT_KANZI_PERTURBATION_POLICY =
  "kanzi_perturbation_policy"` — appended to `provenance` **only** on
  the opt-in path, so default provenance tuples are unchanged.
* `__init__`: `perturbation` kwarg; `TypeError` (message
  `perturbation_must_implement_PerturbationPolicy_or_be_None:...`) for
  an argument without a `propose` method.
* `apply_restart_distribution`: the `fresh_x` computation is the only
  changed block. Legacy branch keeps
  `_synthesize_latent_like_tensor(np.random.default_rng(restart_seed))`
  verbatim; the opt-in branch calls `propose` and reshapes to
  `KANZI_STATE_SHAPE`. The blend, clamp, digest, cache and channel
  wiring are untouched.

### `adaptive_reflow/adapters/lineageflow.py`

Same shape, plus one channel-specific step: the amino-acid channel is a
per-position categorical, so the opt-in branch **projects the proposal
back onto the simplex** (clip at 0, row-renormalise) before the blend.
Audit constant `AUDIT_LINEAGEFLOW_PERTURBATION_POLICY`. The provenance
expression was re-parenthesised (its conditional now appends the
perturbation audit in both arms) — a no-op for the default.

### Tests (4 new per adapter, 8 total)

`tests/test_adapters/test_kanzi.py`, `tests/test_adapters/test_lineageflow.py`:

1. `..._default_perturbation_is_uniform_fresh` — no-arg constructor
   installs `UniformFreshPerturbation`, `seed_offset == 0`.
2. `..._default_perturbation_preserves_legacy_restart_blend` — the
   regression test. Asserts (a) implicit default ≡ explicit
   `UniformFreshPerturbation()` (same digest, same array), (b) both
   equal a from-first-principles recomputation of the legacy
   `(policy_hash, source_round)`-seeded blend, (c) no new audit code in
   `provenance`.
3. `..._brai_perturbation_is_opt_in_and_changes_restart` — passing
   `PaperQuantityAttractorInversion(eps_scale=0.25, default_sigma=1.0)`
   with an `e_rho` snapshot on the prior native-state entry produces
   exactly `x + eps * x / sigma^2` as the fresh state (analytic Gaussian
   gradient), emits the new audit code, and yields a digest that differs
   from the default path. LineageFlow additionally asserts the result is
   still a valid row-stochastic categorical.
4. `..._constructor_rejects_non_perturbation_policy` — `TypeError`.

## 4. Paper-quantity plumbing

BRAI needs a paper-quantity snapshot. `apply_restart_distribution`'s
signature is fixed by the `FlowMatchingODEAdapter` protocol, so the
adapters read `prior_entry.get("paper_quantities")` from the native-state
cache (and `prior_entry.get("t", 0.0)` for the time). When absent, BRAI
takes its own documented graceful fallback to uniform-fresh and emits
`brai_no_paper_quantities`. Threading a live snapshot into the cache is
left to the scheduler/eval-pipeline wave (out of this agent's disjoint
file scope).

## 5. Verification

```
$ PYTEST_SERIAL=1 pytest tests/test_adapters/test_kanzi.py \
      tests/test_adapters/test_lineageflow.py -q
90 passed, 6 skipped
```

(44 + 3 skipped Kanzi, 46 + 3 skipped LineageFlow; skips are
`torch` / `kanzi` package absent in the base venv, pre-existing.)

Byte-stability independently corroborated by the D.4 pinned regression
vectors and the D.5 conformance battery:

```
$ PYTEST_SERIAL=1 pytest tests/test_adapters/test_regression_vectors.py \
      tests/test_adapters/test_adapter_common.py \
      tests/test_adapters/conformance_battery.py -q
187 passed, 8 skipped
```

Note on the harness: `tests/conftest.py`'s Wave 60 `serial_tool` session
fixture returns without yielding when `PYTEST_SERIAL` is unset, which
errors every test in the repo at collection-fixture time. That is a
pre-existing failure on `HEAD` (verified with `git stash`), owned by the
Wave 60 agent and outside this agent's file scope; runs above set
`PYTEST_SERIAL=1` to take the yielding branch.

## 6. Not touched

`framework/`, `scheduler/`, merge operator, `paper_quantities`,
`tools/run_real_ckpt_eval.py`, other adapters, and
`adaptive_reflow/algorithm/perturbation.py` (read-only input).
