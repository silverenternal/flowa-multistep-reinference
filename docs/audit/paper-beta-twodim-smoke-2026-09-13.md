# Paper beta calibration: twodim CPU smoke

Ran the existing controlled audit in the project `.venv` as the next
resource-free acceptance step:

```text
./.venv/bin/python -m tools.run_controlled_audit --quick \
  --models twodim_fm --sigma 0 \
  --output verification_outputs/twodim_beta_smoke_20260913/result.json
```

The single-seed smoke completed in 3.52 seconds across NFE 10/50/200. All
three matched-NFE checks passed, but framework metrics were higher than
baseline (deltas +0.1339, +0.1288, +0.1288), so the plan's target
“framework improves by ≥5%” is **not met**. This is evidence for keeping the
beta-calibration plan `IN PROGRESS`; no GPU run was started. The JSON output is
isolated and resumable for a multi-seed follow-up.

