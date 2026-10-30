# 41 absolute paths the portability gate could not see

**Date:** 2026-10-30
**Scope:** `tests/test_portability.py`; every `*.py` under
`adaptive_reflow/`, `tools/`, `scripts/`, `reproduce/`, `tests/`.
**Status:** closed. No metric, claim, status label, or verdict moved. No GPU
was used.

---

## 1. The gate that only checked one spelling

`tests/test_portability.py` exists because 93 lines once pinned the repository
root to `/home/hugo/codes/flowa-multistep-reinference`. Its check was:

```python
LITERAL = '"/home/hugo/codes/flowa-multistep-reinference"'
```

The trailing quote is the defect. A *bare* literal matched; a literal with a
suffix did not:

```
"/home/hugo/codes/flowa-multistep-reinference"                  <- caught
"/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo"  <- missed
```

41 lines in 22 files carried the prefixed form. Every one of them pointed at a
directory that exists on this box and would not exist on a reviewer's clone,
which is exactly the failure the test was written to prevent.

## 2. What the 41 were

| Class | Example | Fix |
|---|---|---|
| data path | `tools/convert_reos_pickle_to_npy.py:52` | `REPO_ROOT / "data" / "FlowMol3" / ...` |
| venv interpreter | `scripts/wave229_p3_core_adapter_paper_quantities.py:56` | `str(REPO_ROOT / ".venvs" / "lineageflow_venv" / "bin" / "python")` |
| evidence directory | `tools/gap41_tier_analysis.py:33` | `REPO_ROOT / "verification_outputs" / ...` |
| output destination | `scripts/wave209_p6_r5a_extended.py:25` | `REPO_ROOT / "verification_outputs" / ...` |
| docstring / comment | `tools/aggregate_wave186_p4.py:6` | repo-relative spelling in prose |

Each file gained at most one `REPO_ROOT = Path(__file__).resolve().parents[1]`
(the two test files reuse the constant they already had).

## 3. Behaviour is unchanged on this box

Every rewritten constant was re-imported and printed. All 17 resolve to the
byte-identical absolute path they had before:

```
tools.gap41_tier_analysis.TIER = /home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41-n1000
scripts.wave246_p4_subgroup_meta.META_CSV = .../verification_outputs/wave234-p5-meta-analysis.csv
tools.convert_reos_pickle_to_npy.DEFAULT_PKL = .../data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl
```

## 4. The gate now matches the prefix

```python
REPO_LITERAL = "/home/hugo/codes/flowa-multistep-reinference"
```

The test's docstring records why the first spelling missed the suffixed form,
so the next person to touch it does not reintroduce the quote.

## 5. What is deliberately still absolute

31 lines still name `/home/hugo/...` and should. They point at software
installed on this host, not at this checkout:

```
/home/hugo/xtb_prefix/bin/xtb          (xtb binary, env-var overridable)
/home/hugo/.venv-flowmol311            (the FlowMol3 py3.11 sidecar)
/home/hugo/data/synthetic_image_v1/... (external Inception reference stats)
/home/hugo/.conda/envs/omegafold_py310 (OmegaFold interpreter)
/home/hugo/hmmer_build/bin/hmmscan     (HMMER build)
/home/hugo/bin/mmseqs                  (MMseqs2 build)
/home/hugo/.local/bin/pytest           (host pytest)
```

Each already has either an env-var override or an `is_file()` guard, and each
is a toolchain fact rather than a repo-root assumption. A gate that forbade
them would have to be waived on the next line, which is worse than a gate that
states its scope. The scope is written in the test's docstring.

## 6. Same class as the previous two rounds

| Round | Surface | Why it was invisible |
|---|---|---|
| `clone-reproducibility.md` | symlink targets | the working tree has the targets; only a clone does not |
| `doc-anchor-audit.md` | `#fragment` ids | `check_doc_links` drops the fragment; `mkdocs --strict` ignores it |
| this record | prefixed absolute paths | the check matched a quoted literal, not the prefix |

Each time the surface was checked, just not in the spelling that was actually
present. The remedy is the same: make the check match the shape of the
violation rather than one example of it.
