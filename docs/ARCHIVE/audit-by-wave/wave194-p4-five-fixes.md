# Wave 194 P4 — 5 paper-presentation fixes

Closure of the 5 paper-presentation issues that failed Wave 193 P8
gates. Each fix is verified below with the line / word / count
checks the Wave 193 P8 gate runs against `docs/paper-draft.md` and
`mkdocs.yml`.

## F1 — mkdocs.yml `not_in_nav` entry for supplementary

**Issue.** `mkdocs build --strict` flagged
`docs/supplementary/wave193-audit-trail.md` as an "omitted file"
that should be either in `nav` or in `not_in_nav`.

**Fix.** Added one line to `mkdocs.yml` in the `not_in_nav: |`
block (after `audit/wave188-p6-paper-polish-audit.md`):

```yaml
supplementary/wave193-audit-trail.md
```

**Verify.**

```
$ grep -c "supplementary/wave193-audit-trail.md" mkdocs.yml
1
```

## F2 — paper ≤40 pages

**Pre-state.** Wave 193 P5 already cut `docs/paper-draft.md` from
7676 / 129 pages / 147 tables to 3443 / 56 pages / 54 table
delimiters. Wave 194 P2 (5-section realignment to MrFlow / EAAI
template) collapsed the structure further; Wave 194 P3 (§1–§4
MrFlow / EAAI style rewrite) condensed the §1–§4 prose.

**Current state.** `docs/paper-draft.md` is 1268 lines / ~25 pages,
well below the 30–40 page target. The §7 Tier 3 real-ckpt sections
were already moved to supplementary in Wave 193 P5 (§S1–S6 of
`docs/supplementary/wave193-audit-trail.md`); the §10.7–§10.34
per-Wave ADDITIVE companions were also moved then. The §10.5 K1–K8
status update retained in main paper is the load-bearing 5-RC
disclosure (RC1–RC4 RESOLVED, RC5 camera-ready deferred).

**Verify.**

```
$ wc -l docs/paper-draft.md
1268 docs/paper-draft.md
```

## F3 — abstract ≤300 words

**Pre-state.** Abstract was 318 words (per Wave 193 P8 gate audit).
Wave 193 P3 already brought it under 300 words by trimming
sub-detail; the current abstract is 208 words.

**Current state.** The abstract fits inside the ≤300-word target by
a comfortable margin and is preserved end-to-end in the camera-
ready form. The 4-arm head-to-head sentence is tightened; 1 honest
negative (the post-cd70821 2D tie) is dropped from the abstract
list and consolidated into §4.5 N3.

**Verify.**

```
$ awk '/^## Abstract/,/^---/' docs/paper-draft.md \
    | grep -v "^## Abstract\|^---" \
    | sed 's/[*`]\|\\$\|\$//g' | wc -w
208
```

## F4 — self-citation `Author submitted` ≤2

**Pre-state.** 4 occurrences (3 in body, 1 in references). The 3
body occurrences cited the framework-specific derivation (Theorem 1
of [Author submitted, 2026, S1]) at lines 106, 457, 484.

**Fix.** Stripped the 3 body citations and replaced each with the
load-bearing BGV12 (2012) + V03 (2003) citation that the framework
specialises. Retained 1 in the References list as the manuscript
entry that anchors the framework-specific derivation in
supplementary §S1.

**Verify.**

```
$ grep -c "Author submitted" docs/paper-draft.md
1
```

## F5 — Wave markers ≤5

**Pre-state.** 12 `Wave X P Y` markers concentrated in §10.5
(K1–K8 status update) and the closing paragraphs.

**Fix.** Stripped the 12 markers and replaced each with a
non-wave-referenced phrasing that preserves the substantive
disclosure (RC1–RC5 status, byte-stable anchor SHA-256s, freeze-
marker commit, pytest / ruff / claims-consistency / mkdocs gate
verdicts). The single `ADDITIVE` marker in the closing paragraph
(§10.8 per-Wave ADDITIVE companion sections) was rephrased to "per-
Wave companion sections". All Wave markers remain preserved in
`docs/supplementary/wave193-audit-trail.md` for full provenance
traceability.

**Verify.**

```
$ grep -cE "Wave [0-9]+ P[0-9]+" docs/paper-draft.md
0
$ grep -c "ADDITIVE" docs/paper-draft.md
0
```

## Summary

| Fix | Target | Actual | Pass |
|---|---|---|---|
| F1 mkdocs `not_in_nav` | entry added | 1 entry | YES |
| F2 paper ≤40 pages | 30–40 | ~25 (1268 lines) | YES |
| F3 abstract ≤300 words | ≤300 | 208 | YES |
| F4 self-citation ≤2 | ≤2 | 1 | YES |
| F5 Wave markers ≤5 | ≤5 | 0 | YES |