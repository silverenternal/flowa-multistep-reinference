# Wave 40 — Blocker-unblock synthesis

**Date:** 2026-09-05
**Wave:** 40
**Agent:** Wave 40 Agent C (final verify + summary)
**Scope:** High-level summary of what Wave 40 unblocked across the PHASE-4
real-checkpoint axis (Kanzi + LineageFlow) plus the cold-clone capability
audit rerun.

## TL;DR

Wave 40 closes **three residual real-ckpt blockers** that survived Wave 36
through Wave 39:

1. **LineageFlow upstream clone + real numerical forward** (Agent A) —
   the 10.5 GB released checkpoint now loads into the real upstream model
   on a CPU-only sidecar venv, 576/576 tensors match (0 missing, 0
   unexpected), and the denoiser + 8-step base-flow ODE solver run without
   NaN.
2. **Kanzi `GPT.forward` monkey-patch** (Agent B) — an upstream positional
   / kwarg binding bug at `kanzi/models.py:145` is patched from our side,
   so `DAE.forward(gpt_prior=True)` (the Wave 36/39 Kanzi ckpt config) runs
   end-to-end with a real GPT-prior loss branch instead of the Wave 39
   `gpt_prior_loss = 0` workaround.
3. **Cold-clone capability audit rerun post-Wave-38/39** (Agent C, prior
   turn) — `G-MASTER-CAPABILITY = PASS` for the **second consecutive**
   run; all 5 HARD G. gates and both SOFT gates unchanged vs Wave 38.

Net effect: the PHASE-4 real-ckpt axis is **unblocked for Wave 41+** to
land framework-vs-baseline numbers on real Kanzi + LineageFlow weights
without further infrastructure work, and the framework's value surface
is **stable** across two consecutive cold-clone audits.

## Verification summary (this turn)

| Check | Result |
|---|---|
| `pytest tests/test_adapters/test_kanzi.py tests/test_adapters/test_lineageflow.py -q` | **55 passed, 3 skipped** (kanzi not installed in flowmol3_venv by design; 3 skips are expected) |
| `.venvs/flowmol3_venv/bin/mkdocs build --strict` | **0 errors** (9.02 s) |
| Wave 40 commits on `main` | **4** (`a4a4bd8`, `c2bcfe9`, `d7c2f89`, `8eacd9d`) — exceeds 2+ requirement |
| Files changed across Wave 40 | tracked additions to `adaptive_reflow/adapters/kanzi.py`, `tests/test_adapters/test_kanzi.py`, `tests/test_adapters/test_lineageflow.py`, `tools/run_kanzi_gpt_prior.py`, `tools/run_lineageflow_real_ckpt.py`, `tools/run_real_ckpt_eval.py`, `docs/CONSOLIDATED_RESULTS.md`, 5 audit docs, plus `requirements-lineageflow.txt` |

Latest 3 commits on `main`:

```
d04f3c2 Wave 41 Agent A: Kanzi GPT-prior end-to-end test on real 530 MB ckpt
0d8d56d Wave 41 Agent B: --force-mode flag + real-ckpt Kanzi eval
8eacd9d Wave 40 Agent A: LineageFlow upstream clone + real-ckpt numerical forward
```

## What was unblocked, per blocker

### Blocker 1 — LineageFlow: ckpt loads, model not on `sys.path`

| Blocker | Status before Wave 40 | Status after |
|---|---|---|
| Upstream source located | Wave 36 (URL only, case mismatch `jinxbye` vs `Jinx-byebye` corrected) | cloned at commit `ccef84ad` |
| ckpt pickle unpickles | Wave 39 (`_install_checkpoint_compat()` shim) | unchanged, confirmed |
| `LineageFlowClassifier` importable | **BLOCKED** (upstream ships no `setup.py` / `pyproject.toml`) | runs via `sys.path.insert(0, "data/lineageflow_upstream")` (recorded in JSON `upstream.install_method`) |
| Weights actually load | **NEVER RUN** | **576/576 tensors, 0 missing, 0 unexpected** (657.6 M parameters, matches paper) |
| Denoiser forward | **NEVER RUN** | `(4, 64, 20)` logits, 0.46 s CPU, deterministic |
| Base-flow ODE solver | **NEVER RUN** | 8 Euler steps, 45.7 s CPU, no NaN |
| Wave 33 entropy metric (non-saturated) | not measurable | **2.266 / 2.996 ceiling** (interior, not degenerate) |

Key file: `docs/audit/wave40-lineageflow-real-ckpt-forward.md`. Output
JSON: `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`
(gitignored).

### Blocker 2 — Kanzi: GPT-prior loss branch blows up

The upstream `kanzi` package (commit `cfed9cf4`) has a positional / kwarg
binding bug at `kanzi/models.py:145`:

```python
for block in self.blocks:
    s_BLD = block(s_BLD, block_mask, pair_bias_BLLD=None)
```

`block_mask` binds positionally to `pair_bias_BLLD`, then the explicit
`pair_bias_BLLD=None` kwarg collides:

```
TypeError: TransformerBlock.forward() got multiple values for
argument 'pair_bias_BLLD'
```

This breaks `DAE.forward(gpt_prior=True)` for **any** GPT-enabled
checkpoint, including the Wave 36/39 Kanzi ckpt (`gpt_prior=True`).

Wave 39 worked around it by patching `DAE.forward` to skip the GPT-prior
branch entirely (reporting `gpt_prior_loss = 0`). Wave 40 replaces that
workaround with a real monkey-patch on `kanzi.models.GPT.forward` that
introspects `TransformerBlock.forward`'s signature and routes
`block_mask` to the correct slot. The patch is module-level in
`adaptive_reflow/adapters/kanzi.py` (`_install_gpt_prior_patch()`) and
runs at import time.

| Blocker | Status before Wave 40 | Status after |
|---|---|---|
| `DAE.forward(gpt_prior=True)` | **TypeError** | runs end-to-end with real GPT-prior loss |
| Wave 39 `gpt_prior_loss = 0` workaround | active | removed (Wave 41 Agent A's `--force-mode` runner exercises the real branch) |
| Upstream fork dependency | required (Wave 36/39 path) | **none** — pure runtime patch |

Key files: `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md`,
`docs/audit/wave41-kanzi-gpt-prior-e2e.md`. The Wave 41 Agent A work
(commit `d04f3c2`) uses the patched GPT-prior branch end-to-end on the
real 530 MB ckpt.

### Blocker 3 — Cold-clone capability audit drift

The Wave 39 Kanzi sidecar venv work could in principle have perturbed
the framework's G.* value surface (it adds a 5th integrated model, it
runs in a sidecar Python env, it loads real Kanzi weights into the
flowmol3_venv's `sys.path` if anything is wired wrong). The Wave 40
Agent C audit rerun shows **no perturbation**:

| Subset | Pass | Fail | Delta vs Wave 38/39 |
|---|---|---|---|
| HARD (G.1, G.3, G.4, G.6, G.7) | **5** | 0 | unchanged |
| SOFT (G.2, G.5) | **2** | 0 | unchanged |
| `G-MASTER-CAPABILITY` | **PASS** | — | unchanged |
| `MUST-4 FREEZE GATE` | **PASS** | — | unchanged |

JSON byte-level diff vs Wave 38:

```
476c476  <  "timestamp": "2026-09-05T11:43:06.332336+00:00"
         >  "timestamp": "2026-09-05T12:10:41.041126+00:00"
507c507  <  "captured_at": "2026-09-05T11:43:06.334830+00:00"
         >  "captured_at": "2026-09-05T12:10:41.042608+00:00"
```

**Only timestamps differ.** All 10 G.1 evidence rows, the 4 G.2
wallclock rows, the G.3 worst cell, the G.4 family counts, the G.6
per-family hns, the G.7 reproducibility checks, the `env_hash`, the
`integrated_models` autodetect list, and the aggregate verdict block
are byte-identical.

This is the **second consecutive cold-clone audit** in which SOFT is
2/2 PASS (Wave 39 was the first; Wave 36 was the last 1/2 reading).
Per-family signed_mean remains `framework_improves_all_models = TRUE`
across `{twodim_fm: +0.408, rectified_flow_cifar: +0.213, mnist_fm:
+0.063, lineageflow: +0.001}`.

Key file: `docs/audit/wave40-cold-clone-capability-audit.md`. Output
JSON: `verification_outputs/capability_audit_q4_2026_post_w40.json`.

## Why these three unblocks are mutually reinforcing

- **Blocker 1 + 2** turn "the real ckpt loads" into "the real ckpt runs
  end-to-end through both model families that the PHASE-4 plan called
  out as scope". Without Blocker 2, LineageFlow would still need a
  separate GPT-prior workaround when Wave 41+ generalises the runner;
  without Blocker 1, the LineageFlow audit could only land a wallclock
  signal, not a framework-vs-baseline delta.
- **Blocker 3** is the regression-prevention backbone: every Wave 40
  fix lives in a disjoint file scope (adapters + tests + tools), and the
  cold-clone audit confirms nothing in the framework's value surface
  regressed. That is what licenses Wave 41 to add `kanzi` to
  `integrated_models` (it would have been a 5th family and any regression
  would have shown up in G.3 worst cell).

## Status distribution and what's next

Wave 40 ends with the PHASE-4 real-ckpt axis **unblocked for Wave 41+**:

| PHASE-4 scope item | Status | Owner of next move |
|---|---|---|
| Kanzi ckpt download | DONE (Wave 36) | — |
| Kanzi sidecar venv + forward | DONE (Wave 39) | — |
| Kanzi GPT-prior monkey-patch | DONE (Wave 40 Agent B) | — |
| Kanzi `--force-mode` real-ckpt eval runner | DONE (Wave 41 Agent B, commit `0d8d56d`) | Wave 41+ Agent C: framework-vs-baseline numbers |
| LineageFlow upstream clone | DONE (Wave 40 Agent A) | — |
| LineageFlow real-ckpt forward | DONE (Wave 40 Agent A) | — |
| LineageFlow framework-vs-baseline | not yet | Wave 41+ |
| FreqFlow / MM-FM | OUT OF SCOPE (Wave 36 — no upstream ckpt) | — |

The cold-clone capability gate is on a 2-consecutive-audit streak of
5/5 HARD + 2/2 SOFT; a 3rd consecutive run (post-Wave-41 framework-vs-
baseline on Kanzi) is the natural next signal to check.

## Risks and known limitations

1. **Sidecar-venv split.** LineageFlow's real forward lives in
   `.venvs/lineageflow_venv/` (Python 3.12.13, torch 2.5.1+cpu). It is
   not on the flowmol3_venv's `sys.path`. A future Wave 41+ that wants
   the framework runner to call LineageFlow directly needs to either
   (a) install LineageFlow into flowmol3_venv, or (b) keep the runner
   pattern of `sys.path.insert(0, "data/lineageflow_upstream")` at
   runtime. The latter is what `tools/run_lineageflow_real_ckpt.py`
   already does.
2. **Synthetic-mode eval ceiling.** `tools/run_real_ckpt_eval.py`
   hard-codes `force_mode="synthetic"`, so the 9 PHASE-4 eval cells
   land as `TIE_AT_SATURATION` by design. Wave 41 Agent B's
   `--force-mode` flag is the opt-in to real-ckpt evaluation; a Wave 41+
   agent needs to use that flag and read the resulting JSON to produce
   non-saturated framework-vs-baseline numbers.
3. **Entropy metric was inlined.** `tools/run_lineageflow_real_ckpt.py`
   inlines the per-position entropy formula rather than importing from
   `tools/run_controlled_audit._per_position_entropy`. Parity is
   numerically verified (bit-identical on `(4,64,20)` and `(8,16,33)`
   random inputs), but the duplication is a future-cleanup item.

## Files changed in Wave 40

Tracked (selected; full list via `git diff --stat HEAD~5 HEAD`):

- `adaptive_reflow/adapters/kanzi.py` — `_install_gpt_prior_patch()` + import-time install
- `tests/test_adapters/test_kanzi.py` — regression tests for GPT-prior patch
- `tools/run_kanzi_gpt_prior.py` — new GPT-prior end-to-end runner
- `tools/run_lineageflow_real_ckpt.py` — new LineageFlow real-ckpt runner
- `tools/run_real_ckpt_eval.py` — refactor + `--force-mode` support (Wave 41 Agent B)
- `requirements-lineageflow.txt` — pinned deps for the sidecar venv
- `docs/CONSOLIDATED_RESULTS.md` — Wave 40 + 41 additions
- `docs/audit/wave40-cold-clone-capability-audit.md` — this turn's audit
- `docs/audit/wave40-kanzi-gpt-prior-monkey-patch.md` — Agent B
- `docs/audit/wave40-kanzi-real-eval-synthesis.md` — Agent B (Phase 4)
- `docs/audit/wave40-lineageflow-real-ckpt-forward.md` — Agent A

Untracked / gitignored:

- `data/lineageflow_upstream/` (cloned upstream source)
- `data/lineageflow/lineageflow-rp55.ckpt` (10.5 GB real ckpt)
- `.venvs/lineageflow_venv/`, `.venvs/kanzi_venv/` (sidecar venvs)
- `verification_outputs/*.json` (audit + forward result JSONs)

## Verification record (this turn, 2026-09-05)

```text
$ .venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_kanzi.py \
    tests/test_adapters/test_lineageflow.py -q --tb=line
...
55 passed, 3 skipped, 3 warnings in 15.11s

$ .venvs/flowmol3_venv/bin/mkdocs build --strict
INFO    -  Building documentation to directory: .../site
INFO    -  Documentation built in 9.02 seconds

$ git log -3 --oneline
d04f3c2 Wave 41 Agent A: Kanzi GPT-prior end-to-end test on real 530 MB ckpt
0d8d56d Wave 41 Agent B: --force-mode flag + real-ckpt Kanzi eval
8eacd9d Wave 40 Agent A: LineageFlow upstream clone + real-ckpt numerical forward

$ git log --oneline | grep -c "Wave 40"
4
```

All four Wave 40 commits land on `main` (`a4a4bd8`, `c2bcfe9`,
`d7c2f89`, `8eacd9d`), exceeding the 2-commit threshold.
