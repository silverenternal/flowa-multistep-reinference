# Wave 101 P1-A Kanzi runner audit

The requested extraction is already present in history (`949001b`, Wave 105
P1-A). The three canonical N=1000 drivers delegate their sweep body to
`tools._kanzi_sweep_runner.run_kanzi_sweep`; their remaining code is CLI/profile
wiring and mode-specific defaults. No further mechanical move is warranted,
so CLI and output behavior remain unchanged.

Current line counts are 200, 171, and 201 lines for the three drivers and 1,045
lines for the shared runner. All three `--help` invocations exited 0 and exposed
`--pb-engine`. Runner tests are dependency-gated: 2 skipped because torch is
not installed in the active framework environment.
