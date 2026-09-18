# Wave 194 Reference Template Plan

Structural imitation plan for FlowA's EAAI submission, derived from 2 EAAI 2026 reference papers.

## Reference 1: Diao et al. 2026 (PAYLOCKED — metadata only)

| Field | Value |
|---|---|
| Title | Flow-accelerated diffusion model for trajectory generation and optimization in offline reinforcement learning |
| Authors | He Diao, Shan Zhong, Xianglin Chen, Ping Zhang, Zhenyu Feng, Bei Peng |
| Journal | Engineering Applications of Artificial Intelligence, Vol 181, Article 115521 |
| Year | 2026 |
| DOI | 10.1016/j.engappai.2026.115521 |
| OA Status | closed (Unpaywall) |

**Scope:** Offline RL with diffusion trajectory generation. NOT a direct match to FlowA but useful for EAAI typography/template only.

See `diao2026-eaai.md` for full metadata.

---

## Reference 2: MrFlow (Zheng et al. 2026, arXiv 2607.01642)

- **Title:** Multi-Resolution Flow Matching: Training-Free Diffusion Acceleration via Staged Sampling
- **Authors:** Xingyu Zheng, Xianglong Liu, Yifu Ding, Weilun Feng, Junqing Lin, Jinyang Guo, Haotong Qin
- **Source:** arXiv 2607.01642 (open access, downloaded to `/tmp/w194/mrflow.pdf`)
- **Abstract word count:** 279
- **Page count:** 32
- **Figure count:** 10
- **Table count:** 16
- **Reference count:** 50

### Section structure (MrFlow)

- 1 Introduction
- 2 Related Work
- 3 Method
- 3.1 Low-Resolution Structure Generation
- 3.2 Pixel-Space Super-Resolution
- 3.3 Low-Strength Noise for High-Frequency Resampling
- 3.4 High-Resolution Detail Refinement
- 4 Empirical Results
- 4.1 Implementation Details
- 4.2 Main Results
- 4.3 Ablation Study
- 5 Conclusion
- References
- Appendix A Background
- Appendix B Detailed Experimental Setup
- Appendix C Stage-wise Analysis
- C.1 Sources of Acceleration at the Low-Resolution Stage
- C.2 Two Design Choices of Pixel-Space Super-Resolution
- C.3 Formal Characterization of High-Frequency Resampling
- C.4 Single-Step Sufficiency of High-Resolution Detail Refinement
- C.5 Structure-Detail Decoupling
- Appendix D MrFlow on Recent Open Models
- Appendix E Efficiency Analysis
- Appendix F More Generation Examples
- F.1 Comparison with Various SOTA Strategies
- F.2 More Examples of MrFlow
- F.3 Prompts of the Images in the Paper

---

## Imitation Plan for FlowA

### Abstract structure (target: ~280 words, single paragraph)

1. 1-sentence problem statement: diffusion inference is slow; training-free acceleration is the focus
2. 1-2 sentence gap: existing multi-resolution latent-upsampling methods blur or introduce artifacts; require runtime dynamic identification
3. 1-2 sentence proposal: MrFlow-style staged LR->SR->noise->HR pipeline that operates in pixel-space and needs no training
4. 1-2 sentence headline result: 10x speedup within 1% quality gap; combines orthogonally with timestep distillation to 25x
5. Total ~280 words (matches MrFlow target)

### Introduction structure (5-6 paragraphs)

1. Opening: 'Diffusion built upon Transformers ... flow matching ... has become mainstream' (cite Qwen-Image-20B 47s/A100 example)
2. Paragraph 2: Survey of acceleration strategies — quantization, efficient attention, timestep distillation, feature caching, token pruning. Note their tradeoffs (training cost, <4x speedup, <1.5x).
3. Paragraph 3: Multi-resolution generation strategies get >5x but exhibit blurring/artifacts due to latent upsampling + runtime dynamic identification.
4. Paragraph 4 (our proposal): our approach — LR sampling + pixel-space SR + low-strength noise + HR refine — 4 numbered sub-points explaining each design choice's contribution.
5. Paragraph 5 (experimental headline): 10x within 1% gap; orthogonal to timestep distillation; >25x combined.
6. Paragraph 6 (contributions, bulleted): 3 bullet contributions — pipeline design, principle innovation per stage, operational flexibility.

### Related work structure (4 grouped paragraphs)

1. Flow matching — 1 paragraph, formal definition (xt = (1-sigma_t)x0 + sigma_t eps), model learns v_theta, integral from t=1 to t=0. Cite Lipman 2022, Liu 2022.
2. Acceleration of diffusion generation — 1 paragraph, split into 3 sub-families: timestep reduction, feature caching, token pruning. Each with quantitative speedup range.
3. Multi-resolution generation — 1 paragraph, split into 2 sub-classes: (1) extending attainable resolution (Du 2024, Wu 2025b) and (2) treating MR as acceleration (Tang 2025, Jeong 2026, Tian 2025, Xiao 2026) — all do upsampling in latent/frequency domain.
4. Super-resolution and image repainting — 1 paragraph on the 3 SR families (regression/SwinIR, GAN/Real-ESRGAN, diffusion/OSEDiff) used in pixel space.

### Method structure (overview + 4 sub-sections, each with Formulation/Analysis)

- Method overview: 1 paragraph stating the 7-step pipeline (LR latent sample -> VAE decode -> SR in pixel space -> VAE encode -> noise injection -> HR latent sample -> VAE decode) with default 12 LR steps + 0.1 noise + 1 HR step.
- Section 3.1 Low-Resolution Structure Generation — formulation (eqs 3-5) + analysis (2 acceleration sources).
- Section 3.2 Pixel-Space Super-Resolution — formulation (eq 6) + analysis (2 design choices).
- Section 3.3 Low-Strength Noise for High-Frequency Resampling — formulation (eqs 7-8) + analysis (sigma_t lower bound eq 9).
- Section 3.4 High-Resolution Detail Refinement — formulation (eqs 10-11) + analysis (single-step sufficiency).
- Each subsection follows: Formulation -> Equation(s) -> Analysis -> Cross-reference to Appendix.

### Experiments structure (4.1-4.3 + appendices B/C)

- Section 4.1 Implementation Details — models (FLUX.1-dev, Qwen-Image-20B), baselines (ToMA, DB-Taylor, SPEED, RALU, Pi-Flow), hardware (A100), metrics (OneIG-Bench, DPG-Bench, CLIP-consistency), resolution (1024x1024).
- Section 4.2 Main Results — Table 1 (main quantitative comparison), Table 2 (cross-resolution), Figure 1 (qualitative Qwen-Image), Figure 5 (FLUX.1-dev qualitative), Table 3 (per-baseline numerical).
- Section 4.3 Ablation Study — per-stage ablation table, noise-strength sweep, SR-strategy comparison, step-count sweep.
- Appendix B (Detailed Experimental Setup) — extended baselines, hyper-parameters at each operating point.
- Appendix C (Stage-wise Analysis) — C.1 single-step cost + few-step convergence, C.2 SR design choices, C.3 noise-level formalization, C.4 single-step sufficiency, C.5 structure-detail decoupling.

### EAAI-specific formatting notes

- Use Elsevier EAAI single-column body layout with header banner.
- Abstract must fit within EAAI constraints (typically <=300 words, structured abstract NOT required for original research).
- Section numbering: 1, 2, 3, 3.1, 3.2 (subsections 3 levels deep).
- Use 'Figure X:' / 'Table X:' captions above tables and below figures.
- References in Elsevier style (author surname initial., year, title, venue, vol(issue), pp.).
- Include a Highlights section (3-4 bullet points, <=85 chars each) for EAAI submission.
- CRediT author contributions statement required.
- Declaration of competing interest required.
- Appendix sections labeled A, B, C ... (single capital letter) with subsections A.1, A.2 ...

---

## Source files

- `/tmp/w194/mrflow.pdf` — full text (8.7 MB, 32 pages)
- `/tmp/w194/mrflow.txt` — pdftotext -layout extraction (1862 lines)
- `/tmp/w194/mrflow-abstract.txt` — clean abstract body (279 words)
- `/tmp/w194/diao2026.pdf` — HTML 302 redirect (PDF unavailable, paywalled)
- `/tmp/w194/crossref-diao.json` — Crossref API metadata for Diao 2026
- `/tmp/w194/diao-unpaywall.json` — Unpaywall API metadata (oa_status=closed)
- `/tmp/w194/ss-diao.json`, `/tmp/w194/ss-diao2.json` — Semantic Scholar (no abstract)
- `/tmp/w194/arxiv-diao.xml` — arXiv API (no preprint match)
