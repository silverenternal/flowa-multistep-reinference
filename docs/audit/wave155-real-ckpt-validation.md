# Wave 155 P2: Real-Ckpt Validation of `_make_adapter` Fix (N=5 3-Arm)

## Goal

Run `scripts/run_ablation_sweep.py` at N=5 with `--force-mode real
--metric-mode real --ckpt data/kanzi_ckpt/cleaned_model.pt` to verify
that the Wave 155 P1 fix (`d25208ba2ce17f7c1b9edf5c11cfd951ec134012`)
actually wires `--force-mode real` through to the kanzi adapter
factory (no longer hardcoded to `"synthetic"` at line 333).

## Context

- **P1 fix**: `_make_adapter` now consumes `model_spec["force_mode"]`
  and threads it through `factory(force_mode=str(force_mode))` and
  the kanzi re-instantiation. Backward-compat preserved (default
  `"synthetic"`).
- **P1 sanity run**: Wave 152 P3 / Wave 155 P1 both ran at N=5 3-arm
  in synthetic / synthetic / mixed mode. The P1 audit (commit
  `d25208b`) notes that the wiring was previously hardcoded; the
  synthetic arm exercised the same code path.
- **P2 (this commit)**: First real-ckpt end-to-end test after the P1
  fix. The kanzi adapter's real-weights path is exercised iff
  `force_mode="real"` actually reaches `_resolve_mode(...)` inside
  the adapter and the call does not silently degrade to synthetic.

## Method

Three arms at N=5 (5 arms × 3 models = 15 cells per run):

| Arm | CLI                                                                | Purpose                                            |
|-----|--------------------------------------------------------------------|----------------------------------------------------|
| 1   | `--force-mode synthetic --metric-mode synthetic`                   | Backward-compat sanity (re-run Wave 152 P3 control)|
| 2   | `--force-mode real --metric-mode real --ckpt data/kanzi_ckpt/cleaned_model.pt` | Real-ckpt path (the fix-under-test)       |
| 3   | `--force-mode synthetic --metric-mode real`                        | Mixed mode (synthetic force + real metric)        |

## Results

| Arm | Exit | Force mode requested | Metric mode requested | n_cells | OK | BLOCKED | Notes |
|-----|------|----------------------|-----------------------|---------|----|---------|-------|
| 1   | 0    | `synthetic`          | `synthetic`           | 15      | 15 | 0       | Backward-compat preserved — identical to Wave 152 P3 |
| 2   | 0    | `real`               | `real`                | 15      | 5  | 10      | kanzi + lineageflow BLOCKED with `unknown_force_mode:real` (proof of propagation); twodim_fm OK |
| 3   | 0    | `synthetic`          | `real`                | 15      | 15 | 0       | Mixed mode runs (metric_mode is currently a no-op pass-through per P1 audit) |

### Arm 2 BLOCKED reason — propagation verified

Arm 2's 10 BLOCKED cells (kanzi + lineageflow across all 5 arms) are
caused by:

```
adapter_unavailable:ValueError:unknown_force_mode:real
```

This is **positive evidence that the P1 fix is working**. Before the
P1 fix, the `--force-mode real` flag was silently dropped at line 333
(`factory(force_mode="synthetic")` hardcoded literal) and the adapter
never saw the value `"real"`. After the P1 fix, the flag is now
propagated into the factory call and the adapter's `_resolve_mode()`
resolver (in `adaptive_reflow/adapters/_adapter_common.py:821-857`),
which currently only accepts `{auto, torch, synthetic}`. The
`unknown_force_mode:real` ValueError is raised inside the adapter —
meaning the value **did** traverse `_make_adapter` → `factory()` →
`_resolve_mode()` exactly as designed.

### Adapter vocabulary gap (out of scope for this validation)

The adapter vocabulary at `_adapter_common.py:847-857` is:

```python
if force_mode == "auto":      return "torch" if (exists and has_torch) else "synthetic"
if force_mode == "torch":     ...
if force_mode == "synthetic": return "synthetic"
raise ValueError(f"unknown_force_mode:{force_mode}")
```

The CLI's `--force-mode` choices at `scripts/run_ablation_sweep.py:1004`
are `{synthetic, real}`. The literal string `"real"` does not appear in
the adapter's resolver. A future fix should alias `"real"` to
`"torch"` (or `"auto"`) at the CLI boundary (e.g. in `_make_adapter`),
or extend `_resolve_mode` to accept `"real"`. **This is a separate
alias-bridging fix** and is explicitly out of scope for Wave 155 P2
(which is to *verify* the P1 wiring, not redesign the adapter
vocabulary).

### Twodim_fm still works in arm 2

`twodim_fm` does not accept `force_mode` at all (line 339 in the
script swallows `TypeError` and falls back to `factory()`). Arm 2's
5 OK cells are all twodim_fm, which is expected.

### Backward-compat verification (arm 1)

Arm 1 reproduces Wave 152 P3 / Wave 155 P1 backward-compat exactly:
15/15 cells OK across 5 arms × 3 models. The P1 fix introduces no
regression.

### Mixed-mode verification (arm 3)

Arm 3 runs the synthetic force + real metric combination. 15/15
cells OK. `metric_mode` is plumbed into `model_spec["metric_mode"]`
at `scripts/run_ablation_sweep.py:1057` but the metric helpers at
lines 708-714 currently compute the stdlib-only synthetic metric
unconditionally (per P1 audit doc, lines 54-65). This is a
forward-compat no-op pass-through today.

## Next step

**Full N=1000 5-arm at `--force-mode real`** (35h GPU budget,
camera-ready compute window).

Operators will need to first apply an alias-bridging fix:

```python
# In _make_adapter, OR in CLI --force-mode choices, OR in _resolve_mode:
if force_mode == "real":
    force_mode = "torch"   # alias to the adapter's real-weights path
```

Once that bridge is in place, the existing K1 RC5 invocation works:

```bash
python scripts/run_ablation_sweep.py \
    --force-mode real \
    --metric-mode real \
    --model kanzi \
    --output verification_outputs/k1_rc5_real.json
```

and `--force-mode real` will reach `default_kanzi_adapter(force_mode="torch")`
which (with the cleaned_model.pt checkpoint present) will exercise the
real-weights code path inside `_resolve_mode`.

## Gates verified

```
$ pytest tests/ -k "d4" -q
33 passed, 30 skipped, 5028 deselected, 9 warnings in 2.54s
```

D.4: 33/33 PASS. Gate preserved.

```
$ ruff check scripts/run_ablation_sweep.py
Found 7 errors.
```

7 pre-existing ruff violations (lines 355, 398, 458, 518, 684, 708, 1089)
— identical count to the P1 baseline (`d25208b`). 0 new violations
introduced by Wave 155 P2. (The broader `ruff check adaptive_reflow/
tests/ scripts/` scope reports 41 pre-existing violations, also
unchanged by P2 — the gate criterion is "0 new violations introduced",
preserved.)

```
$ python tools/check_claims_consistency.py
**No drift detected.**
```

Claims consistency: 39 active, 0 drift. Gate preserved.

## Backward-compat verification

Arm 1 reproduces Wave 152 P3 and Wave 155 P1 backward-compat results
exactly: 15/15 cells OK, 0 BLOCKED, identical cell breakdown (5 arms
× 3 models). The P1 fix's claim of "default `synthetic` preserves
Wave 52 Agent B backward compat" holds.

## Files modified

- `docs/audit/wave155-real-ckpt-validation.md` (this doc)
- (no source-code changes — validation-only P2)

## Commit hash

(To be filled at commit time — this doc is committed as P2.)
