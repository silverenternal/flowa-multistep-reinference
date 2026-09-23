#!/usr/bin/env bash
# Vendored upstream NOT-touched check.
#
# The three vendored trees under ``data/`` carry upstream code that the
# project does NOT own and MUST NOT modify directly:
#
#   * ``data/FlowMol3/``           — FlowMol3 molecule FM upstream
#   * ``data/lineageflow_upstream/`` — LineageFlow protein FM upstream
#   * ``data/Kanzi/``              — (placeholder; canonical Kanzi weights
#                                    live under ``data/kanzi_ckpt/``)
#
# Any diff against HEAD inside these paths is a hard pre-merge gate
# failure — the modification has to land in the upstream repo first
# and be re-vendored. This script is wired into the pre-commit
# ``vendored-unchanged`` hook and the CI ``vendored-NOT-touched`` step.
#
# Exit code:
#   * 0 — no vendored file modified against HEAD.
#   * 1 — at least one vendored file modified (the diff is echoed).
#
# Usage:
#   tools/check_vendored_unchanged.sh         # against HEAD (CI default)
#   tools/check_vendored_unchanged.sh origin/main  # against a ref
#
# The script is read-only: it never mutates the working tree. Bypassing
# it (with ``git commit --no-verify``) skips both the local hook AND
# the CI gate, so reviewers will catch the change at PR time anyway.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

# Vendored roots the CI enforces (matches .github/workflows/ci.yml +
# CONTRIBUTING.md §2 gate 6). Paths are repo-relative; an empty
# tree (e.g. data/Kanzi/ on a fresh clone) is silently skipped.
VENDORED_ROOTS=(
  "data/FlowMol3"
  "data/lineageflow_upstream"
  "data/Kanzi"
)

# Default ref is HEAD so the script behaves the same locally and in CI.
REF="${1:-HEAD}"

echo "Vendored NOT-touched check against ${REF} ..."
echo

violations=0
for root in "${VENDORED_ROOTS[@]}"; do
  if [ ! -d "${root}" ]; then
    # Vendored root not vendored yet (e.g. Kanzi on a fresh clone) —
    # skip silently. The vendoring process is documented in
    # docs/CONTRIBUTING-upstream.md (when present) or the Wave N
    # vendoring audit doc.
    echo "[skip] ${root} not vendored"
    continue
  fi

  # ``git diff --stat`` returns 0 if no diff, 1 if there is a diff. We
  # invert that logic so a vendored change is an exit-1 failure here.
  if diff_out="$(git diff --stat -- "${root}" "${REF}" -- . 2>&1)"; then
    echo "[ok]   ${root}"
  else
    echo "[FAIL] ${root} modified against ${REF}:"
    echo "${diff_out}" | sed 's/^/        /'
    violations=$((violations + 1))
  fi
done

echo
if [ "${violations}" -gt 0 ]; then
  echo "Vendored NOT-touched check FAILED: ${violations} tree(s) modified."
  echo "Vendored upstream must be edited in the upstream repo and re-vendored,"
  echo "not in-place. See docs/audit/waveNNN-vendoring-audit.md for the protocol."
  exit 1
fi

echo "Vendored NOT-touched check PASSED."
