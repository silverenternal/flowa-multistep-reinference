"""GAP-34 — R1 init dose-response analysis (``tools/gap34_dose_analysis.py``).

These CPU tests pin the statistics: Spearman monotonicity, the ``tau=0`` collapse
anchor, and the paired-t helper against known Student-t tail values. No torch /
GPU.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    p = str(REPO_ROOT / "tools")
    if p not in sys.path:
        sys.path.insert(0, p)
    return importlib.import_module("gap34_dose_analysis")


def _payload(hits_by_tau: dict[float, list[int]]) -> dict:
    taus = sorted(hits_by_tau)
    seeds = [42, 43, 44]
    rows = [
        {"tau": t, "seed": s, "hits": h}
        for t in taus
        for s, h in zip(seeds, hits_by_tau[t], strict=True)
    ]
    return {"taus": taus, "seeds": seeds, "rows": rows}


def test_spearman_monotone_is_one() -> None:
    mod = _load()
    assert abs(mod.spearman([0, 1, 2, 3, 4], [0, 10, 20, 30, 40]) - 1.0) < 1e-9
    assert abs(mod.spearman([0, 1, 2, 3, 4], [40, 30, 20, 10, 0]) + 1.0) < 1e-9


def test_analyse_collapse_and_rise() -> None:
    mod = _load()
    payload = _payload({
        0.0: [0, 0, 0],
        0.25: [261, 255, 270],
        0.5: [290, 288, 300],
        1.0: [298, 295, 305],
        2.0: [300, 297, 308],
    })
    out = mod.analyse(payload)
    assert abs(out["spearman_mean"] - 1.0) < 1e-9
    assert out["collapse_anchor"]["tau0_all_zero"] is True
    assert out["rise_contrast"]["mean_rise"] > 0
    assert out["rise_contrast"]["n_seeds"] == 3


def test_analyse_detects_non_monotone() -> None:
    mod = _load()
    payload = _payload({
        0.0: [0, 0, 0],
        0.25: [10, 10, 10],
        0.5: [5, 5, 5],   # dips
        1.0: [30, 30, 30],
        2.0: [40, 40, 40],
    })
    out = mod.analyse(payload)
    assert out["spearman_mean"] < 1.0


def test_analyse_inverted_u_peak() -> None:
    """The observed shape: hits rise then fall (interior optimum at tau=1)."""
    mod = _load()
    payload = _payload({
        0.0: [0, 0, 0],
        0.25: [261, 255, 270],
        0.5: [290, 288, 300],
        1.0: [298, 295, 305],   # peak
        2.0: [62, 60, 66],      # falls
    })
    out = mod.analyse(payload)
    assert out["spearman_mean"] < 1.0                 # not monotone
    assert out["peak"]["peak_tau"] == 1.0
    assert out["peak"]["max_tau"] == 2.0
    assert out["peak"]["max_over_peak"] < 0.5         # max tau well below peak
    assert out["collapse_anchor"]["tau0_all_zero"] is True


def test_t_tail_matches_known_values() -> None:
    mod = _load()
    # t=2.0, df=2 -> two-sided p ~= 0.1835 ; t=4.303, df=2 -> ~= 0.05
    assert abs(mod._t_sf_two_sided(2.0, 2) - 0.1835) < 1e-3
    assert abs(mod._t_sf_two_sided(4.303, 2) - 0.05) < 1e-3
