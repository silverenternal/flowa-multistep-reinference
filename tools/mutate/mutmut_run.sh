#!/usr/bin/env bash
# Linux-targeted mutation-testing runner.
#
# Canonical entry point for the mutation-nightly GitHub Actions job
# (see .github/workflows/mutation-nightly.yml). Linux is the source of
# truth for mutation score because the upstream `mutmut` library does
# not run on Windows (see WINDOWS_LIMITATION.md, upstream issue 397).
#
# This wrapper is intentionally thin: it locates the repository root,
# sets the mutmut environment, and delegates to `run_mutmut.sh`, which
# owns the actual mutmut invocation, JSON snapshot capture, HTML
# report generation, and the survived-count threshold gate. Keeping
# the wrapper separate from the canonical runner lets us swap the
# runner implementation (e.g. point at a different mutmut version)
# without breaking callers that reference `mutmut_run.sh` by name.

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Delegate to the canonical Linux runner.
exec bash "$REPO_ROOT/tools/mutate/run_mutmut.sh" "$@"
