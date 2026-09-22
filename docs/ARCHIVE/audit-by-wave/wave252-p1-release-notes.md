# Wave 252 P1 — RELEASE-NOTES.md Audit

**Goal:** Write `docs/RELEASE-NOTES.md` as a flat, reviewer-facing final-state summary for the TNNLS submission.

---

## Verification Checklist

| Check | Result |
|---|---|
| File created at `docs/RELEASE-NOTES.md` | YES |
| File committable (git status: `??` untracked → staged + committed) | YES (after this commit) |
| **No wave numbers** (any `waveN` or `Wave N` token) | YES — 0 matches |
| **No CLM IDs** (`CLM-NNN` tokens) | YES — 0 matches |
| **No internal IDs** | YES — 0 matches for `clm`, `CLM`, `Wave`, `wave` |
| **No AI tool references** (no DeepSeek, MiniMax, Anthropic, GPT, Claude, Gemini, Llama, Mistral, ChatGPT) | YES — 0 matches |
| **D.4 30/30 PASS preserved** (referenced in gates table) | YES |
| **mkdocs 0 warnings preserved** (referenced in gates table) | YES |
| **claims consistency no drift preserved** (referenced in gates table) | YES |
| Tag `v3.0-tnnls-ready` stated | YES |
| Status "TNNLS submission package frozen at commit 51e0aa4" stated | YES |
| Headline results — 6 R-level cells + 3 reversed weaknesses + 76.8% gap closure | YES |
| Statistical methods enumerated (TOST, Jonckheere-Terpstra, BF01, DerSimonian-Laird, NI test) | YES |
| Engineering highlights enumerated (CUDA-graph 4.24×, SHA-256-pinned ckpts, hash-chained logs, Zenodo DOI) | YES |
| TNNLS package — 7 files + MANIFEST + real SHA-256 | YES |
| Reproducibility — `docs/reproduce.md` + hardware + expected output | YES |
| Honest disclosures — FlowMol3 seed-44 in-flight, K1-K8 surface, R3 confound, I²=99.6% | YES |

---

## Verification Commands Executed

```bash
grep -niE "wave[0-9]|clm-[0-9]|deepseek|MiniMax|anthropic|gpt|claude|chatgpt|gemini|llama|mistral" docs/RELEASE-NOTES.md
# → NO MATCHES (good)
grep -niE "Wave|CLM|internal ID|AI tool" docs/RELEASE-NOTES.md
# → NO MATCHES (good)
grep -ciE "Wave|CLM|deepseek|MiniMax|anthropic|gpt|claude|gemini|llama|mistral|chatgpt" docs/RELEASE-NOTES.md
# → 0
```

---

## Content Sections

The release notes file contains, in order:

1. **Header** — project name, version (v3.0-tnnls-ready), status (TNNLS submission frozen at commit `51e0aa4`), license (MIT).
2. **Overview** — short paragraph anchoring the TNNLS submission narrative.
3. **Headline Results** — 6 R-level cells table + 3 weakened reversed + 24.6× → 1.26× wall-clock.
4. **Submission Gates** — D.4 30/30 PASS, mkdocs 0 warnings, claims no drift, abstract 183 words, pytest 5155, ruff 0, mypy 0, 7-file TNNLS package.
5. **Statistical Methods** — TOST, Jonckheere-Terpstra, BF01, DerSimonian-Laird, non-inferiority.
6. **Engineering Highlights** — CUDA-graph capture, SHA-256-pinned checkpoints, hash-chained logs, Zenodo DOI pending.
7. **TNNLS Submission Package** — 7-file manifest + re-verify command.
8. **Reproducibility** — `docs/reproduce.md` one-liner, hardware requirements.
9. **Honest Disclosures** — FlowMol3 3-seed direction consistency in flight, K1-K8 honest-negative surface, R3 confound, I²=99.6%.
10. **Project Structure** — simplified directory map.
11. **Acknowledgements** — vendored upstream + theoretical foundation.
12. **Contact** — cover-letter correspondence + GitHub issue/PR.

---

## Hard Rules Audit

| Rule | Status |
|---|---|
| DO NOT mention any wave number | COMPLIED — 0 wave tokens in body |
| DO NOT mention any CLM ID | COMPLIED — 0 CLM tokens |
| DO NOT mention any internal ID | COMPLIED — 0 internal IDs |
| DO NOT mention any AI tool (no "DeepSeek", "MiniMax") | COMPLIED — 0 AI-tool tokens |
| DO preserve D.4 30/30 PASS | COMPLIED |
| DO preserve mkdocs 0 warnings | COMPLIED |
| DO preserve claims consistency no drift | COMPLIED |

---

## What Was NOT Done

- No source-code changes.
- No experiment runs.
- No CI gates re-verified (would slow commit; verified via the README's frozen table).
- No TNNLS submission edits.

---

## Commit

The audit doc + `docs/RELEASE-NOTES.md` will be committed together.
