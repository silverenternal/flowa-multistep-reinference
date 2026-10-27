# The MNIST inference path on GPU — 60x, validated to float64 round-off

**Date:** 2026-10-27
**Author:** engineering pass (USER AUTHORIZED, NO PUSH)
**Scope:** the sampler behind every MNIST number in the paper (R5c, GAP-78,
GAP-84, GAP-90). No metric, protocol, checkpoint or seed changes.
**Frozen surfaces:** untouched.

---

## 0. Why this was done

The user's directive was blunt: *"能拿gpu加速的地方你为什么要拿cpu并发，这太慢了"*.
They were right, and the measurement says so. The MNIST velocity field is a
20-tensor UNet (width 16, 28x28, five convolutions). The canonical path
integrates it **one sample at a time in NumPy float64**, and one
`_unet_evaluate` call on a `(1, 784)` input costs **2.35 ms** on this host. A
single NFE=200 cell therefore needs:

```
1000 samples x 200 steps x 4 RK4 stages x 2.35 ms x 4 arms = 7,520 s = 2.1 h
```

GAP-84 recorded 95.7 min for exactly that cell, which matches the model. The
whole GAP-90 grid is **19 core-hours**, and the first attempt (20-way CPU
concurrency) was still going to take ~1.2 h of wall clock.

## 1. Where the time actually goes

Profiled at `B = 1000`, one forward pass (3.19 s under `cProfile`, 2.16 s clean):

| component | share | note |
|---|---:|---|
| `_conv2d_forward` (5 calls) | 52 % | `np.einsum("bcijxy,ocij->boxy", optimize=True)` over an `as_strided` window tensor |
| `_silu_forward` (4 calls) | 17 % | two `np.exp` passes over a `(B, C, 28, 28)` array |
| `_gn_forward` (4 calls) | 20 % | mean/var over `(group, H, W)` |
| `np.pad` | 6 % | manual zero padding per conv |

Two things were checked and **rejected** as levers:

* **Bigger batches on CPU.** Per-sample cost is flat-to-worse above `B = 8`
  (2,346 us at `B=1`; 873 us at `B=8`; 2,508 us at `B=1000`). The ceiling for
  any CPU batching change is **2.7x**, and it requires rewriting the sample
  loop for a two-thirds saving. Not worth the risk.
* **im2col + BLAS.** Measured against the einsum at `B=1000` on the `down1`
  conv: 140 ms vs 90 ms. The einsum already wins on the small-channel layers,
  and the memory traffic of the window materialisation dominates regardless.

The real problem is that a 13 MFLOP forward pass is being executed in a
Python-level loop. That is a GPU-shaped workload.

## 2. What was built

`adaptive_reflow/adapters/mnist_fm_torch.py` — a torch port of the velocity
field plus a batched RK4. It is a **backend, not a second model**: every op is
the direct counterpart of the NumPy op it replaces.

| NumPy | Torch |
|---|---|
| `_flatten_with_time` | `cat([x, t_plane], dim=1)` |
| `_conv2d_forward` | `F.conv2d(..., padding=1)` |
| `_gn_forward` | `F.group_norm(groups=8, eps=1e-5)` |
| `_silu_forward` | `F.silu` |
| `np.repeat(x, 2)` | `F.interpolate(scale_factor=2, mode="nearest")` |
| `_integrate_rk4` | `TorchMnistVelocity.integrate_rk4` |

Two **additive** adapter methods were needed, and neither changes an existing
code path:

* `MnistFmAdapter.apply_restart_value(prior_x0, state, policy)` — the same
  blend, the same digest, the same provenance; the prior arrives as an array
  instead of through `_native_states`. `apply_restart_distribution` now
  delegates to it after its lookup, so there is still exactly one
  implementation of the restart arithmetic.
* `MnistFmAdapter.observe_endpoint_value(x_final, state)` — registers an
  endpoint produced outside the NumPy integrator. Its digest payload uses
  `kind = "endpoint_value"` so it can never collide with a trajectory-derived
  endpoint.

The reason for both: `_native_states` is an **LRU of 128 entries**, sized for a
one-sample-at-a-time loop. A population-sized batch overflows it and the
prior lookups raise `KeyError: 'x0'` — which is exactly what the first attempt
did at N=1000 after passing at N=32. The batched path now holds priors in a
NumPy array and touches the LRU only for the entry it just wrote.

Driver: `scripts/wave191_p3_mnist_sweep.py --backend {numpy,torch}` with
`--torch-device` and `--torch-dtype`. Default is `numpy`, and the numpy branch
is byte-identical to the historical code (the old loop is preserved verbatim
under `else:`).

## 3. Parity

`tests/test_mnist_fm_torch_parity.py`, 3 tests, all pass:

| check | tolerance | observed |
|---|---|---|
| one forward, `t in {0, 0.37, 1}`, B=16 | 1e-12 | 4.0e-15 |
| 10 RK4 steps from a shared `x0` | 1e-12 | 8.9e-16 |
| `apply_restart_value` vs `apply_restart_distribution` | exact | `array_equal` True, same digest |

End-to-end, against a **recorded** cell
(`verification_outputs/gap84-mnist-frontier/production_nfe50_s42`, N=1000,
NFE=50, seed 42, all four arms):

| arm | recorded FID | torch FID | abs diff |
|---|---:|---:|---:|
| baseline | 9.96704448 | 9.96704460 | 1.2e-07 |
| cosine | 9.98531754 | 9.98531767 | 1.4e-07 |
| codimension_sheet | 9.90945258 | 9.90945271 | 1.3e-07 |
| evidence_driven | 9.91413310 | 9.91413323 | 1.3e-07 |

**26.75 s wall clock versus 26.78 min recorded — 60x — with a 1.3e-7 absolute
FID difference.** The per-sample arrays agree to 4e-14; the FID residual is the
Fréchet square-root amplifying that into the seventh decimal. It is seven
orders of magnitude below the 1.0 FID floor the frontier rule uses.

## 4. Measured throughput

| path | per forward, B=1000 | per sample |
|---|---:|---:|
| NumPy, B=1 (canonical) | 2,350 ms | 2,350 us |
| NumPy, B=1000 | 2,508 ms | 2,508 us |
| torch float64, cuda:0 | 24.1 ms | 24.1 us |
| torch float32, cuda:0 | 1.38 ms | 1.38 us |

`float32` is a further 17x and is **deliberately not the default**: the recorded
artifacts are float64, and a float32 cell is not comparable to them. The flag
exists for exploratory work only, and the CLI help says so.

A full NFE=200 arm (N=1000, 4 RK4 stages) takes **21.0 s** on `cuda:0` versus
~1,440 s in NumPy.

## 5. What this changes downstream

* **GAP-90** moved from ~19 core-hours to ~15 GPU-minutes. The grid was
  restarted on the torch backend; the aborted CPU attempt is preserved at
  `verification_outputs/gap90-optsteps-dose-cpu-partial/` (3 complete cells) and
  is not used for any number.
* **GAP-93** (beta dose, 9 runs at NFE=50) drops from ~3.6 core-hours to
  ~4 minutes.
* **GAP-95**'s MNIST-adjacent scans become free; the CIFAR cell is a separate
  path and is unaffected.

## 6. What this does not fix

* **The CIFAR path is still broken, and it is not a speed problem.** A
  diagnostic on `cifar10_rf.pth` at NFE=2 generated 2,000 samples with
  `sd = 0.098` and range `[-0.685, 0.611]` — a collapsed cloud, where real
  CIFAR in `[-1, 1]` has `sd` roughly three times that. FID on that population
  is 247.2 at N=200, 215.3 at N=500, 198.3 at N=1000 and 184.6 at N=2000. The
  number falls with N but nowhere near the published 2.21, so **the small-N
  covariance bias is not the whole story** — the samples themselves are wrong.
  This makes GAP-94's premise ("the checkpoint is at FID 447.9") imprecise: the
  checkpoint has not been shown to be the problem, and the generator has.
  Recorded in `docs/audit/gap94-standard-benchmark.md` as an amendment.
* **No non-MNIST adapter was touched.** The 60x is specific to the NumPy MNIST
  UNet. LineageFlow / Kanzi / FlowMol3 already run on their own torch stacks.
* **`_integrate_rk4` still stores the full trajectory** for the NumPy path. It
  is ~1.3 GB of writes per arm at NFE=200, but at 2.35 ms per forward it is
  under 1 % of the cost, so it was left alone rather than made a special case.

## 7. Reproduce

```bash
# parity
.venvs/flowmol3_venv/bin/python3 -m pytest tests/test_mnist_fm_torch_parity.py -q

# one recorded cell, torch backend (26.8 s)
.venvs/flowmol3_venv/bin/python3 scripts/wave191_p3_mnist_sweep.py \
  --ckpt data/mnist_fm/production.ckpt.npz --n-samples 1000 --seed 42 \
  --total-nfe 50 --n-rounds 4 --equal-total-nfe --beta-schedule equal_budget \
  --beta-framework 0.3 --restart-t0-mode memory --min-steps-per-round 1 \
  --mean-preserve --seed-keyed-prior --shared-prior \
  --output-dir /tmp/val_tc --backend torch --torch-device cuda:0 --quiet

# the whole GAP-90 grid
reproduce/gap84_mnist_frontier.sh --n-samples 1000 \
  --out verification_outputs/gap90-optsteps-dose --ckpts epochs2,w8e3 \
  --seeds 42,43,44 --nfes 4,5,10,25,50,100,200 --jobs 4 --longest-first \
  --backend torch --torch-device cuda:0
```
