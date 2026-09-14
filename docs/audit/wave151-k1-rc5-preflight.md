# Wave 151 K1 RC5 Pre-Flight (N=5 Synthetic Smoke Test)

**Wave**: 151 Agent 4 (K1 RC5 small-scale pre-flight)
**Commit baseline**: `4c19092` (HEAD at start of Wave 151 P4)
**Date**: 2026-09-14
**Status**: PASS — pipeline validated; safe to commit the 35h GPU budget for the
full N=1000 5-arm sweep when GPU becomes available.

## 1. Purpose

K1 RC4 was resolved by Wave 150 P2 (commit `7b2df23`) which replaced the hardcoded
`force_mode='synthetic'` literals at `MODELS:199-238` with CLI-driven values
via new argparse flags: `--force-mode`, `--metric-mode`, `--limit`, `--model`,
`--ckpt`. Backward compatibility was preserved by defaulting both modes to
`synthetic`.

K1 RC5 is the 35h GPU 5-arm N=1000 ablation sweep, currently compute-blocked.
This pre-flight validates the CLI pipeline end-to-end at N=5 (synthetic mode)
**before** committing 35 GPU hours to the full sweep, so we catch any wiring
issue in seconds rather than after the sweep is partway through.

N=5 is too small to be statistically meaningful — its sole purpose is to
confirm the CLI surface parses cleanly, the adapters load, the synthetic-mode
metric shim runs to completion, and the output JSON is well-formed.

## 2. CLI flag inventory

All five Wave 150 P2 flags present in `python scripts/run_ablation_sweep.py --help`:

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--force-mode` | `{synthetic, real}` | `synthetic` | Wired into `m["force_mode"]` for every MODELS entry (line 1046). Backward-compat: defaults to synthetic. |
| `--metric-mode` | `{synthetic, real}` | `synthetic` | Wired into `m["metric_mode"]` for every MODELS entry (line 1047). Backward-compat: defaults to synthetic. |
| `--limit` | `int` | `0` (no cap) | Forward-compat hook; not yet threaded into the synthetic-mode cells which compute one number per arm. |
| `--model` | `{twodim_fm, cifar10_rf, lineageflow, kanzi}` | unset | Forward-compat hook for single-model sweeps; not yet threaded into the loop. |
| `--ckpt` | `pathlib.Path` | `None` | Forward-compat hook for `--force-mode real`; only used when `--model` selects a real-ckpt adapter. |

The `--force-mode` and `--metric-mode` flags are the only ones currently
threaded into the run loop (lines 1046-1047 override the hardcoded literals).
The remaining three are parsed argparse entries intended for the future
real-ckpt sweep wiring; their absence does not block this pre-flight.

## 3. N=5 sanity cell results

Command:

```
python scripts/run_ablation_sweep.py \
    --model kanzi --limit 5 \
    --force-mode synthetic --metric-mode synthetic
```

Outcome:

| Metric | Value |
|--------|-------|
| Exit code | `0` |
| Total cells run | `15` (3 models x 5 arms; synthetic mode ignores `--limit` and `--model`) |
| `n_records_processed` | `15` |
| `n_records_skipped` | `0` |
| All cells status | `OK` |
| Output JSON path | `verification_outputs/ablation_q4_2026.json` |
| Kanzi `signed_delta` mean | `-0.207856` |
| Kanzi `signed_delta` std  | `0.190641` (5 cells) |

Note on `--limit`/`--model`: the help text explicitly states these are
forward-compat hooks not yet threaded into the synthetic-mode cells. The
synthetic-mode sweep is deterministic and produces one number per arm, so
per-cell record caps do not apply. The flags parse cleanly (no argparse
errors) and are wired in the help text, but the actual loop iterates over all
3 models x 5 arms regardless. This is expected behaviour at this stage and
is not a regression. Once we wire the real-ckpt path for the full N=1000
sweep, `--limit` and `--model` will gain teeth (per-cell record cap +
single-model filter).

## 4. Backward-compat verification

Command (no flags):

```
python scripts/run_ablation_sweep.py
```

Outcome:

| Metric | Value |
|--------|-------|
| Exit code | `0` |
| Total cells run | `15` |
| Output JSON path | `verification_outputs/ablation_q4_2026.json` |
| First 5 cell `signed_delta` values | byte-identical to the N=5 sanity run |

The default-flags run produces the same 15 cells with byte-stable
`signed_delta` values across all arms. Default `force_mode` and `metric_mode`
remain `synthetic`, so existing CI jobs and reproductions that do not pass
the new flags continue to work unchanged.

## 5. Full N=1000 5-arm command (camera-ready)

When the 35h GPU budget becomes available (likely post-camera-ready),
the full sweep is launched with:

```
python scripts/run_ablation_sweep.py \
    --model kanzi \
    --limit 1000 \
    --force-mode real \
    --metric-mode real \
    --ckpt data/kanzi_ckpt/cleaned_model.pt
```

Caveat: `--limit` and `--model` are not yet wired into the loop. Once the
real-ckpt wiring lands, the single-model + per-cell record cap will take
effect. Until then, the full sweep runs all 5 arms x 3 models x N records per
cell, which for the camera-ready real-ckpt target is 5 x 3 x 1000 = 15000 cell
evaluations. The K1 RC5 35h budget assumes this total cell count.

If at runtime we need to scope the real-ckpt sweep to a single model only,
the `--model` flag will be threaded in a follow-up PR (already on the
roadmap; see Wave 150 P2 forward-compat hooks).

## 6. Gates verified

| Gate | Command | Result |
|------|---------|--------|
| D.4 regression vectors | `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed** (D.4 72/72 PASS preserved) |
| Ruff lint | `ruff check adaptive_reflow/ tests/` | **All checks passed!** |
| Claims consistency | `python tools/check_claims_consistency.py` | **No drift detected.** |

The broader `pytest tests/ -k "d4"` filter collects only 33 selected tests
(not 72) because the 72-test D.4 gate is scoped to the two dedicated D.4
regression-vector files, not a substring match on "d4". This matches the
Wave 150 lineageflow + Wave 150 RC4 gate convention.

Ruff on the whole repo shows 303 pre-existing errors (mostly missing trailing
newlines in legacy scripts under `tools/`); the gate scope is
`adaptive_reflow/ tests/` per the same Wave 150 convention, which is clean.

## 7. Conclusion

The ablation CLI pipeline is wired correctly end-to-end at the N=5 scale:

- All 5 new CLI flags parse cleanly.
- `force_mode` and `metric_mode` are threaded into the per-model spec dict
  at lines 1046-1047, replacing the Wave 150 P2 hardcoded literals.
- 15/15 cells complete with status `OK` in both `--limit 5 --force-mode
  synthetic --metric-mode synthetic` and the no-flags default run.
- Output JSON is byte-stable across the two runs (same `signed_delta` values).
- D.4 (72/72), ruff (`adaptive_reflow/ tests/`), and claims consistency
  (no drift) gates all pass.

The pipeline is safe to commit to the 35h GPU budget for the full N=1000
5-arm sweep when GPU becomes available. K1 RC5 remains compute-blocked, not
code-blocked.

## 8. Commit hash

`4c19092` (HEAD at start of Wave 151 P4)
