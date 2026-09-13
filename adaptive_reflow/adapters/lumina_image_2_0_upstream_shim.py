"""Lumina-Image 2.0 upstream shim: thin wrapper around the published NextDiT + transport.

Routes the :class:`adaptive_reflow.adapters.lumina_image_2_0.LuminaImage20Adapter`
to the canonical ``models.nextdit.NextDiT_2B_GQA_patch2_Adaln_Refiner`` +
``transport.create_transport`` / ``transport.Sampler`` from the cloned
Lumina repo at ``data/lumina_image_2_0/repo``.

Verified import on this host (2026-09-03):

* ``from models.nextdit import NextDiT_2B_GQA_patch2_Adaln_Refiner``
  requires the :mod:`flash_attn` module to be importable. On the
  ``lumina_venv`` a clean ``flash_attn` wheel is NOT installed (it
  requires a CUDA-toolchain build against the running torch wheel).
  The shim therefore stubs ``flash_attn`` and
  ``flash_attn.bert_padding`` in :data:`sys.modules` *before* the
  ``models.nextdit`` import: the stub uses
  :func:`torch.nn.functional.scaled_dot_product_attention` as a
  reference-quality replacement and the bert-padding helpers are
  thin passthroughs. The shim documents this swap in
  :data:`_LUMINA_FLASH_ATTN_STUB_NOTE`.
* ``from transport import create_transport, Sampler`` imports cleanly
  after ``sys.path.insert(0, data/lumina_image_2_0/repo)`` — the
  ``transport`` package is pure numpy/torch and has no third-party
  compile-time deps.
"""

from __future__ import annotations

import logging
import sys
import types
from dataclasses import dataclass, field
from typing import Any

import torch.nn.functional as F

_LOGGER = logging.getLogger(__name__)

LUMINA_UPSTREAM_REPO: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/lumina_image_2_0/repo"
)

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_NEXTDIT_CLS: Any = None
_UPSTREAM_TRANSPORT_FACTORY: Any = None
_UPSTREAM_SAMPLER_CLS: Any = None

_LUMINA_FLASH_ATTN_STUB_NOTE: str = (
    "Lumina's `models/model.py` does unconditional `from flash_attn "
    "import flash_attn_varlen_func` at module scope. On this host no "
    "compiled flash_attn wheel matches torch 2.7.0+cu128; the shim "
    "installs a sys.modules-level stub that uses torch.nn.functional."
    "scaled_dot_product_attention as a reference-quality replacement. "
    "Correctness on real weights: NOT verified — the official Lumina "
    "checkpoint expects flash_attn v2 attention exactly. Use this shim "
    "for import-only smoke tests; run the upstream harness in a venv "
    "with flash_attn installed for production eval."
)


def _install_upstream_path() -> None:
    if LUMINA_UPSTREAM_REPO not in sys.path:
        sys.path.insert(0, LUMINA_UPSTREAM_REPO)


def _install_flash_attn_stub() -> None:
    """Install a sys.modules-level :mod:`flash_attn` stub.

    Safe to call multiple times; idempotent.
    """
    if "flash_attn" in sys.modules:
        return
    fa = types.ModuleType("flash_attn")
    fab = types.ModuleType("flash_attn.bert_padding")

    def _flash_attn_varlen_func(q, k, v, *args, **kwargs):  # noqa: ANN001, D401
        # q/k/v are (T, H, D) tensors. Fall back to SDPA on (B, H, T, D).
        q_b = q.unsqueeze(0).transpose(1, 2)
        k_b = k.unsqueeze(0).transpose(1, 2)
        v_b = v.unsqueeze(0).transpose(1, 2)
        out = F.scaled_dot_product_attention(q_b, k_b, v_b)
        return out.transpose(1, 2).squeeze(0)

    def _index_first_axis(index, x):  # noqa: ANN001, D401
        return x[index]

    def _pad_input(hidden_states, indices, num_new_tokens, *args, **kwargs):  # noqa: ANN001, D401
        # Reference flash_attn signature: returns (padded, indices, batch_sizes).
        return hidden_states, indices, None

    def _unpad_input(x, indices, batch_sizes, *args, **kwargs):  # noqa: ANN001, D401
        # Reference flash_attn signature: returns (unpadded, indices, batch_sizes, seqlens).
        return x[indices], indices, batch_sizes, None

    fa.flash_attn_varlen_func = _flash_attn_varlen_func
    fab.index_first_axis = _index_first_axis
    fab.pad_input = _pad_input
    fab.unpad_input = _unpad_input
    sys.modules["flash_attn"] = fa
    sys.modules["flash_attn.bert_padding"] = fab


def _try_import_upstream() -> dict[str, Any]:
    """Import and cache Lumina NextDiT + transport pieces."""
    global _UPSTREAM_IMPORT_ERROR
    global _UPSTREAM_NEXTDIT_CLS
    global _UPSTREAM_TRANSPORT_FACTORY
    global _UPSTREAM_SAMPLER_CLS
    if _UPSTREAM_NEXTDIT_CLS is not None and _UPSTREAM_TRANSPORT_FACTORY is not None:
        return {
            "NextDiT": _UPSTREAM_NEXTDIT_CLS,
            "create_transport": _UPSTREAM_TRANSPORT_FACTORY,
            "Sampler": _UPSTREAM_SAMPLER_CLS,
        }
    _install_upstream_path()
    _install_flash_attn_stub()
    try:
        # The upstream package is named ``models`` (not ``nextdit``);
        # ``models/__init__.py`` re-exports the four NextDiT_* factories.
        # Importing ``models.model`` directly bypasses the ``__init__``
        # so we sidestep any nested module that may need optional compile-time
        # deps (``apex`` for RMSNorm is a UserWarning, not an error).
        from models.model import (  # noqa: PLC0415
            NextDiT_2B_GQA_patch2_Adaln_Refiner,
            NextDiT_3B_GQA_patch2_Adaln_Refiner,
            NextDiT_4B_GQA_patch2_Adaln_Refiner,
            NextDiT_7B_GQA_patch2_Adaln_Refiner,
        )
        from transport import Sampler, create_transport  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "lumina_image_2_0_upstream_shim: upstream import failed; "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return {}
    # Use the 2B variant by default; the adapter can swap via
    # :func:`get_nextdit_factory`.
    _UPSTREAM_NEXTDIT_CLS = {
        "2B": NextDiT_2B_GQA_patch2_Adaln_Refiner,
        "3B": NextDiT_3B_GQA_patch2_Adaln_Refiner,
        "4B": NextDiT_4B_GQA_patch2_Adaln_Refiner,
        "7B": NextDiT_7B_GQA_patch2_Adaln_Refiner,
    }
    _UPSTREAM_TRANSPORT_FACTORY = create_transport
    _UPSTREAM_SAMPLER_CLS = Sampler
    return {
        "NextDiT": _UPSTREAM_NEXTDIT_CLS,
        "create_transport": _UPSTREAM_TRANSPORT_FACTORY,
        "Sampler": _UPSTREAM_SAMPLER_CLS,
    }


def get_nextdit_factory(size: str = "2B") -> Any:
    """Return the canonical NextDiT constructor for the requested model size."""
    modules = _try_import_upstream()
    factories = modules.get("NextDiT", {})
    if size not in factories:
        raise KeyError(
            f"unknown_lumina_size:{size} (expected one of {tuple(factories)})"
        )
    return factories[size]


def is_upstream_available() -> bool:
    return bool(_try_import_upstream())


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt."""
    if _UPSTREAM_NEXTDIT_CLS is None and _UPSTREAM_IMPORT_ERROR is None:
        _try_import_upstream()
    return _UPSTREAM_IMPORT_ERROR


@dataclass
class LuminaUpstreamLoadResult:
    """Lazy wrapper around the upstream :class:`NextDiT` + :class:`Sampler`."""

    model_size: str = "2B"
    nextdit: Any = None
    sampler: Any = None
    transport: Any = None
    last_inputs: dict[str, Any] = field(default_factory=dict)
    last_error: BaseException | None = None

    def materialize(self, *, model_size: str = "2B", **model_kwargs: Any) -> bool:
        modules = _try_import_upstream()
        if not modules:
            self.last_error = _UPSTREAM_IMPORT_ERROR
            return False
        factory = get_nextdit_factory(model_size)
        self.model_size = model_size
        try:
            self.nextdit = factory(**model_kwargs)
        except Exception as exc:  # noqa: BLE001
            self.last_error = exc
            _LOGGER.warning("Lumina NextDiT construction failed: %s", exc)
            return False
        # Transport / sampler are config-only — no need to instantiate here.
        self.transport = modules["create_transport"]()
        self.sampler = modules["Sampler"]
        return True

    def sample(
        self,
        model_inputs: dict[str, Any],
        *,
        num_steps: int = 60,
        cfg_scale: float = 4.0,
    ) -> Any:
        """Run upstream sampler; mirrors ``sample.py::main`` end-to-end.

        Caller is responsible for tokenizing the prompt + preparing
        ``z``, ``clip_ctx``, etc. (the upstream ``demo.py`` does this).
        """
        if self.nextdit is None or self.sampler is None:
            raise RuntimeError(
                "LuminaUpstreamLoadResult.sample called before materialize()"
            )
        self.last_inputs = dict(model_inputs)
        return self.sampler(self.transport, num_steps=num_steps, cfg_scale=cfg_scale)


__all__ = [
    "LUMINA_UPSTREAM_REPO",
    "_LUMINA_FLASH_ATTN_STUB_NOTE",
    "LuminaUpstreamLoadResult",
    "get_nextdit_factory",
    "get_upstream_import_error",
    "is_upstream_available",
]


def _smoke_check() -> None:
    modules = _try_import_upstream()
    err = _UPSTREAM_IMPORT_ERROR
    print(f"upstream_available={bool(modules)}")
    print(f"upstream_repo={LUMINA_UPSTREAM_REPO}")
    print(f"nextdit_factories={list(modules.get('NextDiT', {}))}")
    print(
        "upstream_import_error="
        f"{type(err).__name__ if err is not None else 'None'}: {err}"
    )
    print(_LUMINA_FLASH_ATTN_STUB_NOTE)


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()
