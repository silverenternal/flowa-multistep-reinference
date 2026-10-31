# Run profiles (`configs/runs/`)

Sweep-driver defaults live in one place: **YAML profiles in `configs/runs/`**
replace the per-driver hardcoded CLI / shell / module constants that
previously had to be edited by hand every time a sweep was re-run. This page
indexes every profile in the directory and links to the audit docs behind
each one.

## How to use

```bash
# 1. Pick a profile (any of the four below)
# 2. Pass it to the canonical CLI
.venvs/eval_venv/bin/python tools/eval/cli.py --config configs/runs/kanzi_n1000_baseline.yaml ...

# 3. Or to a thin-launcher shell / Python driver
bash tools/lineageflow_n1000_gpu_sweep.sh configs/runs/lineageflow_n1000_gpu.yaml
```

**Resolution order:** `CLI flag > YAML value > module-level default`.
Profiles are the new default surface; CLI flags remain the override surface.

**Schema:** see [`tools/eval/config.py`](../configs/runs/) and the schema
walkthrough in `docs/audit/sweep_eval/b-config-scattering-audit.md` §2.

---

## Profile index

### 1. `kanzi_n1000_baseline.yaml` — Kanzi N=1000 baseline arm

**One-line summary.** Kanzi N=1000 baseline-arm paper-metric sweep
(`force_mode: synthetic`, `pb_engine: uff`, 1 mol/record,
`nfe_budgets: [100]`). Reproduces the N=1000 baseline arm exactly.

**Source:** [`configs/runs/kanzi_n1000_baseline.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/kanzi_n1000_baseline.yaml)

**Motivation.** F-A002, F-A004, F-B001, F-B003, F-B004, F-B005, F-B007,
F-B008 and F-C001/RC-1 from the sweep-driver review.

- [Reviewer A — sweep driver architecture audit](ARCHIVE/audit-by-wave/wave111-a-sweep-driver-audit.md)
- Reviewer B — configuration scattering audit
- [Reviewer C — GPU utilization audit](ARCHIVE/audit-by-wave/wave111-c-gpu-utilization-audit.md)

### 2. `kanzi_n1000_framework.yaml` — Kanzi N=1000 framework arm

**One-line summary.** Kanzi N=1000 framework-arm paper-metric sweep
(`force_mode: real`, `paper_metrics: true`, σ=1e-3 synthetic endpoint via
`_synthesize_x_final_synthetic`). Tracks the PARTIAL framework-arm run that
the Bug 2 fix put back in flight.

**Source:** [`configs/runs/kanzi_n1000_framework.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/kanzi_n1000_framework.yaml)

**Motivation.** The same sweep-driver review; specifically F-A001 / F-B002
(`--pb-engine` flag contradiction) and F-C002 / RC-2 (placeholder
framework-arm `torch.zeros_like` return → fail-fast in C-2).

- [Reviewer A](ARCHIVE/audit-by-wave/wave111-a-sweep-driver-audit.md)
- Reviewer B
- [Reviewer C](ARCHIVE/audit-by-wave/wave111-c-gpu-utilization-audit.md)
- [Bug 2 fix (force_mode=real in KanziAdapter construction)](https://github.com/hugo/flowa-multistep-reinference/commit/4f7e3c7)

### 3. `flowmol3_n1000_paper.yaml` — FlowMol3 N=1000 paper-metric (PB-xtb)

**One-line summary.** FlowMol3 N=1000 PB-xtb paper-metric sweep
(`force_mode: real`, `pb_engine: xtb`, `nfe_budgets: [250]`, 4
molecules/record). Reproduces the N=1000 PB-xtb reading.

**Source:** [`configs/runs/flowmol3_n1000_paper.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/flowmol3_n1000_paper.yaml)

**Motivation.** F-B001, F-B004 (per-model NFE default = `250` for FlowMol3 vs
`100` for Kanzi), F-B008 (`paper_metrics`).

- [Reviewer A](ARCHIVE/audit-by-wave/wave111-a-sweep-driver-audit.md)
- Reviewer B

### 4. `lineageflow_n1000_gpu.yaml` — LineageFlow N=1000 GPU framework-vs-baseline

**One-line summary.** LineageFlow N=1000 GPU framework-vs-baseline sweep via
the thin-launcher shell wrapper (`venv_py`, `timeout_s`, `output_filename`
are out-of-schema — the shell parses this YAML directly via
`yaml.safe_load`). Closes F-A006 (11 hardcoded shell constants) and the
lineageflow path of F-A007.

**Source:** [`configs/runs/lineageflow_n1000_gpu.yaml`](https://github.com/hugo/flowa-multistep-reinference/blob/main/configs/runs/lineageflow_n1000_gpu.yaml)

**Motivation.** F-A006 (shell hardcodes) and the shell-wrapper migration
commit.

- [Reviewer A](ARCHIVE/audit-by-wave/wave111-a-sweep-driver-audit.md)
- Reviewer B

---

## See also

- **Plan + schema walkthrough:** `docs/audit/data_packaging/data-linkage-plan.md` §4.
- **Closure:** `docs/audit/data_packaging/data-linkage-closure.md` — C-1..C-9 commit SHAs and finding-to-commit map.
- **Adapter glue:** `tools/_kanzi_sweep_runner.py` consumes the profile values for `adapter_*` and `output_filename` keys.
- **Canonical CLI:** `tools/eval/cli.py` is the only driver required to consume a profile; sweep wrappers read the same YAML via shared helpers.
