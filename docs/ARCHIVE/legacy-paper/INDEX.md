# docs/ARCHIVE/legacy-paper/ — superseded manuscript surfaces

**Created:** 2026-10-21.
**Why:** `docs/` and `docs/drafts/` each carried several generations of the
manuscript body next to the canonical `docs/drafts/paper-A-final.*`. They were
moved here with `git mv` (history preserved, nothing deleted) so the live
directories contain one manuscript.

**Nothing in this directory is read by tooling.** Verified with a repo-wide
grep of `*.py` / `*.sh` / `*.yml` before the move. The historical audit records
that cite the old paths (`docs/audit/wave*.md`, `docs/ARCHIVE/audit-by-wave/*`)
are left untouched on purpose: they describe where a file was at the time, and
rewriting them would falsify the trail.

## Moved from `docs/`

| file | era | why it is not live |
|---|---|---|
| `paper-draft.md` | EAAI | superseded by `paper-A-final.md` |
| `paper-draft-anonymous.md` | NeurIPS | anonymous review build, never canonical |
| `paper-final-neurips.md` | NeurIPS 2025 | different venue template, different claim set |
| `paper-final-neurips.pdf` | NeurIPS 2025 | render of the above |
| `paper-eaai.pdf` | EAAI | render of the EAAI-era body |
| `paper-tnnls.pdf` | TNNLS draft | byte-identical duplicate of `paper-eaai.pdf` |
| `paper-draft-precut.md.bak` | pre-cut snapshot | superseded; kept for provenance |
| `paper-draft-precut-w193.md.bak` | pre-cut snapshot (Wave 193) | superseded; kept for provenance |

## Moved from `docs/drafts/`

| file | why it is not live |
|---|---|
| `paper-flat-ieeetran.tex` | pre-flattening LaTeX draft; `paper-A-final.tex` is the live source |
| `paper-flat-ieeetran.pdf` | render of the above |
| `paper-flat-ieeetran.aux` / `.out` / `.log` | LaTeX intermediates of the above |
| `pdflatex-rerun.log` … `pdflatex-rerun4.log` | build-iteration logs, superseded by `paper-A-final.log` |

SHA-256 values for the moved `paper-flat-ieeetran.*` files are unchanged and are
still recorded in `docs/drafts/ARCHIVE_INDEX.md` (rows marked MOVED 2026-10-21).

## Deliberately NOT moved

| file | reason |
|---|---|
| `docs/drafts/paper-flat-flattened.ARCHIVED-2026-09-23.md` | referenced by the frozen `tnnls_submission/MANIFEST.md` (GitHub blob link); moving it would dangle a frozen surface |
| `docs/drafts/paper-flat-flattened-zh.md` | cited by `docs/drafts/ARCHIVE_INDEX.md` as the bilingual provenance copy |
| `docs/drafts/paper-flattened-draft.md`, `results-final.md`, `abstract-final.md`, `section-2-method.md`, `methods-*.md`, `limitations-*.md` | live draft components still cited by the canonical build |

## Live manuscript

`docs/drafts/paper-A-final.md` (prose) → `paper-A-final.tex` (IEEEtran) →
`paper-A-final.pdf`. Frozen surface: change only via additive addenda.
