# Run profiles (`configs/runs/`)

Wave 111 introduced a single source of truth for sweep-driver defaults:
**YAML profiles in `configs/runs/`** replace the per-driver hardcoded CLI /
shell / module constants that previously had to be edited by hand every
time a sweep was re-run. This page indexes every profile in the directory
and links to the audit docs that motivated each one.

## How to use

```bash
# 1. Pick a profile (any of the four below)
# 2. Pass it to the canonical CLI
.venvs/eval_venv/bin/python tools/eval/cli.py --config configs/runs/kanzi_n1000_baseline.yaml ...

# 3. Or to a thin-launcher shell / Python driver
bash tools/lineageflow_n1000_gpu_sweep.sh configs/runs/lineageflow_n1000_gpu.yaml
```

**Resolution order** (Wave 111.B §3): `CLI flag > YAML value > module-level default`.
Profiles are the new default surface; CLI flags remain the override surface.

**Schema:** see [`tools/eval/config.py`](../configs/runs/) and the schema
walkthrough in [`docs/audit/wave111-b-config-scattering-audit.md`](audit/wave111-b-config-scattering-audit.md) §2.

---

## Profile index

### 1. `kanzi_n1000_baseline.yaml` — Kanzi N=1000 baseline arm

**One-line summary.** Wave 109.A-equivalent Kanzi N=1000 baseline-arm
paper-metric sweep (`force_mode: synthetic`, `pb_engine: uff`, 1 mol/record,
`nfe_budgets: [100]`). Reproduces Wave 109.A baseline exactly.

**Source:** [`configs/runs/kanzi_n1000_baseline.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/kanzi_n1000_baseline.yaml)

**Motivation.** Wave 111.0 Reviewer A (F-A002, F-A004), Reviewer B
(F-B001, F-B003, F-B004, F-B005, F-B007, F-B008), Reviewer C (F-C001/RC-1).

- [Wave 111.0 Reviewer A — sweep driver architecture audit](audit/wave111-a-sweep-driver-audit.md)
- [Wave 111.0 Reviewer B — configuration scattering audit](audit/wave111-b-config-scattering-audit.md)
- [Wave 111.0 Reviewer C — GPU utilization audit](audit/wave111-c-gpu-utilization-audit.md)

### 2. `kanzi_n1000_framework.yaml` — Kanzi N=1000 framework arm

**One-line summary.** Wave 110.C-equivalent Kanzi N=1000 framework-arm
paper-metric sweep (`force_mode: real`, `paper_metrics: true`, σ=1e-3
synthetic endpoint via `_synthesize_x_final_synthetic`). Tracks the
PARTIAL Wave 110.C run that Bug 2 (Wave 110.B) put back in flight.

**Source:** [`configs/runs/kanzi_n1000_framework.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/kanzi_n1000_framework.yaml)

**Motivation.** Same Wave 111 audits; specifically F-A001 / F-B002
(`--pb-engine` flag contradiction) and F-C002 / RC-2 (placeholder
framework-arm `torch.zeros_like` return → fail-fast in C-2).

- [Wave 111.0 Reviewer A](audit/wave111-a-sweep-driver-audit.md)
- [Wave 111.0 Reviewer B](audit/wave111-b-config-scattering-audit.md)
- [Wave 111.0 Reviewer C](audit/wave111-c-gpu-utilization-audit.md)
- [Wave 110.B — Bug 2 fix (force_mode=real in KanziAdapter construction)](https://github.com/hugo/flowa-multistep-reinference/commit/4f7e3c7)

### 3. `flowmol3_n1000_paper.yaml` — FlowMol3 N=1000 paper-metric (PB-xtb)

**One-line summary.** Wave 87-equivalent FlowMol3 N=1000 PB-xtb
paper-metric sweep (`force_mode: real`, `pb_engine: xtb`, `nfe_budgets:
[250]`, 4 molecules/record via Wave 74 F1). Reproduces Wave 87 N=1000.

**Source:** [`configs/runs/flowmol3_n1000_paper.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/flowmol3_n1000_paper.yaml)

**Motivation.** Wave 111.0 Reviewer B (F-B001, F-B004 per-model NFE
default = `250` for FlowMol3 vs `100` for Kanzi, F-B008 `paper_metrics`).

- [Wave 111.0 Reviewer A](audit/wave111-a-sweep-driver-audit.md)
- [Wave 111.0 Reviewer B](audit/wave111-b-config-scattering-audit.md)

### 4. `lineageflow_n1000_gpu.yaml` — LineageFlow N=1000 GPU framework-vs-baseline

**One-line summary.** Wave 109.B-equivalent LineageFlow N=1000 GPU
framework-vs-baseline sweep via the thin-launcher shell wrapper
(`venv_py`, `timeout_s`, `output_filename` are out-of-schema — the shell
parses this YAML directly via `yaml.safe_load`). Closes F-A006 (11
hardcoded shell constants) and F-A007-equivalent lineageflow path.

**Source:** [`configs/runs/lineageflow_n1000_gpu.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/lineageflow_n1000_gpu.yaml)

**Motivation.** Wave 111.0 Reviewer A (F-A006 shell hardcodes) + Wave
112.D-3 shell-wrapper migration commit (Wave 112.C-7).

- [Wave 111.0 Reviewer A](audit/wave111-a-sweep-driver-audit.md)
- [Wave 111.0 Reviewer B](audit/wave111-b-config-scattering-audit.md)

---

## See also

- **Plan + schema walkthrough:** [`docs/audit/wave111-data-linkage-plan.md`](audit/wave111-data-linkage-plan.md) §4.
- **Closure:** [`docs/audit/wave111-data-linkage-closure.md`](audit/wave111-data-linkage-closure.md) — C-1..C-9 commit SHAs and finding-to-commit map.
- **Adapter glue:** `tools/_kanzi_sweep_runner.py` (Wave 105 P1-A) consumes the profile values for `adapter_*` and `output_filename` keys.
- **Canonical CLI:** `tools/eval/cli.py` (Wave 112.C-4) is the only driver required to consume a profile; sweep wrappers read the same YAML via shared helpers.
