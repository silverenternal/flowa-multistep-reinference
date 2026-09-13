# BRAI perturbation magnitude audit

The planned low-level BRAI fix is already landed: the perturbation policy's
`propose(..., magnitude=...)` override scales the perturbation per call,
validates finite positive values, and does not mutate the constructor
`eps_scale`. Existing property tests explicitly cover override, idempotence,
rejection, and state non-mutation.

Focused validation passed **45 tests** with one Hypothesis-dependent test
skipped because Hypothesis is absent from the active environment (3 warnings).
No model or GPU sweep was started; the remaining ESM-2 decision-metric swap in
the plan is a separate, model-dependent research task and remains pending.
