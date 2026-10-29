# Portable paths — the code assumed it lived in `/home/hugo`

**Date:** 2026-10-29
**Scope:** `adaptive_reflow/`, `tools/`, `scripts/`, `reproduce/`, `tests/`.
**Status:** closed for the repository-root class. No metric, claim, status
label, or verdict changed; no GPU was used; no behaviour changed on this box.

---

## 1. The defect

The repository root was pinned as a literal string in 94 lines:

```python
REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, "/home/hugo/codes/flowa-multistep-reinference")
```

On this machine that is exactly right, so every gate stayed green. On a
reviewer's clone every one of those lines points at a directory that does not
exist — and the failure is silent, because a `Path` that names nothing is a
valid `Path`. The adapters then fall back to synthetic behaviour rather than
raising.

This matters more than a cosmetic lint: the paper's reproducibility claim is
that a reviewer can re-run the cells. A clone that silently degrades is worse
than one that errors.

## 2. What changed

**94 root literals → `Path(__file__).resolve().parents[N]`.** The depth is
per-file (`tools/x.py` → 1, `tools/audit_thm5/x.py` → 2,
`adaptive_reflow/adapters/x.py` → 2) and was verified mechanically: for all 80
rewritten modules, `Path(file).resolve().parents[N]` equals the repository
root. The 13 `sys.path.insert` calls were rewritten the same way.

**17 library-level path defaults.** `FLOWMOL3_UPSTREAM_REPO`,
`FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR` (twice), `WAN22_REPO_PATH`,
`WAN_UPSTREAM_REPO`, `HIDREAM_UPSTREAM_REPO`, `PROTBFN_UPSTREAM_REPO`,
`PROTBFN_UPSTREAM_DEFAULT_WEIGHTS_ROOT`, `LUMINA_UPSTREAM_REPO`,
`DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH`, the RDKit NCI fallback, and the
`__main__` smoke path in `flowmol3_eq4_fg_deviation.py` now resolve from
`_REPO_ROOT = Path(__file__).resolve().parents[2]`.

Because `_REPO_ROOT` resolves to the same directory here, **every constant
evaluates to the identical string it did before** — verified by importing
`flowmol3_upstream_shim`, `flowmol3_metrics_upstream` and `fg_deviation` and
printing the values:

```
/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo
/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom
/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized
/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/references/geom_drugs_train.smi
```

## 3. Measured

| | before | after |
|---|---:|---:|
| lines mentioning `/home/hugo` | 181 | 76 |
| lines pinning the repository root | 94 | **0** |
| library (`adaptive_reflow/`) hardcoded paths | 17 | 1 |

## 4. What still mentions an absolute path, and why

The 76 remaining lines fall into three classes, none of which can be made
repo-relative:

1. **A venv outside the repository.** `DEFAULT_SIDECAR_VENV =
   "/home/hugo/.venv-flowmol311"` — a Python 3.11 environment built for the
   FlowMol3 sidecar because `dgl` has no 3.12 wheel. Its own docstring already
   documents the `FLOWMOL3_SIDECAR_VENV` override, so the literal is a
   documented fallback, not a hidden assumption.
2. **External data and tool prefixes.** `/home/hugo/xtb_prefix/bin/xtb`,
   `/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz`,
   `/home/hugo/.conda/envs/omegafold_py310/bin/python`. These name artefacts
   that never live in the repository; they are inputs, and the code already
   accepts overrides for most of them.
3. **Docstrings** quoting an example path.

## 5. The gate

`tests/test_portability.py` — two tests:

- no line in `adaptive_reflow/`, `tools/`, `scripts/`, `reproduce/`, `tests/`
  contains the repository-root literal;
- the library's `flowmol3` path defaults are absolute and resolve inside the
  repository, so a future refactor cannot quietly move them out.

The first test fails on the *next* line anyone writes as
`"/home/hugo/codes/flowa-multistep-reinference"`, which is the whole point.

## 6. Deliberately not done

- **The 76 remaining absolute paths were left alone** — see §4; each is an
  external input with an override, and rewriting them would change runtime
  behaviour rather than make it portable.
- **`docs/` was not swept.** Its absolute paths are historical records inside
  audit documents; §7.1 of `docs/audit/doc-link-audit.md` covers the
  backticked-path class separately.
- **No adapter semantics changed.** Every constant evaluates to the same
  string as before on this machine; the suite is the evidence (§7).

## 7. Gates

| Gate | Result |
|---|---|
| `pytest tests/test_portability.py` | 2 passed |
| full `pytest` (CPU, `test_paper_metrics` excluded) | 5540 passed / 180 skipped / 12 xfailed |
| `ruff check adaptive_reflow/ tests/ scripts/ tools/` | 0 findings |
| `python -m py_compile` on every changed file | clean |
| 12-entry `todo.json` gate chain | all rc=0 |
