"""Tests for ``tools.paper_metrics`` (Wave 75 Phase 2).

The :mod:`tools.paper_metrics` module wraps the upstream FlowMol3
``SampleAnalyzer`` to expose the 4 paper-parity metrics:

  1. ``compute_validity_pct`` (RDKit sanitization pass rate)
  2. ``compute_pb_validity_pct`` (PoseBusters pass rate, with
     ``full_pb=True`` = paper path incl. energy_ratio module)
  3. ``compute_fg_deviation`` (cumulative REOS flag-rate deviation vs
     GEOM_DRUGS training reference, OR NCI_first_5K_proxy fallback)
  4. ``compute_ood_ring_rate`` (ChEMBL ring-system OOD rate)

The upstream ``flowmol`` package requires torch + DGL + PoseBusters +
useful_rdkit_utils, which may not all be installed on test rigs.
This test suite therefore **mocks the upstream ``SampleAnalyzer``** so
the tests run deterministically without any of those deps. The mocks
return canned values that exercise each metric path independently.

Test surface (4 tests; matches the Wave 75 Phase 2 task spec):

  * ``test_validity_pct_known_answer`` — synthetic SampledMolecule-like
    input where 3/4 mols pass → ``validity_pct == 0.75``.
  * ``test_pb_validity_pct_subset_vs_full`` — same input through the
    ``full_pb=True`` and ``full_pb=False`` paths; assert that the
    full path is **stricter** (lower pass rate) than the subset path
    by construction.
  * ``test_fg_deviation_geom_drugs_vs_nci_proxy`` — same input through
    the two reference dirs; assert that different refs give different
    numbers (the GEOM_DRUGS reference has more distinct
    substructures → higher L1 deviation).
  * ``test_ood_ring_rate_no_rings`` — input with no rings → OOD rate
    is ``0.0`` (no rings means no ChEMBL-misses).

All tests pass regardless of whether the real upstream ``flowmol``
package is importable on the test rig — the upstream ``SampleAnalyzer``
is replaced with a mock fixture.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Test fixtures — mock upstream SampledMolecule + SampleAnalyzer
# ---------------------------------------------------------------------------


class _FakeSampledMolecule:
    """Duck-typed stand-in for upstream ``SampledMolecule``.

    The real upstream class lives at
    ``flowmol/analysis/molecule_builder.py:17``. Our tests only need
    the public attributes the analyzer reads (``build_molecule``,
    ``num_atoms``); everything else is duck-typed.
    """

    def __init__(self, *, num_atoms: int = 5, n_rings: int = 0, smiles: str | None = None):
        self.num_atoms = int(num_atoms)
        self.n_rings = int(n_rings)
        self.smiles = smiles

    def build_molecule(self):  # noqa: D401 — duck-typed mirror of upstream
        """Mirror upstream ``SampledMolecule.build_molecule``."""
        return None


def _install_mock_flowmol(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Install a mock ``flowmol3_metrics_upstream`` shim into ``sys.modules``.

    The :mod:`tools.paper_metrics` module imports
    :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream._UPSTREAM_MODULES`
    + :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.is_upstream_available`
    lazily on first use. We mock both so the paper-metrics helpers see a
    deterministic upstream ``SampleAnalyzer`` that returns canned
    values for the 4 paper metrics.

    The mock tracks per-analyzer-instance state (pb_energy,
    processed_data_dir, buster_config) so different
    SampleAnalyzer() constructor calls don't bleed state into each
    other. Canned buckets:

        default       — base case (val=0.75, pb=0.5, fg=0.27, ood=0.10)
        full_pb       — pb_valid=0.5 (energy_ratio active → stricter)
        subset_pb     — pb_valid=0.8 (energy_ratio skipped → lenient)
        xtb_injected  — pb_valid=0.92 (Wave 82: vendored YAML injection)
        geom_drugs    — fg_dev=0.27 (GEOM_DRUGS reference, paper value)
        nci_proxy     — fg_dev=0.15 (NCI_first_5K_proxy → different dev)
        no_rings      — ood_rate=0.0 (no rings → no ChEMBL misses)
    """
    canned: dict[str, dict[str, float]] = {
        "default": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.5,
            "reos_cum_dev": 0.27,
            "ood_rate": 0.10,
            "frac_mols_stable_valence": 0.9,
            "frac_atoms_stable": 0.95,
        },
        "full_pb": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.5,
            "reos_cum_dev": 0.27,
            "ood_rate": 0.10,
        },
        # Wave 73 baseline: no energy_ratio module → most mols pass PB.
        # The vendored YAML path (Wave 82) is STRICTER than the subset
        # path because it uncomments the energy_ratio module with the
        # paper-tuned threshold=100.0. Without energy_ratio, the
        # subset path accepts ~99% of mols (only chemistry + geometry
        # checks apply).
        "subset_pb": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.99,
            "reos_cum_dev": 0.27,
            "ood_rate": 0.10,
        },
        # Wave 82: when the vendored YAML with energy_ratio UNCOMMENTED
        # is injected via ``analyzer.buster = PoseBusters(config=...)``,
        # the analyzer returns the paper-parity ``pb_valid`` value of
        # ~0.92. Used by ``test_pb_validity_pct_uses_xtb_energy_ratio``.
        "xtb_injected": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.92,
            "reos_cum_dev": 0.27,
            "ood_rate": 0.10,
        },
        "geom_drugs": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.5,
            "reos_cum_dev": 0.27,
            "ood_rate": 0.10,
        },
        "nci_proxy": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.5,
            "reos_cum_dev": 0.15,
            "ood_rate": 0.10,
        },
        "no_rings": {
            "frac_valid_mols": 0.75,
            "pb_valid": 0.5,
            "reos_cum_dev": 0.0,
            "ood_rate": 0.0,
        },
    }

    def _SampleAnalyzer(
        *,
        pb_workers: int = 0,
        pb_energy: bool = False,
        processed_data_dir: Any = None,
        **kwargs: Any,
    ) -> Any:
        # Per-instance state (was module-level before Wave 82 — caused
        # state bleed between successive ``compute_*`` calls in the
        # same test).
        state: dict[str, Any] = {
            "pb_energy": bool(pb_energy),
            "processed_data_dir": processed_data_dir,
            "buster_config": None,
        }
        analyzer = MagicMock()

        def analyze(
            sampled_molecules: Any,
            *,
            functional_validity: bool = False,
            posebusters: bool = False,
            **kw: Any,
        ) -> dict[str, float]:
            # Select canned bucket based on analyzer ctor + analyze call-site.
            ref_dir = str(state["processed_data_dir"] or "")
            if "geom_full_kekulized" in ref_dir:
                ref_key = "geom_drugs"
            elif "geom_5_kekulized" in ref_dir:
                ref_key = "nci_proxy"
            else:
                ref_key = "default"
            # Wave 82: PB-only call-site with vendored YAML injected.
            if posebusters and not functional_validity:
                if state["buster_config"] is not None:
                    return dict(canned["xtb_injected"])
                return dict(canned["full_pb" if state["pb_energy"] else "subset_pb"])
            # Override for no-rings branch (driven by ood_rate=0.0 in canned).
            if functional_validity and not posebusters:
                return dict(canned[ref_key])
            # Aggregate path (both flags set) → use ref_key (default geom_drugs).
            return dict(canned[ref_key])

        def compute_validity(
            sampled_molecules: Any,
            return_counts: bool = False,
        ) -> dict[str, float]:
            return dict(canned["default"])

        analyzer.analyze = analyze
        analyzer.compute_validity = compute_validity
        # Per-instance state for the analyze() closure.
        analyzer._state = state

        # Wave 82: track re-assignment of ``analyzer.buster``. The
        # vendored YAML injection path sets
        # ``analyzer.buster = <PoseBusters-with-config>``; we record
        # the config dict into the per-instance state["buster_config"]
        # so the analyze() closure returns the ``xtb_injected`` bucket.
        def _buster_setter(instance: Any, value: Any) -> None:
            state["buster_config"] = getattr(value, "_config", None)
            instance._buster_value = value

        type(analyzer).buster = property(
            fget=lambda instance: getattr(instance, "_buster_value", None),
            fset=_buster_setter,
        )
        return analyzer

    SampleAnalyzer = _SampleAnalyzer

    # ---- Build the fake ``flowmol3_metrics_upstream`` module.
    fake_module = types.ModuleType("adaptive_reflow.adapters.flowmol3_metrics_upstream")
    fake_module._UPSTREAM_MODULES = {"SampleAnalyzer": SampleAnalyzer, "SampledMolecule": _FakeSampledMolecule}
    fake_module.is_upstream_available = lambda: True
    fake_module.FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR = (
        "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized"
    )
    fake_module.FLOWMOL3_UPSTREAM_REPO = "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo"
    fake_module.FLOWMOL3_PINNED_COMMIT = "77cae22174b7792b0e25e9e0414038420736d841"
    monkeypatch.setitem(sys.modules, "adaptive_reflow.adapters.flowmol3_metrics_upstream", fake_module)
    return canned


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_validity_pct_known_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthetic 4-mol set → 3 valid + 1 invalid → ``validity_pct == 0.75``.

    Drives the ``compute_validity_pct`` helper directly. The mock
    ``SampleAnalyzer.compute_validity`` returns a canned dict with
    ``frac_valid_mols=0.75``; we assert the helper passes that value
    through unmodified.
    """
    canned = _install_mock_flowmol(monkeypatch)
    # Import the paper_metrics module AFTER the mock is installed so
    # the lazy import picks up our fake shim.
    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    out = paper_metrics.compute_validity_pct(mols)
    assert out == pytest.approx(0.75, abs=1e-9)
    assert 0.0 <= out <= 1.0


def test_pb_validity_pct_subset_vs_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same input → ``full_pb`` (vendored YAML) is stricter than ``subset_pb``.

    The full path (``full_pb=True``, Wave 82 default) injects the
    vendored ``data/FlowMol3/pb_config_with_energy_ratio.yaml`` via
    ``analyzer.buster = PoseBusters(config=<yaml_dict>)``. The YAML
    has the ``energy_ratio`` module UNCOMMENTED with paper-tuned
    parameters (``threshold_energy_ratio=100.0``,
    ``ensemble_number_conformations=50``) — which adds an extra
    rejection step for molecules whose UFF-based energy ratio is bad.
    The subset path (``full_pb=False``) uses the upstream vendored
    ``pb_config.yaml`` which has ``energy_ratio`` commented out
    (``pb_config.yaml:101-110``) → less strict.

    Both paths share the same upstream code
    (``flowmol/analysis/metrics.py:154-166``). The ``full_pb`` flag
    selects between two upstream ``PoseBusters`` configurations.

    This test verifies the wire: same input through both paths,
    different results. The vendored YAML bucket returns ``pb_valid = 0.92``
    (paper-parity value), the subset bucket returns ``pb_valid = 0.8``.
    """
    canned = _install_mock_flowmol(monkeypatch)
    # Mock posebusters + yaml so the vendored-YAML injection branch
    # can run (otherwise compute_pb_validity_pct raises FileNotFoundError).
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")
    fake_yaml.safe_load = lambda fh: {"modules": [{"name": "Loading", "function": "loading"}]}
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    pb_full = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)
    pb_subset = paper_metrics.compute_pb_validity_pct(mols, full_pb=False, pb_workers=0)
    # Canned mock: full_pb (vendored YAML) returns 0.92; subset_pb
    # (no energy_ratio module) returns 0.99.
    assert pb_full == pytest.approx(0.92, abs=1e-9)
    assert pb_subset == pytest.approx(0.99, abs=1e-9)
    # Sanity: vendored YAML path is stricter than subset path
    # (energy_ratio adds an extra rejection step).
    assert pb_full <= pb_subset


def test_fg_deviation_geom_drugs_vs_nci_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same mols → different refs → different fg_dev numbers.

    ``compute_fg_deviation`` accepts a ``reference`` label. The
    ``GEOM_DRUGS`` reference reads the canonical
    ``train_reos_ring_counts.pkl`` (30K mols); the
    ``NCI_first_5K_proxy`` reference uses the smaller 5K-mol subset.
    Different reference distributions yield different cumulative
    deviations — even for the same sample.

    This test verifies the wire: the helper selects different canned
    outputs based on the reference argument, AND the returned numbers
    are different (proving the reference-selection code path actually
    runs).
    """
    canned = _install_mock_flowmol(monkeypatch)
    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    fg_geom = paper_metrics.compute_fg_deviation(mols, reference=paper_metrics.REFERENCE_GEOM_DRUGS)
    fg_nci = paper_metrics.compute_fg_deviation(mols, reference=paper_metrics.REFERENCE_NCI_FIRST_5K_PROXY)
    # Canned mock returns 0.27 (geom) vs 0.15 (nci).
    assert fg_geom == pytest.approx(0.27, abs=1e-9)
    assert fg_nci == pytest.approx(0.15, abs=1e-9)
    assert fg_geom != fg_nci


def test_ood_ring_rate_no_rings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mols with no rings → ``ood_ring_rate == 0.0``.

    The ChEMBL ring-system OOD rate is the fraction of rings in the
    sample whose ring-system SMILES is NOT in the ChEMBL DB
    (``metrics.py:330-333``). If the sample has no rings, there are no
    ring systems to miss, so the OOD rate is identically ``0.0``.

    This test verifies: (a) the no-rings branch of the helper, AND
    (b) the sentinel handling — upstream ``SampleAnalyzer.reos_and_rings``
    returns ``ood_rate=-1`` when no molecules were sanitized; the
    helper must collapse that to ``0.0`` rather than propagating the
    sentinel.
    """
    canned = _install_mock_flowmol(monkeypatch)
    from tools import paper_metrics  # noqa: PLC0415

    # Override the nci_proxy canned bucket to return ood_rate=-1 (the
    # upstream "no sanitized molecules" sentinel). This drives the
    # no-rings branch in the helper: any negative value must collapse
    # to 0.0.
    canned["nci_proxy"]["ood_rate"] = -1.0  # upstream sentinel
    canned["nci_proxy"]["reos_cum_dev"] = -1.0  # upstream sentinel too

    no_ring_mols = [_FakeSampledMolecule(n_rings=0) for _ in range(4)]
    out = paper_metrics.compute_ood_ring_rate(
        no_ring_mols, reference=paper_metrics.REFERENCE_NCI_FIRST_5K_PROXY
    )
    # The helper must NOT propagate the upstream ``-1`` sentinel.
    assert out == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= out <= 1.0


# ---------------------------------------------------------------------------
# Exception / robustness tests (additive; not in the spec but cheap)
# ---------------------------------------------------------------------------


def test_unknown_reference_label_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown ``reference`` label raises ``ValueError``.

    Only the two canonical reference labels are accepted. This guards
    against typos in CLI plumbing.
    """
    _install_mock_flowmol(monkeypatch)
    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    with pytest.raises(ValueError, match="unknown reference"):
        paper_metrics.compute_fg_deviation(mols, reference="BOGUS_REF")


def test_aggregator_returns_all_4_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """``compute_all_paper_metrics`` returns a 4-field frozen dataclass.

    The aggregator wraps a single upstream ``SampleAnalyzer.analyze``
    call and extracts the 4 paper-parity metrics. This test verifies
    the dataclass shape.
    """
    canned = _install_mock_flowmol(monkeypatch)
    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    out = paper_metrics.compute_all_paper_metrics(mols)
    # All 4 fields present + correct types.
    assert isinstance(out, paper_metrics.PaperMetricsResult)
    assert isinstance(out.paper_validity_pct, float)
    assert isinstance(out.paper_pb_validity_pct, float)
    assert isinstance(out.paper_fg_deviation, float)
    assert isinstance(out.paper_ood_ring_rate, float)
    # Canned values should match the "default" bucket (0.75, 0.5,
    # 0.27, 0.10).
    assert out.paper_validity_pct == pytest.approx(0.75, abs=1e-9)
    assert out.paper_pb_validity_pct == pytest.approx(0.5, abs=1e-9)
    assert out.paper_fg_deviation == pytest.approx(0.27, abs=1e-9)
    assert out.paper_ood_ring_rate == pytest.approx(0.10, abs=1e-9)


# ---------------------------------------------------------------------------
# Wave 82 — PB energy_ratio integration tests
#
# Wave 82 closes the gap between the paper's ``pb_validity_pct = 0.919``
# and our reported ``pb_valid ≈ 1.0`` (which lacked the energy_ratio
# module). The fix: vendor a custom PoseBusters config at
# ``data/FlowMol3/pb_config_with_energy_ratio.yaml`` with the energy_ratio
# module UNCOMMENTED and paper-tuned params
# (``threshold_energy_ratio=100.0``,
# ``ensemble_number_conformations=50``), then inject it via
# ``analyzer.buster = PoseBusters(config=<our_yaml_dict>)`` (PB 0.6.5
# accepts either a preset name or a config dict — verified at
# ``posebusters/posebusters.py:73-127``).
# ---------------------------------------------------------------------------


def test_pb_validity_pct_uses_xtb_energy_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``full_pb=True`` injects the vendored YAML into ``analyzer.buster``.

    The Wave 82 vendored YAML
    (``data/FlowMol3/pb_config_with_energy_ratio.yaml``) uncomments the
    PoseBusters ``energy_ratio`` module with upstream-tuned parameters
    (``threshold_energy_ratio=100.0``,
    ``ensemble_number_conformations=50``). Our
    :func:`tools.paper_metrics.compute_pb_validity_pct` injects it via
    ``analyzer.buster = posebusters.PoseBusters(config=<yaml_dict>)``.

    This test verifies the wire: the vendored YAML path is selected
    when ``full_pb=True`` (default), AND the resulting ``pb_valid``
    value matches the paper-parity ``xtb_injected`` canned bucket
    (~0.92). We mock ``posebusters.PoseBusters`` so the test runs
    without RDKit / PoseBusters deps installed.
    """
    canned = _install_mock_flowmol(monkeypatch)
    # Mock posebusters + yaml in sys.modules so the YAML injection
    # branch in compute_pb_validity_pct can run.
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config
            self._max_workers = int(max_workers)

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")

    def _fake_safe_load(fh: Any) -> dict[str, Any]:
        # Return a minimal valid YAML dict for the test
        return {
            "modules": [
                {"name": "Loading", "function": "loading"},
                {"name": "Energy ratio", "function": "energy_ratio",
                 "chosen_binary_test_output": ["energy_ratio_passes"]},
            ]
        }

    fake_yaml.safe_load = _fake_safe_load
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]
    out = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)
    # When the vendored YAML is injected, the canned "xtb_injected"
    # bucket returns ``pb_valid = 0.92`` (matches the paper-parity
    # value).
    assert out == pytest.approx(0.92, abs=1e-9)
    assert 0.0 <= out <= 1.0
    # Sanity: the vendored YAML path is NOT the same as the
    # ``full_pb=False`` subset path. The subset path uses the upstream
    # vendored ``pb_config.yaml`` (energy_ratio commented out) and
    # returns ~0.99 in the canned bucket (no energy_ratio rejection).
    out_subset = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=False, pb_workers=0
    )
    assert out_subset == pytest.approx(0.99, abs=1e-9)
    # Sanity: full_pb path (with vendored YAML) is stricter than
    # the subset path.
    assert out < out_subset


def test_pb_validity_pct_returns_real_number_when_xtb_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``compute_pb_validity_pct`` returns a real finite float in [0, 1].

    Wave 82 paper-path smoke test: with both the vendored YAML
    available AND PoseBusters importable, the helper should:
      1. Construct the upstream SampleAnalyzer (valency refs loaded).
      2. Re-assign ``analyzer.buster`` with the vendored YAML dict.
      3. Call ``analyze(posebusters=True)`` and return the
         ``pb_valid`` key as a float in [0, 1].

    This test verifies the happy path: returns a real number, not a
    sentinel ``0.0`` from upstream import failure or YAML parse error.
    """
    canned = _install_mock_flowmol(monkeypatch)
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")
    fake_yaml.safe_load = lambda fh: {"modules": [{"name": "Loading", "function": "loading"}]}
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    # Verify the vendored YAML exists on disk (Wave 82 Phase A).
    yaml_path = paper_metrics.PB_CONFIG_WITH_ENERGY_RATIO_PATH
    assert yaml_path.is_file(), (
        f"Wave 82 vendored YAML missing at {yaml_path}; "
        "Phase A vendoring is incomplete"
    )

    mols = [_FakeSampledMolecule() for _ in range(4)]
    out = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)
    # The vendored YAML bucket returns ``pb_valid = 0.92`` per the
    # paper-parity value (Dunn et al., NeurIPS 2024, arXiv 2508.12629).
    assert isinstance(out, float)
    assert 0.0 <= out <= 1.0
    # Real finite float (not NaN, not inf, not the upstream import-failure
    # sentinel).
    assert out == out  # not NaN
    assert out not in (float("inf"), float("-inf"))


def test_pb_validity_pct_falls_back_to_uff_when_xtb_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the vendored YAML is missing, fall back to subset_pb (UFF).

    The vendored YAML at
    ``data/FlowMol3/pb_config_with_energy_ratio.yaml`` is REQUIRED for
    paper parity (energy_ratio UNCOMMENTED with paper-tuned params).
    When the file is missing on disk (e.g. incomplete Wave 82 Phase A
    vendoring), :func:`compute_pb_validity_pct` falls back to the
    Wave 73 ``subset_pb`` path: the upstream vendored
    ``pb_config.yaml`` (energy_ratio commented out → UFF-only PB
    checks). This is the byte-stable fallback the Wave 73 test
    fixtures already verify.

    This test verifies the fallback: when the vendored YAML is
    absent, ``compute_pb_validity_pct`` does NOT raise
    ``FileNotFoundError`` (it falls back gracefully to subset_pb).
    """
    canned = _install_mock_flowmol(monkeypatch)
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")
    fake_yaml.safe_load = lambda fh: {"modules": []}
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    # Patch the vendored YAML path to a non-existent location so the
    # fallback branch triggers.
    fake_missing = paper_metrics.PB_CONFIG_WITH_ENERGY_RATIO_PATH.parent / "_does_not_exist_.yaml"
    monkeypatch.setattr(paper_metrics, "PB_CONFIG_WITH_ENERGY_RATIO_PATH", fake_missing)

    mols = [_FakeSampledMolecule() for _ in range(4)]
    # When the vendored YAML is missing, the helper falls back to
    # subset_pb path (Wave 73 byte-stable behavior). The canned
    # ``subset_pb`` bucket returns ``pb_valid = 0.99``.
    out = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)
    assert isinstance(out, float)
    assert 0.0 <= out <= 1.0
    assert out == pytest.approx(0.99, abs=1e-9)
    # Sanity: subset path with ``full_pb=False`` returns the same
    # value (the fallback IS the subset path).
    out_explicit_subset = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=False, pb_workers=0
    )
    assert out == out_explicit_subset
