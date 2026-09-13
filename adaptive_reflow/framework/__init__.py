"""Protocol surfaces and adapter-conformance machinery (Wave 11, JMAA theory-driven).

This package declares the abstract Protocol interfaces that adapters and
algorithm-layer implementations conform to. It is the *contract* layer:
adapters satisfy conformance structurally (via :func:`assert_adapter_compliance`)
without needing a base class.

Most call sites should import from :mod:`adaptive_reflow.framework.interfaces`
directly. This ``__init__`` is a thin re-export layer for convenience.
"""

from adaptive_reflow.framework.interfaces import (  # noqa: F401
    ChannelwiseBlender,
    ChannelwiseMemoryFractionPolicy,
    IntegratorProtocol,
    MergeOperatorProtocol,
    MissingProtocolError,
    NoiseInjectionProtocol,
    PosteriorEvaluator,
    SelectionRatioWitness,
    SheetSchedulerProtocol,
    Theorem1Statement,
    Theorem1StatementChecker,
    assert_adapter_compliance,
    emit_theorem1_statement,
    implements,
)

__all__ = [
    "ChannelwiseBlender",
    "ChannelwiseMemoryFractionPolicy",
    "IntegratorProtocol",
    "MergeOperatorProtocol",
    "MissingProtocolError",
    "NoiseInjectionProtocol",
    "PosteriorEvaluator",
    "SelectionRatioWitness",
    "SheetSchedulerProtocol",
    "Theorem1Statement",
    "Theorem1StatementChecker",
    "assert_adapter_compliance",
    "emit_theorem1_statement",
    "implements",
]
