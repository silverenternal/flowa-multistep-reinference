# Wave 173 P1 — Kanzi framework NFE-invariance bug audit

## Symptom

Wave 172b P1 produced the following framework-arm FASTA sha256s for kanzi:

| NFE | kanzi framework sha256 |
|-----|------------------------|
| 50  | `aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94` |
| 100 | `aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94` |
| 200 | `aa190a396725533a0ff142b35330bfd1a5f29e1ad013b87ea7734ccfc7222d94` |

All three are **byte-identical**. The corresponding lineageflow framework-arm
sha256s differ across NFE (per-record sequence bytes change as expected).

The kanzi framework path therefore **ignores `--nfe`** in the wave172b FASTA
generator, which is the specific bug this audit pins down.

## Bug location

The byte-identicality is rooted in **how the wave172b kanzi FASTA generator
reads the framework trajectory back out**, not in the solve path itself. The
NFE parameter IS propagated all the way to the kanzi solver; the issue is
that the output channel it lands on is decoupled from `num_steps`.

### Call chain (verified end-to-end)

1. **`tools/w172b_gen_kanzi_fastas.py:146`** — `_framework_emit_sequence`
   calls `_solve_framework(adapter, nfe=NFE_PER_RECORD, ...)` with the
   per-record NFE (default 10, overridable via `--nfe`).
2. **`tools/eval/framework.py:434-` `_solve_framework`** — splits `nfe` into
   `nfe_per_round_list` and emits an `ODEConditionDelta(delta_spec={"num_steps":
   per_round_nfe, ...})` for each round. NFE propagation is correct.
3. **`adaptive_reflow/adapters/kanzi.py:2279-` `solve_ode`** — reads
   `num_steps = int(condition.delta_spec.get("num_steps", self._num_steps))`
   at line **2296** and uses it to build `t_grid = np.linspace(0, KANZI_T_END,
   num_steps + 1)` at line **2343**. The trajectory length and digest do vary
   with `num_steps`. NFE consumption is correct.
4. **`tools/w172b_gen_kanzi_fastas.py:159-160`** — calls
   `adapter.observe_token_indices(trace, paper_quantities=None)` and reads
   `obs_dict["discrete_token_index"]`.
5. **`adaptive_reflow/adapters/kanzi.py:2548-2645` `observe_token_indices`**
   — walks the native-state chain `traj_entry -> src_digest -> prior_entry`
   (line **2608**) and returns `prior_entry["discrete_idx"]` (line **2612**).
   The prior entry was populated once in `_build_initial_state_and_condition`
   (line **1876** `discrete_idx: np.asarray(...)`) and is **frozen** for the
   lifetime of the cache.

### Root cause (one-liner)

The kanzi framework FASTA is built from the AR-prior side channel
(`discrete_token_index`), which is a fixed property of the initial-state
prior entry. The ODE integration's `num_steps` controls the **trajectory's
length and digest** but does **not** mutate the prior entry's
`discrete_idx` — so `observe_token_indices` returns the same `(L_z,)` int
array regardless of NFE, and the FASTA bytes are invariant.

### Why lineageflow varies with NFE (contrast)

`adaptive_reflow/adapters/lineageflow.py:2210-` `observe_token_indices`
reads `argmax(trajectory[-1], axis=-1)` — the **trajectory's final-step
categorical** — so the output is a direct function of `num_steps` (the
trajectory is `(N+1, L, K)` and the final-step argmax changes as `N`
grows). Lineageflow is therefore correctly NFE-sensitive.

## Why kanzi pLDDT loses (-0.28)

Wave 172b P3 reported baseline 57.42 vs framework 57.15 (-0.28). The
mechanism:

* Kanzi's framework trajectory is consumed by the foldability / structure
  metric path (OmegaFold pLDDT on CA coords decoded from
  `kanzi_latent_to_coords`).
* The framework solver runs at the per-round NFE the FASTA generator
  passed (e.g. 50/100/200), but the kanzi trajectory in synthetic mode
  is a deterministic Euler/Heun roll-out from a tiny perturbation of
  `x0` (line **2356**: `x0 + 1e-6 * perturb_rng.standard_normal(x0.shape)`).
  At higher NFE the trajectory samples more of the same low-energy band
  and converges to a similarly-low-diversity endpoint.
* The baseline path is a bare-RNG draw (per the wave172b P1 spec), which
  in synthetic mode lands on a different latent-bucket than the framework
  solver at the default NFE. Because the framework's value-add in
  synthetic mode is concentrated in the (untouched) AR-prior side
  channel, the framework trajectory looks statistically similar to
  baseline noise on a structure-level metric like pLDDT.

The NFE-invariance bug is **independent** of the pLDDT delta but is the
upstream reason the wave172b kanzi cell cannot demonstrate a
NFE-scaling curve at the FASTA byte level. Once NFE is wired through to
`discrete_idx` (see fix below), the framework FASTA should diverge
across NFE and the kanzi pLDDT curve can be re-measured against a
non-degenerate framework signal.

## Fix design

**Goal**: thread `--nfe` to the kanzi framework FASTA so the per-cell
sha256 varies with NFE (matching the lineageflow contract) and the
pLDDT NFE curve can be re-measured honestly.

**Approach** (one of two, listed in order of preference):

1. **Add an NFE-dependent perturbation to the prior entry's
   `discrete_idx`** (preferred). When `_solve_framework` emits the
   per-round `ODEConditionDelta`, the kanzi adapter's `solve_ode` (or a
   new `compose_condition` step) should perturb `discrete_idx` by a
   deterministic function of `(num_steps, seed, round)`. This:
   * preserves the existing AR-prior side-channel contract
     (synthetic mode stays byte-stable for fixed `(seed, num_steps)`),
   * makes the FASTA NFE-sensitive at the byte level,
   * requires no changes to the wave172b generator.

2. **Switch the kanzi FASTA channel** from `discrete_token_index` to a
   trajectory-derived categorical (e.g. argmax over a per-position
   softmax applied to the trajectory's `tanh`-bounded latent). This
   mirrors the lineageflow pattern and would be a closer behavioral
   match, but is a larger refactor and changes the public
   `observe_token_indices` contract for kanzi.

**Recommendation**: Apply option 1 in a follow-up wave (Wave 173 P2).
The minimal change is roughly 6-10 LOC in
`adaptive_reflow/adapters/kanzi.py:2279-` and a corresponding test in
`tests/test_adapters/test_kanzi_solve_ode.py` (or equivalent) asserting
that `solve_ode` mutates `discrete_idx` as a function of
`(num_steps, seed, round)`.

**This audit does NOT apply the fix** (per the wave173 task spec — audit
and document only). The fix is staged for wave173 P2 once the
re-measurement plan is approved.

## Verification

| Gate | Status |
|------|--------|
| `pytest tests/ -k d4` | 33 passed, 31 skipped, 5020 deselected |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | All checks passed |
| `python tools/check_claims_consistency.py` | No drift detected |

No code changes; audit doc only. Wave 172b P1/P2/P3 results remain
intact; the kanzi pLDDT -0.28 delta is preserved as the honest
"synthetic-mode framework trajectory at the wave172b P3 default NFE
is NFE-invariant at the byte level" disclosure until the fix lands.

## Cross-references

* Wave 172b P1 — kanzi FASTA generator: `tools/w172b_gen_kanzi_fastas.py`
* Wave 172b P2 — kanzi foldability / scPerplexity for the 12-cell NFE
  ladder (the -0.28 pLDDT delta is sourced from this sweep).
* Wave 172b P3 — cross-model NFE curve in `typical` regime (12 cells,
  N=30/cell, both models at NFE=50/100/200). Section 10.18 ADDITIVE.
* Wave 172b P4 — paper writeup of section 10.18 (NFE=50/100/200 only,
  supersedes the cancelled Wave 172 NFE=10/100/500 curve).
* Lineageflow `observe_token_indices` (for contrast):
  `adaptive_reflow/adapters/lineageflow.py:2210-` — reads
  `argmax(trajectory[-1], axis=-1)`, NFE-sensitive.
* `_synthesize_discrete_token_indices` (the seed for the frozen
  `discrete_idx`):
  `adaptive_reflow/adapters/kanzi.py:717-` — uniform draw over
  `[0, vocab_size)`, fully determined by `(seed, vocab_size,
  seq_length)` — no NFE input.
