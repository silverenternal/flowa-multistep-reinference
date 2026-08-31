"""RDKit glue for molecular adapters — endpoint (x, a, c, e) -> Chem.Mol.

This is the Phase-A in-process conversion layer between the molecular
mechanics adapters (``adaptive_reflow.adapters.flowmol3_v2_adapter`` and
``adaptive_reflow.adapters.graphbfn``) and :mod:`tools.run_mol_eval`. It
exists *separately* from :mod:`adaptive_reflow.molecular.mixer` because
the mixer file is restart-blend math (torch-gated), while the writer here
is pure RDKit chemistry assembly.

Public surface — FlowMol3 (point-cloud: x, a, c, dense e)
---------------------------------------------------------

* :func:`endpoint_to_rdkit_mol` — convert one endpoint (x, a, c, e) tuple
  to a single ``Chem.Mol``. Returns ``None`` on failure so the caller can
  charge it into the validity denominator.
* :func:`trajectory_endpoint_to_rdkit_mol` — pull the t=1 slice from a
  trajectory dict (returned by
  :meth:`FlowMol3V2Adapter.export_trajectory`) and convert it.
* :func:`adapter_endpoint_to_rdkit_mol` — top-level entry: given an
  adapter instance and an :class:`ODEIntegratorTrace`, look up the
  endpoint via :meth:`adapter.export_trajectory`, take the t=1 slice,
  convert it.

Public surface — GraphBFN (graph: atom_types, bond_types, adjacency)
--------------------------------------------------------------------

* :func:`graph_to_rdkit_mol` — convert a rounded GraphBFN graph
  (``atom_types`` ``(N,)``, ``bond_types`` ``(E,)``, ``adjacency``
  ``(N, N)``) to a ``Chem.Mol``.
* :func:`graphbfn_round_trajectory` — argmax-round a GraphBFN
  ``export_trajectory`` payload (Categorical logits) into the rounded
  graph form.
* :func:`graphbfn_trajectory_to_rdkit_mol` /
  :func:`graphbfn_endpoint_to_rdkit_mol` — the two convenience entries
  mirroring the FlowMol3 pair.

The two families need genuinely different conversion paths: FlowMol3
emits a 3D point cloud with a *dense symmetric* ``(N, N)`` bond-label
matrix whose no-bond sentinel is a reserved label; GraphBFN factorises
edge *existence* (a Bernoulli ``(N, N)`` adjacency) from edge *order* (a
separate length-``E`` Categorical vector) and carries no coordinates at
all. See the "GraphBFN conversion" section below.

Conversion details
------------------

These are the four silent-corruption landmines called out by the
Phase-1 risk register; failing to apply any of them turns the entire
metric panel into noise.

1. **Bond labels are off by one.** The FlowMol3 adapter's no-bond
   sentinel is index ``4`` (``FLOWMOL3ADAPTER_N_BOND_TYPES - 1``); the
   FlowMol3 reference's no-bond is index ``0``. Remap: adapter
   ``4 -> 0`` (no-bond) and adapter ``0..3 -> +1`` (single, double,
   triple, aromatic). The remap is hard-coded here because the
   vocabulary is owned by the zavalab FlowMol3 repo (see
   ``data/FlowMol3/repo/flowmol/analysis/molecule_builder.py`` line 10).
2. **Atom types map 1:1.** No remap needed; the configs/dev.yml
   vocabulary is ``['C','H','N','O','F','P','S','Cl','Br','I']`` which
   matches ``FLOWMOL3ADAPTER_N_ATOM_TYPES = 10`` exactly.
3. **Charges must be rounded + clamped.** Adapter ``c`` is a
   continuous float64 (sampled from ``N(0, 1)``). The FlowMol3 reference
   round-trips through ``Chem.Atom.GetFormalCharge`` which only takes
   ints in ``[-2, +3]``. ``np.rint`` to round, then clamp.
4. **``e`` is dense symmetric (N, N).** Take the upper triangle
   (``np.triu_indices(N, k=1)``) and drop the no-bond entries.

Why we reimplement ``build_molecule`` instead of importing it
-------------------------------------------------------------

The upstream ``flowmol.analysis.molecule_builder.build_molecule`` is
~30 lines of pure RDKit (RWMol + AddAtom + AddBond + Conformer), but
the file's module scope unconditionally imports ``dgl`` (line 4) and
its ``from_rdkit_mol`` classmethod imports ``dgl`` again at line 119.
Our framework is ``requires-python>=3.12`` and dgl has no py3.12 wheel
on the cuda121 channel; importing this module would fail at
``from rdkit_export import ...`` time on a clean py3.12 venv. The pure
RDKit assembly is duplicated here so the writer can run inside the
framework's main venv with only the ``chemistry`` extra (``rdkit``).
The metric computation (in
``data/FlowMol3/repo/fm3_evals/baselines/compute_baseline_comparison.py``)
remains behind the FlowMol3 py3.10 env boundary — it is not invoked
from this module.

NON-CLAIM: this glue is the re-inference plumbing, not a chemistry
oracle. Validity / QED / SA / logP are measured by the downstream
``tools/run_mol_eval.py``; this module only ships the writer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants — the atom-type vocabulary is owned by the FlowMol3 reference
# repo at data/FlowMol3/repo/configs/dev.yml:36. Pinning it here so a
# future FlowMol3 config change cannot silently desync the decoder.
# ---------------------------------------------------------------------------


#: Element symbols per atom-type index (FlowMol3 dev config vocabulary).
#: Index 0 = C, 1 = H, ..., 9 = I.
FLOWMOL3_ATOM_SYMBOLS: tuple[str, ...] = (
    "C", "H", "N", "O", "F", "P", "S", "Cl", "Br", "I",
)

#: Bond-type remap. The FlowMol3 reference's
#   ``flowmol.analysis.molecule_builder.bond_type_map`` is
#   ``[None, SINGLE, DOUBLE, TRIPLE, AROMATIC, None]`` — i.e. index 0
#   is the no-bond sentinel. Our adapter's no-bond is index 4 (the
#   highest index, ``N_BOND_TYPES - 1``). Remap:
#   ``adapter 4 -> 0`` (no-bond) and ``adapter 0..3 -> +1`` (SINGLE,
#   DOUBLE, TRIPLE, AROMATIC).
_BOND_REMAP: tuple[int, ...] = (1, 2, 3, 4, 0)


def _remap_bond(adapter_label: int) -> int:
    """Return the FlowMol3-reference bond index for an adapter label.

    Defensive: out-of-range labels are coerced to no-bond (``0``).
    """
    if adapter_label < 0 or adapter_label >= len(_BOND_REMAP):
        return 0
    return _BOND_REMAP[int(adapter_label)]


def _round_and_clamp_charge(charge: float) -> int:
    """Round ``charge`` to the nearest int in ``[-2, +3]``.

    The FlowMol3 reference one-hots ``charge + 2`` with ``num_classes=6``
    (data/FlowMol3/repo/flowmol/analysis/molecule_builder.py:124), so
    values outside ``[-2, +3]`` raise inside the upstream round-trip.
    RDKit's :class:`Chem.Atom` formal charge is unbounded but the
    reference vocabulary has 6 slots, so we clamp to the same window.
    """
    rounded = int(np.rint(float(charge)))
    if rounded < -2:
        return -2
    if rounded > 3:
        return 3
    return rounded


# ---------------------------------------------------------------------------
# Core assembly
# ---------------------------------------------------------------------------


def _build_mol_from_arrays(
    x: NDArray[np.float64],
    a: NDArray[np.int64],
    c: NDArray[np.float64],
    e: NDArray[np.int64],
) -> Any:
    """Pure-RDKit molecule assembly from the four endpoint arrays.

    Mirrors ``data/FlowMol3/repo/flowmol/analysis/molecule_builder.py``
    lines 268-297 (``build_molecule`` free function). Returns
    ``Chem.Mol`` or ``None`` on failure so the caller can route it to
    the validity denominator.

    Shape contract (matches the adapter's native-state lineage):

    * ``x`` — ``(n_atoms, 3)`` float64 positions (Angstrom).
    * ``a`` — ``(n_atoms,)`` int64 atom-type indices in
      ``[0, FLOWMOL3ADAPTER_N_ATOM_TYPES)``.
    * ``c`` — ``(n_atoms,)`` float64 formal-charge logits; will be
      rounded + clamped via :func:`_round_and_clamp_charge`.
    * ``e`` — ``(n_atoms, n_atoms)`` int64 dense symmetric bond labels
      in ``[0, FLOWMOL3ADAPTER_N_BOND_TYPES)``; no-bond = 4.
    """
    from rdkit import Chem
    from rdkit.Geometry import Point3D

    n_atoms = int(np.asarray(x).reshape(-1, 3).shape[0])
    if n_atoms == 0:
        return None
    a_arr = np.asarray(a, dtype=np.int64).reshape(n_atoms)
    c_arr = np.asarray(c, dtype=np.float64).reshape(n_atoms)
    e_arr = np.asarray(e, dtype=np.int64).reshape(n_atoms, n_atoms)
    x_arr = np.asarray(x, dtype=np.float64).reshape(n_atoms, 3)

    mol = Chem.RWMol()
    conformer = Chem.Conformer(int(n_atoms))
    for i in range(int(n_atoms)):
        atom_idx = int(a_arr[i])
        if atom_idx < 0 or atom_idx >= len(FLOWMOL3_ATOM_SYMBOLS):
            # Out-of-vocabulary label — coerce to carbon so the molecule
            # at least builds; downstream validity will judge it.
            atom_idx = 0
        atom = Chem.Atom(FLOWMOL3_ATOM_SYMBOLS[atom_idx])
        atom.SetFormalCharge(_round_and_clamp_charge(float(c_arr[i])))
        mol.AddAtom(atom)
        conformer.SetAtomPosition(
            int(i), Point3D(float(x_arr[i, 0]), float(x_arr[i, 1]), float(x_arr[i, 2]))
        )
    # Bonds — take the upper triangle (k=1) and drop no-bond entries.
    rows, cols = np.triu_indices(int(n_atoms), k=1)
    for r, c in zip(rows.tolist(), cols.tolist(), strict=True):
        raw = int(e_arr[int(r), int(c)])
        remapped = _remap_bond(raw)
        if remapped == 0:
            # No-bond — FlowMol3 reference sentinel.
            continue
        try:
            mol.AddBond(
                int(r), int(c), _rdkit_bond_type(remapped)
            )
        except Exception:  # noqa: BLE001 — permissive on purpose
            continue
    mol.AddConformer(conformer, assignId=True)
    try:
        Chem.SanitizeMol(mol)
    except Exception:  # noqa: BLE001 — caller routes None into validity
        return None
    return mol.GetMol()


def _rdkit_bond_type(remapped_index: int) -> Any:
    """Return the RDKit bond-type enum for a remapped bond index."""
    from rdkit import Chem

    table = {
        1: Chem.BondType.SINGLE,
        2: Chem.BondType.DOUBLE,
        3: Chem.BondType.TRIPLE,
        4: Chem.BondType.AROMATIC,
    }
    return table[int(remapped_index)]


# ---------------------------------------------------------------------------
# Public glue
# ---------------------------------------------------------------------------


def endpoint_to_rdkit_mol(
    x: NDArray[np.float64],
    a: NDArray[np.int64],
    c: NDArray[np.float64],
    e: NDArray[np.int64],
) -> Any:
    """Convert a single endpoint (x, a, c, e) tuple to ``Chem.Mol | None``."""
    return _build_mol_from_arrays(
        np.asarray(x, dtype=np.float64),
        np.asarray(a, dtype=np.int64),
        np.asarray(c, dtype=np.float64),
        np.asarray(e, dtype=np.int64),
    )


def trajectory_endpoint_to_rdkit_mol(trajectory: Mapping[str, Any]) -> Any:
    """Take the t=1 slice of a ``export_trajectory`` dict and convert it.

    The trajectory dict is the return value of
    :meth:`FlowMol3V2Adapter.export_trajectory`; it carries the per-step
    ``(traj_x, traj_c, traj_e, traj_a)`` lineage. We pick ``[-1]`` of
    each, so the call site can stay agnostic to whether the integration
    was Euler, Heun, or anything else.
    """
    if not {"traj_x", "traj_c", "traj_e", "traj_a"}.issubset(set(trajectory.keys())):
        return None
    return endpoint_to_rdkit_mol(
        x=np.asarray(trajectory["traj_x"][-1], dtype=np.float64),
        a=np.asarray(trajectory["traj_a"][-1], dtype=np.int64),
        c=np.asarray(trajectory["traj_c"][-1], dtype=np.float64),
        e=np.asarray(trajectory["traj_e"][-1], dtype=np.int64),
    )


def adapter_endpoint_to_rdkit_mol(
    adapter: Any,
    trace: Any,
) -> Any:
    """Top-level glue: take an adapter + :class:`ODEIntegratorTrace` and convert.

    Looks up the trajectory via :meth:`adapter.export_trajectory`,
    takes the t=1 slice, and converts via
    :func:`trajectory_endpoint_to_rdkit_mol`. Returns ``None`` when the
    trajectory is not found under ``trace.native_state_digest`` (e.g.
    the trace refers to a digest emitted by another adapter instance).
    """
    trajectory = adapter.export_trajectory(trace)
    if trajectory is None:
        return None
    return trajectory_endpoint_to_rdkit_mol(trajectory)


# ---------------------------------------------------------------------------
# GraphBFN conversion — graph (atom_types, bond_types, adjacency) -> Chem.Mol
# ---------------------------------------------------------------------------
#
# The GraphBFN adapter's native payload is structurally different from
# FlowMol3's, so it needs its own writer rather than a reshape into the
# FlowMol3 one:
#
# * **No coordinates.** ``GRAPHBFN_CHANNELS`` is
#   ``(atoms, bonds, adjacency, valence, charge)`` — there is no
#   coordinate channel, so the molecules built here carry NO conformer.
#   That is sufficient for the Phase-A metric panel (validity / QED / SA
#   / logP / FCD are all topology-only); it is NOT sufficient for the
#   geometry metrics (PoseBusters, RMSD, xTB energy) that the FlowMol3
#   path can reach.
# * **Existence is factored out of order.** ``adjacency`` is a binary
#   ``(N, N)`` Bernoulli mask (``adjacency_logits > 0``, diagonal
#   forced to zero) and ``bond_types`` is a SEPARATE length-``E``
#   Categorical vector over ``GRAPHBFN_BOND_VOCAB = 4`` slots. Because
#   existence already lives in ``adjacency``, all four bond slots are
#   read as bond ORDERS (single / double / triple / aromatic) — there is
#   no no-bond sentinel to strip, unlike the FlowMol3 dense matrix where
#   label 4 means "no bond".
# * **``E`` is independent of the adjacency mask.** The adapter samples
#   ``n_edges`` from its own geometric draw, so the number of
#   ``bond_types`` slots does not equal the number of ``adjacency``
#   true-cells. Slots are consumed in upper-triangular row-major order
#   and wrap (``bond_types[k % E]``) so every admitted edge gets an
#   order and the assignment stays deterministic.
#
# PROVISIONAL VOCABULARY. The adapter declares bare cardinalities
# (``GRAPHBFN_ATOM_VOCAB_QM9 = 9``, ``GRAPHBFN_ATOM_VOCAB_ZINC250K = 38``)
# with no element-symbol map anywhere, and ``data/graphbfn/repo/`` holds
# only a README (no eval code, no weights). The tables below are
# therefore authored here, sized to the adapter's cardinalities, and
# MUST be re-pinned against the published checkpoint's own vocabulary
# when the weights-acquisition phase lands. Until then any chemistry
# read off this decoder is decoration, not a result.


#: Element symbols per GraphBFN atom-type index, QM9 head (9 slots).
#: The first four slots are QM9's canonical heavy-atom set
#: ``['C', 'N', 'O', 'F']``; the remaining five extend it with the
#: standard organic set so the table fills the adapter's declared
#: ``GRAPHBFN_ATOM_VOCAB_QM9 = 9`` cardinality. PROVISIONAL — see the
#: section header.
GRAPHBFN_ATOM_SYMBOLS_QM9: tuple[str, ...] = (
    "C", "N", "O", "F", "P", "S", "Cl", "Br", "I",
)

#: Element symbols per GraphBFN atom-type index, ZINC250k (38 slots).
#: ZINC250k's canonical heavy-atom set is the same nine symbols; the
#: published GraphBFN ZINC250k head declares 38 slots (charge- and
#: valence-expanded variants in most graph-generation codebases), and the
#: expansion order is not recoverable from anything in this repo. Slots
#: 9..37 therefore decode to carbon rather than guessing an ordering.
#: PROVISIONAL — see the section header.
GRAPHBFN_ATOM_SYMBOLS_ZINC250K: tuple[str, ...] = (
    GRAPHBFN_ATOM_SYMBOLS_QM9 + ("C",) * 29
)

#: Bond-order names per GraphBFN bond-type index. Four slots, all read
#: as orders (existence lives in ``adjacency``).
GRAPHBFN_BOND_ORDER_NAMES: tuple[str, ...] = (
    "SINGLE", "DOUBLE", "TRIPLE", "AROMATIC",
)


def graphbfn_atom_symbols(dataset: str) -> tuple[str, ...]:
    """Return the provisional element-symbol table for ``dataset``.

    ``"zinc250k"`` selects the 38-slot table; anything else (including
    ``"qm9"``) selects the 9-slot QM9 table. Unknown dataset tags fall
    through to QM9 rather than raising so a typo downgrades the decode
    instead of killing a run mid-sample.
    """
    if str(dataset).lower() == "zinc250k":
        return GRAPHBFN_ATOM_SYMBOLS_ZINC250K
    return GRAPHBFN_ATOM_SYMBOLS_QM9


def _graphbfn_bond_type(order_index: int) -> Any:
    """Return the RDKit bond-type enum for a GraphBFN bond-order index.

    Out-of-range indices coerce to ``SINGLE`` so an out-of-vocabulary
    label produces a buildable (and then honestly judged) molecule
    rather than dropping the edge silently.
    """
    from rdkit import Chem

    table = {
        0: Chem.BondType.SINGLE,
        1: Chem.BondType.DOUBLE,
        2: Chem.BondType.TRIPLE,
        3: Chem.BondType.AROMATIC,
    }
    return table.get(int(order_index), Chem.BondType.SINGLE)


def graph_to_rdkit_mol(
    *,
    atom_types: NDArray[np.int64],
    bond_types: NDArray[np.int64],
    adjacency: NDArray[np.int64],
    charges: NDArray[np.float64] | None = None,
    dataset: str = "qm9",
) -> Any:
    """Convert a rounded GraphBFN graph to ``Chem.Mol | None``.

    Shape contract (matches
    :func:`adaptive_reflow.adapters.graphbfn._argmax_rounded_samples`):

    * ``atom_types`` — ``(N,)`` int64 in ``[0, atom_vocab)``.
    * ``bond_types`` — ``(E,)`` int64 in ``[0, 4)``; ``E`` need not
      relate to the adjacency mask's edge count (see the section header).
    * ``adjacency`` — ``(N, N)`` int64 binary, zero diagonal. Only the
      upper triangle is read, so an asymmetric matrix is interpreted as
      its upper triangle rather than rejected.
    * ``charges`` — optional ``(N,)`` float64 formal-charge scalars,
      rounded + clamped to ``[-2, +3]`` exactly as on the FlowMol3 path.
      ``None`` leaves every formal charge at zero.

    Returns ``None`` on an empty graph or a sanitization failure so the
    caller can charge it into the validity denominator.
    """
    from rdkit import Chem

    a_arr = np.asarray(atom_types, dtype=np.int64).reshape(-1)
    n_atoms = int(a_arr.shape[0])
    if n_atoms == 0:
        return None
    b_arr = np.asarray(bond_types, dtype=np.int64).reshape(-1)
    adj = np.asarray(adjacency, dtype=np.int64)
    if adj.shape != (n_atoms, n_atoms):
        # A mis-shaped adjacency is unrecoverable — the pair indices
        # would not address the atoms we just built.
        return None
    if charges is None:
        c_arr: NDArray[np.float64] = np.zeros((n_atoms,), dtype=np.float64)
    else:
        c_raw = np.asarray(charges, dtype=np.float64).reshape(-1)
        # A length mismatch means the charge vector does not describe
        # this graph; fall back to neutral rather than mis-assigning.
        c_arr = (
            c_raw
            if int(c_raw.shape[0]) == n_atoms
            else np.zeros((n_atoms,), dtype=np.float64)
        )

    symbols = graphbfn_atom_symbols(dataset)
    mol = Chem.RWMol()
    for i in range(n_atoms):
        atom_idx = int(a_arr[i])
        if atom_idx < 0 or atom_idx >= len(symbols):
            # Out-of-vocabulary label — coerce to carbon so the molecule
            # at least builds; downstream validity will judge it.
            atom_idx = 0
        atom = Chem.Atom(symbols[atom_idx])
        atom.SetFormalCharge(_round_and_clamp_charge(float(c_arr[i])))
        mol.AddAtom(atom)

    rows, cols = np.triu_indices(n_atoms, k=1)
    n_bond_slots = int(b_arr.shape[0])
    edge_k = 0
    for r, c in zip(rows.tolist(), cols.tolist(), strict=True):
        if int(adj[int(r), int(c)]) == 0:
            continue
        # ``E`` is independent of the adjacency mask's edge count, so the
        # order slots are consumed in upper-triangular row-major order
        # and wrap.
        order_index = (
            0 if n_bond_slots == 0 else int(b_arr[edge_k % n_bond_slots])
        )
        edge_k += 1
        try:
            mol.AddBond(int(r), int(c), _graphbfn_bond_type(order_index))
        except Exception:  # noqa: BLE001 — permissive on purpose
            continue
    try:
        Chem.SanitizeMol(mol)
    except Exception:  # noqa: BLE001 — caller routes None into validity
        return None
    return mol.GetMol()


def graphbfn_round_trajectory(
    trajectory: Mapping[str, Any],
) -> dict[str, NDArray[np.int64]] | None:
    """Argmax-round a GraphBFN ``export_trajectory`` payload.

    :meth:`GraphBFNAdapter.export_trajectory` returns the raw
    Categorical parameters (``theta_node``, ``theta_edge``,
    ``adjacency_logits``, ``charge``, ``valence``), NOT the rounded
    graph. The rounding rule mirrors the adapter's own
    ``_argmax_rounded_samples`` — argmax over the last axis for the two
    Categorical tensors, ``logits > 0`` with a zeroed diagonal for the
    Bernoulli adjacency — and is reimplemented here so this module stays
    importable without the adapter (and without numpy-on-torch).

    Returns ``None`` when the payload lacks the three required keys.
    """
    required = {"theta_node", "theta_edge", "adjacency_logits"}
    if not required.issubset(set(trajectory.keys())):
        return None
    theta_node = np.asarray(trajectory["theta_node"], dtype=np.float64)
    theta_edge = np.asarray(trajectory["theta_edge"], dtype=np.float64)
    adj_logits = np.asarray(trajectory["adjacency_logits"], dtype=np.float64)

    if theta_node.ndim == 2 and theta_node.shape[0] > 0:
        atom_types = np.argmax(theta_node, axis=-1).astype(np.int64)
    else:
        atom_types = np.zeros((0,), dtype=np.int64)
    if theta_edge.ndim == 2 and theta_edge.shape[0] > 0:
        bond_types = np.argmax(theta_edge, axis=-1).astype(np.int64)
    else:
        bond_types = np.zeros((0,), dtype=np.int64)
    if adj_logits.ndim == 2 and adj_logits.shape[0] > 0:
        adjacency = (adj_logits > 0.0).astype(np.int64)
        np.fill_diagonal(adjacency, 0)
    else:
        adjacency = np.zeros((0, 0), dtype=np.int64)
    return {
        "atom_types": atom_types,
        "bond_types": bond_types,
        "adjacency": adjacency,
    }


def graphbfn_trajectory_to_rdkit_mol(
    trajectory: Mapping[str, Any],
    *,
    dataset: str = "qm9",
) -> Any:
    """Round a GraphBFN trajectory payload and convert it to ``Chem.Mol``.

    The GraphBFN counterpart of
    :func:`trajectory_endpoint_to_rdkit_mol`. Returns ``None`` when the
    payload is malformed or the assembled molecule fails sanitization.
    """
    rounded = graphbfn_round_trajectory(trajectory)
    if rounded is None:
        return None
    return graph_to_rdkit_mol(
        atom_types=rounded["atom_types"],
        bond_types=rounded["bond_types"],
        adjacency=rounded["adjacency"],
        charges=np.asarray(trajectory.get("charge", None), dtype=np.float64)
        if trajectory.get("charge", None) is not None
        else None,
        dataset=dataset,
    )


def graphbfn_endpoint_to_rdkit_mol(
    adapter: Any,
    trace: Any,
    *,
    dataset: str = "qm9",
) -> Any:
    """Top-level GraphBFN glue: adapter + trace -> ``Chem.Mol | None``.

    The GraphBFN counterpart of :func:`adapter_endpoint_to_rdkit_mol`.
    Returns ``None`` when the trace's digest is not in the adapter's
    native-state cache (e.g. it was evicted by the LRU bound, or it was
    emitted by a different adapter instance).
    """
    trajectory = adapter.export_trajectory(trace)
    if trajectory is None:
        return None
    return graphbfn_trajectory_to_rdkit_mol(trajectory, dataset=dataset)


__all__ = [
    "FLOWMOL3_ATOM_SYMBOLS",
    "GRAPHBFN_ATOM_SYMBOLS_QM9",
    "GRAPHBFN_ATOM_SYMBOLS_ZINC250K",
    "GRAPHBFN_BOND_ORDER_NAMES",
    "adapter_endpoint_to_rdkit_mol",
    "endpoint_to_rdkit_mol",
    "graph_to_rdkit_mol",
    "graphbfn_atom_symbols",
    "graphbfn_endpoint_to_rdkit_mol",
    "graphbfn_round_trajectory",
    "graphbfn_trajectory_to_rdkit_mol",
    "trajectory_endpoint_to_rdkit_mol",
]
