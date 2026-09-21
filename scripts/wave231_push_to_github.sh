#!/usr/bin/env bash
# Wave 231 P5 — Push the frozen TPAMI submission branch to GitHub origin.
#
# This script:
#   1. Verifies the working tree is clean (so the submission bundle is
#      byte-stable and reviewer-verifiable).
#   2. Lists unpushed commits on origin/main..HEAD (the Wave 229–231 audit
#      chain that constitutes the paper's reproducibility provenance).
#   3. Asks for an explicit confirmation before `git push origin main`
#      because the push is irreversible from the GitHub side.
#   4. Echoes the next-step checklist (public visibility toggle, Zenodo
#      DOI generation, TPAMI Editorial Manager submission).
#
# Exit codes:
#   0 — push succeeded
#   1 — pre-flight check failed (dirty tree, missing remote, etc.)
#   2 — user cancelled the confirmation prompt
#
# Usage:
#   bash scripts/wave231_push_to_github.sh
#
# Optional environment overrides:
#   REMOTE   — git remote name (default: origin)
#   BRANCH   — branch to push (default: main)

set -euo pipefail

REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "============================================================"
echo " Wave 231 P5 — Push flowa-multistep-reinference to GitHub"
echo "============================================================"
echo " Repo root:  ${REPO_ROOT}"
echo " Remote:     ${REMOTE}"
echo " Branch:     ${BRANCH}"
echo " Date:       $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo

# 1. Pre-flight: working tree must be clean.
if ! git diff --quiet --ignore-submodules HEAD; then
    echo "ERROR: working tree has uncommitted changes."
    echo "       Commit or stash before pushing the submission bundle."
    git status --short
    exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
    # Untracked files only matter if they are submission-bundle artefacts.
    # We warn rather than fail so reviewer-token secrets and IDE state
    # can stay untracked.
    echo "WARNING: untracked files present:"
    git status --short --untracked-files=all | head -20
    echo
fi

# 2. Verify the remote exists and is reachable.
if ! git remote get-url "${REMOTE}" >/dev/null 2>&1; then
    echo "ERROR: remote '${REMOTE}' is not set on this clone."
    echo "       Add it with: git remote add origin <url>"
    exit 1
fi

REMOTE_URL="$(git remote get-url "${REMOTE}")"
echo " Remote URL: ${REMOTE_URL}"
echo

# 3. List unpushed commits — the audit chain reviewers will see.
UNPUSHED_COUNT="$(git rev-list --count "${REMOTE}/${BRANCH}..${BRANCH}" 2>/dev/null || echo 0)"

if [[ "${UNPUSHED_COUNT}" -eq 0 ]]; then
    echo "No unpushed commits on ${REMOTE}/${BRANCH}..${BRANCH}."
    echo "Nothing to push."
    exit 0
fi

echo " Unpushed commits on ${REMOTE}/${BRANCH}..${BRANCH} (${UNPUSHED_COUNT}):"
git log --oneline "${REMOTE}/${BRANCH}..${BRANCH}" | sed 's/^/   /'
echo

# 4. Confirm before pushing.
read -r -p "Push ${UNPUSHED_COUNT} commit(s) to ${REMOTE} ${BRANCH}? [y/N] " REPLY
echo
if [[ ! "${REPLY}" =~ ^[Yy]$ ]]; then
    echo "Cancelled by user."
    exit 2
fi

# 5. Push.
git push "${REMOTE}" "${BRANCH}"

echo
echo "============================================================"
echo " Push complete. Next steps:"
echo "============================================================"
echo
echo " 1. GitHub repo → Settings → General → Danger Zone →"
echo "    'Change repository visibility' → 'Public'."
echo "    (Required for the TPAMI reproducibility artifact to be"
echo "    reviewer-accessible without auth.)"
echo
echo " 2. Zenodo → log in with GitHub OAuth → enable the"
echo "    flowa-multistep-reinference repository → trigger DOI"
echo "    generation on the freeze-marker commit."
echo "    Add the resulting DOI to the paper's Data Availability"
echo "    section (see docs/drafts/paper-flattened-draft.md)."
echo
echo " 3. TPAMI Editorial Manager → 'New Submission' → upload:"
echo "    - paper-flattened-draft.pdf (from docs/drafts/)"
echo "    - supplementary.pdf (from supplementary.md)"
echo "    - cover-letter-tpami.pdf (after filling the"
echo "      [USER TO FILL] placeholders listed in §0 of"
echo "      docs/cover-letter-tpami.md)"
echo
echo " Detailed action list: docs/internal/tpami_submission_action_checklist.md"
echo " Submission manifest:  verification_outputs/wave231-submission-bundle-manifest.md"