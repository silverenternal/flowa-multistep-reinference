# Wave 111.0 Reviewer B — Configuration Scattering Audit

**SHA (HEAD):** `70501280ac0e9e197064d3b2b029bb0787289403`
**Date:** 2026-09-11
**Mode:** READ-ONLY
**Scope:** Identify the 5-10 settings that SHOULD live in a per-model run-profile
config file (`configs/runs/<model>_<purpose>.yaml`) but are currently scattered as
CLI flags across sweep drivers, with inconsistent defaults and copy-paste
invocations.

## Context

- User feedback 2026-09-11: "all runtime configs should be config-file driven, not
  command-line; command-line is error-prone."
- Wave 88 F-4 stochasticity caveat (`0.0947 Å`) was caused by an unseeded
  `DAE.decode` in the Kanzi bridge — solved in Wave 108.A by threading `--seed`
  through the driver. Today every driver re-implements `--seed` with the same
  default of `42`, and none of them enforce it as the only valid invocation.
- Wave 110.C PARTIAL (4 sweeps × 71 min) could not be issued as a single command
  because `--seed`, `--device`, `--n-steps-decoder`, and `--pb-engine` had to be
  re-passed on every driver invocation.
- Wave 95.1.D flipped `--pb-engine` default to `xtb` in only 2 of the 3 Kanzi
  sweep drivers, and `Wave 105 P0-B` added `--pb-engine` as a CLI flag rather than
  as a per-model profile default — see `tools/sweep_kanzi_n1000_paper_metrics.py`
  (lines 62-66).

## Section 1 — Per-Concept Settings Table

Below: the 12 settings that appear as `--flag` arguments across the sweep-driver
fleet. The "drivers" column is the set of top-level CLI scripts that take the
flag; defaults are quoted from `add_argument(..., default=...)` source code (not
from runbooks).

| # | Setting | Concept | Drivers taking it | Default per driver | Consistent? | Should migrate to YAML? |
|---|---|---|---|---|---|---|
| 1 | `--seed` / `--seeds` | RNG seed | `tools/eval/cli.py:43-44` (--seeds, required, CSV), `tools/sweep_kanzi_n1000_paper_metrics.py:55` (default 42), `tools/sweep_kanzi_n1000_framework_paper_metrics.py:66` (default 42), `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:64` (default 42), `tools/sweep_kanzi_n1000_diverse.py:118-120` (default 42), `tools/run_ablation.py` (DEFAULT_SEED, see `tools/run_ablation.py:128-130` area), `tools/wave87_n1000_sweep.py` (n/a — uses single positional), `tools/upstream_eval.py:432-439` (no --seed, takes positional) | `42` (Kanzi family), `0`/`None` (`run_ablation`), required-CSV (`eval/cli`) | **No** — `eval/cli.py` requires CSV, `sweep_kanzi_*` defaults to 42, `run_ablation.py` uses module-level `DEFAULT_SEED`, `upstream_eval.py` has no seed flag at all | **YES** — Wave 88 F-4 root cause |
| 2 | `--pb-engine` (uff / xtb) | PoseBusters engine | `tools/sweep_kanzi_n1000_paper_metrics.py:62-66` (default `uff`), `tools/sweep_kanzi_n1000_framework_paper_metrics.py:73-77` (default `uff`), `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` (no flag — uses runner default `uff`) | `uff` in 2 of 3 — Wave 95.1.D inconsistency | **No** — inv_proj driver was missed | **YES** — per-model profile |
| 3 | `--n-steps-decoder` / `--nfe` / `--nfe-budgets` / `--nfe` | NFE budget | `tools/eval/cli.py:46-49` (--nfe-budgets, required CSV), `tools/sweep_kanzi_n1000_paper_metrics.py` runner nfe_steps=100, `tools/sweep_kanzi_n1000_framework_paper_metrics.py:69-72` (default 100), `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:62` (default 100), `tools/sweep_kanzi_n1000_diverse.py:116-118` (default 100), `tools/run_rf_cifar_ablation.py` (default 2) | `100` for Kanzi family, `2` for CIFAR-10 RF, required-CSV for `eval/cli.py` | **No** — different defaults per model family, no single source of truth | **YES** — model-dependent |
| 4 | `--max-records` / `--limit` / `-n / -N / --N` | N records cap | `tools/sweep_kanzi_n1000_paper_metrics.py:51-53` (--limit, default None), `tools/sweep_kanzi_n1000_framework_paper_metrics.py:78-80` (--limit, default None), `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:65` (--limit, default 1000), `tools/sweep_kanzi_n1000_diverse.py:121-123` (--max-records, default 1000), `tools/upstream_eval.py:435-436` (--max-records, default 0 = all) | `None` (2 drivers), `1000` (2 drivers), `0=all` (`upstream_eval.py`) | **No** — 4 different defaults for the same concept | **YES** — per-run profile |
| 5 | `--force-mode` (synthetic / real / auto) | Adapter mode | `tools/eval/cli.py:64-74` (default `synthetic`, Wave 41.B) | `synthetic` (default in `eval/cli.py`); `tools/run_real_ckpt_eval.py` factory defaults differ per adapter | **No** — Wave 50.A fixed flowmol3 factory, but Kanzi/LineageFlow factory dispatch still has implicit "real if available" branches | **YES** — per-model profile |
| 6 | `--composite-metric` (synthetic / real / auto) | Composite metric mode | `tools/eval/cli.py:107-131` (default `auto`, Wave 47 + Wave 49) | `auto` only in `eval/cli.py`; Kanzi+LineageFlow+FlowMol3 composite are wired there but no other driver exposes the flag | **Partly** — single-flag surface exists but only for `eval/cli.py` | **YES** — per-model profile |
| 7 | `--paper-metrics` (action=store_true) | Paper-parity opt-in | `tools/eval/cli.py:146-162` (default False, Wave 75) | Only `eval/cli.py` exposes it | **Single-driver** but conceptually belongs to the run profile | **YES** — per-model profile |
| 8 | `--paper-reference` (GEOM_DRUGS / NCI_first_5K_proxy) | Paper reference distribution | `tools/eval/cli.py:163-176` (default `GEOM_DRUGS`, Wave 75) | Only `eval/cli.py` | **Single-driver** | **YES** — per-model profile |
| 9 | `--restart-min-nfe` | NFE-adaptive gate threshold | `tools/eval/cli.py:90-106` (default 20, Wave 58) | Only `eval/cli.py`; factory signature filters to FlowMol3 v1 | **Single-driver** but conceptually framework-level | **YES** — algorithm-tier profile |
| 10 | `--n-molecules` | Multi-mol per cell | `tools/eval/cli.py:132-145` (default 1, Wave 74 F1) | Only `eval/cli.py`; FlowMol3 v2 only consumer | **Single-driver** | **YES** — per-model profile |
| 11 | `--upstream-n-samples` | Upstream eval N | `tools/eval/cli.py:247-258` (default 1000, Wave 79/92b) | Only `eval/cli.py` | **Single-driver** but very expensive to mis-set (1.5-4h/cell) | **YES** — per-model profile |
| 12 | `--metric-mode` (synthetic / real / auto) | Per-cell downstream metric mode | `tools/eval/cli.py:75-89` (default `synthetic`, Wave 43) | Only `eval/cli.py` | **Single-driver** | **YES** — per-model profile |

Additional flags audited but NOT recommended for YAML migration (kept on CLI):

- `--input` / `--ckpt` / `--output-dir` — per-invocation I/O paths, not config.
- `--upstream-eval` opt-ins (`--lineageflow-upstream-eval`, `--kanzi-upstream-eval`,
  `--flowmol3-upstream-eval`, `--kanzi-framework-paper-metrics`) — boolean toggles
  for opt-in features; better as CLI than config-file.
- `--print-only` / `--disable-XXX` — debugging toggle, single-driver.
- `--device` (auto / cuda / cuda:0 / cpu) — only `tools/run_image_eval.py`
  exposes it; rare to need per-model pinning.
- `--weights-path` / `--reference-features` — only
  `tools/run_rf_cifar_ablation.py`; one-off ablation driver.

## Section 2 — Proposed YAML Schema

Config-file location: `configs/runs/<model>_<purpose>.yaml` (per-model run
profile). Drivers consume via `--config <yaml>` and override nothing by default.

```yaml
# configs/runs/kanzi_n1000_baseline.yaml
# Purpose: Wave 109.A-equivalent Kanzi N=1000 baseline-arm paper-metric sweep.
# Profile version: 2026-09-11 (Wave 109.A). Authoritative defaults — any CLI
# override is byte-stable per Wave 105 P1-A refactor.
model: kanzi                            # drives --model in eval/cli.py

# --- §1. RNG / determinism (closes Wave 88 F-4) ---
seed: 42                                # Kanzi DAE.decode stochasticity
                                       # (Wave 108.A — closes Wave 88 F-4)

# --- §2. Adapter operating mode (Wave 41.B + Wave 50) ---
force_mode: synthetic                   # synthetic|real|auto
metric_mode: synthetic                  # synthetic|real|auto (Wave 43)
composite_metric: auto                  # synthetic|real|auto (Wave 47+49)

# --- §3. Sweep axes ---
nfe_budgets: [100]                      # DAE.decode diffusion steps
max_records: 1000                       # N records (cap; 0 = all)
n_rounds: 3                             # framework rounds per cell
n_molecules: 1                          # Wave 74 F1 (Kanzi honors single)

# --- §4. Per-model engine knob (Wave 95.1.D + Wave 105 P0-B) ---
pb_engine: uff                          # uff|xtb (PoseBusters downstream)

# --- §5. Algorithm-tier (framework knobs) ---
restart_min_nfe: 20                     # Wave 58 NFE-adaptive gate

# --- §6. Paper-metric tier (Wave 75 + Wave 79) ---
paper_metrics: false                    # opt-in 4 paper-parity metrics
paper_reference: GEOM_DRUGS             # GEOM_DRUGS|NCI_first_5K_proxy
kanzi_upstream_eval: true               # Wave 79 subprocess opt-in
kanzi_framework_paper_metrics: true     # Wave 91 Phase 3 framework arm
upstream_n_samples: 1000                # Wave 92b upstream N

# --- §7. I/O (NOT migrated — kept on CLI per audit §1) ---
# input_path: verification_outputs/kanzi_n1000_coords.txt   # CLI: --input
# output_dir: verification_outputs/kanzi_n1000_paper_metrics  # CLI: --output-dir
```

```yaml
# configs/runs/flowmol3_n1000_paper.yaml
# Purpose: Wave 87-equivalent FlowMol3 N=1000 PB-xtb paper-metric sweep.
model: flowmol3_v2

seed: 42
force_mode: real                        # Wave 50.A factory fix
metric_mode: real                       # Wave 53 Agent B real→torch wiring
composite_metric: real                  # Wave 49 Agent D 5-axis chemistry

nfe_budgets: [250]                      # FlowMol3 paper NFE
max_records: 1000
n_rounds: 3
n_molecules: 4                          # Wave 74 F1 multi-mol

pb_engine: xtb                          # Wave 74 F3 — xtb path only
restart_min_nfe: 20                     # FlowMol3 v1 is the only consumer

paper_metrics: true                     # Wave 75 4-metric paper-parity
paper_reference: GEOM_DRUGS
flowmol3_upstream_eval: false           # Wave 79 — use --paper-metrics instead
upstream_n_samples: 1000
```

CLI invocation contract:

```bash
# Today (Wave 110.C PARTIAL — 4 sweeps × 71 min):
python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir verification_outputs/kanzi_n1000_paper_metrics \
    --seed 42 --pb-engine uff --n-steps-decoder 100 --max-records 1000

# Proposed (Wave 111.B target):
python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --output-dir verification_outputs/kanzi_n1000_paper_metrics \
    --config configs/runs/kanzi_n1000_baseline.yaml
# CLI accepts --config and overrides nothing by default; per-flag override
# remains opt-in for ablation but is error-prone — the profile wins.
```

## Section 3 — Top-5-10 Settings Priority List

Ranked by frequency-of-use × error-proneness × Wave-history root-cause weight:

| Rank | Setting | Why it tops the list |
|---|---|---|
| 1 | **`--seed`** | Wave 88 F-4 root cause (0.0947 Å stochasticity). 5+ drivers re-implement; `upstream_eval.py` has no flag at all. RNG mis-set silently corrupts every downstream metric — invisible until you compare two cells. |
| 2 | **`--pb-engine` (uff vs xtb)** | Wave 95.1.D default-flip inconsistency: 2 of 3 Kanzi drivers got the flip, `inv_proj` was missed. Wave 87 explicitly noted UFF-vs-xtb semantic divergence — wrong engine silently changes paper-metric numbers. |
| 3 | **`--force-mode` (synthetic / real / auto)** | Wave 50.A + Wave 110.B bug chain: FlowMol3 factory was producing random weights when `force_mode=real` but no ckpt was passed; Kanzi `framework_inv_proj` shape mismatch (Bug 2). Per-model profile default of `real` is the only safe choice at N=1000. |
| 4 | **`--nfe-budgets` / `--n-steps-decoder`** | Different per-model defaults (`100` for Kanzi, `2` for CIFAR-10 RF, `250` for FlowMol3) and no central registry. Wave 110.C's 4 sweeps needed 4 different NFE values; today this is re-passed each time. |
| 5 | **`--max-records` / `--limit`** | 4 different defaults across 4 drivers (`None`, `1000`, `1000`, `0=all`). The `inv_proj` driver defaults to `1000` (its baseline), the `framework_paper_metrics` driver defaults to `None` (smoke-friendly). Wave 109.A had to re-pass `--max-records 1000` 4×. |
| 6 | **`--composite-metric`** | Wave 47 + Wave 49 + Wave 52 wired 3 different composites (lineageflow_composite, flowmol3_composite, kanzi_composite) but only `eval/cli.py` exposes the flag. Re-running a Wave 47 sweep with `composite_metric=real` is impossible from the legacy sweep drivers. |
| 7 | **`--upstream-n-samples`** | Wave 92b patched `tools/upstream_eval.py` to honor `--upstream-n-samples` (default 1000). Each cell costs 1.5-4h — typo'd `10000` would burn 15-40h silently. Per-profile default is the only safe surface. |
| 8 | **`--paper-metrics` / `--paper-reference`** | Wave 75 added 4 paper-parity metrics but as a CLI boolean (`--paper-metrics`); the `paper_reference` choice (GEOM_DRUGS vs NCI_first_5K_proxy) silently changes the fg_dev number. Per-profile default avoids mis-comparison across cells. |
| 9 | **`--restart-min-nfe`** | Wave 58 framework-tier knob (default 20). Currently `--restart-min-nfe 0` disables the gate; only FlowMol3 v1 honors it. Per-profile default of 20 keeps the algorithm-tier behavior consistent across 9-cell sweeps. |
| 10 | **`--n-molecules`** | Wave 74 F1 opt-in for multi-mol per cell; only FlowMol3 v2 honors it. A profile-level default (`1` for paper parity, `4` for ablation) prevents the Wave 75 drop-SMILES bug class from re-emerging. |

## Section 4 — Design Notes

### What the config files look like

- **Location:** `configs/runs/<model>_<purpose>.yaml` (one file per
  model×purpose tuple). Mirrors the existing `tools/pb_config_with_energy_ratio.yaml`
  pattern (Wave 82 vendored it for FlowMol3 PB-xtb).
- **Schema:** flat key-value (PyYAML-safe_load). No nested includes.
- **Required fields:** `model`, `seed`, `nfe_budgets`, `max_records`, `force_mode`,
  `metric_mode`. Optional fields use the YAML schema defaults above.
- **Versioning:** top-level `# Profile version: 2026-09-11 (Wave XXX)` comment.
  Drivers refuse to load profiles with a newer version than they understand.

### Where they live

- `configs/runs/` is the canonical dir. Existing YAML (Wave 82
  `tools/pb_config_with_energy_ratio.yaml`) stays in `tools/` because it's
  consumed by `tools.paper_metrics`, not by a sweep driver — different concern.
- `docs/configs.md` (new) indexes the 5-10 profiles with one-line summaries.

### How drivers consume them

Each sweep driver:

1. Adds ONE new flag: `--config <yaml>`. All other `--flag` defaults still work
   for backward-compat (Wave 105 P1-A byte-stable contract).
2. Resolution order: CLI flag > YAML value > module-level default. CLI wins.
3. Helper: `tools.eval.config.load_run_profile(path: Path) -> dict` —
   validates schema, raises on missing required keys, raises on unknown keys.
4. Print summary on load: `[PROFILE] kanzi_n1000_baseline.yaml v=2026-09-11
   seed=42 force_mode=synthetic nfe=[100] N=1000 pb_engine=uff` — visible in
   the cell loop (the `eval/cli.py:312-320` `[CELL]` print).

### Migration sequencing (Wave 111.B candidate, not implemented)

1. Add `tools.eval.config` module + `--config` flag to `tools/eval/cli.py`.
2. Migrate the 3 Kanzi sweep drivers to use `--config` with backward-compat
   defaults preserved.
3. Migrate `tools/sweep_kanzi_n1000_diverse.py` and `tools/wave87_n1000_sweep.py`.
4. Migrate `tools/run_image_eval.py`, `tools/run_rf_cifar_ablation.py`,
   `tools/run_ablation.py`.
5. Drop the legacy CLI defaults (gate behind a `DeprecationWarning` for 1 wave).

### What this fixes (concrete Wave history)

- **Wave 88 F-4**: 0.0947 Å caveat closes permanently (single seed source).
- **Wave 110.C PARTIAL**: 4 sweeps × 71 min collapses to `for cfg in
  configs/runs/*.yaml; do run --config $cfg; done` (or one shell wrapper).
- **Wave 95.1.D inconsistency**: `--pb-engine` flip is a one-line YAML edit,
  not 3 PRs across 3 drivers.
- **Wave 50.A factory bug**: `force_mode: real` in the YAML profile becomes
  the single source of truth for "use real ckpt" — no more implicit
  factory-dispatch branches.

## Citations

All file:line citations use SHAs from the current HEAD `70501280ac0e9e197064d3b2b029bb0787289403`:

- `tools/eval/cli.py` — SHA `b3aa8fd96cb83e3728125e99d4a7e44982369469`
  - L43-44: `--seeds` (required CSV)
  - L46-49: `--nfe-budgets` (required CSV)
  - L64-74: `--force-mode` (default `synthetic`)
  - L75-89: `--metric-mode` (default `synthetic`)
  - L90-106: `--restart-min-nfe` (default 20)
  - L107-131: `--composite-metric` (default `auto`)
  - L132-145: `--n-molecules` (default 1)
  - L146-162: `--paper-metrics` (default False)
  - L163-176: `--paper-reference` (default `GEOM_DRUGS`)
  - L247-258: `--upstream-n-samples` (default 1000)
- `tools/sweep_kanzi_n1000_paper_metrics.py` — SHA `5a18594bd401b4c085834bf8712562355063e8c7`
  - L51-53: `--limit` (default None)
  - L55-58: `--seed` (default 42)
  - L62-66: `--pb-engine` (default `uff`)
- `tools/sweep_kanzi_n1000_framework_paper_metrics.py` — SHA `139a3918bbd39fb387b3edd6364621c78eed1373`
  - L66-69: `--seed` (default 42)
  - L69-72: `--n-steps-decoder` (default 100)
  - L73-77: `--pb-engine` (default `uff`)
  - L78-80: `--limit` (default None)
- `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` — SHA `10b9beec33e32ae9a127eef9243c34c7baaa34a4`
  - L62: `--n-steps-decoder` (default 100)
  - L63: `--seed` (default 42)
  - L64: no `--pb-engine` (Wave 95.1.D inconsistency — inv_proj missed)
  - L65: `--limit` (default 1000)
- `tools/sweep_kanzi_n1000_diverse.py` — SHA `c7b788c89dc492300b030d04e9b685bb3dd1b615`
  - L107-109: `--input`
  - L111-113: `--ckpt`
  - L115: `--output-dir` (required)
  - L116-118: `--n-steps-decoder` (default 100)
  - L118-120: `--seed` (default 42)
  - L121-123: `--max-records` (default 1000)
- `tools/upstream_eval.py` — SHA `c3c40dfcbbaa6f6b6d628dbb7d86d21747ca69cb`
  - L431-439: Kanzi upstream-eval CLI (no `--seed`)
  - L774-779: FlowMol3 upstream-eval CLI (`--pb-workers` default 2)
- `tools/run_image_eval.py` — SHA `c2f910c762519363a3fa71ab199d5cfc0bd96b33`
  - `--device` (default `auto`)
  - `--fid-batch-size` (default 16)
  - `--arm` (default `framework`)
- `tools/run_rf_cifar_ablation.py` — SHA `e5c71c2d636479a915699142dfb741bfd6b113a6`
  - `--n-rounds` (default 5)
  - `--samples-per-round` (default 64)
  - `--nfe` (default 2)
  - `--weights-path`
- `tools/run_ablation.py` — SHA `33abfac1705f5b850d441d7d3dbad1e4a65b6314`
  - `--rounds`, `--quick`, `--num-steps`, `--seed`, `--out`

## Return

```json
{
  "audit_doc_path": "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave111-b-config-scattering-audit.md",
  "settings_audited": 12,
  "top_priority_settings": [
    "--seed",
    "--pb-engine",
    "--force-mode",
    "--nfe-budgets / --n-steps-decoder",
    "--max-records / --limit",
    "--composite-metric",
    "--upstream-n-samples",
    "--paper-metrics / --paper-reference",
    "--restart-min-nfe",
    "--n-molecules"
  ],
  "yaml_schema_sketch": "configs/runs/<model>_<purpose>.yaml flat key-value (PyYAML-safe_load); required: model, seed, nfe_budgets, max_records, force_mode, metric_mode; resolution order: CLI flag > YAML value > module-level default; loaded via tools.eval.config.load_run_profile(path) which validates schema and prints a [PROFILE] summary on load."
}
```
