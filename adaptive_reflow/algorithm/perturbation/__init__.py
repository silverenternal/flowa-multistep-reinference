"""Perturbation subpackage.

Aggregates the canonical perturbation surface across the framework:

* :class:`UniformFreshPerturbation` + :class:`PaperQuantityAttractorInversion`
  — canonical perturbation policies (``perturbation.py``).
* :class:`CategoricalDynamicNoiseBias` + :class:`Theorem1DynamicNoiseBias`
  + :class:`IdentityDynamicNoiseBias` — dynamic noise bias family
  (``dynamic_noise_bias.py``).
* :class:`RotationPolicy` + :class:`BanditUCBRotationPolicy` +
  :class:`RoundRobinRotationPolicy` — rotation policy family
  (``rotation_policy.py``).
* Wave-18 round-2 extensions (``round2_extra.py``).

Each canonical module preserves its public symbol set; this
``__init__`` re-exports the names so that downstream code can use
either ``from adaptive_reflow.algorithm.perturbation import X``
(preferred new path) or the historical top-level shim
``from adaptive_reflow.algorithm.X import Y``.

PEP 562 ``__getattr__`` lazy binding
----------------------------------

The :mod:`round2_extra` module imports
:mod:`adaptive_reflow.algorithm.scheduler` which transitively pulls
in :mod:`adaptive_reflow.frame.adapter`. Loading the perturbation
subpackage eagerly therefore re-enters the partially-initialised
``adaptive_reflow.algorithm`` namespace (via ``frame.merge``), which
triggers an import-time circular error. To break the cycle we
expose the ``round2_extra`` symbols via PEP 562 ``__getattr__`` so
they are only materialised on first attribute access — by which
time ``adaptive_reflow.algorithm`` has finished initialising.
"""

from __future__ import annotations

from .dynamic_noise_bias import (
    CategoricalDynamicNoiseBias,
    DEFAULT_DECAY_KIND,
    DEFAULT_MIN_GUMBEL_TEMP,
    DynamicNoiseBiasProtocol,
    IdentityDynamicNoiseBias,
    NEW_DYNAMIC_NOISE_BIAS_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP,
    NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC,
    NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED,
    NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER,
    NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT,
    NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE,
    Theorem1DynamicNoiseBias,
    default_dynamic_noise_bias,
)
from .rotation_policy import (
    ROTATION_POLICY_REGISTRY,
    BanditUCBRotationPolicy,
    RotationPolicy,
    RoundRobinRotationPolicy,
    build_rotation_policy,
)

# Alias-import the ``perturbation`` submodule so the subpackage's own
# name does not shadow it. ``from .perturbation import X`` would be a
# self-import (the subpackage itself), which causes a partial-init
# error. Bind the module to a local alias instead.
from . import perturbation as _perturbation_mod

PaperQuantitiesPerturbationSnapshotProtocol = (
    _perturbation_mod.PaperQuantitiesPerturbationSnapshotProtocol
)
PaperQuantityAttractorInversion = _perturbation_mod.PaperQuantityAttractorInversion
PerturbationConfigError = _perturbation_mod.PerturbationConfigError
PerturbationPolicy = _perturbation_mod.PerturbationPolicy
UniformFreshPerturbation = _perturbation_mod.UniformFreshPerturbation
BRAI_FALLBACK_FIELDS_MISSING = _perturbation_mod.BRAI_FALLBACK_FIELDS_MISSING
BRAI_GRAD_FALLBACK_TO_FD = _perturbation_mod.BRAI_GRAD_FALLBACK_TO_FD
BRAI_NO_PAPER_QUANTITIES = _perturbation_mod.BRAI_NO_PAPER_QUANTITIES
BRAI_NONFINITE_QUANTITY_COERCED = _perturbation_mod.BRAI_NONFINITE_QUANTITY_COERCED
DEFAULT_BRAI_EPS_SCALE = _perturbation_mod.DEFAULT_BRAI_EPS_SCALE
DEFAULT_BRAI_GRAD_EPS = _perturbation_mod.DEFAULT_BRAI_GRAD_EPS
DEFAULT_BRAI_SIGMA = _perturbation_mod.DEFAULT_BRAI_SIGMA
build_perturbation_from_config = _perturbation_mod.build_perturbation_from_config
default_brai_perturbation = _perturbation_mod.default_brai_perturbation
default_uniform_fresh_perturbation = _perturbation_mod.default_uniform_fresh_perturbation
del _perturbation_mod


def __getattr__(name: str):
    """PEP 562 lazy lookup for round2_extra symbols.

    Imported on first access to break the algorithm → scheduler →
    frame → algorithm circular chain at subpackage load time.
    """
    if name in {
        "DUAL_TARGET_ADAPTIVE_FAMILY",
        "MULTICHANNEL_CONSTANT_POLICY_FAMILY",
        "MULTICHANNEL_JITTERED_FAMILY",
        "DualTargetAdaptivePolicyDriver",
        "MultiChannelConstantPolicyDriver",
        "MultiChannelJitteredConstantScheduler",
    }:
        from . import round2_extra

        g = globals()
        for sym in (
            "DUAL_TARGET_ADAPTIVE_FAMILY",
            "MULTICHANNEL_CONSTANT_POLICY_FAMILY",
            "MULTICHANNEL_JITTERED_FAMILY",
            "DualTargetAdaptivePolicyDriver",
            "MultiChannelConstantPolicyDriver",
            "MultiChannelJitteredConstantScheduler",
        ):
            g.setdefault(sym, getattr(round2_extra, sym))
        return g[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BRAI_FALLBACK_FIELDS_MISSING",
    "BRAI_GRAD_FALLBACK_TO_FD",
    "BRAI_NO_PAPER_QUANTITIES",
    "BRAI_NONFINITE_QUANTITY_COERCED",
    "BanditUCBRotationPolicy",
    "CategoricalDynamicNoiseBias",
    "DEFAULT_BRAI_EPS_SCALE",
    "DEFAULT_BRAI_GRAD_EPS",
    "DEFAULT_BRAI_SIGMA",
    "DEFAULT_DECAY_KIND",
    "DEFAULT_MIN_GUMBEL_TEMP",
    "DUAL_TARGET_ADAPTIVE_FAMILY",
    "DualTargetAdaptivePolicyDriver",
    "DynamicNoiseBiasProtocol",
    "IdentityDynamicNoiseBias",
    "MULTICHANNEL_CONSTANT_POLICY_FAMILY",
    "MULTICHANNEL_JITTERED_FAMILY",
    "MultiChannelConstantPolicyDriver",
    "MultiChannelJitteredConstantScheduler",
    "NEW_DYNAMIC_NOISE_BIAS_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_DIGEST_ONLY",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_FLOORED_BY_PAPER_EXTERIOR_GAP",
    "NEW_DYNAMIC_NOISE_BIAS_EPSILON_NONPOSITIVE",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_HEURISTIC",
    "NEW_DYNAMIC_NOISE_BIAS_GUMBEL_TEMP_COMPUTED",
    "NEW_DYNAMIC_NOISE_BIAS_NO_MATERIALIZER",
    "NEW_DYNAMIC_NOISE_BIAS_PREV_ANCHORED_TO_PREV_ENDPOINT",
    "NEW_DYNAMIC_NOISE_BIAS_SHEET_NONPOSITIVE",
    "PaperQuantitiesPerturbationSnapshotProtocol",
    "PaperQuantityAttractorInversion",
    "PerturbationConfigError",
    "PerturbationPolicy",
    "ROTATION_POLICY_REGISTRY",
    "RotationPolicy",
    "RoundRobinRotationPolicy",
    "Theorem1DynamicNoiseBias",
    "UniformFreshPerturbation",
    "build_perturbation_from_config",
    "build_rotation_policy",
    "default_brai_perturbation",
    "default_dynamic_noise_bias",
    "default_uniform_fresh_perturbation",
]
