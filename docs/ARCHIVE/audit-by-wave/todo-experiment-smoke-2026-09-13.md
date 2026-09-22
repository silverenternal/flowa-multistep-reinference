# Controlled TODO experiment smoke (2026-09-13)

Applied the `flowa-experiment-sweep` workflow to the nearest executable
pending task: the Kanzi framework paper-metric driver dry-run. The run was
bounded to the driver's explicit `--dry-run --no-config` path; it does not
load weights, launch GPU work, or overwrite prior evidence.

* Command: `python tools/sweep_kanzi_n1000_framework_paper_metrics.py
  --dry-run --no-config`
* Result: exit code **78**, documented `SKIP_NO_CONFIG` gate.
* Output: `verification_outputs/todo_smoke_20260913/result.json` and
  `kanzi_dry_run.log`.
* Limitation: this mode intentionally skips adapter construction when no
  config is supplied; a full protocol smoke requires the Kanzi sidecar
  environment and config and remains a separate bounded step.

