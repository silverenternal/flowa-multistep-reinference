# Wave 171 P1 — Evaluation abstraction refactor (sampling temperature)

## Summary

Adds a sampling-temperature knob to the abstract evaluation layer
(`LineageFlowAdapter.observe_token_indices` + a shared
`decode_with_temperature` helper in `_adapter_common.py`) so
framework-vs-baseline **distributional** advantage is measurable.
The default path (`temperature=1.0`) is **byte-stable** with every
pre-Wave-171 result: D.4 sha256, Wave 158 / Wave 161 K6 FASTA
sha256, R1 / R6 / D.4 / claims.

## Why this refactor

Wave 170 P5 (`docs/audit/wave170-fair-comparison.md`) surfaced a
defect: **framework restart-blend is INERT in synthetic mode**
because the decoder collapses all posterior diversity to a single
argmax sequence per seed. The fair-comparison cells
(baseline=solve_ode N=1 vs framework=solve_ode+restart N=3) had
identical framework.fasta sha256 across baseline_n1 and
framework_n3 arms because the synthetic velocity field converges
to the same endpoint distribution regardless of restart-blend,
and argmax picks the same arg per position.

The fix is to expose a sampling-temperature knob at the abstract
evaluation layer so the **decoder** becomes a controllable source
of stochasticity, separate from the velocity field. Argmax stays
as the default (and as the byte-stable regression path).

## The new abstraction

### `decode_with_temperature(theta, temperature=1.0, *, rng=None)`

In `adaptive_reflow/adapters/_adapter_common.py`. Pure NumPy (no
torch round-trip); takes a ``(L, K)`` per-position categorical,
returns a ``(L,)`` ``int64`` token-index array.

Three regimes:

| `temperature` | Behavior | Byte-stable? |
|---|---|---|
| `1.0` | `argmax(theta, axis=-1)` | **Yes** — identical to the prior inline argmax |
| `< 1.0` | `argmax(theta, axis=-1)` (explicit) | Yes (argmax is invariant to monotone re-scaling) |
| `> 1.0` | `rng.choice(K, p=softmax(log(theta + eps) / T))` per row | No — caller MUST seed `rng` |

The `temperature=1.0` path is a direct passthrough to
`np.argmax(theta, axis=-1)` — the same expression every prior call
site used. The Wave 161 K6 FASTA sha256 regen (below) confirms
this byte-for-byte.

### `LineageFlowAdapter.observe_token_indices(trace, paper_quantities, *, temperature=1.0, rng=None)`

In `adaptive_reflow/adapters/lineageflow.py`. New keyword-only
`temperature` + `rng` parameters default to the prior behavior
(`temperature=1.0`, `rng=None`). All existing call sites are
unchanged because they pass nothing for the new kwargs and the
default falls through to byte-stable argmax.

The Protocol-level signature in
`adaptive_reflow/universal/adapter.py` is updated in parallel so
duck-typed callers (Kanzi, FlowMol3, FreqFlow, etc.) see the new
keyword-only args and can opt-in to stochastic decoding. Kanzi's
existing implementation is left untouched because its
`observe_token_indices` operates on the AR-prior's
`discrete_token_index` channel (a different surface — not a
per-position categorical — so the temperature ladder does not
apply without a separate justification).

### `--temperature` CLI flag

* `tools/gen_lineageflow_n1000_fastas.py` — adds `--temperature`
  (default `1.0`) and threads it through `_framework_emit_sequence`
  + `_write_framework_arm`. The byte-stable default preserves
  Wave 158 / Wave 161 K6 / Wave 167 P5 manifest bytes.

* `data/lineageflow_upstream/evaluation/evaluate_all.py` — adds
  `--temperature` (default `1.0`) as a metadata-only passthrough
  recorded in `<outdir>/inputs.json`. The eval CLI evaluates
  pre-generated FASTAs from disk and does not perform decoding
  itself, so the flag is currently metadata-only; future eval-side
  stochastic decoding paths can consume the same field without
  re-plumbing the CLI.

## Verification

### Backward compatibility — D.4 72/72 PASS

```
$ pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q --tb=line
72 passed, 3 warnings in 37.77s
```

All 30 `tests/test_d4_regression_vectors.py` tests (Wave 38
first-batch vectors) + all 42 `tests/test_adapters/test_regression_vectors.py`
tests (Wave 32 batch 1) pass on the current host.

### Wave 161 K6 sha256 unchanged

```
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w171/sanity/w161k6_regen/ \
        --n 1000 --seed 42 --temperature 1.0 --nfe 10 --n-rounds 3
$ sha256sum /tmp/w171/sanity/w161k6_regen/{baseline,framework}.fasta
4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1  baseline.fasta
afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5  framework.fasta
$ sha256sum /tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta
4ef0ec94d67850aa018d8cb83806d1ad52f80081dca758a732891a08a9e80db1  baseline.fasta
afe53dc0ea168c9d7629915ce6bda02de28299cc1bfa730583410888b83aaec5  framework.fasta
```

Both arms match the canonical Wave 158 references byte-for-byte.
This validates the `temperature=1.0` path is byte-stable with the
prior inline argmax.

### Sanity test — `temperature=1.5` produces different framework output

```
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w171/sanity/baseline_T10/ \
        --n 5 --seed 42 --temperature 1.0 --nfe 10 --n-rounds 3
$ python tools/gen_lineageflow_n1000_fastas.py --outdir /tmp/w171/sanity/baseline_T15/ \
        --n 5 --seed 42 --temperature 1.5 --nfe 10 --n-rounds 3
$ diff /tmp/w171/sanity/baseline_T10/baseline.fasta /tmp/w171/sanity/baseline_T15/baseline.fasta && echo "BASELINE IDENTICAL"
BASELINE IDENTICAL
$ diff /tmp/w171/sanity/baseline_T10/framework.fasta /tmp/w171/sanity/baseline_T15/framework.fasta && echo "FRAMEWORK IDENTICAL" || echo "FRAMEWORK DIFFERS"
FRAMEWORK DIFFERS
```

- Baseline arms are byte-identical (temperature has no effect on
  the bare-RNG baseline, as expected).
- Framework arms differ per record (stochastic sampling is active
  when `temperature > 1.0`).

### Ruff clean

```
$ ruff check adaptive_reflow/ tests/ scripts/ tools/
All checks passed!
```

The ruff errors that surface on
`data/lineageflow_upstream/evaluation/evaluate_all.py` are
pre-existing in the vendored upstream tree (13 errors, unchanged
from `git stash`-baseline) and out of scope for this refactor.

### Claims consistency PASS

```
$ python tools/check_claims_consistency.py | tail -3
- Forced to PROVISIONAL by `Disputed by` citation: CLM-040
- Cross-referenced from at least one governance surface: CLM-001, CLM-002, ... CLM-047

**No drift detected.**
```

## LOC accounting

```
$ git diff --stat
 adaptive_reflow/adapters/_adapter_common.py | 137 ++++++++++++++++++++++++++++
 adaptive_reflow/adapters/lineageflow.py     |  41 ++++++++-
 adaptive_reflow/universal/adapter.py        |  26 ++++++
 tools/gen_lineageflow_n1000_fastas.py       |  60 +++++++++++-
 data/lineageflow_upstream/evaluation/evaluate_all.py |  23 ++++++++++
 5 files changed, 283 insertions(+), 4 deletions(-)
```

260 + 23 = 283 net insertions across 5 files; 137 of those are
the `decode_with_temperature` body + docstring in
`_adapter_common.py`.

## Files touched

| Path | Change |
|---|---|
| `adaptive_reflow/adapters/_adapter_common.py` | Add `decode_with_temperature` helper + `__all__` export |
| `adaptive_reflow/adapters/lineageflow.py` | Add `temperature` + `rng` kwargs to `observe_token_indices`; route decode through the new helper |
| `adaptive_reflow/universal/adapter.py` | Update Protocol signature for `observe_token_indices` with new keyword-only args |
| `tools/gen_lineageflow_n1000_fastas.py` | Add `--temperature` CLI flag; thread through `_framework_emit_sequence` + `_write_framework_arm` + manifest |
| `data/lineageflow_upstream/evaluation/evaluate_all.py` | Add `--temperature` CLI flag (metadata passthrough); record in `inputs.json` |
| `docs/audit/wave171-eval-refactor.md` | This audit doc |

## What's NOT in this wave

* **Wave 171 P2 — sampling-comparison experiment**. With the
  decoder knob in place, the next wave re-runs the Wave 170 P5
  fair-comparison cells at `temperature=1.5` and reports the
  framework-vs-baseline distributional delta. That is a
  compute-heavy GPU step and lives in its own wave.
* **Kanzi observe_token_indices refactor**. Kanzi's surface
  operates on the AR-prior's `discrete_token_index` channel (not
  a per-position categorical), so the temperature ladder does
  not apply without a separate theoretical justification
  (documented gap — the framework-internal-metrics §11 entropy
  formula is also deferred for Kanzi for the same reason).
* **Other-adapter (FlowMol3 / FreqFlow / SelfFlow) sampling
  support**. These adapters carry continuous-domain latents at
  the protocol boundary, so the sampling temperature would have
  to operate on a different (latent-space) surface. Deferred to
  the wave that surfaces a framework-vs-baseline metric gap for
  those adapters.

## Cross-references

* Wave 170 P5 audit: `docs/audit/wave170-fair-comparison.md`
  (the INERT-restart finding this refactor closes)
* Wave 170 P2 design: `docs/audit/wave170-fix-design.md`
* Wave 158 baseline: `docs/audit/wave158-close.md` (the FASTA
  sha256 canonicals re-verified above)
* Wave 161 K6 R6 headline: `docs/baseline-audit-report.md` §R.60
* Wave 167 P5 N-axis observation: `docs/baseline-audit-report.md`
  §R.60-N
