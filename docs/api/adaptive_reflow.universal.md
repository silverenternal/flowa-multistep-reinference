# `adaptive_reflow.universal`

Model-family-agnostic kernel: Flow Matching ODE re-inference engine +
adapter / evaluator / mixer Protocols + envelope dataclasses. Any model
family (molecular pocket-conditioned 3D flow matching, graph flow,
image flow, sequence flow) can implement these abstractions without
ever reaching into molecule-specific code.

The page below drills into each Protocol-bearing file inside the
`universal` subpackage rather than stopping at the top-level
`__init__.py` re-exports, so internal symbols (Protocol method
signatures, validator helpers, error sentinels) that are not
re-exported publicly still show up in the rendered reference.

## `adaptive_reflow.universal.adapter`

`FlowMatchingODEAdapter` Protocol + `AdapterCapabilities` (with
per-adapter `channel_domains`). Hosts the canonical
`validate_capabilities` / `validate_condition_delta` /
`validate_integrator_trace` / `validate_state_bundle` helpers.

::: adaptive_reflow.universal.adapter
    options:
      members: true
      show_source: true

## `adaptive_reflow.universal.state`

`TensorRef`, `StateBundle`, `ODEConditionDelta`, `ODEIntegratorTrace`
pure-data carriers (no molecule-specific channel names).

::: adaptive_reflow.universal.state
    options:
      members: true
      show_source: true

## `adaptive_reflow.universal.envelope`

`EnvelopeCriterion` + `EnvelopeClassification` (no molecule-specific
observable names). The model-family-agnostic counterpart to
`molecular.envelope`.

::: adaptive_reflow.universal.envelope
    options:
      members: true
      show_source: true

## `adaptive_reflow.universal.evaluator`

`Evaluator` Protocol (no GNINA / QED / ADMET / PoseBusters
assumptions). Any model family can satisfy this Protocol without
pulling in chemistry-specific code.

::: adaptive_reflow.universal.evaluator
    options:
      members: true
      show_source: true

## `adaptive_reflow.universal.mixer`

`RestartMixer` Protocol (no `(N, 3)` coordinate-shape hardcoding).
Satisfied by `molecular.mixer.EqualRmsCoordinateMixer` for the
molecule family.

::: adaptive_reflow.universal.mixer
    options:
      members: true
      show_source: true

## `adaptive_reflow.universal.validators`

Single point of entry for all universal validators -- the fail-closed
gate for `EnvelopeCriterion` / `Evaluator` / `RestartMixer` Protocol
implementations.

::: adaptive_reflow.universal.validators
    options:
      members: true
      show_source: true