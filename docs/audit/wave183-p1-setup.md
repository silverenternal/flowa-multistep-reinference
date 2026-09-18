# Wave 183 P1 — 9-NFE-point setup verification (10/25/50/75/100/150/200/300/500)

**Date:** 2026-09-18
**Branch:** main
**Scope:** Wave 183 P1 — verify that the kanzi + lineageflow
generators already accept the full 9-NFE-point sweep
`NFE ∈ {10, 25, 50, 75, 100, 150, 200, 300, 500}` used by the
nfe-sweep ablation. **No source changes required.**

---

## 1. Goal

The Wave 183 nfe-sweep ablation needs to trace `pLDDT` and
`scPerplexity` as a function of NFE across a much finer grid than
the Wave 178 P6 / Wave 179 P3 coarse grid (which used only
`{50, 100, 200}`). The fine grid `NFE ∈ {10, 25, 50, 75, 100, 150,
200, 300, 500}` (9 points) covers:

- **NFE=10** — Wave 81/86/158 manifest-byte-stable legacy default;
  the "fast but noisy" left tail.
- **NFE=25, 75, 150, 300** — half-step intermediates between the
  coarse grid (Wave 178 P6 used `NFE ∈ {50, 100, 200}` only).
- **NFE=50, 100, 200** — Wave 178 P6 / Wave 179 P3 coarse grid
  (replicated for cross-wave consistency).
- **NFE=500** — the "long-budget" right tail (catches solver-level
  saturation, which Wave 35 closed at ≤ 50 steps for CIFAR-10 but
  has not been measured for protein).

This doc verifies the CLI + pipeline surface for that sweep is
ready — **both generators accept the full 9-NFE-point grid with
no validation gate, no special case, and no byte-stability
breakage at any NFE**.

---

## 2. Generator support (kanzi + lineageflow)

### 2.1 Kanzi generator: `tools/w172b_gen_kanzi_fastas.py`

**`--nfe` flag:** present at line 237-241, `type=int`, `default=10`,
no `choices=[...]` restriction, no min/max validator. Threaded
through `global NFE_PER_RECORD = int(args.nfe)` in `main()` (line
250) and read by `_framework_emit_sequence` (line 107 via
`num_steps=NFE_PER_RECORD` and line 146 via `nfe=NFE_PER_RECORD`).

```python
p.add_argument(
    "--nfe", type=int, default=10,
    help=("Per-record NFE budget for the framework arm (default 10 "
          "to match Wave 81 + Wave 86 manifest)."),
)
```

**Behavior at all 9 NFE points:** `NFE_PER_RECORD` is the per-record
NFE budget for the framework arm's `_solve_framework` call. The
budget is sliced into `n_rounds=3` rounds by the Wave 64 Agent 1
formula (`base_per_round = max(1, nfe // 3)`, `remainder` absorbed
into the last round) in `tools/eval/framework.py` lines 526-534.
All 9 NFE values divide cleanly into 3 rounds:

| NFE | base_per_round | remainder | per-round sum   |
|-----|----------------|-----------|-----------------|
| 10  | 3              | 1         | [3, 3, 4] = 10  |
| 25  | 8              | 1         | [8, 8, 9] = 25  |
| 50  | 16             | 2         | [16, 16, 18] = 50 |
| 75  | 25             | 0         | [25, 25, 25] = 75 |
| 100 | 33             | 1         | [33, 33, 34] = 100 |
| 150 | 50             | 0         | [50, 50, 50] = 150 |
| 200 | 66             | 2         | [66, 66, 68] = 200 |
| 300 | 100            | 0         | [100, 100, 100] = 300 |
| 500 | 166            | 2         | [166, 166, 168] = 500 |

Every NFE in the grid passes `max(1, nfe // n_rounds_int) >= 1` —
no edge case where a round collapses to zero steps.

**Byte-stability for NFE=10 default:** legacy default
`NFE_PER_RECORD = 10` (line 68) matches CLI default `--nfe 10`
(line 238). The global reassignment writes 10 when flag omitted.
No change in legacy Wave 81/86/158 manifest bytes.

**No modification required for kanzi generator.**

### 2.2 LineageFlow generator: `tools/gen_lineageflow_n1000_fastas.py`

**`--nfe` flag:** present at lines 335-344, `type=int`, `default=10`,
no `choices=[...]` restriction, no min/max validator. Threaded
through `global NFE_PER_RECORD = int(args.nfe)` in `main()` (line
380) and forwarded to the LineageFlow adapter via
`_build_lineageflow_adapter` (line 142) and
`_framework_emit_sequence` (line 205).

```python
p.add_argument(
    "--nfe",
    type=int,
    default=10,
    help=(
        "Per-record NFE budget for the framework arm "
        "(default: 10 to match Wave 81 + Wave 86 manifest). "
        "Wired into NFE_PER_RECORD via global reassignment in main()."
    ),
)
```

**Behavior at all 9 NFE points:** identical pattern to kanzi. The
same `nfe // n_rounds_int` slicing in `_solve_framework` applies.
The LineageFlow velocity-field call has no NFE-specific
constraints — it consumes the budget as a sequence of
`num_steps=NFE_PER_RECORD` Euler steps.

**Byte-stability for NFE=10 default:** legacy default
`NFE_PER_RECORD = 10` (line 80) matches CLI default `--nfe 10`
(line 338). No change in legacy Wave 81/86/158 manifest bytes.

**No modification required for lineageflow generator.**

### 2.3 Generator CLI patterns (verified)

**Kanzi (per NFE, per seed):**
```bash
.venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
  --outdir /tmp/w183/cells/kanzi_nfe_${NFE} \
  --n ${N} --seed ${SEED} --nfe ${NFE} --n-rounds 3
```

**LineageFlow (per NFE, per seed):**
```bash
.venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
  --outdir /tmp/w183/cells/lineageflow_nfe_${NFE} \
  --n ${N} --seed ${SEED} --nfe ${NFE} --n-rounds 3
```

`--nfe ${NFE}` accepts any positive int — the 9-point grid
`{10, 25, 50, 75, 100, 150, 200, 300, 500}` all pass with the
exact same CLI pattern (just swap the value).

---

## 3. Eval pipeline support (`tools.eval.cli / _run_cell`)

### 3.1 `_solve_framework` NFE support (verified)

`tools/eval/framework.py` line 478:
```python
def _solve_framework(adapter: Any, *, nfe: int, seed: int,
                    n_rounds: int = 3, n_molecules: int = 1) -> tuple[Any, float]:
```

The implementation handles all 9 NFE points cleanly because:

- `bundle, _ = _build_initial_state_and_condition(adapter, seed=seed, nfe=nfe)`
  (line 522) — no NFE-specific branch.
- `n_rounds_int = max(1, int(n_rounds))` (line 529) — floored to 1.
- `base_per_round = max(1, int(nfe) // n_rounds_int)` (line 530) —
  all 9 NFE values yield `base_per_round >= 3` (no degenerate 0-step
  round).
- `for r in range(int(n_rounds)):` (line 544) — loop runs 3 times
  (n_rounds=3 default).
- The post-loop re-anchoring `final_condition` at lines 636-644
  keys on `target_round=int(n_rounds)` — for n_rounds=3, target
  round is 3 (correct).
- Total framework NFE budget = `nfe` (matched to baseline, per the
  docstring contract "Total [NFE] is matched to the baseline").

**Verified that all 9 NFE points work:** the `base_per_round`
formula distributes the budget with the remainder absorbed into the
last round (Wave 64 Agent 1 Bug A.3 fix, lines 526-534). The
per-round table in §2.1 shows all 9 NFE values slice cleanly.

### 3.2 `tools/eval/cli.py` NFE support (verified)

`tools/eval/cli.py` line 55-60:
```python
p.add_argument(
    "--nfe-budgets", type=str, default="50,100,200",
    help=(
        "Comma-separated list of NFE budgets per cell "
        "(default 50,100,200 — Wave 178 P6 / Wave 179 P3 coarse grid)."
    ),
)
```

**Behavior:** `--nfe-budgets` accepts a comma-separated list of
positive ints. Wave 183 P2 must pass `--nfe-budgets
10,25,50,75,100,150,200,300,500` to drive the 9-point grid. The
list is split with `nfe_budgets = [int(x) for x in
args.nfe_budgets.split(",")]` and dispatched to `_run_cell` per
NFE.

**No validation gate, no `choices=[...]` restriction.** Any
positive int list passes.

### 3.3 `_run_cell` propagation (verified)

`tools/eval/sweep.py` lines 72-113: `_run_cell` accepts `nfe: int`
kwarg and forwards to `_run_cell_impl`. Lines 116-177:
`_run_cell_impl` stores `nfe` in the cell dict as `nfe_budget`
(line 146) and passes it to `_solve_framework(adapter, nfe=int(nfe),
seed=int(seed), n_rounds=int(n_rounds), n_molecules=int(n_molecules))`
at line 175-177. The NFE flows untouched from CLI → `_run_cell` →
`_run_cell_impl` → `_solve_framework`.

**No modification required for eval CLI or _run_cell.**

### 3.4 Eval CLI pattern (verified)

**Per (model, seed, nfe):**
```bash
python tools/run_real_ckpt_eval.py \
  --model ${MODEL} \
  --seeds ${SEED} \
  --nfe-budgets 10,25,50,75,100,150,200,300,500 \
  --n-rounds 3 \
  --output /tmp/w183/eval/${MODEL}_seed${SEED}.json \
  --force-mode synthetic \
  --metric-mode synthetic
```

`--nfe-budgets 10,25,50,75,100,150,200,300,500` accepts any
positive int list — the 9-point grid passes verbatim.

---

## 4. Smoke test results (N=2, seed 42, all 9 NFE points × 2 models)

### 4.1 Smoke methodology

Per the Wave 179 P1 / Wave 184 P1 smoke-test pattern: run all
generator invocations at N=2 records to verify the CLI accepts the
NFE point and the output layout is well-formed. **No eval** — eval
budget is reserved for Wave 183 P2 (the actual ablation sweep).

### 4.2 Smoke invocations (18 cells total, 36 FASTAs, 18 manifests)

```bash
# LineageFlow — 9 NFE points
for NFE in 10 25 50 75 100 150 200 300 500; do
  .venvs/lineageflow_venv/bin/python tools/gen_lineageflow_n1000_fastas.py \
    --outdir /tmp/w183/smoke/lineageflow_nfe_${NFE} \
    --n 2 --seed 42 --nfe ${NFE} --n-rounds 3
done

# Kanzi — 9 NFE points
for NFE in 10 25 50 75 100 150 200 300 500; do
  .venvs/kanzi_venv/bin/python tools/w172b_gen_kanzi_fastas.py \
    --outdir /tmp/w183/smoke/kanzi_nfe_${NFE} \
    --n 2 --seed 42 --nfe ${NFE} --n-rounds 3
done
```

### 4.3 Smoke result — all 18 cells PASSED

| Cell | NFE | Records (baseline / framework) | Manifest `nfe_per_record` |
|------|-----|-------------------------------|---------------------------|
| lineageflow_nfe_10   | 10  | 2 / 2 | 10  |
| lineageflow_nfe_25   | 25  | 2 / 2 | 25  |
| lineageflow_nfe_50   | 50  | 2 / 2 | 50  |
| lineageflow_nfe_75   | 75  | 2 / 2 | 75  |
| lineageflow_nfe_100  | 100 | 2 / 2 | 100 |
| lineageflow_nfe_150  | 150 | 2 / 2 | 150 |
| lineageflow_nfe_200  | 200 | 2 / 2 | 200 |
| lineageflow_nfe_300  | 300 | 2 / 2 | 300 |
| lineageflow_nfe_500  | 500 | 2 / 2 | 500 |
| kanzi_nfe_10         | 10  | 2 / 2 | 10  |
| kanzi_nfe_25         | 25  | 2 / 2 | 25  |
| kanzi_nfe_50         | 50  | 2 / 2 | 50  |
| kanzi_nfe_75         | 75  | 2 / 2 | 75  |
| kanzi_nfe_100        | 100 | 2 / 2 | 100 |
| kanzi_nfe_150        | 150 | 2 / 2 | 150 |
| kanzi_nfe_200        | 200 | 2 / 2 | 200 |
| kanzi_nfe_300        | 300 | 2 / 2 | 300 |
| kanzi_nfe_500        | 500 | 2 / 2 | 500 |

**All 18 cells PASSED.** No exceptions, no errors, no warnings
beyond the normal `[w172b-kanzi]` startup banner. Each cell emits:
- `baseline.fasta` (2 records, `>fastdllm_seed...|family=PF...` headers)
- `framework.fasta` (2 records, same header format)
- `manifest.json` with `nfe_per_record` correctly set to the
  requested NFE.

### 4.4 Smoke output paths

```
/tmp/w183/smoke/
├── kanzi_nfe_10/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_25/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_50/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_75/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_100/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_150/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_200/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_300/{baseline,framework}.fasta + manifest.json
├── kanzi_nfe_500/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_10/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_25/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_50/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_75/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_100/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_150/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_200/{baseline,framework}.fasta + manifest.json
├── lineageflow_nfe_300/{baseline,framework}.fasta + manifest.json
└── lineageflow_nfe_500/{baseline,framework}.fasta + manifest.json
```

Total: 18 cells × 3 files = 54 output files.

---

## 5. Cross-cell summary

| Layer                          | 9-NFE support | default | byte-stable at default | modification |
|--------------------------------|---------------|---------|------------------------|--------------|
| `tools/w172b_gen_kanzi_fastas.py` | full grid {10,25,50,75,100,150,200,300,500} | 10 | yes (legacy default 10 = CLI default 10) | **none** |
| `tools/gen_lineageflow_n1000_fastas.py` | full grid {10,25,50,75,100,150,200,300,500} | 10 | yes | **none** |
| `tools/eval/cli.py`            | full grid via `--nfe-budgets` | "50,100,200" (Wave 178 P6 default) | yes (legacy coarse grid preserved) | **none** |
| `tools/eval/sweep.py:_run_cell` | full grid (forwards NFE) | n/a | yes | **none** |
| `tools/eval/framework.py:_solve_framework` | full grid {10,25,50,75,100,150,200,300,500} | n/a | yes | **none** |

All five layers are 9-NFE-point-ablation-ready. **No source
modifications needed for Wave 183 P1.**

---

## 6. Per-NFE timing observation (smoke only, N=2)

Per-cell wall time on the smoke test (N=2 records, seed 42,
n_rounds=3):

| NFE  | lineageflow wall (s) | kanzi wall (s) |
|------|----------------------|----------------|
| 10   | ~0.5                 | ~0.6                |
| 25   | ~0.5                 | ~0.6                |
| 50   | ~0.5                 | ~0.6                |
| 75   | ~0.6                 | ~0.6                |
| 100  | ~0.6                 | ~0.7                |
| 150  | ~0.6                 | ~0.7                |
| 200  | ~0.7                 | ~0.7                |
| 300  | ~0.7                 | ~0.8                |
| 500  | ~0.8                 | ~0.8                |

All cells finish in < 1 s. The wall time grows mildly with NFE
(as expected — the framework arm's solver loop is `O(NFE)` in
synthetic mode) but is dwarfed by Python startup overhead.

**Extrapolation to N=30 (Wave 183 P2 production):** Wave 178 P6
reports ~3 s/cell for N=10 at NFE=200. N=30 should be ~9 s/cell at
NFE=200. NFE=500 (the slowest grid point) should be ~25 s/cell.
9 NFE × 2 models × 1 seed = 18 cells × ~25 s = **~7.5 min total
generation budget** for Wave 183 P2 at N=30, seed 42.

Eval budget (mirroring Wave 179 P3 / Wave 184 P2 patterns): N=30
× foldability + self_consistency × 18 cells × ~110 s/cell = ~33
min total eval budget (single GPU, omegafold_py310 conda env).
Combined P2 budget: ~40 min wall (well within a single Wave
budget).

---

## 7. Gates & dependencies

- D.4: **PASS at HEAD** (last verified Wave 178 P7; unchanged
  this wave since no source modifications).
- Ruff on `tools/` + `docs/audit/`: **expected PASS** (only this
  audit doc added).
- Claims consistency: **expected PASS** — no claim text modified.
- Byte-stability for NFE=10 default: **preserved** (legacy
  `NFE_PER_RECORD = 10` constant matches CLI default `--nfe 10`
  for both generators).
- GPU availability: GPU 0 (RTX PRO 6000 Black, 98 GB) + GPU 1
  (RTX 5090, 32 GB) confirmed at Wave 184 P3 (eval budget will
  reuse the same GPUs as Wave 184).

---

## 8. Decision

**9-NFE-point grid `NFE ∈ {10, 25, 50, 75, 100, 150, 200, 300,
500}` is fully supported** by the kanzi + lineageflow generators
and the `tools.eval.cli / _run_cell / _solve_framework` pipeline.
All 18 smoke cells (N=2, seed 42) PASSED — baseline + framework
FASTAs + manifest are well-formed, `nfe_per_record` is correctly
recorded in each manifest. The Wave 183 P2 sweep can launch
immediately using the §2.3 generator CLI pattern + the §3.4 eval
CLI pattern — no source changes required.