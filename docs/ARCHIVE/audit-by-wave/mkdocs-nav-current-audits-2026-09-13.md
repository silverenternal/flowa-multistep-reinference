# MkDocs current-audit navigation fix

Added a `Current audit records` group and a `Development workflow` entry to
`mkdocs.yml` for every previously omitted audit/workflow page. Existing nav
entries were preserved and no warning suppression or exclusion was added.

Validation command:

```text
./.venv/bin/python -m mkdocs build --strict \
  --site-dir /tmp/flowa-mkdocs-review
```

Result: documentation built successfully in 15.75 seconds with exit code 0.
The only output is the upstream Material-for-MkDocs future-version notice and
the existing optional Black/Ruff formatting notice; there are no omitted-file
or broken-link errors.

