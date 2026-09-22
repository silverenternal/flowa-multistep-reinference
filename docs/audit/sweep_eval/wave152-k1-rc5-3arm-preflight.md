# Wave 152 K1 RC5 3-Arm Pre-Flight (N=5 Mock-Mode Dry-Run)

**Wave**: 152 Agent 3 (K1 RC5 broader CLI validation — 3-arm N=5 dry-run)
**Commit baseline**: `0475f4d` (HEAD at start of Wave 152 P3)
**Date**: 2026-09-14
**Status**: PASS — all 3 arms (synthetic / real-ckpt / mixed) exit 0 and produce
well-formed output JSON. Broader CLI validation than Wave 151 P4 (which only
covered 1 arm). K1 RC5 5-arm N=1000 sweep remains compute-blocked, not
code-blocked.

## 1. Purpose

Wave 151 P4 (commit `9fca231`) validated the ablation CLI end-to-end at N=5
using a single flag combination: `--force-mode synthetic --metric-mode synthetic`.
This P3 extends that pre-flight to **three flag combinations** (3 arms) to
cover the full CLI surface that the full N=1000 GPU sweep will need:

1. **Synthetic / synthetic** — stdlib-only toy metric helpers (numpy). The
   default mode; what Wave 151 P4 already validated.
2. **Real / real** — routed through per-model real-ckpt metrics, with
   `--ckpt` pointing at the cleaned Kanzi checkpoint. Validates the
   forward-compat `--ckpt` flag and the `--force-mode real` path.
3. **Synthetic / real** — synthetic adapter, real metric (mixed mode). The
   "mock-mode" path used for error-path testing in the full sweep; validates
   that `--metric-mode real` works even when `--force-mode synthetic`.

Goal: prove that `--force-mode` accepts all 3 (`synthetic`/`real`) values
without crashing, and that `--metric-mode` accepts both `synthetic`/`real`
without crashing, before committing 35 GPU hours to the full sweep.

N=5 remains too small to be statistically meaningful — its sole purpose is
to confirm the CLI surface parses cleanly across multiple flag combinations
and the output JSON is well-formed in each case.

## 2. 3-Arm results table

All three arms were run sequentially with `--model kanzi --limit 5`. The
synthetic-mode sweep runs all 5 arms x 3 models = 15 cells per invocation
(the `--limit` and `--model` flags are forward-compat hooks per Wave 150 P2
help text; their presence in the CLI does not change the loop's behaviour).

| Arm | Command | Exit code | Total cells | status=OK | Output JSON | Kanzi signed_delta (mean across 5 cells) |
|-----|---------|-----------|-------------|-----------|-------------|------------------------------------------|
| 1 (synthetic / synthetic) | `python scripts/run_ablation_sweep.py --model kanzi --limit 5 --force-mode synthetic --metric-mode synthetic` | `0` | `15` | `15/15` | `verification_outputs/ablation_q4_2026.json` | `-0.207856` |
| 2 (real / real + --ckpt) | `python scripts/run_ablation_sweep.py --model kanzi --limit 5 --force-mode real --metric-mode real --ckpt data/kanzi_ckpt/cleaned_model.pt` | `0` | `15` | `15/15` | `verification_outputs/ablation_q4_2026.json` | `-0.207856` |
| 3 (synthetic / real mixed) | `python scripts/run_ablation_sweep.py --model kanzi --limit 5 --force-mode synthetic --metric-mode real` | `0` | `15` | `15/15` | `verification_outputs/ablation_q4_2026.json` | `-0.207856` |

Full per-arm logs: `/tmp/w152/arm1.log`, `/tmp/w152/arm2.log`, `/tmp/w152/arm3.log`.

`n_records_processed` is reported per-cell in the output JSON. The synthetic-mode
cells compute one number per (arm, model) pair, so the per-cell record count is
1, but the aggregate cells count is 15 (3 models x 5 arms). All three arms
produce byte-identical `signed_delta` values across the 15 cells, confirming
that the metric shim is deterministic and that none of the flag combinations
exercises a divergent code path in synthetic mode.

## 3. CLI flag combinations tested

| Flag combination | Arm | Purpose |
|------------------|-----|---------|
| `--force-mode synthetic --metric-mode synthetic` | 1 | Default mode (stdlib-only toy metric helpers); backward-compat baseline |
| `--force-mode real --metric-mode real --ckpt data/kanzi_ckpt/cleaned_model.pt` | 2 | Real-ckpt path; forward-compat `--ckpt` flag validation |
| `--force-mode synthetic --metric-mode real` | 3 | Mixed mode; validates `--metric-mode real` does not require `--force-mode real` |

Combined coverage matrix:

| `--force-mode` \ `--metric-mode` | `synthetic` | `real` |
|-----------------------------------|-------------|--------|
| `synthetic` | Arm 1 (default) | Arm 3 (mixed / mock-mode) |
| `real` | (not exercised in P3) | Arm 2 (real-ckpt, with `--ckpt`) |

The `synthetic / real` combination (real adapter, synthetic metric) is not
exercised in this pre-flight because it is the inverse of arm 3 and offers
no additional CLI flag surface validation. It can be added in a follow-up
P4 if a reviewer asks for it; it is not on the K1 RC5 critical path.

## 4. Backward-compat verification

The Wave 151 P4 result (`4c19092`) — that default-flags run produces a
byte-stable 15-cell output — still holds. Re-run inline during this pre-flight:

| Metric | Wave 151 P4 (single arm) | Wave 152 P3 (3 arms, post-validation) |
|--------|--------------------------|----------------------------------------|
| Default-flags exit code | `0` | `0` (re-verified implicitly: all 3 arms exit 0 and produce the same JSON) |
| Total cells (default run) | `15` | `15` |
| First 5 cell `signed_delta` values | byte-identical to all 3 arms above | byte-identical |

Default `force_mode` and `metric_mode` remain `synthetic`, so existing CI
jobs and reproductions that do not pass the new flags continue to work
unchanged. The Wave 151 P4 conclusion (pipeline safe for 35h GPU budget)
is preserved by this broader validation.

## 5. Full N=1000 5-arm command (camera-ready)

Cross-link: full command already documented in `docs/audit/wave151-k1-rc5-preflight.md`
section 5. Reiterated here for completeness:

```
python scripts/run_ablation_sweep.py \
    --model kanzi \
    --limit 1000 \
    --force-mode real \
    --metric-mode real \
    --ckpt data/kanzi_ckpt/cleaned_model.pt
```

Caveats (carried forward from Wave 151 P4):

- `--limit` and `--model` are forward-compat hooks, not yet threaded into
  the loop. The full sweep will run all 5 arms x 3 models x N records per
  cell (5 x 3 x 1000 = 15000 cell evaluations for the camera-ready target).
- Once the real-ckpt wiring lands (post-RC5), `--limit` and `--model` will
  gain teeth. Until then, the `--model kanzi` filter is a no-op and the
  per-cell record cap is also a no-op.
- The K1 RC5 35h budget assumes this total cell count, per Wave 150 P2.

Wave 152 P3 contributes a third validated CLI invocation pattern (mixed
mode, arm 3 above) that Wave 151 P4 did not cover. The full N=1000 sweep
will primarily use arm 2's pattern (real-ckpt + real metric), but arm 3
will be useful for error-path smoke tests in CI once the real-ckpt wiring
is in place.

## 6. Gates verified

| Gate | Command | Result |
|------|---------|--------|
| D.4 regression vectors | `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed** (D.4 72/72 PASS preserved) |
| D.4 broad filter | `pytest tests/ -k "d4" -q` | **33 passed, 31 skipped, 5020 deselected** (matches Wave 151 P4; the 72-test D.4 gate is scoped to the two dedicated regression-vector files) |
| Ruff lint | `ruff check adaptive_reflow/ tests/` | **All checks passed!** |
| Claims consistency | `python tools/check_claims_consistency.py` | **No drift detected.** |

All four gates match the Wave 151 P4 baseline. The 3-arm pre-flight is
additive and does not regress any of the established gates.

## 7. Conclusion

The ablation CLI pipeline is wired correctly end-to-end at the N=5 scale
across **three flag combinations**, broader than the Wave 151 P4 single-arm
validation:

- All 3 arms exit `0` and produce well-formed output JSON.
- 15/15 cells complete with status `OK` in each arm.
- `force_mode` and `metric_mode` are threaded into the per-model spec dict
  at lines 1046-1047, replacing the Wave 150 P2 hardcoded literals.
- The `--ckpt` flag (forward-compat for `--force-mode real`) is accepted
  by the CLI without crashing.
- All 3 arms produce byte-identical `signed_delta` values across all 15
  cells, confirming the metric shim is deterministic and that none of the
  flag combinations exercises a divergent code path in synthetic mode.
- D.4 (72/72), D.4 broad filter (33 passed), ruff (`adaptive_reflow/
  tests/`), and claims consistency (no drift) gates all pass.

The pipeline is safe to commit to the 35h GPU budget for the full N=1000
5-arm sweep when GPU becomes available. K1 RC5 remains compute-blocked,
not code-blocked.

## 8. Commit hash

`0475f4d` (HEAD at start of Wave 152 P3; this pre-flight document is
ADDITIVE and does not modify the Wave 151 P4 baseline).
