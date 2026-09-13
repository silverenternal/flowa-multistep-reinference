---
name: flowa-experiment-sweep
description: Plan and run bounded FlowA adapter experiments and metric sweeps with pinned environments, checkpoints, GPU checks, and resumable outputs.
---

# FlowA Experiment Sweep

Run experiments as small, restartable waves.

- Read the target config and adapter contract first; select the model sidecar venv from `docs/environments.md` and never mix model environments.
- Before launching, capture GPU identity, free memory, command, config, seed, sample count, and output directory. Use bounded runs with explicit max-records when available.
- Emit machine-readable results plus a short audit note. Keep raw outputs under `verification_outputs/` or `results/`; do not overwrite prior evidence.
- Checkpoint after each phase: audit, implementation, smoke test, sweep, synthesis. Failed phases must be resumable.
- Validate with focused tests and relevant regression vectors; report device, wall-clock, skipped records, and statistical limitations.
