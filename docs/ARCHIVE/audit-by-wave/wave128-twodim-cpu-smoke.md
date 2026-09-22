# Wave 128 twodim CPU smoke

Using the `flowa-experiment-sweep` bounded-wave procedure, a CPU-only N=100
scheduler smoke was run with seed 42 for sigma labels `0.0`, `0.1`, and `0.5`.
The current repository has no dedicated twodim driver accepting these sigma
parameters, so this smoke exercises the existing `CodimensionSheetScheduler`
contract and records evidence ratios rather than claiming W2/FID improvement.

Command: inline Python invoking `CodimensionSheetScheduler(cycle_length=5,
n_min=0, n_max=1, eps_implicit=sigma)`; output:
`verification_outputs/wave128_twodim_cpu/smoke.json`.

All three cases completed on CPU under Python 3.14.5. Ratios follow the
diminishing-epsilon schedule through the interior rounds; the final value is
subject to the documented `1e-9` floor and therefore can rebound to ~1.0.
No long sweep or GPU process was started. Full twodim metric validation remains
blocked on a driver that exposes sigma and matched-NFE controls.
