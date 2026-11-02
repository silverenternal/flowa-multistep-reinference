"""Protect four-point regression intervals from using a df=4 t quantile."""

from __future__ import annotations

import re

import pytest

from tools import gap91_holdout


def test_four_point_holdout_uses_two_residual_degrees_of_freedom(monkeypatch, capsys):
    """Known OLS fixture: xbar=1.5, prediction=2.5, residual variance=0.9."""
    values = {
        "a": (0.0, 1.0),
        "b": (1.0, 2.0),
        "c": (2.0, 2.0),
        "d": (3.0, 5.0),
        "hold": (1.5, 2.5),
    }
    monkeypatch.setattr(
        gap91_holdout,
        "CHECKPOINTS",
        {key: (key, key != "hold") for key in values},
    )
    monkeypatch.setattr(gap91_holdout, "plateaus", values.__getitem__)
    assert gap91_holdout.main() == 0
    output = capsys.readouterr().out
    row = next(line for line in output.splitlines() if line.strip().startswith("hold "))
    bounds = re.search(r"\[\s*([-\d.]+),\s*([-\d.]+)\]", row)
    assert bounds is not None
    # t(.975, 2)=4.3026527; SEprediction=sqrt(.9*(1+1/4))=sqrt(1.125).
    # These expected bounds are independent of the script's quantile constant.
    assert float(bounds.group(1)) == pytest.approx(-2.063675, abs=0.0005)
    assert float(bounds.group(2)) == pytest.approx(7.063675, abs=0.0005)
