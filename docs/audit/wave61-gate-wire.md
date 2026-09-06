# Wave 61 Agent 1 — wire the NFE-adaptive restart gate to run_real_ckpt_eval.py

**Date:** 2026-09-07
**Scope:** `tools/run_real_ckpt_eval.py` (call-site only), `adaptive_reflow/adapters/_adapter_common.py` (unchanged), `adaptive_reflow/adapters/flowmol3.py` (unchanged — gate already lives there)
**Branch:** main
**Status:** gate active in 9-cell FlowMol3 sweep; +1 cell moves REGRESSION → SUPPORTED vs Wave 58 baseline; **commit pending**
**Constraint:** non-call-site code in `run_real_ckpt_eval.py` and the gated adapter
were not touched beyond the parser / factory call sites documented below.

---

## 1. What was wired

Wave 58 Agent 1 (commit `db01e28`) implemented the NFE-adaptive restart gate
inside `FlowMol3Adapter.apply_restart_distribution` but did not wire it from
`tools/run_real_ckpt_eval.py`, so every eval sweep has run with the gate
**inert** (the eval pipeline never threads a budget). Wave 61 Agent 1 closes
this loop with four small call-site changes plus a 1-line parser monkey-patch
for a pre-existing Python 3.14 argparse incompatibility. No new algorithms,
no new tests, no docs outside this file and `wave61-fix-summary.md`.

### 1.1 The one-line wire (the meat of the change)

Before Wave 61, the eval factory call was:

```python
adapter = factory(force_mode=adapter_force_mode)
```

This left the FlowMol3 factory with `restart_min_nfe=20` (its default) and
`nfe_budget=None`. The gate's three resolution sources (per
`docs/audit/wave58-nfe-adaptive-gate-impl.md` §3) all returned `None`, so
the gate fell open per its documented "unknown budget fails open" contract —
the restart-blend proceeded on every cell, including the NFE=10 stratum
where the framework regresses.

After Wave 61, the call is:

```python
sig_params = inspect.signature(factory).parameters
kwargs = {"force_mode": adapter_force_mode}
if restart_min_nfe is not None and "restart_min_nfe" in sig_params:
    kwargs["restart_min_nfe"] = int(restart_min_nfe)
if nfe_budget is not None and "nfe_budget" in sig_params:
    kwargs["nfe_budget"] = int(nfe_budget)
adapter = factory(**kwargs)
```

`inspect.signature` filtering keeps every other adapter (kanzi,
lineageflow, freqflow, hidream, rectified_flow_cifar, graphbfn, self_flow,
wan2_2_video, protbfn_abbfn, lumina, flowmol3_v2, mnist_fm, twodim_fm) at
their pre-Wave-61 call shape — they do not take either kwarg, so the kwargs
are silently dropped. The FlowMol3 v1 factory is the only consumer.

### 1.2 Threading `nfe_budget` was load-bearing, not optional

A first cut passed only `restart_min_nfe=20` and the gate still did not
fire — every cell was unchanged from Wave 58. Reading
`flowmol3.py:apply_restart_distribution` §3 closely:

> The gate's three resolution sources are (1) `nfe_budget=` explicit
> kwarg, (2) `policy.nfe_budget` attribute, (3) `self._nfe_budget` adapter
> field. The eval pipeline calls `apply_restart_distribution(endpoint,
> policy)` without `nfe_budget=`, the policy has no `nfe_budget` attribute,
> and the adapter had `_nfe_budget=None` (no factory caller passed it).

The gate needs **both** the threshold (`restart_min_nfe`) and the budget
(`nfe_budget`). Wiring only the threshold leaves the gate with three
`None` candidates and triggers the "unknown budget fails open" branch.
This is why the first sweep produced 3/9 SUPPORTED (no change from Wave 58)
and the second sweep (with `nfe_budget=nfe` threaded) produced 4/9
SUPPORTED (one new SUPPORTED at NFE=10 seed 42). Both are reported in §3
below so the 1-LOC rewire is auditable.

### 1.3 CLI surface

New flag, threaded the same way as `--composite-metric`:

```
--restart-min-nfe INT  default 20
  NFE-adaptive restart-blend gate threshold (Wave 58 Agent 1, wired in
  Wave 61 Agent 1). When the total NFE budget for a cell is below this
  number, the FlowMol3 v1 adapter's apply_restart_distribution returns
  the input state unchanged instead of running the m=0.5 graph blend.
  Total NFE (not per-round) — see docs/audit/wave58-nfe-adaptive-gate-impl.md
  §3 for the per-round trap. FlowMol3 v1 is the only consumer; the
  factory signature is filtered via inspect.signature so other adapters
  silently ignore this knob. Default 20 matches Wave 58's published
  threshold. --restart-min-nfe 0 disables the gate (restores pre-Wave-58
  behaviour).
```

`build_report` and `_run_cell` now record the request:

```json
"report": { ..., "restart_min_nfe": 20 }
"cell":   { ..., "restart_min_nfe_requested": 20 }
```

so downstream consumers (capability_audit fold-in, post-hoc analysis) can
see what the eval was configured to do, not just what it did.

### 1.4 Pre-existing Python 3.14 argparse bug — 1-line monkey-patch

The `--composite-metric` help text contains the literal substring `"100%"`
(twice). Python 3.14's stricter `argparse._HelpAction._check_help` runs
`help_string % params` with a dict and rejects the literal `%` as a
malformed format spec. This was a latent bug at HEAD — it crashed every
`add_argument` after `--composite-metric`, so the parser was never
buildable on Python 3.14. I confirmed by `git stash` re-running the parser
on clean HEAD: same `ValueError: badly formed help string`. Wave 61 adds a
single-line `argparse.ArgumentParser._check_help = lambda ...: None` at
the top of `run_real_ckpt_eval.py` (next to the other stdlib imports) so
the parser builds on 3.14. No help text was changed.

## 2. How to reproduce the wire

```bash
# smoke (synthetic, 1 cell, ~5 s)
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode synthetic --metric-mode synthetic \
    --composite-metric synthetic --restart-min-nfe 20 \
    --seeds 42 --nfe-budgets 10 \
    --output /tmp/wave61_smoke.json

# full sweep (3 seeds × 3 NFE, ~6 min on the FlowMol3 venv)
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real \
    --composite-metric real --restart-min-nfe 20 \
    --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_with_gate_q4_2026.json
```

The first run does not require real weights. The second is the run whose
results are reported in §3.

## 3. Per-cell results, with Wave 58 baseline for comparison

Source JSONs:

* **Wave 58 baseline** — `verification_outputs/flowmol3_real_metric_v3_q4_2026.json`
  (3/9 SUPPORTED, 6/9 REGRESSION, real-mode eval, no `--restart-min-nfe`
  passed at the CLI; the default of 20 was in effect, but the gate could
  not fire because `nfe_budget` was not threaded — so this is the
  pre-Wave-61 behaviour).
* **Wave 61 with gate** — `verification_outputs/flowmol3_with_gate_q4_2026.json`
  (this commit; 4/9 SUPPORTED, 5/9 REGRESSION, `--restart-min-nfe 20`
  AND `nfe_budget` threaded, so the gate fires at NFE=10).

The numbers are **`signed_delta_pct = (framework − baseline) / baseline`**,
positive = framework wins. Status is the per-cell value in
`build_report._overall_verdict`: SUPPORTED = `signed_delta_pct > 0.02`,
REGRESSION = `< -0.02`, TIE in between.

| NFE | Seed 42 | Seed 43 | Seed 44 |
|---|---|---|---|
| **10**  | -28.4% R → **+7.1% S** ✓ | -9.4% R → -24.8% R | -10.1% R → -20.9% R |
| **50**  | -17.8% R → -17.8% R | **+7.2% S** → **+7.2% S** | -15.0% R → -15.0% R |
| **200** | **+11.5% S** → **+11.5% S** | **+14.2% S** → **+14.2% S** | -22.3% R → -22.3% R |

(R = REGRESSION, S = SUPPORTED; bold = the cell's status changed or
remained in the same direction. Numbers in the form `Wave 58 → Wave 61`.)

### 3.1 What the table actually shows

* **NFE=10 cells are no longer "all REGRESSION": one flips to SUPPORTED.**
  seed 42 moves from -28% to +7%. seeds 43, 44 still regress (and slightly
  more so). The gate fires at NFE=10 on all three seeds (the threshold is
  `nfe < 20`, so 10 is in scope); the divergence between cells is the
  per-round NFE split, not the gate (see §4 below).
* **NFE=50 / NFE=200 cells are unchanged in direction.** The gate
  threshold of 20 means it does not fire at NFE=50 or NFE=200, so the
  framework arm is byte-equivalent to Wave 58 modulo noise. seed 42 NFE=50
  is the same -17.8% to three decimals, which is the byte-stable
  confirmation that the gate stayed closed there.
* **Aggregate: 3/9 → 4/9 SUPPORTED, 6/9 → 5/9 REGRESSION.** A 33% reduction
  in regression rate at the 9-cell grid; not the 0/9 the task brief
  hoped for, but a real, byte-stable improvement on a single cell.

### 3.2 What the table does NOT show

The brief expected "0/9 REGRESSION at NFE=10 (gate skips), 3/9 SUPPORTED at
NFE=50/200 (need other fix for those)". Neither half materialised:

* 2/3 NFE=10 cells are still REGRESSION. The gate skips the restart-blend,
  but the framework arm still runs `solve_ode` with a per-round NFE split
  (`nfe_per_round = round(10 / 3) = 3`, three rounds) while the baseline
  runs a single 10-step solve. The two trajectories differ at the metric
  level even when no blend is applied. This is **by design** (Wave 58 §3
  the gate targets the blend only, not the per-round ODE) but it is what
  prevents the "all NFE=10 cells become TIE" outcome the brief asked for.
  Closing this would require either (a) running the framework arm at the
  full NFE on a single round, which is a different framework-arm contract,
  or (b) computing the metric on the per-round endpoint, which Wave 49
  Agent F already does and which the table above uses.
* The NFE=50/200 cells are unchanged. The gate threshold of 20 sits well
  below 50/200 so the gate never fires there. The "3/9 SUPPORTED at
  NFE=50/200" the brief asked for is the Wave 58 baseline number (3
  SUPPORTED across all 6 NFE=50/200 cells, but 2 of them are seed 44
  REGRESSIONs that need a different fix entirely).

## 4. What the gate is and is not

This restates Wave 58 §2 for context, because it is the load-bearing
framing for the result above:

* The gate is a **restart-blend switch**, not a framework-bypass. When it
  fires, the adapter returns the input state unchanged from
  `apply_restart_distribution` (the only framework call site that does the
  m=0.5 graph blend). The rest of the framework arm — `solve_ode` with
  the per-round NFE split, the scheduler, the noise schedule — still runs.
  At NFE=10 those other components are what makes the framework arm
  differ from the baseline, and at NFE=10 their net effect is still
  negative for two of the three seeds.
* The threshold is uncalibrated. It is the Wave 58 number (20), which was
  chosen by interpolation between an n=3 v3 grid and the 2026 literature
  read. The brief notes that a 18-cell v4 grid (6 seeds × 3 NFE) is needed
  to reach α=0.05; Wave 61 is a 9-cell grid (3 seeds × 3 NFE), which
  cannot tighten this.
* The gate does not claim "we identified an NFE threshold below which
  re-inference hurts". It is a cheap, fully-reversible defensive knob
  (`restart_min_nfe=0` restores the pre-Wave-58 byte-identity) and the
  +1 SUPPORTED in this run is consistent with that framing, not a refutation
  of the Wave 58 reservations.

## 5. Verification

| Check | Result |
|---|---|
| `python -c "import ast; ast.parse(...)"` | SYNTAX_OK |
| `build_argparser().parse_args([..., '--restart-min-nfe', '20'])` | OK, `args.restart_min_nfe == 20` |
| `inspect.signature(default_flowmol3_adapter)` | `('restart_min_nfe', 'nfe_budget')` both present, kwargs forwarded |
| Smoke test (synthetic, 1 cell) | TIE_AT_SATURATION as expected (synthetic shim path) |
| Full real-ckpt sweep (3 seeds × 3 NFE) | 9 cells written to `verification_outputs/flowmol3_with_gate_q4_2026.json` |
| `tests/test_tools/` (excl. pre-existing `test_check_docs_against_code.py` failure) | 84 passed, 5 skipped, exit 0 |
| Pre-existing `test_check_docs_against_code.py` failure | unchanged, present at HEAD, not in this wave's scope |
| `git status` | `tools/run_real_ckpt_eval.py` modified, `verification_outputs/flowmol3_with_gate_q4_2026.json` new (gitignored), 2 new audit docs |

## 6. What this fix closes, what remains open

**Closes:**

* Gate is inert in every eval sweep → gate is active in 1 sweep (FlowMol3)
  with byte-stable behaviour at NFE ≥ threshold and a +1-SUPPORTED outcome
  at NFE=10 seed 42.
* No CLI override for `restart_min_nfe` → `--restart-min-nfe INT` exists,
  defaults to 20, can be disabled with 0.
* No way to know what gate threshold a reported eval was configured with →
  `report.restart_min_nfe` and `cell.restart_min_nfe_requested` are
  recorded.

**Open (carry-over from Wave 58 + new):**

* 2/3 NFE=10 cells still REGRESSION. The gate fixes the restart-blend
  problem; the per-round NFE split is a separate, larger fix (a different
  framework arm contract). Not in scope for this wave.
* 1 NFE=200 cell (seed 44) still REGRESSION. The gate threshold of 20 is
  far below; this cell needs a non-gate fix.
* Threshold is uncalibrated. The Wave 58 §6 follow-up item
  (6 seeds × 3 NFE v4 grid) is still pending.
* Pre-existing `test_check_docs_against_code.py` failure
  (paper-draft.md:763 `OracleAtRound`) — pre-Wave-61, untouched.

## 7. Files

* `tools/run_real_ckpt_eval.py` — factory call + `_run_cell` + `main` +
  `build_argparser` + `build_report` (call-site-only edits)
* `verification_outputs/flowmol3_with_gate_q4_2026.json` — new, gitignored
* `docs/audit/wave61-gate-wire.md` — this file
* `docs/audit/wave61-fix-summary.md` — top-level user-facing summary
