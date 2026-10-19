# GAP-52 — Channel-faithful restart blend: run record

**Status:** COMPLETE — dev screen returned **no survivor**; the pre-registered
rule stops before the confirmatory block.
**Pre-registration:** `docs/audit/gap52-charge-channel-preregistration.md`
**Analysis tool:** `tools/gap52_dev_analysis.py`
**Parent:** `docs/audit/gap43-blend-positive-run.md`
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Value |
|---|---|
| Cell | R3, FlowMol3 `fg_dev` (primary), `pb_validity_pct` (secondary) |
| Defect 1 | charge is categorical upstream, continuous in the blend → std 1.000→0.707, P(neutral) 38.3 %→52.0 % at m=0.5 |
| Defect 2 | one scalar m for coordinate / charge / pair despite per-channel policy support |
| Arms | C0 (continuous, flat), C1 (categorical, flat), C2 (categorical, per-channel), C3 (continuous, per-channel) |
| Dev seeds | 1000…1090 (10, fresh) |
| Confirm seeds | 2000…2490 (50, fresh) — **not run** |
| Dev winner | **none** (`survivors = []`) |
| Verdict | **DEV-SCREEN NULL** — no arm beats the as-wired C0 |

---

## 1. Prerequisites

### 1.1 Byte stability of the default path

`charge_blend_mode` defaults to `"continuous"`, and the restart digest only
gains a `charge_mode` field when the mode is not the default. Evidence:

| Gate | Result |
|---|---|
| `pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` | **72 passed** |
| `pytest tests/test_gap52_charge_blend.py -q` | **8 passed** |
| `pytest tests/test_gap52_dev_analysis.py -q` | **3 passed** |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| `python3 tools/check_claims_consistency.py` | exit 0 |
| `mkdocs build --strict` | exit 0 |

### 1.2 Smoke (plumbing only)

`N=100`, seed 1000, arm C2 (`categorical`, `m = (0.25, 0.75, 0.75)`),
`cuda:0`, `.venvs/flowmol3_venv`.

| Check | Result |
|---|---|
| exit code | 0 |
| `n_sampled` | 100 / 100 |
| `charge_blend_mode` recorded | `categorical` |
| `restart_memory_by_channel` recorded | `{coordinate: 0.25, charge: 0.75, raw_pair: 0.75}` |
| `shared_prior` / `real_restart_blend` | `true` / `true` |
| `fg_dev` baseline / framework | 0.6387 / 0.4907 (Δ = −0.1479) |
| `pb_validity_pct` baseline / framework | 0.14 / 0.12 |

**Reading caveat.** N=100 is a plumbing check, not an effect estimate:
`fg_dev` is strongly N-dependent, and `pb_validity` at N=100 moves in
~1/100 steps. The smoke only proves the flags reach the blend.

Artifacts: `verification_outputs/gap52-charge-channel/_smoke/`.

### 1.3 Launch metadata

`nvidia_smi_at_launch.txt` and `dev_start.txt` are written next to the
`dev/` tree. Each arm also gets a `run_metadata.json` from
`tools/gap43_run_metadata.py` (git SHA, command, versions, checkpoint md5,
PoseBusters YAML sha256, GPU name/driver, start/end UTC).

---

## 2. Commands (as run)

```bash
# dev screen — 4 arms x 10 seeds x N=200, NFE=250, shared prior
/tmp/run_gap52_dev.sh
```

Per arm:

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH="$PWD" .venvs/flowmol3_venv/bin/python \
  scripts/wave338_p5_r3_n1000_paired.py \
  --n-total 200 --nfe 250 --nfe-batch 100 \
  --seeds 1000 1010 ... 1090 \
  --shared-prior --real-restart-blend \
  [--charge-blend-mode {continuous,categorical}] \
  [--restart-memory-fraction-coordinate 0.25 \
   --restart-memory-fraction-charge 0.75 \
   --restart-memory-fraction-pair 0.75] \
  --device cuda:0 --output-dir verification_outputs/gap52-charge-channel/dev/<arm>
```

---

## 3. Dev-screen results

10 seeds × N=200, NFE=250, shared prior. Δ = framework − baseline
(negative favours the framework). Reference = C0, the GAP-43 as-wired arm.

| arm | charge mode | `(m_x, m_c, m_pair)` | mean Δ `fg_dev` | SD | t(9) | p | `d_z` | `d_z` 95 % CI | mean Δ `pb_validity` |
|---|---|---|---:|---:|---:|---:|---:|---|---:|
| **C0** | continuous | (0.5, 0.5, 0.5) | **−0.02988** | 0.06874 | −1.375 | 0.203 | −0.435 | [−1.170, +0.168] | +0.2880 |
| C1 | categorical | (0.5, 0.5, 0.5) | −0.01077 | 0.05552 | −0.613 | 0.555 | −0.194 | [−1.159, +0.425] | +0.2885 |
| C2 | categorical | (0.25, 0.75, 0.75) | +0.00787 | 0.09305 | +0.267 | 0.795 | +0.085 | [−0.581, +1.035] | +0.3573 |
| C3 | continuous | (0.25, 0.75, 0.75) | +0.00201 | 0.09526 | +0.067 | 0.948 | +0.021 | [−0.669, +0.866] | +0.3413 |

Per-seed `fg_dev` deltas:

| arm | seed 1000 → 1090 |
|---|---|
| C0 | −0.063, −0.035, −0.176, −0.022, +0.034, −0.025, +0.061, −0.077, −0.039, +0.043 |
| C1 | −0.053, −0.052, −0.086, −0.026, +0.093, +0.024, +0.047, −0.061, +0.006, 0.000 |
| C2 | −0.130, +0.069, −0.116, −0.070, +0.070, +0.039, +0.125, −0.065, +0.077, +0.080 |
| C3 | −0.144, +0.046, −0.118, −0.085, +0.051, +0.028, +0.101, −0.093, +0.088, +0.106 |

**Selection rule (§4):** reference mean = −0.02988. No arm has a lower mean,
so `survivors = []`, `winner = None`, `proceed_to_confirm = false`.

**Determinism check.** The baseline arm is bit-identical across all four
arm directories for every shared seed (same `--shared-prior` key), which
confirms the four comparisons use the same reference draws.

---

## 4. Confirmatory results

**Not run.** §4 of the pre-registration says: if no arm beats C0, stop and
record a null. Running the 50-seed block anyway would be a post-hoc
extension, so it was not started. The GAP-43 50-seed result therefore stands
as the as-wired evidence.

---

## 5. Interpretation

**H1 (charge fix) — rejected.** C1 differs from C0 only in the charge
channel (the e/a/x draws are bit-identical, pinned by a CPU test). Its mean
`fg_dev` delta is **+0.019 worse** than C0 (n.s.). Preserving the charge
class marginal does not help `fg_dev`; if anything it is slightly harmful.
The neutral-charge bias was real, but it was not load-bearing for the metric.

**H2 (per-channel m) — rejected.** C3 isolates the memory-fraction change
(m_x 0.5→0.25, m_c/m_pair 0.5→0.75) with the continuous charge. Its mean is
**+0.032 worse** than C0 (n.s.). Giving coordinates more exploration and
discrete channels more conservation does not improve the geometry metric.

**Interaction — no.** C2 (both changes) is the worst arm (+0.008, i.e.
slightly framework-worse). The two changes do not combine to a win.

**K1 `pb_validity` is robust to both changes.** The as-wired arm wins by
+0.288; the charge fix leaves it at +0.289; per-channel m raises it to
+0.357 (C2) / +0.341 (C3). So the GAP-43 K1 result is **not** an artifact of
the charge representation — the as-wired arm is, if anything, conservative
on K1. This is a consistency check, not a new claim (10 seeds, n.s.).

**Net.** The as-wired blend is not suffering a correctable
representation-level defect on `fg_dev`. The GAP-43 `INCONCLUSIVE` is an
effect-size limit, not a bug that a few lines can flip. For FlowMol3 R3 the
"dormant lever" programme is now closed: the faithful all-channel blend was
already the best of the four mechanism variants tested.

---

## 6. Unresolved / noted

- The per-arm JSON filenames still say `n1000` even at `N=200`; the true
  sample size is in `n_total_per_arm` in the sweep JSON. Cosmetic only.
- `raw_pair` also carries the atom-type channel `a`, so the `pair` memory
  fraction controls two channels. This is a pre-existing adapter limitation
  and is unchanged by GAP-52.
- The dev screen is N=200. All four arms have `|d_z| < 0.5` and every p is
  > 0.2, so "no survivor" is a **non-significant ranking**, not a proof of
  equivalence. The pre-registered rule is nonetheless decisive for stopping.
- The C0 dev mean (−0.030) is consistent in sign and magnitude with the
  GAP-43 50-seed N=1000 mean (−0.019), which is a reassuring regime check.
- `pb_validity` under per-channel m (+0.34 to +0.36) is exploratory and
  n.s. at 10 seeds; it is not promoted and no confirmatory run was done.
