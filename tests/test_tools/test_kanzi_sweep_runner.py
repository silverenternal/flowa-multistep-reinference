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

    # The pin: the construction in `run_kanzi_sweep` MUST pass
    # either `force_mode="real"` (the CLI-native token from Wave 41.B,
    # which is translated via _ADAPTER_FORCE_MODE_ALIAS to "torch" for
    # the kanzi factory) OR `force_mode="torch"` (the kanzi adapter's
    # native token). Either is acceptable because they both select the
    # real torch mode via the same adapter path.
    real_mode_present = (
        'force_mode="real"' in src_text or 'force_mode="torch"' in src_text
    )
    assert real_mode_present, (
        "Wave 110.B pin: framework_inv_proj arm MUST construct the "
        "KanziAdapter in real (torch) mode via either `force_mode=\"real\"` "
        "(CLI-native token — translated via _ADAPTER_FORCE_MODE_ALIAS) "
        "or `force_mode=\"torch\"` (kanzi adapter's native token). The "
        "synthetic fallback path is incompatible with the Wave 95.P3.C "
        "bridge which requires (B, L, n_channels_decoder=512)."
    )

    # The construction site MUST be inside the framework-mode branch
    # (so the baseline arm is unaffected — Wave 87 baseline byte-stability).
    inv_proj_block = src_text.split(
        'if mode in {"framework_synthetic", "framework_inv_proj"}',
    )[1].split("per_seq_rmsd")[0]
    assert real_mode_present and (
        'force_mode="real"' in inv_proj_block
        or 'force_mode="torch"' in inv_proj_block
    ), (
        "Wave 110.B pin: the `force_mode=\"real\"` (or `force_mode=\"torch\"`) "
        "MUST be inside the "
        "`if mode in {\"framework_synthetic\", \"framework_inv_proj\"}` "
        "branch so the baseline arm's byte-stability is preserved."
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

    The Wave 110.B fix replaces the broken forward with a zero-return
    that preserves the input shape. The trajectory endpoint is then
    equal to the initial state (zeros perturbation + zero velocity),
    which still satisfies the bridge's `(B, L, n_channels_decoder=512)`
    contract without raising.

    The pin is a static text-match against the upstream adapter
    source so the test does not require a torch / kanzi sidecar
    venv to load the real DAE.
    """
    repo_root: Path = REPO_ROOT
    kanzi_path: Path = (
        repo_root / "adaptive_reflow" / "adapters" / "kanzi.py"
    )
    src_text = kanzi_path.read_text(encoding="utf-8")

    # Pin (a): the broken forward path is gone — no
    # `self._dae.encode(x, preprocess=False)` followed by
    # `self._dae.net(x, t, z_BLD=c_BLD)` inside the shim. Wave 112.C-2
    # fail-fasts the placeholder (the Wave 110.B fix returned
    # `torch.zeros_like(x)` and made the framework arm a silent
    # no-op). The synthetic-mode caller short-circuits before the
    # shim is ever invoked; real-mode callers now surface a
    # NotImplementedError instead of silently corrupting the
    # trajectory endpoint.
    assert "raise NotImplementedError" in src_text, (
        "Wave 112.C-2 pin: the shim's `forward()` MUST raise "
        "`NotImplementedError` (the Wave 110.B placeholder is now "
        "fail-fast). The synthetic-mode path "
        "(`self._synthetic_weights is not None`) short-circuits "
        "before this shim is invoked, so framework_synthetic sweeps "
        "are unaffected."
    )

    # Pin (b): the `_torch_velocity_field` docstring claims the
    # shape is `(state_shape,)`-shaped output — this is the bridge's
    # (B, L, n_channels_decoder=512) contract for the real mode.
    torch_vf_idx = src_text.find("def _torch_velocity_field(")
    assert torch_vf_idx != -1, (
        "expected `_torch_velocity_field` definition in "
        f"{kanzi_path.relative_to(repo_root)}"
    )
    torch_vf_block = src_text[torch_vf_idx : torch_vf_idx + 4000]
    assert "out.reshape(state_shape)" in torch_vf_block, (
        "Wave 110.B pin: `_torch_velocity_field` MUST reshape its "
        "output to `state_shape` (the adapter's per-record state "
        "shape = (L, n_channels_decoder=512)) so the bridge's "
        "_apply_project_out_inv receives the correct (B, L, 512) "
        "post-project_out latent."
    )


# ---------------------------------------------------------------------------
# Test 5 (Wave 115.P2 — CUDA device-mismatch regression test):
# The `torch.as_tensor(coords_BLD, dtype=torch.float32, ...)` call that
# feeds `dae.encode` MUST carry `device=dae.device`. Pre-Wave 115.P2
# the call omitted `device=`; when the DAE was on CUDA but the
# input numpy array was implicitly on CPU, the per-record inner loop
# crashed inside `dae.encode` with `RuntimeError: Expected all tensors
# to be on the same device ...`. The sweep's outer `try/except` then
# caught the exception and incremented `n_skipped` for every record,
# silently producing a 0-record JSONL with no error visible to the
# operator. The Wave 115.P2 fix threads `device=dae.device` through so
# any future CPU/CUDA mismatch becomes a loud, fast, attributable
# `AttributeError` early in the constructor path (before the loop)
# rather than a silent 0-record sweep.
#
# The pin is a static text-match against the runner source so the
# test does not require a torch / kanzi sidecar venv to import the
# runner or load the real DAE.
# ---------------------------------------------------------------------------


def test_run_envelope_input_matches_dae_device(runner: Any) -> None:
    """The shared sweep loop's `torch.as_tensor(coords_BLD, ...)` MUST
    carry `device=dae.device` so a CPU/CUDA mismatch crashes early.

    See module-level Test 5 comment for the full Wave 115.P2 root cause.
    The pin is a static source-text match — no DAE / GPU required.
    """
    src_text = _RUNNER_PATH.read_text(encoding="utf-8")

    # Pin (a): the `torch.as_tensor(coords_BLD, ...)` call inside the
    # shared `run_kanzi_sweep` envelope MUST include `device=dae.device`.
    # The pre-Wave 115.P2 call site was:
    #
    #     torch.as_tensor(coords_BLD, dtype=torch.float32),
    #
    # which (with DAE on CUDA) raised silently inside `dae.encode` and
    # produced a 0-record sweep.
    assert (
        "torch.as_tensor(" in src_text
    ), (
        "Wave 115.P2 pin: the shared sweep envelope MUST construct the "
        "encode input via `torch.as_tensor(...)` (not `torch.tensor(...)` "
        "or manual numpy→Tensor conversion). Expected at least one "
        "`torch.as_tensor(` call in the runner source."
    )
    assert (
        "device=dae.device" in src_text
    ), (
        "Wave 115.P2 pin: the shared sweep envelope's `torch.as_tensor` "
        "call MUST carry `device=dae.device` so a CPU/CUDA mismatch "
        "crashes loudly inside `dae.encode` (RuntimeError on cross-device "
        "matmul) instead of silently producing a 0-record JSONL."
    )

    # Pin (b): the device-pin MUST be on the `torch.as_tensor(coords_BLD,`
    # call site (the only one that feeds `dae.encode`), not somewhere
    # unrelated. Scan the call site specifically.
    call_site_idx = src_text.find("torch.as_tensor(\n                            coords_BLD,")
    if call_site_idx == -1:
        # Fallback for slight whitespace variation.
        call_site_idx = src_text.find("torch.as_tensor(coords_BLD,")
    assert call_site_idx != -1, (
        "Wave 115.P2 pin: could not locate the `torch.as_tensor(coords_BLD,` "
        "call site in the runner source — fix may have been applied to "
        "the wrong site or reformatted away from the search pattern."
    )
    # Inspect the next 200 chars after the call — must contain the device pin.
    call_site_block = src_text[call_site_idx : call_site_idx + 400]
    assert "device=dae.device" in call_site_block, (
        "Wave 115.P2 pin: the `device=dae.device` argument MUST be on the "
        "`torch.as_tensor(coords_BLD, ...)` call site itself (so the tensor "
        "input to `dae.encode` matches the DAE's parameter device). Got:\n"
        f"{call_site_block[:200]!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 (Wave 115.P2 — CUDA device-mismatch regression test):
# The diverse-endpoint sweep driver
# ``tools/sweep_kanzi_n1000_diverse.py`` MUST also thread
# ``device=dae.device`` through its `torch.as_tensor(coords_BLD, ...)`
# call inside the re-encode block. This driver is NOT covered by the
# shared `run_kanzi_sweep` envelope (it keeps its own per-record inner
# loop because of the jsonl writer + GPU watchdog + per-record
# `--max-records` semantics). Without the same device pin, the same
# silent-0-record bug would re-surface on this driver.
# ---------------------------------------------------------------------------


def test_sweep_d_kanzi_input_device_in_sync_with_dae() -> None:
    """The diverse-endpoint sweep driver MUST carry `device=dae.device`
    on its `torch.as_tensor(coords_BLD, ...)` call site.

    The diverse driver keeps its own per-record inner loop (jsonl
    writer + GPU watchdog + per-record ``--max-records`` semantics),
    so the shared ``run_kanzi_sweep`` envelope does not cover it.
    Without the same device pin, the Wave 115.P2 root cause would
    re-surface on this driver.

    The pin is a static text-match — no DAE / GPU required.
    """
    diverse_path: Path = REPO_ROOT / "tools" / "sweep_kanzi_n1000_diverse.py"
    src_text = diverse_path.read_text(encoding="utf-8")

    # Pin (a): the diverse driver MUST construct the encode input via
    # `torch.as_tensor(... coords_BLD, ...)` (single-line OR multi-line).
    # The post-Wave 115.P2 source reformats the call to multiple lines
    # to fit the `device=dae.device` argument + the comment block, so
    # we accept either format.
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
        "device=dae.device" in src_text
    ), (
        "Wave 115.P2 pin: the diverse-endpoint sweep driver's "
        "`torch.as_tensor(coords_BLD, ...)` call MUST carry "
        "`device=dae.device` so a CPU/CUDA mismatch crashes loudly "
        "instead of silently producing a 0-record JSONL."
    )

    # Pin (b): the device-pin MUST be on the diverse driver's
    # `torch.as_tensor(... coords_BLD, ...)` call site specifically
    # (within ~400 chars of the call to tolerate the multi-line
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
    assert "device=dae.device" in call_site_block, (
        "Wave 115.P2 pin: the `device=dae.device` argument MUST be on "
        "the diverse driver's `torch.as_tensor(... coords_BLD, ...)` "
        "call site. Got:\n"
        f"{call_site_block[:300]!r}"
    )
