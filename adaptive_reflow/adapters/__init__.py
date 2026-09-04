"""Adaptive reflow — model glue (DTB-G1 + DTB-G2).

Concrete :class:`FlowMatchingODEAdapter` implementations. The synthetic
fixtures live here (not in ``tests/``) so external parity harnesses can
import them too.
"""
from typing import Any

from .flowmol3 import (  # noqa: I001 -- alphabetical re-export ordering
    FLOWMOL3_CHANNEL_DOMAINS,
    FLOWMOL3_CHANNELS,
    FlowMol3Adapter,
    FlowMol3Capabilities,
    default_flowmol3_adapter,
    flowmol3_registry_entry,
)
from .hidream_i1 import (
    HIDREAM_I1_CHANNEL_DOMAINS,
    HIDREAM_I1_CHANNELS,
    HIDREAM_I1_MECHANISM_ID,
    HIDREAM_I1_STATE_SHAPE,
    HiDreamI1Adapter,
    HiDreamI1Capabilities,
    default_hidream_i1_adapter,
    hidream_i1_resolve_weights_path,
)
from .lumina_image_2_0 import (  # noqa: I001
    LUMINA_IMAGE_2_0_CHANNEL_DOMAINS,
    LUMINA_IMAGE_2_0_CHANNELS,
    LUMINA_IMAGE_2_0_CONFIG_HASH,
    LUMINA_IMAGE_2_0_CONFIG_VERSION,
    LUMINA_IMAGE_2_0_MECHANISM_ID,
    LUMINA_IMAGE_2_0_STATE_SHAPE,
    LuminaImage20Adapter,
    LuminaImage20Capabilities,
    default_lumina_image_2_0_adapter,
)
from .lineageflow import (
    LINEAGEFLOW_CHANNEL_DOMAINS,
    LINEAGEFLOW_CHANNELS,
    LINEAGEFLOW_CONFIG_HASH,
    LINEAGEFLOW_CONFIG_VERSION,
    LINEAGEFLOW_MECHANISM_ID,
    LINEAGEFLOW_NUM_STEPS_DEFAULT,
    LINEAGEFLOW_STATE_SHAPE,
    LineageFlowAdapter,
    LineageFlowCapabilities,
    default_lineageflow_adapter,
    lineageflow_resolve_weights_path,
)
from .protbfn_abbfn_adapter import (
    AMINO_ACID_CATEGORICAL,
    PROTBFN_ABBFN_CHANNELS,
    PROTBFN_ABBFN_CHANNEL_DOMAINS,
    PROTBFN_ABBFN_CONFIG_HASH,
    PROTBFN_ABBFN_STATE_SHAPE,
    ProtBFNAbBFNAdapter,
    ProtBFNAbBFNCapabilities,
    default_protbfnabbfn_adapter,
)
from .flowmol3_v2_adapter import (
    AUDIT_FLOWMOL3_NUMPY_BACKEND,
    AUDIT_FLOWMOL3_RESTART_BLEND,
    AUDIT_FLOWMOL3_TORCH_BACKEND,
    AUDIT_FLOWMOL3_TRAJECTORY_BUILT,
    FLOWMOL3ADAPTER_CHANNEL_DOMAINS,
    FLOWMOL3ADAPTER_CHANNELS,
    FLOWMOL3ADAPTER_CONFIG_HASH,
    FLOWMOL3ADAPTER_CONFIG_VERSION,
    FLOWMOL3ADAPTER_DOMAIN_METADATA,
    FLOWMOL3ADAPTER_MECHANISM_ID,
    FLOWMOL3ADAPTER_N_ATOM_TYPES,
    FLOWMOL3ADAPTER_N_BOND_TYPES,
    FLOWMOL3ADAPTER_NATIVE_STATES_MAXSIZE,
    FLOWMOL3ADAPTER_NUM_STEPS_DEFAULT,
    FLOWMOL3ADAPTER_PINNED_COMMIT,
    FLOWMOL3ADAPTER_STATE_SHAPE,
    FlowMol3V2AdapterCapabilities,
    FlowMol3V2Adapter,
    default_flowmol3adapter,
)
from .graphbfn import (
    GRAPHBFN_CHANNELS,
    GRAPHBFN_CHANNEL_DOMAINS,
    GRAPHBFN_CONFIG_HASH_HIER,
    GRAPHBFN_CONFIG_HASH_ICLR,
    GRAPHBFN_CONFIG_VERSION,
    GRAPHBFN_CONDITION_KINDS,
    GRAPHBFN_NATIVE_STATES_MAXSIZE,
    GRAPHBFN_NUM_STEPS_DEFAULT,
    GraphBFNAdapter,
    GraphBFNCapabilities,
    default_graphbfn_adapter,
    graphbfn_resolve_weights_path,
    torch_is_available as graphbfn_torch_is_available,
)
from .integrators import (
    INTEGRATOR_REGISTRY,
    AMEDSolverIntegrator,
    DormandPrinceRK45Integrator,
    DPMSolverIntegrator,
    HeunIntegrator,
    IntegratorProtocol,
    RK4Integrator,
    UniPCIntegrator,
    build_integrator,
)
from .karras_preconditioner import KarrasPreconditioner
from .self_flow import (
    SELF_FLOW_CHANNEL_DOMAINS,
    SELF_FLOW_CHANNELS,
    SELF_FLOW_CONFIG_HASH,
    SELF_FLOW_CONFIG_VERSION,
    SELF_FLOW_MECHANISM_ID,
    SELF_FLOW_NUM_STEPS_DEFAULT,
    SELF_FLOW_STATE_SHAPE,
    SelfFlowAdapter,
    SelfFlowCapabilities,
    default_self_flow_adapter,
    self_flow_resolve_weights_path,
)
from .reference_flowa import (
    REFERENCE_FLOWA_CHANNEL_DOMAINS,
    REFERENCE_FLOWA_CHANNELS,
    ReferenceFlowAAdapter,
)
from .synthetic import (
    ALL_SYNTHETIC_CHANNELS,
    CONTINUOUS_CHANNELS,
    DISCRETE_CHANNELS,
    MIXED_CHANNELS,
    SyntheticContinuousAdapter,
    SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter,
    SyntheticUnsupportedAdapter,
)
from .toy_gaussian import (
    GaussianAdapterCapabilities,
    ToyGaussianAdapter,
    default_toy_gaussian_adapter,
    gauss_score,
)
from .toy_linear import (
    CHANNEL_DOMAINS as TOY_LINEAR_CHANNEL_DOMAINS,
)
from .toy_linear import (
    NATIVE_CONFIG_HASH as TOY_LINEAR_CONFIG_HASH,
)
from .toy_linear import (
    NATIVE_CONFIG_VERSION as TOY_LINEAR_CONFIG_VERSION,
)
from .toy_linear import (
    SUPPORTED_CHANNELS as TOY_LINEAR_CHANNELS,
)
from .toy_linear import (
    ToyLinearAdapter,
    default_toy_linear_adapter,
)
from .twodim_fm import (
    AUDIT_RESTART_BLEND,
    ERR_INTEGRATOR_OVERFLOW,
    TWODIM_FM_CHANNELS,
    TWODIM_FM_CONFIG_HASH,
    TWODIM_FM_CONFIG_VERSION,
    TwoDimFMAdapter,
    default_twodim_fm_adapter,
)
from .mnist_fm import (
    MNIST_FM_CHANNELS,
    MNIST_FM_CHANNEL_DOMAINS,
    MNIST_FM_CONFIG_HASH,
    MNIST_FM_CONFIG_VERSION,
    MnistFMCapabilities,
    MnistFmAdapter,
    default_mnist_fm_adapter,
)
from .rectified_flow_cifar import (
    RF_CIFAR_CHANNELS,
    RF_CIFAR_CONFIG_HASH,
    RF_CIFAR_CONFIG_VERSION,
    RF_CIFAR_STATE_SHAPE,
    RectifiedFlowCIFARAdapter,
    RectifiedFlowCIFARCapabilities,
    default_rectified_flow_cifar_adapter,
    rectified_flow_cifar_resolve_weights_path,
)
from .stochastic_fm import StochasticFMAdapter
from .wan2_2_video import (
    AUDIT_WAN22_FORWARD_NOISE_APPLIED,
    AUDIT_WAN22_OBSERVED,
    AUDIT_WAN22_RESTART_BLEND,
    WAN22_A14B_STATE_SHAPE,
    WAN22_CHANNELS,
    WAN22_CHANNEL_DOMAINS,
    WAN22_CONFIG_HASH,
    WAN22_CONFIG_VERSION,
    WAN22_MECHANISM_ID,
    WAN22_NUM_STEPS_DEFAULT,
    WAN22_SOLVER_HEUN,
    WAN22_TI2V5B_STATE_SHAPE,
    Wan22VideoAdapter,
    Wan22VideoAdapterCapabilities,
    default_wan22_video_flowmatchingodeadapter,
    wan22_resolve_weights_path,
)

# ---------------------------------------------------------------------------
# Adapter registry (P2-9)
# ---------------------------------------------------------------------------

#: Family name -> zero-arg default factory. Mirrors INTEGRATOR_REGISTRY
#: (integrators.py:1110). Values are callables, not instances, so
#: importing this module never constructs an adapter or touches weights.
ADAPTER_REGISTRY: dict[str, Any] = {
    "flowmol3": default_flowmol3_adapter,
    "flowmol3_v2": default_flowmol3adapter,
    "graphbfn": default_graphbfn_adapter,
    "hidream_i1": default_hidream_i1_adapter,
    "lineageflow": default_lineageflow_adapter,
    "lumina_image_2_0": default_lumina_image_2_0_adapter,
    "mnist_fm": default_mnist_fm_adapter,
    "protbfn_abbfn": default_protbfnabbfn_adapter,
    "rectified_flow_cifar": default_rectified_flow_cifar_adapter,
    "self_flow": default_self_flow_adapter,
    "toy_gaussian": default_toy_gaussian_adapter,
    "toy_linear": default_toy_linear_adapter,
    "twodim_fm": default_twodim_fm_adapter,
    "wan2_2_video": default_wan22_video_flowmatchingodeadapter,
}


def build_adapter(family: str, **kwargs: Any) -> Any:
    """Construct the default adapter for ``family``.

    Raises ``KeyError`` naming the known families — same fail-closed shape as
    ``build_integrator`` (integrators.py:1136).
    """
    if family not in ADAPTER_REGISTRY:
        raise KeyError(
            f"unknown adapter family {family!r}; "
            f"known: {sorted(ADAPTER_REGISTRY)}"
        )
    return ADAPTER_REGISTRY[family](**kwargs)


# Naming aliases (P2-9): the canonical form is ``default_<family>_adapter``.
# ``default_flowmol3adapter`` is one character from ``default_flowmol3_adapter``
# but builds a DIFFERENT adapter (v2 vs the v1 placeholder); the aliases below
# are unambiguous. Originals are retained for back-compat.
default_flowmol3_v2_adapter = default_flowmol3adapter
default_protbfn_abbfn_adapter = default_protbfnabbfn_adapter
default_wan2_2_video_adapter = default_wan22_video_flowmatchingodeadapter
