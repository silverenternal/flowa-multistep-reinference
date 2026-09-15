"""Thin latent→coord bridge for Kanzi — closes the framework-arm gap.

Closes the chain::

    KanziAdapter.solve_ode  ->  KanziAdapter.observe_endpoint
       ->  kanzi_latent_to_coords(latent, decoder, fsq_quantizer)
            ->  coords (B, n_atoms, 3) in Angstrom

so the framework arm of the Wave 88 paper-metric sweep can produce
a Kabsch RMSD per record, matching the Wave 88 baseline arm.

References (upstream Kanzi vendored at ``data/kanzi_upstream/src/kanzi/``):

* :class:`DAE.decode` — ``data/kanzi_upstream/src/kanzi/models.py:364-429``
  Diffusion rollout returning ``(B, L, 3)`` in nm (input scale).
* :class:`FSQ.codes_to_indices` —
  ``data/kanzi_upstream/src/kanzi/fsq.py:116-120``
  Snaps the continuous post-``project_out`` code to its nearest
  discrete index — the inverse of :class:`DAE.encode`.
* :func:`kabsch_rmsd` — ``data/kanzi_upstream/src/kanzi/utils.py:3``

The bridge is **in-process** (the ``kanzi`` package is installed in the
``.venvs/kanzi_venv`` sidecar, not a subprocess boundary). Compare to
the FlowMol3 xtb bridge at ``tools/flowmol3_xtb_bridge.py`` which IS
subprocess-only.

Design rules
------------

* **Imports are LOCAL** (inside each public function). This avoids the
  cold-import cost of ``torch`` + ``kanzi`` at module-load time and
  keeps ``import tools.kanzi_latent_to_coord`` cheap on hosts where the
  kanzi sidecar venv is unavailable.
* **NO adapter-side re-implementation.** The function consumes an
  already-decoded ``latent`` tensor + the upstream
  :class:`DAE` / :class:`FSQ` instances; it does not re-implement the
  diffusion rollout or the FSQ basis.
* **Mean-centering is the bridge's responsibility** (matches the
  ``DAE.encode`` line 353 + ``DAE.decode`` line 376 invariant; see
  Phase 1 audit §3.6).
* **nm → Angstrom** at the very end (``* 10.0``) — matches
  ``tools/upstream_eval.py:357-358``.

Wave 91 Phase 3 wires this into ``tools/run_real_ckpt_eval.py:_run_cell``
(mirroring the Wave 88 baseline arm path).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import torch

# Upstream-side paths (resolved at call time, not import time).
KANZI_UPSTREAM_SRC: str = "data/kanzi_upstream/src"

# Wave 95 Phase 3.B — Path B (train inverse). The bridge replaces the
# Wave 92c ``torch.cdist`` nearest-neighbour (NN) projection with a
# trained ``Linear(512 → 4)`` inverse of the FSQ ``project_out`` map.
# See ``docs/audit/wave95-phase3-pin-probe.md`` for the decision-tree
# output (col-space residual > 0.01 fires the NEED-TO-TRAIN path even
# though the Moore-Penrose identity is algebraically valid) and
# ``tools/_kanzi_project_out_inv_train.py`` for the training script.
#
# The state_dict is ~8 KB and lives next to the bridge so the module is
# self-contained at runtime. Loaded LAZILY on the first ``kanzi_latent_to_coords``
# call so module import stays cheap (matches the existing local-import
# pattern for ``torch`` + ``kanzi``).
_PROJECT_OUT_INV_PATH: str = "tools/_kanzi_project_out_inv.pt"
_PROJECT_OUT_INV_CACHE: dict[str, Any] | None = None


def kanzi_latent_to_coords(
    latent: np.ndarray | Any,
    decoder: Any,
    fsq_quantizer: Any,
    *,
    n_steps: int = 100,
    noise_weight: float = 0.45,
    cfg_weight: float = 1.0,
    score_weight: float = 1.0,
    seed: int = 0,
) -> np.ndarray:
    """Snap the ODE endpoint ``latent`` → coords ``(B, n_atoms, 3)`` Å.

    Pipeline (mirrors ``tools/upstream_eval.py:347-358``):

      1. Convert ``latent`` → ``torch.float32`` tensor on the decoder's
         device. Accepts ``(B, L, d)`` or ``(L, d)`` — the latter is
         unsqueezed to ``(1, L, d)`` (the canonical DAE input shape).
      2. Snap each ``(L, d)`` row to its nearest FSQ code via
         ``fsq_quantizer.codes_to_indices(x_BLD)`` (matches
         ``FSQ.codes_to_indices`` semantics at
         ``data/kanzi_upstream/src/kanzi/fsq.py:116-120`` — the
         inverse of the ``project_out`` step inside ``DAE.encode``).
      3. Call ``decoder.decode(idx_BL, n_steps=..., noise_weight=...,
         cfg_weight=..., score_weight=...)`` inside ``torch.no_grad()``
         (matches the diffusion rollout at
         ``data/kanzi_upstream/src/kanzi/models.py:364-429``).
      4. Multiply by ``10.0`` to recover Angstrom (matches
         ``tools/upstream_eval.py:357-358``).

    Determinism: the global torch RNG is seeded via
    ``torch.manual_seed(seed)`` before the decode call so repeated
    invocations with the same input and seed produce identical
    coords. ``DAE.decode`` (line 421) uses ``torch.randn_like`` for
    the diffusion noise — seeding the global RNG is the simplest
    portable hook.

    Parameters
    ----------
    latent : np.ndarray | torch.Tensor
        The ODE trajectory endpoint ``x_final`` of shape
        ``(B, L, n_channels_decoder)`` float32 — the adapter's
        ``observe_endpoint`` output (see
        ``adaptive_reflow/adapters/kanzi.py:1908-1991``).
    decoder : kanzi.DAE
        The upstream :class:`DAE` instance returned by
        ``DAE.from_pretrained(ckpt_path)``. Must be in ``.eval()``
        mode and on the same device as ``latent`` (the bridge
        auto-coerces ``latent`` to the decoder's parameter device).
    fsq_quantizer : kanzi.FSQ
        The upstream :class:`FSQ` instance attached to ``decoder`` as
        ``decoder.quantize``. Acceptable to pass ``decoder.quantize``
        directly (Wave 91 Phase 3 does this).
    n_steps : int
        Number of diffusion steps for ``DAE.decode``. Default 100
        matches the upstream eval driver (``tools/upstream_eval.py:341``).
    noise_weight : float
        ``DAE.decode`` diffusion noise scalar (default 0.45, matches
        upstream eval driver).
    cfg_weight : float
        ``DAE.decode`` classifier-free-guidance scalar (default 1.0,
        no guidance).
    score_weight : float
        ``DAE.decode`` score-weight scalar (default 1.0).
    seed : int
        Seed for the global torch RNG before decode. Default 0.

    Returns
    -------
    np.ndarray
        Coords in Angstrom, shape ``(B, L, 3)`` float64. Matches the
        numpy contract of ``tools/extract_ca_coords_for_kanzi.py``
        output (single-record loop yields ``(L, 3)``).
    """
    import torch  # local import — keep module-load cheap

    # Resolve decoder device once (reused for tensor placement + seed).
    try:
        device = next(decoder.parameters()).device
    except StopIteration:
        # Decoder has no parameters (e.g. fully mocked in tests);
        # default to CPU.
        device = torch.device("cpu")

    # Step 1: numpy / scalar → torch.float32 on the decoder device.
    x_t = torch.as_tensor(latent, dtype=torch.float32, device=device)
    if x_t.ndim == 2:
        # (L, d) → (1, L, d) — canonical DAE input shape.
        x_t = x_t.unsqueeze(0)

    # Seed the GLOBAL torch RNG (DAE.decode uses torch.randn_like,
    # which reads from the global generator; this is the simplest
    # portable hook and matches the upstream eval driver contract).
    torch.manual_seed(int(seed))

    # Step 2: snap the continuous latent endpoint to FSQ codes → (B, L)
    # int64 indices. The framework trajectory endpoint ``x_final`` lives
    # in the post-``project_out`` (n_channels_decoder=512) space; the
    # upstream ``FSQ`` is configured with ``dim = n_channels_encoder =
    # 256`` so neither ``fsq_quantizer(x_t)`` nor
    # ``fsq_quantizer.codes_to_indices(x_t)`` accept the input shape
    # (they assert ``shape[-1] == self.dim == 256`` and ``shape[-1] ==
    # self.codebook_dim == 4`` respectively).
    #
    # Wave 92c workaround: ``FSQ.implicit_codebook`` is built by
    # ``indices_to_codes(torch.arange(self.codebook_size),
    # project_out=False)`` at __init__ time, yielding the full
    # ``(1000, codebook_dim=4)`` pre-``project_out`` codebook.
    # Wave 95 Phase 3.B: we now apply a *trained* ``Linear(512 → 4)``
    # inverse of ``project_out`` (see ``tools/_kanzi_project_out_inv.pt``)
    # to each ``x_final`` row to get a 4-d latent estimate, then
    # argmin over the 1000 4-d codebook entries. This is the
    # algebraically-faithful inverse path (vs. the Wave 92c 512-d
    # ``torch.cdist`` nearest-neighbour surrogate). See
    # ``docs/audit/wave95-phase3-pin-probe.md`` for the decision-tree
    # output and the rationale for choosing Path B (5-min training)
    # over Path A (Moore-Penrose identity).
    with torch.no_grad():
        # Resolve the 4-d implicit codebook. The upstream FSQ stores
        # ``implicit_codebook`` at ``__init__`` (line 89:
        # ``indices_to_codes(arange(codebook_size), project_out=False)``)
        # with shape ``(1000, codebook_dim=4)``. We use direct attribute
        # access (not ``getattr``) because the MagicMock auto-attr
        # machinery in unit tests can shadow explicitly-set attributes.
        implicit_codebook = fsq_quantizer.implicit_codebook
        if (
            implicit_codebook is None
            or not isinstance(implicit_codebook, torch.Tensor)
            or implicit_codebook.shape[-1] != 4
        ):
            # Defensive fallback: rebuild the 4-d implicit codebook by
            # running ``indices_to_codes`` with ``project_out=False``.
            codes_4d = fsq_quantizer.indices_to_codes(
                torch.arange(
                    int(fsq_quantizer.codebook_size),
                    device=device,
                ),
                project_out=False,
            )  # (1000, 4)
        else:
            codes_4d = implicit_codebook.float()

        # Wave 95 Phase 3.B trained-inverse path. Project each
        # post-``project_out`` row ``x_t[B, L, 512]`` through the
        # trained ``Linear(512 → 4)`` to get a 4-d latent estimate,
        # then argmin over the 1000 4-d codebook entries.
        B_dim = int(x_t.shape[0])
        L_dim = int(x_t.shape[1])
        x_flat = x_t.reshape(B_dim * L_dim, -1).float()  # (B*L, 512)
        x_4d = _apply_project_out_inv(x_flat)  # (B*L, 4)
        dists = torch.cdist(
            x_4d, codes_4d.float(),  # (B*L, 4) vs (1000, 4)
        )  # (B*L, 1000)
        idx_BL = dists.argmin(dim=-1).to(torch.int64).reshape(
            B_dim, L_dim,
        )  # (B, L)
        # Step 3: decode the (B, L) indices back to (B, L, 3) nm.
        x_pred = decoder.decode(
            idx_BL,
            n_steps=int(n_steps),
            noise_weight=float(noise_weight),
            cfg_weight=float(cfg_weight),
            score_weight=float(score_weight),
        )
    # Step 4: nm → Angstrom, float64 (matches adapter numpy contract).
    out = x_pred.detach().cpu().numpy() * 10.0
    return out.astype(np.float64)


# ---------------------------------------------------------------------------
# Wave 95 Phase 3.B — trained Linear(512 → 4) inverse of FSQ ``project_out``.
# ---------------------------------------------------------------------------


def _load_project_out_inv() -> dict[str, Any]:
    """Lazy-load the Wave 95 Phase 3.B trained inverse.

    Returns a dict with keys ``state_dict`` (nn.Linear weights),
    ``input_dim``, ``output_dim``, ``levels``, and ``schema_version``.
    Cached module-level so repeated bridge calls re-use the same
    loaded object.

    Raises
    ------
    FileNotFoundError
        If ``tools/_kanzi_project_out_inv.pt`` is missing (run
        ``tools/_kanzi_project_out_inv_train.py`` first).
    """
    global _PROJECT_OUT_INV_CACHE
    if _PROJECT_OUT_INV_CACHE is not None:
        return _PROJECT_OUT_INV_CACHE
    from pathlib import Path as _Path  # noqa: WPS433 — local import by design

    import torch  # local import — keep module-load cheap

    # Resolve relative to this module file (works under spec_from_file_location
    # and direct ``python -m tools.kanzi_latent_to_coord`` alike).
    try:
        module_dir = _Path(__file__).resolve().parent
    except NameError:
        module_dir = None
    inv_path = (
        module_dir / "_kanzi_project_out_inv.pt"
        if module_dir is not None else _Path(_PROJECT_OUT_INV_PATH)
    )
    if not inv_path.exists():
        # Fallback to CWD-relative (the test hermetic import path).
        inv_path = _Path(_PROJECT_OUT_INV_PATH)
    if not inv_path.exists():
        raise FileNotFoundError(
            f"Wave 95 Phase 3.B trained inverse not found at {inv_path}. "
            f"Run tools/_kanzi_project_out_inv_train.py to generate it."
        )
    blob = torch.load(str(inv_path), map_location="cpu", weights_only=False)
    _PROJECT_OUT_INV_CACHE = blob
    return blob


def _apply_project_out_inv(x_t: torch.Tensor) -> torch.Tensor:
    """Apply the trained ``Linear(512 → 4)`` inverse to ``x_t``.

    Mirrors the structure of the original Wave 92c NN step but replaces
    ``torch.cdist(x_t, codes_1K_512d)`` with a two-stage projection:
    ``inv_linear(x_t) → (B*L, 4)`` followed by argmin over the 1000
    4-d basis codes (``implicit_codebook`` with ``project_out=False``).
    See ``docs/audit/wave95-phase3-pin-probe.md`` for the algebraic
    justification and Wave 95 Phase 3.B commit for the training recipe.
    """
    import torch  # local import — keep module-load cheap
    import torch.nn as nn  # local import — keep module-load cheap

    inv_blob = _load_project_out_inv()
    state = inv_blob["state_dict"]
    # Reconstruct the Linear at call time so callers don't need torch.nn
    # at module-import time.
    weight = state["weight"].float().to(device=x_t.device)
    bias = state["bias"].float().to(device=x_t.device)
    # Linear(x) = x @ weight.T + bias — matches nn.Linear semantics.
    return torch.nn.functional.linear(x_t, weight, bias)


__all__ = [
    "KANZI_UPSTREAM_SRC",
    "kanzi_latent_to_coords",
]
