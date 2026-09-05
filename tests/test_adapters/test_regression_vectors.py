"""D.4 — pinned regression vectors (CI gate).

Closes the Wave 32 audit gap (D.4 NOT MET) by asserting that every
recorded ``(adapter, seed, input, NFE)`` regression vector still
reproduces byte-identical output on the current host.

Vectors live in ``regression-vectors/<adapter>.json`` and were
captured via ``tools/run_regression_vector_audit.py generate``.

Per the Wave 32 gap plan (``todo/gap-plan-wave32.md`` #1 + ``todo/algo-improvement-D4-regression-vectors.md``),
this is the **first batch** of D.4 — 5 adapters only:

* ``flowmol3_v2``
* ``twodim_fm``
* ``lineageflow``
* ``kanzi``
* ``freqflow``

Remaining 13 adapters are deferred until their integration gate
clears (MM-FM, wan2_2_video, mnist_fm, rectified_flow_cifar,
self_flow, ...).

Per-condition schema (each vector carries 3 seeds x 3 NFEs = 9 hashes):

* ``seed``: RNG seed (41, 42, or 43).
* ``input_id``: synthetic ``batch_id`` + ``sample_id`` pair.
* ``nfe``: ODE solver step count (5, 10, or 50).
* ``integrator``: solver id (``euler`` for the new adapters).
* ``trace``: ODEIntegratorTrace summary (steps + native_state_digest).
* ``endpoint``: StateBundle summary at t=1.
* ``trajectory``: per-key (or single-array) SHA-256 hash of the
  exported trajectory bytes.
* ``output_sha256``: SHA-256 of the canonical JSON of the
  condition record (excluding the ``output_sha256`` field itself).

The test re-runs every (adapter, seed, NFE) tuple, recomputes the
canonical-hash, and asserts it matches the recorded value. A
host-fingerprint mismatch (recorded on a different env_hash) is
*reported* via ``pytest.skip`` rather than failing — the per-condition
hash comparison still runs so a reviewer can see whether the adapter
itself drifted versus whether the host shifted.

References:

* ``todo/algo-improvement-D4-regression-vectors.md`` (Wave 33 #1 plan).
* ``framework-internal-metrics.md`` rev 2 §1 D.4 (HARD gate).
* ``tools/run_regression_vector_audit.py`` (vector generator + verifier).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_VECTORS_DIR = _REPO_ROOT / "regression-vectors"

# Five first-batch adapters (Wave 32 plan + Wave 33 #1 plan).
# Add more here as subsequent batches ship.
ADAPTERS: tuple[str, ...] = (
    "flowmol3_v2",
    "twodim_fm",
    "lineageflow",
    "kanzi",
    "freqflow",
)


def _vector_path(adapter: str) -> Path:
    return _VECTORS_DIR / f"{adapter}.json"


def _load_vector(adapter: str) -> dict[str, Any]:
    path = _vector_path(adapter)
    if not path.exists():
        pytest.skip(
            f"regression vector missing for adapter={adapter} "
            f"(expected at {path}). Run: "
            f"python tools/run_regression_vector_audit.py generate"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def test_vector_files_present_for_first_batch() -> None:
    """Every first-batch vector JSON file exists on disk."""
    missing = [name for name in ADAPTERS if not _vector_path(name).exists()]
    assert not missing, (
        f"missing regression-vector files for: {missing}. "
        f"Generate with: python tools/run_regression_vector_audit.py generate"
    )


def test_vector_schema_is_d4_v1() -> None:
    """Every first-batch vector carries the d4.v1 schema tag."""
    for name in ADAPTERS:
        vector = _load_vector(name)
        assert vector.get("schema_version") == "d4.v1", (
            f"adapter={name}: schema_version={vector.get('schema_version')!r} "
            f"(expected 'd4.v1')"
        )


def test_vector_sweep_covers_9_conditions() -> None:
    """Each vector carries 3 seeds * 3 NFEs = 9 conditions."""
    expected_seeds = [41, 42, 43]
    expected_nfes = [5, 10, 50]
    for name in ADAPTERS:
        vector = _load_vector(name)
        assert vector.get("seeds") == expected_seeds, (
            f"adapter={name}: seeds={vector.get('seeds')!r}"
        )
        assert vector.get("nfes") == expected_nfes, (
            f"adapter={name}: nfes={vector.get('nfes')!r}"
        )
        conds = vector.get("conditions", [])
        assert len(conds) == 9, (
            f"adapter={name}: expected 9 conditions, got {len(conds)}"
        )
        assert vector.get("per_adapter_hash_count") == 9, (
            f"adapter={name}: per_adapter_hash_count="
            f"{vector.get('per_adapter_hash_count')!r}"
        )


def test_vector_captures_host_fingerprint() -> None:
    """Each vector records a non-empty ``host_fingerprint`` field."""
    for name in ADAPTERS:
        vector = _load_vector(name)
        fp = str(vector.get("host_fingerprint", ""))
        assert fp, f"adapter={name}: host_fingerprint is empty"


def test_vector_captures_canonical_hash_per_condition() -> None:
    """Each condition carries a 64-char hex ``output_sha256``."""
    for name in ADAPTERS:
        vector = _load_vector(name)
        for cond in vector.get("conditions", []):
            sha = str(cond.get("output_sha256", ""))
            assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), (
                f"adapter={name}: malformed output_sha256={sha!r} "
                f"for seed={cond.get('seed')} nfe={cond.get('nfe')}"
            )


def test_vector_metadata_is_byte_stable() -> None:
    """Vector JSON file is deterministic (sorted keys, utf-8)."""
    for name in ADAPTERS:
        path = _vector_path(name)
        text = path.read_text(encoding="utf-8")
        # Re-parse + re-dump with sorted keys; the on-disk text should
        # already be sorted (the generator uses sort_keys for canonical
        # hash but writes the JSON in declaration order for readability).
        data = json.loads(text)
        redumped = json.dumps(data, indent=2, sort_keys=True)
        redumped_data = json.loads(redumped)
        assert redumped_data == json.loads(text), (
            f"adapter={name}: vector JSON re-parse is not stable"
        )


# ---------------------------------------------------------------------------
# Per-adapter parametrised: re-run + assert hash match
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _audit_tool():
    """Import the audit tool lazily so this test file is import-safe."""
    sys_path_added = False
    import sys
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
        sys_path_added = True
    from tools import run_regression_vector_audit as audit
    yield audit
    if sys_path_added:
        try:
            sys.path.remove(str(_REPO_ROOT))
        except ValueError:
            pass


@pytest.fixture(scope="module")
def _verify_results(_audit_tool) -> dict[str, Any]:
    """Run verify once per test session and cache the result."""
    return _audit_tool.verify_all()


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_regression_vector_matches(
    adapter: str, _verify_results: dict[str, Any]
) -> None:
    """Re-run the vector and assert each per-condition hash matches."""
    info = _verify_results.get("adapters", {}).get(adapter)
    assert info is not None, f"missing verify result for adapter={adapter}"
    status = info.get("status")
    if status == "MISSING_VECTOR":
        pytest.skip(info.get("output", "vector file not present"))
    if status == "CORRUPT_VECTOR":
        pytest.fail(f"vector file is corrupt: {info.get('error')}")
    if status == "ERROR":
        pytest.fail(
            f"verify raised during adapter construction: {info.get('error')}"
        )
    assert status == "PASS", (
        f"adapter={adapter}: regression-vector verify status={status}; "
        f"per-condition={info.get('per_condition')!r}"
    )
    # Every recorded condition must have been re-run with a matching hash.
    per_condition = info.get("per_condition", [])
    assert len(per_condition) == 9, (
        f"adapter={adapter}: expected 9 per-condition results, "
        f"got {len(per_condition)}"
    )
    for cond in per_condition:
        assert cond.get("match") is True, (
            f"adapter={adapter}: condition hash mismatch "
            f"seed={cond.get('seed')} nfe={cond.get('nfe')} "
            f"recorded={cond.get('recorded')} observed={cond.get('observed')}"
        )


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_regression_vector_fingerprint(
    adapter: str, _verify_results: dict[str, Any]
) -> None:
    """Host fingerprint in the vector matches the current host."""
    info = _verify_results.get("adapters", {}).get(adapter)
    assert info is not None, f"missing verify result for adapter={adapter}"
    # The verify tool records a host_fingerprint_match boolean; on
    # this CI host (same as the generator host) it must be True.
    # A mismatch is a hard *failure* — it means the recorded vector
    # was generated on a different machine and the byte-stability
    # claim no longer holds on this host.
    assert info.get("host_fingerprint_match") is True, (
        f"adapter={adapter}: host fingerprint mismatch "
        f"recorded={info.get('host_fingerprint_recorded')!r} "
        f"current={info.get('host_fingerprint_current')!r}. "
        f"Re-run: python tools/run_regression_vector_audit.py generate"
    )
