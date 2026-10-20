"""GAP-54 — FlowMol3 CTMC sampler-stochasticity passthrough.

The upstream ``FlowMol.sample`` defaults to ``stochasticity=8.0``
(``ctmc_vector_field.py:149``), which lets a 1e-2 coordinate perturbation flip
a discrete class and break the Lipschitz premise of the contraction bound.
The adapter must be able to pass ``stochasticity=0.0`` without changing the
legacy call when the argument is omitted.
"""

from __future__ import annotations

import pytest

from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter


def test_default_does_not_forward_stochasticity() -> None:
    adapter = FlowMol3V2Adapter(backend="numpy", num_steps=4)
    assert adapter._sampler_kwargs() == {}


def test_zero_is_forwarded() -> None:
    adapter = FlowMol3V2Adapter(
        backend="numpy", num_steps=4, sampler_stochasticity=0.0,
    )
    assert adapter._sampler_kwargs() == {"stochasticity": 0.0}


def test_positive_value_is_forwarded() -> None:
    adapter = FlowMol3V2Adapter(
        backend="numpy", num_steps=4, sampler_stochasticity=2.5,
    )
    assert adapter._sampler_kwargs() == {"stochasticity": 2.5}


@pytest.mark.parametrize("bad", [-0.1, float("nan"), float("inf")])
def test_invalid_values_are_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        FlowMol3V2Adapter(
            backend="numpy", num_steps=4, sampler_stochasticity=bad,
        )
