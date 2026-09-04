"""Regression tests for ``tools.eval_rf_cifar.extract_inception_features``.

Commit ``2fb3dc0`` fixed a silent dimensionality bug in
:func:`tools.eval_rf_cifar.extract_inception_features` — the previous
incarnation built ``InceptionV3`` with the IMAGENET1K_V1 weights and
``aux_logits=False`` simultaneously, which (a) violates torchvision's
checkpoint contract (the IMAGENET1K_V1 aux head is part of the
checkpoint, so ``aux_logits=False`` triggers a ``ValueError`` at
construct-time) and (b) leaves the canonical-pytorch-fid shape broken
(``model.fc`` is the 1000-class classifier head, not the 2048-dim
``pool3`` features that FID is defined against). That fix swapped to
``weights=None, aux_logits=False, transform_input=False`` and replaced
``model.fc`` with ``torch.nn.Identity()`` so the forward returns the
2048-dim pool3 vector directly.

**Wave 1 P0-1 supersedes the ``weights=None`` half of that fix.**
``extract_inception_features`` is now a thin delegation to the single
canonical extractor surface
:func:`tools.run_image_eval.extract_inception_features_for_image_eval`
-> :func:`tools.run_image_eval.load_inception_for_fid`, which builds
``inception_v3(weights=Inception_V3_Weights.IMAGENET1K_V1,
aux_logits=True, transform_input=False)``, replaces ``model.fc`` with
``Identity`` and drops ``model.AuxLogits``. Rationale and the FID
provenance reconciliation are in ``docs/CONSOLIDATED_RESULTS.md``
("P0-1 reconciliation note", the ``Extractor family`` column): the
``weights=None`` construction is a *randomly initialised* network whose
pool3 magnitudes (~1e10-1e12) drove the ~1e25 / 409.18 FID outliers, so
random-init is now the named defect rather than the desired state. The
2048-dim ``Identity``-fc half of ``2fb3dc0`` is unchanged and still
guarded below.

These tests lock in the fix at the regression level so future refactors
do not silently regress to the 1000-dim logits path. They are gated on
both ``torch`` and ``torchvision`` being importable; if either is
missing the entire file is skipped (the synthetic-mode codepath in
``tools.eval_rf_cifar`` is exercised by other suites).

Tests
-----

* ``test_extract_inception_features_returns_2048_dim`` — calling
  :func:`extract_inception_features` on a synthetic ``(4, 3, 32, 32)``
  batch of floats in ``[-1, 1]`` returns a ``(4, 2048)`` array.
* ``test_extract_inception_features_uses_canonical_imagenet_weights``
  — the function must construct InceptionV3 with *deliberately chosen*
  pretrained weights, never a random init. We patch
  ``torchvision.models.inception_v3`` with a tiny stub and assert it is
  invoked with ``weights=Inception_V3_Weights.IMAGENET1K_V1``. Renamed
  from ``..._does_not_use_imagenet_weights_when_extracting`` in Wave 3:
  the guarded regression (silent random-init feature extraction) is
  unchanged, but P0-1 inverted the pinned value, and asserting the
  IMAGENET1K_V1 identity is strictly stronger than the old
  ``weights is None`` assertion for that regression.
* ``test_extract_inception_features_finite`` — outputs contain no
  ``NaN`` / ``Inf``.
* ``test_extract_inception_features_deterministic`` — two calls with
  the same input produce bit-identical outputs (no random
  augmentation, no dropout in ``eval()`` mode).
* ``test_extract_inception_features_handles_different_batch_sizes`` —
  the chunking loop produces the same final array for ``batch_size`` in
  ``(1, 2, 4, 8)`` regardless of the chunk boundary.

The "tiny InceptionV3" is implemented by monkeypatching
``torchvision.models.inception_v3`` with a small ``nn.Module`` whose
``forward`` returns a ``(N, 2048)`` tensor of Gaussian noise. This
exercises the real :func:`extract_inception_features` codepath (resize,
``[-1, 1]`` -> ImageNet normalization, batch chunking, ``Identity`` fc
replacement, ``np.float32`` cast) without paying for a real
InceptionV3 forward pass on each test.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Imports — gate on torch + torchvision.
# ---------------------------------------------------------------------------

torch = pytest.importorskip("torch")
torchvision = pytest.importorskip("torchvision")  # noqa: F841  (used via patch)


# ---------------------------------------------------------------------------
# Helpers — load tools/eval_rf_cifar.py as a module without registering
# ``tools`` as a package (the repo's pytest conftest already puts the
# repo root on sys.path; we replicate the import the script performs at
# its top to keep the test independent of ``tools.__init__``).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EVAL_RF_PATH = _REPO_ROOT / "tools" / "eval_rf_cifar.py"


@pytest.fixture(scope="module")
def eval_rf_module() -> Any:
    """Import :mod:`tools.eval_rf_cifar` once per module and return it.

    We use ``importlib.util.spec_from_file_location`` rather than a
    normal ``import`` because the script-level docstring + the
    ``sys.path`` insertion in the module body expect to run as a
    script, not as a package submodule. Loading it this way mirrors how
    :mod:`tests.test_tools.test_run_sota_cifar_experiment` loads its
    target script.
    """
    # Make sure the repo root is on sys.path so the in-script
    # ``from adaptive_reflow.adapters.rectified_flow_cifar import ...``
    # resolves.
    repo_str = str(_REPO_ROOT)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    spec = importlib.util.spec_from_file_location(
        "tools_eval_rf_cifar_under_test", str(_EVAL_RF_PATH)
    )
    assert spec is not None and spec.loader is not None, (
        f"could not load spec for {_EVAL_RF_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture()
def tiny_inception_v3(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Patch ``torchvision.models.inception_v3`` with a tiny stub.

    The stub is a small ``nn.Module`` whose ``forward`` returns a
    ``(N, 2048)`` tensor of Gaussian noise drawn from a fixed seed. It
    exposes a public ``fc`` attribute (so the production
    ``model.fc = torch.nn.Identity()`` assignment is a no-op rather
    than an ``AttributeError``) and tracks every construction call so
    the "no pretrained weights" test can inspect the kwargs.

    Returns
    -------
    call_log : list[dict[str, Any]]
        Per-call kwargs passed to the stub ``inception_v3``. Each entry
        is a copy of the kwargs dict at construction time.
    """

    import torch.nn as nn

    call_log: list[dict[str, Any]] = []

    class _TinyInceptionV3(nn.Module):
        """Stand-in for ``torchvision.models.inception_v3``.

        The forward returns a deterministic ``(N, 2048)`` tensor that
        is finite (no NaN / Inf) and reproduces across calls when the
        PRNG is seeded.
        """

        def __init__(self, **kwargs: Any) -> None:
            super().__init__()
            self.kwargs = dict(kwargs)
            # Mirror torchvision: an ``fc`` attribute that the
            # production code replaces with ``torch.nn.Identity()``.
            self.fc = nn.Linear(2048, 1000)
            # Flag the dropout / training-mode toggles the model can
            # call, but eval() disables them anyway.
            self.eval_called = False

        def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
            # Deterministic per-row Gaussian noise keyed off the row
            # CONTENT (not the in-chunk index, not the batch size).
            # The production chunking loop splits the batch into chunks
            # of ``batch_size`` rows and concatenates the per-chunk
            # outputs. If the stub keyed off the in-chunk index, then
            # ``batch_size=1`` would always produce a [seed_0; seed_0;
            # seed_0; seed_0] array (every chunk restarts at index 0),
            # and the cross-batch-size equality check below would
            # always fail even when the production code is correct.
            # Keying off the per-row sum makes the stub behave like a
            # real network: the same input row produces the same
            # output feature regardless of which chunk it lands in
            # (``F.interpolate`` is per-image independent, so the
            # content-derived key is stable across chunk boundaries).
            out = torch.zeros(
                int(x.shape[0]), 2048, dtype=torch.float32
            )
            for i in range(int(x.shape[0])):
                # Per-row content fingerprint: the row-sum is a stable
                # continuous float (no float-mode ambiguity from the
                # chunk split) and is essentially unique across random
                # uniform rows.
                row_sum = float(x[i].sum().item())
                seed = int(abs(row_sum) * 1e3) % (2**31 - 1)
                gen = torch.Generator().manual_seed(int(seed))
                out[i] = torch.randn(
                    2048, generator=gen, dtype=torch.float32
                )
            return out

        def eval(self) -> "_TinyInceptionV3":  # type: ignore[override]
            self.eval_called = True
            return super().eval()

    def _factory(**kwargs: Any) -> _TinyInceptionV3:
        call_log.append(dict(kwargs))
        return _TinyInceptionV3(**kwargs)

    # Patch the symbol the production code looks up
    # (``torchvision.models.inception_v3``). We rebind on the live
    # ``torchvision.models`` module, NOT on the cached reference the
    # eval_rf_cifar module imported at load time — but since
    # ``extract_inception_features`` re-imports ``torchvision.models as
    # tvm`` *inside* the function, rebinding on the live module is the
    # correct layer.
    monkeypatch.setattr(
        "torchvision.models.inception_v3", _factory, raising=True
    )
    return call_log


@pytest.fixture()
def sample_batch() -> np.ndarray:
    """Synthetic ``(4, 3, 32, 32)`` float32 batch in ``[-1, 1]``."""
    rng = np.random.default_rng(0)
    return rng.uniform(-1.0, 1.0, size=(4, 3, 32, 32)).astype(np.float32)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_extract_inception_features_returns_2048_dim(
    eval_rf_module: Any,
    tiny_inception_v3: list[dict[str, Any]],
    sample_batch: np.ndarray,
) -> None:
    """``extract_inception_features`` must return ``(N, 2048)`` for ``(N, 3, 32, 32)`` input.

    Regression guard for commit ``2fb3dc0``: an earlier incarnation
    made ``model.forward`` return a 1000-dim classifier-logits tensor
    instead of the 2048-dim pool3 features FID is defined against. The
    surviving half of that fix is ``model.fc = Identity``, which the
    canonical Wave 1 P0-1 surface
    (:func:`tools.run_image_eval.load_inception_for_fid`) still applies
    on top of ``weights=IMAGENET1K_V1, aux_logits=True``. This test
    pins the *shape* contract only; the weights contract is pinned by
    ``test_extract_inception_features_uses_canonical_imagenet_weights``.
    """
    feats = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    assert isinstance(feats, np.ndarray)
    assert feats.shape == (4, 2048), (
        f"expected (4, 2048) pool3 features; got {feats.shape}. This is "
        f"the regression guarded by commit 2fb3dc0 — the InceptionV3 "
        f"weight-loading shape has drifted back to the 1000-dim logits "
        f"path."
    )


def test_extract_inception_features_uses_canonical_imagenet_weights(
    eval_rf_module: Any,
    tiny_inception_v3: list[dict[str, Any]],
    sample_batch: np.ndarray,
) -> None:
    """``extract_inception_features`` must build Inception with IMAGENET1K_V1.

    Regression guard, provenance ``2fb3dc0`` -> Wave 1 P0-1.

    The guarded regression is unchanged: **no production caller may
    silently extract FID features from a network whose weights were not
    deliberately chosen.** At ``2fb3dc0`` the deliberate choice was
    ``weights=None`` (believed necessary because the pretrained
    checkpoint forces ``aux_logits=True``); P0-1 established that a
    random-init Inception produces pool3 magnitudes ~1e10-1e12 and the
    ~1e25 / 409.18 FID outliers recorded in
    ``docs/CONSOLIDATED_RESULTS.md`` ("P0-1 reconciliation note"), and
    pinned ``torchvision`` ``IMAGENET1K_V1`` as the single canonical
    extractor family (``tools.run_image_eval.CANONICAL_INCEPTION_FAMILY
    == "inceptionv3_torchvision_IMAGENET1K_V1"``).

    Asserting the IMAGENET1K_V1 identity **subsumes** the old
    ``weights is None`` assertion as a random-init guard: it rules out
    ``None`` and every other checkpoint enum, so a future revert to
    random init still fails here, loudly, on the first assertion below.
    """
    import torchvision.models as tvm

    feats = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    # Sanity: extraction still returns 2048-dim pool3 features (the
    # surviving ``model.fc = Identity`` half of the 2fb3dc0 fix).
    assert feats.shape == (4, 2048)

    # At least one inception_v3 construction call must have happened.
    assert len(tiny_inception_v3) >= 1, (
        "torchvision.models.inception_v3 was never called; the "
        "production code took a non-torch path or skipped "
        "construction."
    )

    expected_weights = tvm.Inception_V3_Weights.IMAGENET1K_V1
    for call_idx, kwargs in enumerate(tiny_inception_v3):
        got_weights = kwargs.get("weights", "SENTINEL_UNSET")
        # (a) The original 2fb3dc0-era regression guard, restated:
        #     never a randomly-initialised feature extractor.
        assert got_weights is not None, (
            f"call #{call_idx}: torchvision.models.inception_v3 was "
            f"called with weights=None, i.e. a RANDOMLY INITIALISED "
            f"InceptionV3. Random pool3 activations have magnitude "
            f"~1e10-1e12 and collapse FID to ~1e25 (see the P0-1 "
            f"reconciliation note in docs/CONSOLIDATED_RESULTS.md). "
            f"Production must load deliberately chosen weights."
        )
        # (b) The Wave 1 P0-1 canonical pin: not merely 'some weights',
        #     but the one family the published reference statistics
        #     (MJHQ-30K / CIFAR) were computed with. A different
        #     checkpoint would silently break cross-paper comparability.
        assert got_weights is expected_weights, (
            f"call #{call_idx}: expected "
            f"weights=Inception_V3_Weights.IMAGENET1K_V1 (the single "
            f"canonical extractor family pinned by Wave 1 P0-1 at "
            f"tools/run_image_eval.py load_inception_for_fid); got "
            f"{got_weights!r}."
        )
        # (c) The IMAGENET1K_V1 checkpoint carries the aux head, so
        #     torchvision requires ``aux_logits=True`` at construction.
        #     The canonical loader satisfies that and then drops the
        #     head (``model.AuxLogits = None``) plus replaces
        #     ``model.fc`` with ``Identity``, so the forward still
        #     returns the 2048-dim pool3 vector asserted above.
        assert kwargs.get("aux_logits") is True, (
            f"call #{call_idx}: aux_logits expected True (required by "
            f"the IMAGENET1K_V1 checkpoint contract); got "
            f"{kwargs.get('aux_logits')!r}."
        )
        # (d) ``transform_input=False`` — the canonical surface does its
        #     own [-1,1] -> [0,1] -> ImageNet normalisation; letting
        #     torchvision re-transform would double-normalise.
        assert kwargs.get("transform_input") is False, (
            f"call #{call_idx}: transform_input expected False; got "
            f"{kwargs.get('transform_input')!r}."
        )


def test_extract_inception_features_finite(
    eval_rf_module: Any,
    tiny_inception_v3: list[dict[str, Any]],
    sample_batch: np.ndarray,
) -> None:
    """Extracted features must contain no NaN or Inf."""
    feats = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    assert feats.shape == (4, 2048)
    assert np.all(np.isfinite(feats)), (
        "extract_inception_features returned a non-finite value "
        "(NaN or Inf); FID computation will propagate the corruption "
        "via the mean / covariance."
    )


def test_extract_inception_features_deterministic(
    eval_rf_module: Any,
    tiny_inception_v3: list[dict[str, Any]],
    sample_batch: np.ndarray,
) -> None:
    """Same input twice must produce bit-identical outputs.

    :func:`extract_inception_features` runs the model in ``eval()``
    mode inside ``torch.no_grad()`` so dropout / BN running-stats
    updates are disabled; there is no random augmentation. This test
    pins that contract — any future "let's add test-time augmentation"
    refactor must update both the test and the regression rationale.
    """
    feats_a = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    feats_b = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    assert feats_a.shape == feats_b.shape == (4, 2048)
    # ``np.array_equal`` is the strongest deterministic equality we can
    # ask for without coupling to the model's internal float-mode
    # handling. ``np.allclose`` would mask genuine regressions.
    assert np.array_equal(feats_a, feats_b), (
        "extract_inception_features is non-deterministic across two "
        "calls with identical inputs. eval() / no_grad() must have "
        "been bypassed or a random augmentation was introduced."
    )


@pytest.mark.parametrize("batch_size", [1, 2, 4, 8])
def test_extract_inception_features_handles_different_batch_sizes(
    eval_rf_module: Any,
    tiny_inception_v3: list[dict[str, Any]],
    sample_batch: np.ndarray,
    batch_size: int,
) -> None:
    """The chunking loop must produce the same output for ``batch_size`` in ``(1, 2, 4, 8)``.

    The :func:`extract_inception_features` body slices the input with
    ``range(0, images.shape[0], batch_size)`` and concatenates the
    per-chunk outputs. ``batch_size=1`` exercises the smallest chunk
    (one image per forward call); ``batch_size=8`` exercises the
    "single chunk, larger than N" branch where ``i + batch_size > N``
    must be silently handled by NumPy slicing. All four must produce
    identical final arrays (the stub model is deterministic).
    """
    feats = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=int(batch_size)
    )
    assert feats.shape == (4, 2048), (
        f"batch_size={batch_size}: expected (4, 2048); got {feats.shape}. "
        f"The chunking loop in extract_inception_features dropped or "
        f"duplicated rows."
    )
    assert np.all(np.isfinite(feats))
    # Cross-batch-size determinism: the stub model's output is keyed
    # only on the batch dimension, so all four batch_size values must
    # produce the same final array. This guards against off-by-one
    # slicing in the chunk loop (e.g. ``i + batch_size`` off the end).
    expected = eval_rf_module.extract_inception_features(
        sample_batch, batch_size=4
    )
    assert np.array_equal(feats, expected), (
        f"batch_size={batch_size} produced a different array than "
        f"batch_size=4; the chunking loop is concatenating chunks in "
        f"the wrong order or skipping rows at chunk boundaries."
    )