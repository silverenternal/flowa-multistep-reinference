"""MMFF-minimized ETKDGv3 conformer pipeline (Fix B).

The FlowMol3 paper-aligned PoseBusters-validity (PB-validity) pipeline
requires a 3D conformer-generation stage that the FlowMol3 paper
itself performs via the model's own coordinate head during inference.
For de-novo generation evaluation on SMILES strings (where the
generated coordinates are not available), the published recipe is the
RDKit ETKDGv3 distance-geometry embed + MMFF94 force-field
minimisation (per Buttenschoen et al. 2024 Chem Sci §2.2.2 — Wang et
al. 2020 J Chem Inf Model ETKDGv3 + Rappe 1992 UFF; the PoseBusters
package's own energy_ratio module, which is **COMMENTED OUT** in the
shipped ``pb_config.yaml``, uses ETKDGv3 + MMFF94 internally).

This module is a **thin wrapper** that REUSES the existing
RDKit primitives:

  1. ``rdkit.Chem.AllChem.EmbedMultipleConfs`` with ``ETKDGv3()`` and
     a fixed ``randomSeed`` for deterministic reproducibility.
  2. ``rdkit.Chem.AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=200)``
     for the force-field relaxation.

The upstream FlowMol3 repo (``data/FlowMol3/repo``) does NOT ship a
public MMFF conformer pipeline — its ``flowmol.analysis.ff_energy``
only exposes single-point energy evaluators
(:func:`compute_mmff_energy`, :func:`compute_uff_energy`); the FM3
evals submodule (``fm3_evals.geometry.geom_utils.utils``) only wraps
``MMFFOptimizeMolecule`` (single conformer, no embed). So there is
nothing to reuse at the conformer-generation layer from upstream —
this module is the canonical conformer builder.

Why a multi-conformer sweep?
----------------------------

ETKDGv3 is stochastic in its distance-bounds embedding; different
seeds and pruning paths can land in different basins. The published
PoseBusters convention is to take the PB-validity verdict of the
LOWEST-ENERGY conformer (the one closest to a local MMFF94 minimum)
— so we generate ``num_confs`` candidates, MMFF-minimize each, and
hand the lowest-energy one to PoseBusters. ``num_confs=10`` matches
the upstream FlowMol3 + FM3 default for relax evaluation.
"""
from __future__ import annotations

import logging
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem

_LOGGER = logging.getLogger(__name__)

#: Default number of ETKDGv3 candidates to generate before picking the
#: lowest-energy MMFF-minimised conformer. Matches the upstream
#: FlowMol3 / FM3 relax default of 10 conformers per molecule.
DEFAULT_NUM_CONFS: int = 10

#: Default MMFF94 optimisation max-iteration cap. Matches the
#: upstream ``flowmol3_metrics_upstream.sampled_mols_from_smiles``
#: recipe (``MMFFOptimizeMolecule(maxIters=200)``).
DEFAULT_MMFF_MAX_ITERS: int = 200

#: Default ETKDGv3 random seed for deterministic conformer
#: reproducibility. PoseBusters checks are a function of the
#: conformer; a stable seed makes the metric bit-reproducible.
DEFAULT_RANDOM_SEED: int = 42

#: Returned by :func:`embed_mmff` when no conformer survived the
#: ETKDGv3 + MMFF-minimize sweep (e.g. macrocyclic / over-large
#: graph where the distance-geometry embed fails).
MMFF_CONFORMER_FAILURE: int = -1


def embed_mmff(
    mol: Chem.Mol,
    *,
    num_confs: int = DEFAULT_NUM_CONFS,
    seed: int = DEFAULT_RANDOM_SEED,
    max_iters: int = DEFAULT_MMFF_MAX_ITERS,
) -> tuple[int, float]:
    """Build ``num_confs`` ETKDGv3 candidates and MMFF-minimize them.

    Parameters
    ----------
    mol : :class:`rdkit.Chem.Mol`
        Heavy-atom RDKit mol (no explicit Hs). The function
        appends Hs internally, embeds with ETKDGv3, MMFF-minimises
        each conformer, then strips the Hs back off so the
        returned conformer is on the heavy-atom mol.
    num_confs : int, default 10
        Number of ETKDGv3 candidate conformers to generate before
        the MMFF-minimise sweep.
    seed : int, default 42
        Random seed for the ETKDGv3 distance-geometry embed.
    max_iters : int, default 200
        Maximum iterations per MMFF94 force-field minimisation
        pass. Matches the upstream FlowMol3 wrapper
        (``flowmol3_metrics_upstream.sampled_mols_from_smiles``).

    Returns
    -------
    tuple[int, float]
        ``(conformer_id_of_lowest_energy_mol, energy_kcal_per_mol)``.
        On failure (embed or all MMFF optimisations failed),
        returns ``(MMFF_CONFORMER_FAILURE, float('inf'))`` and the
        input ``mol`` is left with zero conformers.

    Notes
    -----
    The conformer is **assigned in-place** on ``mol`` so callers can
    hand it straight to :class:`posebusters.PoseBusters.bust` after
    this function returns. The ``conformer_id_of_lowest_energy_mol``
    is the ``confId`` of the surviving lowest-energy conformer on
    ``mol``; on a single-conformer build that is always ``0``.

    The MMFF94 force field is used in its default variant
    (``MMFFGetMoleculeProperties(mol)``). MMFF can refuse some
    topologies (transition metals, very strained cages); for those
    molecules the function returns the failure tuple and logs at
    DEBUG level.
    """
    if mol is None:
        return MMFF_CONFORMER_FAILURE, float("inf")

    try:
        mol_h = Chem.AddHs(mol)
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        _LOGGER.debug("mmff_conformer.embed_mmff: AddHs failed (%s)", exc)
        return MMFF_CONFORMER_FAILURE, float("inf")

    params = AllChem.ETKDGv3()  # type: ignore[attr-defined]
    params.randomSeed = int(seed)

    try:
        conf_ids = list(
            AllChem.EmbedMultipleConfs(mol_h, numConfs=int(num_confs), params=params)  # type: ignore[attr-defined]
        )
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        _LOGGER.debug("mmff_conformer.embed_mmff: EmbedMultipleConfs failed (%s)", exc)
        return MMFF_CONFORMER_FAILURE, float("inf")

    if not conf_ids:
        _LOGGER.debug(
            "mmff_conformer.embed_mmff: EmbedMultipleConfs produced 0 conformers"
        )
        return MMFF_CONFORMER_FAILURE, float("inf")

    # MMFF-minimize each conformer in place. ``MMFFOptimizeMoleculeConfs``
    # returns a list of convergence codes (0 == converged) and writes
    # the minimised coordinates back onto the conformers.
    try:
        AllChem.MMFFOptimizeMoleculeConfs(mol_h, maxIters=int(max_iters))  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        _LOGGER.debug(
            "mmff_conformer.embed_mmff: MMFFOptimizeMoleculeConfs failed (%s)", exc
        )

    # Score each conformer with single-point MMFF94 and pick the
    # lowest-energy one. ``MMFFOptimizeMoleculeConfs`` returns a tuple
    # ``(converged_flag, energy)`` per conformer; when it fails
    # outright, ``results`` is None and we fall back to the embed
    # geometry for the conformer count.
    best_cid: int = MMFF_CONFORMER_FAILURE
    best_energy: float = float("inf")
    for cid in conf_ids:
        try:
            props = AllChem.MMFFGetMoleculeProperties(mol_h)  # type: ignore[attr-defined]
            ff = AllChem.MMFFGetMoleculeForceField(mol_h, props, confId=cid)  # type: ignore[attr-defined]
            if ff is None:
                continue
            energy = float(ff.CalcEnergy())
        except Exception as exc:  # noqa: BLE001 — permissive on purpose
            _LOGGER.debug(
                "mmff_conformer.embed_mmff: MMFF energy calc failed on confId=%d (%s)",
                cid,
                exc,
            )
            continue
        if energy < best_energy:
            best_energy = energy
            best_cid = int(cid)

    # Some MMFF optimisations may have failed; the lowest-energy
    # conformer on success is always a real ``confId`` ≥ 0.
    if best_cid < 0:
        _LOGGER.debug(
            "mmff_conformer.embed_mmff: no MMFF energy computed across %d conformers",
            len(conf_ids),
        )
        return MMFF_CONFORMER_FAILURE, float("inf")

    # Strip Hs and copy the winning conformer onto the heavy-atom mol.
    # AddHs appends Hs at the end of the atom list, so heavy-atom
    # positions are identical between ``mol_h`` and the original ``mol``
    # — only the conformer needs to be transferred.
    try:
        new_mol = Chem.RemoveHs(mol_h)
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        _LOGGER.debug("mmff_conformer.embed_mmff: RemoveHs failed (%s)", exc)
        return MMFF_CONFORMER_FAILURE, float("inf")
    if new_mol.GetNumConformers() == 0:
        return MMFF_CONFORMER_FAILURE, float("inf")

    # Clear any prior conformers on ``mol`` then add the chosen one.
    for i in range(mol.GetNumConformers() - 1, -1, -1):
        mol.RemoveConformer(i)
    winning_conf = new_mol.GetConformer(best_cid)
    mol.AddConformer(winning_conf, assignId=True)

    _LOGGER.debug(
        "mmff_conformer.embed_mmff: lowest-energy conformer cid=%d energy=%.4f kcal/mol "
        "(num_confs=%d, seed=%d, max_iters=%d)",
        best_cid,
        best_energy,
        int(num_confs),
        int(seed),
        int(max_iters),
    )
    return best_cid, best_energy


def embed_mmff_smiles(
    smiles: str,
    *,
    num_confs: int = DEFAULT_NUM_CONFS,
    seed: int = DEFAULT_RANDOM_SEED,
    max_iters: int = DEFAULT_MMFF_MAX_ITERS,
) -> tuple[Chem.Mol | None, float]:
    """Convenience wrapper: SMILES -> RDKit Mol with MMFF-min conformer.

    Returns ``(mol, energy)`` where ``mol`` is a heavy-atom RDKit mol
    with one conformer assigned (the lowest-energy ETKDGv3 + MMFF94
    candidate), or ``(None, inf)`` on parse / embed / minimisation
    failure.
    """
    if not smiles:
        return None, float("inf")
    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        _LOGGER.debug("mmff_conformer.embed_mmff_smiles: MolFromSmiles failed (%s)", exc)
        return None, float("inf")
    if mol is None:
        return None, float("inf")
    cid, energy = embed_mmff(mol, num_confs=num_confs, seed=seed, max_iters=max_iters)
    if cid < 0:
        return None, float("inf")
    return mol, energy


__all__ = [
    "DEFAULT_NUM_CONFS",
    "DEFAULT_MMFF_MAX_ITERS",
    "DEFAULT_RANDOM_SEED",
    "MMFF_CONFORMER_FAILURE",
    "embed_mmff",
    "embed_mmff_smiles",
]
