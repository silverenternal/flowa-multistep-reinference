# Algorithm improvement — F.5: env_hash infrastructure

**Status:** done (Wave 15 P1 — commit 43b862d; F.5 LIVE: env_hash.txt + scripts/capture_env_hash.py + requirements-lock.txt + docs/adapter-dependencies.md) (+ Wave 38: host_fingerprint module added to api_churn_report + capture_env_hash + 5 other call sites; Wave 41: KanziAdapter @implements + LineageFlow upstream numerical forward verified via env_hash-locked venv)
**Date:** 2026-09-05
**Priority:** high (HARD gate per framework-internal-metrics rev 2 §1 F.5;
blocks Phase 2 entry gate, Phase 4 gate, and paper-writeup gate)
**Depends on:** none (but resolves uv.lock drift discovered in Wave 14 baseline)
**Owner:** framework maintainer
**Goal:** ship `scripts/capture_env_hash.py` + `requirements-lock.txt` +
`env_hash.txt` + per-adapter dep list; ensure every reproduction can be
cold-clone verified.

## Background

Framework-internal-metrics rev 2 §1 F.5:
> env_hash = SHA256( requirements-lock.txt + python --version +
> torch.__version__ + torch.version.cuda + adapter-specific dependency
> versions ); NOT full pip freeze.

Rev 2 §6 baseline audit found (all MISSING):
- `scripts/capture_env_hash.py`
- `requirements-lock.txt` (uv.lock exists but framework lacks own venv)
- `env_hash.txt`
- per-adapter dep list

**uv.lock drift discovered**: `uv.lock` pins `torch==2.14.0`; only
`cpg/.venv` has `torch==2.13.0+cu130`. Framework lacks its own
uv-managed venv, which is why several env-dependent tests fail to even
collect.

## What to do

1. **Provision framework's own uv-managed venv** (`.venv/`) to fix uv.lock drift
   - `uv sync` to install per uv.lock
   - Verify `python -c "import torch; print(torch.__version__, torch.version.cuda)"`
     matches uv.lock
2. **Generate `requirements-lock.txt`**
   - `uv pip freeze --strict | grep -v '^#' | sort > requirements-lock.txt`
   - Commit as new file
3. **Author `scripts/capture_env_hash.py`** per F.5 spec:
   ```python
   def capture_env_hash() -> dict[str, str]:
       # Returns: {lock_hash, python_version, torch_version, cuda_version,
       #           adapter_deps}
       # Plus: write env_hash.txt containing all 5 fields + their hashes
   ```
4. **Capture initial `env_hash.txt`** + commit
5. **Document adapter-specific dependency lists** (`docs/adapter-dependencies.md`)
6. **Wire into CI**: `.github/workflows/cpu-tests.yml` runs
   `scripts/capture_env_hash.py --verify` against the committed
   `env_hash.txt` and fails if drifted
7. **Wire into Phase 4 comparison**: every `comparison.md` must include
   `env_hash.txt` capture + hash

## Files affected

- `requirements-lock.txt` (NEW)
- `env_hash.txt` (NEW)
- `scripts/capture_env_hash.py` (NEW)
- `docs/adapter-dependencies.md` (NEW)
- `.venv/` (NEW; framework venv; gitignored)
- `.github/workflows/cpu-tests.yml` (UPDATE; env_hash verify)
- `mkdocs.yml` (UPDATE; add scripts to nav)

## Acceptance

- [ ] Framework venv provisioned; torch version matches uv.lock
- [ ] `requirements-lock.txt` committed
- [ ] `scripts/capture_env_hash.py` exists, exits 0, produces `env_hash.txt`
      deterministically
- [ ] `env_hash.txt` committed (initial capture)
- [ ] CI runs capture_env_hash.py --verify on every PR
- [ ] `docs/adapter-dependencies.md` lists each adapter's deps
- [ ] `docs/baseline-audit-report.md` §F.5 updated to "MET" (all artifacts present)
- [ ] `pytest --collect-only -q` still works in the new framework venv

## Estimated time

30-60 min (no GPU; uv + script + CI wire-up).

## Acceptance gate

**Gate name:** `G-F5-ENV-HASH` (new; defined here)

**Pre-condition:** uv installed + `uv.lock` exists
**Pass conditions:**
- [ ] All acceptance checklist items above
- [ ] CI integration verified (1 successful CI run with the verify job)
- [ ] `docs/baseline-audit-report.md` §F.5 updated to "MET"

## Out of scope

- Per-model integration work (Phase 3 onwards) — separate task
- Algorithm improvement B (rate bound theorem) — separate task

## Wave 56 close-out

Status line updated: F.5 env_hash infrastructure is now consumed by the host_fingerprint module (Wave 38 Agent A WF3) and used to lock Kanzi/LineageFlow sidecar venvs (Wave 39 Agent A, Wave 41 Agent B). F.5 remains the canonical "environment state" gate; all later per-model real-ckpt verifications depend on it. Last touched commit: `811ca75` (Wave 55 Agent C: Author todo/INDEX.md master entry point).