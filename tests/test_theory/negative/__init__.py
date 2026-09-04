"""Canonical must-fail (hypothesis-violation) fixtures for A.7.

This subdirectory is the canonical home for hypothesis-violation
fixtures (A.7, rev 2): tests that assert a paper-statement function
rejects inputs violating the statement's preconditions.

Convention (Wave 15 A.7.2):

* Each module under ``tests/test_theory/negative/`` corresponds to a
  single paper statement (Lemma N / Theorem N / Proposition N) and
  imports the function-under-test from
  ``adaptive_reflow.theory.{paper_quantities,validation,...}``.
* Positive fixtures for the same paper statement stay in the
  sibling ``tests/test_theory/test_<statement>.py`` modules (the
  Wave 11 / Wave 12 convention). The split keeps positive and
  must-fail tests discoverable separately so the A.7 audit can
  enumerate them via ``ls tests/test_theory/negative/`` without
  false positives from co-located positive tests.

Initial population (Wave 15 A.7.1):

* ``test_lemma3_per_cell_coefficient.py`` -- promoted from the
  audit's strict-reading gap. Future per-paper must-fail fixtures
  (Lemma 2 / 4 / 5 dedicated modules, Proposition 6 dedicated
  module, etc.) will land here in subsequent waves.

See also:

* ``docs/baseline-audit-report.md`` §A.7 for the per-statement
  inventory and current coverage.
* ``todo/framework-internal-metrics.md`` §1.A.7 for the metric
  definition (constructive entries by Wave 16).
"""