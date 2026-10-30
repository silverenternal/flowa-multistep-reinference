# FreqFlow checkpoint directory (Wave 36 Agent B)

**Checkpoint status: NOT AVAILABLE — no public release exists as of 2026-09-05.**

This directory holds what *is* publicly obtainable for FreqFlow
(Ren et al., CVPR 2026, arXiv:2604.15521):

| Item | Status | Path |
|---|---|---|
| Upstream source tree | downloaded | `upstream/` |
| Upstream tarball | downloaded | `upstream.tar.gz` |
| Checksums | verified | `SHA256SUMS` |
| `nnet_ema.pth` weights | **absent (not published)** | `nnet_ema.pth` (expected) |

## Why the weights are absent

Probed 2026-09-05 from this host (network reachable, `github.com` HTTP 200):

- `api.github.com/repos/OliverRensu/FreqFlow/releases` → `[]` (no release assets).
- Full recursive git tree of `main` → code + `figs/img.png` only; no `.pth`,
  `.safetensors`, or LFS pointer.
- `huggingface.co/api/models?search=FreqFlow` → `[]`.
- `huggingface.co/api/models?search=Frequency-Aware Flow Matching` → `[]`.
- `huggingface.co/api/models?author=OliverRensu` → `[]` (no HF account).

The README's `--nnet_path=/path/to/nnet_ema.pth` is a **local placeholder in
the authors' own inference recipe**, not a download URL. No mirror was found.

## Manual acquisition procedure (when weights are released)

1. Watch <https://github.com/OliverRensu/FreqFlow> releases, or contact the
   corresponding author (`oliverrensu@gmail.com`, per the upstream README).
2. Place the file here as `nnet_ema.pth`, or point `$FREQFLOW_CKPT` at it:

   ```sh
   export FREQFLOW_CKPT=/abs/path/to/nnet_ema.pth   # file or containing dir
   ```

3. Record its digest and re-verify:

   ```sh
   cd data/freqflow_ckpt
   sha256sum nnet_ema.pth >> SHA256SUMS
   sha256sum -c SHA256SUMS
   ```

4. Re-run the gated suite; its skips flip to real-checkpoint assertions:

   ```sh
   pytest tests/test_adapters/test_freqflow_real_ckpt.py -v
   ```

Expected size ~2.7 GB (675 M params, fp32). License is unstated upstream
(no `LICENSE` file in the tree) — do **not** redistribute.

## Regenerating the upstream snapshot

```sh
curl -sSL -o upstream.tar.gz \
  https://codeload.github.com/OliverRensu/FreqFlow/tar.gz/refs/heads/main
```

`figs/img.png` (504 KB) is stripped from the extracted tree; the tarball
checksum in `SHA256SUMS` covers the unmodified download.

This whole directory is under the repo-wide `data/` gitignore and is **not**
committed. The durable record lives in `docs/models/freqflow.model_card.md`.
