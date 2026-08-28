"""Karras EDM preconditioner for the 2D velocity-field MLP.

Implements the EDM preconditioner from Karras et al. 2022
(``Elucidating the Design Space of Diffusion-Based Generative
Models``, arXiv:2206.00364) used to scale the velocity-field input
and output during training and sampling. The preconditioner
transforms ``(sigma, x) -> (c_skip, c_out, c_in, c_noise)`` so that

    D_theta(x, sigma) = c_skip(sigma) * x + c_out(sigma) * F_theta(
        c_in(sigma) * x, c_noise(sigma)
    )

with the canonical EDM coefficients:

    c_skip(sigma) = sigma_data^2 / (sigma^2 + sigma_data^2)
    c_out(sigma)  = sigma * sigma_data / sqrt(sigma^2 + sigma_data^2)
    c_in(sigma)   = 1 / sqrt(sigma^2 + sigma_data^2)
    c_noise(sigma) = 0.25 * ln(sigma)

This module exists so the ``TwoDimFMAdapter`` can optionally wire
Karras preconditioning without changing its protocol surface; legacy
callers that don't pass a preconditioner keep the raw MLP.

Module boundary
---------------

* stdlib-only.
* Pure: deterministic given identical inputs.
* Fail-closed: bad sigma / sigma_data raise :class:`ValueError`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, ClassVar

from adaptive_reflow.contracts import hash_artifact


@dataclass(frozen=True)
class KarrasPreconditioner:
    """EDM preconditioner coefficients (Karras et al. 2022).

    Holds the four coefficient functions of the canonical EDM
    preconditioner. Constructed via :meth:`from_config` or the
    explicit ``__init__`` with ``sigma_data``.

    :param sigma_data: data scale (defaults to 1.0; the canonical EDM
        value for image-scale data is 1.5).
    """

    FAMILY: ClassVar[str] = "karras_edm"

    sigma_data: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.sigma_data, (int, float)) or isinstance(
            self.sigma_data, bool
        ):
            raise ValueError(
                f"sigma_data must be a real number, got {self.sigma_data!r}"
            )
        s = float(self.sigma_data)
        if not math.isfinite(s) or s <= 0.0:
            raise ValueError(
                f"sigma_data must be finite and > 0, got {s!r}"
            )

    def c_skip(self, sigma: float) -> float:
        s = float(sigma)
        if not math.isfinite(s) or s < 0.0:
            raise ValueError(f"sigma must be finite and >= 0, got {s!r}")
        sd2 = float(self.sigma_data) ** 2
        return float(sd2 / (s * s + sd2))

    def c_out(self, sigma: float) -> float:
        s = float(sigma)
        if not math.isfinite(s) or s < 0.0:
            raise ValueError(f"sigma must be finite and >= 0, got {s!r}")
        sd = float(self.sigma_data)
        sd2 = sd * sd
        return float(s * sd / math.sqrt(s * s + sd2))

    def c_in(self, sigma: float) -> float:
        s = float(sigma)
        if not math.isfinite(s) or s < 0.0:
            raise ValueError(f"sigma must be finite and >= 0, got {s!r}")
        sd2 = float(self.sigma_data) ** 2
        return float(1.0 / math.sqrt(s * s + sd2))

    def c_noise(self, sigma: float) -> float:
        s = float(sigma)
        if not math.isfinite(s) or s <= 0.0:
            raise ValueError(f"sigma must be finite and > 0, got {s!r}")
        return float(0.25 * math.log(s))

    def config_hash(self) -> str:
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "sigma_data": float(self.sigma_data),
                }
            )
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "sigma_data": float(self.sigma_data),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> KarrasPreconditioner:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(sigma_data=float(config.get("sigma_data", 1.0)))


__all__ = ["KarrasPreconditioner"]
