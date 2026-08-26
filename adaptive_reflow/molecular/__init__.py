"""Molecule concrete subpackage — pocket-conditioned 3D flow matching.

This subpackage is the *concrete* molecule implementation of the
universal abstractions declared in
:mod:`adaptive_reflow.universal`. It collects the molecule-specific
dataclasses, channel vocabulary, domain table, stratification enum,
mixer, and evaluator protocols into a single namespace.

Module boundary
---------------

* :mod:`adaptive_reflow.molecular.bundle` — :class:`MoleculeRoundResultBundle`
  (the concrete molecule atomic source bundle) + per-channel source-round
  validator.
* :mod:`adaptive_reflow.molecular.envelope` — :class:`MoleculeEnvelopeLayer`
  and the frozen manifest / tail budget / classification dataclasses.
* :mod:`adaptive_reflow.molecular.channels` — ``MOLECULE_CHANNELS`` tuple,
  the four ``*ChannelRef`` NewType aliases, and the closed
  :class:`MoleculeChannel` enum.
* :mod:`adaptive_reflow.molecular.domain` —
  :data:`MOLECULE_DOMAIN_BY_CHANNEL` fallback table.
* :mod:`adaptive_reflow.molecular.stratification` —
  :class:`MoleculeStratum` / :class:`MoleculeStratumAssignment` /
  :func:`dominance_ratio` / :func:`cross_stratum_mix_rejected`.
* :mod:`adaptive_reflow.molecular.mixer` —
  :class:`RMSPreservingCoordinateMixer` (concrete ``RestartMixer``)
  + back-compat :func:`adaptive_reflow_memory_restart_coords`.
* :mod:`adaptive_reflow.molecular.calibration_protocols` — concrete
  :class:`Evaluator` implementations for the four molecule evaluator
  arms (GNINA, PoseBusters, QED, ADMET) plus their factory helpers.

Public surface
--------------

The names re-exported below form the canonical ``adaptive_reflow.molecular``
public API. A caller who imports from this module does not need to
reach into the submodules directly.

Molecule channel vocabulary
    :data:`MOLECULE_CHANNELS`
    :data:`MOLECULE_DOMAIN_BY_CHANNEL`
    :data:`MOLECULE_CALIBRATION_TARGETS`
    :data:`MOLECULE_CHANNEL_TO_METRIC`
    :class:`MoleculeChannel`
    :data:`CoordinateChannelRef`
    :data:`ChargeChannelRef`
    :data:`RawPairChannelRef`
    :data:`ProjectedPairChannelRef`

Pure-data carriers
    :class:`MoleculeRoundResultBundle`
    :class:`MoleculeEnvelopeLayer`
    :class:`MoleculeEnvelopeManifest`
    :class:`MoleculeEnvelopeClassification`
    :class:`MoleculeTailBudgetRow`
    :class:`MoleculeStratum`
    :class:`MoleculeStratumAssignment`

Restart mixer (concrete ``RestartMixer`` Protocol)
    :class:`RMSPreservingCoordinateMixer`
    :func:`adaptive_reflow_memory_restart_coords`

Evaluator factories (concrete ``Evaluator`` Protocol)
    :func:`gnina_evaluator`
    :func:`posebusters_evaluator`
    :func:`qed_evaluator`
    :func:`admet_evaluator`
    :class:`GNINAEvaluator`
    :class:`PoseBustersEvaluator`
    :class:`QEDEvaluator`
    :class:`ADMETEvaluator`

Validators
    :func:`validate_molecule_round_result_bundle`
    :func:`validate_molecule_envelope_manifest`
    :func:`validate_molecule_tail_budget_row`

Back-compat helpers
    :func:`attach_molecule_channels`

Tasks satisfied
---------------

* ``DTB-G1`` — molecule channels are advertised via ``MOLECULE_CHANNELS``
  + :class:`MoleculeChannel`.
* ``DTB-R1`` / ``DTB-R2`` — :class:`MoleculeRoundResultBundle` extends
  the round-bundle contract with the four molecule channel handles.
* ``DTB-NC1`` / ``DTB-NC2`` — :class:`MoleculeEnvelopeLayer` implements
  the molecule half of the envelope ladder.
* ``DTB-R7`` — concrete molecule :class:`Evaluator` implementations
  live in :mod:`molecular.calibration_protocols`.
* ``DTB-L3`` / ``DTB-L4`` — :class:`MoleculeStratum` + dominance-ratio
  + Frankensteing-mix rejection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias, cast

from .bundle import (
    MoleculeRoundResultBundle,
    attach_molecule_channels,
    validate_molecule_round_result_bundle,
)
from .calibration_protocols import (
    DEFAULT_ADMET_TOX_THRESHOLD,
    DEFAULT_GNINA_TARGET_SCORE,
    DEFAULT_POSEBUSTERS_FAILURE_FRACTION,
    DEFAULT_QED_TARGET,
    MOLECULE_CALIBRATION_TARGETS,
    MOLECULE_CHANNEL_TO_METRIC,
    ADMETEvaluator,
    GNINAEvaluator,
    PoseBustersEvaluator,
    QEDEvaluator,
    adaptive_reflow_external_metric_controls,
    admet_evaluator,
    gnina_evaluator,
    posebusters_evaluator,
    qed_evaluator,
)
from .channels import (
    MOLECULE_CHANNELS,
    ChargeChannelRef,
    CoordinateChannelRef,
    MoleculeChannel,
    ProjectedPairChannelRef,
    RawPairChannelRef,
)
from .domain import MOLECULE_DOMAIN_BY_CHANNEL
from .envelope import (
    MoleculeEnvelopeClassification,
    MoleculeEnvelopeLayer,
    MoleculeEnvelopeManifest,
    MoleculeTailBudgetRow,
    validate_molecule_envelope_manifest,
    validate_molecule_tail_budget_row,
)
from .mixer import (
    RestartMemoryState,
    RMSPreservingCoordinateMixer,
    adaptive_reflow_memory_restart_coords,
    require_torch,
)
from .stratification import (
    MoleculeStratum,
    MoleculeStratumAssignment,
    cross_stratum_mix_rejected,
    dominance_ratio,
)

if TYPE_CHECKING:
    # Imported only for the static type checker so the ``TypeAlias`` below
    # can resolve the canonical RoundResultBundle without forcing an
    # eager runtime import that would cycle back into this module.
    from adaptive_reflow.molecular.bundle import (
        RoundResultBundle as _ContractsRoundResultBundle,
    )
    from adaptive_reflow.molecular.bundle import (
        RoundResultBundle as _Legacy,
    )
else:
    # Lazy runtime resolution: the actual class is fetched via a small
    # module-level helper rather than a top-level ``from contracts import``
    # so the ``contracts`` ↔ ``molecular`` import cycle is sidestepped.
    # The helper returns the same class object the type checker sees
    # through the ``TYPE_CHECKING`` branch above.
    def _resolve_contracts_round_result_bundle() -> type:
        from adaptive_reflow.contracts import RoundResultBundle

        return RoundResultBundle

    _ContractsRoundResultBundle: type = _resolve_contracts_round_result_bundle()
    _Legacy = _ContractsRoundResultBundle

# ---------------------------------------------------------------------------
# Thin adapter shim: map between molecule.RoundResultBundle and the OLD
# contracts.RoundResultBundle so existing tests continue to work.
#
# The OLD location (``adaptive_reflow.contracts.bundle.RoundResultBundle``)
# is unchanged in Phase B; it still exposes the four molecule channel
# fields because the molecule layer has been duplicated onto it. The
# shim below defines three helpers that bridge the two representations
# without touching the old file:
#
# 1. ``to_molecule_bundle(old_bundle)`` — copy the universal + molecule
#    fields from an old ``contracts.bundle.RoundResultBundle`` into a fresh
#    ``MoleculeRoundResultBundle``.
# 2. ``from_molecule_bundle(new_bundle)`` — copy the fields back into a
#    fresh ``contracts.bundle.RoundResultBundle`` for legacy callers.
# 3. ``is_compatible(old, new)`` — return True iff the two bundles carry
#    the same payload (universal + molecule fields). This is what
#    ``validate_round_result_bundle`` callers use to assert that no
#    data was lost in translation.
# ---------------------------------------------------------------------------


def to_molecule_bundle(
    old_bundle: contracts_RoundResultBundle,
) -> MoleculeRoundResultBundle:
    """Copy an old ``contracts.bundle.RoundResultBundle`` into a molecule one.

    The fields are copied 1-for-1; the derived ``observed_channels``
    mapping is populated by :class:`MoleculeRoundResultBundle.__post_init__`.
    """
    import dataclasses

    from adaptive_reflow.contracts import RoundResultBundle as _Legacy

    if not isinstance(old_bundle, _Legacy):
        raise TypeError(
            "to_molecule_bundle expected a contracts.RoundResultBundle, "
            f"got {type(old_bundle).__name__}"
        )
    molecule_field_names = {
        f.name for f in dataclasses.fields(MoleculeRoundResultBundle)
    }
    legacy_field_names = {f.name for f in dataclasses.fields(_Legacy)}
    shared = molecule_field_names & legacy_field_names
    # ``observed_channels`` is derived (``init=False``) and lives only on the
    # molecule bundle; drop it from the payload so the constructor accepts it.
    shared.discard("observed_channels")
    payload = {name: getattr(old_bundle, name) for name in shared}
    return MoleculeRoundResultBundle(**payload)


def from_molecule_bundle(
    new_bundle: MoleculeRoundResultBundle,
) -> contracts_RoundResultBundle:
    """Copy a molecule bundle back into the old ``contracts.bundle`` shape.

    The derived ``observed_channels`` mapping is *not* propagated; the
    legacy shape carries the four explicit molecule channel fields only.
    """
    import dataclasses

    # Lazy import to sidestep the ``contracts`` ↔ ``molecular`` cycle.
    # mypy sees the module-level ``TYPE_CHECKING`` binding for ``_Legacy``
    # (declared as ``RoundResultBundle``); the runtime import below does
    # not shadow it because we use ``del`` to drop the local binding
    # immediately after fetching the class reference into a typed local.
    from adaptive_reflow.contracts import RoundResultBundle as _Legacy

    legacy_class: type = _Legacy
    del _Legacy  # drop the local so static analyzers see only the typed alias

    if not isinstance(new_bundle, MoleculeRoundResultBundle):
        raise TypeError(
            "from_molecule_bundle expected a MoleculeRoundResultBundle, "
            f"got {type(new_bundle).__name__}"
        )
    molecule_field_names = {
        f.name for f in dataclasses.fields(MoleculeRoundResultBundle)
    }
    legacy_field_names = {f.name for f in dataclasses.fields(legacy_class)}
    shared = molecule_field_names & legacy_field_names
    shared.discard("observed_channels")
    payload = {name: getattr(new_bundle, name) for name in shared}
    return cast(contracts_RoundResultBundle, legacy_class(**payload))


def is_compatible(
    old_bundle: contracts_RoundResultBundle,
    new_bundle: MoleculeRoundResultBundle,
) -> bool:
    """Return True iff the two bundles carry the same payload.

    Compares every non-derived field with ``==``. The derived
    ``observed_channels`` mapping is *not* compared because it has no
    counterpart on the legacy bundle.
    """
    import dataclasses

    from adaptive_reflow.contracts import RoundResultBundle as _Legacy

    if not isinstance(old_bundle, _Legacy):
        return False
    if not isinstance(new_bundle, MoleculeRoundResultBundle):
        return False
    old_field_names = {f.name for f in dataclasses.fields(_Legacy)}
    new_field_names = {
        f.name for f in dataclasses.fields(MoleculeRoundResultBundle)
    }
    shared = old_field_names & new_field_names
    shared.discard("observed_channels")
    return all(getattr(old_bundle, name) == getattr(new_bundle, name) for name in shared)


# ``contracts_RoundResultBundle`` is a forward-reference annotation used by
# :func:`to_molecule_bundle` and :func:`from_molecule_bundle`. The actual
# ``adaptive_reflow.contracts.RoundResultBundle`` class is imported only
# for the static type checker (via ``TYPE_CHECKING``); the runtime
# resolution happens lazily inside the helper functions to sidestep the
# ``contracts`` ↔ ``molecular`` import cycle. Declared as a
# :data:`TypeAlias` so mypy treats it as a type rather than a plain
# variable.
contracts_RoundResultBundle: TypeAlias = _ContractsRoundResultBundle

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    # Molecule channel vocabulary
    "MOLECULE_CHANNELS",
    "MOLECULE_DOMAIN_BY_CHANNEL",
    "MOLECULE_CALIBRATION_TARGETS",
    "MOLECULE_CHANNEL_TO_METRIC",
    "MoleculeChannel",
    # Channel NewType aliases
    "CoordinateChannelRef",
    "ChargeChannelRef",
    "RawPairChannelRef",
    "ProjectedPairChannelRef",
    # Atomic source bundle (molecule concrete)
    "MoleculeRoundResultBundle",
    "validate_molecule_round_result_bundle",
    "attach_molecule_channels",
    # Envelope dataclasses
    "MoleculeEnvelopeLayer",
    "MoleculeEnvelopeManifest",
    "MoleculeEnvelopeClassification",
    "MoleculeTailBudgetRow",
    "validate_molecule_envelope_manifest",
    "validate_molecule_tail_budget_row",
    # Stratification
    "MoleculeStratum",
    "MoleculeStratumAssignment",
    "dominance_ratio",
    "cross_stratum_mix_rejected",
    # Restart mixer
    "RMSPreservingCoordinateMixer",
    "RestartMemoryState",
    "adaptive_reflow_memory_restart_coords",
    "require_torch",
    # Concrete Evaluator classes
    "GNINAEvaluator",
    "PoseBustersEvaluator",
    "QEDEvaluator",
    "ADMETEvaluator",
    # Evaluator factories
    "gnina_evaluator",
    "posebusters_evaluator",
    "qed_evaluator",
    "admet_evaluator",
    # Default targets
    "DEFAULT_GNINA_TARGET_SCORE",
    "DEFAULT_QED_TARGET",
    "DEFAULT_POSEBUSTERS_FAILURE_FRACTION",
    "DEFAULT_ADMET_TOX_THRESHOLD",
    # Back-compat free function (legacy facade)
    "adaptive_reflow_external_metric_controls",
    # Adapter shim helpers
    "to_molecule_bundle",
    "from_molecule_bundle",
    "is_compatible",
    # Forward-reference string used by the shim
    "contracts_RoundResultBundle",
]
