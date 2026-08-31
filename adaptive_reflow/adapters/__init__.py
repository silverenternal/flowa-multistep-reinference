"""Adaptive reflow — model glue (DTB-G1 + DTB-G2).

Concrete :class:`FlowMatchingODEAdapter` implementations. The synthetic
fixtures live here (not in ``tests/``) so external parity harnesses can
import them too.
"""
from .flowmol3 import (
    FLOWMOL3_CHANNEL_DOMAINS,
    FLOWMOL3_CHANNELS,
    FlowMol3Adapter,
    FlowMol3Capabilities,
    default_flowmol3_adapter,
    flowmol3_registry_entry,
)
from .protbfnabbfnadapter import (
    AMINO_ACID_CATEGORICAL,
    PROTBFN_ABBFN_CHANNELS,
    PROTBFN_ABBFN_CHANNEL_DOMAINS,
    PROTBFN_ABBFN_CONFIG_HASH,
    PROTBFN_ABBFN_STATE_SHAPE,
    ProtBFNAbBFNAdapter,
    ProtBFNAbBFNCapabilities,
    default_protbfnabbfn_adapter,
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
