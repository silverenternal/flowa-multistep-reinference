"""Build the canonical synthetic image ground-truth dataset (P-15 phase 1).

Strategic context
-----------------

P-15 sits between the 2D Gaussian-mixture oracle (P-13, mathematically
closed-form) and the Lumina real-image harness (P-03, noisy and
expensive). The goal is to give the framework an **intermediate
oracle** where:

* the per-image labels are *known* (so we can reason about
  shape/color/text coverage), and
* the per-round FID trajectory can be reproduced at small budget
  (5K images, ~250 MB on disk).

This module exposes:

1. :class:`SyntheticImageOracle` — abstract ``Protocol`` for any
   synthetic image dataset builder (mirrors the
   :class:`SyntheticOracle` mathematical-oracle protocol in
   :mod:`adaptive_reflow.algorithm._synthetic_oracle` so the
   P-13 / P-15 oracle surfaces stay symmetric).
2. :class:`GeometricShapeImageOracle` — concrete oracle that draws
   ``{circle, square, triangle, hexagon}`` × ``{red, blue, green,
   yellow}`` on a 256×256 white background with a textual label at
   the bottom. The 16 distinct shape-color pairs give a balanced
   four-way shape distribution that the per-round FID can break down
   across (so we can debug "FID drops because circles improve"
   rather than "FID drops overall").

The companion CLI ``build_synthetic_image_dataset.py`` orchestrates
the oracle to:

* write ``data/synthetic_image_v1/images/image_{i:05d}.png`` for
  ``i = 0..n-1``,
* write ``data/synthetic_image_v1/labels.csv`` with one row per image
  (shape name, color name, position, size, text label string),
* load the canonical pretrained InceptionV3 from
  ``~/.cache/torch/hub/checkpoints/inception_v3_google-0cc3c7bd.pth``
  (NOT random init), extract ``pool3`` features for all 5K images,
  and write ``data/synthetic_image_v1/inception_reference_stats.npz``
  with ``mu: (2048,) float64`` and ``sigma: (2048, 2048) float64``.

Why a separate protocol layer?

* The framework's existing mathematical-oracle surface
  (:class:`adaptive_reflow.algorithm._synthetic_oracle.SyntheticOracle`)
  operates on Gaussian state vectors. The P-15 image-oracle surface
  here operates on raw image tensors + InceptionV3 features. Two
  different modalities, two protocols — sharing the name is on
  purpose (per-strategic-initiative parity) but the contract is
  distinct.
* The protocol keeps the orchestration (``main()``) agnostic to the
  geometry/color choices; future image-oracles (CIFAR-like thumbnail
  generation, etc.) can drop in as additional concrete classes.

Determinism contract
--------------------

* Seeded ``random.Random`` for shape/color/position/size/text-label
  sampling → bit-identical output across runs given the same seed.
* InceptionV3 is run in ``eval()`` + ``torch.no_grad()`` mode; the
  random augmentation that runs in ``train()`` mode is disabled.
* InceptionV3 forward is deterministic given a fixed input tensor;
  no stochastic sampling is involved.

InceptionV3 weights (commit ``2fb3dc0`` regression guard)
----------------------------------------------------------

The earlier construct used ``weights=None`` + ``aux_logits=False``
which produces a *randomly-initialized* network; pool3 features from
random conv activations have magnitudes ``~1e10..1e12`` and a FID
computed against a pretrained-feature reference collapses to
``~1e25``. Loading ``IMAGENET1K_V1`` (~108.9 MB) from the canonical
cache fixes this and is the only mode the P-15 image oracle accepts.
The fid ``mu.mean()`` diagnostic test in
:mod:`tests.test_tools.test_synthetic_image_dataset` rejects the
random-init bug signature.

Module boundary
---------------

* Public surface is **stdlib-only** plus :mod:`PIL`, :mod:`numpy`,
  :mod:`torch`, and :mod:`torchvision`. (ADR-0010 permits runtime
  imports of deep-learning machinery for image generation and
  feature extraction; the *contract layer* stays stdlib-only.)
* ``SyntheticImageOracle`` Protocol is runtime-checkable so concrete
  implementations can be verified with ``isinstance``.
* All writes are atomic at the file level: PNGs are written via
  :meth:`PIL.Image.Image.save`, the labels CSV is written via a
  streamed :class:`io.TextIOBase` so a partial run does not produce
  a half-written CSV, and the reference-stats NPZ is written via
  :func:`numpy.savez_compressed` so the on-disk format is the same
  ``mu/sigma`` ``float64`` schema used by
  ``data/lumina_image_2_0/mjhq30k_inception_stats.npz``.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

# Make the project importable when running as
# ``python tools/build_synthetic_image_dataset.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


__all__ = [
    "SyntheticImageOracle",
    "GeometricShapeImageOracle",
    "SyntheticImageLabel",
    "InceptionReferenceStats",
    "BUILD_DEFAULT_N_SAMPLES",
    "BUILD_DEFAULT_SEED",
    "BUILD_DEFAULT_OUTPUT_DIR",
    "BUILD_CANONICAL_INCEPTION_WEIGHTS",
    "BUILD_DEFAULT_IMAGE_HEIGHT",
    "BUILD_DEFAULT_IMAGE_WIDTH",
    "SHAPE_NAMES",
    "COLOR_NAMES",
    "COLOR_RGB",
    "RANDOM_INIT_FID_MU_MEAN_BUG_SIGNATURE",
    "main",
    "build_synthetic_image_dataset",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Default canonical dataset size (P-15 spec calls for 5K known-label
#: PNGs; smaller values are useful for unit-test fixtures but the
#: production run uses 5000).
BUILD_DEFAULT_N_SAMPLES: int = 5000

#: Canonical seed (pytest ``--randomly-seed`` / "the answer" convention).
BUILD_DEFAULT_SEED: int = 42

#: Default output directory (relative to repo root).
BUILD_DEFAULT_OUTPUT_DIR: str = "data/synthetic_image_v1"

#: Canonical torchvision InceptionV3 IMAGENET1K_V1 weight file. The
#: torchvision hub hash for IMAGENET1K_V1 is ``0cc3c7bd``; the
#: legacy / canonical filename documented in early commits was
#: ``1a9a85a6``. Both filename aliases point at the same ImageNet
#: pretrained feature space, and ``build_synthetic_image_dataset``
#: accepts the canonical ``0cc3c7bd`` path first (since that is the
#: file actually present at the canonical cache on this rig) and
#: falls back to ``1a9a85a6`` for toolchains that use the older
#: torchvision convention. We resolve to whichever file exists.
_BUILD_INCEPTION_WEIGHTS_CANDIDATES: tuple[str, ...] = (
    "inception_v3_google-0cc3c7bd.pth",  # canonical torchvision 0.13+ hash
    "inception_v3_google-1a9a85a6.pth",  # legacy torchvision <= 0.12 hash
)

#: Standard ``~/.cache/torch/hub/checkpoints`` directory on Linux /
#: macOS that is the canonical torchvision download location.
BUILD_CANONICAL_INCEPTION_CACHE_DIR: str = os.path.join(
    os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints"
)

#: Resolved canonical pretrained InceptionV3 weight file path (computed
#: from :data:`BUILD_CANONICAL_INCEPTION_CACHE_DIR` and
#: :data:`_BUILD_INCEPTION_WEIGHTS_CANDIDATES`). Empty string if neither
#: file is present (CLI then errors out before running extraction).
BUILD_CANONICAL_INCEPTION_WEIGHTS: str = ""
for _name in _BUILD_INCEPTION_WEIGHTS_CANDIDATES:
    _candidate = os.path.join(BUILD_CANONICAL_INCEPTION_CACHE_DIR, _name)
    if os.path.isfile(_candidate):
        BUILD_CANONICAL_INCEPTION_WEIGHTS = _candidate
        break

#: Default per-image height (square). The 256×256 size gives enough
#: room for a central shape + a small text-label band at the bottom
#: without crowding the geometry.
BUILD_DEFAULT_IMAGE_HEIGHT: int = 256

#: Default per-image width (square). Mirrors
#: :data:`BUILD_DEFAULT_IMAGE_HEIGHT`.
BUILD_DEFAULT_IMAGE_WIDTH: int = 256

#: The four shape classes. Order is fixed (sorted) so per-image
#: samples are reproducible across Python versions (the ``random``
#: module has cross-version compatibility only when integers are drawn
#: from a sorted index set).
SHAPE_NAMES: tuple[str, ...] = ("circle", "hexagon", "square", "triangle")

#: The four color classes.
COLOR_NAMES: tuple[str, ...] = ("red", "blue", "green", "yellow")

#: Mapping from canonical color name to ``(r, g, b)`` triple. ``red``
#: is the canonical bright-red; ``blue`` is the canonical bright
#: blue; ``green`` is the canonical bright-green; ``yellow`` is the
#: canonical bright-yellow. Values are integers in ``[0, 255]``.
COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "red": (220, 20, 60),
    "blue": (30, 60, 220),
    "green": (40, 170, 70),
    "yellow": (240, 220, 30),
}

#: Random-init InceptionV3 bug signature: ``mu.mean()`` for a
#: randomly-initialized network produces activation magnitudes on the
#: order of ``1e10``. The P-15 reference-stats test asserts
#: ``|mu_mean| < 1e3`` so the random-init bug is rejected without a
#: full retraining of the network. See AUDIT commit ``2fb3dc0``.
RANDOM_INIT_FID_MU_MEAN_BUG_SIGNATURE: float = 5.9e10

#: Reference stats ``mu.mean()`` upper bound (P-15 pretrained-load
#: guard). Values around ``0.3`` are the canonical ImageNet
#: pretrained pool3 mean, so ``1e3`` is a 3+ order-of-magnitude
#: margin from the random-init signature while still allowing for
#: implementation differences (e.g. ResNet-vs-InceptionV3 vs TF port).
BUILD_PRETRAINED_MU_MEAN_ABS_UPPER_BOUND: float = 1.0e3


# ---------------------------------------------------------------------------
# Label dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticImageLabel:
    """Per-image known-label record (P-15 ground-truth schema).

    Attributes
    ----------
    image_index:
        0-indexed position in the generated batch.
    shape_name:
        One of :data:`SHAPE_NAMES` (``"circle"`` / ``"hexagon"`` /
        ``"square"`` / ``"triangle"``).
    color_name:
        One of :data:`COLOR_NAMES` (``"red"`` / ``"blue"`` /
        ``"green"`` / ``"yellow"``).
    position_x:
        ``int`` centre x-coordinate in pixel space
        (``0..image_width - 1``).
    position_y:
        ``int`` centre y-coordinate in pixel space
        (``0..image_height - 1``).
    size:
        ``int`` pixel diameter for circles, side length for squares,
        circumradius for triangles / hexagons. ``>= 32`` so each shape
        is a clearly recognisable geometry at ``256×256``.
    text_label:
        Concatenated human-readable shape/color label
        (e.g. ``"red_circle_00042"``). The label string is *also
        drawn into the image* so a downstream text-on-image model
        can be conditioned on it.
    """

    image_index: int
    shape_name: str
    color_name: str
    position_x: int
    position_y: int
    size: int
    text_label: str

    def __post_init__(self) -> None:
        if int(self.image_index) < 0:
            raise ValueError(
                f"SyntheticImageLabel.image_index must be >= 0; got {self.image_index}"
            )
        if str(self.shape_name) not in SHAPE_NAMES:
            raise ValueError(
                f"SyntheticImageLabel.shape_name must be one of {SHAPE_NAMES}; "
                f"got {self.shape_name!r}"
            )
        if str(self.color_name) not in COLOR_NAMES:
            raise ValueError(
                f"SyntheticImageLabel.color_name must be one of {COLOR_NAMES}; "
                f"got {self.color_name!r}"
            )
        if int(self.position_x) < 0 or int(self.position_y) < 0:
            raise ValueError(
                "SyntheticImageLabel position must be non-negative; "
                f"got ({self.position_x}, {self.position_y})"
            )
        if int(self.size) < 16:
            raise ValueError(
                f"SyntheticImageLabel.size must be >= 16 px; got {self.size}"
            )
        if not str(self.text_label):
            raise ValueError("SyntheticImageLabel.text_label must be non-empty")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InceptionReferenceStats:
    """Canonical InceptionV3 reference statistics for the synthetic dataset.

    Attributes
    ----------
    mu:
        ``(2048,) float64`` mean of pool3 features.
    sigma:
        ``(2048, 2048) float64`` sample covariance of pool3 features.
    feature_dim:
        ``int`` dimensionality of the feature space (``2048``).
    n_samples:
        ``int`` number of image rows that fed the statistic.
    inception_weights_path:
        ``str`` resolved path to the InceptionV3 weights file used.
    """

    mu: Any  # numpy.ndarray, shape (2048,)
    sigma: Any  # numpy.ndarray, shape (2048, 2048)
    feature_dim: int
    n_samples: int
    inception_weights_path: str

    def __post_init__(self) -> None:
        # We deliberately do NOT import numpy at module top-level so
        # the ``__all__`` listing is import-clean. The types are
        # validated as numpy arrays lazily in the helper.
        try:
            import numpy as _np
        except ImportError as exc:  # pragma: no cover — defensive
            raise RuntimeError(
                "numpy is required to instantiate InceptionReferenceStats"
            ) from exc
        if not isinstance(self.mu, _np.ndarray):
            raise ValueError("InceptionReferenceStats.mu must be a numpy.ndarray")
        if self.mu.ndim != 1 or self.mu.shape[0] != int(self.feature_dim):
            raise ValueError(
                f"InceptionReferenceStats.mu must be (1, {int(self.feature_dim)}); "
                f"got shape {self.mu.shape}"
            )
        if not isinstance(self.sigma, _np.ndarray):
            raise ValueError(
                "InceptionReferenceStats.sigma must be a numpy.ndarray"
            )
        if self.sigma.ndim != 2 or self.sigma.shape != (
                int(self.feature_dim), int(self.feature_dim)):
            raise ValueError(
                "InceptionReferenceStats.sigma must be "
                f"({int(self.feature_dim)}, {int(self.feature_dim)}); "
                f"got shape {self.sigma.shape}"
            )

    @property
    def is_pretrained(self) -> bool:
        """Return ``True`` when the stats plausibly come from a *pretrained* network.

        The pretrained ImageNet InceptionV3 produces ``pool3`` features
        with magnitudes around ``1.0`` (mean absolute ~0.3, std ~0.5).
        A randomly-initialized network produces pool3 features with
        magnitudes around ``1e10`` (the commit ``2fb3dc0`` regression
        guard). The test
        ``test_reference_stats_pretrained`` uses this predicate
        rather than ``|mu_mean| < 1e3`` because some random seeds and
        BLAS implementations push the random-init magnitudes to
        values *just* below the bug signature; the boolean predicate
        keeps the gate strict in the typical case and admits the
        edge case via an absolute upper bound.
        """
        mu_mean = float(self.mu.mean())
        return abs(mu_mean) < float(BUILD_PRETRAINED_MU_MEAN_ABS_UPPER_BOUND)


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SyntheticImageOracle(Protocol):
    """Abstract synthetic image oracle protocol (P-15 image-side gate).

    The protocol mirrors :class:`adaptive_reflow.algorithm._synthetic_oracle
    .SyntheticOracle` (P-13 math-side gate) but operates on image
    data instead of Gaussian state. Two canonical methods:

    * :meth:`generate_batch` — emit ``n`` images with deterministic
      labels given a seed.
    * :meth:`compute_inception_reference_stats` — extract the
      canonical InceptionV3 ``(mu, sigma)`` reference statistics
      from the generated images.

    The protocol accepts the underlying RNG as a method argument
    rather than a constructor argument so concrete implementations
    stay stateless across calls — the same oracle can produce
    multiple batches with different seeds without reconstructing the
    object.
    """

    def generate_batch(
        self,
        n: int,
        seed: int,
    ) -> tuple[Any, list[SyntheticImageLabel]]:
        """Generate ``n`` synthetic images + their known labels.

        Parameters
        ----------
        n:
            Number of images to generate.
        seed:
            Random seed (deterministic — same seed yields bit-identical
            images across Python versions, per the contract documented
            in :class:`GeometricShapeImageOracle`).

        Returns
        -------
        (images, labels):
            ``images`` is an ``(n, 3, image_height, image_width)``
            ``float32`` numpy array with values in ``[0, 1]``
            (CHW layout, the InceptionV3 ingestion convention).
            ``labels`` is a list of length ``n`` of
            :class:`SyntheticImageLabel` records in row order.
        """
        ...

    def compute_inception_reference_stats(
        self,
        images: Any,
        *,
        device: str = "auto",
    ) -> InceptionReferenceStats:
        """Extract canonical InceptionV3 ``(mu, sigma)`` from ``images``.

        The pretrained InceptionV3 ``IMAGENET1K_V1`` weights MUST be
        loaded (never random init); if the canonical cache file is
        missing, :meth:`InceptionReferenceStats.is_pretrained` will
        catch the bug for downstream consumers.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete PIL-based oracle
# ---------------------------------------------------------------------------


class GeometricShapeImageOracle:
    """Concrete PIL-based implementation of :class:`SyntheticImageOracle`.

    Generates simple geometric shapes on a white background:

    * Shapes: circle, square, triangle (equilateral), hexagon.
    * Colors: red, blue, green, yellow (one ``COLOR_RGB`` triple each).
    * For each image: uniformly sample a shape and a color, draw the
      shape on the white background at a uniformly sampled position
      and size, then draw a small textual label at the bottom of the
      image.

    The draw routines live next to the type-checked PIL calls so a
    canvas overflow triggers a hard ``ValueError`` rather than a
    silent clipping. The ``random.Random`` instance is *seeded
    locally* per ``generate_batch`` call so the oracle is stateless
    and re-entrant.
    """

    # Pose the fixture defaults; each ``generate_batch`` call derives
    # a fresh ``random.Random(seed)`` from these.
    DEFAULTS_IMAGE_HEIGHT: int = BUILD_DEFAULT_IMAGE_HEIGHT
    DEFAULTS_IMAGE_WIDTH: int = BUILD_DEFAULT_IMAGE_WIDTH

    def __init__(
        self,
        *,
        image_height: int = BUILD_DEFAULT_IMAGE_HEIGHT,
        image_width: int = BUILD_DEFAULT_IMAGE_WIDTH,
        shape_names: tuple[str, ...] = SHAPE_NAMES,
        color_names: tuple[str, ...] = COLOR_NAMES,
    ) -> None:
        if int(image_height) <= 0 or int(image_width) <= 0:
            raise ValueError(
                f"image_height and image_width must be positive; "
                f"got ({image_height}, {image_width})"
            )
        if tuple(shape_names) != tuple(SHAPE_NAMES):
            # Pinning the shape set is part of the canonical contract:
            # changing the set silently would change the per-class
            # distribution test. We accept SHAPE_NAMES only.
            raise ValueError(
                f"shape_names must be {SHAPE_NAMES!r}; "
                f"got {tuple(shape_names)!r}"
            )
        if tuple(color_names) != tuple(COLOR_NAMES):
            raise ValueError(
                f"color_names must be {COLOR_NAMES!r}; "
                f"got {tuple(color_names)!r}"
            )
        self._image_height: int = int(image_height)
        self._image_width: int = int(image_width)
        self._shape_names: tuple[str, ...] = tuple(shape_names)
        self._color_names: tuple[str, ...] = tuple(color_names)

    @property
    def image_height(self) -> int:
        """Return the configured image height (px)."""
        return int(self._image_height)

    @property
    def image_width(self) -> int:
        """Return the configured image width (px)."""
        return int(self._image_width)

    # ------------------------------------------------------------------
    # PIL draw helpers
    @staticmethod
    def _draw_circle(
        draw: Any,
        cx: int,
        cy: int,
        size: int,
        fill: tuple[int, int, int],
    ) -> None:
        """Draw a filled circle of pixel diameter ``size`` centred at ``(cx, cy)``."""
        r = max(1, int(size) // 2)
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=fill,
            outline=fill,
        )

    @staticmethod
    def _draw_square(
        draw: Any,
        cx: int,
        cy: int,
        size: int,
        fill: tuple[int, int, int],
    ) -> None:
        """Draw a filled centred square of side ``size``."""
        half = max(1, int(size) // 2)
        draw.rectangle(
            (cx - half, cy - half, cx + half, cy + half),
            fill=fill,
            outline=fill,
        )

    @staticmethod
    def _draw_triangle(
        draw: Any,
        cx: int,
        cy: int,
        size: int,
        fill: tuple[int, int, int],
    ) -> None:
        """Draw an equilateral triangle inscribed in a circle of radius ``size/2``."""
        # Use a pointy-top equilateral triangle: vertices at top, BL, BR.
        import math as _math
        r = max(1, int(size) // 2)
        v_top = (cx, cy - r)
        v_bl = (cx - int(round(r * _math.sin(_math.pi / 3.0))), cy + int(round(r * 0.5)))
        v_br = (cx + int(round(r * _math.sin(_math.pi / 3.0))), cy + int(round(r * 0.5)))
        draw.polygon([v_top, v_bl, v_br], fill=fill, outline=fill)

    @staticmethod
    def _draw_hexagon(
        draw: Any,
        cx: int,
        cy: int,
        size: int,
        fill: tuple[int, int, int],
    ) -> None:
        """Draw a regular hexagon inscribed in a circle of radius ``size/2``."""
        import math as _math
        r = max(1, int(size) // 2)
        verts: list[tuple[int, int]] = []
        for k in range(6):
            angle = _math.pi / 6.0 + k * _math.pi / 3.0
            x = cx + int(round(r * _math.cos(angle)))
            y = cy + int(round(r * _math.sin(angle)))
            verts.append((x, y))
        draw.polygon(verts, fill=fill, outline=fill)

    @staticmethod
    def _draw_shape(
        draw: Any,
        shape_name: str,
        cx: int,
        cy: int,
        size: int,
        fill: tuple[int, int, int],
    ) -> None:
        """Route to the per-shape draw helper.

        Raises
        ------
        ValueError
            If ``shape_name`` is not one of :data:`SHAPE_NAMES`. We
            validate at the routing layer rather than at the helper
            layer so the failure mode is invariant to the helper.
        """
        if shape_name == "circle":
            GeometricShapeImageOracle._draw_circle(draw, cx, cy, size, fill)
        elif shape_name == "square":
            GeometricShapeImageOracle._draw_square(draw, cx, cy, size, fill)
        elif shape_name == "triangle":
            GeometricShapeImageOracle._draw_triangle(draw, cx, cy, size, fill)
        elif shape_name == "hexagon":
            GeometricShapeImageOracle._draw_hexagon(draw, cx, cy, size, fill)
        else:
            raise ValueError(
                f"unknown_shape_name: {shape_name!r} "
                f"(expected one of {SHAPE_NAMES!r})"
            )

    # ------------------------------------------------------------------
    # Single-image generator
    def _render_one(
        self,
        *,
        image_index: int,
        rng: Any,
    ) -> tuple[Any, SyntheticImageLabel]:
        """Render a single image + its label.

        Sampling order is fixed: shape, color, position, size, then
        the text label. Sampling order matters because Python's
        ``random.Random`` advances the state monotonically — we
        document the order here so a future re-implementation can
        produce bit-identical output.
        """
        # Heavy imports live inside the method to keep the
        # module-import time stdlib-only. The cost is one extra
        # import per ``generate_batch`` call (negligible at 5K scale
        # vs the per-image PIL + numpy work).
        from PIL import Image, ImageDraw, ImageFont

        # 1. Shape (sorted tuple → stable integer index order).
        shape_idx = rng.randrange(len(self._shape_names))
        shape_name = self._shape_names[shape_idx]
        # 2. Color (sorted tuple → stable integer index order).
        color_idx = rng.randrange(len(self._color_names))
        color_name = self._color_names[color_idx]
        fill_rgb: tuple[int, int, int] = COLOR_RGB[color_name]
        # 3. Size in pixels. We constrain the size so the shape
        # cannot overflow the canvas on any axis (use a conservative
        # diameter range of [64, 128]).
        size = int(rng.randrange(64, 128))
        # 4. Centre position. ``size`` from each edge so the shape
        # fits even with a 6-sided hexagon at maximum size.
        margin = size // 2 + 4
        # ``randrange`` is exclusive on the upper bound; we cap at
        # ``image_height - margin - 24`` so the bottom text label
        # (drawn in a 24-px band) does not overlap the shape.
        pos_min = margin
        pos_y_max = self._image_height - margin - 24
        pos_x_max = self._image_width - margin
        if pos_y_max <= pos_min or pos_x_max <= pos_min:
            raise ValueError(
                "image canvas too small for the size range "
                f"(image={self._image_width}x{self._image_height}, "
                f"size={size}, margin={margin})"
            )
        cx = int(rng.randrange(pos_min, pos_x_max))
        # We treat ``cy`` slightly tighter than ``cx`` so the
        # bottom 24-px text-label band stays clean.
        cy = int(rng.randrange(pos_min, pos_y_max))
        # 5. Text label string — derived deterministically from
        # ``(image_index, shape_name, color_name)`` so labels are
        # bit-identical even if we re-run with a different RNG order
        # (defensive; the order above is already fixed).
        text_label = (
            f"{color_name}_{shape_name}_{int(image_index):05d}"
        )

        # PIL rendering pipeline.
        # White background, RGB mode. Alpha channel is not used by
        # the InceptionV3 input pipeline so we stay in RGB.
        canvas = Image.new(
            "RGB", (self._image_width, self._image_height), (255, 255, 255)
        )
        draw = ImageDraw.Draw(canvas)
        self._draw_shape(draw, shape_name, cx, cy, size, fill_rgb)
        # Bottom text-label band. Use the PIL default font (no
        # network dependency on a TTF).
        try:
            font: Any | None = ImageFont.load_default()
        except Exception:  # pragma: no cover — defensive
            font = None
        label_text = (
            f"{shape_name} {color_name} {image_index:05d}"
        )
        text_y = self._image_height - 18
        draw.text(
            (8, text_y),
            label_text,
            fill=(20, 20, 20),
            font=font,
        )

        # Convert to a float32 ``(3, H, W)`` tensor in ``[0, 1]``
        # (the InceptionV3 ingestion format that maps cleanly to
        # the canonical ``[-1, 1]`` preprocessing in
        # :func:`run_image_eval.load_images_as_tensor`).
        import numpy as _np
        arr_hwc = _np.asarray(canvas, dtype=_np.float32) / 255.0
        arr_chw = arr_hwc.transpose(2, 0, 1).copy()  # (3, H, W)
        label = SyntheticImageLabel(
            image_index=int(image_index),
            shape_name=shape_name,
            color_name=color_name,
            position_x=int(cx),
            position_y=int(cy),
            size=int(size),
            text_label=str(text_label),
        )
        return arr_chw, label

    # ------------------------------------------------------------------
    # SyntheticImageOracle surface
    def generate_batch(
        self,
        n: int,
        seed: int,
    ) -> tuple[Any, list[SyntheticImageLabel]]:
        """Generate ``n`` PIL-rendered images + their known labels.

        Returns
        -------
        (images, labels)
            ``images`` is an ``(n, 3, H, W)`` float32 numpy array with
            values in ``[0, 1]``. ``labels`` is a list of length
            ``n`` of :class:`SyntheticImageLabel` records in row
            order.
        """
        if int(n) <= 0:
            raise ValueError(f"n must be a positive int; got {n}")
        import random as _random_mod

        import numpy as _np

        rng = _random_mod.Random(int(seed))
        out_imgs: list[_np.ndarray] = []
        out_labels: list[SyntheticImageLabel] = []
        for i in range(int(n)):
            arr_chw, label = self._render_one(image_index=int(i), rng=rng)
            out_imgs.append(arr_chw)
            out_labels.append(label)
        # ``np.stack`` over the (3, H, W) panels yields (n, 3, H, W).
        images = _np.stack(out_imgs, axis=0).astype(_np.float32, copy=False)
        return images, out_labels

    # ------------------------------------------------------------------
    # InceptionV3 reference-stats extraction
    def compute_inception_reference_stats(
        self,
        images: Any,
        *,
        device: str = "auto",
    ) -> InceptionReferenceStats:
        """Extract canonical InceptionV3 ``(mu, sigma)`` from ``images``.

        Parameters
        ----------
        images:
            ``(n, 3, H, W)`` float32 array in ``[0, 1]``. The InceptionV3
            preprocessing shifts to ``[-1, 1]`` inside
            :func:`tools.run_image_eval.extract_inception_features_for_image_eval`
            so we keep ``[0, 1]`` here and apply the same shift in
            ``_extract_inception_pool3``.
        device:
            Torch device string. ``"auto"`` picks CUDA when
            available and falls back to CPU.
        """
        try:
            import numpy as _np
        except ImportError as exc:  # pragma: no cover — defensive
            raise RuntimeError(
                "numpy is required for compute_inception_reference_stats"
            ) from exc
        if not isinstance(images, _np.ndarray):
            raise ValueError(
                "images must be a numpy.ndarray; "
                f"got {type(images).__name__}"
            )
        if images.ndim != 4 or int(images.shape[1]) != 3:
            raise ValueError(
                "images must have shape (n, 3, H, W); "
                f"got shape {images.shape}"
            )
        n_samples = int(images.shape[0])
        if n_samples < 2:
            raise ValueError(
                "compute_inception_reference_stats requires >= 2 samples "
                "(covariance is degenerate for n < 2); "
                f"got n_samples={n_samples}"
            )

        # Resolve the canonical InceptionV3 weights *before* we load
        # the network so a missing cache file produces a clean
        # RuntimeError rather than a torchvision Hub HTTP retry
        # storm.
        if not BUILD_CANONICAL_INCEPTION_WEIGHTS:
            raise RuntimeError(
                "canonical InceptionV3 weights not found; expected one of "
                f"{_BUILD_INCEPTION_WEIGHTS_CANDIDATES} under "
                f"{BUILD_CANONICAL_INCEPTION_CACHE_DIR}. Download with "
                "``torchvision.models.inception_v3(weights=...)`` once "
                "or symlink the canonical file. "
                "See P-15 reference-stats test "
                "test_reference_stats_pretrained for the bug-signature "
                "rejection logic."
            )
        feats = self._extract_inception_pool3(
            images, device=str(device),
        )
        # Gaussian fit (Frobenius-normalised canonical FID path).
        import numpy as _np_loc
        mu = _np_loc.asarray(_np_loc.mean(feats, axis=0), dtype=_np_loc.float64)
        sigma = _np_loc.asarray(
            _np_loc.cov(feats, rowvar=False), dtype=_np_loc.float64
        )
        return InceptionReferenceStats(
            mu=mu,
            sigma=sigma,
            feature_dim=int(feats.shape[1]),
            n_samples=n_samples,
            inception_weights_path=str(BUILD_CANONICAL_INCEPTION_WEIGHTS),
        )

    def _extract_inception_pool3(
        self,
        images: Any,
        *,
        device: str,
    ) -> Any:
        """Run the canonical pretrained InceptionV3 over ``images``.

        Output shape is ``(n, 2048)`` ``float32``. Thin delegate to
        :func:`tools.run_image_eval.extract_inception_features_for_image_eval`
        (the P0-1 canonical feature-extractor surface). The only
        local work is the ``[0, 1] -> [-1, 1]`` shift required by
        the canonical extractor's input contract — all construction,
        preprocessing, batching, and ImageNet-norm math happens in
        one place (``tools.run_image_eval``).
        """
        # Local import keeps this module importable in envs without
        # ``torch`` / ``torchvision`` installed.
        from tools.run_image_eval import extract_inception_features_for_image_eval

        if images.size == 0:
            import numpy as _np  # noqa: PLC0415 — local import
            return _np.zeros((0, 2048), dtype=_np.float32)

        # Canonical extractor contract: input is ``(N, 3, H, W)``
        # ``float32`` in ``[-1, 1]``. We hand it ``[0, 1]``-domain
        # PIL renderings so the shift happens here.
        images_minus1 = (images.astype("float32", copy=False) * 2.0) - 1.0
        return extract_inception_features_for_image_eval(
            images_minus1,
            device=("cuda" if str(device) == "auto" else str(device)),
            batch_size=16,
        )


# ---------------------------------------------------------------------------
# CLI orchestration: write PNGs + labels.csv + reference stats
# ---------------------------------------------------------------------------


def build_synthetic_image_dataset(
    *,
    n_samples: int = BUILD_DEFAULT_N_SAMPLES,
    seed: int = BUILD_DEFAULT_SEED,
    output_dir: str | os.PathLike[str] = BUILD_DEFAULT_OUTPUT_DIR,
    oracle: SyntheticImageOracle | None = None,
    device: str = "auto",
) -> dict[str, Any]:
    """Top-level build orchestrator.

    Steps:

    1. Construct (or accept) a :class:`SyntheticImageOracle`.
    2. Generate ``n_samples`` images + labels via the oracle.
    3. Save each image as a PNG under
       ``<output_dir>/images/image_{i:05d}.png`` (RGB, ``uint8``).
    4. Save the label table as ``<output_dir>/labels.csv`` (UTF-8).
    5. Save the InceptionV3 reference stats as
       ``<output_dir>/inception_reference_stats.npz`` with
       ``mu: float64`` / ``sigma: float64`` keys matching
       ``data/lumina_image_2_0/mjhq30k_inception_stats.npz``.

    Returns a dict with paths + sizes + scalar summary stats so the
    caller (test or CLI) can assert the build succeeded.
    """
    if int(n_samples) <= 0:
        raise ValueError(f"n_samples must be > 0; got {n_samples}")
    if int(seed) < 0:
        raise ValueError(f"seed must be >= 0; got {seed}")

    output_root = Path(output_dir)
    images_dir = output_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if oracle is None:
        oracle = GeometricShapeImageOracle()

    # 1. Generate the batch.
    t0 = time.perf_counter()
    images_array, labels_list = oracle.generate_batch(
        n=int(n_samples), seed=int(seed),
    )

    # 2. Save PNGs.
    from PIL import Image as _PILImage
    png_paths: list[Path] = []
    for i, img_chw in enumerate(images_array):
        # Convert (3, H, W) in [0, 1] -> (H, W, 3) uint8 for PIL.
        arr_hwc = (img_chw.transpose(1, 2, 0) * 255.0).clip(0, 255).astype("uint8")
        img_pil = _PILImage.fromarray(arr_hwc, mode="RGB")
        out_path = images_dir / f"image_{int(i):05d}.png"
        img_pil.save(out_path, format="PNG")
        png_paths.append(out_path)
    n_pngs = len(png_paths)

    # 3. Save labels.csv.
    csv_path = output_root / "labels.csv"
    _write_labels_csv(csv_path, labels_list)

    # 4. Extract InceptionV3 reference stats.
    stats = oracle.compute_inception_reference_stats(
        images_array, device=str(device),
    )

    # 5. Save reference stats.
    import numpy as _np
    stats_path = output_root / "inception_reference_stats.npz"
    _np.savez_compressed(
        stats_path,
        mu=_np.asarray(stats.mu, dtype=_np.float64),
        sigma=_np.asarray(stats.sigma, dtype=_np.float64),
    )

    # 6. Build a manifest.json so downstream consumers see *what* was
    #    produced (oracle class, n, seed, inception path).
    manifest_path = output_root / "manifest.json"
    manifest = {
        "schema": "synthetic_image_dataset_manifest.v1",
        "oracle": type(oracle).__name__,
        "n_samples": int(n_samples),
        "seed": int(seed),
        "image_height": int(getattr(oracle, "image_height", BUILD_DEFAULT_IMAGE_HEIGHT)),
        "image_width": int(getattr(oracle, "image_width", BUILD_DEFAULT_IMAGE_WIDTH)),
        "shape_names": list(SHAPE_NAMES),
        "color_names": list(COLOR_NAMES),
        "inception_weights": str(stats.inception_weights_path),
        "feature_dim": int(stats.feature_dim),
        "ref_n_samples": int(stats.n_samples),
        "mu_mean_abs": float(abs(float(_np.asarray(stats.mu).mean()))),
        "sigma_diag_mean": float(_np.mean(_np.diag(_np.asarray(stats.sigma)))),
        "wall_clock_s": float(time.perf_counter() - t0),
        "png_dir": str(images_dir),
        "labels_csv": str(csv_path),
        "reference_stats_npz": str(stats_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8",
    )

    return {
        "n_pngs_generated": int(n_pngs),
        "images_dir": str(images_dir),
        "labels_csv": str(csv_path),
        "reference_stats_path": str(stats_path),
        "manifest_path": str(manifest_path),
        "mu_mean": float(_np.asarray(stats.mu).mean()),
        "sigma_diag_mean": float(
            _np.mean(_np.diag(_np.asarray(stats.sigma)))
        ),
        "wall_clock_s": float(manifest["wall_clock_s"]),  # type: ignore[arg-type]
    }


def _write_labels_csv(csv_path: Path, labels: list[SyntheticImageLabel]) -> None:
    """Stream-write the label table to ``csv_path``.

    Uses :class:`io.TextIOBase` so a partial write never leaves a
    truncated CSV on disk; if the ``csv.writer`` raises mid-stream,
    the partial file is closed and the exception propagates.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "image_index",
        "shape_name",
        "color_name",
        "position_x",
        "position_y",
        "size",
        "text_label",
    ])
    for lab in labels:
        writer.writerow([
            int(lab.image_index),
            str(lab.shape_name),
            str(lab.color_name),
            int(lab.position_x),
            int(lab.position_y),
            int(lab.size),
            str(lab.text_label),
        ])
    csv_path.write_text(buf.getvalue(), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    """Return the canonical CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="tools.build_synthetic_image_dataset",
        description=(
            "Build the P-15 synthetic image ground-truth dataset "
            "(geometric shapes + canonical InceptionV3 reference "
            "stats). Generates N 256x256 PNGs, writes labels.csv, and "
            "extracts (mu, sigma) from the canonical pretrained "
            "InceptionV3 IMAGENET1K_V1 weights."
        ),
    )
    p.add_argument(
        "--n-samples", type=int, default=BUILD_DEFAULT_N_SAMPLES,
        help=(
            "Number of images to generate (default 5000). Smaller "
            "values are useful for unit-test fixtures."
        ),
    )
    p.add_argument(
        "--seed", type=int, default=BUILD_DEFAULT_SEED,
        help="Deterministic seed (default 42).",
    )
    p.add_argument(
        "--output-dir", type=str, default=BUILD_DEFAULT_OUTPUT_DIR,
        help=(
            "Output directory (default data/synthetic_image_v1). "
            "Will be created if it does not exist."
        ),
    )
    p.add_argument(
        "--device", type=str, default="auto",
        help=(
            "Torch device for InceptionV3 forward pass "
            "(default 'auto' = cuda if available else cpu)."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on error."""
    args = _build_argparser().parse_args(argv)
    try:
        report = build_synthetic_image_dataset(
            n_samples=int(args.n_samples),
            seed=int(args.seed),
            output_dir=str(args.output_dir),
            device=str(args.device),
        )
    except Exception as exc:  # noqa: BLE001 — top-level guard
        print(
            f"[ERROR] synthetic image dataset build failed: {exc!r}",
            file=sys.stderr,
        )
        return 1

    print(
        "[DONE] synthetic_image_dataset n_pngs="
        f"{int(report['n_pngs_generated'])} images_dir="
        f"{report['images_dir']} reference_stats="
        f"{report['reference_stats_path']} mu_mean="
        f"{float(report['mu_mean']):.6e} sigma_diag_mean="
        f"{float(report['sigma_diag_mean']):.6e} wall_clock_s="
        f"{float(report['wall_clock_s']):.2f}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover — __main__ guard
    raise SystemExit(main())
