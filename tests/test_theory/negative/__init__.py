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

Wave 23 E addition:

* ``test_proposition2_symmetry.py`` -- closes the final A.7 strict
  gap. Proposition 2 (line 62-64) was previously recorded as
  "covered-by-symmetry via Proposition 6"; this module replaces the
  symmetry argument with an explicit fixture set that violates
  Proposition 2's own hypothesis ``0 < m <= a(x) <= M < infinity``
  (4 rejections for ``inf a = 0``, 2 positive controls, 1 delegation
  control documenting that ``M < infinity`` is NOT enforced at fixed
  ``(d, c, rho, eta)``). With it, strict A.7 = 8 / 8 = 100 % of
  constructive A.0 entries.

See also:

* ``docs/baseline-audit-report.md`` §A.7 for the per-statement
  inventory and current coverage.
* ``todo/framework-internal-metrics.md`` §1.A.7 for the metric
  definition (constructive entries by Wave 16).
"""