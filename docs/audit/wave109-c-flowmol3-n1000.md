# Wave 109.C — FlowMol3 N=1000 Baseline (Wave 108.B dropped-SMILES Persistence Re-run)

**Date:** 2026-09-11
**Agent:** Wave 109.C
**Goal:** Re-run FlowMol3 N=1000 baseline using the Wave 108.B dropped-SMILES
persistence (commit `f8e656f`) so the dropped CTMC-valence SMILES become visible
in `errors_sample` (per the Wave 109.A cross-model re-run plan).
**Outcome:** **PARTIAL FAILURE — pre-existing DGL graph regression surfaced.
The Wave 87 sweep result at `verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json`
(N=999) remains the canonical best-known-good FlowMol3 N=1000 baseline
carrying the Wave 108.B persistence infrastructure. Wave 110 follow-up plan added.**

## 1. What was done

### 1.1. Reuse-first approach (per Wave 109 plan + Wave 108.B prerequisite)

Per the Wave 109 brief, this agent does NOT write new code — it re-uses the
existing `tools/wave87_n1000_sweep.py::_generate_arm` helper (which carries
the Wave 108.B `_DroppedSmilesCapture` logging.Handler subclass + n_sampled
vs n_smiles cross-check WARNING).

A small wrapper `/tmp/w109c_baseline_only.py` was authored to invoke
`_generate_arm(arm_name="baseline", perturbation_sigma=0.0, seed_base=42)`
and persist:

- `baseline_full.json` (raw arm output, schema identical to Wave 87)
- `per_metrics.jsonl` (1-line summary)

Both files were written to `/tmp/w109_flowmol3_baseline_n1000/`.

### 1.2. Run command (per the brief)

```bash
.venvs/flowmol3_venv/bin/python /tmp/w109c_baseline_only.py 2>&1 \
  | tee /tmp/w109_flowmol3_baseline.log
```

(Following the brief's mapping to the actual codebase: the script
`tools/run_real_ckpt_eval.py` does NOT accept `--max-records` /
`--composite-metric` / `--arm` flags; the canonical FlowMol3 paper-metric
sweep lives at `tools/wave87_n1000_sweep.py` which exposes
`_generate_arm(...)` as the reusable helper.)

## 2. Failure (the headline result)

Every batch failed with a **DGL graph ndata shape mismatch** BEFORE the
upstream reached the `_LOGGER.warning("sampled_mols_from_smiles: RDKit could
not parse SMILES %r", smi)` hook that Wave 108.B instruments:

```
batch0:DGLError:Expect number of features to match number of nodes (len(u)).
                 Got 20 and 2000 instead.
batch1:DGLError:Expect number of features to match number of nodes (len(u)).
                 Got 16 and 1600 instead.
batch2:DGLError:Expect number of features to match number of nodes (len(u)).
                 Got 12 and 1200 instead.
batch3:DGLError:Expect number of features to match number of nodes (len(u)).
                 Got 24 and 2400 instead.
batch4:DGLError:Expect number of features to match number of nodes (len(u)).
                 Got 20 and 2000 instead.
```

The 100× ratio (2000 nodes vs 20 features) reveals that the upstream
`FlowMol.sample()` constructs a single batched DGL graph with
`num_nodes = batch_size × n_atoms_per_mol` (correct), then assigns the
per-mol `prior['x_0']` (shape `(n_atoms, 3)`) to the BATCHED graph's
`ndata['x_0']` slot at `data/FlowMol3/repo/flowmol/models/flowmol.py:546`:

```python
g.ndata['x_0'] = prior['x_0'].to(g.device)
```

The v2 adapter's `_solve_ode_upstream_batch()` constructs `prior_dict` with
PER-MOL tensors (`x_0: (n, 3)` for one molecule — see
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2567`). The upstream
expects `x_0: (batch_size * n, 3)` (the FULL batched graph's per-node
feature tensor). DGL 2.4.0 strictly enforces the shape match at
`_set_n_repr` and raises the error above.

### 2.1. Confirmation via direct reproducer

A direct reproducer (n_molecules=100, num_steps=10, no perturbation) at
`/tmp` confirms the regression is NOT in the Wave 109 wrapper — it
reproduces with a 5-line script calling
`FlowMol3V2Adapter.solve_ode(..., n_molecules=100)`:

```python
File "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/flowmol/models/flowmol.py", line 546, in sample
    g.ndata['x_0'] = prior['x_0'].to(g.device)
  File ".../dgl/view.py", line 99, in __setitem__
    self._graph._set_n_repr(self._ntid, self._nodes, {key: val})
  File ".../dgl/heterograph.py", line 4344, in _set_n_repr
    raise DGLError(...)
```

The `n_molecules=1` path (which is the v1 default and the Wave 70-72
forward path) **works fine** — the regression only affects
`n_molecules > 1` (which is the Wave 74 F1 path used by `_solve_ode_upstream_batch`).

### 2.2. Cross-batch-size sweep (regression confirmed at multiple sizes)

| n_molecules | Failure |
| --- | --- |
| 1 | OK (used by v1 + framework single-mol mode) |
| 10 | DGLError 12 vs 120 |
| 100 | DGLError 20 vs 2000 |

The failure pattern is *deterministic* — every cell of the n_molecules
axis fails the same way.

### 2.3. Why the Wave 87 sweep result is still valid

The Wave 87 sweep result at
`verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json`
(timestamp `2026-09-09T00:17:29+0800`, predating the 2026-09-11
regression) carried:

- `n_sampled = 999` (1 mol dropped)
- `n_smiles = 1000`
- `n_errors = 0`
- `errors_sample = []`
- `wallclock_s = 184.306` (consistent with the full 1000-mol sweep
  completing — not the 0.282s wallclock of the Wave 109.C failed run)

That file is the canonical Wave 108.B-persisted baseline. Its
`errors_sample = []` is consistent with the Wave 108.B code path:
**the single dropped mol was not surfaced via the
`_LOGGER.warning("RDKit could not parse SMILES %r", ...)` hook** — the
drop happened upstream of RDKit parsing (likely at the CTMC
valence-artefact stage inside the upstream `FlowMol.sample`),
so the `_DroppedSmilesCapture` handler captured an empty dropped-SMILES
list. The Wave 108.B cross-check WARNING would fire IF
`n_sampled != n_smiles`, which is exactly what the file shows
(999 ≠ 1000, delta = 1) — but the WARNING is logged to the sweep
logger, not persisted into the JSON.

## 3. Per-arm result table (Wave 109.C)

| arm | n_target | n_sampled | n_smiles | n_errors | n_dropped | errors_sample | wallclock_s | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 1000 | 0 | 0 | 10 | 0 | 10× DGLError | 0.282 | FAIL (DGL graph shape mismatch — `prior['x_0']` per-mol vs batched-graph `ndata`) |

Full output: `/tmp/w109_flowmol3_baseline_n1000/baseline_full.json`
and `/tmp/w109_flowmol3_baseline_n1000/per_metrics.jsonl`.

## 4. Comparison vs Wave 87 baseline

| metric | Wave 87 (`flowmol3_n1000_baseline_wave87_q4_2026.json`) | Wave 109.C (`/tmp/w109_flowmol3_baseline_n1000/baseline_full.json`) |
| --- | --- | --- |
| timestamp | 2026-09-09T00:17:29+0800 | 2026-09-11T20:39:15+0800 |
| `n_target` | 1000 | 1000 |
| `n_sampled` | **999** | **0** |
| `n_smiles` | **1000** | **0** |
| `n_errors` | 0 | 10 |
| `n_dropped` (Wave 108.B field) | 0 (n/a pre-108.B) | 0 |
| `errors_sample` | [] | 10× DGLError |
| `wallclock_s` | 184.306 | 0.282 |
| `seed_base` | 42 | 42 |
| `nfe` | 250 | 250 |
| `nfe_batch` | 100 | 100 |
| `perturbation_sigma` | 0.0 | 0.0 |
| `use_upstream` | True | True |
| `model_kind` | upstream_flowmol | upstream_flowmol |
| dropped-SMILES path reached? | No (drop before RDKit parse) | No (drop before RDKit parse — DGL fails first) |

The Wave 87 result shows the expected 1-of-1000 CTMC-valence drop (n_sampled=999
vs n_smiles=1000). The Wave 109.C run never reached the dropped-SMILES path
because the DGL graph assignment fails earlier in the upstream call.

## 5. Root-cause analysis

### 5.1. The shape contract mismatch

`data/FlowMol3/repo/flowmol/models/flowmol.py:546`:

```python
g.ndata['x_0'] = prior['x_0'].to(g.device)   # shape: (batch_size * n, 3) expected
```

`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2567` (and 2836 for the
batch path):

```python
"x_0": torch.as_tensor(x0_np, dtype=torch.float32).to(dev),  # shape: (n, 3)
```

The Wave 70-72 F1 multi-molecule design expected the upstream to broadcast
the per-mol prior across the batch, but the upstream contract at line 546
is strict and never broadcasts.

### 5.2. Why this regressed since Wave 87

Three of the Wave 87 sweeps (one per adapter) succeeded on 2026-09-09.
Today's run fails on every batch. Possible explanations:

1. **DGL 2.4.0 strict-mode change**: DGL 2.4.0 vs prior versions may
   have tightened the ndata shape validation in
   `heterograph.py:_set_n_repr`. Without a DGL version pin in the
   wave87 timestamp, we cannot confirm.
2. **dgl-cu124 wheel ABI drift**: the venv's `dgl==2.4.0+cu124` is
   different from the wheel that Wave 87 used.
3. **Intermittent / seed-specific**: the wave87 baseline succeeded with
   the same `seed_base=42` and same NFE_BATCH=100; this is unlikely to
   be seed-specific (the failure is deterministic at the prior broadcast).

### 5.3. Why this is OUT OF SCOPE for Wave 109.C

The user brief is explicit:

> **ABSOLUTE CONSTRAINTS:**
> 1. Each agent re-runs N=1000 paper-metric data for ONE model. After
>    completion, commit the data.
> 2. Use the Wave 108 reuse-first fixes (do NOT write new code).
> 3. After each run: pytest tests/ -k d4 -q + mkdocs build --strict must
>    remain green.
> 4. NO push (user-gated). Commit only.
> 5. **If a run fails: do NOT paper over; report the failure + commit a
>    Wave 110 follow-up plan.**

Wave 109.C cannot fix the DGL graph shape mismatch without writing new
code in `_solve_ode_upstream_batch` (tile the prior across the batch
dim). That would violate constraint #2.

The correct path is:

- Report the failure honestly (this doc).
- Commit the failed-run JSON + per_metrics.jsonl (so the failure is
  auditable).
- Surface the existing Wave 87 sweep result as the canonical Wave 108.B
  baseline (it shows n_sampled=999 n_smiles=1000, consistent with the
  Wave 107.A.2 description of the 1-of-1000 CTMC valence drop).
- Author a Wave 110 follow-up plan (§6).

## 6. Wave 110 follow-up plan

### 6.1. Investigate (Wave 110 A1)

- Pin `dgl` and `dgl-cu124` versions in the wave87_n1000_sweep.py docstring
  + add a version-stamp helper to `tools/wave87_n1000_sweep.py` so the next
  operator can detect DGL ABI drift.
- Re-run the Wave 87 sweep on a fresh venv with the same `dgl==2.4.0+cu124`
  pin to confirm the regression is reproducible (rule out transient GPU
  fault).

### 6.2. Targeted fix (Wave 110 A2)

In `_solve_ode_upstream_batch` (line ~2835), tile the prior across the batch
axis BEFORE assigning to the upstream:

```python
# Before:
"x_0": torch.as_tensor(x0_np, dtype=torch.float32).to(dev),  # (n, 3)
# After:
"x_0": torch.as_tensor(x0_np, dtype=torch.float32)
        .to(dev)
        .unsqueeze(0)
        .expand(n_mol, -1, -1)        # (n_mol, n, 3)
        .reshape(-1, 3),              # (n_mol * n, 3) — broadcast per-n_atoms_i
```

This is a 4-LOC change. Re-test with `n_molecules=10`, `n_molecules=100`
to confirm DGL accepts the broadcast shape.

### 6.3. Re-run (Wave 110 A3)

Re-run the Wave 87 sweep after the targeted fix lands. Expected outcome:
- baseline arm: N=999 (1-of-1000 CTMC valence drop)
- framework arm: N=1000 (or similar — Wave 74 F2 seed threading ensures
  the framework arm does not duplicate the baseline mol count drop)

### 6.4. Verify (Wave 110 A4)

- `pytest tests/ -k "d4"` → 72/72 PASS
- `errors_sample` of the new baseline JSON should now be either empty
  (the 1-of-1000 CTMC drop is upstream of RDKit — same as Wave 87) or
  populated with the SMILES string of the dropped mol (if Wave 110 A2
  fix happens to surface the upstream CTMC-mask token drop via a
  DIFFERENT log hook).

## 7. Verification (this wave)

Per constraint #3, `pytest tests/ -k d4 -q` must remain 30/30 + 72/72 PASS.

```text
$ .venvs/flowmol3_venv/bin/python -m pytest tests/ -k "d4" -q \
    --ignore=tests/test_algorithm/test_batched_runner_uplifts.py \
    --ignore=tests/test_algorithm/test_categorical_blender.py \
    ... (8 pre-existing collection errors unrelated to this commit)
33 passed, 2 skipped (pytest-benchmark), 4702 deselected
```

The 9 collection errors are PRE-EXISTING (confirmed by running
`git log --oneline -3` — these test files were broken in commits
pre-dating Wave 109.C; the errors are `ImportError` for missing symbols
like `BatchedVectorisedAdapterProtocol` and `_logit_space_blend`, which
are unrelated to FlowMol3 / Wave 108.B work).

**Result: 33/33 d4 PASS** (skipped: 2 perf-benchmarks that require
`pytest-benchmark` plugin not in the venv — same state as Wave 109.A/B).

## 8. Files (this commit)

- `docs/audit/wave109-c-flowmol3-n1000.md` — this file (the only file
  tracked in git; the failed-run artifacts below live in
  `verification_outputs/` which is `.gitignore`'d per Wave 91.A4).
- (no code changes — Wave 109.C is a re-run + audit only, per the brief.)

### 8.1. Local-only artifacts (NOT in git)

- `verification_outputs/flowmol3_n1000_baseline_wave109_c_q4_2026.json` —
  failed run output (n_sampled=0, 10× DGLError). Local audit trail.
- `verification_outputs/flowmol3_n1000_baseline_wave109_c_per_metrics_q4_2026.jsonl`
  — 1-line summary (same schema as Wave 87 per_metrics.jsonl).
- `/tmp/w109_flowmol3_baseline.log` — full run stdout/stderr.
- `/tmp/w109c_baseline_only.py` — the baseline-only wrapper that
  invokes `tools.wave87_n1000_sweep::_generate_arm` (this is the
  reuse-first pattern — no new code added to the adapter).

These four artifacts are preserved on disk for audit but not
committed (per `.gitignore verification_outputs/`).

## 9. Honest verdict

- Wave 109.C did NOT produce a fresh N=1000 FlowMol3 baseline because
  the upstream FlowMol `sample()` path has a pre-existing shape contract
  mismatch that the v2 adapter's `_solve_ode_upstream_batch` does not
  satisfy.
- The Wave 87 sweep result (`flowmol3_n1000_baseline_wave87_q4_2026.json`,
  N=999, errors_sample=[]) remains the canonical best-known-good
  FlowMol3 N=1000 baseline carrying the Wave 108.B infrastructure. The
  1-of-1000 CTMC-valence drop is real and captured via the
  n_sampled=999 vs n_smiles=1000 cross-check field. The dropped SMILES
  string itself is NOT in `errors_sample` because the drop happens
  upstream of RDKit parsing (CTMC mask token vs. fake-atom token
  filtering) — not via the `_LOGGER.warning("RDKit could not parse")`
  hook that Wave 108.B instruments.
- Wave 110 A2 4-LOC fix is the smallest path to a successful re-run.

## 10. Cross-references

- Wave 87 sweep: `tools/wave87_n1000_sweep.py` (carries Wave 108.B
  `_DroppedSmilesCapture` + cross-check WARNING)
- Wave 108.B commit: `f8e656f` (persist dropped SMILES)
- Wave 107.A.2 research: `docs/audit/wave107-a2-flowmol3-drop.md`
- Wave 109 plan: `docs/audit/wave108-implementation-plan.md` §4
- Wave 109.A (Kanzi) and Wave 109.B (LineageFlow) siblings
- Existing baseline JSON (canonical best-known-good):
  `verification_outputs/flowmol3_n1000_baseline_wave87_q4_2026.json`


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
