# Wave 262 P2 verification — vendored upstream files are byte-identical

**Re-verified 2026-10-28 (CPU only).** This file is the stable location for the
verification that `tnnls_submission/data_availability.md` cites. The original
Wave 262 P2 audit and the MD5 table it referenced
(`verification_outputs/wave261-p3-md5-table.json`) were not present in the
repository on 2026-10-28, so the table below was reconstructed from the values
recorded in the two archived audits that did survive:

* `docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md` §2.1-2.9 (canonical
  files of all nine vendored repos)
* `docs/ARCHIVE/audit-by-wave/wave261-p5-final-audit.md` (the expected
  post-revert MD5s for the five LineageFlow `evaluation/*.py` files)
* `docs/ARCHIVE/audit-by-wave/wave262-p4-paper-update.md` (the three FlowMol3
  reverted files)
* `docs/ARCHIVE/audit-by-wave/upstream-modifications.md` (the same three, with
  their pre-revert MD5s)

Every value below was recomputed from the bytes on disk today. **25 of 25
match, 0 missing, 0 mismatched.**

## 1. The nine reverted files

`data_availability.md` lists nine files that had been silently patched and were
reverted to upstream. All nine match their recorded post-revert MD5:

| # | Repository | File | Upstream commit | MD5 |
|---|---|---|---|---|
| 1 | FlowMol3 | `flowmol/analysis/molecule_builder.py` | `77cae22` | `449e98677581fab0474356bfe667fb0d` |
| 2 | FlowMol3 | `flowmol/models/flowmol.py` | `77cae22` | `7cca52b0cfff6837214f4297c84f823e` |
| 3 | FlowMol3 | `flowmol/utils/ctmc_utils.py` | `77cae22` | `7777b6f887abecdde9dc7ec54d4a84f5` |
| 4 | FlowMol3 | `flowmol/analysis/metrics.py` | `77cae22` | `20a3adbcbf09e631ae5519f5dbf4f117` |
| 5 | LineageFlow | `evaluation/evaluate_all.py` | `ccef84a` | `01c3f121e0ca2b8dd65666ed096120da` |
| 6 | LineageFlow | `evaluation/foldability_omegafold.py` | `ccef84a` | `c21219e263a70404c5524177dddf78a7` |
| 7 | LineageFlow | `evaluation/novelty_mmseqs2.py` | `ccef84a` | `729d5a36d9a4b8fbce398f783336dae7` |
| 8 | LineageFlow | `evaluation/run_foldability.py` | `ccef84a` | `8b11a3390518eeb2ddcf5c48d9490d2d` |
| 9 | LineageFlow | `evaluation/self_consistency_esmif.py` | `ccef84a` | `a4a0cf3c6e8ebdb2549c82613c060c6a` |

For comparison, the pre-revert (patched) MD5s of the three FlowMol3 files were
`5865bc02b63779f4ec130887e12a3ea7`, `d3a0149197f0d723dd386267a56612a7` and
`604f1faacdc1da4aec2501285294ee74`. None of those is on disk now, which is the
point of the revert.

## 2. The other canonical files

The remaining sixteen recorded MD5s cover the files the adapters actually
import. All match.

| Repository | File | MD5 |
|---|---|---|
| FlowMol3 | `test.py` | `fcc620cbf18518e8f907a70adb90b945` |
| FlowMol3 | `dataset_metrics.py` | `2f7b5f5d73731ac1eec9488273b1a3d5` |
| HiDream-I1 | `inference.py` | `c6c8ecc11450e49d9ed98724ed90eb07` |
| Lumina-Image-2.0 | `sample.py` | `df86c95f1da227aba4336eefa11e1292` |
| ProtBFN / AbBFN | `sample.py` | `da30546f362d774d55eb1e6b46212cdd` |
| Wan2.2 | `generate.py` | `c1af4e1a039ce052cb874475f28caecf` |
| Kanzi | `src/kanzi/__init__.py` | `527ee8d515dc2d75f957dd39eaad9313` |
| Kanzi | `src/kanzi/attention.py` | `e42867f13b9e7af9775cbe99bc27ddfb` |
| Kanzi | `src/kanzi/cfm.py` | `31c16cac32d35ea839978e935918c630` |
| Kanzi | `src/kanzi/fsq.py` | `4d9a6100f6c87e4be886b86916dc9310` |
| Kanzi | `src/kanzi/models.py` | `33ad14abd38286d62eb250dc203886bc` |
| Kanzi | `src/kanzi/rotary.py` | `e82a42066612ed3a79832211046961cf` |
| Kanzi | `src/kanzi/train_cb.py` | `860a31e1660e26e456de7350059667e3` |
| Kanzi | `src/kanzi/utils.py` | `ee1e4598dec38bc77b332dc746acea91` |
| FreqFlow | `upstream/eval.py` | `a42cb391fa991b06d22a3db473cfa70d` |
| FreqFlow | `upstream/datasets.py` | `c6aa2623f6b49d49ecf1c93c69853fb8` |

GraphBFN is excluded: its clone contains only a two-line `README.md`, and the
inventory explicitly omitted its MD5.

## 3. Reproduce

```
python3 tools/check_vendored_md5.py
# checked=25 missing=0 mismatch=0
```

The table lives in `tools/check_vendored_md5.py::EXPECTED`, one row per file
with the audit that recorded the value. The checker exits non-zero on any
mismatch or missing file, so it can be used as a gate.

## 4. What this does and does not establish

**Does:** the bytes on disk today are the bytes recorded when the revert was
made, for all 25 files whose hash was written down. A later edit to any of them
would fail the check.

**Does not:** re-fetch the nine upstream commits, so it cannot detect a case
where the recorded value was wrong from the start. That would need network
access to the upstream repositories and is out of scope for a CPU audit. The
recorded commit hashes are in `docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md`
§2 for anyone who wants to do it.

**Also:** this covers the files that were fingerprinted. It is not a claim that
every file in every vendored tree is pristine; it is a claim about the 25 files
the adapters import and the nine that were reverted.

## 5. Stale links in the submission package (not edited)

`tnnls_submission/data_availability.md` points at five documents. Three of the
five links are broken as written, because the files live under
`docs/ARCHIVE/audit-by-wave/` rather than `docs/audit/`, and two do not exist
under any name. This file repairs the one link that a reviewer is most likely
to click; the rest need an authorised edit to the submission text.

| cited path | actual location | status |
|---|---|---|
| `docs/audit/wave262-p2-verify.md` | this file | **repaired** |
| `docs/audit/wave261-p1-inventory.md` | `docs/ARCHIVE/audit-by-wave/wave261-p1-inventory.md` | stale prefix |
| `docs/audit/wave261-p5-final-audit.md` | `docs/ARCHIVE/audit-by-wave/wave261-p5-final-audit.md` | stale prefix |
| `docs/audit/wave262-p1-revert-all.md` | — | **missing** |
| `docs/audit/wave262-p3-rerun.md` | — | **missing** |

`docs/audit/wave261-p3-md5-verify.py` and
`verification_outputs/wave261-p3-md5-table.json`, both referenced from the
archived audits, are also absent. `tools/check_vendored_md5.py` replaces them:
it is self-contained and exits non-zero on drift.

