# RF CIFAR ablation resumability audit

`tools/run_rf_cifar_ablation.py` executes scheduler arms serially and writes
each arm only after completion. A failed long arm therefore forced operators
to repeat earlier arms. Added an opt-in `--resume` flag: when a per-arm JSON
exists, has the expected scheduler name, and has no recorded error, the arm is
reused; malformed, partial, or failed artifacts are ignored and recomputed.
Default behavior is unchanged, and no algorithm or scheduler semantics were
modified.

Validation: `python -m tools.run_rf_cifar_ablation --help` exposes `--resume`;
the focused test file passes **5 tests** (2 dependency-gated skips, 3 warnings).
No GPU sweep was launched.
