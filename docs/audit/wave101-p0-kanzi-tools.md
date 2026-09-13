# Wave 101 Layer-2 P0 Kanzi tools audit

The requested P0 items were already present in the current history: the two
obsolete `project_out_inv` Python utilities are archived under
`tools/archive/wave95-kanzi-inv/`, and all three canonical Kanzi N=1000 drivers
expose `--pb-engine {uff,xtb}` and forward it to `run_kanzi_sweep`.

This pass made one small environment fix in `tools/_kanzi_sweep_runner.py`:
PyTorch is now imported optionally, with a clear runtime error only when a
sweep is actually executed. This keeps `--help` usable in the lightweight
framework environment where the Kanzi sidecar (and torch) is absent.

Validation: both framework driver `--help` commands successfully render the
`--pb-engine` option. Kanzi runner tests are dependency-gated and reported
`2 skipped` because torch is not installed in the active environment.
