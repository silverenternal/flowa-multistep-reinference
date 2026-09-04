"""Wave 14 C: 36-uplift isolation test suite.

One parametrized test per row of ``docs/benchmark-uplifts.md``. Each
parametrization calls ``_run_uplift`` with the uplift id, executes the
``on`` path (uplift enabled) and the ``off`` path (uplift disabled),
then asserts the per-uplift assertion recipe drawn from the
``assertion_strength`` taxonomy:

* **witness** -- discrete artifact (audit code / field) present on
  ``on`` and provably absent on ``off``. Deterministic; no MC noise.
* **inequality** -- continuous metric with a genuine OFF code path;
  assert directional inequality. For seed-dependent rows the assertion
  uses ``|mean(M_on - M_off)| > 3 * sigma``.
* **identity** -- byte-identical / exact-equality determinism guard.
  No ON/OFF axis; asserts identical across two configurations plus a
  negative control that the equality is not vacuous.
* **smoke-only** -- no distinguishable OFF path in framework code
  (baseline is NaN / a constant / a tool-side simulation). Test pins
  the golden value to 1e-9 and the documented range.
"""
