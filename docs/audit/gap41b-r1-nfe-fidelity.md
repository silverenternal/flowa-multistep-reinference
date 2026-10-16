# GAP-41b — R1 NFE-fidelity: is the canonical `--nfe 10` the reason the levers look inert?

**Date:** 2026-10-16
**Author:** GAP-41b agent (USER AUTHORIZED, NO PUSH)
**Scope:** a fidelity audit of the *inference budget* used by the canonical R1
sweeps. Every dormant-lever rejection (GAP-38/39/40/40b/34/41) was measured at
the canonical R1 config `--nfe 10`. The upstream LineageFlow released config
uses a much larger inference budget (`steps_base=100` + `steps_final=50` ≈
**150 NFE**). If the canonical R1 budget should be ~150, then the lever
rejections may be an artifact of the low NFE, not evidence the levers are inert.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

| Item | Result |
|---|---|
| **The fidelity gap** | canonical R1 runs at `--nfe 10`; the upstream LineageFlow released config (`data/lineageflow_upstream/config/generation.json`) uses `steps_base=100` + `steps_final=50` ≈ **150 NFE** — a ~15× budget difference |
| **The three distinct "n"s** | statistical n = **3 seeds** (the STRONG bar); sample N = **1000** records/seed; inference budget NFE = **10** (ours) vs **~150** (upstream) |
| **Consequence for prior levers** | GAP-38/39/40/40b/34/41 were all evaluated at NFE=10 — a *shared confound* |
| **Premise test (this doc)** | N=200, seed 42, arms `{legacy, tier}`, NFE ∈ {10, 150}: does the budget move the R1 HMMER metric and/or the tier lever? |
| **Resumable generation** | `--start-index` added to `tools/gen_lineageflow_n1000_fastas.py` (additive, default 0 byte-stable) so the N=200 result can be extended to N=1000 without recomputing the first 200 records |
| Verdict | *(pending — filled once the premise run completes)* |

---

## 1. Motivation

The user directive: *"n=3 有什么用啊，本来推理预算动不动就是 100 或者 1000 这样的，
你看一下原任务原论文里他们的 n 是多少"* + *"以前你排除的那些杠杆可能也存在这样的
漏洞"*.

The observation is that the canonical R1 protocol fixes the inference budget at
`--nfe 10`, but the upstream SOTA reference uses ~150 Euler steps. If the budget
is a load-bearing axis, then a lever that is inert at NFE=10 may be active at
NFE=150 — and the entire "power-limited, not code-limited" conclusion (see
`docs/audit/gap41-r1-tier-aware-ncap.md` §4) would be a *config-limited* artifact.

## 2. The budget comparison (facts)

| axis | our canonical R1 (Wave 158/280) | upstream LineageFlow (ICML 2026) |
|---|---|---|
| inference budget | `--nfe 10` (per-record, split over `n_rounds=3`) | `steps_base=100` + `steps_final=50` = **150** Euler steps (code defaults 200+200) |
| samples N | 1000 | `num_samples=512` (batch) / `batch_size=64` |
| families | 4 (PF00005/00072/00183/02517, 250 each) | `max_families=64`, `runs_per_family_batch=16` |
| rounds | 3 | 3 |
| statistical n (seeds) | 3 (42/43/44) | single released-config eval |

Sources: `data/lineageflow_upstream/config/generation.json`,
`data/lineageflow_upstream/config/generation.md`,
`data/lineageflow_upstream/inference/inference.py:671` (the `steps_base` /
`steps_final` split), `data/lineageflow_upstream/README.md` (Quick Start).

**Note on the confound.** The canonical R1 framework arm applies a
`min(1.0, NFE_REF / nfe)` β-scale factor with `NFE_REF = 50`; at `nfe=10` the
factor saturates at 1.0, at `nfe=150` it is 1/3. So changing the budget changes
both the number of Euler steps *and* the restart-blend β. This is the canonical
driver's behaviour; the experiment holds it fixed and reports the combined
effect.

## 3. Design

**Premise test** (`/home/hugo/gap41b-nfe150/run_premise.sh`): N=200, seed 42,
gate-open config (`--n-rounds 3 --restart-min-nfe 5 --temperature 1.0`), arms
`{legacy, tier}`, NFE ∈ {10, 150}, canonical HMMER counter.

`tier` = `--tier-aware-n-cap 0.5 --tier-aware-baseline-metrics-jsonl <k6
foldability.jsonl>` (the GAP-41 strongest lever).

**Resumable generation.** `tools/gen_lineageflow_n1000_fastas.py` gains
`--start-index` (additive; default 0 = byte-stable): records `[0, start_index)`
are skipped (their RNG stream replayed so record `start_index` matches a
from-scratch run) and only `[start_index, n)` are written, appended. This lets
the N=200 result be extended to N=1000 without recomputing the first 200
records. Byte-exactness and default byte-stability are pinned by
`tests/test_tools/test_gen_lineageflow_n1000_fastas.py::test_gen_script_resume_is_byte_exact`.

## 4. Results

*(pending — filled once the premise run completes)*

## 5. Verdict

*(pending)*

## 6. Reproduce

```bash
bash /home/hugo/gap41b-nfe150/run_premise.sh              # N=200 seed 42, NFE {10,150}
# extend to N=1000 later (resumable):
N=1000 START=200 bash /home/hugo/gap41b-nfe150/run_premise.sh
```

Evidence: `verification_outputs/gap41b-r1-nfe-fidelity/`.
