# Kanzi inverse-projection bridge follow-up

Source audit confirms the planned pre-loop bridge is already implemented in
`tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` (Wave 122): for
`framework_inv_proj`, it decodes the `(L,512)` endpoint through the trained
512→4 inverse and DAE decoder, converts Å→nm, updates the trajectory shape to
`(L,3)`, then enters `solve_ode`. No additional CPU-safe code change is
justified without the Kanzi sidecar model.

Focused tests were invoked:

```text
pytest -q tests/test_tools/test_kanzi_latent_to_coord.py \
  tests/test_tools/test_kanzi_sweep_runner.py
```

Result: 2 tests collected, both **skipped** because torch is unavailable in
the active environment. This is an environment limitation, not a test
failure. A long N=1000 sweep is intentionally deferred. Resumable command
metadata:

```json
{"command":".venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics.py --input <records> --limit 1000 --mode framework_inv_proj","max_records":1000,"output_dir":"verification_outputs/kanzi_inv_proj_wave125","resume":"rerun with same output_dir"}
```

