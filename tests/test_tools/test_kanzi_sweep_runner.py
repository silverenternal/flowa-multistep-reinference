"""Regression tests for ``tools._kanzi_sweep_runner``.

Wave 110.A — pin two contracts for ``_synthesize_x_final_synthetic``
that were broken by the Wave 95.P3.C bridge rewrite:

  (1) Shape contract: the function MUST emit ``(L=64, n_channels_decoder=512)``
      — the post-``project_out`` latent space that the bridge's
      ``_apply_project_out_inv`` (Linear 512→4) requires. Pre-Wave 110.A
      the function emitted ``(64, 4)`` which crashed the bridge on a
      matmul shape mismatch (``bridge_failed:RuntimeError`` for every
      record in the framework_synthetic arm — see
      ``docs/audit/wave110-plan.md`` Bug 1 root-cause).
  (2) Seeded determinism: the same ``(record_idx, seed)`` tuple MUST
      produce byte-identical output across calls. The sweep loop
      relies on this for byte-stable regression verification
      (``pytest tests/ -k d4``).

Both tests are stdlib + ``numpy`` + ``pytest`` only (no DAE / GPU /
network). The module is loaded via ``spec_from_file_location`` to keep
the test hermetic and independent of any side effects from
``tools/__init__.py``.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# torch is only present in torch-bearing venvs (Wave 80 Kanzi sidecar,
# wave39_kanzi_venv, etc.). Skip the entire module when missing so the
# rest of the suite still collects on CPU-only / torch-free hosts.
_torch_spec = pytest.importorskip(
    "torch",
    reason=(
        "torch not in venv "
        "(install via `uv pip install torch torchvision diffusers "
        "transformers accelerate`)"
    ),
)

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
_RUNNER_PATH: Path = REPO_ROOT / "tools" / "_kanzi_sweep_runner.py"


def _load_runner() -> Any:
    """Import the runner via ``spec_from_file_location``.

    Mirrors the hermetic import pattern used in
    ``tests/test_tools/test_kanzi_latent_to_coord.py``.
    """
    spec = importlib.util.spec_from_file_location(
        "_kanzi_sweep_runner", str(_RUNNER_PATH),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def runner() -> Any:
    """Lazily import the runner module once per test file."""
    return _load_runner()


# ---------------------------------------------------------------------------
# Test 1: shape contract (Wave 110.A — Bug 1 regression test)
# ---------------------------------------------------------------------------


def test_synthesize_x_final_synthetic_shape_64_512(runner: Any) -> None:
    """``_synthesize_x_final_synthetic`` MUST emit shape ``(L=64, n_channels_decoder=512)``.

    Pre-Wave 110.A this emitted ``(64, 4)`` — correct under the
    Wave 91 bridge contract, but the Wave 95.P3.C bridge rewrite
    now unconditionally applies ``_apply_project_out_inv``
    (Linear 512→4) and crashes on a 4-d input with
    ``bridge_failed:RuntimeError`` (matmul shape mismatch).

    Regression test for Bug 1 — Wave 110.A fix.
    """
    fn = runner._synthesize_x_final_synthetic
    x = fn(record_idx=0, seed=42)
    assert isinstance(x, np.ndarray), (
        f"expected np.ndarray, got {type(x).__name__}"
    )
    assert x.shape == (64, 512), (
        f"Wave 110.A contract: expected shape (64, 512) for the "
        f"post-project_out latent space; got {x.shape}. Pre-Wave 110.A "
        f"this emitted (64, 4) which crashes the Wave 95.P3.C bridge."
    )
    assert x.dtype == np.float64, (
        f"expected float64 to match the adapter numpy contract; got {x.dtype}"
    )
    # Sigma is 1e-3, so the L2 norm of a 64×512 noise matrix should be
    # well under 1.0 (sanity check — protects against accidental
    # scale-up regressions in future refactors).
    norm = float(np.linalg.norm(x))
    assert norm < 1.0, (
        f"sigma=1e-3 N(0, 1) noise on (64, 512) yields expected "
        f"norm ~ 0.18; got {norm:.4f} (>> 1.0 implies a scale-up "
        f"regression)."
    )


# ---------------------------------------------------------------------------
# Test 2: seeded determinism (byte-stability for D.4 regression)
# ---------------------------------------------------------------------------


def test_synthesize_x_final_synthetic_deterministic_seed(
    runner: Any,
) -> None:
    """Two calls with identical ``(record_idx, seed)`` MUST produce
    byte-identical output. Required for D.4 byte-stable regression
    (``pytest tests/ -k d4``).
    """
    fn = runner._synthesize_x_final_synthetic

    # Same record_idx + seed → identical output.
    x1 = fn(record_idx=7, seed=42)
    x2 = fn(record_idx=7, seed=42)
    assert x1.shape == x2.shape == (64, 512)
    assert np.array_equal(x1, x2), (
        "two calls with identical (record_idx, seed) MUST produce "
        "byte-identical output (D.4 byte-stable contract); got diff "
        f"with max abs delta {float(np.max(np.abs(x1 - x2)))}"
    )

    # Different record_idx → different output (per-record diversity).
    x_a = fn(record_idx=0, seed=42)
    x_b = fn(record_idx=1, seed=42)
    assert not np.array_equal(x_a, x_b), (
        "different record_idx MUST yield different output (per-record "
        "diversity is required by the sweep loop; identical across "
        "records would collapse the framework arm)"
    )

    # Different seed → different output (the seed drives the RNG
    # multiplier ``seed * 1_000_003 + record_idx``).
    x_c = fn(record_idx=0, seed=42)
    x_d = fn(record_idx=0, seed=43)
    assert not np.array_equal(x_c, x_d), (
        "different seed MUST yield different output (seed must drive "
        "the RNG so --seed CLI flag produces reproducible but "
        "seed-distinct results)"
    )


# ---------------------------------------------------------------------------
# Test 3 (Wave 110.B — Bug 2 regression test):
# `run_kanzi_sweep(mode="framework_inv_proj", ...)` MUST construct
# the adapter with `force_mode="real"` (CLI-native token). This is the
# pin for the Wave 110.B fix (Wave 41.B introduced `--force-mode real`
# for `run_real_ckpt_eval.py`; Wave 110.B threads the same token
# into the shared sweep loop's framework_inv_proj arm so the velocity
# field wires through the real `_torch_velocity_field` path
# (KANZI_ABSTRACT_STATE_SHAPE → KANZI_REAL_STATE_SHAPE = (64, 512))
# rather than the synthetic (64, 64) path that crashes the bridge.
# ---------------------------------------------------------------------------


def test_framework_inv_proj_construction_uses_real_mode(runner: Any) -> None:
    """The framework_inv_proj arm MUST build the KanziAdapter in real (torch) mode.

    Pre-Wave 110.B the construction silently fell through to the
    abstract / synthetic fallback when the adapter's `_real_state_shape`
    was unset, which made the velocity field emit shape
    ``(64, 64)`` (the abstract ``KANZI_ABSTRACT_STATE_SHAPE``) —
    incompatible with the Wave 95.P3.C bridge which requires
    ``(B, L, n_channels_decoder=512)``.

    The fix pins ``force_mode="torch"`` (the kanzi adapter's native
    token for "real checkpoint loaded"; equivalent to the CLI-native
    ``"real"`` token after translation via
    :data:`_ADAPTER_FORCE_MODE_ALIAS["kanzi"] = {"real": "torch"}` —
    see ``tools/eval/baseline.py:33``) so that:

      * a real Kanzi ckpt at ``--ckpt`` loads the real torch-mode
        encoder (forcing ``KANZI_ABSTRACT_STATE_SHAPE →
        KANZI_REAL_STATE_SHAPE``) and the trajectory endpoint satisfies
        the bridge contract;
      * in the absence of a real ckpt the adapter fails loudly
        (``FileNotFoundError`` from :func:`_resolve_mode`) instead
        of silently producing an off-shape velocity field that
        crashes the bridge on a matmul shape mismatch.

    The pin is a static string-match against the source file so the
    test does not require a torch / kanzi sidecar venv to import the
    runner.
    """
    src_text = _RUNNER_PATH.read_text(encoding="utf-8")

    # The construction site MUST be inside the framework-mode branch
    # (so the baseline arm is unaffected — Wave 87 baseline byte-stability).
    inv_proj_block = src_text.split(
        'if mode in {"framework_synthetic", "framework_inv_proj"}',
    )[1].split("per_seq_rmsd")[0]

    # Pin (a) — Wave 124 Phase 2 contract-drift fix (was Wave 110.B):
    # The framework_inv_proj arm MUST pass a ``force_mode=`` kwarg at the
    # ``default_kanzi_adapter(...)`` call site (so the real torch-mode
    # encoder loads and ``_real_state_shape`` is correct). The runner now
    # threads ``adapter_force_mode`` (a function parameter) instead of a
    # literal ``"real"`` / ``"torch"`` string — see Pin (c) for the
    # default-value check.
    assert "default_kanzi_adapter(" in inv_proj_block, (
        "Wave 124 Phase 2 pin: framework_inv_proj arm MUST call "
        "`default_kanzi_adapter(...)` (the real-mode factory). The "
        "synthetic fallback path is incompatible with the Wave 95.P3.C "
        "bridge which requires (B, L, n_channels_decoder=512)."
    )
    assert "force_mode=" in inv_proj_block, (
        "Wave 124 Phase 2 pin: the `default_kanzi_adapter(...)` call "
        "MUST pass a `force_mode=...` kwarg (the real torch-mode "
        "encoder selection). The synthetic fallback path is incompatible "
        "with the Wave 95.P3.C bridge which requires "
        "(B, L, n_channels_decoder=512)."
    )

    # Pin (b) — Wave 124 Phase 2: the `force_mode=...` kwarg MUST live
    # INSIDE the framework-mode branch so the baseline arm is unaffected
    # (Wave 87 baseline byte-stability). Already verified by the
    # `inv_proj_block` slice above; re-pin for clarity.
    real_mode_present = (
        "force_mode=" in inv_proj_block
    )
    assert real_mode_present, (
        "Wave 124 Phase 2 pin: the `force_mode=` kwarg MUST be inside "
        "the `if mode in {\"framework_synthetic\", \"framework_inv_proj\"}` "
        "branch so the baseline arm's byte-stability is preserved."
    )

    # Pin (c) — Wave 124 Phase 2: the `run_kanzi_sweep(...)` function
    # signature MUST default `adapter_force_mode` to `"torch"` (the
    # kanzi adapter's native token for "real checkpoint loaded";
    # equivalent to the CLI-native `"real"` token after translation
    # via ``_ADAPTER_FORCE_MODE_ALIAS["kanzi"] = {"real": "torch"}`` —
    # see ``tools/eval/baseline.py:33``).
    sig_idx = src_text.find("def run_kanzi_sweep(")
    assert sig_idx != -1, (
        "Wave 124 Phase 2 pin: could not locate `def run_kanzi_sweep(` "
        "in the runner source — the framework-mode branch check above "
        "would be meaningless without a function signature to default."
    )
    sig_block = src_text[sig_idx : sig_idx + 1500]
    assert 'adapter_force_mode: str = "torch"' in sig_block, (
        "Wave 124 Phase 2 pin: the `run_kanzi_sweep(...)` function "
        "signature MUST default `adapter_force_mode` to `\"torch\"` "
        "(real-mode native token — equivalent to the CLI-native "
        "`\"real\"` token via `_ADAPTER_FORCE_MODE_ALIAS`). A change "
        "to `\"synthetic\"` or any other abstract-mode default would "
        "silently fall back to (B, L, 64) — incompatible with the "
        "Wave 95.P3.C bridge."
    )


# ---------------------------------------------------------------------------
# Test 4 (Wave 110.B — Bug 2 regression test):
# The real Kanzi adapter's velocity field MUST emit shape
# (B, L, n_channels_decoder=512) — the post-`project_out` latent
# space the Wave 95.P3.C bridge's `_apply_project_out_inv`
# (Linear 512→4) consumes. Pre-Wave 110.B the shim called
# `_dae.encode(x)` with a (B, L, 512) latent, crashing inside
# `_dae.up` (Linear(3, …)) on a matmul shape mismatch
# `(64x512 and 3x256)`.
# ---------------------------------------------------------------------------


def test_torch_velocity_field_emits_512d_shape(runner: Any) -> None:
    """`_torch_velocity_field` MUST emit shape `(B, L, n_channels_decoder=512)`.

    Pre-Wave 110.B the shim's `forward()` invoked
    `self._dae.encode(x)` with the latent ``x`` of shape
    ``(B, L, 512)`` — but ``_dae.encode`` requires backbone coords
    of shape ``(B, L, 3)`` (its first layer is
    ``nn.Sequential(nn.Linear(3, n_channels_encoder), ...)``).
    Calling encode on the latent crashed inside `_dae.up` on a matmul
    shape mismatch: ``mat1 and mat2 shapes cannot be multiplied
    (64x512 and 3x256)``.

    The Wave 110.B fix replaced the broken forward with a zero-return
    that preserved the input shape. Wave 112.C-2 then fail-fasted the
    placeholder (``raise NotImplementedError``). Wave 113.A finally
    replaced the placeholder with the real backbone-coord migration:
    ``self._dae.encode(x)`` runs on backbone coords ``(B, L, 3)`` and
    returns the codebook-quantized latent ``z`` that the velocity
    field ``self._dae.net(x, t, z_BLD=z)`` consumes. The trajectory
    endpoint then satisfies the bridge's
    ``(B, L, n_channels_decoder=512)`` contract end-to-end.

    The pin is a static text-match against the upstream adapter
    source so the test does not require a torch / kanzi sidecar
    venv to load the real DAE.
    """
    repo_root: Path = REPO_ROOT
    kanzi_path: Path = (
        repo_root / "adaptive_reflow" / "adapters" / "kanzi.py"
    )
    src_text = kanzi_path.read_text(encoding="utf-8")

    # Pin (a) — Wave 124 Phase 2 contract-drift fix (was Wave 112.C-2):
    # The shim's `forward()` MUST wire the real Wave 113.A
    # backbone-coord migration (the two-call upstream pipeline
    # ``self._dae.encode(x)`` -> codebook latent ``z`` -> ``self._dae.net(x, t, z_BLD=z)``).
    # Pre-Wave 113.A the shim raised ``NotImplementedError`` (Wave 112.C-2
    # fail-fast placeholder) — replaced by the Wave 113.A real
    # implementation. The synthetic-mode caller short-circuits before
    # the shim is ever invoked; real-mode callers now run the real
    # backbone-coord pipeline instead of fail-fasting.
    shim_idx = src_text.find("class _KanziDAEShim(")
    assert shim_idx != -1, (
        f"Wave 124 Phase 2 pin: expected `_KanziDAEShim` class in "
        f"{kanzi_path.relative_to(repo_root)} — the shim is what "
        f"`_torch_velocity_field` invokes."
    )
    shim_block = src_text[shim_idx : shim_idx + 3000]
    assert "self._dae.encode(" in shim_block, (
        "Wave 124 Phase 2 pin: the shim's `forward()` MUST call "
        "`self._dae.encode(...)` (the trained encoder + FSQ codebook "
        "step of the Wave 113.A backbone-coord migration). Pre-Wave "
        "113.A this raised `NotImplementedError` (Wave 112.C-2 "
        "fail-fast placeholder); post-Wave 113.A the shim threads the "
        "trained encoder so the velocity field gets a real "
        "codebook-quantized conditioning latent."
    )
    assert "self._dae.net(" in shim_block and "z_BLD=" in shim_block, (
        "Wave 124 Phase 2 pin: the shim's `forward()` MUST call "
        "`self._dae.net(x, t, z_BLD=z)` (the DiT velocity field "
        "consuming the codebook-quantized conditioning latent). "
        "Pre-Wave 113.A this raised `NotImplementedError` (Wave "
        "112.C-2 fail-fast placeholder); post-Wave 113.A the shim "
        "returns the real velocity field instead of fail-fasting."
    )

    # Pin (b): the `_torch_velocity_field` docstring claims the
    # shape is `(state_shape,)`-shaped output — this is the bridge's
    # (B, L, n_channels_decoder=512) contract for the real mode.
    torch_vf_idx = src_text.find("def _torch_velocity_field(")
    assert torch_vf_idx != -1, (
        "expected `_torch_velocity_field` definition in "
        f"{kanzi_path.relative_to(repo_root)}"
    )
    torch_vf_block = src_text[torch_vf_idx : torch_vf_idx + 5000]
    assert "out.reshape(state_shape)" in torch_vf_block, (
        "Wave 110.B pin: `_torch_velocity_field` MUST reshape its "
        "output to `state_shape` (the adapter's per-record state "
        "shape = (L, n_channels_decoder=512)) so the bridge's "
        "_apply_project_out_inv receives the correct (B, L, 512) "
        "post-project_out latent."
    )


# ---------------------------------------------------------------------------
# Test 5 (Wave 115.P2 / Wave 116 — CUDA device-mismatch regression test):
# The `torch.as_tensor(coords_BLD, dtype=torch.float32, ...)` call that
# feeds `dae.encode` MUST carry `device=next(dae.parameters()).device`.
#
# History:
#   Pre-Wave 115.P2: the call omitted `device=`; when the DAE was on CUDA
#     but the input numpy array was implicitly on CPU, the per-record
#     inner loop crashed inside `dae.encode` with
#     `RuntimeError: Expected all tensors to be on the same device ...`.
#     The sweep's outer `try/except` then caught the exception and
#     incremented `n_skipped` for every record, silently producing a
#     0-record JSONL with no error visible to the operator.
#   Wave 115.P2: threads ``device=dae.device`` through so any future
#     CPU/CUDA mismatch becomes a loud ``AttributeError`` on every
#     iteration.
#   Wave 116: ``torch.nn.Module`` does NOT expose a ``.device`` attribute
#     (verified in Wave 115 Phase 3 — ``AttributeError: 'StandInDAE'
#     object has no attribute 'device'``); the correct idiom is
#     ``next(module.parameters()).device``. The 1-LOC fix replaces
#     ``device=dae.device`` with ``device=next(dae.parameters()).device``
#     at BOTH the shared ``run_kanzi_sweep`` envelope site and the
#     diverse-endpoint driver site. Without the fix, every per-record
#     iteration raised ``AttributeError``, was caught by the outer
#     ``try/except``, and silently produced a 0-record sweep — the exact
#     silent-failure mode Wave 115.P2 was trying to surface, but at the
#     wrong attribute name.
#
# The pin is a static text-match against the runner source so the test
# does not require a torch / kanzi sidecar venv to import the runner or
# load the real DAE.
# ---------------------------------------------------------------------------


def test_run_envelope_input_matches_dae_device(runner: Any) -> None:
    """The shared sweep loop's `torch.as_tensor(coords_BLD, ...)` MUST
    carry `device=next(dae.parameters()).device` so a CPU/CUDA mismatch
    crashes early (and any future AttributeError on a wrong attribute
    is loud, not silent).

    See module-level Test 5 comment for the full Wave 115.P2 + Wave 116
    root cause. The pin is a static source-text match — no DAE / GPU
    required.
    """
    src_text = _RUNNER_PATH.read_text(encoding="utf-8")

    # Pin (a): the `torch.as_tensor(coords_BLD, ...)` call inside the
    # shared `run_kanzi_sweep` envelope MUST include the correct device
    # idiom. The pre-Wave 116 source contained ``device=dae.device``
    # which raised ``AttributeError`` on every per-record iteration.
    # We pin the post-Wave 116 correct idiom
    # (``device=next(dae.parameters()).device``) AND assert the broken
    # idiom (``device=dae.device``) is gone.
    assert (
        "torch.as_tensor(" in src_text
    ), (
        "Wave 115.P2 pin: the shared sweep envelope MUST construct the "
        "encode input via `torch.as_tensor(...)` (not `torch.tensor(...)` "
        "or manual numpy→Tensor conversion). Expected at least one "
        "`torch.as_tensor(` call in the runner source."
    )
    assert (
        "device=next(dae.parameters()).device" in src_text
    ), (
        "Wave 116 pin: the shared sweep envelope's `torch.as_tensor` "
        "call MUST carry `device=next(dae.parameters()).device` so a "
        "CPU/CUDA mismatch crashes loudly inside `dae.encode` "
        "(RuntimeError on cross-device matmul) instead of silently "
        "producing a 0-record JSONL. The pre-Wave-116 idiom "
        "`device=dae.device` raises `AttributeError` on every "
        "per-record iteration of `nn.Module` (verified in Wave 115 "
        "Phase 3)."
    )
    assert (
        "device=dae.device" not in src_text
    ), (
        "Wave 116 pin: the broken `device=dae.device` idiom MUST NOT "
        "appear in the runner source. `torch.nn.Module` has no "
        "`.device` attribute; passing `device=dae.device` raises "
        "`AttributeError` on every per-record iteration, which the "
        "outer `try/except` catches and silently swallows into a "
        "0-record sweep."
    )

    # Pin (b): the device-pin MUST be on the `torch.as_tensor(coords_BLD,`
    # call site (the only one that feeds `dae.encode`), not somewhere
    # unrelated. Scan the call site specifically.
    call_site_idx = src_text.find("torch.as_tensor(\n                            coords_BLD,")
    if call_site_idx == -1:
        # Fallback for slight whitespace variation.
        call_site_idx = src_text.find("torch.as_tensor(coords_BLD,")
    assert call_site_idx != -1, (
        "Wave 116 pin: could not locate the `torch.as_tensor(coords_BLD,` "
        "call site in the runner source — fix may have been applied to "
        "the wrong site or reformatted away from the search pattern."
    )
    # Inspect the next 600 chars after the call — must contain the new
    # device pin AND not contain the broken one.
    call_site_block = src_text[call_site_idx : call_site_idx + 600]
    assert (
        "device=next(dae.parameters()).device" in call_site_block
    ), (
        "Wave 116 pin: the `device=next(dae.parameters()).device` "
        "argument MUST be on the `torch.as_tensor(coords_BLD, ...)` "
        "call site itself (so the tensor input to `dae.encode` "
        "matches the DAE's parameter device). Got:\n"
        f"{call_site_block[:300]!r}"
    )
    assert (
        "device=dae.device" not in call_site_block
    ), (
        "Wave 116 pin: the broken `device=dae.device` idiom MUST NOT "
        "appear at the `torch.as_tensor(coords_BLD, ...)` call site. "
        "Got:\n"
        f"{call_site_block[:300]!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 (Wave 115.P2 / Wave 116 — CUDA device-mismatch regression test):
# The diverse-endpoint sweep driver
# ``tools/sweep_kanzi_n1000_diverse.py`` MUST also thread
# ``device=next(dae.parameters()).device`` through its
# `torch.as_tensor(coords_BLD, ...)` call inside the re-encode block.
# This driver is NOT covered by the shared `run_kanzi_sweep` envelope
# (it keeps its own per-record inner loop because of the jsonl writer +
# GPU watchdog + per-record `--max-records` semantics). Without the
# same device pin, the same silent-0-record bug would re-surface on
# this driver.
# ---------------------------------------------------------------------------


def test_sweep_d_kanzi_input_device_in_sync_with_dae() -> None:
    """The diverse-endpoint sweep driver MUST carry
    `device=next(dae.parameters()).device` on its
    `torch.as_tensor(coords_BLD, ...)` call site.

    The diverse driver keeps its own per-record inner loop (jsonl
    writer + GPU watchdog + per-record ``--max-records`` semantics),
    so the shared ``run_kanzi_sweep`` envelope does not cover it.
    Without the same device pin, the Wave 115.P2 / Wave 116 root
    cause would re-surface on this driver.

    The pin is a static text-match — no DAE / GPU required.
    """
    diverse_path: Path = REPO_ROOT / "tools" / "sweep_kanzi_n1000_diverse.py"
    src_text = diverse_path.read_text(encoding="utf-8")

    # Pin (a): the diverse driver MUST construct the encode input via
    # `torch.as_tensor(... coords_BLD, ...)` (single-line OR multi-line).
    # The post-Wave 116 source reformats the call to multiple lines
    # to fit the `device=next(dae.parameters()).device` argument + the
    # comment block, so we accept either format.
    has_as_tensor_call = (
        "torch.as_tensor(coords_BLD," in src_text
        or "torch.as_tensor(\n                            coords_BLD,"
        in src_text
        or "torch.as_tensor(\n                        coords_BLD,"
        in src_text
    )
    assert has_as_tensor_call, (
        "Wave 115.P2 pin: the diverse-endpoint sweep driver MUST construct "
        "the encode input via `torch.as_tensor(... coords_BLD, ...)`. "
        "Expected the call site in `tools/sweep_kanzi_n1000_diverse.py`."
    )
    assert (
        "device=next(dae.parameters()).device" in src_text
    ), (
        "Wave 116 pin: the diverse-endpoint sweep driver's "
        "`torch.as_tensor(coords_BLD, ...)` call MUST carry "
        "`device=next(dae.parameters()).device` so a CPU/CUDA mismatch "
        "crashes loudly instead of silently producing a 0-record JSONL. "
        "The pre-Wave-116 idiom `device=dae.device` raises "
        "`AttributeError` on every per-record iteration of `nn.Module`."
    )
    assert (
        "device=dae.device" not in src_text
    ), (
        "Wave 116 pin: the broken `device=dae.device` idiom MUST NOT "
        "appear in the diverse-endpoint sweep driver. "
        "`torch.nn.Module` has no `.device` attribute; passing "
        "`device=dae.device` raises `AttributeError` on every "
        "per-record iteration, which the outer `try/except` catches "
        "and silently swallows into a 0-record sweep."
    )

    # Pin (b): the device-pin MUST be on the diverse driver's
    # `torch.as_tensor(... coords_BLD, ...)` call site specifically
    # (within ~600 chars of the call to tolerate the multi-line
    # reformatting the fix introduced).
    call_site_idx = -1
    for needle in (
        "torch.as_tensor(coords_BLD,",
        "torch.as_tensor(\n                            coords_BLD,",
        "torch.as_tensor(\n                        coords_BLD,",
        "torch.as_tensor(\n                        coords_BLD, dtype=torch.float32,",
    ):
        call_site_idx = src_text.find(needle)
        if call_site_idx != -1:
            break
    assert call_site_idx != -1, (
        "Wave 115.P2 pin: could not locate the diverse driver's "
        "`torch.as_tensor(... coords_BLD, ...)` call site — fix may "
        "have been applied to the wrong site or reformatted away "
        "from all known patterns."
    )
    call_site_block = src_text[call_site_idx : call_site_idx + 600]
    assert (
        "device=next(dae.parameters()).device" in call_site_block
    ), (
        "Wave 116 pin: the `device=next(dae.parameters()).device` "
        "argument MUST be on the diverse driver's "
        "`torch.as_tensor(... coords_BLD, ...)` call site. Got:\n"
        f"{call_site_block[:300]!r}"
    )
    assert (
        "device=dae.device" not in call_site_block
    ), (
        "Wave 116 pin: the broken `device=dae.device` idiom MUST NOT "
        "appear at the diverse driver's `torch.as_tensor(... "
        "coords_BLD, ...)` call site. Got:\n"
        f"{call_site_block[:300]!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 (Wave 116 — end-to-end N=1 regression test for the REAL
# CUDA bug):
#
# The static-pin tests above (Test 5 + Test 6) guard the textual
# contract on disk. This test guards the *behavioural* contract in
# motion: when the full ``run_kanzi_sweep`` per-record loop runs end-
# to-end on a tiny CPU ``torch.nn.Module`` stand-in (NOT the real
# 500MB DAE checkpoint — too heavy), the pre-fix code raises
# ``AttributeError: 'StandInDAE' object has no attribute 'device'`` on
# every per-record iteration, the outer ``try/except`` swallows it,
# and the sweep silently emits a 0-record JSONL. The post-fix code
# uses ``next(dae.parameters()).device`` and processes the record
# normally.
#
# This is the closest CPU-only reproduction of the CUDA bug the
# runner was hiding: a wrong-attribute access on ``nn.Module`` that
# never reaches the user's screen because the inner try/except
# increments ``n_skipped`` instead of propagating.
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("requires_torch")
def test_run_kanzi_sweep_end_to_end_n1_no_attribute_error(
    runner: Any, tmp_path: Path,
) -> None:
    """End-to-end N=1 regression for Wave 116: ``device=dae.device``
    on a ``torch.nn.Module`` stand-in silently produces 0 records.

    Pre-fix (``device=dae.device``): every per-record iteration of the
    inner loop raises ``AttributeError`` ("'StandInDAE' object has no
    attribute 'device'"), the outer ``try/except`` catches it, and
    the sweep silently emits a summary JSONL with
    ``n_records_processed: 0``. The user sees a "successful" sweep
    that actually processed zero records — the exact failure mode
    Wave 115.P2 was supposed to surface.

    Post-fix (``device=next(dae.parameters()).device``): the inner
    loop resolves the device via the module's parameters, the
    re-encode call returns, and ``n_records_processed`` reaches 1.

    The test uses a tiny 2-layer ``nn.Linear`` stand-in (NOT the
    real Kanzi DAE — the real ckpt is 500MB and would slow the test
    suite by 30+ seconds per run). The stand-in exposes just enough
    surface for ``run_kanzi_sweep(mode="baseline")`` to exercise the
    full per-record loop:

      * ``encode(x, preprocess=...)`` → 4-tuple whose last element
        is ``idx_BL`` (shape ``(B, L)`` int64)
      * ``decode(idx_BL)`` → ``(B, L, 3)`` float tensor
      * ``quantize.codebook_size`` (int attribute)
      * ``quantize.project_out.weight.shape[0]`` (Linear weight)

    We patch ``kanzi.DAE.from_pretrained`` via ``monkeypatch`` to
    return the stand-in instead of attempting the 500MB ckpt load.
    """
    import json

    import torch
    import torch.nn as nn

    # ---- 1. Build a 2-layer Linear stand-in (NOT the real DAE) ----
    class _StandInQuantize(nn.Module):
        """Stand-in for the real Kanzi ``quantize`` submodule.

        Provides the two attributes ``run_kanzi_sweep(mode="baseline")``
        reads:

          * ``codebook_size`` (int) — used at line 568 of the runner
            to size the vocab for codebook metrics.
          * ``project_out.weight.shape[0]`` (Linear) — used at line
            573 of the runner to compute ``n_decoder``.
        """

        def __init__(self) -> None:
            super().__init__()
            self.codebook_size = 4096
            # Linear(512, 512) gives .weight.shape == (512, 512),
            # so .weight.shape[0] == 512 == the real DAE's n_decoder.
            self.project_out = nn.Linear(512, 512)

    class StandInDAE(nn.Module):
        """Tiny CPU stand-in for the real Kanzi DAE.

        Methods mirror the DAE surface ``run_kanzi_sweep(mode="baseline")``
        consumes (no other surface is read in baseline mode):

          * ``encode(x, preprocess=...)`` returns a 4-tuple
            ``(z, mu, logvar, idx_BL)`` where the runner unpacks via
            ``*_, idx_BL = dae.encode(...)``.
          * ``decode(idx_BL)`` returns a ``(B, L, 3)`` float tensor
            (zero-valued — the test doesn't care about the value,
            only that the call succeeds).
          * ``quantize`` is an ``_StandInQuantize`` submodule with
            ``codebook_size`` and ``project_out``.

        A throw-away ``nn.Linear(3, 4)`` is added so the module has
        at least one ``Parameter`` — the post-fix idiom
        ``next(dae.parameters()).device`` requires it. Without any
        parameters, ``next(dae.parameters())`` would raise
        ``StopIteration``.
        """

        def __init__(self) -> None:
            super().__init__()
            self.quantize = _StandInQuantize()
            # Throw-away parameters so ``next(dae.parameters()).device``
            # is well-defined. Not exercised by the loop body — the
            # test only cares that the device-resolve line succeeds.
            self._throwaway = nn.Linear(3, 4)

        def encode(
            self, x: torch.Tensor, preprocess: bool = False,
        ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
            assert x.dim() == 3, f"expected (B, L, 3) input; got shape {tuple(x.shape)}"
            B, L, _ = x.shape
            # Return a 4-tuple; the runner only consumes the last
            # element via ``*_, idx_BL = dae.encode(...)``.
            idx_BL = torch.zeros(B, L, dtype=torch.int64)
            return (x, x, x, idx_BL)

        def decode(self, idx_BL: torch.Tensor) -> torch.Tensor:
            B, L = idx_BL.shape
            return torch.zeros(B, L, 3, dtype=torch.float32)

    stand_in = StandInDAE().eval()

    # ---- 2. Patch kanzi.DAE.from_pretrained to return the stand-in ----
    # The runner does ``from kanzi import DAE, kabsch_rmsd`` lazily,
    # so patching the class attribute on the real kanzi module is
    # sufficient. The kanzi_venv's pip-installed ``kanzi`` package
    # is importable, and the test relies on that for the import.
    import kanzi

    def _fake_from_pretrained(path: str | Path) -> StandInDAE:
        # The runner calls ``DAE.from_pretrained(str(ckpt)).eval()``;
        # ``.eval()`` is inherited from ``nn.Module`` so it works
        # on the stand-in too.
        return stand_in

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            kanzi.DAE, "from_pretrained", _fake_from_pretrained,
        )

        # ---- 3. Create a tiny input file with 1 valid record ----
        # ``parse_record`` accepts comma-separated floats whose count
        # is a multiple of 3. Two atoms → 6 floats.
        input_file = tmp_path / "coords.txt"
        input_file.write_text(
            "0.0,1.0,2.0,3.0,4.0,5.0\n", encoding="utf-8",
        )

        # ---- 4. Call run_kanzi_sweep(mode="baseline", max_records=1) ----
        out_dir = tmp_path / "out"

        # Pre-fix: AttributeError raised by ``device=dae.device`` on
        # nn.Module — caught by the outer try/except, increments
        # n_skipped, n_processed stays at 0.
        # Post-fix: ``next(dae.parameters()).device`` resolves to
        # CPU, the inner encode/decode calls succeed, n_processed
        # reaches 1.
        runner.run_kanzi_sweep(
            mode="baseline",
            output_dir=str(out_dir),
            seed=0,
            max_records=1,
            nfe_steps=10,
            input_path=input_file,
            # ckpt_path is unused because from_pretrained is mocked,
            # but the runner constructs Path() on it so we pass a
            # tmp path that doesn't have to exist.
            ckpt_path=tmp_path / "fake_does_not_exist.pt",
        )
    finally:
        monkeypatch.undo()

    # ---- 5. Assert n_records_processed == 1 (not 0) ----
    summary_path = out_dir / "kanzi_n1000_paper_metrics.json"
    assert summary_path.exists(), (
        f"expected summary at {summary_path} — the sweep should have "
        f"written a summary JSON for mode='baseline'. Missing summary "
        f"implies the loop raised before completion."
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["n_records_processed"] == 1, (
        f"Wave 116 regression: expected n_records_processed=1 (the "
        f"input file has exactly 1 valid record). Pre-fix the loop "
        f"silently produced 0 because `device=dae.device` raised "
        f"`AttributeError` on every per-record iteration of the "
        f"inner loop, the outer `try/except` caught it, and "
        f"`n_skipped` incremented instead of propagating. Got "
        f"n_records_processed={summary['n_records_processed']}."
    )


# ---------------------------------------------------------------------------
# Test 8 (Wave 122 Phase 2 — regression test for the framework_inv_proj
# pre-loop inverse-projection fix):
# `_synthesize_x_final_real(mode="framework_inv_proj", decoder=...)` MUST
# call `kanzi_latent_to_coords()` BEFORE `adapter.solve_ode(...)` to
# convert the initial state `(L, 512)` latent → `(L, 3)` backbone coords
# so the velocity field shim's `DAE.encode(x)` (which expects `(B, L, 3)`
# raw backbone coords) does not crash on a matmul shape mismatch
# (`RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512
# and 3x256)` — Wave 121 P4 NEW deeper bug, distinct from the Wave 120
# shape-validator bug fixed in `kanzi.py:1085`).
#
# The fix is **additive**: the `decoder` + `mode` kwargs default to
# `None`, so existing call sites (and the existing Wave 110.A
# shape-contract regression test for `_synthesize_x_final_synthetic`)
# remain byte-identical. The inverse projection is ONLY activated when
# BOTH `decoder is not None` AND `mode="framework_inv_proj"` are passed.
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("requires_torch")
def test_synthesize_x_final_real_inv_proj_calls_latent_to_coords_bridge(
    runner: Any,
) -> None:
    """Regression for Wave 121 P4 architectural mismatch: framework_inv_proj
    arm must call kanzi_latent_to_coords() before solve_ode to convert
    latent → backbone coords.

    Pre-Wave 122 Phase 2, ``_synthesize_x_final_real`` called
    ``adapter.solve_ode(...)`` directly with the ``(L, 512)`` latent
    initial state, which crashed inside ``DAE.encode(self.up)`` with
    ``RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512
    and 3x256)`` (Wave 121 P4 NEW deeper bug). The Phase 2 fix
    transforms the initial state to ``(L, 3)`` backbone coords via the
    Wave 95.P3.B trained-inverse bridge BEFORE ``solve_ode`` so the
    velocity field shim receives ``(B, L, 3)`` input (which
    ``DAE.encode`` accepts).

    The test patches ``tools.kanzi_latent_to_coord.kanzi_latent_to_coords``
    to a mock that records call args + returns a ``(1, 64, 3)`` array,
    and uses a minimal fake adapter whose ``solve_ode`` method records
    the bundle it received (so we can introspect the ``x0`` shape
    stored in ``_native_states[digest]["x0"]``). Asserts:

      1. ``kanzi_latent_to_coords`` was called at least once.
      2. ``adapter.solve_ode`` was called.
      3. The ``x0`` shape at solve_ode time is ``(64, 3)`` (NOT
         ``(64, 512)``), confirming the inverse projection ran.

    The test is stdlib + numpy + pytest only — no DAE / GPU / network
    required (the DAE is replaced by a minimal fake; the bridge is
    replaced by a mock that returns a deterministic ``(1, 64, 3)``
    array).
    """
    import dataclasses
    import sys as _sys

    # ---- 1. Build a minimal fake adapter that records solve_ode inputs ----
    # We need a real StateBundle + ODEIntegratorTrace for the runner to
    # unpack cleanly. Use the production dataclasses (frozen, so we
    # build via the constructor).

    # ChannelName and TensorRef are imported by the runner via local
    # import inside ``_synthesize_x_final_real`` — but for the fake
    # adapter below we need them too. Import them here so the test
    # is self-contained.
    # Avoid hard-coded imports that would couple the test to the
    # full adapter module chain — only pull in what's strictly needed
    # to build StateBundle / ODEIntegratorTrace.
    from adaptive_reflow.adapters._adapter_common import make_ref
    from adaptive_reflow.universal.state import (
        ODEIntegratorTrace,
        StateBundle,
    )

    class _FakeAdapter:
        """Minimal adapter stand-in for the framework_inv_proj regression test.

        Surfaces consumed by ``_synthesize_x_final_real``:

          * ``build_initial_state(batch_id, sample_id)`` — populates
            ``_native_states[digest]["x0"]`` with a ``(64, 512)``
            deterministic seeded random latent; returns a minimal
            ``StateBundle`` whose ``native_state_digest`` matches the
            cache key.
          * ``solve_ode(bundle, cond, *, seed)`` — records the
            bundle's ``native_state_digest`` so the test can look up
            the post-inverse-projection ``x0`` shape; returns a
            minimal ``ODEIntegratorTrace`` whose
            ``native_state_digest`` is distinct from the bundle's
            (so the runner takes the defensive-fallback path and
            returns the (now (64, 3) coords) x0 unchanged).

        We deliberately use a NEW ``digest`` for the trace so the
        runner's defensive-fallback branch returns the post-projection
        ``x0`` (which now has shape (64, 3)) — this avoids needing to
        populate the trajectory cache.
        """

        def __init__(self) -> None:
            # dict (NOT NativeStateCache) for simplicity — the runner
            # only calls .get(), which both support identically.
            self._native_states: dict[str, dict[str, Any]] = {}
            self._solve_ode_input: dict[str, Any] | None = None
            self._call_count = {"solve_ode": 0}
            # Wave 124 Agent 1 — Wave 122 P2 inverse-projection fix
            # makes the runner call ``adapter.set_traj_shape(...)``
            # before ``adapter.solve_ode(...)`` so the solver honors
            # the actual ``(L, 3)`` backbone-coord shape instead of
            # force-reshaping to ``_real_state_shape``. The fake
            # adapter accepts but ignores the override (its
            # ``solve_ode`` echoes whatever ``x0`` was stored).
            self._traj_shape_override: tuple[int, ...] | None = None

        def set_traj_shape(
            self, shape: tuple[int, ...] | None,
        ) -> None:
            """Wave 124 Agent 1 stub — accept and ignore the shape.

            Mirrors :meth:`KanziAdapter.set_traj_shape`'s signature so
            the runner's call site doesn't raise
            ``AttributeError: '_FakeAdapter' object has no attribute
            'set_traj_shape'``. The fake ``solve_ode`` below does NOT
            introspect the override (it echoes ``x0`` verbatim), so
            a no-op stub is correct.
            """
            self._traj_shape_override = (
                tuple(int(s) for s in shape) if shape is not None else None
            )

        def build_initial_state(
            self, *, batch_id: str, sample_id: str,
        ) -> StateBundle:
            # Deterministic seeded random latent (L=64, n_channels_decoder=512).
            # The shape (64, 512) matches the post-`project_out` space
            # that the real KanziAdapter.build_initial_state emits.
            seed = abs(hash((batch_id, sample_id))) % (2**31)
            x0 = (
                np.random.default_rng(seed)
                .standard_normal((64, 512))
                .astype(np.float64)
            )
            digest = f"fake_digest::{batch_id}::{sample_id}"
            self._native_states[digest] = {"x0": x0}
            bundle = StateBundle(
                channels={
                    # The actual ChannelName / TensorRef content
                    # doesn't matter — the runner doesn't introspect
                    # them in this codepath.
                    "protein_latent": make_ref(
                        "fake:kanzi:latent:initial",
                        "latent:initial",
                        batch=batch_id, sample=sample_id,
                    ),
                },
                masks={},
                batch_id=batch_id,
                sample_id=sample_id,
                reference_frame="world",
                normalization="none",
                source_round=0,
                detach_proof=True,
                native_state_digest=digest,
                provenance=("wave122-p2-fake",),
            )
            return bundle

        def solve_ode(
            self, state: StateBundle, cond: Any, *, seed: int,
        ) -> ODEIntegratorTrace:
            self._call_count["solve_ode"] += 1
            x0 = self._native_states.get(
                state.native_state_digest, {},
            ).get("x0", np.zeros((0,), dtype=np.float64))
            self._solve_ode_input = {
                "digest": state.native_state_digest,
                "x0_shape": tuple(x0.shape),
            }
            # Use a DIFFERENT digest so the runner takes the
            # defensive-fallback path and returns the post-projection
            # x0 (which is now (64, 3) coords in nm after the
            # inverse-projection block ran).
            traj_digest = f"traj_digest::{state.native_state_digest}"
            self._native_states[traj_digest] = {
                "x0": x0,  # echo the post-projection x0
            }
            return ODEIntegratorTrace(
                steps=1,
                accept_rate=1.0,
                native_state_digest=traj_digest,
                integrator_config_hash="fake:wave122-p2",
            )

    # ---- 2. Patch kanzi_latent_to_coords at the tools module level ----
    # The runner does ``from tools.kanzi_latent_to_coord import
    # kanzi_latent_to_coords`` LOCALLY inside the inverse-projection
    # block — patching the attribute on the source module still
    # works because Python imports are by module attribute lookup.
    bridge_calls: list[dict[str, Any]] = []

    def _mock_kanzi_latent_to_coords(latent, decoder, fsq_quantizer, **kwargs):
        # Record what was passed so the test can assert call-site args.
        bridge_calls.append({
            "latent_shape": tuple(np.asarray(latent).shape),
            "decoder_is_decoder": decoder is _decoder_obj,
            "n_steps": kwargs.get("n_steps"),
            "seed": kwargs.get("seed"),
        })
        # Return (1, L=64, 3) coords in Angstrom — the standard bridge
        # output shape. The runner will reshape to (-1, 3) and divide
        # by 10.0 to get nm, so the final stored x0 shape is (64, 3).
        return np.zeros((1, 64, 3), dtype=np.float64)

    # A trivial decoder stand-in (the mock bridge only needs to see
    # that it was passed the same object).
    class _FakeDecoder:
        quantize = None  # never touched by the mock bridge

    _decoder_obj = _FakeDecoder()

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords",
            _mock_kanzi_latent_to_coords,
        )

        # ---- 3. Call _synthesize_x_final_real ----
        fake_adapter = _FakeAdapter()
        out = runner._synthesize_x_final_real(
            adapter=fake_adapter, record_idx=0,
            seed=42, decoder=_decoder_obj, mode="framework_inv_proj",
        )
    finally:
        monkeypatch.undo()

    # ---- 4. Assert kanzi_latent_to_coords was called ----
    assert len(bridge_calls) >= 1, (
        "Wave 122 Phase 2 pin: framework_inv_proj arm MUST call "
        "`tools.kanzi_latent_to_coord.kanzi_latent_to_coords` BEFORE "
        "`adapter.solve_ode` to convert the initial-state (L, 512) "
        "latent → (L, 3) backbone coords (the Wave 95.P3.B "
        "trained-inverse bridge path). Pre-fix the function called "
        "`adapter.solve_ode` directly with the (L, 512) latent, which "
        "crashed inside `DAE.encode(self.up)` with "
        "`RuntimeError: mat1 and mat2 shapes cannot be multiplied "
        "(64x512 and 3x256)` (Wave 121 P4 NEW deeper bug). The fix "
        f"is ADDITIVE — the `decoder` + `mode` kwargs default to "
        f"`None`. Got {len(bridge_calls)} bridge call(s)."
    )
    # Assert the bridge received the original (L, 512) latent (NOT
    # anything pre-processed) and the same decoder the caller passed.
    assert bridge_calls[0]["latent_shape"] == (64, 512), (
        "Wave 122 Phase 2 pin: the bridge MUST receive the raw "
        f"(L=64, n_channels_decoder=512) initial-state latent — got "
        f"latent_shape={bridge_calls[0]['latent_shape']}. The bridge "
        f"applies the Wave 95.P3.B Linear(512→4) trained inverse to "
        f"this latent and then `DAE.decode` to produce (B=1, L, 3) "
        f"backbone coords in Angstrom."
    )
    assert bridge_calls[0]["decoder_is_decoder"], (
        "Wave 122 Phase 2 pin: the bridge MUST receive the same "
        "`decoder` object the caller passed (so the Linear(512→4) "
        f"weights + DAE.decode weights are coherent). Got "
        f"decoder_is_decoder={bridge_calls[0]['decoder_is_decoder']}."
    )

    # ---- 5. Assert adapter.solve_ode was called ----
    assert fake_adapter._call_count["solve_ode"] == 1, (
        "Wave 122 Phase 2 pin: `adapter.solve_ode` MUST be called "
        "exactly once per `_synthesize_x_final_real` invocation. "
        f"Got {fake_adapter._call_count['solve_ode']} call(s)."
    )
    assert fake_adapter._solve_ode_input is not None, (
        "Wave 122 Phase 2 pin: `adapter.solve_ode` MUST be called "
        "and record the bundle's `native_state_digest` so the test "
        "can introspect the post-inverse-projection `x0` shape. "
        "Got `None` (solve_ode was never invoked)."
    )

    # ---- 6. Assert adapter.solve_ode received (L, 3) x0 input ----
    # The whole point of the Wave 122 Phase 2 fix: solve_ode must see
    # (L, 3) backbone coords (so the velocity field's `DAE.encode(x)`
    # accepts the input) — NOT the raw (L, 512) latent that the
    # adapter's `build_initial_state` emits.
    x0_shape_at_solve_ode = fake_adapter._solve_ode_input["x0_shape"]
    assert x0_shape_at_solve_ode == (64, 3), (
        "Wave 122 Phase 2 pin: `adapter.solve_ode` MUST receive "
        f"`(L=64, 3)` backbone coords as the initial state — NOT the "
        f"raw `(L=64, 512)` post-`project_out` latent. Pre-fix the "
        f"`x0` was `(64, 512)` and `DAE.encode(x)` crashed inside "
        f"`DAE.up` (`nn.Linear(3, 256)`) on a matmul shape mismatch. "
        f"Got x0_shape={x0_shape_at_solve_ode}. The fix applies the "
        f"Wave 95.P3.B trained Linear(512→4) inverse + `DAE.decode` "
        f"to convert (L, 512) latent → (L, 3) backbone coords BEFORE "
        f"`adapter.solve_ode` is called."
    )

    # ---- 7. Assert the returned x_final is the post-projection coords ----
    # The runner's defensive-fallback path returns `entry["x0"]` when
    # no `"trajectory"` key is present in the trace's native_states
    # entry. The fake `solve_ode` echoes the (now (64, 3) coords)
    # `x0` into the trace's `_native_states`, so the returned
    # `x_final` should be (64, 3) — confirming the inverse projection
    # end-to-end propagated through the integration.
    assert out.shape == (64, 3), (
        "Wave 122 Phase 2 pin: the `_synthesize_x_final_real` "
        "return value MUST carry the post-inverse-projection "
        f"`(L=64, 3)` coords shape end-to-end. Got out.shape="
        f"{out.shape}. This is the shape that the downstream "
        f"`kanzi_latent_to_coords` bridge call in `run_kanzi_sweep` "
        f"line 626 receives as `x_final` — note that the runner's "
        f"second bridge call expects the raw (L, 512) latent "
        f"contract (the bridge applies the Linear(512→4) inverse + "
        f"`DAE.decode`), so a future wave may also need to skip the "
        f"second bridge call for the framework_inv_proj arm; for "
        f"Wave 122 Phase 2 the focus is the pre-loop inverse "
        f"projection that unblocks `adapter.solve_ode` from the "
        f"matmul shape mismatch."
    )


# ---------------------------------------------------------------------------
# Test 9 (Wave 122 Phase 4 — DAE FSQ stochasticity seeding regression):
# The runner MUST set ``torch.manual_seed(int(seed) * 1_000_003 + int(...))``
# before each DAE forward pass (encode / decode / bridge) so that the
# FSQ stochasticity inside the DAE is reproducible per
# ``(seed, record_idx)`` pair.
#
# Background (Wave 121 P2 root-cause):
#   Pre-Wave 122 Phase 4 the runner seeded the global torch RNG once at
#   sweep entry (``torch.manual_seed(int(seed))`` — Wave 108.A) but the
#   DAE's FSQ stochasticity is sample-dependent and re-sampled per
#   record. Two runs with ``--seed 42`` vs ``--seed 7`` therefore drifted
#   by up to 0.131 Å on the max-outlier RMSD field (only the max outlier
#   drifts; aggregate means stay within 0.004 Å). The fix threads a
#   per-record ``torch.manual_seed(int(seed) * 1_000_003 + int(...))``
#   call before each DAE call site, mirroring the existing
#   ``np.random.default_rng(int(seed) * 1_000_003 + int(record_idx))``
#   pattern at ``tools/_kanzi_sweep_runner.py:331``.
#
# The pin is a runtime behavioural test: the test mocks the
# ``kanzi_latent_to_coords`` bridge to capture
# ``torch.initial_seed()`` at entry (BEFORE the bridge's own internal
# ``torch.manual_seed(int(seed))`` call which is inside the real bridge),
# then calls ``_synthesize_x_final_real(seed=42, record_idx=0,1,2)``
# three times and asserts:
#
#   1. The captured torch seed differs across record_idx (per-record
#      seeding, not global seeding).
#   2. The captured torch seed is deterministic for the same
#      ``(seed, record_idx)`` pair across calls (byte-stable).
#   3. The captured torch seed follows the
#      ``int(seed) * 1_000_003 + int(record_idx)`` pattern (matches
#      the np.random.default_rng contract at line 331).
#
# The test is hermetic — stdlib + numpy + pytest + torch only; no DAE /
# GPU / network required (the DAE is replaced by a minimal fake; the
# bridge is replaced by a mock that captures the torch seed at entry
# and returns a deterministic ``(1, 64, 3)`` array).
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("requires_torch")
def test_dae_seed_threading_is_per_record(
    runner: Any,
) -> None:
    """Regression for Wave 122 P4 DAE FSQ stochasticity: torch.manual_seed
    must be set per ``(seed, record_idx)`` before DAE call so that the
    max-outlier RMSD is reproducible across ``--seed`` values.

    The test mocks the ``kanzi_latent_to_coords`` bridge to capture
    ``torch.initial_seed()`` at entry (before the bridge's internal
    ``torch.manual_seed(int(seed))`` reseeds), calls
    ``_synthesize_x_final_real`` with ``seed=42`` and three different
    ``record_idx`` values, then asserts the captured seeds follow the
    ``int(seed) * 1_000_003 + int(record_idx)`` pattern and are
    deterministic across repeated calls.
    """
    import torch

    from adaptive_reflow.adapters._adapter_common import make_ref
    from adaptive_reflow.universal.state import (
        ODEIntegratorTrace,
        StateBundle,
    )

    # ---- 1. Build a minimal fake adapter (same pattern as Test 8) ----
    class _FakeAdapter:
        """Minimal adapter stand-in for the per-record seeding test.

        Surfaces consumed by ``_synthesize_x_final_real``:

          * ``build_initial_state(batch_id, sample_id)`` — populates
            ``_native_states[digest]["x0"]`` with a ``(64, 512)``
            deterministic seeded random latent; returns a minimal
            ``StateBundle``.
          * ``solve_ode(bundle, cond, *, seed)`` — returns a minimal
            ``ODEIntegratorTrace`` whose ``native_state_digest`` is
            distinct from the bundle's (so the runner takes the
            defensive-fallback path and returns the post-bridge ``x0``
            unchanged).
        """

        def __init__(self) -> None:
            self._native_states: dict[str, dict[str, Any]] = {}
            # Wave 124 Agent 1 — see Test 8 ``_FakeAdapter`` for the
            # rationale. The runner's call site
            # (``adapter.set_traj_shape(x0_coords_nm.shape)`` at
            # ``tools/_kanzi_sweep_runner.py:432``) requires the fake
            # adapter to expose the method; the per-record seeding
            # test does NOT introspect the override so a no-op stub
            # is correct.
            self._traj_shape_override: tuple[int, ...] | None = None

        def set_traj_shape(
            self, shape: tuple[int, ...] | None,
        ) -> None:
            """Wave 124 Agent 1 stub — accept and ignore the shape.

            Mirrors :meth:`KanziAdapter.set_traj_shape`'s signature so
            the runner's call site doesn't raise
            ``AttributeError: '_FakeAdapter' object has no attribute
            'set_traj_shape'``.
            """
            self._traj_shape_override = (
                tuple(int(s) for s in shape) if shape is not None else None
            )

        def build_initial_state(
            self, *, batch_id: str, sample_id: str,
        ) -> StateBundle:
            x0 = (
                np.random.default_rng(
                    abs(hash((batch_id, sample_id))) % (2**31),
                )
                .standard_normal((64, 512))
                .astype(np.float64)
            )
            digest = f"fake_digest::{batch_id}::{sample_id}"
            self._native_states[digest] = {"x0": x0}
            bundle = StateBundle(
                channels={
                    "protein_latent": make_ref(
                        "fake:kanzi:latent:initial",
                        "latent:initial",
                        batch=batch_id, sample=sample_id,
                    ),
                },
                masks={},
                batch_id=batch_id,
                sample_id=sample_id,
                reference_frame="world",
                normalization="none",
                source_round=0,
                detach_proof=True,
                native_state_digest=digest,
                provenance=("wave122-p4-seed-fake",),
            )
            return bundle

        def solve_ode(
            self, state: StateBundle, cond: Any, *, seed: int,
        ) -> ODEIntegratorTrace:
            traj_digest = f"traj_digest::{state.native_state_digest}"
            x0 = self._native_states.get(
                state.native_state_digest, {},
            ).get("x0", np.zeros((0,), dtype=np.float64))
            self._native_states[traj_digest] = {"x0": x0}
            return ODEIntegratorTrace(
                steps=1,
                accept_rate=1.0,
                native_state_digest=traj_digest,
                integrator_config_hash="fake:wave122-p4-seed",
            )

    # ---- 2. Mock the bridge to capture torch.initial_seed() at entry ----
    # The runner does ``from tools.kanzi_latent_to_coord import
    # kanzi_latent_to_coords`` LOCALLY inside the framework_inv_proj
    # block — patching the attribute on the source module works because
    # Python imports are by module attribute lookup. The mock captures
    # the torch seed at entry (BEFORE the real bridge would have
    # called its own internal ``torch.manual_seed(int(seed))`` reseed)
    # so we can verify the runner's per-record seeding is in effect.
    captured_seeds: list[int] = []

    def _mock_kanzi_latent_to_coords(latent, decoder, fsq_quantizer, **kwargs):
        captured_seeds.append(int(torch.initial_seed()))
        # Return (1, L=64, 3) coords in Angstrom — the standard bridge
        # output shape. The runner will reshape to (-1, 3) and divide
        # by 10.0 to get nm, so the final stored x0 shape is (64, 3).
        return np.zeros((1, 64, 3), dtype=np.float64)

    class _FakeDecoder:
        quantize = None  # never touched by the mock bridge

    _decoder_obj = _FakeDecoder()

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords",
            _mock_kanzi_latent_to_coords,
        )

        # ---- 3. Call _synthesize_x_final_real with record_idx=0,1,2 ----
        for record_idx in (0, 1, 2):
            runner._synthesize_x_final_real(
                adapter=_FakeAdapter(), record_idx=record_idx,
                seed=42, decoder=_decoder_obj, mode="framework_inv_proj",
            )
    finally:
        monkeypatch.undo()

    # ---- 4. Assert the captured seeds differ per record_idx ----
    assert len(captured_seeds) == 3, (
        "Wave 122 Phase 4 pin: the runner MUST call the DAE forward "
        "pass once per ``_synthesize_x_final_real`` invocation "
        f"(expected 3 bridge calls for record_idx=0,1,2). Got "
        f"{len(captured_seeds)} call(s) — the per-record seeding fix "
        f"is only effective if the DAE call site is exercised per "
        f"record."
    )
    assert captured_seeds[0] != captured_seeds[1], (
        "Wave 122 Phase 4 pin: torch seed MUST differ across "
        f"record_idx (per-record seeding, not global). Got "
        f"captured_seeds[0]={captured_seeds[0]} == "
        f"captured_seeds[1]={captured_seeds[1]} — the runner is "
        f"NOT setting torch.manual_seed per record before the DAE "
        f"forward pass, so FSQ stochasticity collapses to a global "
        f"seed and the max-outlier RMSD drifts across --seed values."
    )
    assert captured_seeds[1] != captured_seeds[2], (
        "Wave 122 Phase 4 pin: torch seed MUST differ across "
        f"record_idx (per-record seeding, not global). Got "
        f"captured_seeds[1]={captured_seeds[1]} == "
        f"captured_seeds[2]={captured_seeds[2]}."
    )
    assert captured_seeds[0] != captured_seeds[2], (
        "Wave 122 Phase 4 pin: torch seed MUST differ across "
        f"record_idx (per-record seeding, not global). Got "
        f"captured_seeds[0]={captured_seeds[0]} == "
        f"captured_seeds[2]={captured_seeds[2]}."
    )

    # ---- 5. Assert the captured seeds follow the np pattern ----
    # The np.random.default_rng pattern at line 331 is
    # ``int(seed) * 1_000_003 + int(record_idx)``. The torch
    # counterpart MUST match so the two RNGs stay aligned across
    # the sweep.
    expected_seeds = [
        42 * 1_000_003 + 0,
        42 * 1_000_003 + 1,
        42 * 1_000_003 + 2,
    ]
    assert captured_seeds == expected_seeds, (
        "Wave 122 Phase 4 pin: the torch seed threading MUST follow "
        "the ``int(seed) * 1_000_003 + int(record_idx)`` pattern "
        "to match the np.random.default_rng contract at line 331. "
        f"Got captured_seeds={captured_seeds}, expected={expected_seeds}. "
        f"A drift of >0 here would mean the torch and np RNGs are "
        f"no longer aligned across the sweep loop."
    )

    # ---- 6. Assert determinism: same (seed, record_idx) → same seed ----
    # Re-run the same calls and confirm the captured seeds are
    # byte-identical. This is the "byte-stable" contract the sweep
    # loop relies on for regression verification.
    captured_seeds_run2: list[int] = []

    def _mock_kanzi_latent_to_coords_run2(
        latent, decoder, fsq_quantizer, **kwargs,
    ):
        captured_seeds_run2.append(int(torch.initial_seed()))
        return np.zeros((1, 64, 3), dtype=np.float64)

    monkeypatch2 = pytest.MonkeyPatch()
    try:
        monkeypatch2.setattr(
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords",
            _mock_kanzi_latent_to_coords_run2,
        )
        for record_idx in (0, 1, 2):
            runner._synthesize_x_final_real(
                adapter=_FakeAdapter(), record_idx=record_idx,
                seed=42, decoder=_decoder_obj, mode="framework_inv_proj",
            )
    finally:
        monkeypatch2.undo()

    assert captured_seeds_run2 == captured_seeds, (
        "Wave 122 Phase 4 pin: the per-record torch seed MUST be "
        "byte-stable across repeated invocations with the same "
        f"``(seed, record_idx)`` pair. Got run1={captured_seeds} vs "
        f"run2={captured_seeds_run2}. A drift here means the torch "
        f"seed threading depends on hidden global state (e.g., the "
        f"call counter or wall-clock) instead of being a pure "
        f"function of ``(seed, record_idx)``."
    )

    # ---- 7. Assert a different --seed produces a different seed pattern ----
    # The whole point of the fix is to make the torch seed depend on
    # ``--seed`` (so different --seed values produce different
    # stochasticity). For seed=7 vs seed=42, the captured seeds MUST
    # differ.
    captured_seeds_seed7: list[int] = []

    def _mock_kanzi_latent_to_coords_seed7(
        latent, decoder, fsq_quantizer, **kwargs,
    ):
        captured_seeds_seed7.append(int(torch.initial_seed()))
        return np.zeros((1, 64, 3), dtype=np.float64)

    monkeypatch3 = pytest.MonkeyPatch()
    try:
        monkeypatch3.setattr(
            "tools.kanzi_latent_to_coord.kanzi_latent_to_coords",
            _mock_kanzi_latent_to_coords_seed7,
        )
        for record_idx in (0, 1, 2):
            runner._synthesize_x_final_real(
                adapter=_FakeAdapter(), record_idx=record_idx,
                seed=7, decoder=_decoder_obj, mode="framework_inv_proj",
            )
    finally:
        monkeypatch3.undo()

    expected_seeds_seed7 = [
        7 * 1_000_003 + 0,
        7 * 1_000_003 + 1,
        7 * 1_000_003 + 2,
    ]
    assert captured_seeds_seed7 != captured_seeds, (
        "Wave 122 Phase 4 pin: the per-record torch seed MUST depend "
        "on the ``--seed`` CLI flag. Got identical captured seeds "
        f"for seed=7 vs seed=42: run_seed7={captured_seeds_seed7} vs "
        f"run_seed42={captured_seeds}. This means the torch seed "
        f"threading is not consuming the ``seed`` kwarg at all — the "
        f"FSQ stochasticity would be identical regardless of "
        f"``--seed``, which is the exact Wave 121 P2 regression."
    )
    assert captured_seeds_seed7 == expected_seeds_seed7, (
        "Wave 122 Phase 4 pin: the per-record torch seed for seed=7 "
        "MUST follow the ``int(seed) * 1_000_003 + int(record_idx)`` "
        "pattern. Got "
        f"captured_seeds_seed7={captured_seeds_seed7}, "
        f"expected={expected_seeds_seed7}."
    )
