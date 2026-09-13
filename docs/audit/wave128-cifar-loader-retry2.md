# Wave 128 CIFAR loader retry 2

Using `.venvs/kanzi_venv` (torch 2.14.0+cu130, CUDA GPU0), the adapter now
constructs successfully from `data/rectified_flow_cifar10.pth`. The bundle's
EMA section contains metadata (`decay`, `num_updates`, `shadow_params`) rather
than a directly loadable mapping, so the loader safely selected the valid
`model` state dict. No sweep was run.

Evidence is in `verification_outputs/wave128_cifar_gpu_retry2/`; metadata
records the selection and successful construction.
