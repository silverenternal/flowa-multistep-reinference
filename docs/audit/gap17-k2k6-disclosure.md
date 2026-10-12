# GAP-17-K2K6 — env-blocked / deferred K-level cells: pin-env vs honest-disclosure

**Date:** 2026-10-13
**Author:** GAP-17 K2/K6 agent (USER AUTHORIZED, NO PUSH)
**Scope:** Resolve `todo.json` GAP-17-K2K6 ("K2/K6 env-blocked per-cell sweeps
(pin env or retain honest disclosure)") by (a) pinning down exactly which
K-level cells the label refers to, (b) testing whether either can be
*pinned + run* within the hard guardrails, and (c) recording the honest
disposition.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

The label "K2/K6" in `todo.json` is **ambiguous** — two different K-numbering
schemes coexist in this repo (§9 limitation *dimensions* `K1`–`K8` vs the
supplementary K-*cells* `K1/K2/K3/K4/K5/K6/K7`). Resolving it:

| Cell | Meaning | Current status | Can it be "pinned + run"? |
|---|---|---|---|
| **K2** | CIFAR-10 v4 N=500 **provenance gap** | **CLOSED** (Wave 147 P3: source data archived to `docs/r4-survey/cifar_results_v4/`, byte-stable) | N/A — already resolved; nothing to pin |
| **K3** (adjacent) | CIFAR-10 v4 **cosine-ramp PROTOCOL_MISMATCH** | disclosed (Wave 146 P2) | N/A — a protocol *caveat*, not a runnable cell |
| **K6** | Wan2.2 **N=1000 sweep + 4-arm H2H** | **DEFERRED** (compute-priority) | **NO** — see §1.2 |

**The decisive new observation** is that the K6 disclosure classifies the
blocker as *compute-priority only*, but the **real Wan2.2 checkpoint is not
materialised on disk**: every `data/wan2_2/weights/**/diffusion_pytorch_model-*.safetensors`
file is a **135-byte git-LFS pointer stub** (e.g. `oid sha256:cb58f36d…`,
`size 9992481544`). The K6 blocker is therefore **environmental as well as
compute-side**. This does not change the K6 status (`DEFERRED` preserved
verbatim) but it corrects the *root-cause* attribution recorded in the frozen
disclosure surfaces — a correction this audit records at the management
surface only.

**Resolution:** GAP-17 is closed as **honest disclosure retained (accepted)**
per the gap's own acceptance criterion ("pin env **or** retain honest
disclosure"). Neither cell can be pinned-and-run without violating a hard
guardrail: K2 is already closed; K6's real ckpt is absent and pulling it
(`git lfs pull` ≈ 6 × ~10 GB shards) would rewrite working-tree bytes under
the vendored `data/**` tree (guardrail #1: vendored upstream must stay
byte-identical).

---

## 1. Observed facts (verified, not inferred)

### 1.1 K2 — CIFAR-10 v4 N=500 provenance gap is CLOSED

`docs/audit/engineering/followup.md:12` (Wave 147 Phase 3):

> Archived CIFAR v4 N=500 source data to `docs/r4-survey/cifar_results_v4/`
> (6 files: `comparison.md`, `invocation.json`, `per_round_metrics.csv`,
> `README.md`, `run.log`, `summary.json`). **This closes the Wave 146 Phase 2
> audit's K2 provenance gap** ("N=500 v4 source data NOT on disk; provenance is
> reconstructable from logs but not reproducible from data alone"). Establishes
> a single-source-of-truth for the Table 9 +24–31% headline (recomputed from
> on-disk CSVs; byte-stable across re-read).

So K2 is **not env-blocked and not open** — it was a *provenance* gap, now
closed. `tnnls_submission/submission_checklist.md:53` records it as
"[x] K2 (CIFAR-10 v4 N=500 cosine ramp PROTOCOL_MISMATCH): preserved
(Wave 146)" — i.e. the residual is a *disclosed protocol caveat*, not a
pending sweep.

Verify on disk:

```
$ ls docs/r4-survey/cifar_results_v4/
comparison.md  invocation.json  per_round_metrics.csv  README.md  run.log  summary.json
```

### 1.2 K6 — Wan2.2 checkpoint is an un-materialised git-LFS stub

The K6 disclosure (`docs/CLAIMS.md` `§k5-k6-camera-ready-scope`;
`docs/drafts/paper-A-final.md` §9.4.1 footnote) states the deferral is
**compute-priority**, not a missing ckpt / missing adapter:

> "the Wan2.2 vendor ckpt is git-vendored at `data/wan2_2/repo` … and the
> Wan2.2 upstream codebase is byte-identical to the pinned upstream commit
> hash — the deferral is **not** a missing-ckpt or missing-adapter blocker but
> a GPU-compute-priority blocker."

But the actual weights on disk are **LFS pointer stubs**:

```
$ ls -l data/wan2_2/weights/high_noise_model/
-rw-r--r-- 135 diffusion_pytorch_model-00001-of-00006.safetensors
-rw-r--r-- 135 diffusion_pytorch_model-00002-of-00006.safetensors
...
$ cat data/wan2_2/weights/high_noise_model/diffusion_pytorch_model-00001-of-00006.safetensors
version https://git-lfs.github.com/spec/v1
oid sha256:cb58f36df7e604c6e7b0df80a3f6f9b72c77695e581e19985fc3a0e6732ba1e2
size 9992481544
$ du -sh data/wan2_2/weights/    # 1.8M total, i.e. pointers only
1.8M    data/wan2_2/weights/
```

6 shards × ~10 GB ≈ 60 GB for the high-noise model alone (plus the low-noise
model + VAE + T5). The harness `tools/run_sota_wan2_2_video_experiment.py` is a
**STUB** whose own docstring lists the blockers (weights, VAE, text encoder,
`flash-attn`, ≥40 GB VRAM). The verify record
`verification_outputs/wan2_2_verify.txt` step H confirms the mechanism:

> "step H (explicit construct) hangs because T5+DiT+VAE construction reads LFS
> stub files (135-byte pointers). This is the documented blocker — the upstream
> import itself works (proven by step A + step C geometry probe)."

⇒ K6's blocker is **env (un-materialised ckpt) + compute (multi-week sweep)**,
not compute alone. The framework-side is proven wired (`wan2_2_verify.txt`:
synthetic smoke OK, `18 passed` in `tests/test_adapters/test_wan2_2_video.py`).

### 1.3 Why the env cannot be "pinned" within the guardrails

- Pulling the real ckpt (`git lfs pull` inside `data/wan2_2/weights/`) would
  replace the committed pointer blobs in the **working tree** with ~60 GB of
  binary content under the vendored `data/**` tree. Guardrail #1 requires
  vendored upstream to stay byte-identical to the pinned upstream commit; the
  commit object would be unchanged, but every md5/byte check over `data/**`
  (the standing verification step before commit) would flip. This is exactly
  the class of change the guardrail forbids without an explicit user gate.
- Even with the ckpt present, the K6 sweep is a **multi-week GPU** budget
  (N=1000 × 4 arms × NFE∈{50,100} × {pLDDT, scPerplexity} + TOST/JT/BF01/meta/NI),
  which cannot fit this session on the single available GPU (cuda:0, already
  committed to the GAP-01 R6 live sweep).

---

## 2. Interpretation

- **K2:** closed provenance gap; the residual is a disclosed protocol caveat.
  Nothing to pin or run. Retained as-is.
- **K6:** genuinely env-blocked **and** compute-blocked. The honest disclosure
  is the correct and only in-scope disposition. The *root-cause* recorded in
  the frozen surfaces ("compute-priority") is **incomplete** — this audit adds
  the env-side observation. Per the additive rule, the frozen surfaces are
  **not** edited (that would be a wording change not backed by a new
  measurement); the correction lives here and in `todo.json`.
- **K5 (FreqFlow + MM-FM):** the sibling ENV_BLOCKED cell — its `nnet_ema.pth`
  does not exist publicly (verified Wave 189 P3 / CLM-056), so it is
  un-pinnable by construction. Already disclosed; out of scope for a "pin env"
  attempt.

---

## 3. Resolution

`todo.json` GAP-17-K2K6 → **RESOLVED (honest disclosure retained)**:

1. **K2** — closed provenance gap (Wave 147 P3); residual protocol caveat
   disclosed (Wave 146 P2). No action.
2. **K6** — `DEFERRED` retained verbatim (no status promotion); blocker
   re-attributed in this audit as **env (un-materialised LFS ckpt) + compute**.
3. **K5** — `ENV_BLOCKED` retained verbatim (un-pinnable: no public ckpt).
4. No frozen surface edited; no number changed; no status promoted.

---

## 4. Files / surfaces referenced

- `todo.json` — GAP-17-K2K6 status → RESOLVED (management surface only).
- `docs/audit/engineering/followup.md` (K2 closure, Wave 147 P3).
- `docs/audit/wave357-k5-k6-camera-ready.md` (K5/K6 disclosure).
- `docs/CLAIMS.md` `§k5-k6-camera-ready-scope` (frozen; read-only).
- `docs/drafts/paper-A-final.md` §9.4.1 footnote (frozen; read-only).
- `tnnls_submission/submission_checklist.md` rows 17/18/19/20 (frozen; read-only).
- `data/wan2_2/weights/**/*.safetensors` (LFS pointer stubs; read-only).
- `tools/run_sota_wan2_2_video_experiment.py` (STUB harness).
- `verification_outputs/wan2_2_verify.txt` (step H LFS-stub evidence).
- this audit doc.
