# Wave 40 — Kanzi real-ckpt integration synthesis

Date: 2026-09-05
Wave: 40
Agent: B (final verify + summary)
Scope: PHASE-4 Kanzi real-ckpt integration (Agent A) + upstream-bug monkey-patch (Agent B)

## TL;DR

Wave 40 lands two complementary deliverables on the Kanzi real-ckpt axis:

1. **Agent A** (`d7c2f89` predecessor, `c2bcfe9`): sidecar-venv execution of
   `tools/run_real_ckpt_eval.py` against the Kanzi adapter. 9 cells (3 seeds
   x 3 NFE budgets) ran to completion and produced a per-cell JSON report.
   All 9 cells are `TIE_AT_SATURATION` (synthetic-mode ceiling) by design —
   the eval runner hard-codes `force_mode="synthetic"` so no real-ckpt
   forward path is exercised. The wall-clock signal (~3-4x framework speedup
   per cell) is the honest read.
2. **Agent B** (`d7c2f89`): monkey-patches `kanzi.models.GPT.forward` from
   our side to fix an upstream positional/kwarg binding bug at
   `kanzi/models.py:145`. The patch lets `DAE.forward(gpt_prior=True)` run
   end-to-end with a real GPT-prior loss branch instead of the Wave 39
   `gpt_prior_loss = 0` workaround.

Both deliverables are non-regressions: pytest 30 passed, mkdocs strict
build green, no fabricated deltas.

## Why these two pieces are complementary

The eval runner's synthetic-mode design (Wave 36 Agent D) was a
deliberate deferred-honesty choice: it lets PHASE-4 deliverables land
without fabricating framework wins. The runner reports a saturated
ceiling for both arms (`baseline_metric = framework_metric = 0.95`)
because `protein_sequence_validity_rate`'s saturation threshold is
`0.95` and the synthetic shim returns exactly that.

The monkey-patch unlocks the *next* wave's work (a Wave 41+ agent that
owns `tools/` + `adaptive_reflow/adapters/kanzi.py` as disjoint scope):
when that agent adds a real-ckpt code path, the patch is already in
place so the GPT-prior loss branch (which the Wave 36/39 ckpt uses)
runs end-to-end without needing a separate workaround.

In short: **Wave 40 fixes a latent blocker that any real-ckpt
framework-vs-baseline run on Kanzi would have hit**, while
simultaneously shipping a per-ckpt eval JSON that records the
no-fabrication read at the current state.

## Verification summary (Wave 40 Agent B final verify)

| Check | Result |
|---|---|
| `verification_outputs/kanzi_real_ckpt_eval_q4_2026.json` cells | **9** |
| `...` framework wins (`status=SUPPORTED`) | **0** |
| `tests/test_adapters/test_kanzi.py` pytest | **30 passed in 9.24s** (full file) |
| `tests/test_adapters/test_kanzi_real_ckpt.py` pytest | **22 passed in 14.81s** (cold-clone suite) |
| `.venvs/flowmol3_venv/bin/mkdocs build --strict` | **0 errors, 8.45s** |
| Last 2 commits on `main` | `d7c2f89` Wave 40 Agent B monkey-patch, `c2bcfe9` Wave 40 Agent A eval |
| Files changed in `d7c2f89` | `adaptive_reflow/adapters/kanzi.py` (+164), `tests/test_adapters/test_kanzi.py` (+163), `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` (+262) |

## Status distribution

```
Total cells: 9
TIE_AT_SATURATION: 9
SUPPORTED (framework strictly better): 0
REGRESSION: 0
PENDING: 0
BLOCKED: 0
RUN_ERROR: 0
```

All 9 cells carry `adapter_mode=synthetic` and `marker=synthetic_fallback`,
matching the Wave 36 Agent D hard-coded design. The reading is the same
as the Wave 33 cold-clone audit's documented trivial reading on Kanzi.

## Per-NFE wall-clock (honest signal from Agent A sweep)

| nfe_budget | n_cells | baseline_total_s | framework_total_s | framework/baseline |
|---:|---:|---:|---:|---:|
| 10  | 3 | 0.5088 | 0.1282 | 0.252 |
| 50  | 3 | 2.0571 | 0.6392 | 0.311 |
| 200 | 3 | 6.8339 | 1.8971 | 0.278 |

Framework loop is ~3-4x faster per-cell wall-clock on the synthetic shim
because the synthetic forward is cheap and the framework's smaller-NFE
per-round strategy amortizes across 3 short rounds. Consistent with the
Wave 36 §13 numbers.

## Files touched by Wave 40 (Agent A + Agent B)

| Path | Change | Agent |
|---|---|---|
| `verification_outputs/kanzi_real_ckpt_eval_q4_2026.json` | NEW (9 cells, written by runner) | A |
| `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json` | NEW (per-model split) | A |
| `docs/audit/wave40-kanzi-real-eval-results.md` | NEW | A |
| `docs/CONSOLIDATED_RESULTS.md` §14 | APPEND (per-cell table + reading) | A |
| `adaptive_reflow/adapters/kanzi.py` | APPEND `_install_gpt_prior_patch()` + module-load call | B |
| `tests/test_adapters/test_kanzi.py` | APPEND 4 regression tests | B |
| `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` | NEW | B |

## Constraints honored

- Disjoint file scopes: Agent A did NOT touch `tools/`,
  `adaptive_reflow/`, `tests/`, `framework/`, `scheduler/`, or other
  adapters. Agent B did NOT touch `tools/` or the eval runner.
- Sidecar venv (`.venvs/kanzi_venv`) used by Agent A for the eval sweep;
  `.venvs/flowmol3_venv` used by Agent B for pytest + mkdocs strict.
- No fabricated deltas. The 9-cell sweep reports the synthetic ceiling
  on both arms; the monkey-patch is additive on top of the Wave 39
  workaround.
- Committed (no push). Push is a separate decision by the wave driver.

## What Wave 41 (or later) would do

In rough order of work, to produce non-trivial `framework > baseline`
deltas on the Kanzi real-ckpt axis:

1. Extend `tools/run_real_ckpt_eval.py` to accept
   `force_mode="auto"` + auto-discovery of
   `data/kanzi_ckpt/cleaned_model.pt`. (Agent A had to skip this due to
   disjoint scope.)
2. Add a real-ckpt code path inside
   `adaptive_reflow/adapters/kanzi.py` that loads the DAE state_dict,
   runs the encoder + FSQ + flow + decoder chain on
   `build_initial_state`, and threads the output through `solve_ode`.
   (Wave 39 Agent A's `tools/run_kanzi_real_ckpt.py` already proves the
   forward path is viable on the sidecar venv.)
3. Extend `_compute_metric` to compute
   `protein_sequence_validity_rate` from actual generated tokens
   (decode to amino-acid sequence + measure `<unk>` proportion) instead
   of returning the synthetic ceiling.
4. Wire the framework-vs-baseline split (paper-quantity scheduler,
   restart blend) into the real forward path so the comparison
   exercises the framework.
5. Verify on a held-out batch and capture the per-cell delta in the
   JSON. The GPT-prior monkey-patch from Agent B is already in place
   so the `gpt_prior=True` branch will run end-to-end.

## Aggregate verdict

| Stat | Value |
|---|---:|
| n_cells | 9 |
| n_supported | 0 |
| n_tie_at_saturation | 9 |
| n_regression | 0 |
| n_pending | 0 |
| n_blocked | 0 |
| n_run_error | 0 |
| framework_wins | **0** |
| G.1 mean signed Δ% | 0.0 |
| pytest (kanzi) | 30 passed |
| pytest (kanzi_real_ckpt) | 22 passed |
| mkdocs strict | green |
| Verdict | **TIE_AT_SATURATION** + latent upstream bug fix |

## Status

- Agent A eval JSON landed and committed (`c2bcfe9`).
- Agent B monkey-patch landed and committed (`d7c2f89`).
- Wave 40 deliverable closure: complete.
- Awaiting wave-driver push decision.

## Related audit docs

- `docs/audit/wave39-kanzi-real-ckpt-forward.md` — sidecar venv setup + ckpt forward probe
- `docs/audit/wave40-kanzi-real-eval-results.md` — Agent A eval sweep
- `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` — Agent B monkey-patch
- `docs/audit/wave40-cold-clone-capability-audit.md` — Wave 40 Agent C cold-clone rerun
- `docs/audit/wave40-kanzi-real-eval-synthesis.md` — this file