# `adaptive_reflow.adapters`

Concrete `FlowMatchingODEAdapter` implementations. The synthetic
fixtures live here (not in `tests/`) so external parity harnesses can
import them too.

The page below drills into each split file inside the `adapters`
subpackage rather than stopping at the top-level `__init__.py`
re-exports, so internal symbols (per-adapter `*_CHANNELS` constants,
`default_*_adapter` factory helpers, registry-entry helpers) that are
not re-exported publicly still show up in the rendered reference.

## `adaptive_reflow.adapters.synthetic`

The synthetic adapter fixtures (`SyntheticContinuousAdapter`,
`SyntheticDiscreteAdapter`, `SyntheticMixedChannelAdapter`,
`SyntheticUnsupportedAdapter`) + their `*_CHANNELS` channel-vocabulary
constants. Used by `tests/` + external parity harnesses.

::: adaptive_reflow.adapters.synthetic
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.toy_gaussian`

`ToyGaussianAdapter` -- the second non-molecule domain
(`GaussianAdapterCapabilities`, `gauss_score`,
`default_toy_gaussian_adapter`). The worked example for adapters
that target a non-molecule domain.

::: adaptive_reflow.adapters.toy_gaussian
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.toy_linear`

`ToyLinearAdapter` -- the legacy worked example. Quarantined; the
`DOMAIN_BY_CHANNEL` constant that used to live here has been removed
in favour of `AdapterCapabilities.channel_domains`.

::: adaptive_reflow.adapters.toy_linear
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.reference_flowa`

`ReferenceFlowAAdapter` -- the reference FlowA adapter, pinned to the
upstream `ReferenceFlowA` capability shape. Hosts the
`REFERENCE_FLOWA_CHANNELS` / `REFERENCE_FLOWA_CHANNEL_DOMAINS` constants.

::: adaptive_reflow.adapters.reference_flowa
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.flowmol3`

`FlowMol3Adapter` -- the pinned-commit FlowMol-3 adapter, with its
candidate-registry entry + factory helper.

::: adaptive_reflow.adapters.flowmol3
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.twodim_fm`

2D rectified-flow adapter. Opt-in via the `[flow_matching]` extra
dependency.

::: adaptive_reflow.adapters.twodim_fm
    options:
      members: true
      show_source: true

## `adaptive_reflow.adapters.twodim_fm_train`

Offline trainer for the 2D rectified-flow adapter's velocity-field
MLP. Opt-in via the `[flow_matching]` extra dependency.

::: adaptive_reflow.adapters.twodim_fm_train
    options:
      members: true
      show_source: true