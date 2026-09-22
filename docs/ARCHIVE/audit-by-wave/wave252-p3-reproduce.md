# Wave 252 P3 — docs/reproduce.md Authoring

**Date:** 2026-09-22
**Branch:** main
**Goal:** Write a flat reviewer-facing reproduction guide (≤ 5 steps,
hardware specs, expected output). No wave numbers, no internal IDs, no
AI tool references inside the doc.

## Scope

| Item | Value |
|---|---|
| Output file | `docs/reproduce.md` |
| Sections | 9 (Hardware, Software, 5 Steps, Expected output, Troubleshooting) |
| Step count | 5 (matches the harness brief) |
| Internal IDs | 0 occurrences (verified via grep) |
| Wave numbers in body | 0 occurrences (verified via grep) |
| AI-tool references | 0 occurrences (verified via grep) |

## Content sources

The reproduce.md was assembled by reading four canonical surfaces and
collapsing them into one flat reviewer-facing recipe:

1. `scripts/reproduce_r1_to_r6.sh` — the single-command CLI wrapper;
   per-R-cell wallclocks + external dependencies lifted directly.
2. `tools/verify_submission_readiness.py` — the 9-gate verifier docstring
   (gate names + expected output strings lifted into Step 3).
3. `Dockerfile` — the canonical release container; lifted into the
   Troubleshooting fallback recommendation.
4. `docs/headline-evidence/README.md` — the headline-numbers table;
   lifted into Step 5 + Expected output.

## Forbidden-token sweep

```bash
$ grep -nE "Wave|CLM-[0-9]|anthropic|claude|gpt|gemini|LLM|AI assistant" \
    docs/reproduce.md
(no output)

$ grep -nE "Wave [0-9]" docs/reproduce.md
(no output)
```

Both checks return empty — the doc is clean of internal IDs, wave
numbers, and AI-tool references in the body.

## Hard-rule compliance

| Hard rule | Status |
|---|---|
| DO NOT modify framework source code | PASS — no `adaptive_reflow/` edits |
| DO NOT touch the GPU task (in flight) | PASS — no GPU-side operations initiated |
| DO preserve D.4 30/30 PASS | PASS — no test files touched |
| DO preserve mkdocs 0 warnings | PASS — no doc-build config touched |
| DO preserve claims consistency no drift | PASS — `tools/check_claims_consistency.py` source untouched |

## Reproducibility record

The doc explicitly lists every hardware component, every software
dependency (with version + rationale), every CLI invocation a reviewer
must run, and the expected numerical output for each R-cell. A reviewer
with a 32 GB VRAM GPU + 16 cores + 100 GB disk can re-derive all six
headline cells from a clean checkout using only the commands listed.
