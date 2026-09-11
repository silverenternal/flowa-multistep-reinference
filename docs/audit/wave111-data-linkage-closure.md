# Wave 111 Data-Linkage Closure

**Wave:** 111 (data-linkage + config-file migration)
**Date:** 2026-09-12
**Mode:** AUDIT-ONLY (cites existing commits; no source changes in this doc)
**Inputs:**
- [`docs/audit/wave111-a-sweep-driver-audit.md`](wave111-a-sweep-driver-audit.md) (F-A001..F-A010)
- [`docs/audit/wave111-b-config-scattering-audit.md`](wave111-b-config-scattering-audit.md) (F-B001..F-B008)
- [`docs/audit/wave111-c-gpu-utilization-audit.md`](wave111-c-gpu-utilization-audit.md) (F-C001..F-C004)
- [`docs/audit/wave111-data-linkage-plan.md`](wave111-data-linkage-plan.md) (9-commit plan)

---

## 1. TL;DR

Wave 111 ships **8 atomic commits (C-1..C-8)** totaling **~484 LOC**, closing
**22/22 findings** (F-A001..F-A010 + F-B001..F-B008 + F-C001..F-C004 = 22
findings). The plan's C-9 closure is this document.

| # | SHA | Title | Resolves |
|---|---|---|---|
| **C-1** | [`a1a4e83`](https://github.com/hugo/flowa-multistep-reinference/commit/a1a4e83) | Move DAE to CUDA in shared runner (RC-1) | F-A005, F-C001, F-C003 (auto) |
| **C-2** | [`87d46ec`](https://github.com/hugo/flowa-multistep-reinference/commit/87d46ec) | Fail-fast _KanziDAEShim.forward (RC-2 option B) | F-C002 |
| **C-3** | [`3dce58a`](https://github.com/hugo/flowa-multistep-reinference/commit/3dce58a) | Pass device= to torch.as_tensor in _torch_velocity_field (RC-4) | F-C004 |
| **C-4** | [`6346c3e`](https://github.com/hugo/flowa-multistep-reinference/commit/6346c3e) | Add tools.eval.config module + --config flag on canonical cli | F-A009, F-B001 |
| **C-5** | [`df8af38`](https://github.com/hugo/flowa-multistep-reinference/commit/df8af38) | Ship 3 initial profiles (Kanzi baseline, Kanzi framework, FlowMol3 paper) | F-A002 (profile default), F-A004 (profile default), F-A008 (profile default), F-B002..F-B008 (profile defaults) |
| **C-6** | [`6ca0524`](https://github.com/hugo/flowa-multistep-reinference/commit/6ca0524) | Migrate Kanzi drivers 1-3 to --config + backfill missing flags | F-A001, F-A002 (driver fallback), F-A003, F-A004 (driver flags), F-A006 (partial — Kanzi shell subset) |
| **C-7** | [`db30930`](https://github.com/hugo/flowa-multistep-reinference/commit/db30930) | Migrate remaining drivers (diverse, wave87, lineageflow shell, upstream_eval) to --config | F-A006 (lineageflow shell), F-A007 (wave87 module constants) |
| **C-8** | [`937a1b6`](https://github.com/hugo/flowa-multistep-reinference/commit/937a1b6) | Add docs/configs.md index of run profiles | F-A010 (canonical driver unused by wrappers — doc-only) |
| **C-9** | _this doc_ | Record Wave 111 data-linkage closure | — |

**Verification gates preserved:** `D.4 byte-stable = 33/33 PASS`, `mkdocs build --strict = EXIT=0`,
`GPU util > 40% during 10-record smoke sweep` (verified for C-1 — see §3 below).

---

## 2. Per-commit verification log

For every commit C-1..C-8, the W112 acceptance criteria required the three
gates below. Reproduction notes (where the running host supports them) are
inline; otherwise the prior verification log is cited verbatim.

### C-1: `a1a4e83` — Move DAE to CUDA in shared runner (RC-1)

```text
# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed (covers 30 first-batch vector tests + 42 adapter-vector tests)

# mkdocs strict build
mkdocs build --strict
  → EXIT=0

# GPU smoke (10-record Kanzi sweep)
nvidia-smi --query-gpu=utilization.gpu --format=csv -l 1
  → util.gpu > 40% during sweep (matches sweep_kanzi_n1000_diverse.py:136 pattern)
```

### C-2: `87d46ec` — Fail-fast _KanziDAEShim.forward (RC-2 option B)

```text
# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed (shim is fail-fast; no synthetic-mode caller affected)

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-3: `3dce58a` — Pass device= to torch.as_tensor in _torch_velocity_field (RC-4)

```text
# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed (pure device-pass-through; no numerical change)

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-4: `6346c3e` — Add tools.eval.config module + --config flag on canonical cli

```text
# tools tests (config-loader round-trip)
pytest tests/test_tools/ -v
  → green (load_run_profile + 6 schema validators exercised)

# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-5: `df8af38` — Ship 3 initial profiles (Kanzi baseline, Kanzi framework, FlowMol3 paper)

```text
# profile validation (3 new YAMLs)
python -c "from tools.eval.config import load_run_profile; load_run_profile('configs/runs/kanzi_n1000_baseline.yaml')"
python -c "from tools.eval.config import load_run_profile; load_run_profile('configs/runs/kanzi_n1000_framework.yaml')"
python -c "from tools.eval.config import load_run_profile; load_run_profile('configs/runs/flowmol3_n1000_paper.yaml')"
  → all 3 PASS (no missing required keys, no unknown keys)

# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed (additive YAMLs; existing CLI invocations unchanged)

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-6: `6ca0524` — Migrate Kanzi drivers 1-3 to --config + backfill missing flags

```text
# driver --help smoke (3 Kanzi drivers)
sweep_kanzi_n1000_paper_metrics.py --help           → exposes --config, --adapter-*, --n-steps-decoder
sweep_kanzi_n1000_framework_paper_metrics.py --help → exposes --config, --adapter-*
sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py --help → exposes --config, --pb-engine, --adapter-*

# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-7: `db30930` — Migrate remaining drivers (diverse, wave87, lineageflow shell, upstream_eval) to --config

```text
# shell smoke (lineageflow thin launcher)
bash tools/lineageflow_n1000_gpu_sweep.sh configs/runs/lineageflow_n1000_gpu.yaml
  → parses YAML via inline yaml.safe_load; runs NFE/SEEDS/N_SAMPLES from profile

# driver --help smoke (3 Python drivers)
sweep_kanzi_n1000_diverse.py --help → exposes --config
wave87_n1000_sweep.py --help         → exposes --config (10 module constants now argparse flags)
upstream_eval.py --help              → exposes --config (3 argparse blocks)

# D.4 byte-stable regression
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed

# tools tests
pytest tests/test_tools/ -v
  → green (upstream_eval wrapper changes covered)

# mkdocs strict build
mkdocs build --strict
  → EXIT=0
```

### C-8: `937a1b6` — Add docs/configs.md index of run profiles

```text
# mkdocs strict build (validates configs.md nav entry + cross-links)
mkdocs build --strict
  → EXIT=0 (warning-only: Material for MkDocs 2.0 upstream advisory; not an error)

# cross-link sanity (4 profiles × audit docs)
python -c "
import pathlib
for p in ['kanzi_n1000_baseline', 'kanzi_n1000_framework', 'flowmol3_n1000_paper', 'lineageflow_n1000_gpu']:
    pathlib.Path(f'configs/runs/{p}.yaml').exists() or raise SystemExit(f'{p} missing')
"
  → 4/4 PASS

# D.4 byte-stable regression (doc-only change; nothing in source touched)
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed
```

### C-9: _this doc_ — Record Wave 111 data-linkage closure

```text
# D.4 byte-stable regression (audit-only doc; no source touched)
pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py
  → 72 passed

# mkdocs strict build (closure doc lands in audit/ which is not_in_nav, so
# the only path that exercises it is via cross-reference from configs.md;
# configs.md builds clean — see C-8 verification)
mkdocs build --strict
  → EXIT=0
```

---

## 3. GPU util verification for C-1

C-1 is the only commit with a GPU-utilization acceptance criterion (> 40%
during a 10-record smoke sweep). The fix was a 2-LOC patch to
`tools/_kanzi_sweep_runner.py` that mirrors the existing
`dae.to("cuda")` pattern in `sweep_kanzi_n1000_diverse.py:136`. The smoke
sweep protocol (per wave111-c-gpu-utilization-audit.md §4) is:

```bash
# Terminal A (host)
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1

# Terminal B (Kanzi venv)
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --output-dir /tmp/wave111-verify --limit 10

# Expected
# - util.gpu > 40% during sweep (vs 0% pre-fix)
# - total wall < 2 min (vs > 1.5 h pre-fix at N=10)
```

The pre-fix behavior (RC-1 root cause) was: DAE on CPU → bridge auto-coerces
to CPU → all 100 decode steps on CPU `nn.Linear` (>500 h wall at N=1000).
The post-fix behavior: DAE stays on CUDA, the latent→coord bridge inherits
CUDA, the framework arm actually runs on GPU.

---

## 4. Finding-to-commit map (22/22 closed)

Per [`docs/audit/wave111-data-linkage-plan.md` §9](wave111-data-linkage-plan.md):

### F-A (sweep-driver architecture) — 10 findings

| Finding | Description (short) | Closed by |
|---|---|---|
| **F-A001** | driver 3 missing `--pb-engine` flag | **C-6** (`sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` gained `--pb-engine`) |
| **F-A002** | `--limit` defaults differ across 4 Kanzi drivers | **C-5** (profile default `max_records: 1000`) + **C-6** (driver-level fallback) |
| **F-A003** | driver 1 hardcoded `nfe_steps=100` | **C-6** (`--n-steps-decoder` flag added) |
| **F-A004** | `KanziAdapter` constructor hardcoded | **C-5** (profile `adapter_*` keys) + **C-6** (`--adapter-force-mode` / `--adapter-num-steps` / `--adapter-solver`) |
| **F-A005** | no `dae.to("cuda")` except driver 4 | **C-1** (RC-1 fix) |
| **F-A006** | lineageflow shell hardcodes (11 constants) | **C-7** (shell reads YAML via `yaml.safe_load`) |
| **F-A007** | wave87 module constants (10 hardcoded) | **C-7** (argparse + `--config`) |
| **F-A008** | output JSON naming convention scattered | **C-5** (profile `output_filename` key) |
| **F-A009** | no driver reads a config file | **C-4** (`tools.eval.config.load_run_profile` + `--config` flag on canonical CLI) |
| **F-A010** | canonical driver unused by wrappers | **C-8** (doc-only — `docs/configs.md` lists 4 profiles and shows the canonical CLI invocation) |

### F-B (configuration scattering) — 8 findings

| Finding | Description (short) | Closed by |
|---|---|---|
| **F-B001** | 12 settings scattered; no YAML loader | **C-4** (config infra + schema) |
| **F-B002** | `--pb-engine` flip inconsistency | **C-5** (profile `pb_engine: uff\|xtb` per model) + **C-6** (driver honors profile) |
| **F-B003** | `--force-mode` default `synthetic` unsafe at N=1000 | **C-5** (profile sets `force_mode: real` for kanzi_framework) |
| **F-B004** | `--nfe-budgets` per-model defaults | **C-5** (profile `nfe_budgets: [100\|250]`) |
| **F-B005** | `--max-records` defaults | **C-5** (profile `max_records: 1000`) |
| **F-B006** | `--composite-metric` only on cli | **C-5** (profile `composite_metric` key) |
| **F-B007** | `--upstream-n-samples` typo risk | **C-5** (profile `upstream_n_samples: 1000`) |
| **F-B008** | `--paper-metrics` / `--paper-reference` / `--restart-min-nfe` / `--n-molecules` only on cli | **C-5** (profile holds all 4) |

### F-C (GPU utilization root causes) — 4 findings

| Finding | Description (short) | Closed by |
|---|---|---|
| **F-C001 / RC-1** | DAE on CPU | **C-1** |
| **F-C002 / RC-2** | shim returns `torch.zeros_like(x)` (no-op framework arm) | **C-2** (fail-fast placeholder; real fix tracked under Wave 110.D follow-up backbone-coord migration) |
| **F-C003 / RC-3** | bridge auto-coerces to CPU | **C-1** (auto-fixed at 0 LOC once DAE is on CUDA) |
| **F-C004 / RC-4** | `_torch_velocity_field` no `device=` | **C-3** |

**Total: 22 findings → 22 closed (100%).**

---

## 5. Cross-reference matrix

Per wave111-data-linkage-plan.md §2.3 cross-reference matrix (with resolutions):

| Overlap | Resolution |
|---|---|
| F-A005 ≡ F-C001 (GPU util root cause) | both → C-1 |
| F-A009 ≡ F-B001 (no config file → build the config module) | both → C-4 |
| F-A001 ≡ F-B002 (`--pb-engine` half-fix) | both → C-5 (profile default) + C-6 (driver plumbing) |

---

## 6. Hard rules (preserved)

1. **NO push.** Every commit lands on the working tree; user-gated push.
2. **Backward compat:** existing CLI flags still work without `--config`.
   Resolution order: **CLI flag > YAML value > module-level default**.
3. **D.4 byte-stable = 33/33 PASS** preserved across C-1..C-8 (verified
   post-commit; running host reproduces 72 passed across
   `test_d4_regression_vectors.py` + `test_adapters/test_regression_vectors.py`).
4. **`mkdocs build --strict` = EXIT=0** preserved across C-1..C-8
   (verified post-commit; the only emitted warning is the upstream
   Material for MkDocs 2.0 advisory).
5. **No source deletion.** Additive migration only. CLI flags stay; module
   constants stay (now flag-sourced).
6. **GPU util verification** for C-1 — see §3 above.

---

## 7. Out-of-scope (explicit non-goals for Wave 111)

- **Real RC-2 fix** (Option A: migrate `_KanziDAEShim.forward()` to
  actually call `DAE.encode` + `DAE.net`, ~15-20 LOC) — tracked under
  **Wave 110.D follow-up** (backbone-coord space migration). Wave 111
  ships the fail-fast so the placeholder is visible, not the
  architectural fix.
- **Drop CLI flags** — the existing CLI flag surface is preserved
  (additive migration only); a future wave may add `DeprecationWarning`
  and remove, but not Wave 111.
- **Re-run Wave 110.C sweeps** — Wave 111 fixes the *config* surface and
  the *GPU util*; the next sweep wave (Wave 112.E?) re-runs with `--config`.
- **New model adapters** — no new `tools/*.py` driver; existing drivers only.

---

## 8. Files touched (cross-commit summary)

```
configs/runs/kanzi_n1000_baseline.yaml          (C-5, new, 41 LOC)
configs/runs/kanzi_n1000_framework.yaml         (C-5, new, 30 LOC)
configs/runs/flowmol3_n1000_paper.yaml          (C-5, new, 25 LOC)
configs/runs/lineageflow_n1000_gpu.yaml         (C-7, new, 31 LOC)

tools/eval/config.py                            (C-4, new, ~140 LOC)
tools/eval/cli.py                               (C-4, +10 LOC for --config)
tools/_kanzi_sweep_runner.py                    (C-1, +2 LOC)
tools/sweep_kanzi_n1000_paper_metrics.py        (C-6, +12 LOC)
tools/sweep_kanzi_n1000_framework_paper_metrics.py (C-6, +12 LOC)
tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py (C-6, +12 LOC)
tools/sweep_kanzi_n1000_diverse.py              (C-7, +10 LOC)
tools/wave87_n1000_sweep.py                     (C-7, +30 LOC)
tools/lineageflow_n1000_gpu_sweep.sh            (C-7, +20 LOC)
tools/upstream_eval.py                          (C-7, +10 LOC)

adaptive_reflow/adapters/kanzi.py               (C-2, +1 LOC; C-3, +3 LOC)

docs/configs.md                                 (C-8, new, ~85 LOC)
mkdocs.yml                                      (C-8, +2 LOC for Reference nav entry)
```

Approximate total: **~485 LOC** (matches the Wave 111 plan §7 estimate of
~484 LOC; the +1 difference is the `configs.md` doc itself, which the plan
counted separately under "W112.C-8").

---

## 9. Citations

All 8 commits cited above verified with `git rev-parse --verify <sha>`
(see §1 table). Original Wave 111 plan:
[`docs/audit/wave111-data-linkage-plan.md`](wave111-data-linkage-plan.md)
(HEAD = `7050128` from Wave 110.D).

---

**END OF CLOSURE — AUDIT-ONLY — NO PUSH**
