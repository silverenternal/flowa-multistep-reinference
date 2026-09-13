"""``adaptive_reflow.core`` — framework-core glue for adapters.

This subpackage centralises the four abstract glue patterns
that ``todo/PHASE-3-glue-layer-improvement.md`` §"Example glue
patterns to extract to framework core" lists as the MUST-3
prerequisite for D.1 (adapter line count ≤500):

* **HF + GitHub weight loader shim** —
  :mod:`adaptive_reflow.core.ckpt_loader` resolves candidate
  paths, sniffs checkpoint formats, and lazy-loads
  ``torch`` state dicts.
* **Diffusers-style forward wrapper** —
  :mod:`adaptive_reflow.core.diffusers_wrapper` wraps the
  canonical ``DiT.forward(x, t, y, **kwargs)`` contract with
  NumPy ↔ torch conversion, classifier-free-guidance
  duplicate-and-interpolate, and a try-import pipeline
  factory.
* **DGL-style graph wrapper** —
  :mod:`adaptive_reflow.core.graph_wrapper` defines the
  graph-shaped payload (:class:`GraphPayload`,
  :class:`GraphBatch`), the restart-blend helper
  (:func:`blend_graph_features`), and the lazy DGL/PyG
  bridge.
* **VAE latent ↔ pixel decoder** —
  :mod:`adaptive_reflow.core.vae_decoder` ships the synthetic
  byte-stable VAE fallback plus the lazy
  :class:`DiffusersVAEWrapper` over :class:`diffusers.AutoencoderKL`.

All four modules are stdlib + numpy at module level; ``torch``
and the model-specific packages (``diffusers``,
``transformers``, ``dgl``, ``torch_geometric``) are imported
lazily inside the wrappers that need them so the framework
never requires them at import time.

Adoption footprint today: this subpackage ships zero
per-adapter imports (the per-adapter refactor is deferred to a
follow-up wave per the MUST-3 contract — blocked on all 4
RANKING adapters existing). The public surface is
byte-stable so future adapter refactors can adopt without
breaking the digests.

Wave 24 MUST-3 partial completion: modules + tests land in
this wave; the per-adapter refactor (Kanzi, FreqFlow, MM-FM,
Self-Flow, HiDream, Hidream-Lumina, Kanzi variants) ships in
a follow-up wave that consumes the public surface defined
here.

Subpackage surface
------------------

``adaptive_reflow.core`` re-exports the four submodules so
``from adaptive_reflow.core import ckpt_loader`` resolves the
module. Each module's public surface is also re-exported
under ``adaptive_reflow.core`` for callers that prefer the
flat namespace:

>>> from adaptive_reflow.core import (
...     LatentShape,
...     SyntheticVAE,
...     GraphPayload,
...     CheckpointLoader,
...     DiffusersForwardWrapper,
... )
"""
from __future__ import annotations

# Re-export the four submodule names so callers can do
# ``from adaptive_reflow.core import ckpt_loader`` /
# ``from adaptive_reflow.core.ckpt_loader import ...``.
from adaptive_reflow.core import (
    ckpt_loader,
    diffusers_wrapper,
    graph_wrapper,
    vae_decoder,
)

# Flat re-exports — every adapter that adopts the framework-core
# glue imports from ``adaptive_reflow.core`` directly so the
# subpackage becomes the canonical "framework-core glue"
# namespace.
from adaptive_reflow.core.ckpt_loader import (
    CheckpointFormat,
    CheckpointLoader,
    CheckpointMetadata,
    load_checkpoint_metadata,
    load_state_dict_strict_safe,
    resolve_candidate_paths,
    sniff_checkpoint_format,
)
from adaptive_reflow.core.diffusers_wrapper import (
    DiffusersDType,
    DiffusersForwardResult,
    DiffusersForwardSignature,
    DiffusersForwardWrapper,
    DiffusersPipelineFactory,
    DiffusersPipelineSpec,
    diffusers_postprocess,
    diffusers_preprocess,
)
from adaptive_reflow.core.graph_wrapper import (
    DEFAULT_EDGE_FEATURE_DIM,
    DEFAULT_GRAPH_FEATURE_DIM,
    DEFAULT_NODE_FEATURE_DIM,
    DGLGraphBridge,
    EdgeIndexDType,
    GraphBackendProbe,
    GraphBatch,
    GraphPayload,
    blend_graph_features,
    empty_graph_payload,
    merge_graph_batches,
    probe_graph_backends,
    random_graph_payload,
    split_graph_batch,
)
from adaptive_reflow.core.vae_decoder import (
    DEFAULT_VAE_DOWNSAMPLE,
    LATENT_SHAPE_DCAE_256,
    LATENT_SHAPE_FLUX_VAE_1024,
    LATENT_SHAPE_HIDREAM_1024,
    LATENT_SHAPE_SD_VAE_256,
    VAE_FAMILY_DCAE,
    VAE_FAMILY_FLUX_VAE,
    VAE_FAMILY_HIDREAM,
    VAE_FAMILY_SD_VAE,
    VAE_FAMILY_SYNTHETIC,
    DiffusersVAEResult,
    DiffusersVAEWrapper,
    LatentShape,
    SyntheticVAE,
    SyntheticVAEWeights,
    VAEDType,
    default_synthetic_vae,
    latent_to_pixel_shape,
    pixel_to_latent_shape,
    vae_for_family,
)

__all__ = [
    # Submodules.
    "ckpt_loader",
    "diffusers_wrapper",
    "graph_wrapper",
    "vae_decoder",
    # ckpt_loader surface.
    "CheckpointFormat",
    "CheckpointLoader",
    "CheckpointMetadata",
    "load_checkpoint_metadata",
    "load_state_dict_strict_safe",
    "resolve_candidate_paths",
    "sniff_checkpoint_format",
    # diffusers_wrapper surface.
    "DiffusersDType",
    "DiffusersForwardResult",
    "DiffusersForwardSignature",
    "DiffusersForwardWrapper",
    "DiffusersPipelineFactory",
    "DiffusersPipelineSpec",
    "diffusers_postprocess",
    "diffusers_preprocess",
    # graph_wrapper surface.
    "DEFAULT_EDGE_FEATURE_DIM",
    "DEFAULT_GRAPH_FEATURE_DIM",
    "DEFAULT_NODE_FEATURE_DIM",
    "DGLGraphBridge",
    "EdgeIndexDType",
    "GraphBackendProbe",
    "GraphBatch",
    "GraphPayload",
    "blend_graph_features",
    "empty_graph_payload",
    "merge_graph_batches",
    "probe_graph_backends",
    "random_graph_payload",
    "split_graph_batch",
    # vae_decoder surface.
    "DEFAULT_VAE_DOWNSAMPLE",
    "DiffusersVAEResult",
    "DiffusersVAEWrapper",
    "LATENT_SHAPE_DCAE_256",
    "LATENT_SHAPE_FLUX_VAE_1024",
    "LATENT_SHAPE_HIDREAM_1024",
    "LATENT_SHAPE_SD_VAE_256",
    "LatentShape",
    "SyntheticVAE",
    "SyntheticVAEWeights",
    "VAEDType",
    "VAE_FAMILY_DCAE",
    "VAE_FAMILY_FLUX_VAE",
    "VAE_FAMILY_HIDREAM",
    "VAE_FAMILY_SD_VAE",
    "VAE_FAMILY_SYNTHETIC",
    "default_synthetic_vae",
    "latent_to_pixel_shape",
    "pixel_to_latent_shape",
    "vae_for_family",
]
