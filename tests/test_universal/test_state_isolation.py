"""State isolation tests for Flow Matching ODE adapters.

These tests verify that two adapter instances do not share mutable state,
and that successive calls into a single adapter do not leak state across
calls. They cover the four canonical isolation patterns:

* instance-to-instance independence (``TestInstanceIndependence``)
* call-to-call independence for state construction (``TestBatchIndependence``)
* lifecycle independence at construction time (``TestCleanupDoesNotLeak``)
* concurrent-style build isolation (``TestConcurrentBuildInitialState``)

All tests use :class:`ToyLinearAdapter`, the canonical worked-example
adapter declared in :mod:`adaptive_reflow.adapters.toy_linear`. The toy
adapter stores a single mutable parameter, ``_drift``, plus an
implicit-instance ``capability_token`` resolved lazily on
:meth:`capabilities` calls. That surface is small but sufficient to
exercise the isolation contract.
"""

from __future__ import annotations

from adaptive_reflow.adapters.toy_linear import (
    ToyLinearAdapter,
    default_toy_linear_adapter,
)
from adaptive_reflow.universal import validate_state_bundle

# ---------------------------------------------------------------------------
# TestInstanceIndependence
# ---------------------------------------------------------------------------


class TestInstanceIndependence:
    """Two adapter instances must not share mutable instance state."""

    def test_modifying_instance1_drift_does_not_affect_instance2(self) -> None:
        """Mutating ``_drift`` on instance1 MUST NOT affect instance2.

        ToyLinearAdapter stores its drift as a per-instance attribute
        (``self._drift``); the class-level ``pinned_seed_drift`` is only
        used as the default. Two freshly-constructed instances therefore
        own independent copies of ``_drift`` and modifying one must leave
        the other untouched.
        """
        instance1 = ToyLinearAdapter()
        instance2 = ToyLinearAdapter()

        # Sanity: both instances start at the default drift value.
        default_drift = ToyLinearAdapter.pinned_seed_drift
        assert instance1._drift == default_drift
        assert instance2._drift == default_drift

        # Mutate instance1.
        instance1._drift = 7.5

        # instance2 MUST remain at the default value.
        assert instance2._drift == default_drift, (
            "instance2._drift was mutated as a side-effect of writing to "
            "instance1._drift — the two instances share state"
        )
        assert instance2._drift != instance1._drift

    def test_class_attribute_is_not_mutated_by_instance_write(self) -> None:
        """Writing to ``self._drift`` on an instance MUST NOT leak back
        into the class attribute ``pinned_seed_drift``.

        This guards against an adapter author accidentally binding the
        instance parameter to a mutable class-level default (e.g. a list
        or dict shared across instances). The current ToyLinearAdapter
        uses a float, but the test enforces the broader invariant.
        """
        class_default_before = ToyLinearAdapter.pinned_seed_drift

        adapter = ToyLinearAdapter()
        adapter._drift = 99.0

        assert ToyLinearAdapter.pinned_seed_drift == class_default_before, (
            "instance assignment to _drift mutated the class attribute"
        )


# ---------------------------------------------------------------------------
# TestBatchIndependence
# ---------------------------------------------------------------------------


class TestBatchIndependence:
    """Repeated ``build_initial_state`` calls on one adapter must each
    produce a distinct :class:`StateBundle`.
    """

    def test_one_hundred_initial_states_are_distinct(self) -> None:
        """Calling ``build_initial_state`` 100 times on a fresh adapter
        must produce 100 bundles with distinct native_state_digest values.

        The toy adapter derives the digest from ``(batch_id, sample_id,
        source_round)``; feeding each call a unique sample_id guarantees
        the digests collide-free. If state leaked across calls, we would
        see two bundles share a digest.
        """
        adapter = ToyLinearAdapter()

        digests: list[str] = []
        for idx in range(100):
            bundle = adapter.build_initial_state(
                batch_id="batch-A",
                sample_id=f"sample-{idx:03d}",
                source_round=0,
            )
            # Each bundle MUST validate — this is the engine-level
            # structural invariant that isolation must not break.
            ok, errs = validate_state_bundle(bundle)
            assert ok, (
                f"bundle #{idx} failed validate_state_bundle: {errs}"
            )
            digests.append(bundle.native_state_digest)

        # All 100 digests must be unique. If state had leaked across
        # calls (e.g. via a shared counter, a singleton sample-id, or a
        # module-level cache) we'd see duplicates.
        assert len(set(digests)) == 100, (
            f"expected 100 distinct native_state_digest values, "
            f"got {len(set(digests))}"
        )

    def test_initial_state_increments_are_independent(self) -> None:
        """Successive builds MUST produce bundles whose ``sample_id``
        matches the one passed in, not a counter incremented internally.

        This is the most direct proxy for "the adapter is not smuggling
        hidden state into the bundle identifier".
        """
        adapter = ToyLinearAdapter()

        seen_ids: set[str] = set()
        for idx in range(100):
            sample_id = f"sample-{idx:03d}"
            bundle = adapter.build_initial_state(
                batch_id="b",
                sample_id=sample_id,
                source_round=0,
            )
            assert bundle.sample_id == sample_id
            seen_ids.add(sample_id)

        # All 100 ids were recorded — none were silently rewritten.
        assert len(seen_ids) == 100


# ---------------------------------------------------------------------------
# TestCleanupDoesNotLeak
# ---------------------------------------------------------------------------


class TestCleanupDoesNotLeak:
    """Constructing a fresh adapter must not inherit state from a sibling.

    The "leak" we guard against here is the classic Python footgun: a
    mutable default argument, a module-level singleton, or a cached
    ``__init__`` body that hands out references to shared objects.
    ToyLinearAdapter only carries a scalar ``_drift``; that is enough to
    exercise the contract.
    """

    def test_fresh_adapter_has_default_drift(self) -> None:
        """Adapter B constructed after adapter A MUST start at the
        class-level default drift, regardless of what A holds."""
        adapter_a = ToyLinearAdapter()
        adapter_a._drift = 12.34  # pollute A

        adapter_b = ToyLinearAdapter()

        default_drift = ToyLinearAdapter.pinned_seed_drift
        assert adapter_b._drift == default_drift, (
            f"adapter_b._drift == {adapter_b._drift!r}, expected default "
            f"{default_drift!r}; A's mutation leaked into B's construction"
        )

    def test_fresh_adapter_initial_state_matches_default(self) -> None:
        """A fresh adapter must produce the same default initial state
        even after a sibling has been heavily used."""
        # Heavy-use adapter A.
        adapter_a = ToyLinearAdapter(drift=2.5)
        for idx in range(50):
            adapter_a.build_initial_state(
                batch_id="bA",
                sample_id=f"s-{idx:03d}",
                source_round=0,
            )
        adapter_a._drift = 999.0

        # Fresh adapter B: state must be at default, not derived from A.
        adapter_b = ToyLinearAdapter()
        assert adapter_b._drift == ToyLinearAdapter.pinned_seed_drift

        bundle_b = adapter_b.build_initial_state(
            batch_id="bB",
            sample_id="s-fresh",
            source_round=0,
        )
        # The fresh adapter must validate its own bundle cleanly.
        ok, errs = validate_state_bundle(bundle_b)
        assert ok, f"fresh adapter produced invalid bundle: {errs}"
        assert bundle_b.sample_id == "s-fresh"

    def test_default_factory_helper_returns_independent_instance(self) -> None:
        """``default_toy_linear_adapter()`` must return a fresh instance
        each time — calling it twice must yield two independent adapters.
        """
        a = default_toy_linear_adapter()
        b = default_toy_linear_adapter()

        assert a is not b, "factory returned the same singleton object"
        a._drift = 4.2
        assert b._drift == ToyLinearAdapter.pinned_seed_drift


# ---------------------------------------------------------------------------
# TestConcurrentBuildInitialState
# ---------------------------------------------------------------------------


class TestConcurrentBuildInitialState:
    """Build several initial states on a single adapter; each must be
    unique, valid, and free of interference.
    """

    def test_ten_builds_produce_unique_valid_bundles(self) -> None:
        """Ten builds with the same adapter: each bundle's native
        state digest is unique, and each bundle satisfies the StateBundle
        invariants.
        """
        adapter = ToyLinearAdapter()
        n = 10

        bundles = [
            adapter.build_initial_state(
                batch_id="batch-shared",
                sample_id=f"sample-{idx:02d}",
                source_round=0,
            )
            for idx in range(n)
        ]

        # Each bundle MUST validate.
        for idx, bundle in enumerate(bundles):
            ok, errs = validate_state_bundle(bundle)
            assert ok, (
                f"bundle #{idx} failed validate_state_bundle: {errs}"
            )

        # Each bundle MUST be unique-by-digest.
        digests = [b.native_state_digest for b in bundles]
        assert len(set(digests)) == n, (
            f"expected {n} unique digests, got {len(set(digests))}: "
            f"{digests}"
        )

        # Bundles must be distinct objects (no aliasing).
        assert len({id(b) for b in bundles}) == n

    def test_interleaved_builds_do_not_share_provenance(self) -> None:
        """Interleaved build calls must produce bundles whose provenance
        tuples are equal (the toy adapter stamps the same tag on every
        bundle), proving the tuple is not being mutated or extended
        call-to-call.
        """
        adapter = ToyLinearAdapter()

        bundles: list = []
        for idx in range(10):
            bundles.append(
                adapter.build_initial_state(
                    batch_id="b",
                    sample_id=f"s-{idx:02d}",
                )
            )

        provenances = {b.provenance for b in bundles}
        assert len(provenances) == 1, (
            f"provenance tuples diverged across builds: {provenances}"
        )

    def test_repeated_build_with_same_inputs_is_stable(self) -> None:
        """Two builds with identical inputs must produce the same digest
        AND distinct bundle objects. This proves (a) the adapter is
        deterministic and (b) no shared-state caching aliases the
        returned object.
        """
        adapter = ToyLinearAdapter()

        b1 = adapter.build_initial_state(
            batch_id="b", sample_id="s", source_round=0
        )
        b2 = adapter.build_initial_state(
            batch_id="b", sample_id="s", source_round=0
        )

        # Determinism.
        assert b1.native_state_digest == b2.native_state_digest

        # Object identity isolation: b1 and b2 are NOT the same object,
        # so subsequent mutation of one (e.g. via a wrapper) cannot
        # affect the other.
        assert b1 is not b2
