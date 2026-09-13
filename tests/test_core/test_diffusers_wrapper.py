"""Unit tests for :mod:`adaptive_reflow.core.diffusers_wrapper`.

Wave 24 MUST-3 partial completion — the framework-core glue
module that wraps DiT-family forward calls (SiT-XL/2, FreqFlow,
Kanzi encoder, MM-FM, HiDream-I1).

All tests are stdlib + numpy only (CPU-only sandbox). The
torch-dependent branches are exercised via a fake-torch shim
that emulates just enough of the torch surface to satisfy the
wrappers (tensor-from-numpy, unsqueeze, to(dtype), etc.).
"""
from __future__ import annotations

import importlib.util
import sys
import types
from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.core.diffusers_wrapper import (
    DiffusersDType,
    DiffusersForwardSignature,
    DiffusersForwardWrapper,
    DiffusersPipelineFactory,
    DiffusersPipelineSpec,
    diffusers_postprocess,
    diffusers_preprocess,
)


# ---------------------------------------------------------------------------
# Fake torch shim — a minimal subset of the torch surface that satisfies
# the diffusers_wrapper import-time and runtime contracts.
# ---------------------------------------------------------------------------


def _has_real_torch() -> bool:
    """Detect whether a real ``torch`` is importable.

    Defensive against pre-existing fake ``torch`` stubs left in
    :data:`sys.modules` by other test fixtures (some of which
    install a stub module with ``__spec__ = None`` that breaks
    :func:`importlib.util.find_spec`).
    """
    existing = sys.modules.get("torch")
    if existing is not None and getattr(existing, "_is_fake", False):
        return False
    if existing is not None and getattr(existing, "__spec__", None) is None:
        # A torch stub with no spec — treat as absent so the
        # fake install wins (the wrapper would crash on it
        # anyway).
        return False
    try:
        return importlib.util.find_spec("torch") is not None
    except (ImportError, ValueError):
        return False


class _FakeTensor:
    """Tiny NumPy-backed tensor that mimics the subset of the torch
    surface the diffusers_wrapper touches (``detach`` /
    ``cpu().numpy()`` / ``squeeze`` / ``unsqueeze`` /
    ``to(dtype=...)``)."""

    __slots__ = ("_arr", "_dtype", "_device")

    def __init__(self, arr: np.ndarray, dtype: Any = None, device: Any = None) -> None:
        self._arr = np.asarray(arr)
        self._dtype = dtype
        self._device = device

    def detach(self) -> "_FakeTensor":
        return self

    def cpu(self) -> "_FakeTensor":
        return self

    def numpy(self) -> np.ndarray:
        return np.asarray(self._arr, dtype=np.float64)

    def squeeze(self, dim: int | None = None) -> "_FakeTensor":
        if dim is None:
            new = self._arr.squeeze()
        else:
            new = self._arr.squeeze(axis=dim)
        return _FakeTensor(new, dtype=self._dtype, device=self._device)

    def unsqueeze(self, dim: int) -> "_FakeTensor":
        return _FakeTensor(np.expand_dims(self._arr, axis=dim), dtype=self._dtype, device=self._device)

    def to(self, dtype: Any = None, device: Any = None) -> "_FakeTensor":
        return _FakeTensor(self._arr, dtype=dtype, device=device)

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(self._arr.shape)

    def ndim(self) -> int:  # matches torch.Tensor.ndim as a method
        return int(self._arr.ndim)

    def __getitem__(self, key: Any) -> "_FakeTensor":
        return _FakeTensor(self._arr[key], dtype=self._dtype, device=self._device)

    # Arithmetic operators — needed for CFG interpolation
    # (``v_uncond + cfg * (v_cond - v_uncond)``).
    def __add__(self, other: Any) -> "_FakeTensor":
        if isinstance(other, _FakeTensor):
            return _FakeTensor(self._arr + other._arr, dtype=self._dtype, device=self._device)
        return _FakeTensor(self._arr + np.asarray(other), dtype=self._dtype, device=self._device)

    def __radd__(self, other: Any) -> "_FakeTensor":
        return self.__add__(other)

    def __sub__(self, other: Any) -> "_FakeTensor":
        if isinstance(other, _FakeTensor):
            return _FakeTensor(self._arr - other._arr, dtype=self._dtype, device=self._device)
        return _FakeTensor(self._arr - np.asarray(other), dtype=self._dtype, device=self._device)

    def __mul__(self, other: Any) -> "_FakeTensor":
        if isinstance(other, _FakeTensor):
            return _FakeTensor(self._arr * other._arr, dtype=self._dtype, device=self._device)
        return _FakeTensor(self._arr * np.asarray(other), dtype=self._dtype, device=self._device)

    def __rmul__(self, other: Any) -> "_FakeTensor":
        return self.__mul__(other)

    @property
    def dtype(self) -> Any:
        return self._dtype

    @property
    def device(self) -> Any:
        return self._device


def _install_fake_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a test-scoped fake; teardown restores the previous module."""
    existing = sys.modules.get("torch")
    if existing is not None and not getattr(existing, "_is_fake", False):
        # Real torch present — leave it alone.
        return

    fake = types.ModuleType("torch")
    fake._is_fake = True  # type: ignore[attr-defined]
    fake.__spec__ = None  # type: ignore[attr-defined]

    def as_tensor(arr: Any, dtype: Any = None) -> _FakeTensor:
        return _FakeTensor(np.asarray(arr), dtype=dtype, device="cpu")

    def tensor(arr: Any, dtype: Any = None, device: Any = None) -> _FakeTensor:
        return _FakeTensor(np.asarray(arr), dtype=dtype, device=device)

    def zeros(*shape: int, dtype: Any = None, device: Any = None) -> _FakeTensor:
        return _FakeTensor(np.zeros(tuple(shape)), dtype=dtype, device=device)

    fake.as_tensor = as_tensor  # type: ignore[attr-defined]
    fake.tensor = tensor  # type: ignore[attr-defined]
    fake.zeros = zeros  # type: ignore[attr-defined]
    fake.Tensor = _FakeTensor  # type: ignore[attr-defined]
    fake.float32 = "float32"  # type: ignore[attr-defined]
    fake.bfloat16 = "bfloat16"  # type: ignore[attr-defined]
    fake.no_grad = lambda: _FakeNullCtx()  # type: ignore[attr-defined]

    class _FakeNullCtx:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_: Any) -> bool:
            return False

    monkeypatch.setitem(sys.modules, "torch", fake)


@dataclass
class _FakeModel:
    """Captures forward-call arguments and returns a deterministic tensor."""

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]]
    output_channels: int
    use_cfg: bool = True

    def forward(self, x: Any, t: Any, y: Any, **kwargs: Any) -> _FakeTensor:
        self.calls.append(((x, t, y), dict(kwargs)))
        # Produce a tensor with the same spatial shape as ``x`` but
        # ``output_channels`` channels. The velocity field is
        # ``(B, output_channels, H, W)`` = (1, C, H, W).
        if hasattr(x, "shape"):
            shape = tuple(x.shape)
            if len(shape) == 4:
                _, _, h, w = shape
            else:
                _, h, w = shape
        else:
            h, w = 4, 4
        # Pull a deterministic integer seed out of ``t`` if it's
        # a _FakeTensor (the wrapper passes ``t_t = torch.tensor([t])``).
        try:
            if hasattr(t, "cpu"):
                seed_int = int(float(np.asarray(t.cpu().numpy()).reshape(-1)[0]) * 1_000_000) % (1 << 31)
            else:
                seed_int = int(float(t) * 1_000_000) % (1 << 31)
        except Exception:
            seed_int = 0
        rng = np.random.default_rng(int(seed_int))
        out = rng.standard_normal((1, self.output_channels, int(h), int(w))).astype(np.float64)
        return _FakeTensor(out, dtype="float32", device="cpu")

    def __call__(self, x: Any, t: Any, y: Any, **kwargs: Any) -> _FakeTensor:
        """The wrapper calls the model as a callable."""
        return self.forward(x, t, y, **kwargs)

    def eval(self) -> "_FakeModel":
        return self


@pytest.fixture(autouse=True)
def _ensure_fake_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure ``torch`` resolves to the fake shim before each test."""
    if not _has_real_torch():
        _install_fake_torch(monkeypatch)


def test_fake_torch_install_restores_previous_module() -> None:
    """A scoped fake must restore both absent and pre-existing module states."""
    with pytest.MonkeyPatch.context() as outer:
        outer.delitem(sys.modules, "torch", raising=False)
        with pytest.MonkeyPatch.context() as scope:
            _install_fake_torch(scope)
            assert sys.modules["torch"]._is_fake
        assert "torch" not in sys.modules

        previous = types.ModuleType("torch")
        previous._is_fake = True
        outer.setitem(sys.modules, "torch", previous)
        with pytest.MonkeyPatch.context() as scope:
            _install_fake_torch(scope)
            assert sys.modules["torch"] is not previous
        assert sys.modules["torch"] is previous


def test_fake_torch_install_preserves_existing_real_module() -> None:
    """An already-loaded non-fake torch is never replaced."""
    with pytest.MonkeyPatch.context() as scope:
        existing = types.ModuleType("torch")
        scope.setitem(sys.modules, "torch", existing)
        _install_fake_torch(scope)
        assert sys.modules["torch"] is existing


# ---------------------------------------------------------------------------
# Test 1: signature dataclass validation
# ---------------------------------------------------------------------------


def test_signature_rejects_zero_in_channels() -> None:
    with pytest.raises(ValueError, match="in_channels_must_be_positive"):
        DiffusersForwardSignature(in_channels=0, out_channels=4)


def test_signature_rejects_zero_patch_size() -> None:
    with pytest.raises(ValueError, match="patch_size_must_be_positive"):
        DiffusersForwardSignature(in_channels=4, out_channels=4, patch_size=0)


def test_signature_default_values_match_self_flow() -> None:
    """Self-Flow SiT-XL/2 defaults: 4 in, 4 out, patch=2, 1152-dim y."""
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    assert sig.patch_size == 2
    assert sig.conditioning_dim == 1152
    assert sig.use_cfg is True
    assert sig.dtype == "float32"


# ---------------------------------------------------------------------------
# Test 2: numpy preprocessing
# ---------------------------------------------------------------------------


def test_diffusers_preprocess_adds_batch_dim() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    x = np.random.default_rng(0).standard_normal((4, 8, 8))
    t = diffusers_preprocess(x, signature=sig)
    assert tuple(t.shape) == (1, 4, 8, 8)


def test_diffusers_preprocess_rejects_wrong_channels() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    x = np.zeros((3, 8, 8), dtype=np.float64)
    with pytest.raises(ValueError, match="in_channels=4"):
        diffusers_preprocess(x, signature=sig)


def test_diffusers_preprocess_rejects_2d_input() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    x = np.zeros((8, 8), dtype=np.float64)
    with pytest.raises(ValueError, match=r"\(C, H, W\)"):
        diffusers_preprocess(x, signature=sig)


# ---------------------------------------------------------------------------
# Test 3: numpy postprocessing
# ---------------------------------------------------------------------------


def test_diffusers_postprocess_squeezes_batch_dim() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    out = _FakeTensor(np.zeros((1, 4, 8, 8), dtype=np.float64))
    arr = diffusers_postprocess(out, signature=sig)
    assert arr.shape == (4, 8, 8)


def test_diffusers_postprocess_slices_to_in_channels() -> None:
    """Dual-timestep head (8 channels) should be sliced to 4."""
    sig = DiffusersForwardSignature(in_channels=4, out_channels=8)
    out = _FakeTensor(np.zeros((1, 8, 4, 4), dtype=np.float64))
    arr = diffusers_postprocess(out, signature=sig)
    assert arr.shape == (4, 4, 4)


def test_diffusers_postprocess_rejects_non_tensor() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4)
    with pytest.raises(TypeError, match="torch.Tensor"):
        diffusers_postprocess(np.zeros((4, 4, 4)), signature=sig)


# ---------------------------------------------------------------------------
# Test 4: forward wrapper with cfg disabled (single-pass)
# ---------------------------------------------------------------------------


def test_diffusers_forward_wrapper_single_pass_cfg_disabled() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4, use_cfg=False)
    model = _FakeModel(calls=[], output_channels=4)
    wrapper = DiffusersForwardWrapper(model, signature=sig)
    x = np.random.default_rng(0).standard_normal((4, 8, 8))
    y = np.zeros(sig.conditioning_dim, dtype=np.float64)
    result = wrapper(x, t=0.5, y=y, cfg_scale=1.5)
    assert result.cfg_applied is False
    assert result.velocity.shape == (4, 8, 8)
    assert len(model.calls) == 1


def test_diffusers_forward_wrapper_cfg_scale_zero_disables_cfg() -> None:
    """``cfg_scale <= 0`` disables CFG even when ``use_cfg=True``."""
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4, use_cfg=True)
    model = _FakeModel(calls=[], output_channels=4)
    wrapper = DiffusersForwardWrapper(model, signature=sig)
    x = np.zeros((4, 4, 4), dtype=np.float64)
    y = np.zeros(sig.conditioning_dim, dtype=np.float64)
    result = wrapper(x, t=0.5, y=y, cfg_scale=0.0)
    assert result.cfg_applied is False
    assert len(model.calls) == 1


# ---------------------------------------------------------------------------
# Test 5: forward wrapper with cfg enabled (dual-pass)
# ---------------------------------------------------------------------------


def test_diffusers_forward_wrapper_cfg_enabled_runs_dual_pass() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4, use_cfg=True)
    model = _FakeModel(calls=[], output_channels=4)
    wrapper = DiffusersForwardWrapper(model, signature=sig)
    x = np.zeros((4, 4, 4), dtype=np.float64)
    y = np.zeros(sig.conditioning_dim, dtype=np.float64)
    result = wrapper(x, t=0.5, y=y, cfg_scale=2.0)
    assert result.cfg_applied is True
    # Two forward calls: cond + uncond.
    assert len(model.calls) == 2
    # CFG interpolation: v_uncond + cfg * (v_cond - v_uncond) = 2*v_cond - v_uncond.
    assert result.raw_cond is not None
    assert result.raw_uncond is not None


# ---------------------------------------------------------------------------
# Test 6: forward wrapper enforces conditioning_dim
# ---------------------------------------------------------------------------


def test_diffusers_forward_wrapper_rejects_wrong_y_dim() -> None:
    sig = DiffusersForwardSignature(in_channels=4, out_channels=4, use_cfg=False)
    model = _FakeModel(calls=[], output_channels=4)
    wrapper = DiffusersForwardWrapper(model, signature=sig)
    x = np.zeros((4, 4, 4), dtype=np.float64)
    y = np.zeros(64, dtype=np.float64)  # wrong dim (sig.conditioning_dim=1152)
    with pytest.raises(ValueError, match="1152"):
        wrapper(x, t=0.5, y=y, cfg_scale=0.0)


# ---------------------------------------------------------------------------
# Test 7: pipeline factory spec validation
# ---------------------------------------------------------------------------


def test_pipeline_factory_spec_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="pipeline_name_must_be_non_empty"):
        DiffusersPipelineSpec(name="")


def test_pipeline_factory_try_import_returns_none_on_missing_module() -> None:
    factory = DiffusersPipelineFactory(
        DiffusersPipelineSpec(
            name="NoSuchPipeline",
            transformer_symbol="this_module_does_not_exist:SomeClass",
        )
    )
    assert factory.resolve_transformer_class() is None
    assert factory.resolve_scheduler_class() is None
    assert factory.resolve_vae_class() is None


def test_pipeline_factory_returns_none_when_weights_path_missing() -> None:
    factory = DiffusersPipelineFactory(
        DiffusersPipelineSpec(
            name="HiDreamImagePipeline",
            transformer_symbol="diffusers:HiDreamImageTransformer2DModel",
            weights_path="/nonexistent/path/should/not/exist",
        )
    )
    assert factory.build() is None
