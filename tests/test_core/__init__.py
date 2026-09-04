"""Tests for the ``adaptive_reflow.core`` framework-core glue.

This subpackage exercises the four core-glue modules that the
Wave 24 MUST-3 partial-completion wave ships:

* :mod:`tests.test_core.test_ckpt_loader` — HF + GitHub weight
  loader shim.
* :mod:`tests.test_core.test_diffusers_wrapper` —
  diffusers-style forward wrapper for DiT-family models.
* :mod:`tests.test_core.test_graph_wrapper` — DGL-style graph
  wrapper for graph-based models.
* :mod:`tests.test_core.test_vae_decoder` — latent ↔ pixel
  VAE decoder (synthetic fallback + lazy diffusers bridge).

All tests are stdlib + numpy only (CPU-only sandboxes). The
diffusers / torch-dependent branches are exercised via mock
modules that implement just enough of the surface to satisfy
the wrapper without requiring real :mod:`torch` /
:mod:`diffusers` installs.
"""
from __future__ import annotations

__all__: tuple[str, ...] = ()
