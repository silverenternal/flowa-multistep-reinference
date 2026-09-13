# CIFAR FID performance audit

The active N=200 run (`run_sota_cifar_experiment.py --device cuda`) showed
~146% CPU utilization for 16 minutes while GPU0 had only ~2.1 GiB allocated.
Inspection confirms `_compute_fid_tfport_inline` constructs
`pytorch_fid.InceptionV3` without `.to(cuda)`, and `torch.from_numpy` batches
remain on CPU; the adapter inference itself uses GPU. Thus TF-port Inception
feature extraction is the bottleneck.

Moving the model and batches to `cuda:0` is technically feasible, but requires
threading a device argument through `_compute_fid` and ensuring the reference
and generated arrays use identical preprocessing. Risks are GPU memory
pressure (Inception plus UNet), CUDA kernel compatibility, and changed
floating-point FID values; it should be benchmarked as an opt-in path with
CPU fallback before production use. No task was modified or restarted here.
