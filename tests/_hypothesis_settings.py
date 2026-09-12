"""Hypothesis profile registration — single source of truth.

Per Wave 32 Agent B R-5 (``todo/algo-improvement-hypothesis-derandomize.md``)
and Wave 38 Agent B execution: this module is the canonical place where
the CI Hypothesis profile is registered and loaded. The top-level
:mod:`tests.conftest` imports this module so the profile is active for
the entire pytest collection, including the property-based suite under
:mod:`tests.test_property_based` and :mod:`tests.property`.

Why a dedicated module
----------------------
Prior to this change, ``@settings(derandomize=True)`` was duplicated
across roughly a dozen property-based test modules
(``test_theory_checkers_properties.py``, ``test_eval_properties.py``,
``test_policy_driver_properties.py``, …). That pattern has three
problems:

1. **Drift**: a new contributor who adds a property-based test can
   forget to add ``derandomize=True``, breaking CI determinism
   silently.
2. **Bloat**: the same ten-line ``_PROPERTY_SETTINGS = settings(...)``
   block is repeated in every module.
3. **Single point of change is impossible**: tweaking the example
   count, the deadline, or the health-check suppression requires
   touching every file.

This module fixes all three by registering the canonical ``ci`` profile
*once* and loading it via the top-level conftest. Every ``@given``
test in the suite inherits ``derandomize=True`` without per-module
opt-in.

Why ``derandomize=True``
------------------------
The property-based suite targets deterministic algorithms (bounded
merge arithmetic, paper-quantity closed forms, blender convex
combinations, per-round capacity schedulers — see
``tests/test_property_based/__init__.py`` for the canonical list).
For deterministic code, the *positive-path* inputs that Hypothesis
explores do not need to vary run-to-run — what matters is that
Hypothesis's internal shrinker reproduces the *same* minimal failing
example across runs, which is exactly what ``derandomize=True``
guarantees.

Stochastic algorithms (C.7 Simulation-Based Calibration) live in
``tests/test_sbc/`` and are not affected by this profile because they
pin their own RNG via ``numpy.random.default_rng(seed=...)`` — the
determinism surface is independent of Hypothesis's internal deriver.

Database behavior under derandomize
-----------------------------------
``derandomize=True`` implies ``database=None``: no failing examples
are written to ``.hypothesis/examples``. This is the *correct*
behavior for CI:

* The replay DB only matters when a developer needs to reproduce a
  failure found in CI. With ``derandomize=True`` the *same* minimal
  example is regenerated on every run, so the DB adds nothing.
* Avoids the side-effect of CI runs accumulating entries in the
  per-developer ``.hypothesis/examples`` DB (which would otherwise be
  shared across clones via ``hypothesis_cache/`` symlinks, see
  ``docs/audit/web-research-2026.md`` F-11).

If a developer needs to *find* a failure (rather than replay one
that CI found), they can locally run with ``HYPOTHESIS_PROFILE=dev``
(see ``[tool.hypothesis.profiles.dev]`` below) which keeps the DB on
and uses a small ``max_examples`` budget.

Profile summary
---------------
``ci`` (loaded by default in this repo):

    derandomize=True, database=None, max_examples=200,
    deadline=2000, suppress_health_check=[too_slow]

``dev`` (opt-in via ``HYPOTHESIS_PROFILE=dev pytest``):

    derandomize=False, database=DirectoryBasedExampleDatabase,
    max_examples=50, deadline=2000

The pre-existing ``slow`` and ``stress`` profiles in
``pyproject.toml`` (lines under ``[tool.hypothesis.profiles."slow"]``
and ``[tool.hypothesis.profiles."stress"]``) are unchanged — tests
that explicitly opt into them via ``@settings(...)`` continue to
work.

Single-source-of-truth rule
---------------------------
The ``ci`` profile is registered in *two* places that must agree:

1. **Programmatically** — in this module via
   :func:`settings.register_profile` + :func:`settings.load_profile`.
   This is what actually takes effect when ``tests/conftest.py``
   imports this module at collection time.
2. **Declaratively** — in ``pyproject.toml`` under
   ``[tool.hypothesis.profiles.ci]``. This is what
   ``HYPOTHESIS_PROFILE=ci pytest`` picks up *without* going through
   conftest (e.g. for ``tox`` / ``nox`` workflows that bypass the
   test runner's conftest chain).

If you change one, change the other. The ``_CI_PROFILE_FIELDS`` tuple
below is the authoritative list of fields both sides must declare.
"""
from __future__ import annotations

from hypothesis import Verbosity, settings

# ---------------------------------------------------------------------------
# Authoritative profile spec (single source of truth)
# ---------------------------------------------------------------------------

#: Field set declared by the canonical ``ci`` profile. The
#: ``_CI_PROFILE_FIELDS`` tuple here is the authoritative field list;
#: the ``[tool.hypothesis.profiles.ci]`` block in ``pyproject.toml``
#: must declare the same fields. If you add or remove a field here,
#: mirror the change in ``pyproject.toml``.
_CI_PROFILE_FIELDS: tuple[str, ...] = (
    "derandomize",
    "max_examples",
    "deadline",
    "suppress_health_check",
    "verbosity",
)

#: Maximum number of examples explored per ``@given`` test under the
#: ``ci`` profile. The Hypothesis global default is 100; we raise to
#: 200 to give the property-based suite adequate boundary coverage
#: while keeping CI wall-clock bounded. The ``slow`` / ``stress``
#: profiles override this for their respective marker scopes.
_CI_MAX_EXAMPLES: int = 200

#: Per-example deadline in milliseconds. Matches the global default
#: registered in ``pyproject.toml``; the typed-contracts shrink logic
#: can spike to >1s on first compile, so 2000 ms (vs Hypothesis's
#: default 200 ms) is required for ``tests.test_property_based`` to
#: pass without spurious ``DeadlineExceeded`` errors.
_CI_DEADLINE_MS: int = 2000

#: Health checks to suppress. ``too_slow`` is suppressed because the
#: universal/molecular ``RoundResultBundle`` round-trip legitimately
#: exceeds Hypothesis's default 1.5-example-per-second throughput on
#: Windows file IO. ``deadline`` is left enabled — we *want* the
#: deadline health check to fail when an example genuinely exceeds
#: 2000 ms.
_CI_SUPPRESS_HEALTH_CHECK: tuple[str, ...] = ("too_slow",)

#: Verbosity level. ``Verbosity.normal`` surfaces only failure
#: messages; raise to ``Verbosity.verbose`` locally for hypothesis
#: exploration traces.
_CI_VERBOSITY: Verbosity = Verbosity.normal


# ---------------------------------------------------------------------------
# Profile registration (the actual side-effect)
# ---------------------------------------------------------------------------

# Register the ``ci`` profile. ``register_profile`` is idempotent — a
# second call with the same name overwrites the previous registration,
# so re-importing this module (e.g. across pytest's collection phases)
# is safe.
settings.register_profile(
    "ci",
    derandomize=True,
    max_examples=_CI_MAX_EXAMPLES,
    deadline=_CI_DEADLINE_MS,
    suppress_health_check=list(_CI_SUPPRESS_HEALTH_CHECK),
    verbosity=_CI_VERBOSITY,
)

# Register an opt-in ``dev`` profile for local failure-discovery runs.
# This is the *only* profile that keeps the failing-example DB on;
# see the module docstring for the rationale.
settings.register_profile(
    "dev",
    derandomize=False,
    max_examples=50,
    deadline=_CI_DEADLINE_MS,
    suppress_health_check=list(_CI_SUPPRESS_HEALTH_CHECK),
    verbosity=Verbosity.verbose,
)

# Wave 113.A.5 Fix 3 — ``shape_property`` profile for adapter
# shape-contract fuzzing (see
# ``tests/test_property_based/test_adapter_shape_contract.py``).
# The Wave 113.A bug was structurally a shape mismatch; fuzz testing
# with Hypothesis shrinks to the minimal failing tuple that breaks
# the (rank in {2,3}, dims in [1, 1024]) invariant. We deliberately
# cap ``max_examples=50`` and ``deadline=200`` to keep the CI run
# bounded — a true shape mismatch surfaces in <20 examples for any
# adapter whose ``state_shape`` is malformed.
settings.register_profile(
    "shape_property",
    max_examples=50,
    deadline=200,
    derandomize=True,
)

# Load the ``ci`` profile as the default. ``load_profile`` raises if
# the named profile does not exist; the explicit registration above
# guarantees that.
settings.load_profile("ci")


__all__ = [
    "_CI_DEADLINE_MS",
    "_CI_MAX_EXAMPLES",
    "_CI_PROFILE_FIELDS",
    "_CI_SUPPRESS_HEALTH_CHECK",
    "_CI_VERBOSITY",
]
