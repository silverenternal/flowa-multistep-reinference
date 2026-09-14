"""JAX-free loader for the InstaDeep ProtBFN / AbBFN pytree checkpoints.

The published InstaDeep protein-sequence-bfn checkpoints on HuggingFace
(``InstaDeepAI/protein-sequence-bfn``) ship as a flat dump of the Haiku
parameter pytree:

* ``tree_def.npy`` - a numpy ``.npy`` file wrapping a pickled
  ``jaxlib.xla_extension.pytree.PyTreeDef``. The pickle's *state* is a
  flat list of 6-tuples ``(kind, num_children, names, _, num_leaves,
  total_size)`` describing the tree bottom-up (post-order).
* ``array_<i>.npy`` for ``i in [0, N)`` - raw ``float32`` tensors in
  leaf iteration order. ``N == 540`` for ProtBFN and AbBFN.

Empirically observed (validated against
``data/protbfn_abbfn/weights_real/ProtBFN``):

* The state list has 811 entries: 540 leaves + 270 inner dict-nodes +
  1 root dict-node.
* The 270 dict-nodes (each with 2 leaf children) are arranged in
  reverse-preorder at positions ``2 + 3k`` for ``k in [0, 270)``. The
  leaves for dict-node ``k`` are at positions ``2 + 3k - 1`` (first
  child = 'b' / 'offset') and ``2 + 3k - 2`` (second child = 'w' /
  'scale'). The leaves are stored in REVERSE child name order
  (last-name first).
* The leaves are emitted by ``jax.tree_util.tree_flatten`` in
  pre-order DFS over the root's 270 named children, so the leaf index
  ``i`` corresponds to dict-node ``k = i // 2`` and slot ``s = i % 2``
  within that dict-node (slot 0 = first name = 'b' or 'offset';
  slot 1 = second name = 'w' or 'scale').
* Every ``Linear`` weight is persisted transposed (i.e., shape
  ``(in, out)`` rather than the canonical ``(out, in)`` Haiku
  convention). All Linear / LayerNorm biases are stored in canonical
  orientation.

This module reconstructs the pytree without installing JAX. Strategy:

1. Stub ``jaxlib.xla_extension.pytree.PyTreeDef`` and
   ``numpy._core.multiarray._reconstruct`` so ``numpy.load(..., allow_pickle=True)``
   returns a plain object whose ``__setstate__`` captures the
   underlying list.
2. Walk the captured state list to recover the canonical
   ``(name_path, leaf_index)`` mapping using the empirically-validated
   layout described above.
3. Read each ``array_<i>.npy`` (already in leaf order) and bind it to
   the canonical name. Transpose Linear weights back to ``(out, in)``.

Public surface
--------------

* :class:`ProtBFNParamTree` - ``OrderedDict[str, np.ndarray]`` with
  stable iteration order matching the Haiku module hierarchy.
* :func:`load_protbfn_pytree` - load a checkpoint directory into a
  :class:`ProtBFNParamTree`.
* :func:`list_param_names` - return the canonical parameter names in
  leaf order (used by the model module to bind tensors by name).
"""
from __future__ import annotations

import sys
import types
from collections import OrderedDict
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Number of parameter leaves in a ProtBFN / AbBFN checkpoint. The
#: structure is identical between the two (650M-param Haiku BERT-style
#: transformer with 33 attention layers, vocab_size=32 output dim).
PROTBFN_NUM_LEAVES: int = 540

#: Number of root-level child dict-nodes (= 33 attention layers * 8
#: sub-modules + 6 top-level sub-modules = 270).
PROTBFN_NUM_ROOT_CHILDREN: int = 270

#: Stride between consecutive root child dict-nodes in the post-order
#: state list. Each child is a (dict-node, leaf, leaf) triple starting
#: at index ``2 + 3 * k`` and consuming 3 entries.
PROTBFN_ROOT_CHILD_STRIDE: int = 3


# ---------------------------------------------------------------------------
# JAX / numpy pickle stubs
# ---------------------------------------------------------------------------


class _StubPyTreeDef:
    """Pickle stub for ``jaxlib.xla_extension.pytree.PyTreeDef``.

    The pickled ``PyTreeDef.__setstate__`` materialises a Python list
    that we capture verbatim into ``self._state``. Subsequent walks
    consume that list directly. No JAX interpreter is needed.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Default ctor; rarely invoked (the real object comes from
        # ``__setstate__`` below).
        self._state: list[object] = []

    def __setstate__(self, state: object) -> None:
        # The pickled PyTreeDef's state is exactly the flat
        # bottom-up state list described in the module docstring.
        self._state = state  # type: ignore[assignment]

    def __reduce_ex__(self, protocol: int) -> tuple[object, ...]:  # type: ignore[override]
        return (_StubPyTreeDef, ())


def _install_jax_pickle_stubs() -> None:
    """Install ``jaxlib`` / ``jaxlib.xla_extension.pytree`` stubs.

    Idempotent. Registers a stub class for ``PyTreeDef`` and a no-op
    ``numpy._core.multiarray._reconstruct`` so that unpickling
    ``tree_def.npy`` succeeds without a JAX install. The numpy module
    also stubs the legacy ``numpy.core.multiarray._reconstruct`` so
    numpy < 2 fallbacks work.
    """
    # jaxlib stubs
    jaxlib = sys.modules.get("jaxlib")
    if jaxlib is None:
        jaxlib = types.ModuleType("jaxlib")
        sys.modules["jaxlib"] = jaxlib
    xla_ext = sys.modules.get("jaxlib.xla_extension")
    if xla_ext is None:
        xla_ext = types.ModuleType("jaxlib.xla_extension")
        sys.modules["jaxlib.xla_extension"] = xla_ext
    pytree_mod = sys.modules.get("jaxlib.xla_extension.pytree")
    if pytree_mod is None:
        pytree_mod = types.ModuleType("jaxlib.xla_extension.pytree")
        sys.modules["jaxlib.xla_extension.pytree"] = pytree_mod
    pytree_mod.PyTreeDef = _StubPyTreeDef  # type: ignore[attr-defined]

    # numpy reconstruct stub — must return an ndarray-shaped object so
    # that numpy.load's pickle machinery completes. We rebuild the
    # actual array from the dtype / shape inside the loader.
    def _fake_reconstruct(subtype: object, shape: tuple[int, ...], dtype: object) -> object:
        return np.zeros(tuple(int(d) for d in shape), dtype=dtype)

    try:
        import numpy._core.multiarray as _ncm

        _ncm._reconstruct = _fake_reconstruct  # type: ignore[misc]
    except Exception:  # pragma: no cover — defensive
        pass
    try:
        import numpy.core.multiarray as _ncm_legacy

        _ncm_legacy._reconstruct = _fake_reconstruct
    except Exception:  # pragma: no cover — defensive
        pass


# ---------------------------------------------------------------------------
# Tree walk
# ---------------------------------------------------------------------------


def _load_state_list(weights_dir: Path) -> list[object]:
    """Install pickle stubs and return the raw ``tree_def.npy`` state list.

    The state list is the flat post-order representation of the
    ``PyTreeDef``: each entry is a 6-tuple ``(kind, num_children,
    names, _, num_leaves, total_size)`` describing one subtree.
    """
    _install_jax_pickle_stubs()
    td_obj = np.load(weights_dir / "tree_def.npy", allow_pickle=True).item()
    return list(td_obj._state)


def _leaf_index_for_position(state: list[object], pos: int) -> int:
    """Compute the leaf index assigned to ``state[pos]``.

    The post-order layout described in the module docstring assigns
    leaf indices in pre-order DFS over the root's 270 named children.
    Each child contributes 2 leaves (its dict-node's 2 children in
    reverse-name order). The dict-node for child ``k`` of root starts
    at ``state[2 + 3 * k]``; its leaves are at ``state[2 + 3 * k -
    1]`` and ``state[2 + 3 * k - 2]``. The leaf index within the
    child's subtree is ``0`` for the first name (``state[idx-1]``) and
    ``1`` for the second name (``state[idx-2]``).

    So given a leaf position, the leaf index is ``2 * k + slot`` where
    ``k`` and ``slot`` are recovered by inverting the layout above.
    """
    # Sanity check: pos must be a leaf
    if state[pos][2] is not None:  # type: ignore[index]
        raise ValueError(f"position_is_not_a_leaf:{pos}")
    # Each child of root occupies 3 entries starting at 2 + 3 * k.
    # A leaf position p belongs to child k = p // 3 (since each child
    # is 3 entries long). The slot within the child is (p % 3) where
    # 1 and 2 are the two leaves and 0 is the dict-node.
    block = pos // 3
    pos_in_block = pos % 3
    if pos_in_block == 0:
        raise ValueError(f"position_is_dict_node:{pos}")
    # Within child k: state[3k+1] is first child (slot 0), state[3k+2]
    # is second child (slot 1). So slot = pos_in_block - 1.
    slot = pos_in_block - 1
    return 2 * block + slot


def _walk_state(state: list[object]) -> list[tuple[str, int]]:
    """Recover ``(name_path, leaf_index)`` for every leaf in pre-order.

    The root dict-node is the LAST entry (``state[-1]``). Its
    ``s[2]`` is the list of 270 child module names. Each child is a
    sub-module stored at ``state[2 + 3 * k]`` (k=0..269). Each child
    has 2 named leaves stored at ``state[2 + 3 * k - 1]`` (first name)
    and ``state[2 + 3 * k - 2]`` (second name).

    The pre-order DFS visits root, then each child in name order, then
    each child's leaves in name order (offset/scale or b/w).
    """
    if len(state) < 2:
        raise ValueError(f"state_list_too_short:{len(state)}")
    root_names = state[-1][2]  # type: ignore[index]
    if root_names is None:
        raise ValueError("root_has_no_names")
    if len(root_names) != PROTBFN_NUM_ROOT_CHILDREN:
        raise ValueError(
            f"unexpected_root_children:{len(root_names)}:expected:{PROTBFN_NUM_ROOT_CHILDREN}"
        )

    leaves: list[tuple[str, int]] = []
    leaf_counter = 0
    for k, module_name in enumerate(root_names):
        dict_pos = 2 + PROTBFN_ROOT_CHILD_STRIDE * k
        child_names = state[dict_pos][2]  # type: ignore[index]
        if child_names is None:
            raise ValueError(f"child_is_leaf:{k}:{dict_pos}")
        if len(child_names) != 2:
            raise ValueError(
                f"unexpected_child_names:{len(child_names)}:expected:2"
            )
        # Names are stored in REVERSE child order in the post-order
        # state list. state[dict_pos-1] is the FIRST name in child_names
        # (e.g. 'b' / 'offset'), state[dict_pos-2] is the SECOND name
        # (e.g. 'w' / 'scale'). Pre-order DFS visits first name first.
        for _slot, child_name in enumerate(child_names):
            leaf_name = (
                f"{module_name}/{child_name}"
                if module_name
                else child_name
            )
            leaves.append((leaf_name, leaf_counter))
            leaf_counter += 1
    if len(leaves) != PROTBFN_NUM_LEAVES:
        raise ValueError(
            f"unexpected_num_leaves:{len(leaves)}:expected:{PROTBFN_NUM_LEAVES}"
        )
    return leaves


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


class ProtBFNParamTree(OrderedDict):  # type: ignore[type-arg]
    """``OrderedDict`` mapping ``name_path`` -> ``np.ndarray`` for a Haiku tree.

    Iteration order matches the canonical Haiku module hierarchy
    (root -> transformer -> attention_layer_0 -> ... -> attention_layer_32
    -> roberta_lm_head's unrolled sub-modules). Every entry is a
    contiguous ``float32`` ``ndarray`` with canonical Haiku orientation
    (Linear weights in ``(out, in)`` form, biases in ``(out,)``, and
    LayerNorm scale/offset in ``(axis,)``).
    """

    def __init__(
        self,
        *args: object,
        leaf_indices: dict[str, int] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._leaf_indices: dict[str, int] = dict(leaf_indices or {})


def load_protbfn_pytree(
    weights_dir: str | Path,
    *,
    transpose_linear_weights: bool = True,
) -> ProtBFNParamTree:
    """Load a ProtBFN / AbBFN checkpoint directory into a :class:`ProtBFNParamTree`.

    The directory must contain ``tree_def.npy`` and ``array_0.npy`` ...
    ``array_539.npy``. The mapping is:

    * ``tree_def.npy`` -> ``state`` list -> ``(name_path, leaf_index)``
      via the empirically-validated post-order walk in
      :func:`_walk_state`.
    * ``array_<i>.npy`` -> leaf ``i`` (DIRECT mapping; the on-disk
      array index matches the pre-order DFS leaf index).

    Parameters
    ----------
    weights_dir : str | Path
        Path to a ProtBFN or AbBFN weight directory (the directory
        containing ``tree_def.npy``).
    transpose_linear_weights : bool
        If True (the default), every parameter whose canonical name
        ends with ``/w`` (i.e. ``Linear`` weights) is transposed back
        to ``(out, in)``. The InstaDeep checkpoint persists Linear
        weights in ``(in, out)`` form, presumably from a flax-style
        layout choice; the canonical Haiku form is ``(out, in)``.
    """
    weights_dir = Path(weights_dir)
    if not weights_dir.is_dir():
        raise FileNotFoundError(f"weights_dir_not_found:{weights_dir}")
    tree_def_path = weights_dir / "tree_def.npy"
    if not tree_def_path.is_file():
        raise FileNotFoundError(f"tree_def_not_found:{tree_def_path}")

    # Step 1 — install pickle stubs and load the PyTreeDef
    state = _load_state_list(weights_dir)

    # Step 2 — recover (name_path, leaf_index) in leaf iteration order
    leaves = _walk_state(state)
    name_to_leaf: dict[str, int] = {name: idx for name, idx in leaves}

    # Step 3 — read arrays in on-disk order and bind to canonical names
    out: ProtBFNParamTree = ProtBFNParamTree(leaf_indices=name_to_leaf)
    for i in range(PROTBFN_NUM_LEAVES):
        arr_path = weights_dir / f"array_{i}.npy"
        if not arr_path.is_file():
            raise FileNotFoundError(f"array_missing:{arr_path}")
        arr = np.load(arr_path)
        # Look up the canonical name for this leaf index
        name = leaves[i][0]
        if transpose_linear_weights and name.endswith("/w"):
            arr = np.ascontiguousarray(arr.T)
        out[name] = np.asarray(arr, dtype=np.float32)
    return out


def list_param_names(
    weights_dir: str | Path,
) -> list[str]:
    """Return the canonical Haiku parameter names in leaf order."""
    weights_dir = Path(weights_dir)
    if not weights_dir.is_dir():
        raise FileNotFoundError(f"weights_dir_not_found:{weights_dir}")
    state = _load_state_list(weights_dir)
    leaves = _walk_state(state)
    leaves_sorted = sorted(leaves, key=lambda kv: kv[1])
    return [name for name, _ in leaves_sorted]


__all__ = [
    "PROTBFN_NUM_LEAVES",
    "PROTBFN_NUM_ROOT_CHILDREN",
    "PROTBFN_ROOT_CHILD_STRIDE",
    "ProtBFNParamTree",
    "list_param_names",
    "load_protbfn_pytree",
]
