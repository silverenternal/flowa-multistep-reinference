# `verification_outputs/` MANIFEST

**Date:** 2026-09-22

This manifest enumerates every file that is git-tracked under `verification_outputs/` (439 files) with its SHA-256 hash, byte size, R-cell grouping, and a one-line description of what headline number it backs.

Reviewers can verify the headline numbers claimed in the paper by re-computing each SHA-256:

```bash
sha256sum verification_outputs/<file>
```

The hash listed in the table for `<file>` MUST match. If it does not, the artifact has been edited since this manifest was generated — re-run the upstream pipeline that produced it before trusting the headline.

Categories follow the paper's R-level taxonomy (R1 LineageFlow HMMER / R2 Kanzi RMSD uplift / R3 FlowMol3 fg_dev / R4 2D Two Moons / R5 2D Eight Gaussians / R5b CIFAR-10 RF / R6 MNIST FM tier-aware / R1+R2 cross-model / 4-arm head-to-head / statistical methods / wall-clock evidence / engineering gates / other). File paths contain historical wave numbers (cannot be renamed without breaking git history); descriptions stay free of them.

**Total entries:** 439 files

## R1 LineageFlow HMMER (paired N=1000 sweep)

Per-record pLDDT + scPerplexity paired foldability sweep (N=1000) for the R1 LineageFlow HMMER cell. Backs the headline R1 protein-axis framework-vs-baseline delta (Cohen's d_z, tier breakdown) used in CLM-039/CLM-040 references.

Files in this section: 24

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability.log` | 351114 | `dd04671107b205c83eb54515fc35a8008fa1fc8091a6f451be917f0f204f8132` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/foldability.jsonl` | 265386 | `164825057a413af6f4d27a53b3ca519484f5c36019dafaa6c14e33dc823e4261` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/inputs.json` | 125 | `f6c8cd15f99c1e0d73cca02edc21b1885dcc4a4be32cc5968844582e9041f82c` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/metrics_summary.json` | 302 | `f50f3fc6fb353645e89e5cec7da86981fe08ba4ecd735f2f758e263aa6670a60` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/queries.fasta` | 96939 | `503dc8ce3c224ba17efbf3773d697194785dca395681e9cfecc2c7baa44b66b2` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/self_consistency.jsonl` | 185368 | `fd21d98829eb5d5df9d87d3295637bd4a9c5524cff6663ed6f384d43db45ea92` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/self_consistency_summary.json` | 253 | `62be16f2114926350f9c37728bf65ca09bb212276e716353603e404e8f5f63cf` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/foldability/summary.json` | 247 | `5d483e3f4619dd9ebb26f3644e68b3e9522579ceed4240b447880a19ace23e20` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/run_manifest.json` | 288 | `bf896fe6a61ac6863c2568bdd05698a8ccd66aecaba772a060e202aab13f2a51` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/sha256.txt` | 917 | `e90b18359bc4fad1a4382f7db982b2b2a3e2030badf48562bcf4f717936f11fd` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/summary.json` | 344 | `7dc407880063760bd36806518dfbf9f81f7057729fd1ce0a69dafbf906bd0e3d` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/baseline/sweep.log` | 49 | `0137329acd80af83998ff3255b75f1888f39c171161795ee35ba161835b3dce5` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability.log` | 353431 | `40ba4765ce8ea2ecdf473b51452fa8b52efe9d89d1d40cd39aeda3114ee76c73` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/foldability.jsonl` | 266738 | `b608edfb0f13a39bde5a06c3d16ccc94aa98f90db5434411cefe2f647574fc85` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/inputs.json` | 126 | `a1daa9ad501d1dd3345caf5198fa118a20ecb9a54e67ab775146de77a5f95003` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/metrics_summary.json` | 304 | `2b36d588485d40dd65add5af3b4f5775a0536df5a21a2033157f3afe31839e3e` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/queries.fasta` | 97313 | `7cb699eb4b5381c17cdaad62f0c4e1f50b1cf1b88d6b37709e64a7d87ca9b192` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/self_consistency.jsonl` | 186491 | `bbd7ca13b46eb81a4d72fa5a7da25c095f0751b81eead315de5d2cdcb0a1d34b` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/self_consistency_summary.json` | 253 | `21bfab127b1dde26719051954c92c88f7193b09326bac97cdd29771db2930000` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/foldability/summary.json` | 249 | `e96b1e2592a36d25a29658df9258fd408be454aa1ac2bd09f13e1d44f35c3aad` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/run_manifest.json` | 291 | `23db172be2b17a8d232324fa008afceebf1d3770628e6c2054d676acf5773d63` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/sha256.txt` | 924 | `4cfaf900cfced698e145b1f1f6bc915de94a71be62749bc8c8cde12a67a5b7f0` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/summary.json` | 346 | `0aa63c652c6a6ba1bcd5dddfd89c5183efbd76d00dae3557ff1db838a1350269` |
| `verification_outputs/k6_foldability_n1000_w161_q3_2026/framework/sweep.log` | 50 | `9856691ceb2f211f72b2db8a01e91539abbf148dbc717b049cefa0666bd18de6` |

## R1 LineageFlow HMMER (real N=1000 OmegaFold)

Real-checkpoint LineageFlow N=1000 foldability evaluation using OmegaFold as the structural ground-truth model — backs the R1 headline pLDDT/scPerplexity per-record paired data.

Files in this section: 30

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/foldability.jsonl` | 256368 | `ffdc0da7a0083113a6b7325ea28cb397286e3b60004056f5fba32fa2dd76b62b` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/inputs.json` | 115 | `71490eebc656e98074668f52a21fdb54693361b46d659860a90914ba9ef393d8` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/pdb/q0.pdb` | 58409 | `c301b815310db3b500f7dcd5bd88bce1793776c5551c6fdc0dcfbada9baa04a3` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/pdb/q1.pdb` | 58571 | `1a6197f4c3b3ed8c3f698a6eca98d382046a74d2691cb0d930881e3fc54de8ca` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/pdb/q2.pdb` | 61973 | `c8f9718d457e3e62bda054d8e7f71da5afc01ad8ca89dc95f524df6e49dc1af5` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/pdb/q3.pdb` | 62216 | `12cdd54f30e0a7c3e899b2565b06de84a7ba62afbe59ce185b1c5d374f050d54` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/pdb/q4.pdb` | 62135 | `f90466a315759e87b117140e665866c2cecc609736f431193091f53cebe80837` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/queries.fasta` | 437 | `da15c2ff5f234f0b704b051a2dbbdddde2ccfa5e14930cbcc0abc64936da7026` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/queries_20260908_223419.fasta` | 437 | `da15c2ff5f234f0b704b051a2dbbdddde2ccfa5e14930cbcc0abc64936da7026` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/fold/summary.json` | 247 | `e14dadafe708d75b44252d6d8d374d4359b74b694e59d408c7027502fc97d0d5` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/metrics.jsonl` | 334551 | `889039775217755f9755ac66c0a804b8fc0f9d150dd5ac51f0b8d255736c3cfd` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/queries/queries.fasta` | 96939 | `503dc8ce3c224ba17efbf3773d697194785dca395681e9cfecc2c7baa44b66b2` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/sc/self_consistency.jsonl` | 176387 | `5ac40b3e2402b27edc333fb5d612b99a6bdf680d249b09d5e320102d98f329e0` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/baseline/sc/self_consistency_summary.json` | 253 | `7d7117385d2131250e45fd8c0d0be295c875f42b050a456b73a567b867a7761a` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/foldability.jsonl` | 196357 | `2e04c3e57e5302d8033f1b1c49bd4decae5ba0f66305e0dea5070e04811499f2` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/inputs.json` | 116 | `87e90dfa4a12e8011d311203104f383ec832c2e39266cce390ad2176756f9d5f` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/pdb/q0.pdb` | 58409 | `c301b815310db3b500f7dcd5bd88bce1793776c5551c6fdc0dcfbada9baa04a3` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/pdb/q1.pdb` | 58571 | `1a6197f4c3b3ed8c3f698a6eca98d382046a74d2691cb0d930881e3fc54de8ca` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/pdb/q2.pdb` | 61973 | `c8f9718d457e3e62bda054d8e7f71da5afc01ad8ca89dc95f524df6e49dc1af5` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/pdb/q3.pdb` | 62216 | `12cdd54f30e0a7c3e899b2565b06de84a7ba62afbe59ce185b1c5d374f050d54` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/pdb/q4.pdb` | 62135 | `f90466a315759e87b117140e665866c2cecc609736f431193091f53cebe80837` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/queries.fasta` | 437 | `da15c2ff5f234f0b704b051a2dbbdddde2ccfa5e14930cbcc0abc64936da7026` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/queries_20260908_225205.fasta` | 437 | `da15c2ff5f234f0b704b051a2dbbdddde2ccfa5e14930cbcc0abc64936da7026` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/fold/summary.json` | 241 | `40cd1922c7b9b5d8a7d77f65ff14ed077095ed79fcb9f46eab9ced8de254f077` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/metrics.jsonl` | 241261 | `8c5eb155797048212c728de5155d9c60d52ebc37b0f3bd6c077dabd52936478e` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/queries/queries.fasta` | 97313 | `7cb699eb4b5381c17cdaad62f0c4e1f50b1cf1b88d6b37709e64a7d87ca9b192` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/sc/metrics_summary.json` | 257 | `cb7432d33eee55e3d27ac1afe5cc65c22dd79a7f18e4b57096aa6f33d2b43cd6` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/sc/self_consistency.jsonl` | 132649 | `f6c4db8658c56dc20a6bf0808ead5a755f938c56be2fe46212700e8582788b1a` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/framework/sc/self_consistency_summary.json` | 300 | `53db4e6d99c58ca73efb5e018dceb395307c28dad2e5e8ccdaac6ca915ca1b39` |
| `verification_outputs/lineageflow_n1000_omegafold_q4_2026/sweep_summary.json` | 1596 | `ac1dc9c0a3586e1978ca914dcc6188a9e85eef7ef2c1ab1dbdc3f10617c28a3b` |

## R1 LineageFlow novelty (MMseqs2)

MMseqs2-based novelty checks against UniRef-style reference databases, used to back the LineageFlow claim that generated sequences are not memorised training data.

Files in this section: 24

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/baseline/easy_search.m8` | 5850 | `584915814a563bb33b84d8c23ff7c03d9ee62023ffd4b746f413043aacf6288e` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/baseline/per_seq.jsonl` | 138204 | `e72c7b463972c62bebec8a5db1fa13a40d53198da9e541d884a4c28c6eb0592b` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/baseline/summary.json` | 1039 | `5636078c9857f1aa830ad9fc18441bf83e92a0cb41b5a36a136f370e8a798709` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/baseline/sweep.log` | 10066 | `39f50a820e9d54a10f42e35978f140483b33e4eeb95169adb6be381750098774` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/framework/easy_search.m8` | 1773 | `79b29fd5f70a69fe9234493b7a02c6b501a92f7e04a960213f0943e60bc5b4eb` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/framework/per_seq.jsonl` | 139210 | `f05faae1a7762a8401c1762d85c035dbea55b05023879779b05453324da54491` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/framework/summary.json` | 1040 | `9b26432a85a566fd93aa94ede4d93d40523dff136153779afbb543f2776d5ec8` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/framework/sweep.log` | 10081 | `155d3c0568fcbf4d3b4dfc0aff053900b013f786fbcd3aedd1a1f7d6484d31d4` |
| `verification_outputs/lineageflow_novelty_mmseqs2_w163_q3_2026/metrics.json` | 393 | `bb7edf299a33938c29b349bccc979670a4bb341ed5830db464a15b2ad3fdc694` |
| `verification_outputs/novelty_canonical_sensitive_w165b_q3_2026/baseline/sanity_n5_loose.m8` | 669 | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `verification_outputs/novelty_canonical_sensitive_w165b_q3_2026/baseline/sanity_n5_strict.m8` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `verification_outputs/novelty_canonical_sensitive_w165b_q3_2026/framework/sanity_n5_loose.m8` | 12672 | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |
| `verification_outputs/novelty_canonical_sensitive_w165b_q3_2026/framework/sanity_n5_strict.m8` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `verification_outputs/novelty_canonical_sensitive_w165b_q3_2026/novelty_results.json` | 631 | `ddeb6779b796d6183b28967c7589e3dec143b401e4ffaacdf9150c47446c34e9` |
| `verification_outputs/novelty_canonical_w165_q3_2026/baseline/full.m8` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `verification_outputs/novelty_canonical_w165_q3_2026/baseline/sanity_n5_loose.m8` | 481 | `39b219fe3096156acf6426df523621de1a8dafef23ec990555996592a810c134` |
| `verification_outputs/novelty_canonical_w165_q3_2026/baseline/sweep.log` | 12478 | `28da788a4cb33e7421c210b434d2d9c3ac02d5d6b09699843e42b6063d57aa89` |
| `verification_outputs/novelty_canonical_w165_q3_2026/framework/full.m8` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `verification_outputs/novelty_canonical_w165_q3_2026/framework/sanity_n5_loose.m8` | 5351 | `b4121f95008a9025eaf77464c48e9b5afc1d876cdc0b3e0390ffb3d8fbf54b76` |
| `verification_outputs/novelty_canonical_w165_q3_2026/framework/sweep.log` | 12499 | `143c5363754e0bf5c8fe7d86c97efa72610664d503bec8734916f3193dce3a84` |
| `verification_outputs/novelty_canonical_w165_q3_2026/novelty_results.json` | 851 | `513164ca4788043d3c4b3b7d19286aa59339c59d02857701e3b2d3263b6126c9` |
| `verification_outputs/novelty_pctid_w166_q3_2026/baseline/sanity_n5_loose.m8` | 669 | `0f7702aa4eaa26efa7b017999ccddce471eb74061a0770fa8bba1c7760b96d85` |
| `verification_outputs/novelty_pctid_w166_q3_2026/framework/sanity_n5_loose.m8` | 12672 | `5886075cf010409b58181da24a44513ef99db993a00ba305802b9a4f32029307` |
| `verification_outputs/novelty_pctid_w166_q3_2026/novelty_results.json` | 2574 | `91f054f40bddf0a767b339026e7389377e37ed47984ecb290716ccd0daa9f292` |

## R2 Kanzi RMSD uplift (baseline seed=42)

Kanzi baseline RMSD-vs-reference data (seed=42) across multiple iterations; backs the R2 baseline arm's per-record RMSD distribution.

Files in this section: 2

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_baseline_seed42_wave116_q3_2026/kanzi_n1000_paper_metrics.json` | 2523 | `9b3a83f64f6269a2fbf64fb62166e20e9a9ed2b9d400bb9adeae79e3a30a8f58` |
| `verification_outputs/kanzi_n1000_baseline_seed42_wave120_q3_2026/kanzi_n1000_paper_metrics.json` | 2523 | `e0b91baaccde4dff46d94dae6a496a506cb213a7acccfade03a39bdf42f79e40` |

## R2 Kanzi RMSD uplift (baseline seed=7)

Kanzi baseline seed=7 arm — multi-seed coverage of the R2 baseline RMSD distribution.

Files in this section: 1

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_baseline_seed7_wave121_q3_2026/kanzi_n1000_paper_metrics.json` | 2522 | `d20131b6e4a5362c91d28ab27dd9cd161018015335f444a24254761f3f2e2291` |

## R2 Kanzi RMSD uplift (framework inv_proj)

Kanzi framework inv_proj arm — inverse-projection warm-start — backs the R2 framework-vs-baseline per-record RMSD uplift headline number.

Files in this section: 2

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave122_q3_2026/kanzi_n1000_framework_paper_metrics.json` | 2131 | `a81c904f5c524997761eb27a0cfb5301a34991222f98c8ed739183e742e060fe` |
| `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/kanzi_n1000_framework_paper_metrics.json` | 37541 | `27754517a4b032eeb2ceb9d6c127e19f71baa04ab14c9d882360d1bd1a053bf0` |

## R2 Kanzi RMSD uplift (framework inv_proj byte-repro)

Byte-reproducibility capture of the framework inv_proj N=1000 run; identical bytes across re-runs confirm the R2 headline number is reproducible.

Files in this section: 1

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_framework_inv_proj_seed42_wave131_byte_repro_q3_2026/kanzi_n1000_framework_paper_metrics.json` | 37541 | `ab2416bb3eaab056a4823200a083893f0ef9407c9ed99898b1a91e8072a6a2e3` |

## R2 Kanzi RMSD uplift (framework synth seed=42)

Kanzi framework synthesis-from-codebook arm (seed=42) — second framework variant used to triangulate the R2 uplift.

Files in this section: 1

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_framework_synth_seed42_wave121_q3_2026/kanzi_n1000_framework_paper_metrics.json` | 2810 | `b0b7abe8c61e59ed6e758899d457bacd33f83fd024b8b051b5651ca615ecf8b9` |

## R2 Kanzi RMSD uplift (framework synth)

Earlier Kanzi framework synthesis-from-codebook capture before seed=42 freeze.

Files in this section: 1

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_framework_synth_wave120_q3_2026/kanzi_n1000_framework_paper_metrics.json` | 2767 | `102f3eb4a77f19e8fef52c79bf1cfc632483a7f60a020717d1cec790727bb598` |

## R2 Kanzi RMSD uplift (paper metrics)

Kanzi paper-metric JSON for the R2 cell — paper-aligned RMSD and TM-score outputs that back the R2 headline.

Files in this section: 1

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_paper_metrics/kanzi_n1000_paper_metrics.json` | 2191 | `02e9df307defda4f25acadb3dcd135ed697898f9766908f82f823f892e1aa942` |

## R2 Kanzi RMSD uplift (diverse)

Kanzi framework paper-metrics capture using a more diverse query subset — backs the R2 generalisation claim.

Files in this section: 2

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/kanzi_n1000_framework_paper_metrics.json` | 1980 | `a0c37b498f8c664bfdb5b7e39182aad79a083f040d2a61cf05aa29f5206321bd` |
| `verification_outputs/kanzi_n1000_framework_paper_metrics_diverse/per_metric.jsonl` | 1376 | `c9a5956441ec0bf4ce2f6ea74d054f47389cdd05e8655da159bd3517339abeea` |

## R2 Kanzi RMSD uplift (inv_proj corrected)

Inverse-projection N=20 sanity + run-exit logs (corrected after the earlier correctness bug); backs the framework inv_proj path.

Files in this section: 7

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/checkpoint.json` | 9814 | `ceb2d1da861386a3a80147e634655e5e489cfc0235e93de9473a2fa18b65776b` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/initial_summary.json` | 3446 | `3d216cda424895e3343654bd1c39da37af1b087d16b7df08156dbefb836c73bf` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/invocation.json` | 1026 | `c363660deef417490be140ec8eba053692e10b0b7f9c7f3dc8d8e7b949b80d61` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/kanzi_n1000_framework_paper_metrics.json` | 3456 | `c01014cfdfb5005cc8fcf44190a284fcdf360e7fab51fa4242d3de55a4e753a5` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/resume_exit.json` | 53 | `2f6f6320b1efcd07c0d944f55dd1e5ba510ae070bf5d6905f370d0819a2ca920` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/resume_verification.json` | 50 | `6e73501d30d106a9bf9096815f50dfdad4379e477d6f00800ca5a0bcdee74ea5` |
| `verification_outputs/kanzi_inv_proj_n20_20260913_corrected/run_exit.json` | 53 | `0dd0da43f4bffb80f55137f7d9bc0600d7a4874d08630f0e03e3cd02a0e20749` |

## R2 Kanzi RMSD uplift (framework inv_proj bundle)

Framework inv_proj N=1000 bundle — paired RMSD per record plus summary JSON — backs the R2 framework arm's RMSD distribution.

Files in this section: 4

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-baseline/kanzi_n1000_paper_metrics.json` | 35954 | `f43ff1334505cd0f12b91a682e42263f57bf3dbd0df5c0e7a02d1947433572b0` |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-summary.csv` | 436 | `5d2f5e7cec25b00068ab5fa3376a54fb4c57048f34fa1901eadf14e83867dab0` |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.csv` | 32392 | `3bac9ecce2c46c6a30e93220902adc5c474bb9e05a3707708a57dfe8243ec78f` |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.json` | 2849 | `a33c04f2fea8215a76e45d88f976835f7f4da36cfde9b555a4007894952280f4` |

## R3 FlowMol3 fg_dev (molecule)

Per-record SMILES, fg_dev, REOS, validity and uniqueness outputs for the FlowMol3 molecule cell. Backs the R3 framework-vs-baseline fg_dev headline number and the 3-seed reproducibility sweep.

Files in this section: 13

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave189-p3-freqflow-real.json` | 4595 | `3b6e80ebf3c104fee5a88fce50e2b6a680ec7cf91a4a5ef8cc6143cf21b926d3` |
| `verification_outputs/wave189-p4-theorem-load-bearing-kanzi.json` | 7715 | `dd24418a94ed2be22c5133b5bfdb121d305c4162f42082c17c2f5a6462c0b8d9` |
| `verification_outputs/wave190-p2-kanzi-n30.json` | 30486 | `eda22a36c36619290a97b905cf0e16c2e9c4bd9afc31a75d775c8e1ff7d56f3d` |
| `verification_outputs/wave190-p3-lineageflow-n30.json` | 31922 | `a605fdaabeb0b4b0ad2caab68e37045e6adc0224deb7338e851d2031d41c5c97` |
| `verification_outputs/wave206-p3-flowmol3-n1000.csv` | 1417 | `f1abacbdee70f8734ec1300b6f1c769c7b15366adffe2d5002efb4381cd3bb80` |
| `verification_outputs/wave206-p3-flowmol3-n1000.json` | 1667 | `c20a9183931c2b10a3074981204676c83f630ebfd95a60afa248531261c42f36` |
| `verification_outputs/wave235-p4-flowmol3-3seed-per-record.csv` | 167470 | `a20d902e454707dfae1302541eada99f5e58655b62a846bab089c7539d8b2977` |
| `verification_outputs/wave235-p4-flowmol3-3seed.csv` | 1449 | `4ff2a7eeb914d859a2e798d7f4c83968d5919c9995f38f8be5a77ffcc1f31c73` |
| `verification_outputs/wave235-p4-flowmol3-3seed.json` | 1747 | `4ef06440229ec31ca49b0aeceb8f34746dcd7e3f441552d317c6bd7d3cd3a120` |
| `verification_outputs/wave235-p4-flowmol3-seed44-framework.json` | 14445 | `50c543997f318217edb496b192594f469f64bcda85b4742bbe8544f669db488c` |
| `verification_outputs/wave235-p4-flowmol3-seed44-framework.smiles.txt` | 32409 | `6bfad7d0a72ee65b7068fa8406274e0d8ad12a2c3740447beeeedb7e11611b3f` |
| `verification_outputs/wave240-p2-flowmol3-direction.csv` | 1503 | `c4f5b0b3ad5d8839919dddca22834ae89ea993d2d39c491be514404f040e54d5` |
| `verification_outputs/wave242-p2-flowmol3-direction.csv` | 1596 | `4edb517cc8080b405ac5d24aa9d753228b1abdec119cc41e2b1f79432e4a632b` |

## R1+R2 cross-model sweep (real checkpoints)

Cross-model sweep that runs both R1 (LineageFlow) and R2 (Kanzi) on real upstream checkpoints at matched NFE values. Backs the headline claim that the framework improves any 2026 SOTA flow-matching model on its native protein task.

Files in this section: 173

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_nfe_curve.csv` | 485 | `a7957efcc37e0a9e19fb0b192a5aa7994f50f03a625e10b9c1076e70ee527a4d` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_nfe_curve.png` | 150311 | `4a91790d7bbd0d2f35fea8e11453ec9360b313066578018007856abe1725955a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/cross_model_sha256.txt` | 4252 | `29e587b1812a30b5c6526b5916e9988dcae4f114e7f7743d085b8b5e0cdcc0a7` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/eval.log` | 51 | `525dc4dfc6c6fce66c526eeecab5b85f6c18bf7a5b822a244124ef0d84bbe3d8` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability.log` | 13584 | `0eb59bd9ddee8d82e68da63979f67f8d768b213e4f468ce541217a8ff231fb4d` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/foldability.jsonl` | 8135 | `b68ff37f0531b1bfd8237fb15a59ec046449fdc6883b71e190aa70c6e6f8b4d9` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/inputs.json` | 119 | `b172bfe7c3957a21e34a26016e54a821e592ff9cf2a92e415cdec30b8031cea2` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/metrics.jsonl` | 10481 | `ece3c28807c313fe8c78c2652a213f03ba3d9041fe769e98e035c732d87626e9` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/metrics_summary.json` | 297 | `8ce7e85f080421b521b0bf54c0fc43f242debe69326b86cbddf674cb535905fd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/queries.fasta` | 1539 | `b99659ed900c1036716f5733bf8ddb9c10fc98a6b7e4b4a2d91b07cc4520100c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/self_consistency.jsonl` | 5536 | `5c11dce95b7ebc88564639257e36d0fff490d25f220b98622716fa8c000c75d5` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/self_consistency_part00_gpu1.jsonl` | 5536 | `5c11dce95b7ebc88564639257e36d0fff490d25f220b98622716fa8c000c75d5` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/self_consistency_summary.json` | 248 | `ad28b354cc8dc785e2b9c74199cf7073e71dda32d40ab4bd20c918d479ba7c5e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/foldability/summary.json` | 244 | `2593778ca89980e4b56a981162574d2153a944de4baf7bd94189cf2c55a84b74` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/inputs.json` | 1534 | `c7d25d57c253db900b70b99364eceb72cf18c7005976898a40e2ed0f75ef1899` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/run_manifest.json` | 294 | `c64b452eba6327eaed36f16904bc9f09338d0fee87f5097cdd1e537d1934a007` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_100/summary.json` | 339 | `d3c2f572863366abef78d1ea3fd65aa0c2fcf3a320223405e7d1812466e86d17` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/eval.log` | 51 | `da75961a5354041c8d837abf57b45664be23a7e85664ec2ef58f7ae683601ae2` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability.log` | 13584 | `b3ac96f066f47e6bb334c50c442e3716da71905b0503d4e40a7ae3c0e07cb183` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/foldability.jsonl` | 8135 | `ad127e00a69a39f6669cd377c86467741935e86462fae7aa7572dc24735f855c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/inputs.json` | 119 | `c2db3787a61073c4f6637f808df671cba4546bc45a032667f427e8d62f4ed5d8` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/metrics.jsonl` | 10481 | `3c49de8439391b34487c347f8ca35c21d2c9630e2f640d92beaa0c67befa33bc` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/metrics_summary.json` | 298 | `a66bc8ae2abb2fc21abf3453a9d374f972462ea825d8a47e391ca6474fdf59ce` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/queries.fasta` | 1539 | `b99659ed900c1036716f5733bf8ddb9c10fc98a6b7e4b4a2d91b07cc4520100c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/self_consistency.jsonl` | 5536 | `6cd60fe2b1f2672eedb965d74e690960301c32f5eb9d29b5e3f5b274f088a938` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/self_consistency_part00_gpu1.jsonl` | 5536 | `6cd60fe2b1f2672eedb965d74e690960301c32f5eb9d29b5e3f5b274f088a938` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/self_consistency_summary.json` | 249 | `c07426d697bd3182bb1cfb99543fef1bb1d4d45591192168ca997c0d195a3e8c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/foldability/summary.json` | 244 | `2593778ca89980e4b56a981162574d2153a944de4baf7bd94189cf2c55a84b74` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/inputs.json` | 1534 | `d2a251d420225ed934f26160daee1668eabe0d6273db543c1b4e3cab6f60de27` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/run_manifest.json` | 294 | `88b37f189830e2ac34fefec94156601fc06509c2947502b42791bd518ee8a7fb` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_200/summary.json` | 340 | `cac0670d04a4416bfc4bd8c7589a3509eda480410a69b75073da175ac45dc85e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/eval.log` | 50 | `f27093cdaab55c91b952412bd990199de0936c6d2b65809384b24814fabb8124` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability.log` | 13508 | `ced4c8e4cc9d6ff2f6112f89963ffcf8a5dbd2e86efdb0a9384a611d9e7d8b75` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/foldability.jsonl` | 8105 | `d15fa29d73ccc8f45397eb0a94768eea479bc697c2b1ea868c48e5286ffdf236` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/inputs.json` | 118 | `ac11f8370b655a80934317b6faf2250670fb238047875d2982aa7029f49078b1` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/metrics.jsonl` | 10447 | `d223042047c029c0fa0a1234a9f89ea0785d070f4415f2b457889712b2ef57a0` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/metrics_summary.json` | 297 | `4c984a6f0120474a3ef394b7e2079dce91fd64e7cdb1022406e4909a76c45a6a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/queries.fasta` | 1539 | `b99659ed900c1036716f5733bf8ddb9c10fc98a6b7e4b4a2d91b07cc4520100c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/self_consistency.jsonl` | 5502 | `5e6b537b4f3f732b7c4ea3b425f685196bc1c77371f59643fc15a8613d789c8e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/self_consistency_part00_gpu1.jsonl` | 5502 | `5e6b537b4f3f732b7c4ea3b425f685196bc1c77371f59643fc15a8613d789c8e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/self_consistency_summary.json` | 248 | `06bcc879d651952527052ccb7ad236df2bbc06c07833bb851ce5304ca2eb6311` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/foldability/summary.json` | 244 | `2593778ca89980e4b56a981162574d2153a944de4baf7bd94189cf2c55a84b74` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/inputs.json` | 1533 | `0832f81263a07497247c90123257d3c2ce591ccda6ede3758bc8575b9345c53a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/run_manifest.json` | 291 | `bde8572e85f58e4197a7e695cd96a87a243a29ed457bb54b17f63033c141df77` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/kanzi/nfe_50/summary.json` | 339 | `81e8e4b79603d3295cade3bfc0db8425a45115791fa59b8ebb4165d8233c5614` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/eval.log` | 57 | `f937f62da8602878eff0059d46769018b26e65675db89a560d1b51ea80aedc75` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability.log` | 14080 | `8ff71bf9da65a69aca615c4a8bf56cbd6c3197d4ac55157e3418e25d637fad91` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/foldability.jsonl` | 8080 | `945e2048ffbeb59396e73a23f6f08b70b14f77469710ade8e03645aadde461ae` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/inputs.json` | 125 | `8d0f4ed731f4cee1c9f45f7191d4812c8a6c436378df75d65d808e78f414b712` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/metrics.jsonl` | 10431 | `0efaa2ae6ce6c5b5e8a36ba5ee49f0e7bd873e193ac61444c0ef82fd86c8a0cd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/metrics_summary.json` | 293 | `cd4c73e2ffaad90437c65be297c964f258698f975bee00e2987ae50dd661b840` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/queries.fasta` | 3020 | `2d8aa22e114b710e5e642e4dcd9853aaf60f4ef1b93283d4df5ace4ea3449f86` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/self_consistency.jsonl` | 5734 | `524e3316544f4305ae3d8945d4e23bad2220a199df60f7da7dcb4b753cb189df` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/self_consistency_part00_gpu0.jsonl` | 5734 | `524e3316544f4305ae3d8945d4e23bad2220a199df60f7da7dcb4b753cb189df` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/self_consistency_summary.json` | 248 | `9287f150ab5b84792918c7bc502cf8e9c9fb2ccab6cc68612f07d2401597c69e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/foldability/summary.json` | 242 | `706c2aa623bf16411b1261f3efe6045e9dc988689e26ba28e6908bb724bb5e4b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/inputs.json` | 1540 | `fea07eedb2b2b4bd58b9f6d8f20161fadc7518899937d240a0520a9706a0cfaf` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/run_manifest.json` | 312 | `940fd972f2f8696fff407cac5d9f9c009c11c24a81283b05d9ac01b33afd43fb` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_100/summary.json` | 335 | `381cbac2402ba0958cd7387ff9538660b66d3aa5d60b8379572ef4fc16f03926` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/eval.log` | 57 | `5108991d1c29f9d7aec52f02030a922dfabb92d03d48d7aec4cda939ee103e7d` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability.log` | 14114 | `7732396fd1ed607c293f13922b098bba6c4fdfa054c80e870e28f64bacff9643` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/foldability.jsonl` | 8080 | `e6542b4f00ff357d764584c5d4a67446e9472e1c9880dc3ab6573a0c1776ddac` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/inputs.json` | 125 | `fc09bb1729661379d7b1695a44f7544d58229c26613a416b61763d0244daa981` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/metrics.jsonl` | 10427 | `3e37ed0e5d69c4a2776a13b04a042882835f71725c438cf9ff3a1bb74e1e1967` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/metrics_summary.json` | 295 | `e55a8cc29ab93048467b3494dc7a80b55ae97a15fe3072fbbb235d07763dadb6` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/queries.fasta` | 3020 | `2d8aa22e114b710e5e642e4dcd9853aaf60f4ef1b93283d4df5ace4ea3449f86` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/self_consistency.jsonl` | 5730 | `f66ce21dc850dadce47ded8ef5fa95abadbfdbe22f1f86e57a9c4a467df64a49` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/self_consistency_part00_gpu0.jsonl` | 5730 | `f66ce21dc850dadce47ded8ef5fa95abadbfdbe22f1f86e57a9c4a467df64a49` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/self_consistency_summary.json` | 249 | `1b890c63e1b2470b796cdb838c310a5eeff34b7e976f01ceb5ed0e9b5d8d7f89` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/foldability/summary.json` | 242 | `706c2aa623bf16411b1261f3efe6045e9dc988689e26ba28e6908bb724bb5e4b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/inputs.json` | 1540 | `97e9a71e755df756273650f3789ea9c428b9acebb1ed6e9869b2deca27a5425a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/run_manifest.json` | 312 | `93f0efda73f76d84b77405bfcd4bfcc76f14bd5fb997fe766e2b6433dab3b4d9` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_200/summary.json` | 337 | `e2e6ce3e5a27547616a5f30e5633f0ef36a3f27fc80d0fbbd8c50d0f8c856abb` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/eval.log` | 56 | `c5439a0f4d112879a46ab150ed792170512c59888973df68ff7d90f37e0064bf` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability.log` | 14039 | `e7066dcc9ba802be03c48f4a8539fbe8590f86cba4dd07c0e7e76f09bbe21308` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/foldability.jsonl` | 8050 | `0026fcf79bb747827d7bb5e533e45191c9354d9939ca65ade94924ebdfa3ba62` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/inputs.json` | 124 | `66e16b0b8b5eb1b80d463e0a93dbce2f48f9065d3d0f526368504ad4b1dc338b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/metrics.jsonl` | 10400 | `56272a8a6fca18b7f39e51bc86443e4afe0dc883e12806f01e90c7926bdc4e11` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/metrics_summary.json` | 294 | `7e032f595822feb3aa1fa2e80abfaa037671269158eba36e96e21904361d4e5e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/queries.fasta` | 3020 | `2d8aa22e114b710e5e642e4dcd9853aaf60f4ef1b93283d4df5ace4ea3449f86` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/self_consistency.jsonl` | 5703 | `28a35454142191e265c7e970d225b48267483f128505f21cbbbbb4eb49eec601` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/self_consistency_part00_gpu0.jsonl` | 5703 | `28a35454142191e265c7e970d225b48267483f128505f21cbbbbb4eb49eec601` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/self_consistency_summary.json` | 247 | `e21a590796cd1afeee92a80528038abcb2fda948042fe0c0c8ed0a3e1701478e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/foldability/summary.json` | 242 | `706c2aa623bf16411b1261f3efe6045e9dc988689e26ba28e6908bb724bb5e4b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/inputs.json` | 1539 | `a8210220cfb97ad1ad046f2fbbbde058e14fc969a4af8d5673cb13a3d3af47e7` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/run_manifest.json` | 309 | `a001fa210524ac89db47fb558c77d2a4afc0359b75a226f728989b7ac3984964` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/baseline/lineageflow/nfe_50/summary.json` | 336 | `5fdbe3685e8dee190960a7f61d69d921ec8318885fe2d7fc860597b627b8f044` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/eval.log` | 52 | `96e6e0468b54648019837dfb57690b954879a55595bcfabfc2baa47ab201799a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability.log` | 13692 | `7d74e55f9b7f0a68c6fcbc70cae8af896bbcd1b8e2b38459a6dc833a47739a05` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/foldability.jsonl` | 8203 | `7ccacff364f13621bad48d256d6900a86197f4989b7697adac76c3945560633b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/inputs.json` | 120 | `10ec4187a4dd688ce056f263111c09dcb2fed09bb2af8ee75bfff87431b76c97` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/metrics.jsonl` | 10543 | `09374f12f1f188f2c548a1386d627d368233e0abbe02b8295f6acc5868f9cc3b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/metrics_summary.json` | 293 | `bc2787b4ee2657319da81320cac64957b39e67b089a3cf579d5c9f49374321b8` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/queries.fasta` | 1516 | `8aea6f7a96ce1d57bfd4ec354ff77e1524adfa4a60c0f04252bbf0044a6c48bd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/self_consistency.jsonl` | 5560 | `55aa180660eca3b02fcbacbda0d7993d1db8d2008ffdcd1aa8e2387d8ab59279` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/self_consistency_part00_gpu1.jsonl` | 5560 | `55aa180660eca3b02fcbacbda0d7993d1db8d2008ffdcd1aa8e2387d8ab59279` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/self_consistency_summary.json` | 249 | `12074dbf01b197e55e2160eea4f686854ed5956e00fc30aef6af04e91a0238cc` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/foldability/summary.json` | 242 | `87578d7cb6218cc92e593813a599790994d0094121d25b54945ec95887d4e738` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/inputs.json` | 1535 | `24e7273c83aed830a5cde036666aed238b88c76867030c330b42bf5fecfdfe16` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/run_manifest.json` | 297 | `32f04dd3404b5e8505aa6819cfb84bcbc4961e51967b700691045399d78ed2f8` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_100/summary.json` | 335 | `15bd2ceb6e53cc1068b6f39e84fa9a3c83cfa104e9fb35bb9d5b53b8598aad53` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/eval.log` | 52 | `1c3780ae18beea5e718563c0c869dc20e3702f03101cc30878c116e321b03e61` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability.log` | 13659 | `abf3be8aabc2677346e753294feb5a34d545a6cbaaca9f36e3e645647793dd5d` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/foldability.jsonl` | 8203 | `ddbbe946fe88f6cf511006a76c2b41cc4f24c4a0d1fb5b570898a490e2f3272a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/inputs.json` | 120 | `273ee99f4b6e673226a140e588bbc8fa30c9aae3249e2b06fd98ea4939dcc81b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/metrics.jsonl` | 10549 | `d1096fe369eba75bde1024b6e9d640c0fcd0938aa5d4b7b899dd8f0423e938ea` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/metrics_summary.json` | 296 | `de74ad73f3613b3aa8dd35a8499922a4dc71a1cdbbc8580c0f934c5f53d633ad` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/queries.fasta` | 1516 | `8aea6f7a96ce1d57bfd4ec354ff77e1524adfa4a60c0f04252bbf0044a6c48bd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/self_consistency.jsonl` | 5566 | `3324701204111aa55ba66d87339de809ea7179ad2e82d1ca6638339ea8ea654f` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/self_consistency_part00_gpu1.jsonl` | 5566 | `3324701204111aa55ba66d87339de809ea7179ad2e82d1ca6638339ea8ea654f` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/self_consistency_summary.json` | 248 | `2c7eda26cecc18d887ce748465c09771e5944aa0eb7e67f6a61581f3267e2b19` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/foldability/summary.json` | 242 | `87578d7cb6218cc92e593813a599790994d0094121d25b54945ec95887d4e738` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/inputs.json` | 1535 | `89dc373453b63a42b99284b0ea3db2482f909e9499cc226dd77f927ed31b8272` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/run_manifest.json` | 297 | `86a7894f7118389357c8cdefba49d922068e6f8eef61db37e100f6a1b3374f38` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_200/summary.json` | 338 | `1dbc03018e9e5a014ba2817cabf17cb12d199137c6b12e4b33ba89df28eb8540` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/eval.log` | 51 | `abdf61cdee7f2d5a898e5b19499f69dc27868e2c69151ddaff23c076820acc08` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability.log` | 13617 | `565a35de31a94e1946710cf6aa4557cae79d1509f2d09f21a770bbb2078e9592` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/foldability.jsonl` | 8173 | `22ab22a5d53ae93f1ae1eea373c30ba4cc9f87336c7c5eaedee9912a91aac1be` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/inputs.json` | 119 | `8f58d7b4f51bf6cb9884862d109222686488a71c9cba8797d7562a137cf5f805` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/metrics.jsonl` | 10515 | `a8ea02df35a899375e793ccc48d67a51ae36516a5338ec9ee1a12c20779aeff8` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/metrics_summary.json` | 295 | `648436f9a293cca22ee04a2768e5f2e7dbb226f23038d05436e4cf6d8a3f7be3` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/queries.fasta` | 1516 | `8aea6f7a96ce1d57bfd4ec354ff77e1524adfa4a60c0f04252bbf0044a6c48bd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/self_consistency.jsonl` | 5532 | `62830010cfc14b0d9569ef4dd646db40c44f075a445c97ad74077001964b8735` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/self_consistency_part00_gpu1.jsonl` | 5532 | `62830010cfc14b0d9569ef4dd646db40c44f075a445c97ad74077001964b8735` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/self_consistency_summary.json` | 249 | `01a16d71f78299653b5adb86e5f7418ae0a091ced14126e91e7e53d4d341f23e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/foldability/summary.json` | 242 | `87578d7cb6218cc92e593813a599790994d0094121d25b54945ec95887d4e738` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/inputs.json` | 1534 | `058f6a83b81fc411a3de56f6c17e0f126ae8ef109e33fbe030716c37f5158330` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/run_manifest.json` | 294 | `540eafece1e93255157da25a40707ce2d20c55fad8f9b7e7cdbcbe1fc6f7efad` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/kanzi/nfe_50/summary.json` | 337 | `da4696978de3d984131f170d25dd85acceb06350dbe002c0a9785ee078fef22b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/eval.log` | 58 | `f9af3b2d3e24f112d8339646fcb40765e4900c083103dee2846c17662b0c0c58` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability.log` | 14187 | `35481e6636b566f742990e67622abebd6af902de1065a8be70d4263f014924c9` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/foldability.jsonl` | 8107 | `c7df603639e7e2de523131f3ebc0ef14a3d11889ae8a5717866a473974936863` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/inputs.json` | 126 | `4925c117c8744c999e520e97bd7c8432cd4a45dcb4c70568523532862df13ddb` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/metrics.jsonl` | 10454 | `83257bf99cf3e5588ad660fd066b0eafbb60443c29528dddb14cf088a34f605c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/metrics_summary.json` | 297 | `53753d9da0ebe1262b96c308bb99c67ba3005334685b216e6b43c5284688a134` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/queries.fasta` | 2666 | `fc44c98c55e5411fb774fcbade33c8c3b1da0a8f91f8a94aa12d9982b6d84279` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/self_consistency.jsonl` | 5758 | `ed7e3b7684eb8ef52c496820fba5c5162e17fb27d7cdf3b88b9d287625b0c57b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/self_consistency_part00_gpu0.jsonl` | 5758 | `ed7e3b7684eb8ef52c496820fba5c5162e17fb27d7cdf3b88b9d287625b0c57b` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/self_consistency_summary.json` | 250 | `04e3c6e579597b07bf345a254c5c8318780282d3ff807c9f484a6cc8df950c62` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/foldability/summary.json` | 245 | `204abedf24f4e07f617852d9bc7a68ca3c2a7e89aad0cc7f98ec3dd38604bca2` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/inputs.json` | 1541 | `8dccbcdea1d2a20023bef9fdcaf5df7b6a6d8acbcaa937e4326e7260ada33604` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/run_manifest.json` | 315 | `bf9a8063ad587ccc51533bc511306c11b3e2f5ace7ced53075b5d2e7e934366a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_100/summary.json` | 339 | `eca3668ef3de90fd3f6bbb6b0e23b409594584c8a2f833bdeeeabafaf5e7eb4c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/eval.log` | 58 | `1f369772b3ab530ccefc8015feac400283bdbe569a34d62a5c1ba258897a4a1a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability.log` | 14187 | `cc39002c98e2e3aac5afc47e2ee9bb7e497753da527787fa5dc403baf0e4555a` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/foldability.jsonl` | 8110 | `34cd9edf3794f52954a5cd951bbfd5c884610b8be8ecf2c9bb89da270aa04666` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/inputs.json` | 126 | `07585606c5c024f356388c4c1ce837016c1f2c67527878819fababd6b3fbbde2` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/metrics.jsonl` | 10459 | `594ef1a5672510f681381a12dc6b1875e9512319e9b253fb77ffae3837e16824` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/metrics_summary.json` | 294 | `29aafd2f355a545d9f7e444f85e4fd686d4e52a9944e478a4e1ef205085e5f71` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/queries.fasta` | 2666 | `c9207df16200591a583189ecf55f81b5b943eadbf86a7104e95c1b7c55e6350c` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/self_consistency.jsonl` | 5760 | `144c3926d4d57ed6ac98137ce4301d4f00dc135926ef21c17443f4115df795aa` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/self_consistency_part00_gpu0.jsonl` | 5760 | `144c3926d4d57ed6ac98137ce4301d4f00dc135926ef21c17443f4115df795aa` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/self_consistency_summary.json` | 249 | `7ac0f9df831db38101c9185e6e472e6f53f105eeb37b1e12a39e7907792c8c3e` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/foldability/summary.json` | 244 | `69638f621bf9a619c87a43ea54797e0404f078a5fd99999c33198bbe58f9e464` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/inputs.json` | 1541 | `380f8171e4f48d84253dd39efcc353972558311d0d1a7624f164f2d382dc8dd2` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/run_manifest.json` | 315 | `50cbd5b1d37693c6715595e71b2c31af10c9ad24de1931f182a3b4471a51ba86` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_200/summary.json` | 336 | `71ea7e93943ef0e43759ea121c7b170530ad4c59c3a4e8599af21c9f3a8ea007` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/eval.log` | 57 | `596a952f0a481198dc638a5d909a4cd6ca8dd11757bd9804f155df4bc59a4ade` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability.log` | 14045 | `0d58ac71c7f6c718c7e6a20354c1e9566a0c866a57f4c0d4b8284dedc29ca162` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/foldability.jsonl` | 8068 | `57c28486d5643b97bf75a647ea398cc607358e5b69ae348b1f22f0420f40799d` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/inputs.json` | 125 | `2c35d7da0b24f7b33684cebe90dfb9a5151298dd5d76462e09fe9ea1c039339f` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/metrics.jsonl` | 10417 | `8b7cf161f46e7612967482568109a3d77c8c1d6479f225cd2260de9b0e1d6846` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/metrics_summary.json` | 297 | `225cc87c1239416ebf4efc2fbb75b1484b7f20ee6b675ded48b6e644d3b019e7` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/queries.fasta` | 2666 | `06a30239eef8b17d7e08c137ed744c8693916d86bbad4ab9dc6cf16255595bad` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/self_consistency.jsonl` | 5730 | `049bf89723dfc755761042595ab7497831dc7ab0c38835413da42f64140ae2ba` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/self_consistency_part00_gpu0.jsonl` | 5730 | `049bf89723dfc755761042595ab7497831dc7ab0c38835413da42f64140ae2ba` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/self_consistency_summary.json` | 250 | `a224fa42ca79d7c7664104bd944fe22f1bbf24949ae193359cba5e648aa4de40` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/foldability/summary.json` | 247 | `c3e2e7de6c0997637708be7c30016a8c891bce7e298294572a6ffedd66498afd` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/inputs.json` | 1540 | `6b8dad146c8ddc5d4ba5dfc2f2484e3082471e73fb4788788d4585374976b591` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/run_manifest.json` | 312 | `4bfa096939f81f0cc50db56d84b4b353a2fe75c5b0298ccb967d406ac33e6352` |
| `verification_outputs/cross_model_real_ckpt_w172b_q3_2026/raw/eval/framework/lineageflow/nfe_50/summary.json` | 339 | `cdc69675027e2ad43ebb1716ccc12cf10673cfb0c7e5268b44be6ed3787a12da` |
| `verification_outputs/nfe_curve_fair_w170_q3_2026/nfe_curve_fair.csv` | 460 | `cf135c9ff1e1fc052d67abefe330f6df3e8113bdbbf695ad86c2659456c7cb1e` |
| `verification_outputs/nfe_curve_fair_w170_q3_2026/nfe_curve_fair.png` | 88532 | `2e6a7e5cf743299d77e4393d5bf804d2a62bfc249d65a7612391ba9a04347455` |

## R5b CIFAR-10 RF

R5b CIFAR-10 Rectified-Flow N=1000 paired sweep at matched-NFE=50 (4 rounds, n_rounds=1 effective). Backs the CIFAR-10 RF headline: per-record FID, paper-metric aggregates, per-arm summaries (baseline vs cosine, codimension sheet, evidence-driven, free trajectory), plus per-round metrics and inception-feature caches.

Files in this section: 52

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/cifar_n200_nfe50_ema_corrected/comparison.md` | 1734 | `e51720f3f872e142b95912264107340105be70bd503c8a68bd3dcb48ad0a617d` |
| `verification_outputs/wave175-p3-sanity/baseline_summary.json` | 338 | `90947923154ed2a51c2e8e227ed12add5e63a2e750b9bba4591caf11d2cb60fd` |
| `verification_outputs/wave175-p3-sanity/framework_summary.json` | 337 | `07d91a0bd7060f324ca532df40d012570c56d8e9e6ce80fe1d33b62c1a803a02` |
| `verification_outputs/wave175-p3-sanity/manifest.json` | 738 | `26905450f0a96f8df4ee99cca44ef9fdf2042e4b42f2a2e39ac4376d70238333` |
| `verification_outputs/wave178-p6/baseline_nfe_100/eval.log` | 50 | `427cb107c5df31b48be0a6d1b9751314ba9fe4c50cb65d5b7a6f6f193e370c30` |
| `verification_outputs/wave178-p6/baseline_nfe_100/inputs.json` | 1536 | `c489337e5fd95561fe52943dc378a32de92da3b3b48a4edfbf9293cfe3dd225d` |
| `verification_outputs/wave178-p6/baseline_nfe_100/summary.json` | 335 | `ba83d754a71c21f4772f84a3f3e6dba845273f93d14e5e0fcea59dea3f5c6d86` |
| `verification_outputs/wave178-p6/baseline_nfe_200/eval.log` | 50 | `f6fe2c06fb6f0532f577257c6144ff89f08df13db869135f3efcaede53e3fb41` |
| `verification_outputs/wave178-p6/baseline_nfe_200/inputs.json` | 1536 | `c305c101bc3b00b96ca29f4abaff2a314ffd34c7bb1d9cce344df69c4911b09d` |
| `verification_outputs/wave178-p6/baseline_nfe_200/summary.json` | 336 | `8af0e1de7e99d42d59a1b63bc00f1915e3e3f0bc013c8faa41fb0dc68365471d` |
| `verification_outputs/wave178-p6/baseline_nfe_50/eval.log` | 49 | `3ebca36761626fcab69219a5132c3b4131be0adb658e037ce32e8365919f766b` |
| `verification_outputs/wave178-p6/baseline_nfe_50/inputs.json` | 1535 | `8cabd7791c7995764318e243a2f348c18615746a6aa072ac8b356e09fdf07eb0` |
| `verification_outputs/wave178-p6/baseline_nfe_50/summary.json` | 338 | `37c1cb1d9e839599733e4ef4d94508881d3a7d4c12bd20cde9f7ac159438de74` |
| `verification_outputs/wave178-p6/framework_nfe_100/eval.log` | 51 | `8a1775a4e1f9d12f1b572a499facf23e0991d239e8c43b1a2f0d720f279278dc` |
| `verification_outputs/wave178-p6/framework_nfe_100/inputs.json` | 1537 | `cce59b2bfb6344aa5481a6a2cbb82f6629f9472d072dfafd84296a3ff9f90f11` |
| `verification_outputs/wave178-p6/framework_nfe_100/summary.json` | 338 | `5ade2f60978f24396710db90e40f6b28df504a677982d15d090ccaec26100bda` |
| `verification_outputs/wave178-p6/framework_nfe_200/eval.log` | 51 | `492735cabaa7f6dc9a192015cab8cdadb34bb64212e26ff83cc2bd79db373e56` |
| `verification_outputs/wave178-p6/framework_nfe_200/inputs.json` | 1537 | `d022312f2fbf0fc45c6f5ff65dad96569a9311317d4bc7abddb52edb37f550a6` |
| `verification_outputs/wave178-p6/framework_nfe_200/summary.json` | 337 | `615ca10fcc06565d6f9c16a8a3fe071b116a0014380421ad1a3e649f9304bc9a` |
| `verification_outputs/wave178-p6/framework_nfe_50/eval.log` | 50 | `768295204aba77fad88af2b77d3e8deeab5f9e3e267d8766eeb7f62761e93c4c` |
| `verification_outputs/wave178-p6/framework_nfe_50/inputs.json` | 1536 | `4bff145069b969f5f9bb9fff5340081c44927f99969903bb61c4221129c73129` |
| `verification_outputs/wave178-p6/framework_nfe_50/summary.json` | 338 | `7480a92076a632103c947748480f08db709c80a165cfcf20c9d8513ae155dfcb` |
| `verification_outputs/wave183-p3-eval-summary.csv` | 4683 | `64d2746d06b83292bc43cf2ab68442c7a6e23546cbbc1889482b21a69ac23a61` |
| `verification_outputs/wave183-p4-aggregation.csv` | 3010 | `b9627e1a63b1e30f30bfe68a408693be6fe78c4f424d4c15e3a48f85717ec5a6` |
| `verification_outputs/wave183-p4-figure-deltas-finer.png` | 144560 | `1412578cc63add7a33b98d7c25be33a032febea69487ef3cdd683c28c510eb9f` |
| `verification_outputs/wave183-p4-figure-pLDDT-finer.png` | 146117 | `0ac80722b7063f4acf2f73880a99593a1d52da9307157def93c825c9f9f809a0` |
| `verification_outputs/wave183-p4-figure-scPerplexity-finer.png` | 133574 | `f590c0b8ac6b82a17e77b6a21e28aa07b140e659ef6daec963298d0efbdeb961` |
| `verification_outputs/wave186-p2-cells-summary.csv` | 2454 | `00ce030a2fa22d89a84ad04faacddbe74241803f08d97f0b2bd5098678eac074` |
| `verification_outputs/wave186-p3-eval-summary.csv` | 2211 | `1f6602e08b1ffa69ac27fdd216ec117b84892d5ea461589a671c57d782015894` |
| `verification_outputs/wave186-p4-aggregation.csv` | 1090 | `7eb2ddc543bceaf775a17847ef966eae5c5a06e1a738d42c27c7796a3bf62c47` |
| `verification_outputs/wave191-p2-cifar10-n1000.json` | 5267 | `a3c5bea08e44018eabaa6e8332ac7de211de70f48607cf983143b87302d5b0dd` |
| `verification_outputs/wave191-p2-cifar10-n1000/baseline_inception_features.npy` | 16384128 | `1b1d75db1940c573b92e2b53e18305a96bf8c86b39f18f117db84ef7978179fa` |
| `verification_outputs/wave191-p2-cifar10-n1000/baseline_samples.npz` | 24576268 | `f87247276fb6850313b091485af0962d43397654626db74c1be8e9b4163b0e96` |
| `verification_outputs/wave191-p2-cifar10-n1000/codimension_sheet_inception_features.npy` | 16384128 | `e650731681c61ee0c0e0e4030242839fc1fb089798a65903cba231759abf69fe` |
| `verification_outputs/wave191-p2-cifar10-n1000/codimensionsheet_samples.npz` | 24576268 | `49f22d5543b31fa2259c6be3287122531289a1debd90d0aa490f0876a2df67f1` |
| `verification_outputs/wave191-p2-cifar10-n1000/cosine_inception_features.npy` | 16384128 | `fd8c35a4ca2168563efa171090daa5ac9c8d481e6a6e52108b50d69f4cad9346` |
| `verification_outputs/wave191-p2-cifar10-n1000/cosineanneal_samples.npz` | 24576268 | `ff2b1e822d311925f2a78bc590019c247f3b2bca3cdacd1530e9fa9bc391f062` |
| `verification_outputs/wave191-p2-cifar10-n1000/evidence_driven_inception_features.npy` | 16384128 | `c513ae8968df5f2d55f3d57adc7ea976d42b1dd5e06e6c2a24c040713ecd957a` |
| `verification_outputs/wave191-p2-cifar10-n1000/evidencedriven_samples.npz` | 24576268 | `252a71a96d64a09867703db7b2e04e3687feb828f08828ad06580ee24c0a05a6` |
| `verification_outputs/wave191-p2-cifar10-n1000/freetraj_samples.npz` | 24576268 | `ac68231c7f0628ee38a9bf279b0ab8204e8f5c85536eb48706aa851a2592e806` |
| `verification_outputs/wave191-p2-cifar10-n1000/per_round_metrics.csv` | 714 | `7b0f99e18597b2f1358c6244e9dcd4d15a9cbb664c7965afec2b0d7f5fadc17f` |
| `verification_outputs/wave208-p5-pareto-r5b.csv` | 288 | `65cefe0c458cbc045b1452240c80514e19cdaa04aaad4b173ea2fc60ea4884ec` |
| `verification_outputs/wave225-p7-r5b-reduced-rounds.csv` | 1717 | `702f7b32cc13b6761de3537bbf74301333f0af8a521d8bd40625f880f0f0a676` |
| `verification_outputs/wave225-p7-r5b-reduced-rounds.json` | 3591 | `f22f57d9f3f42a978f748e3d4379fce42ff34ba9a54fa70c35c6ad7a80683a0a` |
| `verification_outputs/wave225-p8-pq-weight-tuned.csv` | 8314 | `6c469800222bf8e11dbbf8239e615fb414df13dae1811fecd8ba4ce2d4ae3a9d` |
| `verification_outputs/wave225-p8-pq-weight-tuned.json` | 20478 | `8f40f147864221ec9e0750a05dcaf42a3e03cc992201b2c366f353cfe391a441` |
| `verification_outputs/wave226-p1-a-g-sensitivity.csv` | 997 | `ce5db961b49b9252987d94a6b747c7c3b608467d39b75282c64b6f325604f175` |
| `verification_outputs/wave226-p1-a-g-values.csv` | 4192 | `d5f78e860c3a11f0c2c7e3b837e4c1dbdb8fa24724d095176d3df403ef0a7af8` |
| `verification_outputs/wave226-p3-per-seed-variance-bound.csv` | 2675 | `8b10e2c224640cb1ee82edcfb9e2a114bb0e4d7976d0adceb4dc891f2f8d9aa7` |
| `verification_outputs/wave227-p2-floor-corrected.csv` | 2559 | `fa2313105bbb6e36f4e93dbe57a368a7fc004f76fd04863ec94f689ef624d4ec` |
| `verification_outputs/wave227-p2-floor-corrected.json` | 622 | `0e551479025001ccd6097092edda07fcbbf5a9631a0b470881ac928ed4ab0060` |
| `verification_outputs/wave233-p5-r5b-fix.csv` | 737 | `32d72a9bf00b3f7e9a2d27fda34866c2582a00959a950f232484b24e96e86106` |

## R6 MNIST FM tier-aware

R6 MNIST flow-matching tier-aware N=1000 paired sweep — backs the R6 headline that the tier-aware scheduler produces monotonic framework uplift across difficulty tiers (hard/medium/easy).

Files in this section: 24

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave191-p3-mnist-n1000.json` | 6444 | `a5270a0aacc99551c3ed15304f00d68baa41ac3f6012e3ad26f2dbbe96dc5e06` |
| `verification_outputs/wave191-p3-mnist-n1000/baseline_samples.npz` | 3715325 | `f7eb8c3536426c70faae951803fd84814bdb3900aed5b7adfebd537e6c3fe290` |
| `verification_outputs/wave191-p3-mnist-n1000/codimension_sheet_samples.npz` | 1766754 | `eb6cf305d88c536ba223844ccb08208ae3c797a972b93d6c6a12de77491aeeac` |
| `verification_outputs/wave191-p3-mnist-n1000/cosine_samples.npz` | 1783301 | `6b44d91efb097d7456d39f7151c851a7d477ba16a53b0aef0e0333b1f90baa45` |
| `verification_outputs/wave191-p3-mnist-n1000/evidence_driven_samples.npz` | 1776876 | `be0d58de1e91d972fa03b01e0477bda5065534870cd09079f7c468b8bf698327` |
| `verification_outputs/wave216-p4-r6-uplift.csv` | 1501 | `3f0b8210a265e22a9df78cd799c569b0d351846cec6dbad743d7d06981dbc7b6` |
| `verification_outputs/wave216-p4-r6-uplift.json` | 7250 | `9bf0d5f5761bf6db7365ca1aa8e13244b691ba7a0a9985b7599e954433d89dad` |
| `verification_outputs/wave225-p4-k6-tier-aware.csv` | 1314 | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `verification_outputs/wave225-p4-k6-tier-aware.json` | 9728 | `03edaa21fed42bb4e267bfbfb403913c4289d5c03f67d06276424fe5a763dadb` |
| `verification_outputs/wave225-p5-kanzi-tier-aware.csv` | 1163 | `04ab988d7ae69c0d81ef60865613cb34d2041e530f127abf8a1e16f89c245fa8` |
| `verification_outputs/wave225-p5-kanzi-tier-aware.json` | 8813 | `a65fefced803d31557766aa0346a2b48bdcf287d7825d8ef023dcafcb2f7f635` |
| `verification_outputs/wave228-p1-4arm-per-record-coverage.csv` | 5113 | `04277c8b85713bc7cc3cbab1b267386f42e96a9d5605c7f7347cdb142f20bc97` |
| `verification_outputs/wave228-p1-4arm-per-record-coverage.json` | 30227 | `f36180be73173a91435342c60ee7aec29803a888ef73a6d59796f93fb1021d1a` |
| `verification_outputs/wave228-p2-paper-quantities-distribution.csv` | 698 | `7113cc8ec35adaa228ee32918e518bfa2f3b048577db6d67ada470c6276e02f1` |
| `verification_outputs/wave233-p3-tier-aware-r2.csv` | 1163 | `04ab988d7ae69c0d81ef60865613cb34d2041e530f127abf8a1e16f89c245fa8` |
| `verification_outputs/wave233-p3-tier-aware-r2.json` | 7931 | `7cefbf379df43d1e47d6180bbc77f59f468e3029c221cfc65a67118b2555dd66` |
| `verification_outputs/wave233-p3-tier-aware-r6.csv` | 1314 | `634d9f03c77a7ee95c860b8099dab42dfe6aa9b99cec8b332df9603c32e8ad32` |
| `verification_outputs/wave233-p3-tier-aware-r6.json` | 8589 | `9a0c3eacc847c29a2844fb2ce4dc36f94def244ecbd4b4978fc0c1deeaf15851` |
| `verification_outputs/wave233-p4-r5a-expanded.csv` | 10023 | `55b65b67798c00660b64928f5e7db467f2b7e4f1bcf1ef23f1ed3457eddd9227` |
| `verification_outputs/wave233-p4-r5a-expanded.json` | 6391 | `56bcbfb1190287d7b101bc388740b3fee03032d09c0a2ce60b3cc9d4b7362281` |
| `verification_outputs/wave235-p2-r2-uplift.csv` | 4252 | `3041c9da28ee90d5d4bfa23fa98dedfd42e172b81d419d7046f44afeee5615e2` |
| `verification_outputs/wave235-p2-r2-uplift.json` | 13636 | `9458748eb571fecec92e85ab8f05f50ed46225d82e45cb756167c1839bc9640d` |
| `verification_outputs/wave235-p3-r6-uplift.csv` | 3939 | `a3397fae974aff1c9fb6dc75d6b7115a94dbad1ee4a16d85fe973520819a95c6` |
| `verification_outputs/wave235-p3-r6-uplift.json` | 13843 | `9a9dff1867efa54c8f542c86dfdb7f12fb18dd2998827b82fbd52769c3cc4030` |

## 4-arm H2H (real checkpoints)

Real-checkpoint head-to-head comparisons of the framework vs abcache, fast-dLLM, lediflow, and vanilla — paired per-record summaries, power analyses, ablation tables, per-arm data dumps, mixed-effects regressions, and difficulty-stratified breakdowns. Backs the framework-vs-baselines H2H matrix used in CLM-039 + paper Tables 2-4.

Files in this section: 51

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave180-p2-fastdllm-summary.csv` | 1181 | `29ba8103aa8d6347a771b52ae4887ae8d610255fbdad937b5d178614b7227606` |
| `verification_outputs/wave180-p3-three-arm-comparison.csv` | 245 | `cf85ed6979418e41e3ca72c56190f22de7894b190741ca57deb90e80c77d9299` |
| `verification_outputs/wave181-p2-abcache-summary.csv` | 1002 | `5150e822df608f4a6d7318fc2bf24a7952e36b2f3d46a4f5e98b52161085b45c` |
| `verification_outputs/wave181-p3-four-arm-comparison.csv` | 308 | `0c0025d1cf420551d0e1fb07103985702ef2d23a2fea04fc42185a2f77acec6a` |
| `verification_outputs/wave182-p2-lediflow-summary.csv` | 992 | `012f12998c28ff06d0f2cd1c9c859c62cdfc4953b5458c992481da99e5797287` |
| `verification_outputs/wave182-p3-five-arm-comparison.csv` | 371 | `6cb9739cf8870eee9858e633d50ee860d9f0feca3f23a0c85aa319744fcac662` |
| `verification_outputs/wave184-p3-eval-summary.csv` | 1791 | `df79067fc903cae62d7e7bc28355c6c50086508f8ee555c6ed12a8def071f75a` |
| `verification_outputs/wave184-p4-ablation-table.csv` | 1178 | `2bf352659bd4b6c388c784b8db43211e1932bc673dbb3acf6bf396b34877f5a5` |
| `verification_outputs/wave195-p2-r-level-power.csv` | 2438 | `985b071f3b34facda589f8997e742f44f3fe068b035ae30d5ce66295d21111e3` |
| `verification_outputs/wave198-p2-audit.md` | 8775 | `a3ed3c05be14b881e9b3900bcb0238585faac841e49ef68813c4529d643703c7` |
| `verification_outputs/wave198-p2-per-record-paired.csv` | 635 | `3d25b0b9c2becd3aef9ede0b190656aa1c83be460191b6d62ebea1ae65a4dd2c` |
| `verification_outputs/wave198-p2-per-record-paired.json` | 3808 | `66c03d9362a5ca5528f916f4c4ab70709d4dc0ad5cbdd2bff28332e343a2a0ec` |
| `verification_outputs/wave198-p3-audit.md` | 9641 | `13fa606f6808b4941349568e318294d93c0115a3a07650bb4b9bbcd5c4afb7b6` |
| `verification_outputs/wave198-p3-difficulty-strata.csv` | 2581 | `d989a97b91cf9f160744d2bcb31db6f0bdaad00a1c713ce6a0c671d792c48d58` |
| `verification_outputs/wave198-p3-difficulty-strata.json` | 9991 | `4eab523b07e8af47ecdb8b6bbf8be5c4dac9d5e6f3a9dd1377fd7a532172104e` |
| `verification_outputs/wave199-p3-audit.md` | 4598 | `dc6cad16e621a05b1befdb9e3a995dfdf3c9569f14825d48de42672af7734f9e` |
| `verification_outputs/wave199-p3-lineageflow-per-record.csv` | 265 | `63a9be82701beb3cb372c97f1d2a78c53816186fd2bc4dd92f9d048412dafd64` |
| `verification_outputs/wave199-p3-lineageflow-per-record.json` | 1962 | `1a36d16d1d69ce1a42daf78aa2a040f9c5e5df4e889a8aaa516dfcf1cdec66d4` |
| `verification_outputs/wave199-p3-lineageflow-strata.csv` | 893 | `78d78998f7487265d1bddca8ef208d6f9182f84db428e62b5c8924c702c35d21` |
| `verification_outputs/wave199-p3-lineageflow-strata.json` | 4738 | `e4085a5148d8fef34d22ffb9ac8343837400fcc8b7076b0d0cc478bf7f39ab9b` |
| `verification_outputs/wave200-p2-lineageflow-n1000-baseline-gpu-blocked.json` | 6486 | `30d0a4348760fa5abafd75c157e27c9e619d27225b576bf99f51a6af005a58b8` |
| `verification_outputs/wave202-p5-lineageflow-per-record.csv` | 481 | `ea6beba57f9807a1a850107abaf3eee287879eb26c120572840d7f6fef0bfe83` |
| `verification_outputs/wave202-p5-lineageflow-per-record.json` | 4260 | `4deed22ae6a00e10d517d8822a9928297bbf583b9579ee20c199dd12ac8cf092` |
| `verification_outputs/wave202-p5-lineageflow-strata.csv` | 1017 | `0049415d4f526126f8f192a394a8498ea31258bb0c5e3f40cca4bc031dd7eeb0` |
| `verification_outputs/wave202-p5-lineageflow-strata.json` | 3228 | `53d6776d852e21d47a41e148b9aed8db0edaa45c4313c7711a52e131d7201a27` |
| `verification_outputs/wave203-p3-k6-cluster-robust.csv` | 2983 | `156bea91265685cc88397909144e6d9ed619c9c4150344fb0fc6e41ce96bfeaa` |
| `verification_outputs/wave203-p3-k6-cluster-robust.json` | 22637 | `ee02b64b4ceaa93ea12ff4fc3296ecfd67d6690b673addcfcd6cc67361ae36af` |
| `verification_outputs/wave206-p4-r-level-refresh.csv` | 2480 | `b6706ebb935b5aedb3a1d953ac7caf4763038576cfbd8303d984ed3ac8c2d12b` |
| `verification_outputs/wave206-p4-r-level-refresh.json` | 9599 | `4198e1c7aff48063f1a02516adf7fec9f75c0b9831ae7ed0bb84c8659ce38111` |
| `verification_outputs/wave206-p5-freqflow-n1000.csv` | 483 | `59e059f745cc03a2dc8b884a0177cfbc19aadf03e893d97dd97b6f2b087ef7bd` |
| `verification_outputs/wave206-p5-freqflow-n1000.json` | 436630 | `b731e8dd4af510c6980a938ea5c57d021e0ad724908ff5803dd4d43543d05631` |
| `verification_outputs/wave208-p4-cross-adapter-ablation.csv` | 2845 | `1cc216aee6b04b44e0f332c7eb9b35b06dabacb5732fef5c997e6d764ea3f876` |
| `verification_outputs/wave208-p4-cross-adapter-ablation.json` | 11599 | `1fde8d7f8ea03c65c12ca8e9e7426c6af3de7f1a3dbfd99aa98ee2134842b3c6` |
| `verification_outputs/wave208-p5-efficiency.csv` | 4011 | `1a89ed6456281078a39f32ee09c507c6b46c166114fa79836a68f9dd71cfe766` |
| `verification_outputs/wave208-p5-efficiency.json` | 10280 | `86b6dea0c6682d944183f4339c2f1832d189ab143923f8a4bd4d0567b21c1547` |
| `verification_outputs/wave208-p5-matched-compute-definition.txt` | 1907 | `4485efbd4b1fc84631d61d09efa086459fcc83fc7261528d87ceacc94073c4da` |
| `verification_outputs/wave209-p2-cluster-robust-all-cells.csv` | 4042 | `5cdb1ed8f5f7a07add6a825a607df992bf481c275b8c1320f970510bb2bf7480` |
| `verification_outputs/wave209-p2-per-record-all-cells.csv` | 3856 | `10a8bd0f837d10a5fa6b7f681b0486209b1ab5c65d24d701fde495349d900933` |
| `verification_outputs/wave209-p6-r5a-extended.csv` | 2331 | `c7c17275cd224671d3e8fb03b34513339643932f54da37f593c69681b0912f8a` |
| `verification_outputs/wave216-p1-r3-per-record.csv` | 1483 | `faa3943d481f571dc47a8d57fd7648d8ad2712c3f01a0230d78f11e0c1818081` |
| `verification_outputs/wave216-p1-r3-per-record.json` | 4806 | `579504764e27bb7d2e119254fb1491ff56589773c6b4923abba5f4063af4ca38` |
| `verification_outputs/wave216-p2-r5a-extended.csv` | 4881 | `3df3b09cc33bafa550e21f99747ad420ffe5d14c7829d18714c58d94ef699686` |
| `verification_outputs/wave216-p2-r5a-extended.json` | 2080 | `1e7b271dfa2825cf08ddeada5b60b6cd2745898a3d10079acefa4175109363bc` |
| `verification_outputs/wave216-p3-4arm-per-record-equivalent.csv` | 5320 | `42b9f81bc7322e4b344a2d5a9d62aa8bba81c66179a69b3fb30c5b62571ef2f8` |
| `verification_outputs/wave216-p3-4arm-per-record-equivalent.json` | 26824 | `d6b6dc45e1a3fc1591402cda98b16bed1872f7f9eac58f31b5c72f569dcfeaf2` |
| `verification_outputs/wave218-p3-kanzi-framework-wins.csv` | 536 | `5f957d056ce5977d11e8660f34e4574c7f11a6d7bbea7115f56e2bf5378f5e31` |
| `verification_outputs/wave218-p3-kanzi-framework-wins.json` | 984 | `9b5c3b68d05b136e662fffbef1873693f28c43547cebf7b8c7b480261d0de49c` |
| `verification_outputs/wave225-p2-r3-bootstrap.csv` | 588 | `426cdbf972d7f2f171031657eb9ea0551f2be9ab42d6cded1cc0c046f6f98a3b` |
| `verification_outputs/wave225-p2-r3-bootstrap.json` | 2491 | `54dd74e500878750dcfd75eedc11bfece87ce61326797f4473031fea0debc5c0` |
| `verification_outputs/wave229-p3-core-adapter-paper-quantities.csv` | 825 | `d199f2a0b99ec0594870c1efaf2c7a4486715034646dce352ef739e27567f5b2` |
| `verification_outputs/wave229-p3-core-adapter-paper-quantities.json` | 2128 | `95109117552b486b9c3052eb0b019abc8c0592ea01a3e99ae2651577bb7a3426` |

## Statistical methods (TOST/JT/BF01/Meta/NI)

TOST equivalence, Jonckheere-Terpstra trend, Bayes Factor 01, DerSimonian-Laird meta-analysis, and non-inferiority test outputs. Backs the secondary-statistical-claims dossier (CLM-057/058 and the NI test on the R5b FID regression).

Files in this section: 4

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave234-p3-jonckheere.csv` | 278 | `003f33f4b87b7b3e5a67c41d0fa9e61a29434ad728216b509d0bf98dc6cf4ac0` |
| `verification_outputs/wave234-p4-bf01.csv` | 2349 | `e531da9f717047efdd3d1ccdc72d77f2f257c17134fe8630c29b23074e36791a` |
| `verification_outputs/wave234-p6-ni-test.csv` | 377 | `8db5f339eea1e91c3aaeddfa635542fb955c6f7ac4e68554184db9e64194ba90` |
| `verification_outputs/wave246-p4-subgroup-meta.json` | 2764 | `e0147ab7101b96015d65dfba28ef320533878495438d20dfbb6a6fe03871593b` |

## Wall-clock + cProfile evidence

Wall-clock measurements and cProfile traces for the framework CIFAR/MNIST/Kanzi adapters — backs the speedup-vs-baseline numbers (3-5x on CIFAR, CUDA-graph 4.3x speedup, matched-compute wall-clock gap closure). Includes pstats files, per-component timings, cprofile Top-10 CSV, and memory traces.

Files in this section: 8

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave211-p3-f-side-values.csv` | 4507 | `c1d8ac475f083335c542312e951aad7b518fcb88b7dd32902e6aba10d81b6e37` |
| `verification_outputs/wave229-p4-wall-clock-matched.csv` | 583 | `1c9b089cafc34ec21991a4ac35286143fbe8a805b5dfc1c7e7b9089d3c47d041` |
| `verification_outputs/wave229-p4-wall-clock-matched.json` | 4328 | `4bfba9d91eebfa1e0a63c69391adb56662f9521da03e15e945b4571a29a0be24` |
| `verification_outputs/wave233-p6-cprofile-with-cache.txt` | 2622 | `77ccd22091abcc73e7b87280ce3d8bd9aefcb7ec4a180e06a0d71c203e4e16df` |
| `verification_outputs/wave233-p6-wall-clock.csv` | 187 | `6e7170c3d69fe0a01750cb8e0bf8923e10a5d7bc7a6c5e24736fe91f6e8f12f4` |
| `verification_outputs/wave233-p6-wall-clock.json` | 1521 | `0aa8d08a35eede014354bdf3303adadd77a3c82e5aefa1aae54d605f324236bd` |
| `verification_outputs/wave236-p1-p4finish.json` | 1833 | `2c70209a7a1e85146b89e32b7492d601a3cd6a1a1c049e5929891a90a9f389fe` |
| `verification_outputs/wave236-p2-wallclock.json` | 738 | `b2cbb1abaffab17f057405ee4cb382944b66033543fe4761d873e073f21bada8` |

## Engineering gates (D.4 PASS evidence)

Engineering-gate PASS evidence: SHA-256 manifest of all checkpoint files, paper-metric caches, capability audits, controlled audits, simulation-based-calibration (SBC) checks, NFE-scan sweeps, power-analysis raw outputs, and Phase-4 regression captures. Backs the D.4 30/30 PASS gate and reproducible-by-hash claim.

Files in this section: 4

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/ckpt_sha256.json` | 3488 | `20ca38ddf5b18971488eb90620baf5ffdbc0d385455e68a37e88df8bb7039cb6` |
| `verification_outputs/kanzi_n1000_coords.txt` | 2635744 | `09153a874d993d7749775e0f66c67d91680016fd2da31a4d624c7d8783952d4c` |
| `verification_outputs/kanzi_n1000_manifest.json` | 460 | `584bcceaded51ef2dfc2b06d3c707e0005feb96145f7d86b7778cf213162fa92` |
| `verification_outputs/lineageflow_nfe_scan_paper_metric_q3_2026.json` | 95301 | `4b241e732de1d9620e373962e419e8ca5a44f9f32085d5e31608926a97d2f6ca` |

## Other diagnostics + helpers

Supplementary diagnostic captures: failure-mode audits, ablation tables, baseline comparisons, sweep logs, sanity smoke runs, helper trace outputs, and earlier-iteration artefacts retained for byte-reproducibility. Not headline-bearing but required to reproduce the full audit trail.

Files in this section: 10

| Path (relative to workspace) | Size (bytes) | SHA-256 |
|---|---|---|
| `verification_outputs/wave165_failure_modes_q3_2026/failure_modes.json` | 1669 | `cfae270cd0d7227e5965c03222d253b93d74905b2f6665f04a0b6333814c8f48` |
| `verification_outputs/wave179-p4-aggregation.csv` | 1427 | `940811e1183c2363ef36fcafb996f146c04eab1e5554620ab349e5f95bbde86b` |
| `verification_outputs/wave179-p5-figure-deltas-with-error-bars.png` | 162242 | `b7dfbb331703e1346f727b2df6ba3e995570e67d02f30d2d374fa6e5959fd648` |
| `verification_outputs/wave179-p5-figure-pLDDT-with-error-bars.png` | 113209 | `0246b6a9dfad77d98d1246cbe49edcdf77b0f364321ce382ab1d18148b89a7c8` |
| `verification_outputs/wave179-p5-figure-scPerplexity-with-error-bars.png` | 109624 | `f576646dda68a65ce8f9e9d3e3258e5a35fed13034c3eefbe6d71ef4228b8d3a` |
| `verification_outputs/wave185-p2-empirical-bl.csv` | 2256 | `937f6e00390b9fd710a73b7870639569e20c02dac59dc95490bbce467c4455ef` |
| `verification_outputs/wave185-p3-tightness.csv` | 3041 | `15d1cf8e8f88f685d20e92e2f7e631247f47a55c3a5071e986f7290dd9f1cec7` |
| `verification_outputs/wave185-p4-figure-bl-tightness.png` | 133102 | `3e65115db9f4faf29abcb009886e15e4fe34dd7a9f0b889498dff5c137d121df` |
| `verification_outputs/wave185-p4-figure-tightness-ratio.png` | 107266 | `77d495ed3e30f26626cad963eea350e4ad3d5d5b6f4a9f564a665cb477c2d6ff` |
| `verification_outputs/wave231-submission-bundle-manifest.md` | 8056 | `32d2ebb5a95ab27e858541dcc6934221dd3555b7045b66fd052a10ff341c8642` |

---

## Reviewer verification (single command)

To verify ALL hashes at once:

```bash
(cd verification_outputs && find . -type f -print0 | sort -z | xargs -0 sha256sum) > /tmp/recomputed.sha256
```

and compare the resulting per-line `<sha>  <rel-path>` pairs against the tables above (the `Path (relative to workspace)` column, when stripped of the `verification_outputs/` prefix, matches the relative path `find` will produce).

The manifest itself is generated by `tools/build_verification_manifest.py` from `git ls-files verification_outputs/`; re-running that script regenerates this file in byte-stable form (the table layout is deterministic given input order, and the input file list is fixed by git history).

