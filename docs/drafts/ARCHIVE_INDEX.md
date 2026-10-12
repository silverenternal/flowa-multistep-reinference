# docs/drafts/ ARCHIVE_INDEX

> **Catalog layer for archived + flattened-intermediate files.**
> Wave 356 P5 — added as ADDITIVE catalog (no files deleted).
> Generated: 2026-09-25.
>
> This index is the self-documenting archive layer for `docs/drafts/`.
> The canonical paper surface remains `paper-A-final.md`
> (canonical prose), `paper-A-final.tex` (compiled source), and
> `paper-A-final.pdf` (rendered). The remaining files fall into two
> categories: (a) **ARCHIVED** snapshots preserved for historical
> provenance; (b) **flattened intermediates** preserved as the
> working drafts that fed into the canonical final.

## Canonical surfaces (NOT archived)

| File | Size (bytes) | SHA-256 | Role |
|---|---:|---|---|
| `paper-A-final.md`   | 243669 | `9ec5b7f41ac113f88251cbea36aaeb08d599605829972cba4b58bf7640f4d23d` | Canonical prose (paper body) |
| `paper-A-final.tex`  | 110195 | `2d4785a3920dacfdbf89e8237a83f1bc7b27e833b6bdf62d25cc1a31a721a0fe` | LaTeX source (IEEEtran) |
| `paper-A-final.pdf`  | 305270 | `57c6d38373eb2e0a851b67472630c2f8fbc9df2bcb8342ffa15b9384e7e2dd35` | Rendered PDF |
| `abstract-final.md`  |  13399 | `d4146d7094b28e955aba65dbcca4972930851caa4e3734fbcfab24398c799cc5` | Canonical 9-sentence abstract |
| `results-final.md`   |  60937 | `3aa762d37c9a1bb57a61fcff56d9856267ed7e9065ed08fd7443211d77357144` | Canonical results / §3 / §4 |
| `paper-flat-ieeetran.tex` | 66293 | `c9f4a7d489289d8d15548e0c6af1851791444297ffa3e0475a075c8f49c86a05` | Pre-flattening LaTeX draft (still actively referenced by paper-build flow) |
| `paper-flat-ieeetran.pdf` | 381510 | `d9133f5f9b8bbc9d056f1cc127ed307a820a208df07913acd682a8290d75877a` | Rendered PDF of `paper-flat-ieeetran.tex` |

> **Note.** `paper-flat-ieeetran.tex` is retained as an **intermediate
> LaTeX working surface** referenced by the paper-build driver; it is
> NOT catalogued as an archive item because it is still actively used.

## Archived + flattened files (catalog layer)

### 1. ARCHIVED snapshot

| File | Size (bytes) | SHA-256 | Archive reason |
|---|---:|---|---|
| `paper-flat-flattened.ARCHIVED-2026-09-23.md` | 334703 | `f33d11141e83d2063a6889fbc9e2e0a79e257a25e9edd4b16075c5bf638e88f7` | Explicit `ARCHIVED-2026-09-23` rename on 2026-09-23 (Wave 271-era cleanup); preserved for historical provenance — pre-flattening snapshot of the paper body. Cross-reference: superseded by canonical `paper-A-final.md` (243 KB canonical prose). |

### 2. Flattened-intermediate drafts

These eight files are working-draft snapshots that fed into the
canonical paper surface. They are NOT actively compiled but are
preserved as provenance artifacts (some are still cited as
historical references in `abstract-final.md` and `results-final.md`).

| File | Size (bytes) | SHA-256 | Archive reason |
|---|---:|---|---|
| `paper-flat-flattened-zh.md`     | 268307 | `90a68b710964600bc4876087de5af447ceedb754a793a267efe844706a3880ea` | Chinese-language flattened snapshot of paper body (pre-`paper-A-final.md`); preserved for bilingual provenance. Cross-reference: superseded by canonical `paper-A-final.md`. |
| `paper-flattened-draft.md`       |  92287 | `3d3b9f61b06cf3145c00ef7f3113904039f20e164bc94a42b7ea1f440c975514` | English-language flattened paper draft (Wave 207-era §Abstract + §4 K1–K8 verbatim). Cross-referenced in `abstract-final.md` (Provenance §, line 151) and `results-final.md` (line 936). |
| `abstract-flattened.md`          |   4056 | `37b2ba472dbf4837c031a52a44b2334f7f1e26f53c79de401ec664f7d0a5e517` | Flattened abstract snapshot (Wave 207-era); preserved as historical evidence. Cross-reference: superseded by canonical `abstract-final.md` (9 sentences, TNNLS envelope). |
| `methods-stats-flattened-draft.md` |  17475 | `9998f7bd814ee9a9b0ed440f7903f2a59b5abe06db7de740f669ce4d734f6f6e` | Methods §MS subsection flattened draft (TOST / Jonckheere-Terpstra / BF01 / meta / non-inferiority). Cross-referenced in `results-final.md` (lines 31, 306, 318, 322, 366, 934). |
| `methods-why-per-record.md`      |  54676 | `3c3ac3070cb2bb37c5a880c5ad7d3be42162de3ece6eda765bd1f72586027f69` | Per-record statistical methodology justification; preserved as historical methodology rationale. Cross-reference: superseded by `methods-stats-flattened-draft.md` and `paper-A-final.md` §MS. |
| `results-flattened-draft.md`     |  42266 | `2cf985bdc4de33f829311e6b4ff78694faba539d387cdfd3ade2fe6d2342158f` | Flattened results / §3 / §4 draft (Wave 207-era); preserved as historical evidence. Cross-reference: superseded by canonical `results-final.md`. |
| `section-2-method.md`            | 113570 | `c0bd668fcba003f688bcda393ca01e0870a07076ab0b4c9476f9977c51700858` | Detailed §2 Method draft with confound-analysis reading; preserved for per-seed table + confound disclosure provenance. Cross-referenced in `abstract-final.md` (line 25). |
| `limitations-flattened-draft.md` |  21610 | `e2c7872cdcb04380072506093b51860b08dd4f8d0d1fd75e75efdcd4bc381e14` | Flattened limitations draft (K1–K8 borderline + UNDERPOWERED moved here as boundary statements). Cross-referenced in `results-final.md` (lines 29, 646, 888, 931). |

### Aggregate

- **Total archived + flattened files:** 9
- **Total bytes:** 948140  (≈ 0.904 MB)
- **All SHA-256 captured** for byte-addressable provenance.

## Verification

All 9 archived + flattened files were verified by `grep -F` against
`paper-A-final.md` (canonical prose) — zero matches. Cross-references
that **do** exist (in `abstract-final.md` and `results-final.md`) are
**intentional historical provenance citations** and are documented
in the per-file "Archive reason" column above.

## Policy

- **No file deletions.** This index is an ADDITIVE catalog layer.
- All archived + flattened files are byte-stable and git-tracked.
- The canonical paper surface (`paper-A-final.md` / `.tex` / `.pdf`)
  remains the source of truth.
- If a future agent wishes to remove any archived file, that
  decision must be USER-AUTHORIZED and reflected here.

---

_File created: Wave 356 P5 (2026-09-25) — USER AUTHORIZED, NO PUSH._