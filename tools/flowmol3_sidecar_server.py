#!/usr/bin/env python3
"""Python 3.11 sidecar server hosting the FlowMol3 Lightning checkpoint.

Architecture
------------

This script runs *only* inside the project's Python 3.11 sidecar venv at
``/home/hugo/.venv-flowmol311`` because ``dgl`` has no Python 3.12 wheel
and the upstream ``flowmol`` ``pyproject.toml`` pins
``requires-python = ">=3.10,<3.11"``. The framework at the project's
main Python 3.12 venv owns the ODE loop; the sidecar owns the real
FlowMol3 forward pass.

Wire protocol (one JSON object per line, LF-terminated, UTF-8)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :mod:`adaptive_reflow.adapters.flowmol3_sidecar` for the full
spec. In short:

* ``{"cmd": "init", ...}`` -- eagerly load the checkpoint and reply
  ``{"status": "ready", "epoch": ..., "global_step": ...,
  "atom_map": [...], ...}``. This must complete before any
  ``denoise`` request is sent.
* ``{"cmd": "denoise", "x": ..., "a": ..., "c": ..., "e": ..., "t": ...}``
  -- build a :class:`dgl.DGLGraph`, run
  ``model.vector_field.forward(g, t=...)`` (the
  ``EndpointVectorField.forward`` path used inside
  :meth:`CTMCVectorField.step`), and reply with the endpoint
  predictions as numpy arrays.
* ``{"cmd": "shutdown"}`` -- exit cleanly.

All errors are returned as
``{"status": "error", "code": "...", "message": "..."}``; the process
stays alive so the framework can surface the error and decide whether
to retry or fall back to the synthetic NumPy velocity field.

CLI
~~~

::

    python tools/flowmol3_sidecar_server.py \\
        --weights data/flowmol3/weights_real/checkpoints/last.ckpt \\
        --device cpu \\
        --n-timesteps 1 \\
        --config-yaml data/flowmol3/weights_real/config.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Force unbuffered stdio so the framework's bridge never blocks on a
# full pipe. ``PYTHONUNBUFFERED=1`` is set by the bridge but the
# ``-u`` CLI flag is belt-and-suspenders.
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flowmol3_sidecar_server",
        description=(
            "Python 3.11 sidecar server that hosts the FlowMol3 "
            "Lightning checkpoint and serves JSON-line denoise requests."
        ),
    )
    parser.add_argument(
        "--weights",
        required=True,
        type=str,
        help="Absolute path to the FlowMol3 last.ckpt checkpoint.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        type=str,
        help="Torch device (cpu or cuda:0). Default: cpu.",
    )
    parser.add_argument(
        "--n-timesteps",
        default=1,
        type=int,
        help=(
            "Default number of integration steps per denoise call. "
            "Default 1; the framework integrates over [0, 1] "
            "externally and only needs the endpoint prediction."
        ),
    )
    parser.add_argument(
        "--config-yaml",
        default=None,
        type=str,
        help=(
            "Optional absolute path to the flowmol3 config.yaml. "
            "When omitted, the sidecar parses the parent directory's "
            "config.yaml if one exists."
        ),
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Stub n_atoms histogram
# ---------------------------------------------------------------------------


def _write_stub_n_atoms_histogram(path: Path) -> None:
    """Create a placeholder ``train_data_n_atoms_histogram.pt`` file.

    The FlowMol ``__init__`` builds ``self.n_atoms_dist`` from this file
    but only ``sample_n_atoms`` / ``sample_random_sizes`` consume it.
    The denoise path never calls them, so a 3-bin uniform stub is
    sufficient.
    """
    import torch  # local import; torch is heavy and sidecar-only

    n_atoms = torch.tensor([1, 8, 32], dtype=torch.long)
    counts = torch.tensor([1, 1, 1], dtype=torch.long)
    torch.save((n_atoms, counts), str(path))


def _write_stub_marginal_dists_file(path: Path) -> None:
    """Create a placeholder ``train_data_marginal_dists.pt`` file.

    The current FlowMol ``__init__`` (the marginal-dists load is
    commented out at ``flowmol/models/flowmol.py:173``) does not read
    this file, but the path is still stored as
    ``self.marginal_dists_file``. An empty torch.save() placeholder is
    sufficient.
    """
    import torch  # local import; torch is heavy and sidecar-only

    torch.save(
        {
            "p_a": torch.zeros(0),
            "p_c": torch.zeros(0),
            "p_e": torch.zeros(0),
            "p_c_given_a": torch.zeros(0),
        },
        str(path),
    )


def _write_stub_valency_file(path: Path, atom_map: list[str]) -> None:
    """Create a placeholder ``train_data_valencies_*.json`` file.

    :class:`flowmol.analysis.metrics.MoleculeStability` requires this
    file at init time even though the denoise path never invokes the
    stability function. We emit a JSON dict whose structure matches
    ``flowmol/analysis/metrics.py:loaded_dict`` -- atom symbol ->
    {charge -> [valencies]} -- using RDKit-style standard valencies.
    The values are only read by ``check_stability``; nothing in the
    vector-field forward pass touches them.
    """
    import json  # local import; sidecar-only

    # Standard organic valencies per atom symbol, indexed by integer
    # formal charge. The dummy "Br"/"I"/"F"/"P"/"Cl" rows fall back to
    # the most permissive sensible default (1, 2, 3, 4, 5).
    standard: dict[str, dict[int, list[int]]] = {
        "H": {0: [1], 1: [0], -1: [0]},
        "C": {0: [4], 1: [3], -1: [3], 2: [2], -2: [2], 3: [1], -3: [1]},
        "N": {0: [3], 1: [4], -1: [2], 2: [1], -2: [1], 3: [0]},
        "O": {0: [2], 1: [3], -1: [1], 2: [0]},
        "F": {0: [1], 1: [2], -1: [0]},
        "P": {0: [3, 5], 1: [4], -1: [2], 2: [3], -2: [1]},
        "S": {0: [2, 4, 6], 1: [3, 5], -1: [1, 3], 2: [4], -2: [2]},
        "Cl": {0: [1, 3, 5, 7], 1: [2, 4, 6], -1: [0, 2, 4, 6]},
        "Br": {0: [1, 3, 5, 7], 1: [2, 4, 6], -1: [0, 2, 4, 6]},
        "I": {0: [1, 3, 5, 7], 1: [2, 4, 6], -1: [0, 2, 4, 6]},
    }
    payload = {
        sym: {str(charge): [int(v) for v in vals]
              for charge, vals in standard.get(sym, {0: [1, 2, 3, 4]}).items()}
        for sym in atom_map
    }
    with open(path, "w") as f:
        json.dump(payload, f)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def _load_model(
    *,
    weights_path: str,
    device: str,
    config_yaml: str | None,
) -> tuple[Any, dict[str, Any], tempfile.TemporaryDirectory]:
    """Load the FlowMol3 Lightning checkpoint; return ``(model, info, tmpdir)``.

    The model is moved to ``device`` and set to ``eval()``. A
    :class:`tempfile.TemporaryDirectory` is returned so the caller can
    hold a reference to the stub files (preventing premature GC).
    """
    # Local imports keep the module loadable from lightweight tests
    # (e.g., an ``import flowmol3_sidecar_server`` smoke check).
    import torch  # noqa: PLC0415
    import yaml  # noqa: PLC0415

    import dgl  # noqa: F401, PLC0415  -- sidecar-only import
    from flowmol.model_utils.load import model_from_config  # noqa: PLC0415

    weights_abs = str(Path(weights_path).resolve())
    if not os.path.exists(weights_abs):
        raise FileNotFoundError(f"weights_not_found:{weights_abs}")

    cfg_path = config_yaml
    if cfg_path is None:
        # Fall back to ``config.yaml`` next to the ``checkpoints/`` dir.
        ckpt_dir = Path(weights_abs).parent
        candidate = ckpt_dir.parent / "config.yaml"
        if candidate.exists():
            cfg_path = str(candidate.resolve())
    if cfg_path is None or not os.path.exists(cfg_path):
        raise FileNotFoundError(
            "config_yaml_not_found: expected --config-yaml or "
            "config.yaml next to checkpoints/"
        )
    with open(cfg_path, "r") as f:
        config = yaml.safe_load(f)

    # Stub the two ``.pt`` files the FlowMol constructor requires (only
    # the n_atoms histogram is actually loaded; the marginal_dists load
    # is commented out at flowmol/models/flowmol.py:173 but we still
    # write a placeholder so future versions do not break). Also stub
    # the valency JSON that ``MoleculeStability`` reads on init even
    # though the denoise path never calls the stability function.
    tmpdir = tempfile.TemporaryDirectory(prefix="flowmol3_sidecar_stub_")
    stub_dir = Path(tmpdir.name)
    n_atoms_hist = stub_dir / "train_data_n_atoms_histogram.pt"
    marginal_dists = stub_dir / "train_data_marginal_dists.pt"
    valency_json = stub_dir / "train_data_valencies_kekulized.json"
    _write_stub_n_atoms_histogram(n_atoms_hist)
    _write_stub_marginal_dists_file(marginal_dists)
    _write_stub_valency_file(valency_json, list(config["dataset"]["atom_map"]))

    # Patch the config's data paths to point at our stubs.
    config = dict(config)
    config["dataset"] = dict(config.get("dataset", {}))
    config["dataset"]["processed_data_dir"] = str(stub_dir)

    # ``FlowMol.load_from_checkpoint`` instantiates ``FlowMol(__init__)``
    # with the kwargs we pass and then loads the ckpt weights. The
    # ``processed_data_dir`` indirection in ``__init__`` will rewrite
    # ``n_atoms_hist_file`` / ``marginal_dists_file`` against our stub
    # directory.
    model = model_from_config(config, seed_ckpt=weights_abs)

    # Move to device and freeze.
    model.eval()
    try:
        model.to(device)
    except (RuntimeError, ValueError):
        # CPU is always available; fall back silently.
        model.to("cpu")
        device = "cpu"
    for param in model.parameters():
        param.requires_grad_(False)

    # Read ckpt metadata for the ``ready`` frame.
    ckpt = torch.load(weights_abs, map_location="cpu")
    if isinstance(ckpt, dict) and "callbacks" in ckpt:
        # PyTorch Lightning checkpoint dict.
        epoch = ckpt.get("epoch", -1)
        global_step = ckpt.get("global_step", -1)
    else:
        epoch = -1
        global_step = -1

    info = {
        "epoch": int(epoch) if epoch is not None else -1,
        "global_step": int(global_step) if global_step is not None else -1,
        "atom_map": list(config["dataset"]["atom_map"]),
        "dataset_name": str(config["dataset"]["dataset_name"]),
        "parameterization": str(config["mol_fm"]["parameterization"]),
        "explicit_aromaticity": bool(
            config["mol_fm"]["explicit_aromaticity"]
        ),
        "fake_atom_p": float(config["mol_fm"]["fake_atom_p"]),
        "ctmc": True,
        "device": str(device),
        "weights_path": weights_abs,
        "config_yaml": str(Path(cfg_path).resolve()),
    }
    return model, info, tmpdir


# ---------------------------------------------------------------------------
# Denoise core
# ---------------------------------------------------------------------------


# Adapter-side constants. Mirrored from
# ``adaptive_reflow.adapters.flowmol3_v2_adapter`` so the sidecar does
# not have to import the framework (which would pull in the
# Python-3.12-only modules).
ADAPTER_N_ATOM_TYPES = 10
ADAPTER_N_BOND_TYPES = 5
ADAPTER_TO_MODEL_BOND: tuple[int, ...] = (1, 2, 3, 1, 0)
MODEL_CHARGE_VALUES: tuple[int, ...] = (-2, -1, 0, 1, 2, 3)
MODEL_ATOM_TOKENS = 12  # 10 elements + 1 fake + 1 mask
MODEL_CHARGE_TOKENS = 7  # 6 charges + 1 mask
MODEL_BOND_TOKENS = 5   # 4 bond orders + 1 mask


def _build_dgl_graph(
    *,
    n_atoms: int,
    atom_token_dim: int,
    charge_token_dim: int,
    bond_token_dim: int,
    device: Any,
) -> Any:
    """Construct a fully-connected ``dgl.DGLGraph`` for a single molecule.

    A single-molecule graph is the *bidirectional complete graph* on
    ``n_atoms`` nodes: every ordered pair ``(i, j)`` with ``i != j``
    produces one directed edge. Self-loops are NOT included because the
    upstream FlowMol data loader (``flowmol/data_processing/dataset.py``)
    builds ``edges = cat(upper_triangle, lower_triangle)`` and the
    model splits features back into ``ue_feats``/``le_feats`` via the
    upper-edge mask -- a self-loop would unbalance the counts and the
    ``ue_feats + le_feats`` tensor add at ``vector_field.py:344`` would
    raise ``RuntimeError: sizes 15 and 21 mismatch``.

    Edge ordering is therefore: ``[upper-triangle (i < j)] ++ [lower-
    triangle (i > j)]``, which lets the first ``n*(n-1)/2`` edges be
    the upper mask and the last ``n*(n-1)/2`` edges be the lower mask.
    """
    import dgl  # local import; sidecar-only
    import torch  # local import; sidecar-only

    n = int(n_atoms)
    src_upper, dst_upper = [], []
    src_lower, dst_lower = [], []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if i < j:
                src_upper.append(i)
                dst_upper.append(j)
            else:
                src_lower.append(i)
                dst_lower.append(j)
    src = src_upper + src_lower
    dst = dst_upper + dst_lower
    g = dgl.graph(
        (torch.tensor(src, dtype=torch.int64),
         torch.tensor(dst, dtype=torch.int64)),
        num_nodes=n,
        device=device,
    )

    node_batch_idx = torch.zeros(n, dtype=torch.int64, device=device)
    n_upper = len(src_upper)
    upper_edge_mask = torch.zeros(g.num_edges(), dtype=torch.bool, device=device)
    upper_edge_mask[:n_upper] = True

    # Pre-allocate the categorical ``*_t`` tensors the vector field's
    # ``forward`` reads. We set them per-call below.
    g.ndata["a_t"] = torch.zeros(
        (n, int(atom_token_dim)), device=device
    )
    g.ndata["c_t"] = torch.zeros(
        (n, int(charge_token_dim)), device=device
    )
    g.edata["e_t"] = torch.zeros(
        (g.num_edges(), int(bond_token_dim)), device=device
    )

    return g, node_batch_idx, upper_edge_mask


def _set_graph_state(
    g: Any,
    *,
    x: Any,
    a: Any,
    c: Any,
    e: Any,
) -> None:
    """Stamp ``x_t``, ``a_t``, ``c_t``, ``e_t`` from numpy arrays.

    The FlowMol ``forward`` reads ``g.ndata['a_t'].argmax(-1)`` etc.,
    so the categorical tensors are one-hot encoded.

    Edge ordering must match :func:`_build_dgl_graph`: ``upper-triangle
    (i < j) ++ lower-triangle (i > j)``. The adapter passes the bond
    matrix as a symmetric ``(n_atoms, n_atoms)`` int tensor; we gather
    the flat per-edge labels in the same order so the model's
    ``g.edata['e_t']`` aligns with the message function's edge
    iteration.
    """
    import torch  # local import; sidecar-only

    n_atoms = int(x.shape[0])
    g.ndata["x_t"] = x.to(g.device, dtype=torch.float32)
    # Atom: one-hot over ADAPTER_N_ATOM_TYPES, then padded to the
    # model's token width (12 = 10 elements + 1 fake + 1 mask). The
    # adapter's 10-element vocabulary indexes the *non-fake* atoms, so
    # we leave the fake/mask slots at zero and let the model treat the
    # unmapped positions as zero probability.
    a_idx = a.to(torch.int64).clamp(0, ADAPTER_N_ATOM_TYPES - 1)
    a_onehot = torch.nn.functional.one_hot(
        a_idx, num_classes=MODEL_ATOM_TOKENS
    ).to(dtype=torch.float32, device=g.device)
    g.ndata["a_t"] = a_onehot
    # Charge: continuous float -> nearest charge class, then one-hot
    # over MODEL_CHARGE_TOKENS (6 values + 1 mask).
    charge_values_t = torch.tensor(
        MODEL_CHARGE_VALUES, dtype=torch.float32, device=g.device
    )
    c_diff = (c.to(dtype=torch.float32, device=g.device).unsqueeze(-1)
              - charge_values_t.unsqueeze(0)).abs()
    c_idx = c_diff.argmin(dim=-1).to(torch.int64)
    c_onehot = torch.nn.functional.one_hot(
        c_idx, num_classes=MODEL_CHARGE_TOKENS
    ).to(dtype=torch.float32, device=g.device)
    g.ndata["c_t"] = c_onehot
    # Bond: re-index adapter->model, then one-hot over MODEL_BOND_TOKENS
    # (none/1/2/3 + mask). The adapter's ``aromatic`` label folds onto
    # ``single`` (kekulized training set). We must flatten the
    # ``(n_atoms, n_atoms)`` bond matrix into the ``(num_edges,)``
    # edge-order the graph was built with.
    e_np = e.detach().to("cpu", dtype=torch.int64).numpy()
    upper_pairs, lower_pairs = [], []
    for i in range(n_atoms):
        for j in range(n_atoms):
            if i == j:
                continue
            if i < j:
                upper_pairs.append((i, j))
            else:
                lower_pairs.append((i, j))
    e_flat = [int(e_np[i, j]) for (i, j) in (upper_pairs + lower_pairs)]
    e_idx = torch.tensor(
        e_flat, dtype=torch.int64, device=g.device
    ).clamp(0, ADAPTER_N_BOND_TYPES - 1)
    e_model = torch.tensor(
        ADAPTER_TO_MODEL_BOND, dtype=torch.int64, device=g.device
    )[e_idx]
    e_onehot = torch.nn.functional.one_hot(
        e_model, num_classes=MODEL_BOND_TOKENS
    ).to(dtype=torch.float32, device=g.device)
    g.edata["e_t"] = e_onehot


def _extract_endpoints(
    g: Any,
    dst_dict: dict[str, Any],
    n_atoms: int,
) -> tuple[Any, Any, Any, Any]:
    """Convert ``dst_dict`` from the model into numpy endpoints.

    Returns ``(x_out, a_out, c_out, e_out)`` as numpy arrays.
    """
    import numpy as np  # local import; sidecar-only
    import torch  # local import; sidecar-only

    # x: predicted 3D positions, (n_atoms, 3).
    x_out = dst_dict["x"].detach().to("cpu").to(torch.float64).numpy()
    x_out = x_out.reshape(int(n_atoms), 3)

    # a: argmax of softmax over atom types; map back to the adapter's
    # 10-element vocabulary (drop the model's fake + mask slots).
    a_probs = dst_dict["a"].detach().to("cpu", dtype=torch.float64).numpy()
    if a_probs.shape[-1] >= ADAPTER_N_ATOM_TYPES:
        a_probs = a_probs[..., :ADAPTER_N_ATOM_TYPES]
    a_out = a_probs.argmax(axis=-1).astype(np.int64)

    # c: expected value under the charge softmax (continuous relaxation
    # matches the flow-matching linear interpolant used by the
    # adapter).
    if "c" in dst_dict:
        c_probs = dst_dict["c"].detach().to("cpu", dtype=torch.float64).numpy()
        charge_values = np.asarray(MODEL_CHARGE_VALUES, dtype=np.float64)
        c_out = (c_probs[..., : charge_values.shape[0]] * charge_values).sum(
            axis=-1
        )
    else:
        c_out = np.zeros(int(n_atoms), dtype=np.float64)

    # e: argmax of the upper-triangle bond logits. The FlowMol3 vector
    # field returns bond logits for the upper-triangle edges only
    # (``ue_feats + le_feats`` in ``vector_field.py:344``); the
    # downstream adapter wants a symmetric ``(n_atoms, n_atoms)`` bond
    # matrix, so we scatter each argmax label back into its ``(i, j)``
    # slot and mirror across the diagonal. The diagonal is filled with
    # ``no-bond`` (``4``).
    e_probs = dst_dict["e"].detach().to("cpu", dtype=torch.float64).numpy()
    e_model_argmax = e_probs.argmax(axis=-1).astype(np.int64)
    MODEL_TO_ADAPTER_BOND = (4, 0, 1, 2)  # none, single, double, triple
    e_out_partial = np.asarray(MODEL_TO_ADAPTER_BOND, dtype=np.int64)[
        e_model_argmax
    ]
    e_out = np.full((int(n_atoms), int(n_atoms)), 4, dtype=np.int64)
    upper_pairs = [
        (i, j) for i in range(int(n_atoms)) for j in range(i + 1, int(n_atoms))
    ]
    assert len(upper_pairs) == e_out_partial.shape[0], (
        f"upper_edge_count_mismatch: graph has {len(upper_pairs)} upper "
        f"edges but model emitted {e_out_partial.shape[0]} bond logits"
    )
    for k, (i, j) in enumerate(upper_pairs):
        label = int(e_out_partial[k])
        e_out[i, j] = label
        e_out[j, i] = label

    return x_out, a_out, c_out, e_out


def _denoise_one(
    model: Any,
    x: Any,
    a: Any,
    c: Any,
    e: Any,
    t: float,
    *,
    device: Any,
) -> tuple[Any, Any, Any, Any]:
    """Run a single ``model.vector_field.forward`` on the current state."""
    import torch  # local import; sidecar-only

    n_atoms = int(x.shape[0])
    g, node_batch_idx, upper_edge_mask = _build_dgl_graph(
        n_atoms=n_atoms,
        atom_token_dim=MODEL_ATOM_TOKENS,
        charge_token_dim=MODEL_CHARGE_TOKENS,
        bond_token_dim=MODEL_BOND_TOKENS,
        device=device,
    )
    _set_graph_state(g, x=x, a=a, c=c, e=e)

    t_tensor = torch.full(
        (1,), float(t), dtype=torch.float32, device=device
    )
    with torch.no_grad():
        dst_dict = model.vector_field(
            g,
            t=t_tensor,
            node_batch_idx=node_batch_idx,
            upper_edge_mask=upper_edge_mask,
            apply_softmax=True,
            remove_com=True,
        )
    return _extract_endpoints(g, dst_dict, n_atoms)


# ---------------------------------------------------------------------------
# I/O loop
# ---------------------------------------------------------------------------


def _emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _read_line() -> str | None:
    line = sys.stdin.readline()
    if not line:
        return None
    return line


def _serve(
    *,
    weights_path: str,
    device: str,
    n_timesteps: int,
    config_yaml: str | None,
) -> int:
    # ``import torch`` only here so an import failure surfaces a clear
    # JSON error frame instead of a hard process exit at import time.
    try:
        import torch  # noqa: F401, PLC0415
    except ImportError as exc:  # pragma: no cover
        _emit({
            "status": "error",
            "code": "torch_import_failed",
            "message": f"{exc.__class__.__name__}:{exc}",
        })
        return 2

    try:
        model, info, tmpdir = _load_model(
            weights_path=weights_path,
            device=device,
            config_yaml=config_yaml,
        )
    except Exception as exc:
        _emit({
            "status": "error",
            "code": "model_load_failed",
            "message": f"{exc.__class__.__name__}:{exc}",
        })
        return 3

    info_payload = {"status": "ready", **info, "default_n_timesteps": int(n_timesteps)}

    # Track the tmpdir so it survives the lifetime of the process.
    _state = {"tmpdir": tmpdir, "model": model, "info": info, "device": device}

    # SIGTERM / SIGINT -> graceful shutdown. The framework sends
    # ``{"cmd": "shutdown"}`` explicitly; this is the fallback.
    def _signal_handler(signum: int, frame: Any) -> None:
        _emit({"status": "shutdown", "signal": int(signum)})
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    _emit(info_payload)

    import numpy as np  # local import; sidecar-only

    while True:
        line = _read_line()
        if line is None:
            # EOF; framework closed our stdin.
            return 0
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _emit({
                "status": "error",
                "code": "invalid_json",
                "message": f"{exc.msg} at line {exc.lineno}",
            })
            continue
        cmd = msg.get("cmd")
        if cmd == "shutdown":
            _emit({"status": "shutdown"})
            return 0
        if cmd == "init":
            # The framework re-initializes if we crashed; idempotent.
            _emit(info_payload)
            continue
        if cmd == "denoise":
            t_start = time.monotonic()
            try:
                x_np = np.asarray(msg["x"], dtype=np.float64)
                a_np = np.asarray(msg["a"], dtype=np.int64)
                c_np = np.asarray(msg["c"], dtype=np.float64)
                e_np = np.asarray(msg["e"], dtype=np.int64)
                t_val = float(msg.get("t", 0.5))
                import torch  # local import; sidecar-only
                x_t = torch.from_numpy(x_np)
                a_t = torch.from_numpy(a_np)
                c_t = torch.from_numpy(c_np)
                e_t = torch.from_numpy(e_np)
                x_out, a_out, c_out, e_out = _denoise_one(
                    _state["model"], x_t, a_t, c_t, e_t, t_val,
                    device=_state["device"],
                )
                _emit({
                    "status": "ok",
                    "x_out": x_out.tolist(),
                    "a_out": a_out.tolist(),
                    "c_out": c_out.tolist(),
                    "e_out": e_out.tolist(),
                    "elapsed_s": time.monotonic() - t_start,
                })
            except Exception as exc:
                _emit({
                    "status": "error",
                    "code": "denoise_failed",
                    "message": f"{exc.__class__.__name__}:{exc}",
                })
            continue
        _emit({
            "status": "error",
            "code": "unknown_command",
            "message": f"unknown cmd: {cmd!r}",
        })


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return _serve(
        weights_path=str(args.weights),
        device=str(args.device),
        n_timesteps=int(args.n_timesteps),
        config_yaml=(str(args.config_yaml) if args.config_yaml else None),
    )


if __name__ == "__main__":
    raise SystemExit(main())