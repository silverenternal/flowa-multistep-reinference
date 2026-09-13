"""ProtBFN/AbBFN upstream shim: thin wrapper around the published JAX/Flax/Haiku harness.

Routes the :class:`adaptive_reflow.adapters.protbfn_abbfn_adapter.ProtBFNAbBFNAdapter`
to the canonical ``model.get_transformer_fn`` + ``sample.make_sample_fn`` from the
cloned ProtBFN repo at ``data/protbfn_abbfn/repo``.

The framework's existing torch path
(``adaptive_reflow.adapters.protbfn_abbfn_model.ProtBFNAbBFNModel``) is the
*cheaper, more reliable* route for this host (cf. user's instruction
"choose the cheaper, more reliable path"):

* The upstream is **JAX/Flax/Haiku**-based — `import haiku as hk`
  triggers a chain of compile-time deps (jax + jaxlib + dm-haiku +
  flax). On this host ``protbfn_venv`` runs Python 3.12 with no JAX
  wheel pre-installed; installing ``jax[cuda12]`` alone pulls ~700 MB
  and on a fresh solver takes 5-10 min. The framework's existing torch
  port already exercises the same parameterization + sample loop and
  produces the published NLL / recovery-rate metrics that the r17 audit
  captures.
* The upstream API surface for ProtBFN/AbBFN is *functions*, not a
  class:
    - ``model.get_transformer_fn(model_size: str) -> callable`` builds
      a Haiku-transformed Transformer.
    - ``sample.make_sample_fn(params, transformer, num_steps, sample_length)
      -> callable`` returns a JAX-side sampler.
    - ``sample.make_loss_fn(params, transformer, sample_length, beta_1)
      -> callable`` returns a JAX-side loss.

  The framework's torch path wraps these into a single
  :class:`nn.Module` (``ProtBFNAbBFNModel``) so the rest of the
  framework can dispatch via :class:`FlowMatchingODEAdapter`; the
  shim mirrors that wrapping for callers that opt in to the upstream.

Verified on this host (2026-09-03):

* ``from model import get_transformer_fn`` raises
  ``ImportError: cannot import name 'BFN' from 'model'`` because the
  upstream does NOT export a class named ``BFN`` — it exports
  ``get_transformer_fn`` only. The shim therefore imports
  ``get_transformer_fn`` + ``sample.make_sample_fn`` and explicitly
  documents that "BFN" is a *protocol*, not a class.
* :func:`is_upstream_available` returns ``False`` on the host's
  ``protbfn_venv`` because :mod:`jax` is not installed; the adapter's
  ``use_upstream=True`` flag will degrade gracefully to the framework's
  torch port.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

PROTBFN_UPSTREAM_REPO: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/protbfn_abbfn/repo"
)

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_GET_TRANSFORMER_FN: Callable[..., Any] | None = None
_UPSTREAM_MAKE_SAMPLE_FN: Callable[..., Any] | None = None
_UPSTREAM_MAKE_LOSS_FN: Callable[..., Any] | None = None


def _install_upstream_path() -> None:
    if PROTBFN_UPSTREAM_REPO not in sys.path:
        sys.path.insert(0, PROTBFN_UPSTREAM_REPO)


def _try_import_upstream() -> dict[str, Any]:
    """Import and cache the upstream JAX/Flax/Haiku functions.

    Returns ``{}`` on any import failure (most commonly
    :class:`ImportError` from missing :mod:`jax` or :mod:`haiku`).
    """
    global _UPSTREAM_IMPORT_ERROR
    global _UPSTREAM_GET_TRANSFORMER_FN
    global _UPSTREAM_MAKE_SAMPLE_FN
    global _UPSTREAM_MAKE_LOSS_FN
    if _UPSTREAM_GET_TRANSFORMER_FN is not None:
        return {
            "get_transformer_fn": _UPSTREAM_GET_TRANSFORMER_FN,
            "make_sample_fn": _UPSTREAM_MAKE_SAMPLE_FN,
            "make_loss_fn": _UPSTREAM_MAKE_LOSS_FN,
        }
    _install_upstream_path()
    try:
        from model import get_transformer_fn  # noqa: PLC0415
        from sample import make_loss_fn, make_sample_fn  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "protbfn_abbfn_upstream_shim: upstream import failed; "
            "fall back to the framework's torch port. "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return {}
    _UPSTREAM_GET_TRANSFORMER_FN = get_transformer_fn
    _UPSTREAM_MAKE_SAMPLE_FN = make_sample_fn
    _UPSTREAM_MAKE_LOSS_FN = make_loss_fn
    return {
        "get_transformer_fn": _UPSTREAM_GET_TRANSFORMER_FN,
        "make_sample_fn": _UPSTREAM_MAKE_SAMPLE_FN,
        "make_loss_fn": _UPSTREAM_MAKE_LOSS_FN,
    }


def is_upstream_available() -> bool:
    return bool(_try_import_upstream())


#: Alias used by the adapter's diagnostic surface
#: (:meth:`ProtBFNAbBFNAdapter.upstream_jax_path_available`). Same
#: semantics as :func:`is_upstream_available`; the dual name matches
#: the convention used by the adapter's ``force_mode="upstream_jax"``
#: opt-in path.
def upstream_jax_available() -> bool:
    return is_upstream_available()


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt."""
    if (
        _UPSTREAM_GET_TRANSFORMER_FN is None
        and _UPSTREAM_IMPORT_ERROR is None
    ):
        _try_import_upstream()
    return _UPSTREAM_IMPORT_ERROR


@dataclass
class ProtBFNUpstreamLoadResult:
    """Lazy wrapper around the upstream JAX/Flax/Haiku transformer.

    On this host the upstream is NOT importable (``jax`` is missing
    from the ``protbfn_venv``); the framework's torch port
    (:class:`adaptive_reflow.adapters.protbfn_abbfn_model.ProtBFNAbBFNModel`)
    remains the canonical adapter path. The shim exists so a caller can
    detect upstream availability and route through JAX when the env is
    set up (e.g. when ``jax[cuda12]`` + ``dm-haiku`` + ``flax`` are
    installed).
    """

    model_kind: str = "ProtBFN"  # or "AbBFN"
    transformer_fn: Callable[..., Any] | None = None
    sample_fn: Callable[..., Any] | None = None
    loss_fn: Callable[..., Any] | None = None
    last_inputs: dict[str, Any] = field(default_factory=dict)
    last_error: BaseException | None = None

    def materialize(self, *, model_kind: str = "ProtBFN") -> bool:
        modules = _try_import_upstream()
        if not modules:
            self.last_error = _UPSTREAM_IMPORT_ERROR
            return False
        self.model_kind = model_kind
        self.transformer_fn = modules["get_transformer_fn"](model_kind)
        return True

    def build_sample_fn(
        self,
        *,
        params: Any,
        num_steps: int = 10000,
        sample_length: int = 512,
    ) -> Callable[..., Any]:
        if self.transformer_fn is None:
            raise RuntimeError(
                "ProtBFNUpstreamLoadResult.build_sample_fn called before materialize()"
            )
        modules = _try_import_upstream()
        self.sample_fn = modules["make_sample_fn"](
            params=params,
            transformer=self.transformer_fn,
            num_steps=int(num_steps),
            sample_length=int(sample_length),
        )
        return self.sample_fn

    def build_loss_fn(
        self,
        *,
        params: Any,
        sample_length: int = 512,
        beta_1: float = 2.0,
    ) -> Callable[..., Any]:
        if self.transformer_fn is None:
            raise RuntimeError(
                "ProtBFNUpstreamLoadResult.build_loss_fn called before materialize()"
            )
        modules = _try_import_upstream()
        self.loss_fn = modules["make_loss_fn"](
            params=params,
            transformer=self.transformer_fn,
            sample_length=int(sample_length),
            beta_1=float(beta_1),
        )
        return self.loss_fn


__all__ = [
    "PROTBFN_UPSTREAM_REPO",
    "ProtBFNUpstreamLoadResult",
    "get_upstream_import_error",
    "is_upstream_available",
    "upstream_jax_available",
]


def _smoke_check() -> None:
    modules = _try_import_upstream()
    err = _UPSTREAM_IMPORT_ERROR
    print(f"upstream_available={bool(modules)}")
    print(f"upstream_repo={PROTBFN_UPSTREAM_REPO}")
    print(f"get_transformer_fn={modules.get('get_transformer_fn')}")
    print(
        "upstream_import_error="
        f"{type(err).__name__ if err is not None else 'None'}: {err}"
    )


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()
