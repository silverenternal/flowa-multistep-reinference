# Wave 111 Data-Linkage Fix Plan — Integrated

**SHA (HEAD):** `70501280ac0e9e197064d3b2b029bb0787289403`
**Date:** 2026-09-11
**Mode:** PLAN-ONLY (READ-ONLY synthesis; no commits in this doc)
**Inputs:**
- `docs/audit/wave111-a-sweep-driver-audit.md` (Reviewer A — sweep driver architecture)
- `docs/audit/wave111-b-config-scattering-audit.md` (Reviewer B — config scattering)
- `docs/audit/wave111-c-gpu-utilization-audit.md` (Reviewer C — GPU util root causes)

---

## 1. Executive summary

The 3 Wave 111.0 audits surface **2 distinct failure surfaces** in the sweep-driver fleet: (a) **GPU stays at 0% util during Kanzi sweeps** because `tools/_kanzi_sweep_runner.py:340` loads the DAE on CPU (Reviewer C, RC-1), and (b) **the same logical sweep can be triggered in 2-4 different invocations** with **~71 hardcoded CLI/shell/module constants** scattered across 11 drivers and 0 drivers reading a shared config (Reviewers A + B). This plan ships **9 atomic commits** totaling **~484 LOC**, anchored by 3 GPU-fix commits (RC-1 + RC-2B + RC-4, ~6 LOC) and 6 config-migration commits (~478 LOC) — preserving the **byte-stable** `D.4 = 33/33` and `mkdocs build --strict` gates and the existing CLI flag surface (additive migration only).

---

## 2. Per-finding summary

### 2.1 From Reviewer A — Sweep Driver Architecture (F-A001 .. F-A010)

| Finding ID | Severity | Description | Fix scope | LOC estimate | Commit priority |
|---|---|---|---|---|---|
| **F-A001** | HIGH | 3 Kanzi drivers default `--pb-engine "uff"`, but `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:55-67` omits the flag entirely (Wave 105 P0-B half-fix). | Add `--pb-engine` flag to driver 3, plumb through `_kanzi_sweep_runner.py`. | +6 LOC | **P1** |
| **F-A002** | HIGH | `--limit` defaults differ across 4 Kanzi drivers: `None` / `None` / `1000` / `1000`. | Default every Kanzi driver to `--limit 1000`; gate via config profile. | +4 LOC | **P1** |
| **F-A003** | HIGH | `nfe_steps=100` hardcoded at `sweep_kanzi_n1000_paper_metrics.py:84` (Python literal); the other 3 Kanzi drivers expose it as `--n-steps-decoder`. | Add `--n-steps-decoder` flag to driver 1. | +2 LOC | **P1** |
| **F-A004** | HIGH | `KanziAdapter` constructor settings (`force_mode`, `num_steps=50`, `solver="euler"`) hardcoded at `_kanzi_sweep_runner.py:362-364`. | Expose `--adapter-force-mode` / `--adapter-num-steps` / `--adapter-solver` on all Kanzi sweep drivers. | +12 LOC | **P1** |
| **F-A005** | HIGH | Drivers 1, 2, 3 + `upstream_eval.py:441` never move DAE to CUDA → GPU 0% util (matches Reviewer C RC-1). | Apply `dae.to("cuda")` in shared runner + adapter (covered by F-C001 below). | (overlap w/ F-C001) | **P0** |
| **F-A006** | MED | `lineageflow_n1000_gpu_sweep.sh` has 11 hardcoded shell constants (NFE/SEEDS/N_SAMPLES/CUDA_VISIBLE_DEVICES/VENV_PY/timeout). | Replace shell hardcodes with `--config <yaml>`; shell wrapper becomes thin launcher. | +20 LOC (config-aware shell) | **P2** |
| **F-A007** | MED | `wave87_n1000_sweep.py` has 10 module-level constants, 0 argparse flags → every re-run requires code edit. | Convert module constants to argparse + `--config` loader. | +30 LOC | **P2** |
| **F-A008** | LOW | 3 distinct output JSON naming conventions across Kanzi drivers. | Standardize via config profile (`output_filename` key). | +6 LOC | **P2** |
| **F-A009** | CRITICAL | **No driver reads a config file** — all 11 drivers are CLI/shell/constant surfaces. | Build `tools.eval.config` module + `--config` flag (F-B001 below). | (overlap w/ F-B001) | **P0** |
| **F-A010** | LOW | Canonical driver has 17 flags but Kanzi/LineageFlow wrappers don't use it. | Document + provide a "use canonical driver" example per profile (in `docs/configs.md`). | 0 LOC (doc only) | **P2** |

### 2.2 From Reviewer B — Configuration Scattering (F-B001 .. F-B008)

| Finding ID | Severity | Description | Fix scope | LOC estimate | Commit priority |
|---|---|---|---|---|---|
| **F-B001** | HIGH | 12 logical settings appear as `--flag` arguments across 6+ drivers with **inconsistent defaults** (e.g. `--seed` defaults to `42` in 5 places, `0/None` in 2, `required-CSV` in 1). | Build `tools/eval/config.py` schema + `load_run_profile(path)` helper; add `--config` to all drivers. | +150 LOC (new module) | **P0** |
| **F-B002** | HIGH | `--pb-engine` flip inconsistency (Wave 95.1.D missed driver 3). | Per-profile default (`pb_engine: uff` / `pb_engine: xtb`) becomes the single source of truth. | (overlap w/ F-A001) | **P1** |
| **F-B003** | HIGH | `--force-mode` default `synthetic` in `cli.py:64-74` is wrong for N=1000 real-mode (Wave 50.A bug chain). | Profile sets `force_mode: real`; CLI default stays `synthetic` (backward compat). | (overlap w/ F-B001) | **P1** |
| **F-B004** | HIGH | `--nfe-budgets` defaults differ per model (`100` Kanzi / `250` FlowMol3 / `2` CIFAR-10 RF). | Profile holds the per-model NFE list; CLI `required` becomes optional when `--config` set. | (overlap w/ F-B001) | **P1** |
| **F-B005** | MED | `--max-records` defaults differ across 4 drivers (`None` / `1000` / `1000` / `0=all`). | Profile holds `max_records: 1000`. | (overlap w/ F-B001) | **P1** |
| **F-B006** | MED | `--composite-metric` only on `eval/cli.py`; legacy sweep drivers can't re-run Wave 47 sweep with `composite_metric=real`. | Profile exposes `composite_metric: real`. | (overlap w/ F-B001) | **P2** |
| **F-B007** | MED | `--upstream-n-samples` typo (`10000`) would burn 15-40h silently. | Profile holds `upstream_n_samples: 1000`; CLI default stays explicit. | (overlap w/ F-B001) | **P2** |
| **F-B008** | LOW | `--paper-metrics` / `--paper-reference` / `--restart-min-nfe` / `--n-molecules` only on `eval/cli.py`. | Profile holds all 4; backward-compat CLI flags preserved. | (overlap w/ F-B001) | **P2** |

### 2.3 From Reviewer C — GPU Utilization Root Causes (F-C001 .. F-C004)

| Finding ID | Severity | Description | Fix scope | LOC estimate | Commit priority |
|---|---|---|---|---|---|
| **F-C001 / RC-1** | **CRITICAL** | `tools/_kanzi_sweep_runner.py:340` loads DAE on CPU; bridge auto-coerces → all 100 decode steps on CPU `nn.Linear` (>500h wall at N=1000). | Add `if torch.cuda.is_available(): dae = dae.to("cuda")` after `.eval()`. | +2 LOC | **P0** |
| **F-C002 / RC-2 (option B)** | **HIGH** | `_KanziDAEShim.forward()` at `adaptive_reflow/adapters/kanzi.py:1124-1138` returns `torch.zeros_like(x)` (Wave 110.B "Bug 2 fix" placeholder). Framework arm is a no-op regardless of CUDA. | Replace `return torch.zeros_like(x)` with `raise NotImplementedError("Wave 110.B placeholder: backbone-coord migration pending; framework arm is currently a no-op")`. (Option A = real fix is **out of scope**, tracked under Wave 110.D follow-up.) | +1 LOC | **P0** |
| **F-C003 / RC-3** | **CRITICAL** (downstream) | `kanzi_latent_to_coord.py:148-154` derives `device = next(decoder.parameters()).device` → inherits CPU from RC-1. | **0 LOC** — auto-fixed when F-C001 lands. | 0 LOC | (auto) |
| **F-C004 / RC-4** | LOW | `_torch_velocity_field()` at `adaptive_reflow/adapters/kanzi.py:1046-1057` constructs tensors without `device=`. | Pass `device = next(model.parameters()).device` to 3 `torch.as_tensor` calls. | +3 LOC | **P1** |

**Cross-reference matrix:**
- F-A005 ≡ F-C001 (GPU util root cause)
- F-A009 ≡ F-B001 (no config file → build the config module)
- F-A001 ≡ F-B002 (`--pb-engine` half-fix)

---

## 3. Commit plan (atomic commits, ordered by dependency)

### Commit C-1: `fix(kanzi): move DAE to CUDA in shared runner (RC-1)`

- **File(s) to modify:** `tools/_kanzi_sweep_runner.py`
- **Per-file LOC delta:** +2
- **Acceptance criteria:**
  1. `next(dae.parameters()).device` returns `cuda:0` after runner init when CUDA is available (single-shot smoke).
  2. `nvidia-smi --query-gpu=utilization.gpu` shows > 40% during a 10-record smoke sweep.
  3. `pytest tests/ -k d4 -q` → 72/72 PASS (byte-stable).
  4. `pytest tests/test_tools/ -v` → green.
  5. `mkdocs build --strict` → EXIT=0.
- **Risk level:** LOW — identical pattern to already-working `sweep_kanzi_n1000_diverse.py:136`.
- **Depends on:** none (independent; can land first).

### Commit C-2: `fix(adapter): fail-fast in _KanziDAEShim.forward (RC-2 option B)`

- **File(s) to modify:** `adaptive_reflow/adapters/kanzi.py`
- **Per-file LOC delta:** +1 (replace `return torch.zeros_like(x)` with `raise NotImplementedError(...)`)
- **Acceptance criteria:**
  1. Calling `_KanziDAEShim.forward(...)` outside of synthetic mode raises `NotImplementedError` with the documented message.
  2. The existing synthetic-mode code path (`self._synthetic_weights is not None`) is **not** affected — framework synthetic sweep still runs.
  3. `pytest tests/ -k d4 -q` → 72/72 PASS.
  4. `pytest tests/test_tools/ -v` → green (no test exercises the shim in framework arm).
  5. `mkdocs build --strict` → EXIT=0.
- **Risk level:** LOW — fail-fast is the documented Wave 110.B intent.
- **Depends on:** none (independent).

### Commit C-3: `fix(adapter): pass device= to torch.as_tensor in _torch_velocity_field (RC-4)`

- **File(s) to modify:** `adaptive_reflow/adapters/kanzi.py`
- **Per-file LOC delta:** +3
- **Acceptance criteria:**
  1. `device = next(model.parameters()).device` is computed once at the top of `_torch_velocity_field`.
  2. All 3 `torch.as_tensor(...)` calls carry `device=device`.
  3. After C-1 lands, the input tensor lands on CUDA when the model is on CUDA.
  4. `pytest tests/ -k d4 -q` → 72/72 PASS.
  5. `mkdocs build --strict` → EXIT=0.
- **Risk level:** LOW — pure device-pass-through, no numerical change.
- **Depends on:** C-1 (DAE must be on CUDA for the device= path to matter).

### Commit C-4: `feat(config): add tools.eval.config module + --config flag on canonical cli`

- **File(s) to modify:** `tools/eval/config.py` (new), `tools/eval/cli.py`
- **Per-file LOC delta:** config.py +140, cli.py +10 (--config flag + load_run_profile call)
- **Acceptance criteria:**
  1. `tools.eval.config.load_run_profile(path)` returns a validated dict; raises on missing required keys (`model`, `seed`, `nfe_budgets`, `max_records`, `force_mode`, `metric_mode`); raises on unknown keys.
  2. `tools/eval/cli.py` accepts `--config <yaml>` and **overrides nothing by default** (resolution order: CLI > YAML > module default).
  3. Print summary on load: `[PROFILE] <path> v=<date> seed=<n> force_mode=<m> nfe=<list> N=<n>`.
  4. All 17 existing CLI flags still work without `--config` (backward compat).
  5. `pytest tests/test_tools/ -v` → green; `pytest tests/ -k d4 -q` → 33/33; `mkdocs build --strict` → EXIT=0.
- **Risk level:** MED — touches canonical driver; new module is additive but flag plumbing is in the hot path.
- **Depends on:** C-1 (so profile can gate `device` if desired), C-2 (so framework arm fail-fast is observable via profile).

### Commit C-5: `feat(configs): ship 3 initial profiles (Kanzi baseline, Kanzi framework, FlowMol3 paper)`

- **File(s) to modify:** `configs/runs/kanzi_n1000_baseline.yaml`, `configs/runs/kanzi_n1000_framework.yaml`, `configs/runs/flowmol3_n1000_paper.yaml` (3 new files)
- **Per-file LOC delta:** ~40 LOC each (~120 total)
- **Acceptance criteria:**
  1. Each YAML validates under `load_run_profile()` (no missing required keys).
  2. `kanzi_n1000_baseline.yaml` reproduces Wave 109.A Kanzi N=1000 baseline arm byte-stable output (when loaded via `--config`).
  3. `kanzi_n1000_framework.yaml` reproduces Wave 110.C Kanzi N=1000 framework arm (the PARTIAL one) — at least up to the first cell's `[CELL]` print.
  4. `flowmol3_n1000_paper.yaml` reproduces Wave 87 FlowMol3 N=1000 paper-metric invocation (PB-xtb pipeline).
  5. Each YAML carries a top-level `# Profile version: 2026-09-11 (Wave 111)` comment.
- **Risk level:** LOW — additive files; existing CLI invocations unchanged.
- **Depends on:** C-4.

### Commit C-6: `refactor(sweep): migrate Kanzi drivers 1-3 to --config + backfill missing flags`

- **File(s) to modify:** `tools/sweep_kanzi_n1000_paper_metrics.py`, `tools/sweep_kanzi_n1000_framework_paper_metrics.py`, `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`
- **Per-file LOC delta:** +12 / +12 / +12 (adds `--config`, `--adapter-force-mode`, `--adapter-num-steps`, `--adapter-solver`, fixes F-A001 in driver 3, fixes F-A003 in driver 1, fixes F-A002/F-A004 across all)
- **Acceptance criteria:**
  1. All 3 drivers accept `--config <yaml>` and print `[PROFILE]` summary on load.
  2. Driver 3 (inv_proj) exposes `--pb-engine` (closes Wave 105 P0-B).
  3. Driver 1 (baseline) exposes `--n-steps-decoder` instead of hardcoded `nfe_steps=100`.
  4. Default `force_mode` flows from runner → profile (closes F-A004).
  5. Backward compat: omitting `--config` reproduces Wave 110.C PARTIAL output exactly (CLI defaults unchanged). `pytest tests/ -k d4 -q` → 72/72 PASS; `mkdocs build --strict` → EXIT=0.
- **Risk level:** MED — touches 3 sweep drivers; default-value alignment is error-prone.
- **Depends on:** C-4, C-5.

### Commit C-7: `refactor(sweep): migrate remaining drivers (diverse, wave87, lineageflow shell, upstream_eval) to --config`

- **File(s) to modify:** `tools/sweep_kanzi_n1000_diverse.py`, `tools/wave87_n1000_sweep.py`, `tools/lineageflow_n1000_gpu_sweep.sh`, `tools/upstream_eval.py`
- **Per-file LOC delta:** +10 / +30 / +20 / +10
- **Acceptance criteria:**
  1. `sweep_kanzi_n1000_diverse.py` accepts `--config` (replaces `nfe_steps=50`, `max_records=1000`, `seed=42` hardcodes).
  2. `wave87_n1000_sweep.py` converts module constants to argparse + `--config` (10 module-level constants become flags).
  3. `lineageflow_n1000_gpu_sweep.sh` shell hardcodes (`NFE`, `SEEDS`, `N_SAMPLES`, `VENV_PY`, `timeout`) move to a profile; shell becomes thin launcher.
  4. `upstream_eval.py` (3 argparse blocks) all accept `--config` or read from `--profile <yaml>` envvar.
  5. `pytest tests/ -k d4 -q` → 72/72 PASS; `pytest tests/test_tools/ -v` → green; `mkdocs build --strict` → EXIT=0.
- **Risk level:** MED — touches shell + 3 Python drivers; wave87 module-constant removal is breaking unless guarded.
- **Depends on:** C-4, C-6.

### Commit C-8: `docs(configs): add configs.md index of run profiles`

- **File(s) to modify:** `docs/configs.md` (new), `mkdocs.yml` (+2 lines for nav entry)
- **Per-file LOC delta:** docs/configs.md +40, mkdocs.yml +2
- **Acceptance criteria:**
  1. `docs/configs.md` lists all profiles in `configs/runs/` with one-line summaries.
  2. Each profile entry links to its source YAML and the audit docs that motivated it.
  3. `mkdocs build --strict` → EXIT=0 (nav entry valid, no broken links).
  4. `pytest tests/ -k d4 -q` → 72/72 PASS (doc-only change).
  5. Manual: opening `docs/configs.md` in mkdocs preview shows all 3 initial profiles.
- **Risk level:** LOW — doc + nav entry; no source code touched.
- **Depends on:** C-5 (needs the 3 profiles to exist to index).

### Commit C-9: `docs(audit): record Wave 111 data-linkage closure`

- **File(s) to modify:** `docs/audit/wave111-data-linkage-closure.md` (new)
- **Per-file LOC delta:** +60
- **Acceptance criteria:**
  1. The closure doc cites each of C-1..C-8 with their SHAs.
  2. The closure doc reproduces the per-commit verification log (D.4 33/33 + mkdocs EXIT=0 + GPU util > 40%).
  3. The closure doc maps every F-A/B/C-### finding to its closing commit.
  4. `mkdocs build --strict` → EXIT=0.
  5. `pytest tests/ -k d4 -q` → 72/72 PASS.
- **Risk level:** LOW — audit-only doc, no source.
- **Depends on:** C-1..C-8 (must land first to cite SHAs).

---

## 4. YAML config schema (concrete example)

### 4.1 `configs/runs/kanzi_n1000_baseline.yaml`

```yaml
# configs/runs/kanzi_n1000_baseline.yaml
# Purpose: Wave 109.A-equivalent Kanzi N=1000 baseline-arm paper-metric sweep.
# Profile version: 2026-09-11 (Wave 111). Authoritative defaults — any CLI
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

# --- §7. Adapter-level knobs (Wave 111 F-A004 closure) ---
adapter_force_mode: torch               # _kanzi_sweep_runner KanziAdapter constructor
adapter_num_steps: 50                   # framework ODE num_steps
adapter_solver: euler                   # euler|heun (heun not yet exposed)

# --- §8. Output naming (Wave 111 F-A008 closure) ---
output_filename: kanzi_n1000_paper_metrics.json
```

### 4.2 `configs/runs/kanzi_n1000_framework.yaml`

```yaml
# configs/runs/kanzi_n1000_framework.yaml
# Purpose: Wave 110.C-equivalent Kanzi N=1000 framework-arm paper-metric sweep
# (σ=1e-3 synthetic endpoint via _synthesize_x_final_synthetic).
# Profile version: 2026-09-11 (Wave 111).
model: kanzi

seed: 42
force_mode: real                        # Wave 110.B Bug 2 fix in effect
metric_mode: real                       # synthetic-only is unsafe at N=1000
composite_metric: auto

nfe_budgets: [100]
max_records: 1000                       # F-A002 closure: explicit cap
n_rounds: 3
n_molecules: 1

pb_engine: uff                          # F-A001 / F-B002 closure: explicit
restart_min_nfe: 20

paper_metrics: true                     # Wave 110.C framework arm
paper_reference: GEOM_DRUGS
kanzi_upstream_eval: true
kanzi_framework_paper_metrics: true
upstream_n_samples: 1000

adapter_force_mode: torch               # F-A004 closure
adapter_num_steps: 50
adapter_solver: euler

output_filename: kanzi_n1000_framework_paper_metrics.json
```

### 4.3 `configs/runs/flowmol3_n1000_paper.yaml`

```yaml
# configs/runs/flowmol3_n1000_paper.yaml
# Purpose: Wave 87-equivalent FlowMol3 N=1000 PB-xtb paper-metric sweep.
# Profile version: 2026-09-11 (Wave 111).
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

# Adapter-level knobs not applicable to FlowMol3 (uses upstream subprocess).
output_filename: flowmol3_n1000_paper_wave87_q4_2026.json
```

---

## 5. Hard rules

1. **NO push.** Every commit lands on the working tree; user-gated push.
2. **Backward compat:** existing CLI flags must still work without `--config`. Resolution order: **CLI flag > YAML value > module-level default**. Profiles are the new default surface; CLI flags are the override surface (not the other way around).
3. **`D.4 = 33/33`** must remain PASS throughout (verified by `pytest tests/ -k d4 -q` after every commit).
4. **`mkdocs build --strict`** must remain EXIT=0 throughout (verified by the same protocol).
5. **No source deletion.** Additive migration only. CLI flags stay; module constants stay (just become flag-sourced). Deprecation, if any, is gate-behind-`DeprecationWarning` for 1 wave before removal.
6. **GPU util verification** (per C-1): a 10-record smoke sweep must show non-zero `nvidia-smi` util (target > 40% average) on the active CUDA device.

---

## 6. Verification protocol per commit

For every commit C-1..C-9, the agent MUST run and report results:

```bash
# 1. D.4 byte-stable regression (must remain 33/33)
pytest tests/ -k d4 -q

# 2. Tools tests (must remain green)
pytest tests/test_tools/ -v

# 3. mkdocs strict build (must remain EXIT=0)
mkdocs build --strict

# 4. GPU smoke (only for C-1, C-2, C-3, C-6, C-7 — must show non-zero util)
# Terminal A:
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1
# Terminal B (in .venvs/kanzi_venv/bin/python):
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --output-dir /tmp/wave111-verify --limit 10
# Expected: nvidia-smi util > 40% during sweep; total wall < 2 min
```

Failure of any one gate → commit is blocked; root-cause the regression before retry.

---

## 7. Estimated wall-clock

| Commit | Description | Estimate |
|---|---|---|
| C-1 | DAE → CUDA (RC-1) | 0.1 h |
| C-2 | Shim fail-fast (RC-2B) | 0.1 h |
| C-3 | device= in _torch_velocity_field (RC-4) | 0.2 h |
| C-4 | `tools.eval.config` module + `--config` on canonical cli | 4.0 h |
| C-5 | 3 initial profiles (YAML authoring) | 0.5 h |
| C-6 | Migrate Kanzi drivers 1-3 (3 drivers × 1.0 h) | 3.0 h |
| C-7 | Migrate diverse + wave87 + shell + upstream_eval | 4.0 h |
| C-8 | `docs/configs.md` index | 0.3 h |
| C-9 | `wave111-data-linkage-closure.md` | 0.5 h |
| **Total** | **9 commits** | **~12.7 h** |

Wall-clock assumes single-agent serial execution. With 2 parallel agents (e.g. one on GPU fixes C-1..C-3 + one on config infra C-4..C-9), **critical path is ~8 h**.

---

## 8. Risk table

| Commit | Risk | Rationale |
|---|---|---|
| C-1 | LOW | Identical to already-working `sweep_kanzi_n1000_diverse.py:136`; DAE stays on CPU when CUDA absent. |
| C-2 | LOW | Fail-fast replaces a documented Wave 110.B placeholder; no synthetic-mode caller affected. |
| C-3 | LOW | Pure device-pass-through; no numerical change. |
| C-4 | MED | Touches canonical driver; new module is additive but `--config` plumbing is in the hot path. Mitigated by backward-compat guarantee (CLI > YAML > default). |
| C-5 | LOW | New YAML files; existing CLI invocations unchanged. |
| C-6 | MED | 3 sweep drivers + 1 shared runner; default-value alignment across `--pb-engine` / `--adapter-*` is error-prone. Mitigated by per-driver smoke sweep. |
| C-7 | MED | Shell wrapper + 3 Python drivers; `wave87_n1000_sweep.py` module-constant removal is breaking unless guarded with `if config is None: keep defaults` shim. |
| C-8 | LOW | Doc + mkdocs nav entry; no source touched. |
| C-9 | LOW | Audit-only doc; cites SHAs from C-1..C-8 (which must exist first). |

---

## 9. Cross-finding resolution map

| Finding | Resolved by |
|---|---|
| F-A001 (driver 3 missing `--pb-engine`) | C-6 |
| F-A002 (`--limit` defaults differ) | C-5 (profile default) + C-6 (driver-level fallback) |
| F-A003 (driver 1 hardcoded `nfe_steps=100`) | C-6 |
| F-A004 (`KanziAdapter` constructor hardcoded) | C-6 (exposes `--adapter-*`) + C-5 (profile defaults) |
| F-A005 (no `dae.to("cuda")` except driver 4) | C-1 |
| F-A006 (shell hardcodes) | C-7 |
| F-A007 (wave87 module constants) | C-7 |
| F-A008 (output JSON naming) | C-5 (`output_filename` key) + C-6 (driver reads it) |
| F-A009 (no config file) | C-4 |
| F-A010 (canonical driver unused by wrappers) | C-8 (docs) |
| F-B001 (no YAML loader) | C-4 |
| F-B002 (`--pb-engine` flip inconsistency) | C-5 (profile default) + C-6 |
| F-B003 (`--force-mode` default `synthetic` unsafe at N=1000) | C-5 (profile says `real`) + C-6 (CLI default preserved) |
| F-B004 (`--nfe-budgets` per-model defaults) | C-5 (profile) + C-6 |
| F-B005 (`--max-records` defaults) | C-5 + C-6 |
| F-B006 (`--composite-metric` only on cli) | C-5 + C-6 |
| F-B007 (`--upstream-n-samples` typo risk) | C-5 + C-6 |
| F-B008 (`--paper-metrics` / `--paper-reference` / `--restart-min-nfe` / `--n-molecules`) | C-5 + C-6 |
| F-C001 / RC-1 (DAE on CPU) | C-1 |
| F-C002 / RC-2 (shim returns zeros) | C-2 (Option B fail-fast; real fix tracked under Wave 110.D follow-up) |
| F-C003 / RC-3 (bridge auto-coerces to CPU) | Auto-fixed by C-1 (0 LOC) |
| F-C004 / RC-4 (`_torch_velocity_field` device=) | C-3 |

**Total findings:** 22 (F-A001..F-A010, F-B001..F-B008, F-C001..F-C004).
**Resolved by plan:** 22/22 (100%).

---

## 10. Out of scope (explicit non-goals for Wave 111)

- **Real RC-2 fix** (Option A: migrate `_KanziDAEShim.forward()` to actually call `DAE.encode` + `DAE.net`, ~15-20 LOC) — tracked under **Wave 110.D follow-up** (backbone-coord space migration). Wave 111 ships the fail-fast so the placeholder is visible, not the architectural fix.
- **Drop CLI flags** — the existing CLI flag surface is preserved (additive migration only); a future wave may add `DeprecationWarning` and remove, but not Wave 111.
- **Re-run Wave 110.C sweeps** — Wave 111 fixes the *config* surface and the *GPU util*; the next sweep wave (Wave 112?) re-runs with `--config`.
- **New model adapters** — no new `tools/*.py` driver; existing drivers only.

---

## Citations

All SHAs from the current HEAD `70501280ac0e9e197064d3b2b029bb0787289403`:

- `docs/audit/wave111-a-sweep-driver-audit.md` (Reviewer A — sweep driver architecture)
  - §5 Finding 1-10 — `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py:55-67` (`--pb-engine` missing)
  - §5 Finding 2-9 — `--limit` defaults scattered
  - §5 Finding 3 — `sweep_kanzi_n1000_paper_metrics.py:84` (`nfe_steps=100` hardcode)
  - §5 Finding 4 — `_kanzi_sweep_runner.py:362-364` (adapter constructor hardcode)
  - §5 Finding 5 — `sweep_kanzi_n1000_diverse.py:136` (only driver with `dae.to("cuda")`)
  - §5 Finding 6 — `lineageflow_n1000_gpu_sweep.sh:45,47,49-51,67` (shell hardcodes)
  - §5 Finding 7 — `wave87_n1000_sweep.py:75-82` (module constants)
  - §5 Finding 8 — output JSON naming convention scattered
  - §5 Finding 9 — no driver reads a config file
  - §5 Finding 10 — canonical driver unused by wrappers
- `docs/audit/wave111-b-config-scattering-audit.md` (Reviewer B — config scattering)
  - §1 Settings Table — 12 settings audited across 6+ drivers
  - §2 Proposed YAML schema — `configs/runs/<model>_<purpose>.yaml` flat key-value
  - §3 Top-10 priority settings — `--seed`, `--pb-engine`, `--force-mode`, `--nfe-budgets`, `--max-records`, `--composite-metric`, `--upstream-n-samples`, `--paper-metrics`, `--restart-min-nfe`, `--n-molecules`
  - §4 Design notes — backward-compat guarantee, resolution order, `tools.eval.config.load_run_profile(path)` helper
- `docs/audit/wave111-c-gpu-utilization-audit.md` (Reviewer C — GPU util)
  - §0 TL;DR — 4 root causes (RC-1, RC-2, RC-3, RC-4) + 6 LOC safe fix total
  - §1 Call chain trace — baseline arm + framework arm
  - §2 Root causes identified — RC-1 `_kanzi_sweep_runner.py:340`, RC-2 `adaptive_reflow/adapters/kanzi.py:1124-1138`, RC-3 `kanzi_latent_to_coord.py:148-154`, RC-4 `adaptive_reflow/adapters/kanzi.py:1046-1057`
  - §3 Per-cause fix plan — Option A vs Option B for RC-2
  - §4 GPU verification protocol — nvidia-smi + smoke sweep
  - §5 User-facing message — draft for the user
  - §6 Cross-references — Wave 99.E precedent, Wave 105 P1-A regression, Wave 110.B Bug 2 placeholder
- `4f7e3c7` — Wave 110.B (Bug 2 fix; force_mode=real in KanziAdapter construction)
- `f9df1f6` — Wave 110.C (PARTIAL re-run; baseline arm only)
- `7050128` — Wave 110.D (HEAD; final synthesis)

---

**END OF PLAN — READ-ONLY — NO COMMITS**


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.
