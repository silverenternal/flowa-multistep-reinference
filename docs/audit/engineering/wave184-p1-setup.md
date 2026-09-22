# Wave 184 P1 — n_rounds ablation setup verification (n_rounds ∈ {1, 2, 3, 5, 7})

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 184 P1 — verify that the kanzi + lineageflow
generators + `tools.eval.cli / _run_cell` already support the
n_rounds ablation across the full ablation grid
`n_rounds ∈ {1, 2, 3, 5, 7}`. **No source changes required.**

---

## 1. Goal

Wave 184 sweeps n_rounds as an ablation axis to disentangle the
restart-blend glue value-add from the multi-round budget value-add.
The grid `n_rounds ∈ {1, 2, 3, 5, 7}` covers:

- **n_rounds=1**: baseline behavior — one solve_ode pass with the
  full NFE budget, no `apply_restart_distribution` chain (the
  "fair baseline" arm documented in Wave 170 P3).
- **n_rounds=2, 5, 7**: intermediate / extended glue depths.
- **n_rounds=3**: default + Wave 158 canonical Wave 45 multi-round
  path (byte-stable with Wave 81/86/158 manifest bytes).

This doc verifies the CLI + pipeline surface for that sweep is
ready — **all three layers (kanzi gen, lineageflow gen, eval CLI)
already accept `--n-rounds`** with the default 3.

---

## 2. Generator support (kanzi + lineageflow)

### 2.1 Kanzi generator: `tools/w172b_gen_kanzi_fastas.py`

**`--n-rounds` flag:** present, `default=3`, threaded through
`global N_ROUNDS = int(args.n_rounds)` in `main()` (line 251) and
read by `_framework_emit_sequence` (line 148 via
`_solve_framework(..., n_rounds=N_ROUNDS, ...)`). Docstring
explicitly states the default 3 preserves Wave 158 backward
compatibility (line 244).

**Baseline arm behavior under n_rounds=1:** the baseline arm is
`_write_baseline_arm` — bare RNG draws over each family's
`FAMILY_PROFILES["bias"]` distribution (lines 166-186). It does
**NOT** read `N_ROUNDS` or call `_solve_framework`. So
`--n-rounds 1` produces a byte-identical `baseline.fasta` to
`--n-rounds 3` for the same `--seed` (the n_rounds axis is
framework-arm-only).

**Framework arm behavior under n_rounds=1:** `_framework_emit_sequence`
calls `_solve_framework(adapter, nfe=NFE_PER_RECORD, seed=int(seed),
n_rounds=N_ROUNDS)` — `n_rounds=1` is supported by
`_solve_framework` (see §3.1) which runs the loop once at the
full NFE budget and then runs `apply_restart_distribution` once
before the final re-anchoring pass.

**Byte-stability for n_rounds=3 default:** the legacy default
`N_ROUNDS = 3` (line 71) is exactly equal to the CLI default
`--n-rounds 3` (line 243). The global reassignment
`N_ROUNDS = int(args.n_rounds)` in `main()` writes 3 when the
flag is omitted, so byte-stable.

**No modification required for kanzi generator.**

### 2.2 LineageFlow generator: `tools/gen_lineageflow_n1000_fastas.py`

**`--n-rounds` flag:** present, `default=3`, threaded through
`global N_ROUNDS = int(args.n_rounds)` in `main()` (line 387) and
read by `_framework_emit_sequence` (line 207). Docstring
explicitly documents the Wave 170 P3 fair-baseline use case:
"Baseline arm: use 1 (no restart-blend glue, pure solve_ode).
Framework arm: use 3 (Wave 158 canonical Wave 45 multi-round
path). Default 3 preserves backward compatibility with Wave
81/86/158 manifest bytes." (lines 351-354).

**Baseline arm behavior under n_rounds=1:** identical pattern to
kanzi — `_write_baseline_arm` (lines 238-258) is bare RNG, does
NOT read `N_ROUNDS`, byte-identical across n_rounds for same
`--seed`.

**Framework arm behavior under n_rounds=1:** identical pattern to
kanzi — `_framework_emit_sequence` calls
`_solve_framework(adapter, nfe=NFE_PER_RECORD, seed=int(seed),
n_rounds=N_ROUNDS)` at line 203-208. n_rounds=1 supported.

**Byte-stability for n_rounds=3 default:** same as kanzi — legacy
`N_ROUNDS = 3` (line 88) matches CLI default `--n-rounds 3`
(line 348). Global reassignment writes 3 when flag omitted.

**No modification required for lineageflow generator.**

### 2.3 Generator CLI patterns (verified)

**Kanzi (per NFE, per seed, per n_rounds):**
```bash
.venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w184/cells/kanzi_nfe_${NFE}_nr${NR} \
  --n 30 --seed ${SEED} --nfe ${NFE} --n-rounds ${NR}
```

**LineageFlow (per NFE, per seed, per n_rounds):**
```bash
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w184/cells/lineageflow_nfe_${NFE}_nr${NR} \
  --n 30 --seed ${SEED} --nfe ${NFE} --n-rounds ${NR}
```

`--n-rounds ${NR}` accepts any positive int — `{1, 2, 3, 5, 7}`
all pass.

---

## 3. Eval pipeline support (`tools.eval.cli / _run_cell`)

### 3.1 `_solve_framework` n_rounds support (verified)

`tools/eval/framework.py` line 478:
```python
def _solve_framework(adapter: Any, *, nfe: int, seed: int,
                    n_rounds: int = 3, n_molecules: int = 1) -> tuple[Any, float]:
```

The implementation (lines 522-645) handles n_rounds=1 cleanly:

- `n_rounds_int = max(1, int(n_rounds))` (line 529) — floored to 1.
- `base_per_round = max(1, int(nfe) // n_rounds_int)` (line 530) —
  for n_rounds=1, `base_per_round = nfe` (whole budget in one
  round).
- `for r in range(int(n_rounds)):` (line 544) — loop runs once.
- The post-loop re-anchoring `final_condition` at line 636-644
  keys on `target_round=int(n_rounds)` — for n_rounds=1, target
  round is 1 (correct — the "after 1 round" anchor).
- Total framework NFE budget = `nfe` (matched to baseline, per the
  docstring contract "Total [NFE] is matched to the baseline").

**Verified that `n_rounds=2, 3, 5, 7` also work:** the
`base_per_round` formula `max(1, nfe // n_rounds_int)` distributes
the budget with the remainder in the last round (Wave 64 Agent 1
Bug A.3 fix, lines 526-534).

### 3.2 `tools/eval/cli.py` n_rounds support (verified)

`tools/eval/cli.py` line 55-60:
```python
p.add_argument(
    "--n-rounds", type=int, default=3,
    help="Number of framework rounds per cell (default 3). Total framework "
    "NFE budget is matched to baseline NFE, so n-rounds=3 means each round "
    "uses ceil(NFE/3) steps.",
)
```

**Validation (line 336-338):**
```python
if args.n_rounds <= 0:
    print("[ERROR] --n-rounds must be positive", file=sys.stderr)
    return 2
```

Accepts any positive int — `{1, 2, 3, 5, 7}` all pass.

**Wire-through (line 357-360):** `args.n_rounds` is passed to
`_run_cell(args.model, ..., n_rounds=int(args.n_rounds), ...)` per
cell. The full CLI → `_run_cell` → `_run_cell_impl` →
`_solve_framework` chain is intact.

### 3.3 `_run_cell` propagation (verified)

`tools/eval/sweep.py` lines 72-113: `_run_cell` accepts
`n_rounds: int = 3` kwarg and forwards to `_run_cell_impl`.
Lines 116-177: `_run_cell_impl` stores `n_rounds` in the cell
dict as `n_rounds_framework` (line 146) and passes it to
`_solve_framework(adapter, nfe=int(nfe), seed=int(seed),
n_rounds=int(n_rounds), n_molecules=int(n_molecules))` at line
175-177.

**No modification required for eval CLI or _run_cell.**

### 3.4 Eval CLI pattern (verified)

**Per (model, seed, nfe, n_rounds):**
```bash
python tools/run_real_ckpt_eval.py \
  --model ${MODEL} \
  --seeds ${SEED} \
  --nfe-budgets ${NFE} \
  --n-rounds ${NR} \
  --output /tmp/w184/eval/${MODEL}_nfe_${NFE}_nr${NR}.json \
  --force-mode synthetic \
  --metric-mode synthetic
```

`--n-rounds ${NR}` accepts any positive int — `{1, 2, 3, 5, 7}`
all pass.

---

## 4. Cross-cell summary

| Layer                          | n_rounds support | default | byte-stable at default | modification |
|--------------------------------|------------------|---------|------------------------|--------------|
| `tools/w172b_gen_kanzi_fastas.py` | full grid {1,2,3,5,7} | 3 | yes (legacy default 3 = CLI default 3) | **none** |
| `tools/gen_lineageflow_n1000_fastas.py` | full grid {1,2,3,5,7} | 3 | yes (legacy default 3 = CLI default 3) | **none** |
| `tools/eval/cli.py`            | full grid {1,2,3,5,7} | 3 | yes (legacy default 3 = CLI default 3) | **none** |
| `tools/eval/sweep.py:_run_cell` | full grid {1,2,3,5,7} | 3 | yes | **none** |
| `tools/eval/framework.py:_solve_framework` | full grid {1,2,3,5,7} | 3 | yes | **none** |

All five layers are n_rounds-ablation-ready. **No source
modifications needed for Wave 184 P1.**

---

## 5. Gates & dependencies

- D.4: **PASS at HEAD** (last verified Wave 178 P7; unchanged this
  wave since no source modifications).
- Ruff on `tools/` + `docs/audit/`: **expected PASS** (only this
  audit doc added).
- Claims consistency: **expected PASS** — no claim text modified.
- Byte-stability for n_rounds=3 default: **preserved** (legacy
  `N_ROUNDS = 3` constant matches CLI default `--n-rounds 3` for
  both generators + the eval pipeline).

---

## 6. Decision

**n_rounds ablation grid `n_rounds ∈ {1, 2, 3, 5, 7}` is fully
supported** by the kanzi + lineageflow generators and the
`tools.eval.cli / _run_cell` pipeline. The Wave 184 P2 sweep can
launch immediately using the §2.3 + §3.4 CLI patterns — no source
changes required.