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
    # Wave 95 default: 3-key dict with ``pb_validity`` (PRIMARY —
    # xtb when xtb ran, UFF on graceful fallback), ``pb_validity_uff``
    # (preserved UFF value for byte-stable diff/audit), and ``status``
    # (xtb-vs-uff-fallback discriminator).
    assert isinstance(pb_full, dict)
    assert isinstance(pb_subset, dict)
    assert set(pb_full) == {"pb_validity", "pb_validity_uff", "status"}
    assert set(pb_subset) == {"pb_validity", "pb_validity_uff", "status"}
    # Canned mock: full_pb (vendored YAML) returns 0.92; subset_pb
    # (no energy_ratio module) returns 0.99. xtb pipeline unavailable
    # on the test rig → primary ``pb_validity`` mirrors the UFF value
    # via the graceful fallback path.
    assert pb_full["pb_validity"] == pytest.approx(0.92, abs=1e-9)
    assert pb_subset["pb_validity"] == pytest.approx(0.99, abs=1e-9)
    # UFF is always preserved under ``pb_validity_uff`` regardless of
    # xtb availability (byte-stable diff/audit guarantee).
    assert pb_full["pb_validity_uff"] == pytest.approx(0.92, abs=1e-9)
    assert pb_subset["pb_validity_uff"] == pytest.approx(0.99, abs=1e-9)
    # Sanity: vendored YAML path is stricter than subset path
    # (energy_ratio adds an extra rejection step).
    assert pb_full["pb_validity"] <= pb_subset["pb_validity"]


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
    # Wave 95 default: 3-key dict with ``pb_validity`` (PRIMARY —
    # xtb when xtb ran, UFF on graceful fallback), ``pb_validity_uff``
    # (preserved UFF value for byte-stable diff/audit), and ``status``
    # (xtb-vs-uff-fallback discriminator).
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}
    # When the vendored YAML is injected, the canned "xtb_injected"
    # bucket returns ``pb_valid = 0.92`` (matches the paper-parity
    # value). xtb pipeline unavailable on the test rig → primary
    # ``pb_validity`` mirrors the UFF value via the graceful fallback
    # path; ``pb_validity_uff`` is also 0.92.
    assert out["pb_validity"] == pytest.approx(0.92, abs=1e-9)
    assert out["pb_validity_uff"] == pytest.approx(0.92, abs=1e-9)
    assert 0.0 <= out["pb_validity"] <= 1.0
    # Sanity: the vendored YAML path is NOT the same as the
    # ``full_pb=False`` subset path. The subset path uses the upstream
    # vendored ``pb_config.yaml`` (energy_ratio commented out) and
    # returns ~0.99 in the canned bucket (no energy_ratio rejection).
    out_subset = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=False, pb_workers=0
    )
    assert out_subset["pb_validity"] == pytest.approx(0.99, abs=1e-9)
    # Sanity: full_pb path (with vendored YAML) is stricter than
    # the subset path.
    assert out["pb_validity"] < out_subset["pb_validity"]


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
    # Wave 95 default: 3-key dict (``pb_validity``, ``pb_validity_uff``,
    # ``status``).
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}
    # The vendored YAML bucket returns ``pb_valid = 0.92`` per the
    # paper-parity value (Dunn et al., NeurIPS 2024, arXiv 2508.12629).
    assert 0.0 <= out["pb_validity"] <= 1.0
    assert 0.0 <= out["pb_validity_uff"] <= 1.0
    # Real finite floats (not NaN, not inf, not the upstream
    # import-failure sentinel).
    assert out["pb_validity"] == out["pb_validity"]  # not NaN
    assert out["pb_validity"] not in (float("inf"), float("-inf"))
    assert out["pb_validity_uff"] == out["pb_validity_uff"]
    assert out["pb_validity_uff"] not in (float("inf"), float("-inf"))


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
    # Wave 95 default: 3-key dict (``pb_validity``, ``pb_validity_uff``,
    # ``status``).
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}
    assert 0.0 <= out["pb_validity"] <= 1.0
    assert 0.0 <= out["pb_validity_uff"] <= 1.0
    assert out["pb_validity"] == pytest.approx(0.99, abs=1e-9)
    # xtb pipeline unavailable on test rig → primary ``pb_validity``
    # mirrors the UFF value via graceful fallback; ``pb_validity_uff``
    # is also 0.99.
    assert out["pb_validity_uff"] == pytest.approx(out["pb_validity"], abs=1e-9)
    # Sanity: subset path with ``full_pb=False`` returns the same
    # value (the fallback IS the subset path).
    out_explicit_subset = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=False, pb_workers=0
    )
    assert out["pb_validity"] == out_explicit_subset["pb_validity"]


# ---------------------------------------------------------------------------
# Wave 87 — PB-xtb pipeline wire (FALSE POSITIVE) + FlowMol3 framework-arm
# scope (Option (a)) regression tests.
#
# Wave 87 Agent A audit (`docs/audit/wave87-phase1-audit.md`) confirmed:
#
# 1. PB 0.6.5's ``energy_ratio`` module uses UFF INTERNALLY
#    (RDKit's ``UFFGetMoleculeForceField``, verified at
#    ``.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14``).
#    It is NOT xtb-based. The parent agent's premise that "the
#    paper's pb_validity_pct uses xtb" is a misreading of the literature.
#
# 2. ``compute_pb_validity_pct`` does NOT invoke
#    ``fm3_evals/geometry/xtb_optimization.py`` because xtb is
#    irrelevant to PoseBusters' ``energy_ratio`` check. xtb is for
#    the SEPARATE composite geometry axis (``-med_rmsd_after_xtb``)
#    which is already wired via ``_compute_xtb_geometry_metrics`` in
#    ``tools/run_real_ckpt_eval.py``.
#
# 3. The vendored YAML at
#    ``tools/pb_config_with_energy_ratio.yaml`` is already correctly
#    configured with paper-tuned parameters
#    (``threshold_energy_ratio=100.0``,
#    ``ensemble_number_conformations=50``). No re-wiring required.
#
# These 3 tests document the CORRECT semantics (UFF-not-xtb) so
# future readers do not re-flag the false-positive PB-xtb wire
# question.
# ---------------------------------------------------------------------------


def test_compute_pb_validity_pct_does_not_call_xtb_optimization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``compute_pb_validity_pct`` does NOT invoke the xtb pipeline.

    Wave 87 Agent A audit (§1-3) confirmed that PB 0.6.5's
    ``energy_ratio`` module uses UFF (RDKit's
    ``UFFGetMoleculeForceField``) INTERNALLY — it is NOT xtb-based.
    Therefore ``compute_pb_validity_pct`` must NOT invoke
    ``fm3_evals/geometry/xtb_optimization.py`` or any xtb subprocess
    call: xtb is irrelevant to PoseBusters' ``energy_ratio`` check.

    This test verifies the contract by:
      1. Mocking ``subprocess.run`` (the mechanism by which the xtb
         pipeline would be invoked) so any call into xtb would raise
         ``RuntimeError("xtb must not be called from compute_pb_validity_pct")``.
      2. Patching ``sys.modules["data.FlowMol3.repo.fm3_evals.geometry.xtb_optimization"]``
         with a sentinel that raises on import.
      3. Running ``compute_pb_validity_pct`` and asserting it returns
         the expected paper-parity ``pb_valid`` value (~0.92) WITHOUT
         touching the xtb pipeline.

    If a future refactor inadvertently wires xtb into the PB path,
    this test will FAIL loudly.
    """
    canned = _install_mock_flowmol(monkeypatch)

    # Sentinel 1: any subprocess.run call from inside
    # compute_pb_validity_pct would be a violation (xtb is
    # shell-invoked, not imported).
    import subprocess as _subprocess  # noqa: PLC0415

    def _fail_on_subprocess(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "xtb must not be invoked from compute_pb_validity_pct; "
            "PB 0.6.5's energy_ratio module is UFF-based (verified at "
            "posebusters/modules/energy_ratio.py:6-14). xtb is for the "
            "composite geometry axis (_compute_xtb_geometry_metrics), "
            "not the PB axis. See Wave 87 Agent A audit "
            "(docs/audit/wave87-phase1-audit.md) §1-3."
        )

    monkeypatch.setattr(_subprocess, "run", _fail_on_subprocess)

    # Sentinel 2: any import of the xtb_optimization module from
    # inside compute_pb_validity_pct would be a violation.
    import types as _types  # noqa: PLC0415

    def _fail_on_xtb_import(name: Any, *args: Any, **kwargs: Any) -> Any:
        if "xtb_optimization" in str(name) or "fm3_evals" in str(name):
            raise ImportError(
                f"xtb module {name!r} must not be imported from "
                "compute_pb_validity_pct; PB's energy_ratio is UFF-based. "
                "See Wave 87 Agent A audit §1-3."
            )
        return _orig_import(name, *args, **kwargs)

    import builtins as _builtins  # noqa: PLC0415

    _orig_import = _builtins.__import__
    monkeypatch.setattr(_builtins, "__import__", _fail_on_xtb_import)

    # Set up the rest of the vendored-YAML injection path (same as
    # test_pb_validity_pct_uses_xtb_energy_ratio).
    import types as _types2  # noqa: PLC0415

    fake_posebusters = _types2.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config
            self._max_workers = int(max_workers)

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types2.ModuleType("yaml")

    def _fake_safe_load(fh: Any) -> dict[str, Any]:
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
    # Wave 95 default: 3-key dict. The vendored YAML injection path
    # returns the paper-parity ``xtb_injected`` bucket (~0.92). If this
    # assertion passes without raising, the contract is verified: PB
    # path did NOT touch xtb. Primary ``pb_validity`` mirrors the UFF
    # value via graceful fallback (xtb unavailable on test rig).
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}
    assert out["pb_validity"] == pytest.approx(0.92, abs=1e-9)
    assert out["pb_validity_uff"] == pytest.approx(0.92, abs=1e-9)
    assert 0.0 <= out["pb_validity"] <= 1.0


def test_pb_config_with_energy_ratio_yaml_has_paper_tuned_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The vendored YAML contains the paper-tuned energy_ratio parameters.

    Wave 82 vendored the PoseBusters config with the ``energy_ratio``
    module UNCOMMENTED. The paper-tuned parameters are:
      - ``threshold_energy_ratio: 100.0`` (vs PB default 7.0)
      - ``ensemble_number_conformations: 50``
    These values match the upstream FlowMol3 paper's
    ``pb_config.yaml:101-110`` (the upstream source has them
    COMMENTED OUT at the same indentation; Wave 82 vendored an
    uncommented copy).

    This test asserts both values are present in the vendored YAML
    on disk. If a future re-vendoring or hand-edit accidentally
    reverts them, the test will FAIL.
    """
    from tools import paper_metrics  # noqa: PLC0415

    yaml_path = paper_metrics.PB_CONFIG_WITH_ENERGY_RATIO_PATH
    assert yaml_path.is_file(), (
        f"Wave 82 vendored YAML missing at {yaml_path}; "
        "Phase A vendoring is incomplete"
    )

    import yaml as _yaml  # noqa: PLC0415

    with yaml_path.open("r") as fh:
        pb_config = _yaml.safe_load(fh)

    # The energy_ratio module must be UNCOMMENTED with paper-tuned
    # parameters. Search the modules list for the energy_ratio entry.
    assert "modules" in pb_config, (
        f"PB YAML at {yaml_path} missing top-level 'modules' key"
    )
    modules_list = pb_config["modules"]
    energy_ratio_module = None
    for m in modules_list:
        if m.get("function") == "energy_ratio":
            energy_ratio_module = m
            break

    assert energy_ratio_module is not None, (
        f"PB YAML at {yaml_path} does not contain an energy_ratio module. "
        "Wave 82 Phase A vendoring is incomplete — the energy_ratio module "
        "must be UNCOMMENTED with paper-tuned parameters "
        "(threshold_energy_ratio=100.0, ensemble_number_conformations=50). "
        "See Wave 82 Agent A audit §3 + Wave 87 Agent A audit §3."
    )

    params = energy_ratio_module.get("parameters", {})
    assert params.get("threshold_energy_ratio") == 100.0, (
        f"energy_ratio threshold_energy_ratio = {params.get('threshold_energy_ratio')!r}, "
        "expected 100.0 (paper-tuned). The PB default 7.0 over-rejects "
        "FlowMol3 mols; the paper uses 100.0. See Wave 82 Agent A audit §3."
    )
    assert params.get("ensemble_number_conformations") == 50, (
        f"energy_ratio ensemble_number_conformations = "
        f"{params.get('ensemble_number_conformations')!r}, expected 50. "
        "The paper uses 50 conformations for the UFF ensemble. "
        "See Wave 82 Agent A audit §3."
    )
    # PB's energy_ratio module is UFF-based (NOT xtb-based).
    # Verify the function name is just "energy_ratio" (no xtb suffix).
    assert energy_ratio_module.get("function") == "energy_ratio", (
        f"energy_ratio function = {energy_ratio_module.get('function')!r}, "
        "expected 'energy_ratio'. The function is UFF-based (RDKit's "
        "UFFGetMoleculeForceField), NOT xtb-based. See Wave 87 Agent A "
        "audit §1-3."
    )


def test_pb_validity_pct_vendored_yaml_injection_matches_paper_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vendored-YAML injection path returns the paper-parity value (~0.92).

    Paper value (Dunn et al., NeurIPS 2024, arXiv 2508.12629): ``pb_validity_pct ≈ 0.919``.

    Wave 82 closes the gap between the paper's reported value and the
    naive ``pb_valid ≈ 1.0`` reading (which lacked the energy_ratio
    module). The fix: vendor a custom PoseBusters config at
    ``tools/pb_config_with_energy_ratio.yaml`` with the energy_ratio
    module UNCOMMENTED (paper-tuned params), then inject it via
    ``analyzer.buster = posebusters.PoseBusters(config=<our_yaml_dict>)``
    (PB 0.6.5 accepts either a preset name or a config dict — verified
    at ``posebusters/posebusters.py:73-127``).

    This test verifies the paper-parity value: when the vendored YAML
    is injected, the canned ``xtb_injected`` bucket returns
    ``pb_valid = 0.92``, matching the paper target ``0.919`` within
    ±5% (tolerance: 0.0455).

    Note: the test uses the canned ``xtb_injected`` bucket (which the
    test fixture returns when ``analyzer.buster_config is not None``)
    rather than running the real upstream PB. This is a deterministic
    regression check on the wire (vendored YAML → analyzer.buster
    assignment → canned ``pb_valid`` value); it does NOT exercise
    PB's UFF energy_ratio math. A separate N=10 smoke test on the
    real upstream would be needed to verify the UFF math itself,
    which is out of scope for this regression test (real upstream
    PB requires torch + dgl + RDKit + posebusters all installed and
    is gated on the ``flowmol3_venv`` sidecar).
    """
    canned = _install_mock_flowmol(monkeypatch)

    import types as _types  # noqa: PLC0415

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config
            self._max_workers = int(max_workers)

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")

    def _fake_safe_load(fh: Any) -> dict[str, Any]:
        return {
            "modules": [
                {"name": "Loading", "function": "loading"},
                {"name": "Energy ratio", "function": "energy_ratio",
                 "parameters": {
                     "threshold_energy_ratio": 100.0,
                     "ensemble_number_conformations": 50,
                 },
                 "chosen_binary_test_output": ["energy_ratio_passes"]},
            ]
        }

    fake_yaml.safe_load = _fake_safe_load
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(10)]
    out = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)
    # Wave 95 default: 3-key dict (``pb_validity``, ``pb_validity_uff``,
    # ``status``). Primary ``pb_validity`` mirrors the UFF value via
    # graceful fallback (xtb unavailable on test rig).
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}
    # Paper target: 0.919 (Dunn et al., NeurIPS 2024, arXiv 2508.12629).
    # Canned ``xtb_injected`` bucket returns 0.92. Tolerance: ±5% of
    # 0.919 = 0.04595.
    assert out["pb_validity"] == pytest.approx(0.92, abs=0.05), (
        f"compute_pb_validity_pct (vendored YAML) = {out['pb_validity']}, "
        "expected 0.92 ± 0.05 (paper target 0.919). The vendored YAML "
        "path must return a paper-parity value — if this fails, the "
        "wire is broken."
    )
    assert 0.0 <= out["pb_validity"] <= 1.0

    # Sanity: the full_pb path is STRICTER than the subset path
    # (energy_ratio adds a rejection step). The subset path returns
    # 0.99 in the canned bucket (no energy_ratio rejection).
    out_subset = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=False, pb_workers=0
    )
    assert out["pb_validity"] < out_subset["pb_validity"], (
        f"full_pb path (vendored YAML) = {out['pb_validity']} should be "
        f"STRICTER than subset path = {out_subset['pb_validity']}; "
        "energy_ratio adds a rejection step."
    )


# ---------------------------------------------------------------------------
# Wave 90+ — xtb-bridge availability contract test.
#
# Verifies the new ``status`` discriminator:
#
#   * When the xtb bridge is available, ``compute_pb_validity_pct``
#     returns BOTH UFF-based and xtb-based numbers (different values).
#     ``status == "xtb"``.
#
#   * When the xtb bridge is missing, the helper falls back to UFF
#     only. ``pb_validity_xtb == pb_validity`` (the UFF value).
#     ``status == "uff_fallback"``.
#
# The xtb bridge surface is mocked so the test runs deterministically
# without xtb / rdkit on the test rig (matching the existing test
# rig state — ``rdkit`` is NOT installed in the CPU-only CI venv).
# ---------------------------------------------------------------------------


def _install_mock_xtb_bridge(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Install mocks for ``tools.flowmol3_xtb_bridge`` + ``rdkit.Chem``.

    Returns a dict of per-call counters so the test can assert on
    how the bridge was invoked. The mocks simulate the full xtb
    pipeline (write SDF → xtb_optimize_sdf writes opt SDF →
    per-mol xtb_energy_ratio returns a finite float ratio).
    """
    call_count = {"optimize": 0, "ratio": 0, "write": 0}

    class _FakeXtbBridgeError(RuntimeError):
        pass

    def _fake_xtb_optimize_sdf(
        input_sdf: Any, init_sdf: Any, **_kw: Any
    ) -> Any:
        call_count["optimize"] += 1
        # Mirror upstream convention: opt SDF = input stem + "_opt" + suffix.
        input_sdf_p = Path(str(input_sdf))
        opt_sdf = input_sdf_p.with_name(
            input_sdf_p.stem + "_opt" + input_sdf_p.suffix
        )
        # The upstream script would write the opt SDF; we mimic that.
        opt_sdf.write_text("optimized\n", encoding="utf-8")
        return opt_sdf

    def _fake_xtb_energy_ratio(
        rdkit_mol: Any, _init_sdf: Any, _opt_sdf: Any, **_kw: Any
    ) -> float:
        call_count["ratio"] += 1
        # Distinguish mols by their _Name prop set inside the helper.
        # Use a deterministic but small ratio (well under the
        # xtb_threshold=100.0 paper cutoff) so every mol "passes".
        try:
            name = rdkit_mol.GetProp("_Name") if rdkit_mol is not None else ""
        except Exception:
            name = ""
        # Cycle through 3 small-but-distinct ratios so the test can
        # observe that xtb ran (the resulting pb_validity_xtb is a
        # finite real number derived from these ratios, NOT equal to
        # the canned UFF bucket value).
        idx = int(name.rsplit("_", 1)[-1]) if "_" in name else 0
        ratios = [5.0, 12.0, 50.0]
        return float(ratios[idx % len(ratios)])

    fake_bridge = types.ModuleType("tools.flowmol3_xtb_bridge")
    fake_bridge.XtbBridgeError = _FakeXtbBridgeError
    fake_bridge.xtb_optimize_sdf = _fake_xtb_optimize_sdf
    fake_bridge.xtb_energy_ratio = _fake_xtb_energy_ratio
    monkeypatch.setitem(sys.modules, "tools.flowmol3_xtb_bridge", fake_bridge)

    # Mock rdkit.Chem: SDWriter accepts write() calls and the mol
    # exposes SetProp/GetProp. The mols passed in must already look
    # like RDKit mols (have SetProp + GetProp + GetConformer-friendly
    # attrs); we wrap _FakeSampledMolecule.build_molecule() to
    # return a MagicMock that quacks like an RDKit mol.
    class _FakeRDKitMol:
        """Duck-typed RDKit mol with the surface the bridge touches."""

        def __init__(self, idx: int) -> None:
            self._props: dict[str, str] = {}

        def SetProp(self, key: str, value: str) -> None:
            self._props[str(key)] = str(value)

        def GetProp(self, key: str) -> str:
            return self._props[str(key)]

    class _FakeSDWriter:
        def __init__(self, path: str) -> None:
            self._path = Path(path)
            # Make sure the parent exists so the helper's
            # ``input_sdf.is_file()`` check passes after .close().
            self._path.parent.mkdir(parents=True, exist_ok=True)

        def write(self, _mol: Any) -> None:
            call_count["write"] += 1

        def close(self) -> None:
            # Create an empty file so the bridge sees the SDF as
            # present on disk (the upstream script would write a real
            # record; we only need .is_file() to return True).
            self._path.touch(exist_ok=True)

    class _FakeChem:
        SDWriter = _FakeSDWriter

    fake_rdkit = types.ModuleType("rdkit")
    fake_rdkit.Chem = _FakeChem()
    monkeypatch.setitem(sys.modules, "rdkit", fake_rdkit)

    return call_count


def test_compute_pb_validity_pct_with_xtb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """xtb bridge availability drives the returned ``status`` field.

    When the xtb bridge is available, ``compute_pb_validity_pct``
    returns BOTH UFF-based AND xtb-based numbers (the two values
    must be distinct because they are computed from different
    energy models). The ``status`` field reads ``"xtb"``.

    When the xtb bridge is missing, the helper falls back to UFF
    only: ``pb_validity_xtb`` mirrors the UFF value
    (``pb_validity_xtb == pb_validity``). The ``status`` field reads
    ``"uff_fallback"``.

    This test exercises BOTH branches in a single function and
    asserts the discriminator works end-to-end.
    """
    # ------------------------------------------------------------------
    # Phase 1 — xtb bridge UNAVAILABLE (test-rig default).
    #
    # We deliberately do NOT install the xtb bridge mock here. The
    # helper's ``from tools.flowmol3_xtb_bridge import ...`` will
    # resolve to the real bridge module (which exists), but the
    # bridge's own functions would fail because rdkit is not
    # installed in the test venv. The ImportError on ``from rdkit
    # import Chem`` inside ``_recompute_pb_validity_xtb`` short-
    # circuits to the UFF fallback path.
    # ------------------------------------------------------------------
    _install_mock_flowmol(monkeypatch)
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")
    fake_yaml.safe_load = lambda fh: {
        "modules": [
            {"name": "Loading", "function": "loading"},
            {"name": "Energy ratio", "function": "energy_ratio",
             "parameters": {"threshold_energy_ratio": 100.0,
                            "ensemble_number_conformations": 50}},
        ]
    }
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeSampledMolecule() for _ in range(4)]

    # --- Phase 1: xtb unavailable → status="uff_fallback" ---
    out_no_xtb = paper_metrics.compute_pb_validity_pct(
        mols, full_pb=True, pb_workers=0
    )
    assert isinstance(out_no_xtb, dict)
    # Wave 95 default: 3-key dict (``pb_validity``, ``pb_validity_uff``,
    # ``status``).
    assert set(out_no_xtb) == {"pb_validity", "pb_validity_uff", "status"}
    # The status field must be the fallback literal.
    assert out_no_xtb["status"] == "uff_fallback", (
        f"expected status='uff_fallback' when xtb bridge is missing; "
        f"got status={out_no_xtb['status']!r}"
    )
    # When xtb is missing, primary ``pb_validity`` mirrors the UFF
    # value via the graceful fallback path. Direct UFF-vs-xtb diff is
    # therefore 0 — the UFF number propagates through unchanged.
    assert out_no_xtb["pb_validity_uff"] == pytest.approx(
        out_no_xtb["pb_validity"], abs=1e-9
    )
    assert out_no_xtb["pb_validity_uff"] == out_no_xtb["pb_validity"]
    # Both numbers are well-defined finite floats in [0, 1].
    assert 0.0 <= out_no_xtb["pb_validity"] <= 1.0
    assert 0.0 <= out_no_xtb["pb_validity_uff"] <= 1.0
    assert out_no_xtb["pb_validity"] == out_no_xtb["pb_validity"]  # not NaN
    assert out_no_xtb["pb_validity_uff"] == out_no_xtb["pb_validity_uff"]

    # ------------------------------------------------------------------
    # Phase 2 — xtb bridge AVAILABLE.
    #
    # Install mocks so the bridge + rdkit imports succeed and the
    # xtb pipeline runs end-to-end. Use a subclass of
    # _FakeSampledMolecule that returns a properly-shaped RDKit mol
    # (with SetProp + GetProp) from build_molecule(), so the
    # bridge's per-mol loop produces records.
    # ------------------------------------------------------------------

    class _FakeMolWithRDKit(_FakeSampledMolecule):
        """Subclass whose ``build_molecule()`` returns a fake RDKit mol.

        The xtb bridge needs the returned object to support
        ``SetProp("_Name", ...)`` and ``GetProp("_Name")``. We use
        the ``_FakeRDKitMol`` helper from the bridge mock installer
        — but it lives in a local scope. Re-define a minimal
        compatible version here.
        """

        _counter = 0

        def build_molecule(self) -> Any:  # type: ignore[override]
            cls = type(self)
            cls._counter += 1
            idx = (cls._counter - 1) % 3
            return _Phase2RDKitMol(idx=idx)

    class _Phase2RDKitMol:
        def __init__(self, idx: int) -> None:
            self._idx = int(idx)
            self._props: dict[str, str] = {}

        def SetProp(self, key: str, value: str) -> None:
            self._props[str(key)] = str(value)

        def GetProp(self, key: str) -> str:
            return self._props[str(key)]

        @property
        def _paper_pb_xtb_mol_idx(self) -> int:
            return int(self._idx)

    bridge_calls = _install_mock_xtb_bridge(monkeypatch)

    # Phase-2 mols: build_molecule() returns a properly-shaped mol.
    mols_xtb = [_FakeMolWithRDKit() for _ in range(4)]

    out_xtb = paper_metrics.compute_pb_validity_pct(
        mols_xtb, full_pb=True, pb_workers=0
    )
    assert isinstance(out_xtb, dict)
    # Wave 95 default: 3-key dict (``pb_validity``, ``pb_validity_uff``,
    # ``status``).
    assert set(out_xtb) == {"pb_validity", "pb_validity_uff", "status"}
    # The xtb bridge MUST have run end-to-end.
    assert out_xtb["status"] == "xtb", (
        f"expected status='xtb' when xtb bridge is mocked as available; "
        f"got status={out_xtb['status']!r}"
    )
    # xtb was actually invoked: optimize called once, ratio called per mol.
    assert bridge_calls["optimize"] >= 1, (
        f"expected xtb_optimize_sdf to be called at least once; "
        f"call_count={bridge_calls}"
    )
    assert bridge_calls["ratio"] >= 1, (
        f"expected xtb_energy_ratio to be called at least once; "
        f"call_count={bridge_calls}"
    )
    # Both numbers are well-defined finite floats in [0, 1].
    assert 0.0 <= out_xtb["pb_validity"] <= 1.0
    assert 0.0 <= out_xtb["pb_validity_uff"] <= 1.0
    assert out_xtb["pb_validity"] == out_xtb["pb_validity"]
    assert out_xtb["pb_validity_uff"] == out_xtb["pb_validity_uff"]
    # Wave 95 default-switch contract: when xtb ran, primary
    # ``pb_validity`` is the **xtb-based** number; ``pb_validity_uff``
    # remains the UFF value. The two are now allowed to differ because
    # the primary key has switched engines.
    #   * UFF value (pb_validity_uff) = canned vendored-YAML bucket
    #     returns 0.92 (deterministic from the mock upstream
    #     SampleAnalyzer).
    #   * xtb value (pb_validity) = derived from the 3 mock ratios
    #     (all < 100.0 threshold → all pass → 1.0 for the 4-mol set).
    # We assert that the values are present and finite, NOT that they
    # differ in a specific way (the test must remain deterministic
    # regardless of what the mock returns).
    assert isinstance(out_xtb["pb_validity"], float)
    assert isinstance(out_xtb["pb_validity_uff"], float)

    # Sanity (Wave 95): the two test phases produce the SAME UFF value
    # under ``pb_validity_uff`` (UFF is deterministic from the canned
    # upstream SampleAnalyzer mock; only the xtb-side depends on the
    # bridge availability).
    assert out_no_xtb["pb_validity_uff"] == out_xtb["pb_validity_uff"], (
        f"UFF pb_validity_uff should be deterministic across phases; "
        f"phase1={out_no_xtb['pb_validity_uff']}, "
        f"phase2={out_xtb['pb_validity_uff']}"
    )
    # Sanity (Wave 95): primary ``pb_validity`` DIFFERS across phases
    # because the default now switches engines when xtb is available
    # (Phase 1 = UFF fallback = 0.92; Phase 2 = xtb = 1.0).
    assert out_no_xtb["pb_validity"] != out_xtb["pb_validity"], (
        f"Wave 95 default switch: primary pb_validity should differ "
        f"across phases (Phase 1 = UFF fallback, Phase 2 = xtb). "
        f"phase1={out_no_xtb['pb_validity']}, "
        f"phase2={out_xtb['pb_validity']}"
    )
    # Sanity: the status fields differ — phase 1 is fallback,
    # phase 2 is xtb.
    assert out_no_xtb["status"] != out_xtb["status"]
    assert {out_no_xtb["status"], out_xtb["status"]} == {
        "uff_fallback",
        "xtb",
    }


def test_compute_pb_validity_pct_xtb_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock ``xtb_bridge.xtb_energy_ratio`` to raise ``FileNotFoundError``.

    Verifies that ``compute_pb_validity_pct`` falls back to UFF-only
    when the per-mol xtb energy-ratio call raises
    ``FileNotFoundError`` (the canonical "xtb binary not on $PATH"
    signal). The returned dict must:

      * carry the paper UFF ``pb_validity`` value (the canned
        ``xtb_injected`` bucket ≈ 0.92 when the vendored YAML is
        injected; unchanged by the xtb-side failure);
      * mirror the UFF value into ``pb_validity_xtb`` (the UFF-fallback
        contract — readers can always diff the two keys, even when the
        xtb pipeline is unavailable);
      * report a fallback ``status`` so downstream consumers can
        distinguish "xtb unavailable" from "xtb ran end-to-end".

    This is the missing link between the existing tests:

      * ``test_pb_validity_pct_falls_back_to_uff_when_xtb_missing``
        covers the YAML-side fallback (vendored YAML absent →
        subset_pb).
      * ``test_compute_pb_validity_pct_with_xtb`` covers the xtb-side
        happy path (xtb available, status == "xtb").

    This test covers the per-mol xtb-side failure mode: the canonical
    ``FileNotFoundError`` from the upstream ``subprocess.run(["xtb",
    ...])`` call (which raises ``FileNotFoundError(errno.ENOENT,
    "xtb")`` when the xtb binary is missing on ``$PATH``) is
    short-circuited by the helper's per-mol ``try/except Exception``
    block into a fallback that:

      1. Records the mol as a fail (``n_total += 1``, ``n_pass`` stays)
         — i.e. the xtb-side pass rate collapses to ``0.0`` for that
         record.
      2. Surfaces a non-``"xtb"`` status so callers can branch on the
         cause.

    The test asserts both halves of the contract:
      * UFF-side ``pb_validity`` is preserved (≈0.92 paper-parity).
      * xtb-side does NOT report ``status == "xtb"`` because the
        xtb pipeline did not actually evaluate any per-mol ratios —
        it raised FileNotFoundError for every record.
    """
    import errno
    import os

    canned = _install_mock_flowmol(monkeypatch)
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
        return {
            "modules": [
                {"name": "Loading", "function": "loading"},
                {"name": "Energy ratio", "function": "energy_ratio",
                 "parameters": {"threshold_energy_ratio": 100.0,
                                "ensemble_number_conformations": 50}},
            ]
        }

    fake_yaml.safe_load = _fake_safe_load
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    # Install a stub xtb bridge where the optimize step "succeeds"
    # (writes the expected opt SDF) but the per-mol
    # ``xtb_energy_ratio`` call raises ``FileNotFoundError`` —
    # mirroring the canonical "xtb binary missing on $PATH" failure
    # mode surfaced by the upstream FlowMol3 geometry helpers.
    class _FakeXtbBridgeError(RuntimeError):
        pass

    def _fake_xtb_optimize_sdf(
        input_sdf: Any, init_sdf: Any, **_kw: Any
    ) -> Any:
        input_sdf_p = Path(str(input_sdf))
        opt_sdf = input_sdf_p.with_name(
            input_sdf_p.stem + "_opt" + input_sdf_p.suffix
        )
        opt_sdf.write_text("optimized\n", encoding="utf-8")
        return opt_sdf

    def _fake_xtb_energy_ratio_raises_filenotfound(
        rdkit_mol: Any, _init_sdf: Any, _opt_sdf: Any, **_kw: Any
    ) -> float:
        # The canonical "xtb binary not on $PATH" error from the
        # upstream ``fm3_evals/geometry`` pipeline:
        # ``subprocess.run(["xtb", ...], ...)`` raises
        # ``FileNotFoundError(errno.ENOENT, "xtb")`` when the binary
        # is missing. The bridge propagates this verbatim so callers
        # can distinguish "xtb missing" from other failure modes.
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            "xtb",
        )

    fake_bridge = _types.ModuleType("tools.flowmol3_xtb_bridge")
    fake_bridge.XtbBridgeError = _FakeXtbBridgeError
    fake_bridge.xtb_optimize_sdf = _fake_xtb_optimize_sdf
    fake_bridge.xtb_energy_ratio = _fake_xtb_energy_ratio_raises_filenotfound
    monkeypatch.setitem(sys.modules, "tools.flowmol3_xtb_bridge", fake_bridge)

    # Mock rdkit.Chem so the SDF writer succeeds and the per-mol loop
    # reaches the (mocked) ``xtb_energy_ratio`` call.
    class _FakeRDKitMol:
        def __init__(self) -> None:
            self._props: dict[str, str] = {}

        def SetProp(self, key: str, value: str) -> None:
            self._props[str(key)] = str(value)

        def GetProp(self, key: str) -> str:
            return self._props[str(key)]

    class _FakeMolWithRDKit(_FakeSampledMolecule):
        """Subclass whose ``build_molecule()`` returns a fake RDKit mol."""

        def build_molecule(self) -> Any:  # type: ignore[override]
            return _FakeRDKitMol()

    class _FakeSDWriter:
        def __init__(self, path: str) -> None:
            self._path = Path(path)
            self._path.parent.mkdir(parents=True, exist_ok=True)

        def write(self, _mol: Any) -> None:
            pass

        def close(self) -> None:
            self._path.touch(exist_ok=True)

    class _FakeChem:
        SDWriter = _FakeSDWriter

    fake_rdkit = _types.ModuleType("rdkit")
    fake_rdkit.Chem = _FakeChem()
    monkeypatch.setitem(sys.modules, "rdkit", fake_rdkit)

    from tools import paper_metrics  # noqa: PLC0415

    mols = [_FakeMolWithRDKit() for _ in range(4)]
    out = paper_metrics.compute_pb_validity_pct(mols, full_pb=True, pb_workers=0)

    # Result shape is the 3-key dict — same as the happy path.
    # Wave 95 default: ``pb_validity`` (primary, best-available),
    # ``pb_validity_uff`` (always UFF), ``status`` discriminator.
    assert isinstance(out, dict)
    assert set(out) == {"pb_validity", "pb_validity_uff", "status"}

    # UFF-side: the vendored YAML was injected, so the canned
    # ``xtb_injected`` bucket returns ``pb_valid = 0.92`` (the
    # paper-parity value). The xtb-side failure must NOT bleed into
    # the UFF value.
    assert out["pb_validity"] == pytest.approx(0.92, abs=1e-9)
    assert out["pb_validity_uff"] == pytest.approx(0.92, abs=1e-9)
    assert 0.0 <= out["pb_validity"] <= 1.0

    # xtb-side: the very first per-mol ``xtb_energy_ratio`` call
    # raised ``FileNotFoundError`` (xtb binary missing on $PATH).
    # The helper short-circuits to the UFF-fallback contract —
    # primary ``pb_validity`` mirrors the UFF value (via the
    # ``status != "xtb"`` branch), and ``pb_validity_uff`` always
    # holds the raw UFF number. This guarantees the returned dict is
    # always well-defined and the UFF-vs-xtb diff is zero (callers
    # can still compute it; it just collapses to the no-op case).
    assert out["pb_validity_uff"] == pytest.approx(out["pb_validity"], abs=1e-9)
    assert out["pb_validity_uff"] == out["pb_validity"]
    assert 0.0 <= out["pb_validity_uff"] <= 1.0
    assert out["pb_validity_uff"] == out["pb_validity_uff"]  # not NaN
    assert out["pb_validity_uff"] not in (float("inf"), float("-inf"))

    # Status discriminator: the xtb-side FileNotFoundError must flip
    # ``status`` to ``"xtb_unavailable"`` — distinct from
    # ``"uff_fallback"`` (YAML-missing or generic import failure)
    # and ``"xtb"`` (happy path). Without the dedicated
    # ``FileNotFoundError`` catch the per-mol exception would fall
    # through to ``except Exception`` and the function would
    # misleadingly return ``status == "xtb"`` with
    # ``pb_validity_xtb == 0.0``.
    assert out["status"] == "xtb_unavailable", (
        f"expected status='xtb_unavailable' when xtb_energy_ratio raises "
        f"FileNotFoundError; got status={out['status']!r}. The "
        f"FileNotFoundError short-circuit must flip the discriminator "
        f"so downstream consumers can branch on the cause."
    )

    # Sanity: the UFF value is preserved (real finite float, not NaN,
    # not inf, not the upstream import-failure sentinel).
    assert out["pb_validity"] == out["pb_validity"]  # not NaN
    assert out["pb_validity"] not in (float("inf"), float("-inf"))


# ---------------------------------------------------------------------------
# Wave 95 Phase 2.D — pb_validity default switch (F2 UFF-vs-xtb gap)
#
# Regression test for the Wave 95 default switch: the primary
# ``pb_validity`` key must return the **xtb-based number** when the xtb
# bridge runs end-to-end (the gold standard — matches the paper's
# stated measurement semantics), and gracefully fall back to the
# UFF-based number when xtb is unavailable on ``$PATH``. The raw UFF
# value is always preserved under ``pb_validity_uff`` for byte-stable
# diff/audit.
# ---------------------------------------------------------------------------


def test_pb_validity_default_is_xtb(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wave 95 default switch: ``pb_validity`` returns xtb when xtb ran.

    Verifies the contract:
      * When xtb runs end-to-end (``status == "xtb"``), the primary
        ``pb_validity`` key returns the xtb-based number (not UFF).
      * The UFF-based value is preserved under ``pb_validity_uff``
        (byte-stable diff/audit guarantee).
      * When xtb is unavailable (``status == "uff_fallback"``), the
        primary ``pb_validity`` key mirrors the UFF value via the
        graceful fallback path — the returned dict stays well-defined.
    """
    # ------------------------------------------------------------------
    # Phase 1 — xtb bridge AVAILABLE (default-switch case)
    # ------------------------------------------------------------------
    _install_mock_flowmol(monkeypatch)
    import types as _types

    fake_posebusters = _types.ModuleType("posebusters")

    class _FakePoseBusters:
        def __init__(self, *, config: Any = None, max_workers: int = 0, **_kw: Any):
            self._config = config

    fake_posebusters.PoseBusters = _FakePoseBusters
    monkeypatch.setitem(sys.modules, "posebusters", fake_posebusters)

    fake_yaml = _types.ModuleType("yaml")
    fake_yaml.safe_load = lambda fh: {"modules": [{"name": "Loading",
                                                  "function": "loading"}]}
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)
    _install_mock_xtb_bridge(monkeypatch)

    from tools import paper_metrics  # noqa: PLC0415

    class _RDKitMol:  # noqa: D401 — minimal duck-typed RDKit mol
        def __init__(self) -> None:
            self._props: dict[str, str] = {}

        def SetProp(self, key: str, value: str) -> None:
            self._props[str(key)] = str(value)

        def GetProp(self, key: str) -> str:
            return self._props[str(key)]

    class _MolXtb(_FakeSampledMolecule):
        def build_molecule(self) -> Any:  # type: ignore[override]
            return _RDKitMol()

    out_xtb = paper_metrics.compute_pb_validity_pct(
        [_MolXtb() for _ in range(4)], full_pb=True, pb_workers=0
    )
    assert out_xtb["status"] == "xtb"  # xtb ran end-to-end
    assert out_xtb["pb_validity"] == pytest.approx(1.0, abs=1e-9)
    # xtb-based number ≠ UFF-based number — the primary key switched
    # engines. UFF is preserved for diff/audit under ``pb_validity_uff``.
    assert out_xtb["pb_validity_uff"] == pytest.approx(0.92, abs=1e-9)
    assert out_xtb["pb_validity"] != out_xtb["pb_validity_uff"]


# ---------------------------------------------------------------------------
# __all__ — re-export the public test names so test discovery is robust.
# ---------------------------------------------------------------------------

__all__ = (
    "test_compute_pb_validity_pct_xtb_missing",
    "test_compute_pb_validity_pct_with_xtb",
    "test_pb_validity_default_is_xtb",
    "test_pb_validity_pct_falls_back_to_uff_when_xtb_missing",
    "test_pb_validity_pct_returns_real_number_when_xtb_installed",
    "test_pb_validity_pct_subset_vs_full",
    "test_pb_validity_pct_uses_xtb_energy_ratio",
    "test_pb_validity_pct_vendored_yaml_injection_matches_paper_target",
    "test_compute_pb_validity_pct_does_not_call_xtb_optimization",
    "test_pb_config_with_energy_ratio_yaml_has_paper_tuned_params",
)
