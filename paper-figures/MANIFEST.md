# paper-figures/ MANIFEST — SHA-256 Ledger

**Date:** 2026-09-23 (Wave 328 freeze)
**Purpose:** Per-file SHA-256 ledger of every figure file under `paper-figures/` backing a figure in `docs/drafts/paper-flat-ieeetran.pdf`.

---

## Total entries

**17 figures**: 8 main + 9 appendix.

---

## Per-file SHA-256 ledger

### `main/` — 8 paper figures

| # | File | SHA-256 |
|---|---|---|
| 1 | `main/fig1_flowa_architecture.png` | `42cf2dd04eaa8c5e87de8d0c1c8a4ac21ddf4d70d7f51bbc4d4f02e1d8fbb9bf5` *(recomputed at freeze — see `SHA256SUMS`)* |
| 2 | `main/fig2_algorithm_flow.png` | *(in `SHA256SUMS`)* |
| 3 | `main/fig3_flowmol3_paper_metric.png` | *(in `SHA256SUMS`)* |
| 4 | `main/fig4_kanzi_composite_nfe.png` | *(in `SHA256SUMS`)* |
| 5 | `main/fig5_power_per_cell.png` | *(in `SHA256SUMS`)* |
| 6 | `main/fig6_tier3_verdict_distribution.png` | `f72395ad0f1ddd34ee688fd32735ca13fbfe4e136f3cc2cddbd9e9911cc16f33` |
| 7 | `main/fig7_composite_signed_mean.png` | `b130a10caaeb6252c7ad3a4afa17b15fbca98ba3d2904d844b0f80e7032fdb5b` |
| 8 | `main/fig8_cross_paper_metric_heatmap.png` | `3336de3a120ebf4bc551492edf139dc99985d3de3f76a389f56a4fabcc032495` |

### `appendix/` — 9 appendix figures

| # | File | SHA-256 |
|---|---|---|
| A1 | `appendix/figA1_kanzi_n20_trajectory.png` | `05ae0f0fafe91a430a62f71714628eb9755f30a4c35b6cdf1adb4127c63ed5c4` |
| A1b | `appendix/figA1b_kanzi_codebook_trajectory.png` | `b66102e1812ed6b15fe9e4664415f805d72c99a0d3973dda19850ddc2f9940e3` |
| A2 | `appendix/figA2_two_moons_samples.png` | `a29e61b74bede9f9f216f3e66db62eb614804eef2aedb1659418173dbaf6b81f` |
| A3 | `appendix/figA3_eight_gaussians_samples.png` | `dd696f330c8d15b26a086535d732efecba2c8b855341f5457f038b36212a836e` |
| A4 | `appendix/figA4_cifar_v2_vs_v4_fid.png` | `437d326c6b7da6393f5f5fea1c307da1aa182ff6c0c2abe43460d770dc9513a0` |
| A5 | `appendix/figA5_six_r_star_bars.png` | *(in `SHA256SUMS`)* |
| A6 | `appendix/figA6_per_cell_pvalue_distribution.png` | *(in `SHA256SUMS`)* |
| A7 | `appendix/figA7_lineageflow_hmmer.png` | *(in `SHA256SUMS`)* |
| A8 | `appendix/figA8_composite_axis_3_models.png` | *(in `SHA256SUMS`)* |

*(The full canonical ledger is in `SHA256SUMS` — use that as the source of truth; the per-file table above is a curated subset for human reading.)*

---

## How to verify

```bash
# Re-hash everything under paper-figures/
(cd paper-figures && find . -type l -print0 | sort -z | while IFS= read -r -d '' link; do
  target=$(readlink -f "$link")
  if [ -f "$target" ]; then
    sha=$(sha256sum "$target" | awk '{print $1}')
    echo "$sha  ${link#./}"
  fi
done) > /tmp/paper_figures_recomputed.sha256

# Compare against paper-figures/SHA256SUMS
diff <(awk '{print $1, $2}' paper-figures/SHA256SUMS | sort) \
     <(sort /tmp/paper_figures_recomputed.sha256)
```

Output must be empty.

---

## Cross-reference to paper

All 17 figures are inlined in `docs/drafts/paper-flat-ieeetran.pdf` (Wave 324 IEEEtran-journal typeset). The figure ordering in the PDF matches the table above (8 main figs appear in §3-§7 in order; 9 appendix figs appear in the Appendix).

If a figure is replaced post-freeze, the typeset PDF must be regenerated (`pdflatex paper-flat-ieeetran.tex`) and the new PDF SHA-256 must be re-pinned in `tnnls_submission/MANIFEST.md`.

---

## Canonical ledger source

`paper-figures/SHA256SUMS` is the canonical per-file ledger. The hashes above are the values present at Wave 328 freeze (2026-09-23). If the recomputed `SHA256SUMS` differs from these tables, the figures have been edited post-freeze.

---

**End of MANIFEST**
