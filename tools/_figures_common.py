"""Shared matplotlib preamble for tools/_make_*.py figure scripts.

Wave 105 P1-D: extract the duplicated matplotlib preamble (Agg backend,
pyplot import, OUT_DIR setup, and the standard savefig kwargs) from the
4 matplotlib-using ``_make_*.py`` scripts into a single shared module.

Scripts updated to use this helper (4 of 5):

  - ``tools/_make_figures.py``         — 4 PNG figures (Wave 19 paper set)
  - ``tools/_make_wave41_figure.py``   — per-family signed_mean bar chart
  - ``tools/_make_wave42_figure.py``   — tier3_real_ckpt_signed_mean chart
  - ``tools/_make_nfe_scan_figure.py`` — Wave 58 NFE-scan aggregation plot

NOT updated (intentionally):

  - ``tools/_make_wave19_figures.py`` — renders raw SVG via XML strings; never
    imports matplotlib, so there is nothing to extract.

API:

  - :data:`OUT_DIR`: absolute path to ``<repo>/docs/figures/`` (already
    ``os.makedirs(..., exist_ok=True)``-ed on import).
  - :data:`_FIGURE_DPI`: default DPI for :func:`save_figure` (``150``).
  - :func:`save_figure(fig, path, dpi=None, **kwargs)`: project-standard
    ``fig.savefig`` wrapper. Defaults: ``dpi=_FIGURE_DPI``,
    ``bbox_inches="tight"``, ``facecolor="white"``. Pass
    ``facecolor=None`` to override.
  - ``plt``: re-exported ``matplotlib.pyplot`` so callers can use the
    same import path as before without an additional import line.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (must follow matplotlib.use("Agg"))

# Standard savefig DPI (matches Wave 75 figure convention).
_FIGURE_DPI = 150

# Standard output directory (<repo>/docs/figures/), created on import.
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(OUT_DIR, exist_ok=True)


def save_figure(fig, path, dpi: int | None = None, **kwargs) -> None:
    """Save a matplotlib figure with the project's standard kwargs.

    Defaults match the Wave 75 figure convention: ``dpi=_FIGURE_DPI``,
    ``bbox_inches="tight"``, ``facecolor="white"``. Pass any kwarg through
    to override (e.g. ``facecolor=None`` for the NFE-scan figure that
    doesn't set a white background).
    """
    fig.savefig(
        path,
        dpi=dpi if dpi is not None else _FIGURE_DPI,
        bbox_inches="tight",
        facecolor="white",
        **kwargs,
    )
    plt.close(fig)


__all__ = ["OUT_DIR", "_FIGURE_DPI", "save_figure", "plt"]
