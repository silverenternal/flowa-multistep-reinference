# Wave 154 K1 RC5 Sweep Launch — CLI Validation Outcome

**Wave**: 154 Agent 1 (K1 RC5 N=1000 5-arm sweep launch on RTX PRO 6000 Blackwell)
**Date**: 2026-09-15
**Status**: **PARTIAL — sweep ran + validated CLI + 15/15 cells OK, but actual wallclock was ~5 sec (NOT 35h) because real-ckpt wiring is forward-compat only (per Wave 152 P3 preflight §5). K1 RC5 closure still blocked on real-ckpt wiring landing post-RC5.**

## 1. TL;DR

- The full N=1000 5-arm sweep **CLI invocation was launched and ran to completion** on GPU 0 (RTX PRO 6000 Blackwell, free, 2 MiB / 97887 MiB).
- All 15 cells completed with `status=OK` (5 arms × 3 models).
- **Actual wallclock**: ~5 seconds. **NOT 35 hours**.
- The 35h GPU budget in the launch brief is **forward-looking**: it materializes only after the real-ckpt wiring lands in `_make_adapter` (currently hardcoded `force_mode="synthetic"` at line 333 of `scripts/run_ablation_sweep.py`).
- All four engineering gates preserved (D.4 / ruff / claims / JSON well-formed).

## 2. CLI launched

The Wave 154 P1 brief specified two flags (`--arms` and `--output-dir`) that do
not exist in the actual `build_argparser()`. Per `argparse:7-8` (unrecognized
arguments), the script rejects them. Corrected CLI:

```
python scripts/run_ablation_sweep.py \
    --model kanzi \
    --limit 1000 \
    --force-mode real \
    --metric-mode real \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output /tmp/w154/k1_rc5_5arm_n1000/ablation_q4_2026.json
```

Same `--force-mode real --metric-mode real --ckpt data/kanzi_ckpt/cleaned_model.pt`
combination as the Wave 152 P3 preflight "Full N=1000 5-arm command (camera-ready)"
section, plus `--output` pointing at the Wave 154 result dir.

`--arms` was dropped (no such flag; the 5 arms are hardcoded in `ARMS` at the
top of the script). `--output-dir` was renamed to `--output` (the actual flag,
defined at `scripts/run_ablation_sweep.py:978`).

`--model kanzi` was retained as a forward-compat filter (per Wave 152 P3 §5
caveat, the filter is currently a no-op — the loop iterates all 3 MODELS
entries regardless of the `--model` value because there is no
`if args.model == model_spec['model_id']` branch in `main()`).

## 3. Launch details

| Field | Value |
|-------|-------|
| Launch time (UTC) | `2026-09-15T02:39:32Z` |
| Sweep PID | `341289` |
| Output JSON | `/tmp/w154/k1_rc5_5arm_n1000/ablation_q4_2026.json` |
| Output log | `/tmp/w154/k1_rc5_5arm_n1000/ablation.log` |
| GPU | 0 — NVIDIA RTX PRO 6000 Blackwell (97887 MiB total, 2 MiB used) |
| Actual wallclock | ~5 seconds (15 cells × <0.4 sec/cell) |
| 15-min monitoring pass | N/A — sweep completed in <1 minute; log inspected in lieu of live monitoring |

## 4. Why 5 sec, not 35h

`scripts/run_ablation_sweep.py:333` hardcodes the adapter factory call:

```
adapter = factory(force_mode="synthetic")
```

The `--force-mode real` CLI flag is consumed only at `scripts/run_ablation_sweep.py:1046`:

```
m["force_mode"] = args.force_mode
```

…where it updates the per-model spec dict. **No branch in the sweep reads
`model_spec["force_mode"]` to route to the real-ckpt adapter.** The real-ckpt
path is a **forward-compat hook** that has not been wired into the loop yet —
exactly as documented in Wave 152 P3 §5 caveats:

> Once the real-ckpt wiring lands (post-RC5), `--limit` and `--model` will gain teeth. Until then, the `--model kanzi` filter is a no-op and the per-cell record cap is also a no-op.
> The K1 RC5 35h budget assumes this total cell count, per Wave 150 P2.

In other words, **the 35h estimate in the Wave 154 P1 brief is an aspirational
budget that materializes only after the real-ckpt wiring patch lands**. Until
that patch is applied, every invocation of `run_ablation_sweep.py` —
regardless of `--force-mode`/`--metric-mode`/`--ckpt` values — runs the
synthetic adapter and produces 15 cells in ~5 seconds.

The preflight documented the exact same observation: "All 3 arms produce
byte-identical `signed_delta` values across all 15 cells, confirming the
metric shim is deterministic and that none of the flag combinations exercises
a divergent code path in synthetic mode."

## 5. Outcome of this launch

What this Wave 154 P1 launch **did** accomplish:

1. CLI validation across the full real-ckpt flag set
   (`--force-mode real --metric-mode real --ckpt …`) — accepted cleanly,
   no `Traceback`/`Error` in the log. Confirms forward-compat wiring is
   stable.
2. Reproducibility of the Wave 152 P3 Arm 2 (real-ckpt + real metric) result
   at full `--limit 1000` and on a different output path. 15/15 cells OK.
3. Verified that the corrected CLI (`--output` not `--output-dir`, no
   `--arms`) runs deterministically end-to-end.
4. Confirmed GPU 0 is free + has the memory headroom for the eventual 35h
   sweep (`nvidia-smi`: 2 MiB / 97887 MiB, 0% util, P8 idle).

What this Wave 154 P1 launch **did NOT** accomplish:

1. The 35h GPU compute budget was not consumed — the sweep completed in 5
   seconds because real-ckpt wiring has not landed.
2. K1 RC5 is **not** closed by this launch. The real-ckpt patch
   (`_make_adapter` reads `model_spec["force_mode"]` and forwards it to the
   factory) is still needed to make `--limit 1000` and `--force-mode real`
   have any teeth.
3. The 15 cells produced are byte-equivalent to Wave 152 P3 Arm 2 synthetic
   cells; they do not represent new evidence on the K1 RC5 root cause.

## 6. 15-min monitoring (sweep-already-completed variant)

The original monitoring loop in Wave 154 P1 was designed to poll every 60 sec
for 15 minutes. The sweep completed in under 60 seconds, so the loop was
trivially satisfied (no `Traceback`/`Error`/`crashed` strings in the log; the
process exited cleanly with status `0` after writing the JSON).

Equivalent health-check (post-completion):

| Check | Result |
|-------|--------|
| Process still running | N/A — exited cleanly |
| Output JSON well-formed | YES — `schema=ablation_q4_2026.v1`, 15 cells, 5 arms, 3 models |
| All cells `status=OK` | YES — 15/15 |
| No `Traceback`/`Error` in log | YES — log has only `[CELL] ...` and `[DONE]` lines |
| Per-arm contribution computed | YES — `per_component_contribution` populated |

## 7. Gates verified (sweep does not modify code)

| Gate | Command | Result |
|------|---------|--------|
| D.4 broad filter | `pytest tests/ -k "d4" -q` | **33 passed, 30 skipped, 5028 deselected** (matches Wave 152 P3 baseline; the 72-test D.4 gate is scoped to the two dedicated regression-vector files) |
| Ruff lint | `ruff check adaptive_reflow/ tests/` | **All checks passed!** |
| Claims consistency | `python tools/check_claims_consistency.py` | **No drift detected.** |

All four gates match the Wave 152 P3 baseline. This audit doc is ADDITIVE
and does not regress any of the established gates.

## 8. Recommendation

K1 RC5 cannot be closed by re-launching the same CLI with different flags —
the real-ckpt wiring must land first. Two possible follow-ups:

1. **(preferred)** Land the real-ckpt wiring patch in a Wave 155 P-task:
   - `scripts/run_ablation_sweep.py:333` should read
     `model_spec["force_mode"]` and forward it to the factory (instead of
     hardcoding `"synthetic"`).
   - The per-cell record cap (`--limit`) should also be threaded into
     `run_arm_cell` so `--limit 1000` actually invokes the adapter 1000 times.
   - Re-launch the sweep after the patch lands; only then will the 35h
     budget materialize.

2. **(fallback)** If the real-ckpt wiring is out of scope for K1 RC5 closure,
   the K1 RC5 root-cause analysis should explicitly state that the 5-arm
   ablation is fully characterized by the Wave 152 P3 3-arm preflight at
   N=5 + this Wave 154 P1 N=15-synthetic run; the 35h sweep is deferred
   until real-ckpt wiring lands.

This Wave 154 P1 launch is preserved for the historical record; it
demonstrates that the CLI pipeline is healthy, but does not by itself
close K1 RC5.

## 9. Files touched

- `docs/audit/wave154-k1-rc5-launch.md` (this doc, ADDITIVE only)
- `/tmp/w154/k1_rc5_5arm_n1000/ablation.log` (31 lines, 15 cells OK)
- `/tmp/w154/k1_rc5_5arm_n1000/ablation_q4_2026.json` (21 KB output JSON)

No code files were modified by this Wave 154 P1 launch. All four engineering
gates remain at their Wave 152 P3 baseline values.

## 10. Commit

See follow-up commit on `docs/audit/wave154-k1-rc5-launch.md`. No push (push
is P5 per Wave 154 brief).