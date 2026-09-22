# Wave 213 P6 — Repo Naming Consistency Audit

**Date:** 2026-09-21
**Audit owner:** Wave 213 P6 repo-naming-consistency agent
**Status:** Audit complete; recommendation below; doc-only changes committed.

---

## §1 Problem statement

The submission to IEEE TPAMI describes a method called **FlowA**
("Training-free, paper-quantity-driven re-inference for Flow Matching
checkpoints", `docs/drafts/paper-flattened-draft.md` line 1). The
canonical source-code repository, however, is hosted on GitHub under
the name **`flowa-multistep-reinference`**, which reflects an earlier
project name and is **not** the method name used in the paper.

A reviewer landing on the GitHub link from the paper will see a repo
name (`flowa-multistep-reinference`) that does not match the paper's
method name (`FlowA`). The discrepancy is consistent (the repo name
is *about* the method's behaviour, not its identity), but it is a
small, fixable source of confusion. This audit records the
discrepancy, evaluates the two reasonable resolutions, and locks
the recommended path.

## §2 Current state (verified 2026-09-21)

```
$ git remote -v
origin  https://github.com/silverenternal/flowa-multistep-reinference.git (fetch)
origin  https://github.com/silverenternal/flowa-multistep-reinference.git (push)
```

- **GitHub repo name (URL):** `silverenternal/flowa-multistep-reinference`
- **GitHub repo name (bare):** `flowa-multistep-reinference`
- **Paper method name:** `FlowA`
- **Paper draft occurrences:** 28 occurrences of `FlowA` in
  `docs/drafts/paper-flattened-draft.md`; 0 occurrences of the bare
  repo name `flowa-multistep-reinference` in the paper text.
- **Cover-letter occurrences:** 7 occurrences of `FlowA` in
  `docs/cover-letter-tpami.md` §1/§3/§8; 0 of the bare repo name.
- **RELEASE-NOTES-v3.0.md occurrences:** 0 occurrences of the bare
  repo name `flowa-multistep-reinference`; 0 of `FlowA` either
  (RELEASE-NOTES uses the framework/headline phrasing, not the method
  proper noun).

The two names do not collide in the paper text, but they collide at
the URL layer: the URL a reviewer is given is
`https://github.com/silverenternal/flowa-multistep-reinference`,
and the name they are told to expect at that URL is `FlowA`. That is
the friction point.

## §3 Option A — Rename the GitHub repo to `flowa`

### Mechanics

GitHub repo renames are **not** exposable from `gh` / the REST API in
a way that preserves redirect semantics for forks — they require the
GitHub web UI (Settings → General → Repository name). The rename
preserves:

- All commits, branches, tags, releases.
- A 301 redirect from the old URL to the new URL (so old links
  keep working).
- Issues, PRs, and wiki links (rewritten automatically).

It does **not** preserve:

- Local clones' `origin` remote URL (every developer must update).
- External links hard-coded by anyone during the rename window.

### Recommendation strength

**Strongly recommended** if and only if the maintainer has a 30-second
window to log in to github.com and click through the rename dialog.
The renamed URL would be
`https://github.com/silverenternal/flowa`, which matches the paper's
method name and removes the friction entirely.

### Why this is a manual step

The agent did **not** perform this rename. Repo renames require the
GitHub admin UI; they are out of scope for any automated script that
does not have a maintainer OAuth token with `repo` admin scope. The
"manual step" gate is a feature, not a bug: a typo in the rename
dialog produces a public URL change that cannot be silently rolled
back.

## §4 Option B — Keep `flowa-multistep-reinference` + Code Availability statement

### What changes

The GitHub URL stays as is. The cover letter and the RELEASE-NOTES
both gain a **Code Availability statement** that names both the
repo and the method, explains the discrepancy as historical (the
repo predates the method name finalisation), and locks
**FlowA** as the canonical citation name.

### When to prefer Option B

- If the maintainer cannot perform the rename in time for TPAMI
  submission (low likelihood — 30-second UI click — but possible).
- If the repo URL has been cited in any external communication
  (grant proposal, accepted workshop version, invited talk) and the
  maintainer wants to avoid the redirect-window risk.
- If the maintainer prefers to keep the descriptive repo name
  (`flowa-multistep-reinference` describes *what the code does*,
  `flowa` is just a proper-noun label) and is happy to absorb the
  small reviewer-confusion cost in exchange for a more descriptive
  URL.

### What the Code Availability statement says

> The implementation of **FlowA** is available at
> `https://github.com/silverenternal/flowa-multistep-reinference`
> (repository name: `flowa-multistep-reinference`; method name in
> this paper: **FlowA**). The name discrepancy reflects the
> historical evolution of the project — the repository predates the
> finalisation of the method name in the paper draft. The canonical
> name for citation purposes is **FlowA**. Reviewers following the
> link above will land on the canonical source tree; the descriptive
> repository name is preserved intentionally to keep the URL
> self-documenting about the method's *behaviour* (paper-quantity-
> driven multi-step re-inference) rather than its *identity*
> (**FlowA**).

## §5 Recommendation

**Option A (rename GitHub repo to `flowa`)** is the cleanest fix and
removes the friction entirely. The agent did not perform the rename
(no CLI access to the GitHub admin UI); this audit surfaces the
recommendation and locks it as the post-submission follow-up.

**Option B (Code Availability statement)** is the immediate
mitigation that ships in this commit. The cover-letter and
RELEASE-NOTES both gain the statement now, so the discrepancy is
documented whether or not the rename happens.

Both resolutions are compatible: the maintainer can ship Option B
in the submission packet (committed in this PR), then perform
Option A at any later time without re-touching the paper. If
Option A is performed later, the Code Availability statement
remains accurate (and the URL inside it can be updated by a
one-line edit at that point).

## §6 Changes shipped in this audit

1. `docs/audit/wave213-p6-repo-naming.md` (this file) — the audit
   record.
2. `docs/cover-letter-tpami.md` — adds a **Code Availability**
   subsection under §6 Reproducibility that names both the repo URL
   and the method name and explains the historical discrepancy.
3. `RELEASE-NOTES-v3.0.md` — adds a one-line note under
   "Quick reference" that gives both names (paper method name
   `FlowA`; repo URL `https://github.com/silverenternal/flowa-multistep-reinference`).

No code changes. No renames. The repo URL is unchanged on disk.