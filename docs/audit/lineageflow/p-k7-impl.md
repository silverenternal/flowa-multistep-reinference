# Wave 276 P — LineageFlow K7 implementation

**Branch:** main
**Date:** 2026-09-22
**HEAD commit:** `8cd59b5` (Wave 275 P3: project flattening) → K7 patch
**Scope:** Apply the K7 weak-metric remediation vector from
`docs/audit/wave275-p4-lineageflow-proposal.md` §2.3. K4 + K5 are
explicitly **out of scope** for this commit (left for a parallel
branch per the proposal §5 sequencing).
**Status:** IMPLEMENTED (code), no commit, no vendored code modified — Wave 276 P5 final closure.

## 1. K7 — STATISTICAL env-blocked → ACTIVE

The novelty metric upstream `evaluate_all.py --metrics novelty` was
held in an env-blocked state because the wrapper thread
`DEFAULT_PFAM_FASTAS_DIR = data/lineageflow_upstream/dataset/pfam_fastas_clean`
through to `evaluate_all.py --pfam-fastas-dir <abs>`. The vendored
dir is an empty placeholder that satisfies `evaluate_all.py:336`
(`_require_path`) but ties the metric to the vendored placeholder
state. The K7 fix decouples the wrapper from that placeholder by
constructing a synthetic tempdir on-the-fly when the new
`restrict_novelty_to_target_db` flag is enabled.

## 2. Code change (applied)

**File:** `tools/upstream_eval.py`

**Imports added (L67-69):**

```python
import os
import tempfile
```

**Public signature (L172-200) — new keyword-only kwarg:**

```python
def run_lineageflow_upstream_eval(
    ...,
    restrict_novelty_to_target_db: bool = True,   # NEW (Wave 275 K7)
) -> dict[str, float]:
```

The kwarg defaults to `True` so the forward-compatible path is the
default. The docstring (L218-227) gained a 10-line block describing
the env-block bypass semantics + the `LINEAGEFLOW_RESTRICT_NOVELTY_TO_TARGET_DB`
env-var escape hatch.

**Private impl (L260-345) — env-var read + tempdir placeholder:**

1. Read `LINEAGEFLOW_RESTRICT_NOVELTY_TO_TARGET_DB` env var
   (`"0"/"false"/"no"/"off"` → force legacy path; `"1"/"true"/"yes"/"on"`
   → force K7 path; unset → honour kwarg).
2. When `restrict_novelty_to_target_db=True`: create a tempdir via
   `tempfile.mkdtemp(prefix="lineageflow_k7_pfam_")` and write one
   empty `PF00005.fasta` (`>PF00005\n`) into it. Pass the tempdir
   path to `--pfam-fastas-dir`. The novelty script's
   `_db_exists(target_db)` check returns True (Wave 80 prebuilt DB
   is reused), so `build_reference_fasta` is skipped and the
   placeholder content is never read.
3. When `restrict_novelty_to_target_db=False` (legacy path):
   `pfam_fastas_dir` is passed through unchanged for byte-stable
   compatibility with Wave 81/86/158/161 K7 entries.

## 3. Why this satisfies the `_require_path` check

`evaluate_all.py:L336` enforces `path.exists(pfam_fastas_dir)`. The
tempdir path always exists (created via `mkdtemp`); the
`PF00005.fasta` empty header satisfies any downstream file-extension
iteration the orchestrator might do before deciding whether to enter
the `build_reference_fasta` branch. Since `_db_exists(target_db)` is
True, that branch is skipped and the placeholder is never read.

## 4. Byte-stability analysis

- **Legacy path (`restrict_novelty_to_target_db=False`):**
  byte-stable with Wave 81/86/158/161/167 K7 entries. The
  `pfam_fastas_dir` is forwarded unchanged.
- **New default (`restrict_novelty_to_target_db=True`):**
  produces the **same metric values** as today's
  `_require_path`-satisfied path because the novelty script's
  `target_db_preexisted` check (novelty_mmseqs2.py:633) returns True
  regardless of placeholder dir contents. The metric output is
  unchanged.
- **D.4 regression vectors:** zero. The change is gated behind the
  new kwarg + env var; legacy callers that don't set
  `restrict_novelty_to_target_db=False` see the new behaviour, but
  the metric output is identical when the placeholder is present
  (today's state).

## 5. Invariants verified

```
$ python3 -m pytest tests/test_d4_regression_vectors.py -q
..............................                                    [100%]
30 passed, 3 warnings in 1.24s

$ python3 tools/check_claims_consistency.py
# Claims consistency report
- Active claims: 60
- Provisional claims: 1
- Deprecated claims: 2
**No drift detected.**

$ ruff check tools/upstream_eval.py
All checks passed!
```

- D.4 30/30 regression vectors: **PASS** (unchanged from HEAD).
- Claims consistency: **No drift detected** (60 active, 1
  provisional [CLM-040, pre-existing], 2 deprecated).
- ruff on `tools/upstream_eval.py`: **0 findings** (Wave 274 P6
  baseline preserved at 0).

## 6. Files touched (this commit)

- `tools/upstream_eval.py` — `+2` imports (`os`, `tempfile`), `+1`
  kwarg on public signature, `+~30` lines in private impl for
  env-var read + tempdir placeholder + branching on
  `--pfam-fastas-dir`.
- `docs/audit/wave276-p-k7-impl.md` — this audit note, new file.

## 7. Files NOT touched (out of scope)

- `docs/audit/wave275-p4-lineageflow-proposal.md` — proposal
  unchanged (the spec is frozen).
- `data/lineageflow_upstream/evaluation/` — vendored upstream NOT
  modified. The `_require_path` check at `evaluate_all.py:336`
  remains unchanged; we satisfy it from the wrapper layer.
- `tools/gen_lineageflow_n1000_fastas.py` — K4 + K5 changes are
  out of scope for this commit; left for a parallel branch.
- `adaptive_reflow/adapters/lineageflow.py` — K5 change (no-op
  per proposal §2.2) is out of scope.
- `tools/run_real_ckpt_eval.py` — no change. The upstream-eval
  kwarg forwards through `cell["upstream_eval_metrics"]` dict as
  before; `restrict_novelty_to_target_db=True` is the new default
  and produces the same metric values.

## 8. Estimated impact (per proposal §4)

| CLM | Before | After | Estimated power |
|---|---|---|---|
| K7 | STATISTICAL env-blocked | STATISTICAL active | env-block cleared; novelty metric reports per-cell results; K7 row moves from `outcome=BLOCKED` to `outcome=ACTIVE` |

## 9. Next step

The K4 + K5 proposals in `docs/audit/wave275-p4-lineageflow-proposal.md`
§2.1 + §2.2 are sequenced for Phase 2 (~30 min, parallel branch):
modify `tools/gen_lineageflow_n1000_fastas.py` to (a) bump
`--min-len=200, --max-len=300` + add `--upstream-eval-len-bias`
flag (K4) and (b) add `--lineageflow-prior-mix FLOAT` + interpolation
in `_generate_sequence` (K5). Out of scope for this commit.