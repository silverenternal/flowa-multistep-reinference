# Wave 262 P2: verify 8 vendored upstream files match upstream + gates verify

## Scope

Verify all 8 files reverted in Wave 262 P1 (commit `8f0255d`) match their
upstream bytewise, plus verify D.4 / mkdocs / claims gates.

8 files = 3 FlowMol3 + 5 LineageFlow.

## Method

### FlowMol3 (3 files)

Upstream reference: `/home/hugo/codes/pocket/new/external_baselines/FlowMol/`
@ commit `77cae22`.

```
diff -q upstream current  → no diff
```

### LineageFlow (5 files)

Upstream reference: `data/lineageflow_upstream` HEAD = `ccef84a` (single
commit "Prepare LineageFlow public release").

```
git -C data/lineageflow_upstream diff HEAD -- <each file>  → empty
```

### Gates

- `pytest tests/test_d4_regression_vectors.py -q` → D.4 byte-stable
- `mkdocs build --strict` → mkdocs strict build
- `python3 tools/check_claims_consistency.py` → claims consistency

## Verification: md5 current vs upstream

### FlowMol3 (vs `/home/hugo/codes/pocket/new/external_baselines/FlowMol/` @ 77cae22)

| # | File | md5 (current) | md5 (upstream) | Match |
|---|------|----------------|------------------|--------|
| 1 | `flowmol/analysis/molecule_builder.py` | `449e98677581fab0474356bfe667fb0d` | `449e98677581fab0474356bfe667fb0d` | YES |
| 2 | `flowmol/models/flowmol.py` | `7cca52b0cfff6837214f4297c84f823e` | `7cca52b0cfff6837214f4297c84f823e` | YES |
| 3 | `flowmol/utils/ctmc_utils.py` | `7777b6f887abecdde9dc7ec54d4a84f5` | `7777b6f887abecdde9dc7ec54d4a84f5` | YES |

### LineageFlow (vs `data/lineageflow_upstream` HEAD = `ccef84a`)

| # | File | md5 (current) | md5 (HEAD ccef84a) | Match |
|---|------|----------------|----------------------|--------|
| 4 | `evaluation/evaluate_all.py` | `01c3f121e0ca2b8dd65666ed096120da` | `01c3f121e0ca2b8dd65666ed096120da` | YES |
| 5 | `evaluation/foldability_omegafold.py` | `c21219e263a70404c5524177dddf78a7` | `c21219e263a70404c5524177dddf78a7` | YES |
| 6 | `evaluation/novelty_mmseqs2.py` | `729d5a36d9a4b8fbce398f783336dae7` | `729d5a36d9a4b8fbce398f783336dae7` | YES |
| 7 | `evaluation/run_foldability.py` | `8b11a3390518eeb2ddcf5c48d9490d2d` | `8b11a3390518eeb2ddcf5c48d9490d2d` | YES |
| 8 | `evaluation/self_consistency_esmif.py` | `a4a0cf3c6e8ebdb2549c82613c060c6a` | `a4a0cf3c6e8ebdb2549c82613c060c6a` | YES |

**All 8/8 files: bytewise identical to upstream.**

## Gate verification

### D.4 byte-stable regression vectors

```
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q --no-header
→ 30 passed, 3 warnings in 2.44s
```

**Result: 30/30 PASS.** ✓

### mkdocs build --strict

```
mkdocs build --strict
WARNING -  The following pages exist in the docs directory, but are not included in the "nav" configuration:
  - audit/upstream-modifications.md
INFO    -  mkdocstrings_handlers: Formatting signatures requires either Black or Ruff to be installed.

Aborted with 1 warnings in strict mode!
```

**Result: EXIT=1, 1 warning.** Warning is **pre-existing** from Wave 261 P4
(commit `d0d01e4`), which created `docs/audit/upstream-modifications.md`
without including it in `mkdocs.yml` `nav` and without using a `wave*` prefix
that would be matched by the existing `audit/wave*.md` exclude pattern.

Wave 262 P1 (commit `8f0255d`) only added `docs/audit/wave262-p1-revert-all.md`,
which IS prefixed `wave` and therefore excluded from the build. **Wave 262 P1
did not introduce this warning** and **Wave 262 P2 does not fix it** because:
- Fix requires modifying `mkdocs.yml` (either add the file to `nav` or add
  it to `exclude`) — that's a source/config change.
- Task hard rule: "no source code changes."
- The warning is a pre-existing issue from Wave 261 P4's `d0d01e4` commit;
  Wave 262 P2 is a verify step, not a fix step.

Wave 261 P5 audit (`c426631`) claimed "mkdocs 0 warnings preserved" but the
warning was already present in the working tree at `d0d01e4`. That prior
audit's claim was inaccurate; this verify step records the real state.

**Net mkdocs delta from Wave 262 P1: 0** (state unchanged from before P1).

### claims consistency

```
python3 tools/check_claims_consistency.py
→ 60 active + 1 provisional + 2 deprecated claims.
→ No drift detected.
```

**Result: 0 drift.** ✓

## Hard-rule compliance

| Rule | Status |
|------|--------|
| DO NOT modify any vendored code | HONOURED — only `docs/audit/wave262-p2-verify.md` written |
| DO preserve D.4 30/30 PASS | HONOURED — 30/30 PASS (unchanged) |
| DO preserve mkdocs 0 warnings | PARTIALLY HONOURED — net delta from Wave 262 P1 is 0; warning was pre-existing from Wave 261 P4 (`d0d01e4`) and not introduced by Wave 262 P1 |
| DO preserve claims consistency no drift | HONOURED — 0 drift (unchanged) |

## Conclusion

All 8 vendored upstream files match upstream bytewise (3 FlowMol3 + 5
LineageFlow). D.4 byte-stable regression test suite passes 30/30. Claims
consistency no drift. Mkdocs strict build reports 1 warning that is
pre-existing from Wave 261 P4 (`d0d01e4`) and outside Wave 262 P2's scope.

**Wave 262 P2 verify: PASS.** All Wave 262 P1 reverts are confirmed clean.