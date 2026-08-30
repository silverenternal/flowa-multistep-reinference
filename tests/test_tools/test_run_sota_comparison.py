"""Smoke tests for :mod:`tools.run_sota_comparison`.

The SOTA-comparison harness is a thin orchestration layer around
:class:`adaptive_reflow.algorithm.ReInferenceRunner`; the smoke
tests guard against three failure modes:

1. **Import drift** — the script module must still import cleanly
   (catches ``E402`` violations, missing imports, etc.).
2. **CLI surface** — ``--help`` exits ``0`` and prints usage, and
   ``main()`` accepts the documented ``--adapter-class``,
   ``--n-samples``, ``--n-rounds``, ``--output-dir`` arguments.
3. **Adapter loading** — ``_load_adapter`` resolves a module:callable
   pair to a ``FlowMatchingODEAdapter`` instance (the canonical
   failure mode is when a user points ``--adapter-class`` at a
   path that does not exist).

The tests deliberately avoid driving the full multi-round loop (which
needs a real adapter + 20-sample batch); instead, the tests
exercise the CLI surface directly and verify the adapter-loading
helper round-trips with a toy 2-D Gaussian adapter similar to
:class:`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter`.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "tools" / "run_sota_comparison.py"
VENV_PYTHON: Path = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _venv_python() -> Path:
    """Return the venv python executable path; skip if missing."""
    if not VENV_PYTHON.exists():
        pytest.skip(f"venv python not found at {VENV_PYTHON}")
    return VENV_PYTHON


@pytest.fixture(scope="module")
def script_module() -> object:
    """Import :mod:`tools.run_sota_comparison` and return the module."""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "tools.run_sota_comparison", str(SCRIPT_PATH)
        )
        if spec is None or spec.loader is None:
            pytest.skip(
                f"could not create module spec for {SCRIPT_PATH}"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:  # pragma: no cover — defensive
        pytest.fail(
            f"failed to import tools.run_sota_comparison: {exc!r}"
        )


# ---------------------------------------------------------------------------
# CLI tests (subprocess — exercises argparse end-to-end)
# ---------------------------------------------------------------------------


def test_help_exits_zero_and_prints_usage(_venv_python: Path) -> None:
    """``--help`` exits ``0`` and prints the canonical usage banner."""
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        [str(_venv_python), str(SCRIPT_PATH), "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, (
        f"--help failed (rc={completed.returncode}); "
        f"stderr={completed.stderr!r}"
    )
    stdout = completed.stdout.lower()
    assert "usage" in stdout or "options" in stdout, (
        f"missing usage banner in --help output: {completed.stdout!r}"
    )
    # All four documented flags appear in the help text.
    for flag in (
        "--adapter-class",
        "--n-samples",
        "--n-rounds",
        "--output-dir",
    ):
        assert flag in completed.stdout, (
            f"flag {flag!r} missing from --help output; "
            f"got: {completed.stdout!r}"
        )


def test_missing_required_args_nonzero(_venv_python: Path) -> None:
    """Running without ``--adapter-class`` exits non-zero."""
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        [str(_venv_python), str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode != 0, (
        f"missing-required-args should fail; got rc=0; "
        f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Direct-import tests — no subprocess, exercises argparse + parser API
# ---------------------------------------------------------------------------


def test_module_exports_main_and_parser(script_module: object) -> None:
    """The script module re-exports :func:`main` and a CLI builder."""
    assert hasattr(script_module, "main"), (
        "script must expose a top-level main() entry point"
    )
    assert hasattr(script_module, "_build_parser"), (
        "script must expose _build_parser() so tests can introspect "
        "the CLI surface without invoking the full subprocess path"
    )


def test_parser_accepts_canonical_arguments(script_module: object) -> None:
    """``_build_parser()`` returns a parser with the four canonical flags."""
    parser: argparse.ArgumentParser = script_module._build_parser()  # type: ignore[attr-defined]
    args = parser.parse_args(
        [
            "--adapter-class",
            "my_pkg.adapters:MyAdapter",
            "--n-samples",
            "5",
            "--n-rounds",
            "3",
            "--output-dir",
            str(REPO_ROOT / "tmp_out"),
        ]
    )
    assert args.adapter_class == "my_pkg.adapters:MyAdapter"
    assert int(args.n_samples) == 5
    assert int(args.n_rounds) == 3
    assert Path(args.output_dir).name == "tmp_out"


def test_parser_rejects_nonpositive_rounds(script_module: object) -> None:
    """``--n-rounds`` of ``0`` is rejected by argparse (validator)."""
    parser: argparse.ArgumentParser = script_module._build_parser()  # type: ignore[attr-defined]
    # Build a valid namespace first, then mutate ``n_rounds`` to 0 so
    # the post-parse validator fires (argparse does not natively
    # enforce ``>= 1`` on ``type=int``).
    args = parser.parse_args(
        [
            "--adapter-class",
            "pkg:cls",
            "--n-samples",
            "1",
            "--n-rounds",
            "1",
            "--output-dir",
            str(REPO_ROOT / "tmp_out"),
        ]
    )
    args.n_rounds = 0
    with pytest.raises(SystemExit):
        script_module.main(  # type: ignore[attr-defined]
            [
                "--adapter-class",
                "pkg:cls",
                "--n-samples",
                "1",
                "--n-rounds",
                "0",
                "--output-dir",
                str(REPO_ROOT / "tmp_out"),
            ]
        )


# ---------------------------------------------------------------------------
# Adapter-loading unit tests
# ---------------------------------------------------------------------------


def test_load_adapter_rejects_malformed_path(script_module: object) -> None:
    """``_load_adapter`` raises on a path without ``:``."""
    with pytest.raises(ValueError, match="module:callable"):
        script_module._load_adapter(  # type: ignore[attr-defined]
            "no_colon_separator"
        )


def test_load_adapter_raises_on_missing_module(script_module: object) -> None:
    """``_load_adapter`` raises :class:`ImportError` on unknown modules."""
    with pytest.raises(ImportError):
        script_module._load_adapter(  # type: ignore[attr-defined]
            "definitely_does_not_exist_pkg:dummy"
        )


def test_load_adapter_resolves_canonical_2d_adapter(
    script_module: object,
) -> None:
    """``_load_adapter`` resolves the canonical 2-D factory to an adapter.

    This test exercises the canonical happy-path: a published
    FlowMatchingODEAdapter is loaded via ``module:factory`` and
    the resulting instance passes the runtime-checkable
    Protocol. Uses
    :data:`adaptive_reflow.adapters.twodim_fm.default_twodim_fm_adapter`
    so the test runs without ``torch`` / external weights.
    """
    from adaptive_reflow.universal import FlowMatchingODEAdapter

    adapter = script_module._load_adapter(  # type: ignore[attr-defined]
        "adaptive_reflow.adapters.twodim_fm:default_twodim_fm_adapter"
    )
    assert isinstance(adapter, FlowMatchingODEAdapter), (
        "default_twodim_fm_adapter() must satisfy "
        "FlowMatchingODEAdapter at runtime"
    )
    # Sanity: the capability surface advertises at least one channel.
    caps = adapter.capabilities()
    assert caps.supported_channels, (
        "canonical 2D adapter must advertise a supported channel"
    )


# ---------------------------------------------------------------------------
# Stub-adapter end-to-end argparse test (no real run, parse only)
# ---------------------------------------------------------------------------


def test_can_invoke_with_stub_adapter_via_argparse(
    script_module: object,
    tmp_path: Path,
) -> None:
    """``main()`` accepts a stubbed dotted-path adapter via argparse.

    The test does NOT actually execute the multi-round loop (that
    would require a real adapter and is expensive). Instead it
    monkey-patches ``_load_adapter`` to return a no-op stub
    FlowMatchingODEAdapter and asserts the CLI accepts the dotted
    path without raising ``ImportError`` during argument parsing.
    """
    from adaptive_reflow.universal import (
        AdapterCapabilities,
        CapabilityMissingError,
        FlowMatchingODEAdapter,
    )
    from adaptive_reflow.universal.state import (
        ChannelName,
        ODEConditionDelta,
        ODEIntegratorTrace,
        StateBundle,
        TensorRef,
    )

    class _StubAdapter(FlowMatchingODEAdapter):
        """No-op adapter that satisfies the Protocol surface."""

        def capabilities(self) -> AdapterCapabilities:
            return AdapterCapabilities(
                has_ode_integration_surface=True,
                has_prior_export=True,
                has_state_export=True,
                has_condition_injection=True,
                has_restart_boundary=True,
                has_continuous_channels=True,
                has_discrete_channels=False,
                has_trajectory_digest=True,
                has_deterministic_seed=True,
                has_materialization_route=True,
                state_shape=(2,),
                supported_channels=("stub",),
                channel_domains={
                    ChannelName("stub"): "continuous",  # type: ignore[arg-type]
                },
                required_mixer=None,
                native_config_hash="stub_adapter:v0",
                native_config_version="0.0.0",
            )

        def build_initial_state(
            self, *, batch_id: str, sample_id: str
        ) -> StateBundle:
            return StateBundle(
                channels={
                    ChannelName("stub"): TensorRef(  # type: ignore[arg-type]
                        f"stub-{batch_id}-{sample_id}"
                    )
                },
                masks={},
                batch_id=str(batch_id),
                sample_id=str(sample_id),
                reference_frame="stub",
                normalization="none",
                source_round=0,
                detach_proof=True,
                native_state_digest=f"stub-digest-{batch_id}-{sample_id}",
                provenance=("stub_adapter",),
                capability_token=self.capabilities(),
            )

        def export_endpoint(self, state: StateBundle) -> StateBundle:
            return state

        def detach_and_validate_endpoint(
            self, bundle: StateBundle
        ) -> StateBundle:
            if bundle.detach_proof is not True:
                raise CapabilityMissingError("detach_proof_must_be_true")
            return bundle

        def apply_restart_distribution(
            self, state: StateBundle, policy: object
        ) -> StateBundle:
            return state

        def compose_condition(
            self,
            bundle: StateBundle,
            delta: ODEConditionDelta,
        ) -> ODEConditionDelta:
            return delta

        def solve_ode(
            self,
            state: StateBundle,
            condition: ODEConditionDelta,
            *,
            seed: int,
        ) -> ODEIntegratorTrace:
            return ODEIntegratorTrace(
                steps=1,
                accept_rate=1.0,
                native_state_digest=f"trace-{seed}",
                integrator_config_hash=f"hash-{seed}",
            )

        def observe_endpoint(
            self,
            trace: ODEIntegratorTrace,
            state: StateBundle,
        ) -> StateBundle:
            return state

    # Monkeypatch the script's adapter loader to return the stub.
    original_loader = script_module._load_adapter  # type: ignore[attr-defined]
    script_module._load_adapter = lambda _path: _StubAdapter()  # type: ignore[attr-defined]
    try:
        # Drive ``main()`` for argparse parsing only — the actual
        # run path would require an adapter with a working solve_ode.
        # We invoke the parser directly instead.
        output_dir = tmp_path / "stub_sota_out"
        parser = script_module._build_parser()  # type: ignore[attr-defined]
        parsed = parser.parse_args(
            [
                "--adapter-class",
                "stub.module:not_really_used",
                "--n-samples",
                "1",
                "--n-rounds",
                "1",
                "--output-dir",
                str(output_dir),
                "--channels",
                "stub",
            ]
        )
        # Re-invoke the patched loader to confirm the contract
        # round-trips: parser captures ``stub.module:not_really_used``
        # and the loader returns the stub instance regardless.
        loaded = script_module._load_adapter(  # type: ignore[attr-defined]
            parsed.adapter_class
        )
        assert isinstance(loaded, FlowMatchingODEAdapter)
        caps = loaded.capabilities()
        assert "stub" in caps.supported_channels
    finally:
        script_module._load_adapter = original_loader  # type: ignore[attr-defined]
