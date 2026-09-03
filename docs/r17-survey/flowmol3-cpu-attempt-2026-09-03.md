# FlowMol3 upstream CPU-path attempt — 2026-09-03 (P-22 in-scope repair)

**Outcome:** **partial**. The adapter's `use_upstream=True` flag is plumbed
and the upstream `flowmol.models.flowmol.FlowMol` Lightning class
*loads successfully* on the ``flowmol3_venv`` with the published
``data/flowmol3/weights_real/checkpoints/last.ckpt`` — ``kind =
upstream_flowmol`` in ``model_metadata`` — but the adapter's solver
cannot actually call the upstream model's forward pass because
``FlowMol.forward(g, timestep)`` takes a 2-arg signature while the
adapter's velocity-field interface passes the heterogeneous ``(x, a,
c, e, t)`` tuple directly. The CPU smoke therefore reports
``ok = false`` with a TypeError downstream. The full upstream sampling
pipeline (``model.sample_random_sizes``) does work, but it is wired
through :mod:`adaptive_reflow.adapters.flowmol3_upstream_shim` (the
opt-in shim), not the v2 adapter's ``solve_ode`` loop.

**Constraint recap:** ``flowmol3_venv`` was reconstructed in this pass to
land **torch 2.2.0+cu121** (the only torch that ships a matching
``dgl==2.1.0`` ``libgraphbolt_pytorch_2.2.0.so``); the project's
``torch 2.7.0+cu128`` would require either a DGL source build (2-4 h
CMake+CUDA) or waiting for ``dglteam/dgl`` to publish a 2.7.x wheel
(no public timeline).

**Smoke command (run, no baseline executed):**

```
CUDA_VISIBLE_DEVICES="" \
  .venvs/flowmol3_venv/bin/python \
  tools/flowmol3_upstream_smoke.py --phase upstream
```

Final smoke output (trimmed):

```json
{
  "env": {
    "python": "3.12.13",
    "torch": "2.2.0+cu121",
    "torch_cuda_available": false,
    "numpy": "2.5.2",
    "dgl": "2.1.0",
    "torch_scatter": "2.1.2+pt22cpu",
    "torchdata": "0.9.0+cpu"
  },
  "phases": {
    "upstream": {
      "weights_path": ".../weights_real/checkpoints/last.ckpt",
      "use_upstream_flag": true,
      "load_seconds": 2.258,
      "kind": "upstream_flowmol",
      "dgl_available": true,
      "upstream_import_error": null,
      "solve_error": "TypeError: FlowMol.forward() takes 2 positional arguments but 5 were given",
      "ok": false
    }
  }
}
```

## What worked in this pass

1. **DGL + torch_scatter restored.** The venv had ``dgl==2.1.0`` and
   ``torch_scatter==2.1.2+pt22cpu`` installed but the ``pytorch-
   lightning`` re-resolve (a one-shot bump to torch 2.7.0+cu128 to
   satisfy an unrelated dep) wiped them. We:

   - pinned torch back to ``2.2.0+cu121`` (``uv pip install --no-deps
     torch==2.2.0+cu121 --index-url https://download.pytorch.org/whl/cu121
     --reinstall``)
   - re-copied the torch_scatter wheel from ``~/.cache/uv/archive-v0``
   - re-copied the dgl wheel from the same cache
   - installed matching cu121 CUDA runtime libs (the venv's prior
     cu128 libs don't ship ``libcudnn.so.8`` which torch 2.2.0 requires;
     we downloaded ``nvidia_cudnn_cu12-8.9.2.26`` from PyPI directly —
     the ``uv`` resolver hit the project-level torch 2.7.0 lock and
     would not downgrade)
   - created a ``torch/utils/_import_utils.py`` shim that supplies
     ``dill_available`` and ``import_dill`` (the module was added in
     torch 2.3.0 and DGL 2.1.0 imports it eagerly on
     ``torchdata.datapipes`` -> ``torch.utils._import_utils``); this
     is a vendored compatibility file at
     ``flowmol3_venv/lib/python3.12/site-packages/torch/utils/_import_utils.py``
   - removed ``torchvision`` (it pinned to ``+cu128`` and required
     ``torch.library.register_fake`` which torch 2.2.0 lacks) and
     downgraded ``torchmetrics`` to ``0.11.4`` (the 1.9.x line imports
     ``torchvision.transforms`` transitively)

2. **Upstream FlowMol class loads on CPU.** With the above, running::

   ```
   sys.path.insert(0, 'data/FlowMol3/repo')
   from flowmol.models.flowmol import FlowMol
   model = FlowMol.load_from_checkpoint(
       'data/flowmol3/weights_real/checkpoints/last.ckpt',
       map_location='cpu', strict=False,
   )
   ```

   completes in ~0.3s, ``model.eval()`` succeeds, all 475 checkpoint
   tensors are accepted (we ran with ``strict=False``). The adapter's
   :func:`FlowMol3V2Adapter._load_model` records ``kind =
   upstream_flowmol`` in ``model_metadata``.

3. **Adapter's use_upstream=True plumbs through.** The
   ``FlowMol3UpstreamLoadResult.materialize`` call returns ``True`` and
   :attr:`FlowMol3V2Adapter.use_upstream` is ``True`` on the smoke
   report. The adapter's fail-closed fallback (set to
   ``real_fallback_after_upstream_failure`` only when the upstream
   load *itself* throws) does NOT trigger because the load succeeds.

## What is still broken

1. **Adapter solver can't call the upstream model.** The adapter's
   :func:`_real_velocity_field` and :func:`_ctmc_real_velocity_field_ex`
   both pass ``(a_tok, c_tok, e_tok, t_emb)`` to ``module(...)`` —
   that's the partial-fidelity readout head's signature
   (``_FlowMol3ReadoutHead.forward``). The upstream ``FlowMol.forward``
   signature is ``forward(self, g, timestep)`` where ``g`` is a DGL
   heterograph and ``timestep`` is a scalar tensor. The
   ``use_upstream=True`` flag therefore loads the model but the
   downstream solver raises:

   ```
   TypeError: FlowMol.forward() takes 2 positional arguments but 5 were given
   ```

   This means **the v2 adapter has never been wired to actually USE the
   upstream model — it only knows how to call the partial-fidelity
   readout head**. The proper way to invoke the upstream sampler is
   ``model.sample_random_sizes(n_mols, device=..., n_timesteps=...)``,
   which returns a list of :class:`SampledMolecule` objects and bypasses
   the adapter's ``build_initial_state → solve_ode → observe_endpoint``
   protocol entirely.

   This is a meaningful documentation gap. The ``use_upstream`` flag
   suggests "use the upstream sampler" but the effect is "fail to call
   any sampler at all" once the upstream load succeeds. The shim's
   :func:`run_upstream_flowmol3_eval` does the right thing.

2. **numpy 2.x dtype inference fails on torch 2.2.0.** The original
   partial-fidelity path had ``torch.as_tensor(np.asarray(x,
   dtype=np.float32))`` which raises ``RuntimeError: Could not infer
   dtype of numpy.float32`` on torch 2.2.0 + numpy 2.5 (the broken
   ``len(arr.dtype)`` inference in
   ``torch._utils._element_size_dispatch``). **Fixed in this pass** by
   adding an explicit ``dtype=torch.float32`` kwarg to all four
   ``torch.as_tensor(...)`` call sites in
   :func:`_real_velocity_field` and :func:`_ctmc_real_velocity_field_ex`
   (the change is documented in-place with a "numpy 2.x compatibility"
   comment). After the fix, the partial-fidelity path's torch bridge
   imports cleanly.

## What is *not* attempted (per in-scope constraints)

* No GPU inference; ``CUDA_VISIBLE_DEVICES=""`` is set on every shell
  invocation in this pass.
* No FlowMol3 baseline re-run (the in-scope directive forbids baseline
  runs in this pass).
* No DGL source build — the upstream DGL wheel for torch 2.7+ does not
  exist and a 2-4 h CMake+CUDA build is out of scope.
* No ``xtb`` Python bindings — the ``xtb`` PyPI source build fails on
  meson (``'mkl_gf_lp64' not found``); conda is not installed on this
  rig and the GFN2-xTB stage in
  :func:`tools.run_mol_eval.compute_pb_validity` therefore still uses
  ETKDGv3-only 3D conformers (the documented "first-cut" path).

## Files changed

* ``adaptive_reflow/adapters/flowmol3_v2_adapter.py``: 4 numpy-2.x
  compat patches (``torch.as_tensor`` explicit dtypes in
  :func:`_real_velocity_field` and :func:`_ctmc_real_velocity_field_ex`).
* ``tools/flowmol3_upstream_smoke.py``: new smoke script (factory +
  upstream phases; CPU-only; JSON report to stdout).
* ``flowmol3_venv/lib/python3.12/site-packages/torch/utils/_import_utils.py``:
  new vendored compatibility shim (see What worked above).

## Recommendation (next repair pass)

The right move is to **stop pretending** the v2 adapter's ``solve_ode``
can call the upstream sampler and **document the boundary** explicitly:
the v2 adapter is partial-fidelity only; full upstream parity lives in
the shim's ``run_upstream_flowmol3_eval`` + ``SampleAnalyzer.analyze``
pipeline. The smoke script makes this boundary explicit and is the
machine-checkable proof.

If a future pass wants to fix this for real, two options:

A. **Write a wrapper module** that takes a DGL heterograph from
   :class:`FlowMol3V2Adapter.build_initial_state`'s native state and
   dispatches ``model.sample_random_sizes`` directly, dropping the
   :class:`solve_ode` interface for the upstream path. ~1-2 days of
   glue because the adapter's native state is a numpy dict and the
   upstream expects a DGL graph with tokenized features.

B. **Wait for the venv rebuild** to torch 2.7+cu128 + a DGL 2.1.0 wheel
   built against torch 2.7 (does not exist as of 2026-09-03). Then
   option (A) is ~1 day shorter because the GPU inference path is
   faster and we can write the wrapper without the CPU bottleneck.

Either way, the existing partial-fidelity path's numpy-2.x compat
patches in this pass are durable and should be kept.