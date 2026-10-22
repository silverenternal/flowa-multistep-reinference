# GAP-44 — the paper-quantity channels are live on R1

**Date:** 2026-10-21
**Status:** closed (wiring only; the A/B measurement is GAP-69)
**Scope:** `adaptive_reflow/adapters/lineageflow.py`,
`tools/eval/framework.py`, `tools/gen_lineageflow_n1000_fastas.py`.
No frozen surface touched.

---

## 0. What was dead, and why

`profile_residual_fn` had three implementations in
`adaptive_reflow/adapters/profile_residual.py` (LineageFlow, Kanzi, FlowMol3)
and **no consumer**. The chain that was supposed to consume it has four links,
and the first one was missing:

```
adapter.profile_residual_fn                 <- missing on every adapter
  -> tools.eval.framework._compute_paper_quantities   returns None
    -> _make_framework_policy(paper_quantities=None)  constant-beta branch
      -> CodimensionSheetScheduler(profile_residual_fn=None)
         n_cap saturates at n_max = 1.0
```

The last link is the damaging one. `CodimensionSheetScheduler` computes

```
sheet = A_g * eps
cell  = C_g * B_g * eps^2
ratio = sheet / (sheet + cell)
n_cap = n_min + (n_max - n_min) * ratio
```

and with no profile it falls back to a framework-side heuristic whose ratio
evaluates to 1.0 on every round. Since the framework's convention is
`beta = 1 - n_cap`, `n_cap = 1` means **beta = 0**, i.e. `memory_fraction = 1`,
i.e. `apply_restart_distribution` is an identity map. The `codimension_sheet`
arm on R1 was therefore not a restart arm at all — it was "the same ODE solve
split into four chunks", which is exactly what `gap42-scheduler-budget-
conservation.md` saw as the degenerate `n_cap ~ [1,1,1]`.

Measured before the fix (`tools/gap76_report.py`-style construction,
`cycle_length=20`, `eps_implicit=0.05`, `seed=42`):

```
profile_residual_fn=None   n_cap = [1.0, 1.0, 1.0, 1.0]     beta = 0
```

## 1. The change

Three additive edits, all default-off:

1. **`LineageFlowAdapter.__init__`** gains
   `profile_residual_fn: Callable[[float], float] | None = None`, validated
   callable-or-None (`profile_residual_fn_must_be_callable_or_none`) and stored
   as a public attribute. `None` is the default, so every existing constructor
   call is unchanged.
2. **`_make_framework_policy`** resolves the adapter's profile through the same
   two paths `_compute_paper_quantities` uses (`capabilities()` then the direct
   attribute) and forwards it into `CodimensionSheetScheduler`. This is the link
   that was missing; the scheduler **family** is not switched, which is the
   gap's explicit constraint.
3. **`tools/gen_lineageflow_n1000_fastas.py`** gains `--profile-residual`
   (store_true, default off). When set it builds the registry profile and its
   `PaperQuantitiesCache` once via `_build_profile_residual_channels()` and
   threads the profile into every per-family adapter. The manifest records
   `profile_residual_wired`, `paper_quantities_cache_is_active`, the four
   quantities, and the codimension-sheet `n_cap` vector.

## 2. Observed

Acceptance (1) — the cache is active and the driver carries the profile:

| field | `--profile-residual` off | on |
|---|---|---|
| `profile_residual_wired` | `false` | **`true`** |
| `paper_quantities_cache_is_active` | `false` | **`true`** |
| `paper_quantities` | `null` | `A_g=0.846668`, `B_g=1.169713`, `C_g=1.240756`, `e_rho=1.0e-4` |

Acceptance (2) — `n_cap` is no longer degenerate (4 rounds, seed 42):

```
off   [1.0000, 1.0000, 1.0000, 1.0000]
on    [0.9211, 0.9249, 0.9288, 0.9327]
```

and the per-round `beta` the framework actually emits at NFE=150, R=3:

```
off   beta = 0.1667, 0.1667, 0.1667      (constant-beta legacy path)
on    beta = 0.0263, 0.0250, 0.0237      (paper-quantity-driven)
```

Acceptance (3) — the default path is byte-stable: D.4 regression vectors
**72/72**, and a live 6-record R1 run with and without the flag produces
identical FASTA md5s:

```
baseline.fasta   734c3502fba18260776b567bb85ee1c1   (both)
framework.fasta  88bb3926976f55ebc9b3865febcbda33   (both)
```

### 2.1 The wiring is live, and the output still does not move

The identical FASTAs are **not** evidence that the flag did nothing. A runtime
probe on the actual driver path (`_framework_emit_sequence` →
`_solve_framework`, two records, NFE=150) counts the
`_compute_paper_quantities` calls:

```
off   [(0, None), (1, None), (2, None), (0, None), (1, None), (2, None)]
on    [(0, 0.8467), (1, 0.8467), (2, 0.8467), (0, 0.8467), (1, 0.8467), (2, 0.8467)]
```

So every round of every record takes the paper-quantity branch when the flag is
set. The sequences are nonetheless identical because the R1 framework arm
decodes by `int(v) % 20` on a coarse simplex driven by a synthetic velocity
field — a beta change from 0.167 to 0.026 does not flip a single argmax at this
scale. **Wiring is not an effect.** Whether the channel changes anything is the
question GAP-69 has to measure with the real checkpoint and a powered N.

### 2.2 What this does not license

- It does not license the claim "the paper quantities help". Nothing here
  measures a metric.
- It does not license "the R1 headline is paper-quantity-driven". At the
  canonical R1 configuration (`--nfe 10`, `--restart-min-nfe 20`) the gate is
  closed and `n_rounds` degrades to 1, so no restart and no per-round beta
  exists regardless of this flag.
- It does not change `enable_full_jmaa_theory` (still `False`,
  `engine.py:1000`). The Engine-side 15 sites remain dormant; this gap wires the
  **tool-side** path (`_compute_paper_quantities` + the scheduler base), which is
  the path every R1/R3/R5 driver actually uses.

## 3. Why this was the prerequisite

GAP-68 (FlowMol3), GAP-69 (LineageFlow), GAP-70 (Kanzi) and GAP-71 (image
spectral) all want to ask "does the paper-quantity channel add anything on this
adapter". Before this gap the answer was structurally `None` on all four, so a
negative result would have been uninterpretable — it would have meant "the
channel was never on", not "the channel does not help". That ambiguity is now
removed: the channel is on, one flag away, and the default path is provably
unchanged.

## 4. Test

`tests/test_gap44_profile_residual_wiring.py` (6 tests): cache active and the
four quantities finite; adapter carries the profile; `_compute_paper_quantities`
flips `None` → populated; `n_cap` no longer saturates and varies across rounds;
the default path stays on the constant-beta branch; a non-callable profile is
rejected.
