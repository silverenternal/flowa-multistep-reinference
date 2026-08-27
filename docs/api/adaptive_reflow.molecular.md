# `adaptive_reflow.molecular`

Concrete molecule layer: pocket-conditioned 3D flow matching channel
vocabulary, stratification, RMS-preserving coordinate mixer, and the
GNINA / PoseBusters / QED / ADMET `Evaluator` implementations.

The page below drills into each split file inside the `molecular`
subpackage rather than stopping at the top-level `__init__.py`
re-exports, so internal symbols (channel vocabulary entries, stratification
helpers, mixer helpers) that are not re-exported publicly still show up
in the rendered reference.

## `adaptive_reflow.molecular.bundle`

`MoleculeRoundResultBundle` -- the concrete molecule atomic source
bundle + per-channel source-round validator. Canonical home of the
molecule-aware `RoundResultBundle` re-exported from `contracts.bundle`.

::: adaptive_reflow.molecular.bundle
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.channels`

`MOLECULE_CHANNELS` tuple + the four `*ChannelRef` NewType aliases +
the closed `MoleculeChannel` enum.

::: adaptive_reflow.molecular.channels
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.domain`

`MOLECULE_DOMAIN_BY_CHANNEL` fallback table. Per-channel domain
resolution is normally each adapter's responsibility via
`AdapterCapabilities.channel_domains`; this fallback table remains
for molecule-aware callers.

::: adaptive_reflow.molecular.domain
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.envelope`

`MoleculeEnvelopeLayer` + `MoleculeEnvelopeManifest` -- the concrete
molecule implementation of the universal `EnvelopeCriterion` Protocol.

::: adaptive_reflow.molecular.envelope
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.stratification`

`MoleculeStratum` + `MoleculeStratumAssignment` +
`dominance_ratio` + `cross_stratum_mix_rejected`.

::: adaptive_reflow.molecular.stratification
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.mixer`

`EqualRmsCoordinateMixer` -- the concrete `RestartMixer` Protocol
implementation for molecule coordinates. Also re-exports the
back-compat `adaptive_reflow_memory_restart_coords` shim.

::: adaptive_reflow.molecular.mixer
    options:
      members: true
      show_source: true

## `adaptive_reflow.molecular.calibration_protocols`

Concrete `Evaluator` implementations for the four molecule evaluator
arms (GNINA, PoseBusters, QED, ADMET) plus their factory helpers.

::: adaptive_reflow.molecular.calibration_protocols
    options:
      members: true
      show_source: true